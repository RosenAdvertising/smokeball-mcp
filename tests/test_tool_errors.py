"""Safe, actionable error text as observed through the MCP SDK client."""

from __future__ import annotations

import asyncio

import pytest
import requests
from mcp import Client

from smokeball_mcp import client as smokeball_client
from smokeball_mcp import server


async def _call(name: str, arguments: dict[str, object] | None = None):
    async with Client(server.mcp, cache=None) as sdk_client:
        return await sdk_client.call_tool(name, arguments or {})


def _text(result) -> str:
    block = result.content[0]
    assert block.type == "text"
    return block.text


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (
            smokeball_client.MissingCredentialsError("api_key"),
            "Error executing tool get_firm: Smokeball credentials are missing. Set SMOKEBALL_CLIENT_ID, SMOKEBALL_CLIENT_SECRET, and SMOKEBALL_API_KEY, then run smokeball-mcp-setup and restart the MCP server.",
        ),
        (
            smokeball_client.AccessDeniedError("access_denied"),
            "Error executing tool get_firm: Smokeball access denied: the connected account lacks permission for this action (or the authorization expired; re-run smokeball-mcp-setup if so).",
        ),
        (
            smokeball_client.AuthenticationError("rejected"),
            "Error executing tool get_firm: Smokeball authorization was rejected or expired. Re-authorize with: smokeball-mcp-setup",
        ),
        (
            smokeball_client.VendorHTTPError(
                503, "The service is temporarily unavailable."
            ),
            "Error executing tool get_firm: Smokeball API request failed (HTTP 503). The service is temporarily unavailable.",
        ),
        (
            smokeball_client.RateLimitError(12),
            "Error executing tool get_firm: Smokeball rate limit exceeded (HTTP 429). Retry after 12 seconds.",
        ),
        (
            smokeball_client.VendorHTTPError(404, "not found"),
            "Error executing tool get_firm: The requested item was not found (HTTP 404). Check the ID and try again.",
        ),
        (
            RuntimeError(
                "untrusted bearer-FAKE_TOKEN https://person@example.invalid/?secret=PII"
            ),
            "Error executing tool get_firm",
        ),
    ],
)
def test_error_classes_are_safe_at_sdk_boundary(monkeypatch, caplog, failure, expected):
    class FakeClient:
        def get_firm(self):
            raise failure

    monkeypatch.setattr(server, "SmokeBallClient", FakeClient)
    caplog.set_level("WARNING")
    result = asyncio.run(_call("get_firm"))

    assert result.is_error is True
    assert _text(result) == expected
    assert "FAKE_TOKEN" not in _text(result)
    assert "person@example.invalid" not in caplog.text
    assert "PII" not in caplog.text
    assert "https://" not in caplog.text
    if expected == "Error executing tool get_firm":
        assert "tool_call_failed reason=unexpected" in caplog.text


def test_argument_validation_is_sanitized_before_tool_execution():
    result = asyncio.run(_call("list_matters", {"limit": "PII-MARKER"}))

    assert result.is_error is True
    assert _text(result) == (
        "Invalid arguments: "
        "limit must be an integer from 1 to 200 (greater than or equal to 1)"
    )
    assert "PII-MARKER" not in _text(result)


@pytest.mark.parametrize(
    ("header", "expected_wait"),
    [("12", 12), ("300", 300), ("nan", 10), ("https://token.invalid", 10)],
)
def test_retry_after_is_bounded_and_rejects_untrusted_text(header, expected_wait):
    class Response:
        status_code = 429
        headers = {"Retry-After": header}

    assert smokeball_client._retry_after_seconds(Response()) == expected_wait


def test_rate_limit_tool_text_uses_safe_retry_after(monkeypatch):
    instance = object.__new__(smokeball_client.SmokeBallClient)

    class Response:
        status_code = 429
        ok = False
        headers = {"Retry-After": "https://token.invalid/FAKE_TOKEN"}

    instance.session = requests.Session()
    monkeypatch.setattr(
        instance.session, "request", lambda *_args, **_kwargs: Response()
    )
    monkeypatch.setattr(smokeball_client.time, "sleep", lambda _seconds: None)
    with pytest.raises(RuntimeError, match="retry_after_seconds=10"):
        instance._request("GET", "/safe")


@pytest.mark.parametrize(
    "failure",
    [
        ValueError("private@example.invalid"),
        TypeError("token=FAKE"),
        RuntimeError("Token refresh failed (private@example.invalid)"),
        RuntimeError("private@example.invalid API error 404"),
    ],
)
def test_unknown_messages_are_not_classified_as_known_failures(
    monkeypatch, caplog, failure
):
    def fail():
        raise failure

    monkeypatch.setattr(server, "SmokeBallClient", fail)
    caplog.set_level("WARNING")
    result = asyncio.run(_call("get_firm"))
    assert result.is_error
    assert _text(result) == "Error executing tool get_firm"
    assert "private@example.invalid" not in caplog.text
    assert "token=FAKE" not in caplog.text
    assert "tool_call_failed reason=unexpected" in caplog.text


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (
            401,
            {"message": "private@example.invalid"},
            "Smokeball authorization was rejected or expired. Re-authorize with: smokeball-mcp-setup",
        ),
        (
            403,
            {"message": "token=FAKE"},
            "Smokeball access denied: the connected account lacks permission for this action (or the authorization expired; re-run smokeball-mcp-setup if so).",
        ),
        (
            404,
            {"message": "private@example.invalid"},
            "The requested item was not found (HTTP 404). Check the ID and try again.",
        ),
        (
            400,
            {"code": "invalid_request", "message": "private@example.invalid"},
            "Smokeball API request failed (HTTP 400). The request is invalid.",
        ),
        (
            503,
            {"message": "https://example.invalid/?key=FAKE"},
            "Smokeball API request failed (HTTP 503). The service is temporarily unavailable.",
        ),
        (
            429,
            {"message": "private@example.invalid"},
            "Smokeball rate limit exceeded (HTTP 429). Retry after 12 seconds.",
        ),
    ],
)
def test_http_failures_cross_real_client_and_sdk(
    monkeypatch, caplog, status, body, expected
):
    import json

    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    response.headers["Retry-After"] = "12"
    instance = object.__new__(smokeball_client.SmokeBallClient)
    instance.session = requests.Session()
    instance.tm = object.__new__(smokeball_client.TokenManager)
    instance.tm.tokens = {"access_token": "unused"}
    monkeypatch.setattr(instance.tm, "refresh", lambda: None)
    monkeypatch.setattr(instance.session, "request", lambda *_args, **_kwargs: response)
    monkeypatch.setattr(smokeball_client.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(server, "SmokeBallClient", lambda: instance)
    result = asyncio.run(_call("get_firm"))
    assert result.is_error
    assert _text(result) == "Error executing tool get_firm: " + expected
    assert "private@example.invalid" not in caplog.text
    assert "token=FAKE" not in caplog.text


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (
            400,
            "Smokeball authorization was rejected or expired. Re-authorize with: smokeball-mcp-setup",
        ),
        (
            500,
            "Smokeball API request failed (HTTP 500). The service had an internal error.",
        ),
    ],
)
def test_oauth_refresh_distinguishes_rejected_grant_from_vendor_outage(
    monkeypatch, status, expected
):
    response = requests.Response()
    response.status_code = status
    response._content = b'{"error":"invalid_grant","message":"private@example.invalid"}'
    manager = object.__new__(smokeball_client.TokenManager)
    manager.tokens = {"refresh_token": "unused"}
    monkeypatch.setattr(smokeball_client, "CLIENT_ID", "unused")
    monkeypatch.setattr(smokeball_client, "CLIENT_SECRET", "unused")
    monkeypatch.setattr(
        smokeball_client.requests, "post", lambda *_args, **_kwargs: response
    )

    class FakeClient:
        def get_firm(self):
            return manager.refresh()

    monkeypatch.setattr(server, "SmokeBallClient", FakeClient)
    result = asyncio.run(_call("get_firm"))
    assert result.is_error
    assert _text(result) == "Error executing tool get_firm: " + expected


def test_missing_argument_names_expected_shape():
    result = asyncio.run(_call("get_matter"))
    assert result.is_error
    assert _text(result) == "Invalid arguments: matter_id must be a required string"


@pytest.mark.parametrize(
    ("method", "failure", "expected"),
    [
        (
            "GET",
            requests.Timeout("secret marker"),
            "Smokeball could not be reached. Check the connection and retry.",
        ),
        (
            "GET",
            requests.ConnectionError("secret marker"),
            "Smokeball could not be reached. Check the connection and retry.",
        ),
        (
            "PUT",
            requests.Timeout("secret marker"),
            "Smokeball request outcome is unknown. Check whether it completed before retrying.",
        ),
        (
            "PUT",
            requests.ConnectionError("secret marker"),
            "Smokeball request outcome is unknown. Check whether it completed before retrying.",
        ),
    ],
)
def test_transport_failures_use_http_method_at_sdk_boundary(
    monkeypatch, caplog, method, failure, expected
):
    instance = object.__new__(smokeball_client.SmokeBallClient)
    instance.session = requests.Session()

    def fail(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(instance.session, "request", fail)
    monkeypatch.setattr(server, "SmokeBallClient", lambda: instance)
    caplog.set_level("WARNING")
    if method == "GET":
        result = asyncio.run(_call("get_firm"))
    else:
        result = asyncio.run(_call("update_firm", {"name": "safe"}))
    assert result.is_error is True
    assert (
        _text(result)
        == "Error executing tool "
        + ("get_firm" if method == "GET" else "update_firm")
        + ": "
        + expected
    )
    assert "secret marker" not in _text(result)
    assert "secret marker" not in caplog.text


def test_retry_after_over_sixty_seconds_is_preserved_without_sleep(monkeypatch):
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "300"
    instance = object.__new__(smokeball_client.SmokeBallClient)
    instance.session = requests.Session()
    sleeps = []
    monkeypatch.setattr(instance.session, "request", lambda *_a, **_k: response)
    monkeypatch.setattr(smokeball_client.time, "sleep", sleeps.append)
    with pytest.raises(smokeball_client.RateLimitError) as error:
        instance._request("GET", "/safe")
    assert error.value.retry_after == 300
    assert sleeps == []


def test_retry_after_cumulative_sleep_never_exceeds_sixty(monkeypatch):
    responses = []
    for hint in ("40", "30"):
        response = requests.Response()
        response.status_code = 429
        response.headers["Retry-After"] = hint
        responses.append(response)
    instance = object.__new__(smokeball_client.SmokeBallClient)
    instance.session = requests.Session()
    monkeypatch.setattr(instance.session, "request", lambda *_a, **_k: responses.pop(0))
    sleeps = []
    monkeypatch.setattr(smokeball_client.time, "sleep", sleeps.append)
    with pytest.raises(smokeball_client.RateLimitError) as error:
        instance._request("GET", "/safe")
    assert sleeps == [40]
    assert sum(sleeps) <= 60
    assert error.value.retry_after == 30


def test_string_id_path_segment_is_escaped(monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"ok":true}'
    instance = object.__new__(smokeball_client.SmokeBallClient)
    instance.session = requests.Session()
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return response

    monkeypatch.setattr(instance.session, "request", fake_request)
    instance.get_staff_member("../x")
    assert captured["url"].endswith("/staff/..%2Fx")
    assert "/staff/../x" not in captured["url"]
    assert captured["kwargs"]["timeout"] == 30


def test_secondary_string_path_id_is_escaped(monkeypatch):
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"ok":true}'
    instance = object.__new__(smokeball_client.SmokeBallClient)
    instance.session = requests.Session()
    captured = {}
    monkeypatch.setattr(
        instance.session,
        "request",
        lambda method, url, **kwargs: captured.update(url=url) or response,
    )
    instance.get_contact_relation("parent", "../x")
    assert captured["url"].endswith("/contacts/parent/relations/..%2Fx")
    assert "/relations/../x" not in captured["url"]


@pytest.mark.parametrize("status", [302, 307, 308])
def test_data_redirect_is_not_followed_or_returned_as_success(monkeypatch, status):
    response = requests.Response()
    response.status_code = status
    response.headers["Location"] = "https://redirect.invalid/collect"
    response._content = b'{"access_token":"redirected-token"}'
    instance = object.__new__(smokeball_client.SmokeBallClient)
    instance.session = requests.Session()
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return response

    monkeypatch.setattr(instance.session, "request", fake_request)
    with pytest.raises(smokeball_client.VendorHTTPError) as error:
        instance.get("/firm")
    assert error.value.status == status
    assert captured["kwargs"]["allow_redirects"] is False
    assert captured["kwargs"]["timeout"] == 30


@pytest.mark.parametrize("status", [302, 307, 308])
def test_refresh_token_redirect_is_not_followed_or_accepted(monkeypatch, status):
    response = requests.Response()
    response.status_code = status
    response.headers["Location"] = "https://redirect.invalid/collect"
    response._content = b'{"access_token":"redirected-token"}'
    manager = object.__new__(smokeball_client.TokenManager)
    manager.tokens = {"refresh_token": "dummy-refresh-token"}
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, kwargs=kwargs)
        return response

    monkeypatch.setattr(smokeball_client, "CLIENT_ID", "dummy-client")
    monkeypatch.setattr(smokeball_client, "CLIENT_SECRET", "dummy-secret")
    monkeypatch.setattr(smokeball_client.requests, "post", fake_post)
    with pytest.raises(smokeball_client.VendorHTTPError) as error:
        manager.refresh()
    assert error.value.status == status
    assert captured["kwargs"]["allow_redirects"] is False
    assert captured["kwargs"]["timeout"] == 30


def test_resource_read_masks_exception_and_does_not_log(caplog, monkeypatch):
    marker = "https://person@example.invalid/?token=SECRET"

    def fail():
        raise RuntimeError(marker)

    monkeypatch.setattr(server, "SmokeBallClient", fail)
    caplog.set_level("WARNING")
    with pytest.raises(Exception) as error:
        asyncio.run(server.mcp.read_resource("smokeball://matter_types"))
    assert str(error.value) == "Unable to read the requested Smokeball resource."
    assert marker not in caplog.text
    assert "SECRET" not in str(error.value)


def test_fallback_credentials_are_private_before_writing(tmp_path, monkeypatch):
    import os
    from smokeball_mcp import credentials

    config = tmp_path / "config"
    target = config / ".env"
    monkeypatch.setattr(credentials, "CONFIG_DIR", config)
    monkeypatch.setattr(credentials, "ENV_FILE", target)
    original = os.fdopen
    modes = []

    def checked_open(fd, *args, **kwargs):
        modes.append(os.fstat(fd).st_mode & 0o777)
        return original(fd, *args, **kwargs)

    monkeypatch.setattr(os, "fdopen", checked_open)
    credentials._write_env_file({"TEST_CREDENTIAL": "first-fake-value"})
    target.chmod(0o644)
    credentials._write_env_file({"TEST_CREDENTIAL": "replacement-fake-value"})
    assert modes == [0o600, 0o600]
    assert target.read_text() == "TEST_CREDENTIAL=replacement-fake-value\n"
