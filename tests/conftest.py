"""Keep offline tests isolated from user credential stores."""

import os

os.environ.setdefault("SMOKEBALL_MCP_USE_KEYRING", "0")
os.environ.setdefault("SMOKEBALL_CLIENT_ID", "offline-test-client")
os.environ.setdefault("SMOKEBALL_CLIENT_SECRET", "offline-test-secret")
os.environ.setdefault("SMOKEBALL_API_KEY", "offline-test-api-key")
os.environ.setdefault("SMOKEBALL_REGION", "us")
