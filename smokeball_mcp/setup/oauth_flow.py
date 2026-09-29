#!/usr/bin/env python3
"""One-command OAuth setup for smokeball-mcp.
Opens the browser, captures the callback, exchanges the code, saves tokens.

Credentials (Client ID, Client Secret, API Key, Region) are stored securely via
the OS keyring (macOS Keychain / Windows Credential Manager / Linux Secret
Service), falling back to a 0600 ``.env`` file when no keyring backend is
available or ``SMOKEBALL_MCP_USE_KEYRING=0`` is set.
"""

import getpass
import hmac
import logging
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from smokeball_mcp import credentials

logger = logging.getLogger(__name__)

REDIRECT_URI = "http://127.0.0.1:8768/callback"
CONFIG_DIR = Path.home() / ".smokeball-mcp"

REGIONS = {
    "us": {
        "api": "https://api.smokeball.com",
        "auth": "https://auth.smokeball.com",
    },
    "au": {
        "api": "https://api.smokeball.com.au",
        "auth": "https://auth.smokeball.com.au",
    },
    "uk": {
        "api": "https://api.smokeball.co.uk",
        "auth": "https://auth.smokeball.co.uk",
    },
}

_auth_code: str | None = None
_oauth_state: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def _send_page(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global _auth_code, _oauth_state
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            logger.warning("oauth_callback_rejected reason=unexpected_path")
            self._send_page(404, b"<h2>Callback not found.</h2>")
            return
        params = parse_qs(parsed.query)
        supplied_state = params.get("state", [""])[0]
        if (
            not _oauth_state
            or not supplied_state
            or not hmac.compare_digest(supplied_state, _oauth_state)
        ):
            logger.warning("oauth_callback_rejected reason=state_mismatch")
            self._send_page(400, b"<h2>Authorization could not be verified.</h2>")
            return
        codes = params.get("code", [])
        if len(codes) != 1 or not codes[0]:
            logger.warning("oauth_callback_rejected reason=missing_code")
            self._send_page(400, b"<h2>No authorization code received.</h2>")
            return
        _auth_code = codes[0]
        _oauth_state = None
        self._send_page(
            200, b"<h2>Authorization complete. You can close this tab.</h2>"
        )

    def log_message(self, *args):
        pass


def main():
    global _auth_code, _oauth_state
    _auth_code = None
    _oauth_state = secrets.token_urlsafe(32)

    print("=== smokeball-mcp OAuth Setup ===\n")

    print("Select your Smokeball region:")
    print("  1. US (api.smokeball.com)")
    print("  2. AU (api.smokeball.com.au)")
    print("  3. UK (api.smokeball.co.uk)")
    try:
        region_choice = input("\nRegion [1/2/3, default=1]: ").strip() or "1"
        client_id = input("\nSmokeball Client ID: ").strip()
        client_secret = getpass.getpass("Smokeball Client Secret: ").strip()
        api_key = getpass.getpass("Smokeball API Key (x-api-key): ").strip()
    except (EOFError, KeyboardInterrupt):
        print(
            "Setup cancelled: all three credentials are required. Run smokeball-mcp-setup again."
        )
        raise SystemExit(1) from None
    region_map = {"1": "us", "2": "au", "3": "uk"}
    region = region_map.get(region_choice, "us")
    region_cfg = REGIONS[region]

    auth_base = region_cfg["auth"]
    token_url = f"{auth_base}/connect/token"
    authorize_url = f"{auth_base}/connect/authorize"

    print(f"\nUsing region: {region.upper()} ({region_cfg['api']})")

    if not client_id or not client_secret or not api_key:
        print(
            "Error: SMOKEBALL_CLIENT_ID, SMOKEBALL_CLIENT_SECRET, and SMOKEBALL_API_KEY are all required. Run smokeball-mcp-setup again."
        )
        sys.exit(1)

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid offline_access",
        "state": _oauth_state,
    }
    auth_url = f"{authorize_url}?{urlencode(auth_params)}"

    print("\nOpening browser for Smokeball authorization...")
    if not webbrowser.open(auth_url):
        logger.warning("oauth_setup_rejected reason=browser_open_failed")
        print("Error: Could not open a browser for authorization.")
        sys.exit(1)

    server = HTTPServer(("127.0.0.1", 8768), _CallbackHandler)
    print("Waiting for Smokeball to redirect back (port 8768)...")
    server.handle_request()

    if not _auth_code:
        print("Error: Did not receive authorization code.")
        sys.exit(1)

    print("Exchanging code for tokens...")
    try:
        resp = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": _auth_code,
                "redirect_uri": REDIRECT_URI,
            },
            timeout=30,
        )
    except requests.RequestException:
        logger.warning("oauth_code_exchange_rejected reason=transport_error")
        print(
            "Token exchange outcome is unknown. Check whether authorization completed before retrying setup."
        )
        sys.exit(1)

    if resp.status_code == 403:
        print(
            "Smokeball access denied: the connected account lacks permission for this action "
            "(or the authorization expired; re-run smokeball-mcp-setup if so)."
        )
        sys.exit(1)
    if resp.status_code != 200:
        logger.warning(
            "oauth_code_exchange_rejected reason=upstream_status status=%s",
            resp.status_code,
        )
        print(f"Token exchange failed ({resp.status_code}).")
        sys.exit(1)

    try:
        tokens = resp.json()
    except ValueError:
        logger.warning("oauth_code_exchange_rejected reason=non_json")
        print("Token exchange failed (invalid response).")
        sys.exit(1)

    backend = credentials.set_secret("SMOKEBALL_CLIENT_ID", client_id)
    credentials.set_secret("SMOKEBALL_CLIENT_SECRET", client_secret)
    credentials.set_secret("SMOKEBALL_API_KEY", api_key)
    credentials.set_secret("SMOKEBALL_REGION", region)

    token_file = CONFIG_DIR / "tokens.json"
    credentials.atomic_private_json(token_file, tokens)

    if backend == "keyring":
        print(
            f"\n✓ Credentials saved to the OS keyring ({credentials.storage_backend()})."
        )
    else:
        print(f"\n✓ Credentials saved to {credentials.ENV_FILE} (0600).")
    print(f"✓ Tokens saved to {token_file}")
    print(
        "\nRun 'smokeball-mcp-verify' to test the connection, then restart the MCP server to load the new credentials."
    )


if __name__ == "__main__":
    main()
