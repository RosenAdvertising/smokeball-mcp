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

Secrets are saved under the service name `smokeball-mcp`. Nothing is written to
disk in clear text.

**File fallback.** On a host with no keyring backend (e.g. a headless Linux box
without Secret Service), or if you set `SMOKEBALL_MCP_USE_KEYRING=0`, credentials
fall back to a `~/.smokeball-mcp/.env` file with `0600` permissions.

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
