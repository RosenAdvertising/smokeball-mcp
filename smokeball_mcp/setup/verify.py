#!/usr/bin/env python3
"""Post-setup smoke test — verifies auth and basic Smokeball API access."""

import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".smokeball-mcp"


def check_config():
    env_file = CONFIG_DIR / ".env"
    token_file = CONFIG_DIR / "tokens.json"

    if not env_file.exists():
        print(f"✗ Missing credentials: {env_file}")
        print("  Run: smokeball-mcp-setup")
        return False

    if not token_file.exists():
        print(f"✗ Missing tokens: {token_file}")
        print("  Run: smokeball-mcp-setup")
        return False

    print(f"✓ Config found: {CONFIG_DIR}")
    return True


def check_api():
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from smokeball_mcp.client import SmokeBallClient

        client = SmokeBallClient()

        firm = client.get_firm()
        name = firm.get("name") or firm.get("firmName") or "unknown"
        print(f"✓ Authenticated — firm: {name}")

        matters = client.list_matters(limit=5)
        items = matters.get("value", matters) if isinstance(matters, dict) else matters
        count = len(items) if isinstance(items, list) else 0
        print(f"✓ Matters accessible: {count} returned (limit 5)")

        return True
    except Exception as e:
        print(f"✗ API check failed: {e}")
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
