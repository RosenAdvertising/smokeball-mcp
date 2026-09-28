# MCP specification delta: 2025-11-25 to 2026-07-28

Research date: 2026-08-09. Sources are limited to the official MCP
specification and the official MCP Python SDK repository/documentation.

## Current target and migration release

This repository requires migration rather than conformance-only verification:

- `pyproject.toml` declares `mcp>=1.28.1,<2`, and `uv.lock` resolves MCP Python
  SDK 1.28.1. That SDK line targets protocol `2025-11-25`.
- `smokeball_mcp/server.py` constructs v1 `FastMCP` and uses the default stdio
  `mcp.run()` entry point. It registers 189 tools, three resources, and three
  prompts.
- There were no tracked tests or MCP protocol guard on the default branch.

The official changelog says `2026-07-28` follows `2025-11-25`
([spec changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).
The implementation release is MCP Python SDK `2.0.0`, which supports the new
revision and earlier revisions from the same server
([SDK v2.0.0 release notes](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0)).
The required source port follows the official
[v1-to-v2 migration guide](https://py.sdk.modelcontextprotocol.io/migration/).

Verdicts below mean:

- **AFFECTS-US**: this server exposes or relies on the changed surface. The SDK
  may implement the wire behavior, but the migration must pin, configure, or
  test it.
- **NOT-APPLICABLE**: the feature or direction is not implemented here and is
  not being added merely because the revision permits it.

## Protocol negotiation and lifecycle

| Normative change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Protocol sessions and `Mcp-Session-Id` are removed for modern requests. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | Every modern request must be independently dispatchable. The stdio server keeps no MCP session state; downstream OAuth/token state remains application state. |
| Modern requests remove `initialize` and carry version/capabilities in `_meta`; version mismatch uses the reserved unsupported-version error. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | SDK v2's dual-era dispatcher must accept self-describing modern requests while retaining legacy negotiation. |
| Servers must implement `server/discover`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | Discovery must report `2026-07-28`, identity, and the actual tool/resource/prompt capabilities. |
| Every result requires `resultType`, normally `"complete"`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **AFFECTS-US** | Discovery, tool, resource, and prompt results all require the SDK v2 wire field. |
| Server-initiated requests are replaced by Multi Round-Trip Requests (MRTR). [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | No handler uses sampling, roots, elicitation, or another server-to-client request. |
| `ping`, `logging/setLevel`, and roots-change notifications are removed; protocol logs become request opt-in. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | The application implements none of those methods and does not emit MCP logging notifications. |

## Transports and notifications

| Normative change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Streamable HTTP POSTs require `Mcp-Method` and, for named methods, `Mcp-Name`; `x-mcp-header` can map selected tool parameters to HTTP headers. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE to the shipped transport; conformance-tested** | Production remains stdio-only. An in-memory SDK Streamable HTTP app will verify the v2 routing behavior without adding a hosted transport or parameter-header mapping. |
| HTTP GET and resource subscribe/unsubscribe are replaced by `subscriptions/listen`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | No HTTP transport, subscription publisher, event store, or custom notification bus is exposed. |
| SSE resumability and redelivery are removed. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | No SSE/event-store behavior exists. |
| Legacy HTTP+SSE is deprecated. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | The shipped server exposes stdio only. |

## Capabilities and extensions

| Normative change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Client and server capabilities gain `extensions`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | Discovery exposes this shape; the server must not advertise an extension it does not implement. |
| Experimental core tasks move to `io.modelcontextprotocol/tasks`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#major-changes) | **NOT-APPLICABLE** | There are no MCP task handlers or task-augmented tools. Smokeball practice-management tasks are ordinary vendor records exposed through tools. |
| Roots, Sampling, and Logging are deprecated. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | None is declared or used. |
| Sampling `includeContext` values are deprecated. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | Sampling is not used. |

## Tools, resources, prompts, and cache semantics

| Normative change | Verdict | Repository-specific reason |
| --- | --- | --- |
| List/read results require `ttlMs` and `cacheScope`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | The server exposes tools, resources, and prompts. SDK v2's conservative `ttlMs: 0`, `cacheScope: private` policy preserves the existing no-cache posture. |
| `tools/list` should be deterministic. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | The 189 registered tools must retain stable declaration order across listings. |
| Tool schemas accept JSON Schema 2020-12; structured content may be any JSON value. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | SDK v2 generates the schemas. Existing string-returning tool behavior is preserved; bounded list arguments will be asserted in generated schemas. |
| Resource-not-found changes from `-32002` to Invalid Params `-32602`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | Unknown Smokeball resource URIs must produce `-32602`. |
| URL elicitation completion notification and `elicitationId` are removed. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | Elicitation is not used. |
| Generated numeric schema metadata is corrected. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#other-schema-changes) | **NOT-APPLICABLE** | The repository does not vendor or directly validate against the generated MCP schema artifact; SDK v2 absorbs the correction. |

## Authorization and security

| Normative change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Authorization servers should return `iss`, and MCP clients must validate it before code redemption. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | This process is not an MCP authorization server or MCP OAuth client. Its downstream Smokeball OAuth flow is outside MCP transport authorization and is preserved. |
| MCP Dynamic Client Registration requires `application_type`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | The code does not dynamically register an MCP client. |
| Persisted MCP client credentials must be issuer-bound. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | No MCP client registration is stored. |
| Dynamic Client Registration is deprecated in favor of Client ID Metadata Documents. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#deprecated) | **NOT-APPLICABLE** | Neither DCR role is implemented. |

## Errors, metadata, and observability

| Normative change | Verdict | Repository-specific reason |
| --- | --- | --- |
| MCP reserves `-32020..-32099`; header mismatch, missing capability, and unsupported version become `-32020`, `-32021`, and `-32022`; unknown methods use `-32601`. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **AFFECTS-US** | SDK v2 dispatch is authoritative. Tests cover all reachable errors without manufacturing a feature requiring a client capability. |
| `_meta` defines W3C trace-context keys. [Source](https://modelcontextprotocol.io/specification/2026-07-28/changelog#minor-changes) | **NOT-APPLICABLE** | The server has no MCP trace-context integration of its own. |

Governance and SEP workflow changes do not impose a runtime requirement on
this repository. The feature lifecycle is respected by not adding deprecated
Roots, Sampling, Logging, HTTP+SSE, or DCR behavior.

## SDK v2 source-port classification

The official migration guide identifies many SDK changes; only these touch the
repository:

- **AFFECTS-US:** dependency split and raised SDK release; `FastMCP` renamed to
  `MCPServer`; explicit server version; protocol constants/types now supplied
  by SDK v2/`mcp-types`; sync handlers execute through SDK v2; transport options
  belong on `run()`/app methods; raw-wire test utilities must use v2 clients
  and models.
- **NOT-APPLICABLE:** no subclass/`call_tool` override, explicit result-model
  construction, direct low-level server, custom context, auth provider, MCP
  client, WebSocket, mounted HTTP path, event store, or server-initiated
  request exists. No current-only protocol feature will be added.
