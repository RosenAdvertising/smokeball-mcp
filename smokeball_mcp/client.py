#!/usr/bin/env python3
"""Smokeball API client. OAuth 2.0 auth code flow, x-api-key + Bearer headers, offset pagination."""

import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

# Region-specific base URLs
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

CONFIG_DIR = Path.home() / ".smokeball-mcp"
REDIRECT_URI = "http://127.0.0.1:8768/callback"


def _load_env():
    env_file = CONFIG_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


_load_env()

CLIENT_ID = os.environ.get("SMOKEBALL_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("SMOKEBALL_CLIENT_SECRET", "")
API_KEY = os.environ.get("SMOKEBALL_API_KEY", "")
REGION = os.environ.get("SMOKEBALL_REGION", "us").lower()

_region_cfg = REGIONS.get(REGION, REGIONS["us"])
BASE_URL = _region_cfg["api"]
AUTH_BASE = _region_cfg["auth"]
TOKEN_URL = f"{AUTH_BASE}/connect/token"
AUTH_URL = f"{AUTH_BASE}/connect/authorize"


def _retry_after_seconds(resp, default=10):
    try:
        return int(resp.headers.get("Retry-After", default))
    except (TypeError, ValueError):
        return default


def _json_response(resp):
    try:
        return resp.json()
    except ValueError:
        raise RuntimeError(
            f"Smokeball API returned non-JSON response ({resp.status_code}): "
            f"{resp.text[:200]}"
        )


class TokenManager:
    def __init__(self):
        self.token_file = CONFIG_DIR / "tokens.json"
        self.tokens = self._load()

    def _load(self):
        if self.token_file.exists():
            with open(self.token_file) as f:
                return json.load(f)
        return {}

    def save(self, tokens):
        self.tokens = tokens
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, "w") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.token_file, 0o600)

    @property
    def access_token(self):
        return self.tokens.get("access_token", "")

    @property
    def refresh_token(self):
        return self.tokens.get("refresh_token", "")

    def refresh(self):
        if not self.refresh_token:
            raise RuntimeError("No refresh token. Run: smokeball-mcp-setup")
        if not CLIENT_ID or not CLIENT_SECRET:
            raise RuntimeError("SMOKEBALL_CLIENT_ID and SMOKEBALL_CLIENT_SECRET are required. Run: smokeball-mcp-setup")
        resp = requests.post(TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        })
        if resp.status_code == 200:
            new_tokens = _json_response(resp)
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = self.refresh_token
            new_tokens["refreshed_at"] = datetime.now(timezone.utc).isoformat()
            self.save(new_tokens)
            return new_tokens
        raise RuntimeError(f"Token refresh failed ({resp.status_code}): {resp.text}")


class SmokeBallClient:
    def __init__(self):
        if not API_KEY:
            raise RuntimeError("SMOKEBALL_API_KEY is required. Run: smokeball-mcp-setup")
        self.tm = TokenManager()
        if not self.tm.access_token and not self.tm.refresh_token:
            raise RuntimeError("No Smokeball OAuth tokens found. Run: smokeball-mcp-setup")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.tm.access_token}",
            "x-api-key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(self, method, path, params=None, json_body=None, retry=True, _rate_retries=0):
        url = f"{BASE_URL}/{path.lstrip('/')}"
        resp = self.session.request(method, url, params=params, json=json_body)

        if resp.status_code == 401 and retry:
            self.tm.refresh()
            self.session.headers["Authorization"] = f"Bearer {self.tm.access_token}"
            return self._request(method, path, params=params, json_body=json_body, retry=False)

        if resp.status_code == 429 and _rate_retries < 3:
            wait = _retry_after_seconds(resp)
            print(f"Rate limited. Waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
            return self._request(method, path, params=params, json_body=json_body,
                                  retry=retry, _rate_retries=_rate_retries + 1)

        if resp.status_code == 204:
            return {}

        if not resp.ok:
            raise RuntimeError(f"Smokeball API error {resp.status_code}: {resp.text[:400]}")

        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None):
        return self._request("POST", path, json_body=body)

    def put(self, path, body=None):
        return self._request("PUT", path, json_body=body)

    def patch(self, path, body=None):
        return self._request("PATCH", path, json_body=body)

    def delete(self, path):
        return self._request("DELETE", path)

    # ── Firm ──────────────────────────────────────────────────────────────────

    def get_firm(self):
        return self.get("/firm")

    def update_firm(self, **fields):
        return self.put("/firm", fields)

    def get_firm_user_mappings(self):
        return self.get("/firm/usermappings")

    def get_firm_user_mapping(self, mapping_id):
        return self.get(f"/firm/usermappings/{mapping_id}")

    def update_firm_user_mapping(self, mapping_id, **fields):
        return self.put(f"/firm/usermappings/{mapping_id}", fields)

    def delete_firm_user_mapping(self, mapping_id):
        return self.delete(f"/firm/usermappings/{mapping_id}")

    # ── Staff ─────────────────────────────────────────────────────────────────

    def search_staff(self, query=None, limit=50, offset=0):
        params = {"limit": limit, "offset": offset}
        if query:
            params["query"] = query
        return self.get("/staff", params)

    def get_staff_member(self, staff_id):
        return self.get(f"/staff/{staff_id}")

    def create_staff_member(self, **fields):
        return self.post("/staff", fields)

    def update_staff_member(self, staff_id, **fields):
        return self.put(f"/staff/{staff_id}", fields)

    def delete_staff_member(self, staff_id):
        return self.delete(f"/staff/{staff_id}")

    # ── Users ─────────────────────────────────────────────────────────────────

    def get_user(self, user_id):
        return self.get(f"/users/{user_id}")

    def create_user(self, **fields):
        return self.post("/users", fields)

    def remove_user(self, user_id):
        return self.delete(f"/users/{user_id}")

    def resend_user_invitation(self, user_id):
        return self.post(f"/users/{user_id}/resend-invitation")

    # ── Contacts ──────────────────────────────────────────────────────────────

    def list_contacts(self, limit=50, offset=0):
        return self.get("/contacts", {"limit": limit, "offset": offset})

    def get_contact(self, contact_id):
        return self.get(f"/contacts/{contact_id}")

    def create_contact(self, contact_type: str = "person", first_name: str = "",
                       last_name: str = "", company_name: str = "",
                       email: str = "", phone: str = ""):
        if contact_type.lower() == "company":
            inner = {}
            if company_name:
                inner["name"] = company_name
            if email:
                inner["email"] = email
            if phone:
                inner["phone"] = phone
            body = {"company": inner}
        else:
            inner = {}
            if first_name:
                inner["firstName"] = first_name
            if last_name:
                inner["lastName"] = last_name
            if email:
                inner["email"] = email
            if phone:
                inner["phone"] = phone
            body = {"person": inner}
        return self.post("/contacts", body)

    def update_contact(self, contact_id, **fields):
        return self.put(f"/contacts/{contact_id}", fields)

    def delete_contact(self, contact_id):
        return self.delete(f"/contacts/{contact_id}")

    def get_contact_relations(self, contact_id):
        return self.get(f"/contacts/{contact_id}/relations")

    def get_contact_relation(self, contact_id, relation_id):
        return self.get(f"/contacts/{contact_id}/relations/{relation_id}")

    def create_contact_relation(self, contact_id, **fields):
        return self.post(f"/contacts/{contact_id}/relations", fields)

    def update_contact_relation(self, contact_id, relation_id, **fields):
        return self.put(f"/contacts/{contact_id}/relations/{relation_id}", fields)

    def delete_contact_relation(self, contact_id, relation_id):
        return self.delete(f"/contacts/{contact_id}/relations/{relation_id}")

    def get_contact_tags(self, contact_id):
        return self.get(f"/contacts/{contact_id}/tags")

    def add_contact_tags(self, contact_id, tags: list):
        return self.post(f"/contacts/{contact_id}/tags", tags)

    def remove_contact_tags(self, contact_id, tag_id: str):
        return self.delete(f"/contacts/{contact_id}/tags/{tag_id}")

    # ── Matters ───────────────────────────────────────────────────────────────

    def list_matters(self, limit=50, offset=0):
        return self.get("/matters", {"limit": limit, "offset": offset})

    def get_matter(self, matter_id):
        return self.get(f"/matters/{matter_id}")

    def create_matter(self, number: str = "", matter_type_id: str = "",
                      client_ids: list = None, description: str = "",
                      status: str = ""):
        body = {}
        if number:
            body["number"] = number
        if matter_type_id:
            body["matterTypeId"] = matter_type_id
        if client_ids:
            body["clientIds"] = client_ids
        if description:
            body["description"] = description
        if status:
            body["status"] = status
        return self.post("/matters", body)

    def update_matter(self, matter_id, **fields):
        return self.put(f"/matters/{matter_id}", fields)

    def patch_matter(self, matter_id, **fields):
        return self.patch(f"/matters/{matter_id}", fields)

    def delete_matter(self, matter_id):
        return self.delete(f"/matters/{matter_id}")

    def get_matter_billing_configuration(self, matter_id):
        return self.get(f"/matters/{matter_id}/billingconfiguration")

    def update_matter_billing_configuration(self, matter_id, **fields):
        return self.put(f"/matters/{matter_id}/billingconfiguration", fields)

    def get_matter_tags(self, matter_id):
        return self.get(f"/matters/{matter_id}/tags")

    def add_matter_tags(self, matter_id, tags: list):
        return self.post(f"/matters/{matter_id}/tags", tags)

    def remove_matter_tags(self, matter_id, tag_id: str):
        return self.delete(f"/matters/{matter_id}/tags/{tag_id}")

    # ── Leads ─────────────────────────────────────────────────────────────────

    def list_leads(self, limit=50, offset=0):
        return self.get("/leads", {"limit": limit, "offset": offset})

    def get_lead(self, lead_id):
        return self.get(f"/leads/{lead_id}")

    def create_lead(self, matter_type_id: str = "", client_id: str = ""):
        body = {"isLead": True}
        if matter_type_id:
            body["matterTypeId"] = matter_type_id
        if client_id:
            body["clientIds"] = [client_id]
        return self.post("/matters", body)

    def update_lead(self, lead_id, **fields):
        return self.put(f"/leads/{lead_id}", fields)

    def patch_lead(self, lead_id, **fields):
        return self.patch(f"/leads/{lead_id}", fields)

    def delete_lead(self, lead_id):
        return self.delete(f"/leads/{lead_id}")

    # ── Matter Types ──────────────────────────────────────────────────────────

    def list_matter_types(self, limit=100, offset=0):
        return self.get("/mattertypes", {"limit": limit, "offset": offset})

    def get_matter_type(self, matter_type_id):
        return self.get(f"/mattertypes/{matter_type_id}")

    def list_matter_type_categories(self):
        return self.get("/mattertypes/categories")

    # ── Stages ────────────────────────────────────────────────────────────────

    def list_stage_sets(self):
        return self.get("/stages")

    def get_stage_set(self, stage_set_id):
        return self.get(f"/stages/{stage_set_id}")

    def get_stage_in_set(self, stage_set_id, stage_id):
        return self.get(f"/stages/{stage_set_id}/stages/{stage_id}")

    def list_matter_stage_mappings(self):
        return self.get("/stages/matterstagesmapping")

    def get_matter_stage(self, matter_id):
        return self.get(f"/matters/{matter_id}/stage")

    # ── Roles ─────────────────────────────────────────────────────────────────

    def get_roles_on_matter(self, matter_id):
        return self.get(f"/matters/{matter_id}/roles")

    def get_role_on_matter(self, matter_id, role_id):
        return self.get(f"/matters/{matter_id}/roles/{role_id}")

    def add_role_to_matter(self, matter_id, **fields):
        return self.post(f"/matters/{matter_id}/roles", fields)

    def update_role_on_matter(self, matter_id, role_id, **fields):
        return self.put(f"/matters/{matter_id}/roles/{role_id}", fields)

    def remove_role_from_matter(self, matter_id, role_id):
        return self.delete(f"/matters/{matter_id}/roles/{role_id}")

    # ── Relationships ─────────────────────────────────────────────────────────

    def get_relationships_on_matter(self, matter_id):
        return self.get(f"/matters/{matter_id}/relationships")

    def get_relationship_on_role(self, matter_id, role_id):
        return self.get(f"/matters/{matter_id}/roles/{role_id}/relationships")

    def add_relationship_to_role(self, matter_id, role_id, **fields):
        return self.post(f"/matters/{matter_id}/roles/{role_id}/relationships", fields)

    def update_relationship(self, matter_id, role_id, relationship_id, **fields):
        return self.put(f"/matters/{matter_id}/roles/{role_id}/relationships/{relationship_id}", fields)

    def remove_relationship_from_role(self, matter_id, role_id, relationship_id):
        return self.delete(f"/matters/{matter_id}/roles/{role_id}/relationships/{relationship_id}")

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def get_tasks(self, matter_id=None, limit=50, offset=0):
        params = {"limit": limit, "offset": offset}
        if matter_id:
            params["matterId"] = matter_id
        return self.get("/tasks", params)

    def get_task(self, task_id):
        return self.get(f"/tasks/{task_id}")

    def create_task(self, **fields):
        return self.post("/tasks", fields)

    def update_task(self, task_id, **fields):
        return self.put(f"/tasks/{task_id}", fields)

    def delete_task(self, task_id):
        return self.delete(f"/tasks/{task_id}")

    def get_subtasks(self, task_id):
        return self.get(f"/tasks/{task_id}/subtasks")

    def get_subtask(self, task_id, subtask_id):
        return self.get(f"/tasks/{task_id}/subtasks/{subtask_id}")

    def create_subtask(self, task_id, **fields):
        return self.post(f"/tasks/{task_id}/subtasks", fields)

    def update_subtask(self, task_id, subtask_id, **fields):
        return self.put(f"/tasks/{task_id}/subtasks/{subtask_id}", fields)

    def delete_subtask(self, task_id, subtask_id):
        return self.delete(f"/tasks/{task_id}/subtasks/{subtask_id}")

    def get_task_documents(self, task_id):
        return self.get(f"/tasks/{task_id}/documents")

    def get_task_document(self, task_id, document_id):
        return self.get(f"/tasks/{task_id}/documents/{document_id}")

    def create_task_document(self, task_id, **fields):
        return self.post(f"/tasks/{task_id}/documents", fields)

    def delete_task_document(self, task_id, document_id):
        return self.delete(f"/tasks/{task_id}/documents/{document_id}")

    # ── Events ────────────────────────────────────────────────────────────────

    def get_events(self, matter_id=None, limit=50, offset=0):
        params = {"limit": limit, "offset": offset}
        if matter_id:
            params["matterId"] = matter_id
        return self.get("/events", params)

    def get_event(self, event_id):
        return self.get(f"/events/{event_id}")

    def create_event(self, **fields):
        return self.post("/events", fields)

    def update_event(self, event_id, **fields):
        return self.put(f"/events/{event_id}", fields)

    def delete_event(self, event_id):
        return self.delete(f"/events/{event_id}")

    def get_event_reminders(self, event_id):
        return self.get(f"/events/{event_id}/reminders")

    def create_event_reminder(self, event_id, **fields):
        return self.post(f"/events/{event_id}/reminders", fields)

    def update_event_reminder(self, event_id, reminder_id, **fields):
        return self.put(f"/events/{event_id}/reminders/{reminder_id}", fields)

    def delete_event_reminder(self, event_id, reminder_id):
        return self.delete(f"/events/{event_id}/reminders/{reminder_id}")

    # ── Memos ─────────────────────────────────────────────────────────────────

    def get_memos_on_matter(self, matter_id, limit=50, offset=0):
        return self.get(f"/matters/{matter_id}/memos", {"limit": limit, "offset": offset})

    def get_memo(self, memo_id):
        return self.get(f"/memos/{memo_id}")

    def create_memo(self, matter_id, **fields):
        return self.post(f"/matters/{matter_id}/memos", fields)

    def update_memo(self, memo_id, **fields):
        return self.put(f"/memos/{memo_id}", fields)

    def delete_memo(self, memo_id):
        return self.delete(f"/memos/{memo_id}")

    # ── Fees ──────────────────────────────────────────────────────────────────

    def get_fees(self, matter_id=None, limit=50, offset=0):
        params = {"limit": limit, "offset": offset}
        if matter_id:
            params["matterId"] = matter_id
        return self.get("/fees", params)

    def get_fee(self, fee_id):
        return self.get(f"/fees/{fee_id}")

    def create_fee(self, **fields):
        return self.post("/fees", fields)

    def update_fee(self, fee_id, **fields):
        return self.put(f"/fees/{fee_id}", fields)

    def patch_fee(self, fee_id, **fields):
        return self.patch(f"/fees/{fee_id}", fields)

    def delete_fee(self, fee_id):
        return self.delete(f"/fees/{fee_id}")

    # ── Expenses ──────────────────────────────────────────────────────────────

    def get_expenses(self, matter_id=None, limit=50, offset=0):
        params = {"limit": limit, "offset": offset}
        if matter_id:
            params["matterId"] = matter_id
        return self.get("/expenses", params)

    def get_expense(self, expense_id):
        return self.get(f"/expenses/{expense_id}")

    def create_expense(self, **fields):
        return self.post("/expenses", fields)

    def update_expense(self, expense_id, **fields):
        return self.put(f"/expenses/{expense_id}", fields)

    def patch_expense(self, expense_id, **fields):
        return self.patch(f"/expenses/{expense_id}", fields)

    def delete_expense(self, expense_id):
        return self.delete(f"/expenses/{expense_id}")

    # ── Invoices ──────────────────────────────────────────────────────────────

    def get_invoices(self, matter_id=None, limit=50, offset=0):
        params = {"limit": limit, "offset": offset}
        if matter_id:
            params["matterId"] = matter_id
        return self.get("/invoices", params)

    def get_invoice(self, invoice_id):
        return self.get(f"/invoices/{invoice_id}")

    def get_invoice_download_url(self, invoice_id):
        return self.get(f"/invoices/{invoice_id}/downloadurl")

    # ── Activity Codes ────────────────────────────────────────────────────────

    def get_activity_codes(self, limit=100, offset=0):
        return self.get("/activitycodes", {"limit": limit, "offset": offset})

    def get_activity_code(self, code_id):
        return self.get(f"/activitycodes/{code_id}")

    def create_activity_code(self, **fields):
        return self.post("/activitycodes", fields)

    def update_activity_code(self, code_id, **fields):
        return self.put(f"/activitycodes/{code_id}", fields)

    def delete_activity_code(self, code_id):
        return self.delete(f"/activitycodes/{code_id}")

    # ── Bank Accounts ─────────────────────────────────────────────────────────

    def get_bank_accounts(self, limit=50, offset=0):
        return self.get("/bankaccounts", {"limit": limit, "offset": offset})

    def get_bank_account(self, account_id):
        return self.get(f"/bankaccounts/{account_id}")

    def get_bank_account_matter_balances(self, account_id):
        return self.get(f"/bankaccounts/{account_id}/matterbalances")

    def get_protected_bank_account_balance(self, account_id):
        return self.get(f"/bankaccounts/{account_id}/protectedbalance")

    def get_transactions(self, account_id, limit=50, offset=0):
        return self.get(f"/bankaccounts/{account_id}/transactions",
                        {"limit": limit, "offset": offset})

    def get_transaction(self, account_id, transaction_id):
        return self.get(f"/bankaccounts/{account_id}/transactions/{transaction_id}")

    def create_transaction(self, account_id, **fields):
        return self.post(f"/bankaccounts/{account_id}/transactions", fields)

    def create_requisition(self, account_id, **fields):
        return self.post(f"/bankaccounts/{account_id}/requisitions", fields)

    def protect_funds(self, account_id, **fields):
        return self.post(f"/bankaccounts/{account_id}/protect", fields)

    def unprotect_funds(self, account_id, **fields):
        return self.post(f"/bankaccounts/{account_id}/unprotect", fields)

    # ── Files ─────────────────────────────────────────────────────────────────

    def get_files_on_matter(self, matter_id, limit=50, offset=0):
        return self.get(f"/matters/{matter_id}/files",
                        {"limit": limit, "offset": offset})

    def get_file(self, file_id):
        return self.get(f"/files/{file_id}")

    def get_file_download_url(self, file_id):
        return self.get(f"/files/{file_id}/downloadurl")

    def get_file_upload_url(self, file_id):
        return self.get(f"/files/{file_id}/uploadurl")

    def get_file_history(self, matter_id, limit=50, offset=0):
        return self.get(f"/matters/{matter_id}/files/history",
                        {"limit": limit, "offset": offset})

    def add_file_to_matter(self, matter_id, **fields):
        return self.post(f"/matters/{matter_id}/files", fields)

    def add_files_to_matter(self, matter_id, files: list):
        return self.post(f"/matters/{matter_id}/files/batch", {"files": files})

    def patch_file(self, file_id, **fields):
        return self.patch(f"/files/{file_id}", fields)

    def delete_file(self, file_id):
        return self.delete(f"/files/{file_id}")

    def create_preview_request(self, file_id):
        return self.post(f"/files/{file_id}/preview")

    def get_preview_info(self, file_id):
        return self.get(f"/files/{file_id}/preview")

    def get_preview_info_by_version(self, file_id, version_id):
        return self.get(f"/files/{file_id}/versions/{version_id}/preview")

    # ── Folders ───────────────────────────────────────────────────────────────

    def get_root_folder_contents(self, matter_id):
        return self.get(f"/matters/{matter_id}/folders")

    def get_folder_contents(self, matter_id, folder_id):
        return self.get(f"/matters/{matter_id}/folders/{folder_id}")

    def get_folder_path_hierarchy(self, matter_id, folder_id):
        return self.get(f"/matters/{matter_id}/folders/{folder_id}/path")

    def get_folder_history(self, matter_id, limit=50, offset=0):
        return self.get(f"/matters/{matter_id}/folders/history",
                        {"limit": limit, "offset": offset})

    def create_folder(self, matter_id, **fields):
        return self.post(f"/matters/{matter_id}/folders", fields)

    def update_folder(self, folder_id, **fields):
        return self.put(f"/folders/{folder_id}", fields)

    def patch_folder(self, folder_id, **fields):
        return self.patch(f"/folders/{folder_id}", fields)

    def delete_folder(self, folder_id):
        return self.delete(f"/folders/{folder_id}")

    # ── Archive ───────────────────────────────────────────────────────────────

    def get_matter_archive(self, matter_id):
        return self.get(f"/matters/{matter_id}/archive")

    def update_matter_archive(self, matter_id, **fields):
        return self.put(f"/matters/{matter_id}/archive", fields)

    def patch_matter_archive(self, matter_id, **fields):
        return self.patch(f"/matters/{matter_id}/archive", fields)

    # ── Referral Types ────────────────────────────────────────────────────────

    def get_referral_types(self, limit=100, offset=0):
        return self.get("/referraltypes", {"limit": limit, "offset": offset})

    def get_referral_type(self, referral_type_id):
        return self.get(f"/referraltypes/{referral_type_id}")

    # ── Authorization ─────────────────────────────────────────────────────────

    def get_authorization_groups(self):
        return self.get("/authorization/groups")

    def get_authorization_group(self, group_id):
        return self.get(f"/authorization/groups/{group_id}")

    def create_authorization_group(self, **fields):
        return self.post("/authorization/groups", fields)

    def update_authorization_group(self, group_id, **fields):
        return self.put(f"/authorization/groups/{group_id}", fields)

    def delete_authorization_group(self, group_id):
        return self.delete(f"/authorization/groups/{group_id}")

    def get_authorization_policy(self, reference):
        return self.get(f"/policies/{reference}")

    def create_authorization_policy(self, **fields):
        return self.post("/policies", fields)

    def update_authorization_policy(self, reference, **fields):
        return self.put(f"/policies/{reference}", fields)

    # ── Notifications ─────────────────────────────────────────────────────────

    def get_notification(self, notification_id):
        return self.get(f"/notifications/{notification_id}")

    def create_notification(self, **fields):
        return self.post("/notifications", fields)

    # ── Plugins ───────────────────────────────────────────────────────────────

    def get_plugins(self):
        return self.get("/plugins")

    def get_plugin(self, plugin_id):
        return self.get(f"/plugins/{plugin_id}")

    def create_plugin(self, **fields):
        return self.post("/plugins", fields)

    def update_plugin(self, plugin_id, **fields):
        return self.put(f"/plugins/{plugin_id}", fields)

    def delete_plugin(self, plugin_id):
        return self.delete(f"/plugins/{plugin_id}")

    def get_plugin_subscriptions(self):
        return self.get("/plugins/subscriptions")

    def get_plugin_subscription(self, subscription_id):
        return self.get(f"/plugins/subscriptions/{subscription_id}")

    def subscribe_to_plugin(self, plugin_id):
        return self.post(f"/plugins/{plugin_id}/subscribe")

    def unsubscribe_from_plugin(self, plugin_id):
        return self.delete(f"/plugins/{plugin_id}/subscribe")

    def request_plugin_url(self, plugin_id):
        return self.get(f"/plugins/{plugin_id}/url")

    # ── Portal ────────────────────────────────────────────────────────────────

    def create_portal_task(self, **fields):
        return self.post("/portal/tasks", fields)

    def patch_portal_task(self, task_id, **fields):
        return self.patch(f"/portal/tasks/{task_id}", fields)

    def send_portal_message(self, **fields):
        return self.post("/portal/messages", fields)

    # ── Layout Designs ────────────────────────────────────────────────────────

    def get_layout_designs(self):
        return self.get("/layoutdesigns")

    def get_layout_design(self, design_id):
        return self.get(f"/layoutdesigns/{design_id}")

    # ── Layout Matter Items ────────────────────────────────────────────────────

    def get_layouts_on_matter(self, matter_id):
        return self.get(f"/matters/{matter_id}/layouts")

    def get_layout_on_matter(self, matter_id, layout_id):
        return self.get(f"/matters/{matter_id}/layouts/{layout_id}")

    def add_layout_to_matter(self, matter_id, **fields):
        return self.post(f"/matters/{matter_id}/layouts", fields)

    def add_contact_to_layout(self, matter_id, layout_id, **fields):
        return self.post(f"/matters/{matter_id}/layouts/{layout_id}/contacts", fields)

    def get_layout_contacts(self, matter_id, layout_id):
        return self.get(f"/matters/{matter_id}/layouts/{layout_id}/contacts")

    def merge_layout(self, matter_id, layout_id):
        return self.post(f"/matters/{matter_id}/layouts/{layout_id}/merge")

    def remove_layout_from_matter(self, matter_id, layout_id):
        return self.delete(f"/matters/{matter_id}/layouts/{layout_id}")

    # ── Matter Items ──────────────────────────────────────────────────────────

    def get_items_on_matter(self, matter_id):
        return self.get(f"/matters/{matter_id}/items")

    def get_item_on_matter(self, matter_id, item_id):
        return self.get(f"/matters/{matter_id}/items/{item_id}")

    # ── Integrated Search ─────────────────────────────────────────────────────

    def get_integrated_search_mapping(self):
        return self.get("/search/mapping")

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def get_webhook_subscriptions(self):
        return self.get("/webhooks/subscriptions")

    def get_webhook_subscription(self, subscription_id):
        return self.get(f"/webhooks/subscriptions/{subscription_id}")

    def create_webhook_subscription(self, event_type, url, **fields):
        body = {"eventType": event_type, "url": url, **fields}
        return self.post("/webhooks/subscriptions", body)

    def update_webhook_subscription(self, subscription_id, **fields):
        return self.put(f"/webhooks/subscriptions/{subscription_id}", fields)

    def delete_webhook_subscription(self, subscription_id):
        return self.delete(f"/webhooks/subscriptions/{subscription_id}")

    def get_webhook_event_types(self):
        return self.get("/webhooks/eventtypes")

    def notify_webhook_subscription(self, subscription_id):
        return self.post(f"/webhooks/subscriptions/{subscription_id}/notify")
