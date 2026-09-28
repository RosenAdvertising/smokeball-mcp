"""Fleet canary regressions for list controls, rejection logs, and PII hygiene."""

from __future__ import annotations

import asyncio
import builtins
import http.client
import threading
from urllib.parse import parse_qs, urlsplit

import pytest
from mcp import Client

from smokeball_mcp import client, server
from smokeball_mcp.setup import oauth_flow, verify

PAGINATED_TOOLS = {
    "search_staff",
    "list_contacts",
    "list_matters",
    "list_leads",
    "list_matter_types",
    "list_tasks",
    "list_events",
    "list_memos_on_matter",
    "list_fees",
    "list_expenses",
    "list_invoices",
    "list_activity_codes",
    "list_bank_accounts",
    "list_transactions",
    "list_files_on_matter",
    "get_file_history",
    "get_folder_history",
    "list_referral_types",
}

# These established client methods expose finite child/configuration collections
# without pagination parameters. Vendor documentation is outside this task's
# allowed network scope, so the migration records them instead of inventing a
# Smokeball query contract.
UNPAGINATED_LIST_TOOL_REASONS = {
    "list_matter_type_categories": "finite reference collection",
    "list_stage_sets": "finite reference collection",
    "list_matter_stage_mappings": "finite configuration collection",
    "list_authorization_groups": "finite configuration collection",
    "list_plugins": "finite configuration collection",
    "list_plugin_subscriptions": "finite configuration collection",
    "list_layout_designs": "finite reference collection",
    "list_layouts_on_matter": "finite matter child collection",
    "list_matter_items": "finite matter child collection",
    "list_webhook_subscriptions": "finite configuration collection",
    "list_webhook_event_types": "finite reference collection",
}


def _registered_tools():
    async def get_tools():
        async with Client(server.mcp, cache=None) as mcp_client:
            return (await mcp_client.list_tools()).tools

    return asyncio.run(get_tools())


def test_every_list_tool_is_bounded_or_explicitly_classified() -> None:
    tools = {tool.name: tool for tool in _registered_tools()}
    audited = {
        name
        for name in tools
        if name.startswith("list_")
        or name in {"search_staff", "get_file_history", "get_folder_history"}
    }
    assert audited == PAGINATED_TOOLS | set(UNPAGINATED_LIST_TOOL_REASONS)

    for name in PAGINATED_TOOLS:
        properties = tools[name].input_schema["properties"]
        assert properties["limit"]["minimum"] == 1
        assert properties["limit"]["maximum"] == 200
        assert properties["offset"]["minimum"] == 0
        assert "sort" not in properties
        assert "order" not in properties


@pytest.mark.parametrize(
    ("method", "args", "kwargs", "path", "extra"),
    [
        ("search_staff", (), {"query": "query-marker"}, "/staff", {"query": "query-marker"}),
        ("list_contacts", (), {}, "/contacts", {}),
        ("list_matters", (), {}, "/matters", {}),
        ("list_leads", (), {}, "/leads", {}),
        ("list_matter_types", (), {}, "/mattertypes", {}),
        ("get_tasks", (), {"matter_id": "matter-marker"}, "/tasks", {"matterId": "matter-marker"}),
        ("get_events", (), {"matter_id": "matter-marker"}, "/events", {"matterId": "matter-marker"}),
        ("get_memos_on_matter", ("matter-marker",), {}, "/matters/matter-marker/memos", {}),
        ("get_fees", (), {"matter_id": "matter-marker"}, "/fees", {"matterId": "matter-marker"}),
        ("get_expenses", (), {"matter_id": "matter-marker"}, "/expenses", {"matterId": "matter-marker"}),
        ("get_invoices", (), {"matter_id": "matter-marker"}, "/invoices", {"matterId": "matter-marker"}),
        ("get_activity_codes", (), {}, "/activitycodes", {}),
        ("get_bank_accounts", (), {}, "/bankaccounts", {}),
        ("get_transactions", ("account-marker",), {}, "/bankaccounts/account-marker/transactions", {}),
        ("get_files_on_matter", ("matter-marker",), {}, "/matters/matter-marker/files", {}),
        ("get_file_history", ("matter-marker",), {}, "/matters/matter-marker/files/history", {}),
        ("get_folder_history", ("matter-marker",), {}, "/matters/matter-marker/folders/history", {}),
        ("get_referral_types", (), {}, "/referraltypes", {}),
    ],
)
def test_paginated_client_methods_make_one_request_and_enforce_total_cap(
    monkeypatch, method, args, kwargs, path, extra
) -> None:
    instance = object.__new__(client.SmokeBallClient)
    calls = []

    def fake_get(request_path, params):
        calls.append((request_path, params))
        return {"value": list(range(7)), "total": 7}

    monkeypatch.setattr(instance, "get", fake_get)
    result = getattr(instance, method)(*args, limit=2, offset=3, **kwargs)

    assert calls == [(path, {"limit": 2, "offset": 3, **extra})]
    assert result == {"value": [0, 1], "total": 7}


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (201, 0), (1, -1)])
def test_direct_client_list_bounds_reject_before_http(
    monkeypatch, caplog, limit, offset
) -> None:
    instance = object.__new__(client.SmokeBallClient)
    monkeypatch.setattr(
        instance,
        "get",
        lambda *_args, **_kwargs: pytest.fail("HTTP must not be attempted"),
    )
    caplog.set_level("WARNING", logger=client.__name__)

    with pytest.raises(ValueError):
        instance.list_matters(limit=limit, offset=offset)

    assert "list_request_rejected" in caplog.text


@pytest.mark.parametrize(
    "url",
    [
        "http://person-marker.example/callback",
        "https://",
        "https://127.0.0.1/person-marker",
        "https://person-marker.local/callback",
    ],
)
def test_webhook_rejections_log_only_fixed_reasons(caplog, url) -> None:
    caplog.set_level("WARNING", logger=client.__name__)
    with pytest.raises(ValueError) as exc_info:
        client._validate_webhook_url(url)

    assert "webhook_url_rejected reason=" in caplog.text
    assert "person-marker" not in caplog.text
    assert "person-marker" not in str(exc_info.value)
    assert url not in caplog.text


@pytest.mark.parametrize(
    ("payload", "reason"),
    [("person-marker@example.com", "invalid_json"), ('"person-marker"', "not_array")],
)
def test_matter_tag_rejections_are_logged_without_payload(caplog, payload, reason) -> None:
    caplog.set_level("WARNING", logger=server.__name__)
    result = server.add_matter_tags("matter-marker", payload)

    assert "error" in result
    assert f"reason={reason}" in caplog.text
    assert "person-marker" not in caplog.text
    assert "matter-marker" not in caplog.text


@pytest.mark.parametrize(
    ("tool_name", "invoke"),
    [
        ("update_task", lambda marker: server.update_task("record-marker", completed_str=marker)),
        ("update_subtask", lambda marker: server.update_subtask("record-marker", "child-marker", completed_str=marker)),
        ("create_fee", lambda marker: server.create_fee("matter-marker", "staff-marker", "2026-01-01", 1, billable=marker)),
        ("update_fee", lambda marker: server.update_fee("record-marker", billable=marker)),
        ("patch_fee", lambda marker: server.patch_fee("record-marker", billable=marker)),
        ("create_expense", lambda marker: server.create_expense("matter-marker", "2026-01-01", 1.0, billable=marker)),
        ("update_expense", lambda marker: server.update_expense("record-marker", billable=marker)),
        ("patch_expense", lambda marker: server.patch_expense("record-marker", billed=marker)),
        ("update_portal_task", lambda marker: server.update_portal_task("record-marker", completed_str=marker)),
        ("update_webhook_subscription", lambda marker: server.update_webhook_subscription("record-marker", active=marker)),
    ],
)
def test_boolean_rejections_are_pii_free_and_precede_client_creation(
    monkeypatch, caplog, tool_name, invoke
) -> None:
    marker = "person-marker@example.com"
    monkeypatch.setattr(
        server,
        "SmokeBallClient",
        lambda: pytest.fail("client must not be constructed"),
    )
    caplog.set_level("WARNING", logger=server.__name__)

    with pytest.raises(ValueError) as exc_info:
        invoke(marker)

    assert f"tool={tool_name}" in caplog.text
    assert "reason=invalid_boolean" in caplog.text
    assert marker not in caplog.text
    assert "record-marker" not in caplog.text
    assert marker not in str(exc_info.value)


def test_credential_guards_log_pii_free_reasons(monkeypatch, caplog) -> None:
    caplog.set_level("WARNING", logger=client.__name__)
    monkeypatch.setattr(client, "API_KEY", "")
    with pytest.raises(RuntimeError):
        client.SmokeBallClient()
    assert "reason=missing_api_key" in caplog.text

    caplog.clear()
    monkeypatch.setattr(client, "API_KEY", "configured")

    class EmptyTokenManager:
        access_token = ""
        refresh_token = ""

    monkeypatch.setattr(client, "TokenManager", EmptyTokenManager)
    with pytest.raises(RuntimeError):
        client.SmokeBallClient()
    assert "reason=missing_oauth_tokens" in caplog.text
    assert "configured" not in caplog.text


def test_refresh_guards_and_upstream_failures_are_pii_free(monkeypatch, caplog) -> None:
    caplog.set_level("WARNING", logger=client.__name__)
    manager = object.__new__(client.TokenManager)
    manager.tokens = {}

    with pytest.raises(RuntimeError):
        manager.refresh()
    assert "reason=missing_refresh_token" in caplog.text

    caplog.clear()
    manager.tokens = {"refresh_token": "refresh-marker"}
    monkeypatch.setattr(client, "CLIENT_ID", "")
    monkeypatch.setattr(client, "CLIENT_SECRET", "")
    with pytest.raises(RuntimeError):
        manager.refresh()
    assert "reason=missing_oauth_client_config" in caplog.text
    assert "refresh-marker" not in caplog.text

    caplog.clear()
    marker = "Person Marker person-marker@example.com sub=private-sub"

    class Response:
        status_code = 400
        text = marker

    monkeypatch.setattr(client, "CLIENT_ID", "configured-id")
    monkeypatch.setattr(client, "CLIENT_SECRET", "configured-secret")
    monkeypatch.setattr(client.requests, "post", lambda *_args, **_kwargs: Response())
    with pytest.raises(RuntimeError) as exc_info:
        manager.refresh()
    assert marker not in str(exc_info.value)
    assert marker not in caplog.text
    assert "reason=upstream_status" in caplog.text


def test_vendor_error_body_and_request_path_do_not_reach_error_or_log(
    monkeypatch, caplog
) -> None:
    marker = "Person Marker person-marker@example.com sub=private-sub"

    class Response:
        status_code = 500
        text = marker
        ok = False
        headers = {}

    class Session:
        def request(self, *_args, **_kwargs):
            return Response()

    instance = object.__new__(client.SmokeBallClient)
    instance.session = Session()
    caplog.set_level("WARNING", logger=client.__name__)

    with pytest.raises(RuntimeError) as exc_info:
        instance._request("GET", "/contacts/person-marker@example.com")

    assert marker not in str(exc_info.value)
    assert "person-marker" not in str(exc_info.value)
    assert marker not in caplog.text
    assert "person-marker" not in caplog.text
    assert "reason=upstream_status" in caplog.text


def test_verify_output_does_not_emit_firm_name_or_exception_text(
    monkeypatch, capsys
) -> None:
    marker = "Person Marker person-marker@example.com"

    class FakeClient:
        def get_firm(self):
            return {"name": marker}

        def list_matters(self, limit):
            assert limit == 5
            return {"value": []}

    monkeypatch.setattr(client, "SmokeBallClient", FakeClient)
    assert verify.check_api() is True
    output = capsys.readouterr().out
    assert marker not in output
    assert "Authenticated to Smokeball" in output

    class FailingClient:
        def __init__(self):
            raise RuntimeError(marker)

    monkeypatch.setattr(client, "SmokeBallClient", FailingClient)
    assert verify.check_api() is False
    assert marker not in capsys.readouterr().out


def _callback_request(path: str) -> tuple[int, dict[str, str], bytes]:
    http_server = oauth_flow.HTTPServer(("127.0.0.1", 0), oauth_flow._CallbackHandler)
    thread = threading.Thread(target=http_server.handle_request)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", http_server.server_port)
    connection.request("GET", path)
    response = connection.getresponse()
    result = (response.status, dict(response.getheaders()), response.read())
    connection.close()
    thread.join(timeout=5)
    http_server.server_close()
    assert not thread.is_alive()
    return result


def test_oauth_callback_is_state_bound_and_has_restrictive_headers(caplog) -> None:
    expected_state = "expected-state-marker"
    oauth_flow._oauth_state = expected_state
    oauth_flow._auth_code = None
    caplog.set_level("WARNING", logger=oauth_flow.__name__)

    status, headers, _body = _callback_request(
        "/callback?code=private-code-marker&state=wrong-state-marker"
    )
    assert status == 400
    assert oauth_flow._auth_code is None
    assert "reason=state_mismatch" in caplog.text
    assert "marker" not in caplog.text

    caplog.clear()
    status, _headers, _body = _callback_request("/person-marker?state=wrong-marker")
    assert status == 404
    assert "reason=unexpected_path" in caplog.text
    assert "marker" not in caplog.text

    caplog.clear()
    status, headers, _body = _callback_request(
        f"/callback?code=private-code-marker&state={expected_state}"
    )
    assert status == 200
    assert oauth_flow._auth_code == "private-code-marker"
    assert oauth_flow._oauth_state is None
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    csp = headers["Content-Security-Policy"]
    for directive in (
        "default-src 'none'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ):
        assert directive in csp
    assert "private-code-marker" not in caplog.text


def test_oauth_setup_binds_state_without_printing_authorization_url(
    monkeypatch, tmp_path, capsys
) -> None:
    inputs = iter(["1", "client-id-marker", "client-secret-marker", "api-key-marker"])
    opened_urls = []
    posted = {}

    class FakeServer:
        def __init__(self, *_args, **_kwargs):
            pass

        def handle_request(self):
            oauth_flow._auth_code = "private-code-marker"

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"access_token": "token-marker"}

    def fake_post(url, data):
        posted.update({"url": url, "data": data})
        return Response()

    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(oauth_flow, "HTTPServer", FakeServer)
    monkeypatch.setattr(
        oauth_flow.webbrowser,
        "open",
        lambda url: opened_urls.append(url) or True,
    )
    monkeypatch.setattr(oauth_flow.requests, "post", fake_post)
    monkeypatch.setattr(oauth_flow.credentials, "set_secret", lambda *_args: "keyring")
    monkeypatch.setattr(oauth_flow.credentials, "storage_backend", lambda: "test-keyring")
    monkeypatch.setattr(oauth_flow, "CONFIG_DIR", tmp_path)

    oauth_flow.main()

    assert len(opened_urls) == 1
    query = parse_qs(urlsplit(opened_urls[0]).query)
    assert query["state"] == [oauth_flow._oauth_state]
    assert query["client_id"] == ["client-id-marker"]
    assert posted["data"]["code"] == "private-code-marker"
    output = capsys.readouterr().out
    for marker in (
        "client-id-marker",
        "client-secret-marker",
        "api-key-marker",
        "private-code-marker",
        "token-marker",
        opened_urls[0],
    ):
        assert marker not in output
