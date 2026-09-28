# smokeball-mcp — MCP 2026-07-28 migration report

## Verdict

**MIGRATED (not a no-op).** The default branch baseline was `main` at
`03917bb`, matching `origin/main`. It declared `mcp>=1.28.1,<2`, locked
`mcp==1.28.1`, targeted protocol `2025-11-25`, constructed v1 `FastMCP`, and
had no tracked tests or MCP protocol guard.

The migration pins `mcp==2.0.0`, locks `mcp-types==2.0.0`, constructs SDK v2
`MCPServer`, and guards protocol `2026-07-28`. Existing stdio transport, 189
tools, three resources, three prompts, downstream Smokeball OAuth/token state,
credential-storage order, and private zero-TTL cache posture are preserved.
Modern negotiation selects `2026-07-28`; SDK-supported legacy mode still
selects `2025-11-25`.

The official-changelog classification and repository-specific reasoning are
in [`SPEC-DELTA-2026-07-28.md`](SPEC-DELTA-2026-07-28.md).

No push, deployment, live Smokeball request, live account, or external write
was performed. Offline tests set inert environment values before importing the
server so they do not consult a user credential store.

## Implementation

- Replaced `FastMCP` with `MCPServer` and declared server version `0.1.0`.
- Kept the shipped `mcp.run()` transport as stdio. The Streamable HTTP app is
  instantiated only in memory for raw-wire conformance tests.
- Pinned SDK v2 exactly and refreshed the lock for the `mcp-types`/`httpx2`
  dependency split.
- Added a lightweight guard for the latest and modern protocol constants.
- Retained all existing string-returning tool contracts and downstream
  credential/token lifecycle. No current-only extension, MRTR flow, publisher,
  event store, custom subscription bus, or MCP session state was added.
- Added an explicit core Ruff policy at the repository's declared Python 3.10
  floor.

## Raw-wire conformance

The migration suite proves:

- sessionless `server/discover`, exact supported revision, actual capabilities,
  server identity, and no unused extension declaration;
- modern per-request metadata plus `MCP-Protocol-Version`, `Mcp-Method`, and
  `Mcp-Name` routing headers;
- `resultType: complete`, `ttlMs: 0`, and `cacheScope: private` across discovery,
  every list category, and resource reads;
- deterministic discovery of all 189 tools and JSON object input schemas;
- modern and legacy negotiation from the same server;
- resource-not-found `-32602`, header mismatch `-32020`, unsupported protocol
  `-32022`, and unknown method `-32601`;
- validation errors use the SDK v2 tool-result model without making a vendor
  call.

## Test inventory

Before migration, from the original lock:

- `uv sync --frozen`: passed after recreating the generated virtual environment
  with the host's compatible arm64 Python.
- `pytest -q`: **0/0 tracked tests**; pytest reported no tests and exited 5.
- unrestricted current Ruff: **11 pre-existing findings**.
- installed lock target: `mcp==1.28.1`, protocol `2025-11-25`.

After migration, from the refreshed lock:

- `uv lock --check`: passed.
- `uv sync --locked --all-groups`: passed; 45 packages checked.
- `pytest -q tests/test_spec_2026_07_28.py`: **7/7 passed**.
- `pytest -q tests/test_canary_regressions.py`: **44/44 passed**.
- `pytest -q`: **51/51 passed**.
- `python tests/spec_check.py`: **PASS (`2026-07-28`)**.
- `ruff check .`: **passed** under the declared core policy.
- Python compilation and stdio EOF startup/shutdown smoke: **passed**.
- installed: `mcp==2.0.0`, `mcp-types==2.0.0`.

## Canary sibling checks

### A. LIST-TOOL LIMIT/ORDER — FIXED / CLASSIFIED

All list-style tools were inventoried. The 18 existing offset-paginated tools
made one request each and did not auto-paginate, so there was no multiplied-page
overrun. They now expose schema-enforced `limit` 1–200 and `offset >= 0`, apply
the same validation in the direct client, and defensively trim common list
response shapes to the caller's total limit. Regressions cover every method,
one-request behavior, exact parameter forwarding, invalid bounds, and upstream
over-return.

Eleven established finite reference/configuration/child `list_*` tools have no
pagination surface in this repository and are explicitly allowlisted with a
reason in the audit test. Repository evidence contains no supported Smokeball
sort/order parameter or oldest-first contract. The task's network boundary
excludes vendor documentation, so no guessed parameter was added; vendor order
behavior remains method-verified-only.

### B. SILENT REJECTIONS — FIXED

Webhook URL guards, malformed matter-tag JSON, invalid string booleans, list
bounds, missing credential/token state, transport failures, non-JSON responses,
rate limits, upstream status failures, OAuth callback guards, and OAuth token
failures now emit fixed PII-free reason logs. Invalid tool values reject before
client construction. Regressions assert that supplied values and record IDs do
not enter logs.

### C. ORIGIN/CSP CEREMONY — FIXED; SUBPATTERNS N/A

The repository serves local OAuth callback HTML, so this item is not a blanket
N/A. The callback now requires the exact `/callback` path, binds the browser
round trip to a cryptographically random one-time OAuth `state`, suppresses
access-query logging, and sends `no-store`, `nosniff`, `no-referrer`, and a
restrictive CSP (`default-src`, `frame-ancestors`, `base-uri`, and
`form-action` all deny by default).

The Clio `Sec-Fetch-Site` fallback governs same-origin setup POSTs and would be
wrong for an expected cross-site OAuth GET redirect; OAuth state is the
applicable CSRF defense here. The CSP navigation-handoff pattern is also N/A
because this CLI opens the authorization URL directly and serves no
authorization redirect/handoff page.

### D. PII-IN-LOGS — FIXED / CLEAN

Verification no longer prints a firm name, OAuth setup no longer prints the
authorization URL, and vendor/OAuth response bodies were removed from
exceptions and console output. Transport errors no longer expose request paths.
The final logger sweep contains fixed reason categories plus method, numeric
status, and wait duration only. Marker regressions prove that names, emails,
OAuth `sub` values, URLs, record IDs, codes, states, and upstream bodies do not
reach logs or public error text.

## Commit split

The alternate branch contains, oldest first:

```text
7ed8756 docs: document MCP 2026-07-28 delta
40ea00f feat: migrate server to MCP 2026-07-28
6488de9 test: prove MCP 2026-07-28 conformance
docs: report MCP 2026-07-28 migration (this report commit)
```

Every commit carries:

```text
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

## Git sandbox wall and handoff

The canonical `.git` rejected branch creation with `Operation not permitted`
while creating `refs/heads/spec-2026-07-28.lock`. The requested branch and
commits were therefore built in the authorized alternate Git database. A
verified portable bundle with complete history is exported to:

```text
/private/tmp/claude-501/-Users-tobyrosen-Cowork-RA-Projects/7c2bbcf3-be6b-4bd4-bbc9-3870b657affb/scratchpad/fanout/smokeball-spec-2026-07-28.bundle
```

The bundle must be imported into the canonical repository when its `.git` is
writable. Nothing was pushed.

## Honest limitations

- No live Smokeball account/API test was run. Vendor request paths,
  pagination-response shapes, unpaginated collection contracts, and order
  behavior remain method-verified offline only.
- Streamable HTTP is exercised in memory only for spec conformance; the shipped
  process remains stdio-only.
- The portable bundle needs importing before `spec-2026-07-28` exists in the
  canonical `.git`.
