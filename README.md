# Smokeball MCP server

[![CI](https://github.com/RosenAdvertising/smokeball-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/RosenAdvertising/smokeball-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP 2026-07-28](https://img.shields.io/badge/MCP-2026--07--28-7C3AED.svg)](https://modelcontextprotocol.io)
[![PyPI version](https://img.shields.io/pypi/v/smokeball-mcp.svg)](https://pypi.org/project/smokeball-mcp/)

Connect Claude and other MCP clients to Smokeball to manage matters, contacts, tasks, billing and documents.

Smokeball MCP server is a [Model Context Protocol](https://modelcontextprotocol.io) server for [Smokeball](https://smokeball.com), the law practice management platform. It registers 189 tools that read and write Smokeball data. It runs over stdio by default, for desktop clients such as Claude Desktop, and offers an opt-in stateless Streamable HTTP mode that implements MCP specification 2026-07-28. Smokeball credentials stay on the machine that runs the server: they come from the setup command and your operating system's keyring, or from environment variables, never from the client.

## Features

- **Matters**: create, update, archive, tag and delete matters, and manage billing configuration, roles, relationships and stages.
- **Contacts and leads**: create, read, update and delete contacts and leads, with contact relations and tags.
- **Tasks and events**: manage tasks, subtasks, task documents, calendar events and reminders.
- **Files and folders**: upload, download and preview files, browse the folder hierarchy and read version history.
- **Billing**: record fees and expenses, read invoices, manage activity codes, and work with bank accounts and trust transactions.
- **Client portal**: create and update portal tasks and send portal messages.
- **Document generation**: browse layout designs, add layouts to matters, merge them and read matter items.
- **Administration**: manage staff, users, authorization groups and policies, plugins, webhooks and notifications.

## Tools

The server registers 189 tools. They cover firm settings, staff and users, contacts, matters, leads, matter types and stages, roles and relationships, tasks and events, memos, fees, expenses, invoices, activity codes, bank accounts and transactions, files and folders, archiving, referral types, authorization, notifications, plugins, the client portal, document layouts, matter items, integrated search and webhooks. Tools that take a webhook or plugin URL accept only hosts approved in `SMOKEBALL_ALLOWED_DESTINATION_HOSTS` (see [Approved destination URLs](#approved-destination-urls)).

<details>
<summary>All 189 tools</summary>

- `add_contact_tags`
- `add_contact_to_layout`
- `add_file_to_matter`
- `add_files_to_matter_batch`
- `add_layout_to_matter`
- `add_matter_tags`
- `add_relationship_to_role`
- `add_role_to_matter`
- `archive_matter`
- `create_activity_code`
- `create_authorization_group`
- `create_authorization_policy`
- `create_contact`
- `create_contact_relation`
- `create_event`
- `create_event_reminder`
- `create_expense`
- `create_fee`
- `create_file_preview_request`
- `create_folder`
- `create_lead`
- `create_matter`
- `create_memo`
- `create_notification`
- `create_plugin`
- `create_portal_task`
- `create_requisition`
- `create_staff_member`
- `create_subtask`
- `create_task`
- `create_task_document`
- `create_transaction`
- `create_user`
- `create_webhook_subscription`
- `delete_activity_code`
- `delete_authorization_group`
- `delete_contact`
- `delete_contact_relation`
- `delete_event`
- `delete_event_reminder`
- `delete_expense`
- `delete_fee`
- `delete_file`
- `delete_firm_user_mapping`
- `delete_folder`
- `delete_lead`
- `delete_matter`
- `delete_memo`
- `delete_plugin`
- `delete_staff_member`
- `delete_subtask`
- `delete_task`
- `delete_task_document`
- `delete_webhook_subscription`
- `get_activity_code`
- `get_authorization_group`
- `get_authorization_policy`
- `get_bank_account`
- `get_bank_account_matter_balances`
- `get_contact`
- `get_contact_relation`
- `get_contact_relations`
- `get_contact_tags`
- `get_event`
- `get_event_reminders`
- `get_expense`
- `get_fee`
- `get_file`
- `get_file_download_url`
- `get_file_history`
- `get_file_preview_info`
- `get_file_preview_info_by_version`
- `get_file_upload_url`
- `get_firm`
- `get_firm_user_mapping`
- `get_firm_user_mappings`
- `get_folder_contents`
- `get_folder_history`
- `get_folder_path_hierarchy`
- `get_invoice`
- `get_invoice_download_url`
- `get_layout_contacts`
- `get_layout_design`
- `get_layout_on_matter`
- `get_lead`
- `get_matter`
- `get_matter_archive`
- `get_matter_billing_configuration`
- `get_matter_item`
- `get_matter_stage`
- `get_matter_tags`
- `get_matter_type`
- `get_memo`
- `get_notification`
- `get_plugin`
- `get_plugin_subscription`
- `get_plugin_url`
- `get_protected_bank_account_balance`
- `get_referral_type`
- `get_relationship_on_role`
- `get_relationships_on_matter`
- `get_role_on_matter`
- `get_roles_on_matter`
- `get_root_folder_contents`
- `get_search_mapping`
- `get_staff_member`
- `get_stage_in_set`
- `get_stage_set`
- `get_subtask`
- `get_subtasks`
- `get_task`
- `get_task_document`
- `get_task_documents`
- `get_transaction`
- `get_user`
- `get_webhook_subscription`
- `list_activity_codes`
- `list_authorization_groups`
- `list_bank_accounts`
- `list_contacts`
- `list_events`
- `list_expenses`
- `list_fees`
- `list_files_on_matter`
- `list_invoices`
- `list_layout_designs`
- `list_layouts_on_matter`
- `list_leads`
- `list_matter_items`
- `list_matter_stage_mappings`
- `list_matter_type_categories`
- `list_matter_types`
- `list_matters`
- `list_memos_on_matter`
- `list_plugin_subscriptions`
- `list_plugins`
- `list_referral_types`
- `list_stage_sets`
- `list_tasks`
- `list_transactions`
- `list_webhook_event_types`
- `list_webhook_subscriptions`
- `merge_layout`
- `patch_expense`
- `patch_fee`
- `patch_file`
- `patch_folder`
- `patch_lead`
- `patch_matter`
- `patch_matter_archive`
- `protect_funds`
- `remove_contact_tags`
- `remove_layout_from_matter`
- `remove_matter_tags`
- `remove_relationship_from_role`
- `remove_role_from_matter`
- `remove_user`
- `resend_user_invitation`
- `search_staff`
- `send_portal_message`
- `subscribe_to_plugin`
- `test_webhook_subscription`
- `unarchive_matter`
- `unprotect_funds`
- `unsubscribe_from_plugin`
- `update_activity_code`
- `update_authorization_group`
- `update_authorization_policy`
- `update_contact`
- `update_contact_relation`
- `update_event`
- `update_event_reminder`
- `update_expense`
- `update_fee`
- `update_firm`
- `update_firm_user_mapping`
- `update_folder`
- `update_lead`
- `update_matter`
- `update_matter_billing_configuration`
- `update_memo`
- `update_plugin`
- `update_portal_task`
- `update_relationship`
- `update_role_on_matter`
- `update_staff_member`
- `update_subtask`
- `update_task`
- `update_webhook_subscription`

</details>

### Prompts and resources

The server also registers three prompts and three read-only resources.

| Prompt | What it does |
| --- | --- |
| `daily_briefing` | Morning briefing of open matters needing attention, overdue tasks and unbilled fees. |
| `intake_triage` | Triage a new or recently opened matter by checking its contacts, billing setup and key documents. Takes a `matter_id`. |
| `billing_summary` | Summary of a matter's fees, expenses, invoices and outstanding balances. Takes a `matter_id`. |

| Resource | What it holds |
| --- | --- |
| `smokeball://matter_types` | The matter types configured in your Smokeball firm. |
| `smokeball://activity_codes` | The billable activity codes configured in your Smokeball firm. |
| `smokeball://security-notes` | Security notes for this server, as Markdown. |

## Requirements

- Python 3.10 or later
- A Smokeball account with partner API access: a Client ID, a Client Secret and an API Key
- An MCP client such as Claude Desktop

> **Smokeball partner access:** API credentials are issued through the Smokeball partner/developer program. Contact your Smokeball account representative to request API access.

## Installation

Install [uv](https://docs.astral.sh/uv/), then clone the repository and install its locked dependencies:

```bash
git clone https://github.com/RosenAdvertising/smokeball-mcp.git
cd smokeball-mcp
uv sync --locked
```

Releases are also published to PyPI: `pip install smokeball-mcp` installs version 0.2.0, which predates the HTTP mode described below. Install from source to use HTTP mode.

## Configuration

Run the guided OAuth setup from your clone of the repository:

```bash
uv run --locked smokeball-mcp-setup
```

Setup does four things:

1. Asks for your region (US, AU or UK).
2. Asks for your Client ID, Client Secret and API Key.
3. Opens your browser for Smokeball authorization and listens for the redirect at `http://127.0.0.1:8768/callback`.
4. Saves the credentials to your operating system's keyring (or the file fallback described under [Credential storage](#credential-storage)) and the OAuth tokens to `~/.smokeball-mcp/tokens.json`.

Verify the connection:

```bash
uv run --locked smokeball-mcp-verify
```

Verify checks the stored configuration, signs in to Smokeball, and reads the firm profile and up to five matters.

The server reads these environment variables. A variable set in the process environment takes precedence over a stored value.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `SMOKEBALL_CLIENT_ID` | Yes | Stored value from setup | Smokeball OAuth client ID. |
| `SMOKEBALL_CLIENT_SECRET` | Yes | Stored value from setup | Smokeball OAuth client secret. |
| `SMOKEBALL_API_KEY` | Yes | Stored value from setup | Smokeball partner API key, sent as the `x-api-key` header. |
| `SMOKEBALL_REGION` | No | `us` | `us`, `au` or `uk`. Any other value is rejected at startup (see [Regions](#regions)). |
| `SMOKEBALL_MCP_USE_KEYRING` | No | `1` | Set to `0` (or `false`, `no`, `off`) to skip the OS keyring and use the `.env` file fallback. |
| `SMOKEBALL_ALLOWED_DESTINATION_HOSTS` | Only for webhook and plugin tools that take a URL | unset | Comma-separated hosts approved as webhook and plugin destinations (see [Approved destination URLs](#approved-destination-urls)). |

## Usage with Claude Desktop

Add the server to Claude Desktop's configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "smokeball": {
      "command": "uv",
      "args": ["run", "--locked", "--directory", "/absolute/path/to/smokeball-mcp", "smokeball-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/smokeball-mcp` with the path of your clone. Restart Claude Desktop after saving. Any other stdio MCP client uses the same command and arguments.

## HTTP mode

Stdio is the default. Set `SMOKEBALL_MCP_TRANSPORT=streamable-http` to serve the stateless Streamable HTTP transport from MCP specification 2026-07-28 at `/mcp`. Each request stands alone: no initialization handshake and no `Mcp-Session-Id`. Clients on earlier protocol versions are served on the same endpoint.

> **Security: this endpoint has no authentication and no TLS.** Anyone who can reach the port can run every tool, including write and delete tools, with this server's vendor credentials. Keep the default loopback bind (`127.0.0.1`), or put the server behind an authenticating TLS proxy on a private network. `SMOKEBALL_MCP_ALLOWED_HOSTS` and `SMOKEBALL_MCP_ALLOWED_ORIGINS` protect against browser DNS rebinding, not against direct callers. A proxy in front of it needs connection and idle timeouts: a legacy-style `GET /mcp` with `Accept: text/event-stream` holds a stream open until the client disconnects.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SMOKEBALL_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http`. A set but empty value selects `stdio`. |
| `SMOKEBALL_MCP_HOST` | `127.0.0.1` | Bind address. `127.0.0.1`, `localhost` and `::1` use the SDK's built-in Host and Origin checks; any other value requires `SMOKEBALL_MCP_ALLOWED_HOSTS`. |
| `PORT` | `8080` | Port; must be an integer. |
| `SMOKEBALL_MCP_ALLOWED_HOSTS` | unset | Comma-separated `Host` header values accepted on a non-loopback bind, such as `mcp.example.com:8080` or `mcp.example.com:*`. |
| `SMOKEBALL_MCP_ALLOWED_ORIGINS` | unset | Comma-separated `Origin` values accepted on a non-loopback bind, such as `https://client.example.com`. Requests without an `Origin` header are accepted; with this unset on a non-loopback bind, a request that carries an `Origin` header is rejected. |

Smokeball credentials come from the same configuration as stdio (see [Configuration](#configuration)), never from the request.

```bash
SMOKEBALL_MCP_TRANSPORT=streamable-http PORT=8080 uv run --locked smokeball-mcp
```

Point the MCP client at `http://127.0.0.1:8080/mcp`. Responses use the SDK's default SSE behavior, so a client disconnect cancels the request.

## Error handling

A failed tool call returns an MCP error result (`isError`) with a fixed message. The server never passes a Smokeball response body, a request URL or a credential back to the client. Failures raised while a tool runs start with `Error executing tool <name>: `.

| Situation | What the tool returns |
| --- | --- |
| Credentials or OAuth tokens missing | "Smokeball credentials are missing." or "Smokeball OAuth tokens are missing.", followed by the variables to set and the instruction to run `smokeball-mcp-setup` and restart the MCP server. |
| HTTP 401 (after one automatic token refresh) | "Smokeball authorization was rejected or expired. Re-authorize with: smokeball-mcp-setup" |
| HTTP 403 | "Smokeball access denied: the connected account lacks permission for this action (or the authorization expired; re-run smokeball-mcp-setup if so)." |
| HTTP 404 | "The requested item was not found (HTTP 404). Check the ID and try again." |
| HTTP 429 | "Smokeball rate limit exceeded (HTTP 429). Retry after N seconds." N comes from the `Retry-After` header, or is 10 when the header is missing or unusable. |
| Other HTTP error statuses | "Smokeball API request failed (HTTP 500)." followed by one fixed sentence. By default the sentence depends on the status: "The request was rejected." (400), "The request conflicts with the current item state." (409), "The request fields were rejected." (422), "The service had an internal error." (500), "The service is temporarily unavailable." (502 and 503), "The service timed out." (504), or "The request failed." for any other status. When the Smokeball response body carries a recognized error code, the sentence for that code is used instead: "The request is invalid." (`invalid_request`), "Request validation failed." (`validation_error`), "A request parameter is invalid." (`invalid_parameter`), "The request conflicts with the current item state." (`conflict`) or "The service is temporarily unavailable." (`service_unavailable`). A successful response that is not valid JSON returns "The service returned invalid JSON." |
| Timeout or connection failure on a read | "Smokeball could not be reached. Check the connection and retry." |
| Timeout or connection failure on a write | "Smokeball request outcome is unknown. Check whether it completed before retrying." |
| Webhook or plugin URL not approved | "Invalid argument target_url: expected a public HTTPS URL approved by SMOKEBALL_ALLOWED_DESTINATION_HOSTS." |
| Invalid arguments | A message that names the argument and the shape it expects, such as "Invalid arguments: matter_id must be a required string". |
| Anything else | `Error executing tool <name>` with no detail. |

Every Smokeball request has a 30-second timeout and redirects are not followed. On HTTP 401 the server refreshes the OAuth access token once and repeats the request. On HTTP 429 it waits for the `Retry-After` period (10 seconds when absent) and retries up to 3 times, as long as no single wait is over 60 seconds and the waits together stay within 60 seconds; otherwise it returns the rate-limit message. Other failures are not retried.

Missing credentials do not stop the server from starting: each tool call reports them. At startup the server exits with a message and a non-zero status when `SMOKEBALL_MCP_TRANSPORT` is neither `stdio` nor `streamable-http`, when `PORT` is not an integer, or when a non-loopback `SMOKEBALL_MCP_HOST` is set without `SMOKEBALL_MCP_ALLOWED_HOSTS`. An unsupported `SMOKEBALL_REGION` also stops the server at startup.

## Regions

| Region | API Base             |
| ------ | -------------------- |
| US     | api.smokeball.com    |
| AU     | api.smokeball.com.au |
| UK     | api.smokeball.co.uk  |

Region is set during setup and stored securely (OS keyring or `~/.smokeball-mcp/.env` fallback). `SMOKEBALL_REGION` is trimmed and lowercased before validation. It accepts only `us`, `au`, or `uk`. Setup also accepts the corresponding menu numbers. Unknown values fail; they never select US.

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

**Read order.** A credential already present in the server process environment takes precedence, including one set in your MCP client's configuration. Otherwise the server checks the OS keyring, then the `.env` file. If you change credentials after the server has loaded them, restart the MCP server to reload the new values.

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

## Approved destination URLs

Set `SMOKEBALL_ALLOWED_DESTINATION_HOSTS` in the server environment, for example
`SMOKEBALL_ALLOWED_DESTINATION_HOSTS=hooks.firm.example,.integrations.firm.example`.
Comma-separated exact hosts allow only that host; a leading dot allows the domain
and its subdomains. Matching ignores case and trailing dots and normalizes IDNA.
An empty or unset list refuses destination URLs before any request. HTTPS, no
userinfo, and public literal addresses remain required. This administrator-owned
list prevents model-supplied destinations from sending data to arbitrary hosts,
including private-address DNS aliases and unapproved redirectors. Approve only
hosts whose DNS and redirects the firm trusts; the vendor executes requests later.
Tools cannot change this setting. The list applies to the URL argument of `create_webhook_subscription`, `update_webhook_subscription`, `create_plugin` and `update_plugin`.

## Testing

The test suite runs offline and needs no Smokeball account: Smokeball API calls are replaced with test doubles, and credentials come from inert test values with the OS keyring disabled. It covers the error messages tools return, argument validation, path identifier handling, the OAuth setup callback and credential storage including private file permissions, the webhook and plugin destination allowlist, the setup and verify command help, MCP specification 2026-07-28 behavior, and the Streamable HTTP transport including Host and Origin checks and stateless requests.

```bash
uv sync --locked
uv run --locked pytest -q
```

CI runs the suite on every push and pull request to `main`.

## License

MIT. See [LICENSE](LICENSE).
