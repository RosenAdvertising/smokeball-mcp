#!/usr/bin/env python3
"""Post-setup smoke test — verifies auth and basic Smokeball API access."""

import sys
from pathlib import Path

from smokeball_mcp import credentials

CONFIG_DIR = Path.home() / ".smokeball-mcp"


def check_config():
    token_file = CONFIG_DIR / "tokens.json"

    required = ("SMOKEBALL_CLIENT_ID", "SMOKEBALL_CLIENT_SECRET", "SMOKEBALL_API_KEY")
    if any(not credentials.get_secret(key) for key in required):
        print("✗ Missing credential configuration.")
        print("  Run: smokeball-mcp-setup")
        return False

    if not token_file.exists():
        print("✗ Missing OAuth tokens.")
        print("  Run: smokeball-mcp-setup")
        return False

    print("✓ Credential configuration found.")
    return True


def check_api():
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from smokeball_mcp.client import SmokeBallClient
        from smokeball_mcp.server import _classify_tool_exception

        client = SmokeBallClient()

        client.get_firm()
        print("✓ Authenticated to Smokeball.")

        matters = client.list_matters(limit=5)
        items = matters.get("value", matters) if isinstance(matters, dict) else matters
        count = len(items) if isinstance(items, list) else 0
        print(f"✓ Matters accessible: {count} returned (limit 5)")

        return True
    except Exception as exc:
        message = (
            _classify_tool_exception(exc)
            if "_classify_tool_exception" in locals()
            else None
        )
        if message:
            print(f"✗ API check failed: {message}")
            return False
        print("✗ API check failed.")
        return False


def main():
    print("=== smokeball-mcp Verification ===\n")
    ok = check_config() and check_api()
    if ok:
        print("\n✓ All checks passed. smokeball-mcp is ready.")
    else:
        print("\n✗ Setup incomplete. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
