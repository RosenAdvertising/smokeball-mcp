"""Offline checks for the production stateless HTTP app and shared credentials."""

from __future__ import annotations

import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from threading import Barrier
from unittest.mock import Mock

import httpx2
import pytest
import requests
from mcp import Client, StdioServerParameters

from smokeball_mcp import client as vendor
from smokeball_mcp import server

PROTOCOL = "2026-07-28"
META_PREFIX = "io.modelcontextprotocol/"


def _request(method, params=None, *, request_id=1, client_name="http-test"):
    params = dict(params or {})
    params["_meta"] = {
        META_PREFIX + "protocolVersion": PROTOCOL,
        META_PREFIX + "clientCapabilities": {},
        META_PREFIX + "clientInfo": {"name": client_name, "version": "0"},
    }
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": PROTOCOL,
        "mcp-method": method,
    }
    if method == "tools/call":
        headers["mcp-name"] = params["name"]
    return headers, {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }


def _payload(response):
    assert response.status_code == 200, response.text
    if response.headers["content-type"].startswith("text/event-stream"):
        messages = [
            json.loads(line[6:])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        return next(message for message in messages if "result" in message)
    return response.json()


@asynccontextmanager
async def _http_client():
    app = server.create_serve_app()
    async with app.router.lifespan_context(app):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1:8080"
        ) as client:
            yield client


async def _post(client, method, params=None, **kwargs):
    headers, body = _request(method, params, **kwargs)
    return await client.post("/mcp", headers=headers, json=body)


@pytest.fixture(autouse=True)
def transport_environment(monkeypatch):
    for name in (
        "SMOKEBALL_MCP_TRANSPORT",
        "SMOKEBALL_MCP_HOST",
        "SMOKEBALL_MCP_ALLOWED_HOSTS",
        "SMOKEBALL_MCP_ALLOWED_ORIGINS",
        "PORT",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.asyncio
async def test_http_list_matches_real_stdio_names_and_schemas():
    async with _http_client() as client:
        response = await _post(client, "tools/list")
    http_tools = _payload(response)["result"]["tools"]
    stdio = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from smokeball_mcp.server import main; main()"],
        env={
            "SMOKEBALL_MCP_TRANSPORT": "stdio",
            "SMOKEBALL_MCP_USE_KEYRING": "0",
            "SMOKEBALL_CLIENT_ID": "offline-test-client",
            "SMOKEBALL_CLIENT_SECRET": "offline-test-secret",
            "SMOKEBALL_API_KEY": "offline-test-api-key",
            "SMOKEBALL_REGION": "us",
        },
    )
    async with Client(stdio, cache=None) as client:
        stdio_tools = await client.list_tools()
    assert {tool["name"]: tool["inputSchema"] for tool in http_tools} == {
        tool.name: tool.input_schema for tool in stdio_tools.tools
    }
    assert len(http_tools) == 189
    assert "mcp-session-id" not in response.headers


@pytest.mark.asyncio
async def test_read_tool_uses_existing_vendor_environment_and_request_mock(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(vendor, "CONFIG_DIR", tmp_path)
    (tmp_path / "tokens.json").write_text('{"access_token": "offline-token"}')
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"id": "firm-marker", "name": "Offline firm"}'
    request = Mock(return_value=response)
    monkeypatch.setattr(requests.Session, "request", request)
    async with _http_client() as client:
        result = _payload(await _post(client, "tools/call", {"name": "get_firm"}))[
            "result"
        ]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == response.json()
    request.assert_called_once_with(
        "GET",
        vendor.BASE_URL + "/firm",
        params=None,
        json=None,
        timeout=30,
        allow_redirects=False,
    )


@pytest.mark.asyncio
async def test_disconnect_cancels_the_http_handler(monkeypatch):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def pending_tool(name, arguments, context=None):
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(server.mcp, "call_tool", pending_tool)
    app = server.create_serve_app()
    headers, body = _request("tools/call", {"name": "get_firm"})
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (name.encode(), value.encode())
            for name, value in {**headers, "host": "127.0.0.1:8080"}.items()
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8080),
    }
    body_sent = False

    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": json.dumps(body).encode()}
        await started.wait()
        return {"type": "http.disconnect"}

    async def send(_message):
        pass

    async with app.router.lifespan_context(app):
        await asyncio.wait_for(app(scope, receive, send), timeout=5)
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_tool_boundary_propagates_cancellation(monkeypatch):
    class CancelledClient:
        def get_firm(self):
            raise asyncio.CancelledError()

    monkeypatch.setattr(server, "SmokeBallClient", CancelledClient)
    with pytest.raises(asyncio.CancelledError):
        await server.mcp.call_tool("get_firm", {})


@pytest.mark.asyncio
async def test_requests_have_independent_connections_and_one_lifespan(monkeypatch):
    events = []
    connections = []
    original_call = server.mcp.call_tool

    @asynccontextmanager
    async def lifespan(_server):
        events.append("start")
        yield {"shared_config": "configured-once"}
        events.append("stop")

    async def observe(name, arguments, context=None):
        connection = context.session
        connections.append(connection)
        assert not hasattr(connection, "previous_request_marker")
        connection.previous_request_marker = True
        return await original_call(name, arguments, context)

    instance = object.__new__(vendor.SmokeBallClient)
    instance.get_firm = Mock(return_value={"id": "firm-marker"})
    monkeypatch.setattr(server, "SmokeBallClient", lambda: instance)
    monkeypatch.setattr(server.mcp, "call_tool", observe)
    monkeypatch.setattr(server.mcp._lowlevel_server, "lifespan", lifespan)
    async with _http_client() as client:
        first = await _post(
            client, "tools/call", {"name": "get_firm"}, client_name="first"
        )
        second = await _post(
            client,
            "tools/call",
            {"name": "get_firm"},
            request_id=2,
            client_name="second",
        )
        assert events == ["start"]
        assert _payload(first)["id"] == 1
        assert _payload(second)["id"] == 2
    assert events == ["start", "stop"]
    assert connections[0] is not connections[1]
    assert [item.client_params.client_info.name for item in connections] == [
        "first",
        "second",
    ]
    assert all("mcp-session-id" not in item.headers for item in (first, second))


@pytest.mark.parametrize("value", [None, "", " STDIO "])
def test_default_and_explicit_stdio_preserve_run_call(monkeypatch, value):
    if value is not None:
        monkeypatch.setenv("SMOKEBALL_MCP_TRANSPORT", value)
    run = Mock()
    monkeypatch.setattr(server.mcp, "run", run)
    server.main()
    run.assert_called_once_with()


def test_bogus_transport_exits_with_both_options(monkeypatch):
    monkeypatch.setenv("SMOKEBALL_MCP_TRANSPORT", "bogus")
    with pytest.raises(
        SystemExit, match="SMOKEBALL_MCP_TRANSPORT.*stdio.*streamable-http"
    ):
        server.main()


def test_http_transport_dispatches(monkeypatch):
    monkeypatch.setenv("SMOKEBALL_MCP_TRANSPORT", " STREAMABLE-HTTP ")
    calls = []

    async def serve():
        calls.append("http")

    monkeypatch.setattr(server, "_serve_streamable_http", serve)
    server.main()
    assert calls == ["http"]


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_uses_sdk_security(monkeypatch, host):
    monkeypatch.setenv("SMOKEBALL_MCP_HOST", host)
    assert server._transport_security() is None
    server.create_serve_app()
    manager = server.mcp._lowlevel_server.session_manager
    assert manager.security_settings.enable_dns_rebinding_protection
    assert manager.json_response is False
    assert manager.stateless is True


@pytest.mark.parametrize("allowed_hosts", [None, "", " , "])
def test_non_loopback_requires_allowed_hosts(monkeypatch, allowed_hosts):
    monkeypatch.setenv("SMOKEBALL_MCP_HOST", "0.0.0.0")
    if allowed_hosts is not None:
        monkeypatch.setenv("SMOKEBALL_MCP_ALLOWED_HOSTS", allowed_hosts)
    with pytest.raises(SystemExit, match="SMOKEBALL_MCP_ALLOWED_HOSTS"):
        server.create_serve_app()


@pytest.mark.asyncio
async def test_host_and_origin_allowlists_are_enforced(monkeypatch):
    monkeypatch.setenv("SMOKEBALL_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("SMOKEBALL_MCP_ALLOWED_HOSTS", " 127.0.0.1:8080, firm.example ")
    monkeypatch.setenv("SMOKEBALL_MCP_ALLOWED_ORIGINS", " https://firm.example, ")
    headers, body = _request("tools/list")
    async with _http_client() as client:
        good = await client.post(
            "/mcp", headers={**headers, "origin": "https://firm.example"}, json=body
        )
        bad_host = await client.post(
            "/mcp", headers={**headers, "host": "attacker.example"}, json=body
        )
        bad_origin = await client.post(
            "/mcp", headers={**headers, "origin": "https://attacker.example"}, json=body
        )
    assert good.status_code == 200
    assert bad_host.status_code == 421
    assert bad_origin.status_code == 403


@pytest.mark.asyncio
async def test_omitted_origin_allowlist_refuses_present_origin(monkeypatch):
    monkeypatch.setenv("SMOKEBALL_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("SMOKEBALL_MCP_ALLOWED_HOSTS", "127.0.0.1:8080")
    headers, body = _request("tools/list")
    async with _http_client() as client:
        response = await client.post(
            "/mcp", headers={**headers, "origin": "https://firm.example"}, json=body
        )
        no_origin = await _post(client, "tools/list")
    assert response.status_code == 403
    assert no_origin.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "DELETE"])
async def test_get_and_delete_return_405(method):
    async with _http_client() as client:
        response = await client.request(
            method, "/mcp", headers={"mcp-protocol-version": PROTOCOL}
        )
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert "mcp-session-id" not in response.headers


@pytest.mark.asyncio
async def test_discovery_exposes_package_identity():
    async with _http_client() as client:
        result = _payload(await _post(client, "server/discover"))["result"]
    assert PROTOCOL in result["supportedVersions"]
    info = result["_meta"][META_PREFIX + "serverInfo"]
    assert info["name"] == "smokeball-mcp"
    assert info["title"] == "Smokeball MCP"
    assert info["version"] == server.version("smokeball-mcp")


@pytest.mark.parametrize("value,expected", [(None, 8080), (" 9080 ", 9080)])
def test_port_and_host_defaults(monkeypatch, value, expected):
    if value is not None:
        monkeypatch.setenv("PORT", value)
    assert server._port() == expected
    assert server._host() == "127.0.0.1"


def test_invalid_port_exits_clearly(monkeypatch):
    monkeypatch.setenv("PORT", "not-a-number")
    with pytest.raises(SystemExit, match="PORT must be an integer"):
        server._port()


@pytest.mark.asyncio
async def test_uvicorn_uses_configured_host_port_and_disables_access_log(monkeypatch):
    import uvicorn

    monkeypatch.setenv("SMOKEBALL_MCP_HOST", "localhost")
    monkeypatch.setenv("PORT", "9080")
    configs = []

    class FakeServer:
        def __init__(self, config):
            configs.append(config)

        async def serve(self):
            pass

    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    await server._serve_streamable_http()
    assert len(configs) == 1
    assert configs[0].host == "localhost"
    assert configs[0].port == 9080
    assert configs[0].access_log is False


def test_concurrent_refresh_reuses_the_rotated_tokens(monkeypatch, tmp_path):
    monkeypatch.setattr(vendor, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(vendor, "CLIENT_ID", "offline-test-client")
    monkeypatch.setattr(vendor, "CLIENT_SECRET", "offline-test-secret")
    (tmp_path / "tokens.json").write_text(
        '{"access_token": "initial-access", "refresh_token": "initial-refresh"}'
    )
    managers = [vendor.TokenManager(), vendor.TokenManager()]
    response = requests.Response()
    response.status_code = 200
    response._content = (
        b'{"access_token": "rotated-access", "refresh_token": "rotated-refresh"}'
    )
    post = Mock(return_value=response)
    monkeypatch.setattr(vendor.requests, "post", post)
    ready = Barrier(2)

    def refresh(manager):
        ready.wait(timeout=5)
        return manager.refresh()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(refresh, managers))
    assert post.call_count == 1
    assert post.call_args.kwargs["data"]["refresh_token"] == "initial-refresh"
    assert (
        results[0] == results[1] == json.loads((tmp_path / "tokens.json").read_text())
    )


@pytest.mark.asyncio
async def test_unknown_tool_remains_an_error_result():
    async with _http_client() as client:
        result = _payload(await _post(client, "tools/call", {"name": "unknown"}))[
            "result"
        ]
    assert result["isError"] is True


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_transport_selects_stdio(monkeypatch, value):
    monkeypatch.setenv("SMOKEBALL_MCP_TRANSPORT", value)
    run = Mock()
    monkeypatch.setattr(server.mcp, "run", run)
    server.main()
    run.assert_called_once_with()


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_host_yields_loopback(monkeypatch, value):
    monkeypatch.setenv("SMOKEBALL_MCP_HOST", value)
    assert server._host() == "127.0.0.1"


def test_uppercase_localhost_is_non_loopback(monkeypatch):
    monkeypatch.setenv("SMOKEBALL_MCP_HOST", "LOCALHOST")
    assert server._host() == "LOCALHOST"
    with pytest.raises(SystemExit, match="SMOKEBALL_MCP_ALLOWED_HOSTS"):
        server.create_serve_app()


def test_server_import_without_installed_distribution():
    import subprocess

    probe = (
        "import importlib.metadata\n"
        "from unittest.mock import patch\n"
        "real_version = importlib.metadata.version\n"
        "def effect(name):\n"
        "    if name == 'smokeball-mcp':\n"
        "        raise importlib.metadata.PackageNotFoundError(name)\n"
        "    return real_version(name)\n"
        "with patch.object(importlib.metadata, 'version', side_effect=effect):\n"
        "    import smokeball_mcp.server as reloaded\n"
        "    assert reloaded.mcp is not None\n"
        "print('import-ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "import-ok" in result.stdout
