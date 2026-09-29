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
            RuntimeError("SMOKEBALL_API_KEY is required. Run: smokeball-mcp-setup"),
            "Error executing tool get_firm: Missing credential SMOKEBALL_API_KEY. Run: smokeball-mcp-setup",
        ),
        (
            RuntimeError("Token refresh failed (401)"),
            "Error executing tool get_firm: Smokeball authorization was rejected or expired. Re-authorize with: smokeball-mcp-setup",
        ),
        (
            RuntimeError("Smokeball API error 503"),
            "Error executing tool get_firm: Smokeball API request failed (HTTP 503). The service is temporarily unavailable.",
        ),
        (
            RuntimeError("Smokeball rate limit exceeded; retry_after_seconds=12"),
            "Error executing tool get_firm: Smokeball rate limit exceeded (HTTP 429). Retry after 12 seconds.",
        ),
        (
            RuntimeError("Smokeball API error 404"),
            "Error executing tool get_firm: The requested item was not found (HTTP 404). Check the ID and try again.",
        ),
        (
            RuntimeError(
                "untrusted bearer-FAKE_TOKEN https://person@example.invalid/?secret=PII"
            ),
            "Error executing tool get_firm: Tool failed unexpectedly. Check the server logs and try again.",
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
    if "unexpected" in expected:
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
