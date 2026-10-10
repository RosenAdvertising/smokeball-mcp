# smokeball-mcp

[![PyPI version](https://img.shields.io/pypi/v/smokeball-mcp.svg)](https://pypi.org/project/smokeball-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP server for [Smokeball](https://smokeball.com) — full API coverage for law firm practice management. Use Smokeball from Claude Desktop with natural language.

## What you can do

- **Matters** — create, update, archive, tag, billing config, roles, relationships, stages
- **Contacts & Leads** — full CRUD, relations, tags, lead pipeline
- **Tasks & Events** — tasks, subtasks, task documents, calendar events, reminders
- **Files & Folders** — upload, download, preview, folder hierarchy, version history
- **Billing** — fees (time entries), expenses, invoices, activity codes, bank accounts, trust accounting
- **Portals** — client portal tasks and messages
- **Document generation** — layout designs, merge workflows, matter items
- **Administration** — staff, users, authorization groups/policies, plugins, webhooks, notifications

## Requirements

- Python 3.10+
- Python MCP SDK >=2.3,<3 (supports MCP protocol revision 2026-07-28)
- Claude Desktop (or any MCP-compatible client)
- Smokeball partner credentials (Client ID, Client Secret, API Key)

> **Smokeball partner access:** API credentials are issued through the Smokeball partner/developer program. Contact your Smokeball account representative to request API access.

## Installation

```bash
pip install smokeball-mcp
```

## Setup

Run the guided OAuth setup:

```bash
smokeball-mcp-setup
```

This will:

1. Ask for your region (US / AU / UK)
2. Ask for your Client ID, Client Secret, and API Key
3. Open the browser for Smokeball authorization
4. Save credentials to `~/.smokeball-mcp/`

Verify the connection:

```bash
smokeball-mcp-verify
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "smokeball": {
      "command": "smokeball-mcp"
    }
  }
}
```

Restart Claude Desktop. Smokeball tools will appear automatically.

## HTTP mode

Set `SMOKEBALL_MCP_TRANSPORT=streamable-http` to serve stateless Streamable HTTP
at `/mcp`. Each MCP 2026-07-28 request is a standalone POST; no initialization
or session ID is needed. The SDK also supports older clients on this endpoint.
Stdio remains the default.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `SMOKEBALL_MCP_TRANSPORT` | `stdio` | Select `stdio` or `streamable-http`. |
| `SMOKEBALL_MCP_HOST` | `127.0.0.1` | HTTP bind address. |
| `PORT` | `8080` | HTTP port (integer). |
| `SMOKEBALL_MCP_ALLOWED_HOSTS` | Unset | Required on non-loopback binds; comma-separated accepted Host headers, including ports (for example `mcp.firm.example,localhost:*`). |
| `SMOKEBALL_MCP_ALLOWED_ORIGINS` | Unset | Comma-separated accepted Origins (for example `https://app.firm.example`). On non-loopback binds, an unset list rejects every present Origin. |
| `SMOKEBALL_CLIENT_ID` | Existing credential store | Smokeball OAuth client ID. |
| `SMOKEBALL_CLIENT_SECRET` | Existing credential store | Smokeball OAuth client secret. |
| `SMOKEBALL_API_KEY` | Existing credential store | Smokeball partner API key. |
| `SMOKEBALL_REGION` | `us` | Smokeball region: `us`, `au`, or `uk`. |
| `SMOKEBALL_MCP_USE_KEYRING` | `1` | Set to `0` to disable the OS keyring and use environment/file credentials. |
| `SMOKEBALL_ALLOWED_DESTINATION_HOSTS` | Unset | Existing destination allowlist for webhook and plugin tools; see Approved destination URLs below. |

Use the existing setup wizard to provision OAuth tokens. HTTP tools resolve
credentials using the same environment and credential storage as stdio;
credentials are never supplied through HTTP requests.

```bash
SMOKEBALL_MCP_TRANSPORT=streamable-http PORT=8080 smokeball-mcp
```

The endpoint is `http://127.0.0.1:8080/mcp`. Loopback binds (`127.0.0.1`,
`localhost`, `::1`) use the SDK's built-in Host and Origin validation. Other
bind addresses require `SMOKEBALL_MCP_ALLOWED_HOSTS` before startup. Responses
use the SDK's default SSE behavior so disconnects cancel requests.

## Regions

| Region | API Base             |
| ------ | -------------------- |
| US     | api.smokeball.com    |
| AU     | api.smokeball.com.au |
| UK     | api.smokeball.co.uk  |

Region is set during setup and stored securely (OS keyring or `~/.smokeball-mcp/.env` fallback).

## Credential storage

By default credentials are stored in your operating system's native secret store
via the cross-platform [`keyring`](https://github.com/jaraco/keyring) library:

| OS      | Backend                                  |
| ------- | ---------------------------------------- |
| macOS   | Keychain                                 |
| Windows | Credential Manager                       |
| Linux   | Secret Service (GNOME Keyring / KWallet) |

Secrets are saved under the service name `smokeball-mcp`. With a working
keyring backend, credentials are not written to the file fallback.

**File fallback.** On a host with no keyring backend (e.g. a headless Linux box
without Secret Service), or if you set `SMOKEBALL_MCP_USE_KEYRING=0`, credentials
fall back to a `~/.smokeball-mcp/.env` file with `0600` permissions.

On Windows, the file is stored in the user's profile and protected by Windows'
default per-user access rules. On POSIX, files are created with `0600` permissions
and writes fail closed if private permissions cannot be established.

**Read order.** Credentials resolve in the order OS keyring → process environment
→ `.env` file. So a rotated secret in the keyring always wins, and a
`SMOKEBALL_CLIENT_ID` / `SMOKEBALL_API_KEY` exported in your shell overrides the
file fallback without touching the keyring.

## Authentication

Smokeball uses two credential layers:

- **OAuth 2.0 Bearer token** — user identity, obtained via auth code flow
- **x-api-key header** — app/partner identity, static key from Smokeball partner portal

Both are required for every API call. The setup wizard handles both.

## Example usage in Claude

> "List my open matters"
>
> "Create a task on matter abc-123 due next Friday — prepare hearing brief"
>
> "Add a fee entry for 2.5 hours on the Johnson matter, description: drafted motion to dismiss"
>
> "Show me all trust account transactions for the Smith matter"
>
> "Send a portal message to the client on matter xyz-456 — documents are ready for review"

## Tools

Full coverage across 30 Smokeball API resource categories — 189 tools total.

## License

MIT

### Approved destination URLs

Set `SMOKEBALL_ALLOWED_DESTINATION_HOSTS` in the server environment, for example
`SMOKEBALL_ALLOWED_DESTINATION_HOSTS=hooks.firm.example,.integrations.firm.example`.
Comma-separated exact hosts allow only that host; a leading dot allows the domain
and its subdomains. Matching ignores case and trailing dots and normalizes IDNA.
An empty or unset list refuses destination URLs before any request. HTTPS, no
userinfo, and public literal addresses remain required. This administrator-owned
list prevents model-supplied destinations from sending data to arbitrary hosts,
including private-address DNS aliases and unapproved redirectors. Approve only
hosts whose DNS and redirects the firm trusts; the vendor executes requests later.
Tools cannot change this setting.

`SMOKEBALL_REGION` is trimmed and lowercased before validation. It accepts only `us`, `au`, or `uk`. Setup also accepts the
corresponding menu numbers. Unknown values fail; they never select US.
