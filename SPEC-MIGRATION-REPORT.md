# Smokeball MCP protocol migration

This server targets MCP protocol revision `2026-07-28`. Its runtime
requirement is `mcp>=2.2,<3`; `uv.lock` resolves both `mcp` and `mcp-types` to
`2.2.0`. The server uses `MCPServer` with version `0.1.0` and runs over stdio.
It exposes 189 tools, three resources, and three prompts.

The SDK handles modern discovery and per-request metadata while retaining
legacy protocol negotiation. Modern list and read results use
`resultType: complete`, `ttlMs: 0`, and `cacheScope: private`. Unknown resources return
Invalid Params (`-32602`). Protocol mappings and applicability notes are in
[the specification delta](SPEC-DELTA-2026-07-28.md).

The migration also bounds offset-paginated list arguments to `limit` 1–200
and `offset >= 0`, retains one upstream request per list call, and logs fixed
rejection reasons without supplied values. The local OAuth callback checks
its path and one-time state and returns restrictive response headers. The
shipped transport remains stdio; protocol HTTP behavior is tested through an
in-process SDK app.

## Reproduce locally

Use the project's locked virtual environment. These commands set inert
credentials and disable keyring before Python imports the client, so the tests
do not read a user's credential store. Tests use fake vendor responses.

```bash
SMOKEBALL_MCP_USE_KEYRING=0 SMOKEBALL_CLIENT_ID=offline-test-client SMOKEBALL_CLIENT_SECRET=offline-test-secret SMOKEBALL_API_KEY=offline-test-api-key SMOKEBALL_REGION=us .venv/bin/pytest -q
SMOKEBALL_MCP_USE_KEYRING=0 SMOKEBALL_CLIENT_ID=offline-test-client SMOKEBALL_CLIENT_SECRET=offline-test-secret SMOKEBALL_API_KEY=offline-test-api-key SMOKEBALL_REGION=us .venv/bin/python tests/spec_check.py
.venv/bin/ruff check .
uv lock --check --offline
```

The tests establish local SDK and protocol behavior with mocks and in-process
transport. Live Smokeball API behavior, hosted transport, vendor pagination,
and ordering remain outside this validation scope.

## Open product decision

MCP 2.2.0 masks messages from tool exceptions other than `ToolError` or
`ResourceError`, returning a generic client error. Retaining that masking
limits leakage; explicitly safe `ToolError` messages could give clients more
actionable feedback. Toby should decide which errors, if any, warrant a safe
public message. Existing exception handling remains unchanged.
