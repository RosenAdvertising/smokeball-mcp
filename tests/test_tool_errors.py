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
            "Error executing tool get_firm: Missing credential SMOKEBALL_API_KEY. Run: smokeball-mcp-setup",
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
    [("12", 12), ("999999999999999999999", 60), ("https://token.invalid", 10)],
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
            "Smokeball authorization was rejected or expired. Re-authorize with: smokeball-mcp-setup",
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
