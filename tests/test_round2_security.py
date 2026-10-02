"""Round 2 policy regressions through registered MCP calls, with mocked transport."""

import pytest
from test_daybreak_security import BAD_URLS, invoke, text
from test_daybreak_security import api as api

SETTING = "SMOKEBALL_ALLOWED_DESTINATION_HOSTS"


@pytest.mark.parametrize(
    "name,args,key",
    [
        ("create_webhook_subscription", {"event_type": "probe"}, "url"),
        ("update_webhook_subscription", {"subscription_id": "probe"}, "url"),
        ("create_plugin", {"name": "probe"}, "url"),
        ("update_plugin", {"plugin_id": "probe"}, "url"),
    ],
)
@pytest.mark.parametrize(
    "url",
    BAD_URLS
    + [
        "https://127.0.0.1.sslip.io/",
        "https://example.com/redirect?next=http%3A%2F%2F127.0.0.1%2F",
        "https://unlisted.example/",
        "https://hooks.firm.example.attacker.example/",
        "https://nothooks.firm.example/",
    ],
)
def test_unapproved_destination_zero_requests(api, monkeypatch, name, args, key, url):
    monkeypatch.setenv(SETTING, "hooks.firm.example")
    arguments = dict(args)
    arguments[key] = url
    result = invoke(name, arguments)
    assert result.is_error, text(result)
    api.post.assert_not_called()
    api.put.assert_not_called()


@pytest.mark.parametrize(
    "name,args,key",
    [
        ("create_webhook_subscription", {"event_type": "probe"}, "url"),
        ("update_webhook_subscription", {"subscription_id": "probe"}, "url"),
        ("create_plugin", {"name": "probe"}, "url"),
        ("update_plugin", {"plugin_id": "probe"}, "url"),
    ],
)
@pytest.mark.parametrize("setting", [None, "", " , "])
def test_missing_allowlist_actionable_zero_requests(
    api, monkeypatch, name, args, key, setting
):
    if setting is None:
        monkeypatch.delenv(SETTING, raising=False)
    else:
        monkeypatch.setenv(SETTING, setting)
    url = "https://hooks.firm.example/event"
    arguments = dict(args)
    arguments[key] = url
    result = invoke(name, arguments)
    assert result.is_error, text(result)
    assert SETTING in text(result)
    api.post.assert_not_called()
    api.put.assert_not_called()


@pytest.mark.parametrize(
    "name,args,key",
    [
        ("create_webhook_subscription", {"event_type": "probe"}, "url"),
        ("update_webhook_subscription", {"subscription_id": "probe"}, "url"),
        ("create_plugin", {"name": "probe"}, "url"),
        ("update_plugin", {"plugin_id": "probe"}, "url"),
    ],
)
@pytest.mark.parametrize(
    "setting,url",
    [
        ("hooks.firm.example", "https://hooks.firm.example/event"),
        (
            " unrelated.example, HOOKS.FIRM.EXAMPLE. ",
            "https://HOOKS.FIRM.EXAMPLE./event",
        ),
        (".firm.example", "https://firm.example/event"),
        (".firm.example", "https://sub.hooks.firm.example/event"),
        ("bücher.example", "https://xn--bcher-kva.example/event"),
        ("xn--bcher-kva.example", "https://bücher.example/event"),
    ],
)
def test_approved_destination_preserved(
    api, monkeypatch, name, args, key, setting, url
):
    monkeypatch.setenv(SETTING, setting)
    arguments = dict(args)
    arguments[key] = url
    result = invoke(name, arguments)
    assert not result.is_error, text(result)
    assert api.post.called or api.put.called
    assert url in str(api.post.call_args_list + api.put.call_args_list)


@pytest.mark.parametrize(
    "name,args,key",
    [
        ("create_webhook_subscription", {"event_type": "probe"}, "url"),
        ("update_webhook_subscription", {"subscription_id": "probe"}, "url"),
        ("create_plugin", {"name": "probe"}, "url"),
        ("update_plugin", {"plugin_id": "probe"}, "url"),
    ],
)
@pytest.mark.parametrize(
    "setting,url",
    [
        ("firm.example", "https://sub.firm.example/"),
        (".firm.example", "https://notfirm.example/"),
        (".firm.example", "https://firm.example.attacker.example/"),
        ("*", "https://hooks.firm.example/"),
        ("https://hooks.firm.example", "https://hooks.firm.example/"),
        ("hooks.firm.example/path", "https://hooks.firm.example/"),
        ("hooks.firm.example:443", "https://hooks.firm.example/"),
    ],
)
def test_allowlist_is_exact_and_fail_closed(
    api, monkeypatch, name, args, key, setting, url
):
    monkeypatch.setenv(SETTING, setting)
    arguments = dict(args)
    arguments[key] = url
    result = invoke(name, arguments)
    assert result.is_error, text(result)
    api.post.assert_not_called()
    api.put.assert_not_called()


@pytest.mark.parametrize(
    "name,args,key",
    [
        ("create_webhook_subscription", {"event_type": "probe"}, "url"),
        ("update_webhook_subscription", {"subscription_id": "probe"}, "url"),
        ("create_plugin", {"name": "probe"}, "url"),
        ("update_plugin", {"plugin_id": "probe"}, "url"),
    ],
)
@pytest.mark.parametrize(
    "setting,url",
    [
        (None, "https://hooks.firm.example/"),
        ("hooks.firm.example", "https://127.0.0.1.sslip.io/"),
        (
            "hooks.firm.example",
            "https://example.com/redirect?next=http%3A%2F%2F127.0.0.1%2F",
        ),
    ],
)
def test_rejection_precedes_client_construction(
    monkeypatch, name, args, key, setting, url
):
    from unittest.mock import Mock

    from smokeball_mcp import server

    factory = Mock(side_effect=AssertionError("no client or token refresh"))
    monkeypatch.setattr(server, "SmokeBallClient", factory)
    if setting is None:
        monkeypatch.delenv(SETTING, raising=False)
    else:
        monkeypatch.setenv(SETTING, setting)
    arguments = dict(args)
    arguments[key] = url
    assert invoke(name, arguments).is_error
    factory.assert_not_called()


@pytest.mark.parametrize("region", ["US", " us ", "\tUS\n", "AU"])
def test_region_normalization_at_mcp(region):
    import os
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        import asyncio
        from unittest.mock import Mock
        from mcp.types import CallToolRequestParams
        from smokeball_mcp import client, server
        assert client.REGION == EXPECTED
        assert client.BASE_URL == client.REGIONS[EXPECTED]["api"]
        response = Mock(status_code=200, headers={}, ok=True)
        response.json.return_value = {"ok": True}
        session = Mock()
        session.request.return_value = response
        client.requests.Session = lambda: session
        tm = Mock(access_token="synthetic-value", refresh_token="")
        tm.is_expired.return_value = False
        tm.get_valid_token.return_value = "synthetic-value"
        client.TokenManager = lambda: tm
        client.ORG_ID = "synthetic-org"
        client.API_KEY = "synthetic-key"
        result = asyncio.run(server.mcp._handle_call_tool(
            None, CallToolRequestParams(name="get_firm", arguments={})))
        assert not result.is_error, result
        assert session.request.call_args.args[1].startswith(client.BASE_URL + "/")
    """)
    code = code.replace("EXPECTED", repr(region.strip().lower()))
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=dict(os.environ, SMOKEBALL_REGION=region),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("region", ["US", " au ", " UK "])
def test_setup_normalizes_region(monkeypatch, tmp_path, region):
    from unittest.mock import Mock

    from smokeball_mcp.setup import oauth_flow

    answers = iter([region, "synthetic-id"])
    monkeypatch.setattr("builtins.input", lambda *a: next(answers))
    monkeypatch.setattr(oauth_flow.getpass, "getpass", lambda *a: "synthetic-value")
    browser = Mock(return_value=True)
    monkeypatch.setattr(oauth_flow.webbrowser, "open", browser)

    def callback(*args):
        def handle():
            oauth_flow._auth_code = "synthetic-code"

        return Mock(handle_request=handle)

    monkeypatch.setattr(oauth_flow, "HTTPServer", callback)
    response = Mock(status_code=200)
    response.json.return_value = {"access_token": "synthetic-value"}
    post = Mock(return_value=response)
    monkeypatch.setattr(oauth_flow.requests, "post", post)
    save = Mock(return_value="file")
    monkeypatch.setattr(oauth_flow.credentials, "set_secret", save)
    monkeypatch.setattr(oauth_flow, "CONFIG_DIR", tmp_path)
    oauth_flow.main()
    normalized = region.strip().lower()
    auth = oauth_flow.REGIONS[normalized]["auth"]
    assert browser.call_args.args[0].startswith(auth + "/connect/authorize?")
    assert post.call_args.args[0] == auth + "/connect/token"
    save.assert_any_call("SMOKEBALL_REGION", normalized)
