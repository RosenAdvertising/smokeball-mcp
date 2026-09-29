#!/usr/bin/env python3
"""Smokeball API client. OAuth 2.0 auth code flow, x-api-key + Bearer headers, offset pagination."""

import ipaddress
import json
import logging
import math
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

from smokeball_mcp import credentials

logger = logging.getLogger(__name__)


class MissingCredentialsError(RuntimeError):
    """An expected missing local credential."""


class AuthenticationError(RuntimeError):
    """The vendor rejected authorization."""


class AccessDeniedError(RuntimeError):
    """The authenticated account lacks permission for an action."""


class VendorHTTPError(RuntimeError):
    def __init__(self, status, reason):
        self.status = (
            status if isinstance(status, int) and 100 <= status <= 599 else 500
        )
        allowed_reasons = (
            set(_HTTP_REASONS.values())
            | set(_VENDOR_REASONS.values())
            | {
                "The request failed.",
                "The service returned invalid JSON.",
            }
        )
        self.reason = (
            reason
            if isinstance(reason, str) and reason in allowed_reasons
            else "The request failed."
        )
        super().__init__(f"Smokeball API error {status}")


class RateLimitError(RuntimeError):
    def __init__(self, retry_after):
        try:
            numeric = float(retry_after)
            self.retry_after = (
                math.ceil(numeric) if math.isfinite(numeric) and numeric >= 0 else 10
            )
        except (TypeError, ValueError, OverflowError):
            self.retry_after = 10
        super().__init__(
            f"Smokeball rate limit exceeded; retry_after_seconds={retry_after}"
        )


class ArgumentValidationError(ValueError):
    def __init__(self, argument, expected):
        self.argument = argument
        self.expected = expected
        super().__init__(f"{argument} must be {expected}")


class TransportError(RuntimeError):
    """A sanitized transport failure retaining only whether the request writes."""

    def __init__(self, method):
        self.method = str(method).upper()
        self.outcome_unknown = self.method != "GET"
        super().__init__("request_transport_error")


_HTTP_REASONS = {
    400: "The request was rejected.",
    409: "The request conflicts with the current item state.",
    422: "The request fields were rejected.",
    500: "The service had an internal error.",
    502: "The service is temporarily unavailable.",
    503: "The service is temporarily unavailable.",
    504: "The service timed out.",
}
_VENDOR_REASONS = {
    "invalid_request": "The request is invalid.",
    "validation_error": "Request validation failed.",
    "invalid_parameter": "A request parameter is invalid.",
    "conflict": "The request conflicts with the current item state.",
    "service_unavailable": "The service is temporarily unavailable.",
}


def _vendor_reason(response):
    fallback = _HTTP_REASONS.get(response.status_code, "The request failed.")
    try:
        data = response.json()
    except ValueError:
        return fallback
    if isinstance(data, dict):
        for source in (data, data.get("error")):
            if isinstance(source, dict):
                for key in ("code", "error_code", "error", "message", "detail"):
                    value = source.get(key)
                    if isinstance(value, str) and value.lower() in _VENDOR_REASONS:
                        return _VENDOR_REASONS[value.lower()]
    return fallback


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

# Private/reserved address ranges that must not receive webhook payloads (SSRF hygiene).
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _reject_webhook_url(reason: str) -> None:
    logger.warning("webhook_url_rejected reason=%s", reason)
    raise ArgumentValidationError("target_url", "a public HTTPS URL")


def _validate_webhook_url(url: str) -> None:
    """Raise ValueError if url is not a safe https endpoint for webhook delivery.

    Enforces:
    - scheme must be https (prevents cleartext delivery)
    - hostname must not resolve to a private, loopback, or link-local address
      (prevents SSRF — Smokeball posting matter data to an internal service)

    Note: this is a best-effort syntactic check on the literal hostname.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        _reject_webhook_url("invalid_scheme")
    hostname = parsed.hostname or ""
    if not hostname:
        _reject_webhook_url("missing_hostname")
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        addr = None
    if addr is not None and any(addr in net for net in _PRIVATE_NETS):
        _reject_webhook_url("private_address")
    _BLOCKED_HOSTS = {"localhost", "local", "internal", "metadata.google.internal"}
    if hostname.lower() in _BLOCKED_HOSTS or hostname.lower().endswith(".local"):
        _reject_webhook_url("reserved_hostname")


# Resolve credentials through the pluggable store (OS keyring -> .env file).
credentials.load_into_environ(
    [
        "SMOKEBALL_CLIENT_ID",
        "SMOKEBALL_CLIENT_SECRET",
        "SMOKEBALL_API_KEY",
        "SMOKEBALL_REGION",
    ]
)

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
    """Return a safe numeric hint, retaining legitimate large vendor delays."""
    try:
        raw = resp.headers.get("Retry-After", default)
        if isinstance(raw, bool):
            return default
        number = float(raw)
        if not math.isfinite(number) or number < 0:
            return default
        seconds = math.ceil(number)
    except (TypeError, ValueError, OverflowError):
        return default
    return seconds


def _json_response(resp):
    try:
        return resp.json()
    except ValueError:
        logger.warning(
            "smokeball_response_rejected reason=non_json status=%s",
            resp.status_code,
        )
        raise VendorHTTPError(
            resp.status_code, "The service returned invalid JSON."
        ) from None


def _path_id(value):
    """Encode one untrusted identifier as a single URL path segment."""
    return urllib.parse.quote(str(value), safe="")


def _validate_page(limit: int, offset: int) -> None:
    if not 1 <= limit <= 200:
        logger.warning("list_request_rejected field=limit reason=out_of_range")
        raise ArgumentValidationError("limit", "an integer from 1 to 200")
    if offset < 0:
        logger.warning("list_request_rejected field=offset reason=out_of_range")
        raise ArgumentValidationError("offset", "a non-negative integer")


def _cap_page(result, limit: int):
    """Defensively enforce the caller's total limit on common vendor list shapes."""
    if isinstance(result, list):
        return result[:limit]
    if isinstance(result, dict):
        for key in ("value", "items", "data", "results", "Value", "Items"):
            items = result.get(key)
            if isinstance(items, list):
                if len(items) <= limit:
                    return result
                return {**result, key: items[:limit]}
    return result


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
        credentials.atomic_private_json(self.token_file, tokens)

    @property
    def access_token(self):
        return self.tokens.get("access_token", "")

    @property
    def refresh_token(self):
        return self.tokens.get("refresh_token", "")

    def refresh(self):
        if not self.refresh_token:
            logger.warning("credential_guard_rejected reason=missing_refresh_token")
            raise MissingCredentialsError("oauth_tokens")
        if not CLIENT_ID or not CLIENT_SECRET:
            logger.warning(
                "credential_guard_rejected reason=missing_oauth_client_config"
            )
            raise MissingCredentialsError("oauth_client")
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                timeout=30,
                allow_redirects=False,
            )
        except requests.RequestException:
            logger.warning("oauth_refresh_rejected reason=transport_error")
            raise TransportError("POST") from None
        if resp.status_code == 200:
            new_tokens = _json_response(resp)
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = self.refresh_token
            new_tokens["refreshed_at"] = datetime.now(timezone.utc).isoformat()
            self.save(new_tokens)
            return new_tokens
        logger.warning(
            "oauth_refresh_rejected reason=upstream_status status=%s",
            resp.status_code,
        )
        if resp.status_code in (400, 401):
            raise AuthenticationError("reauthorization_required")
        if resp.status_code == 403:
            raise AccessDeniedError("access_denied")
        if resp.status_code == 429:
            raise RateLimitError(_retry_after_seconds(resp))
        raise VendorHTTPError(resp.status_code, _vendor_reason(resp))


class SmokeBallClient:
    def __init__(self):
        if not API_KEY:
            logger.warning("credential_guard_rejected reason=missing_api_key")
            raise MissingCredentialsError("api_key")
        self.tm = TokenManager()
        if not self.tm.access_token and not self.tm.refresh_token:
            logger.warning("credential_guard_rejected reason=missing_oauth_tokens")
            raise MissingCredentialsError("oauth_tokens")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.tm.access_token}",
                "x-api-key": API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self,
        method,
        path,
        params=None,
        json_body=None,
        retry=True,
        _rate_retries=0,
        _retry_sleep_total=0,
    ):
        url = f"{BASE_URL}/{path.lstrip('/')}"
        try:
            resp = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=30,
                allow_redirects=False,
            )
        except requests.RequestException:
            logger.warning(
                "smokeball_request_rejected reason=transport_error method=%s", method
            )
            raise TransportError(method) from None

        if resp.status_code == 401 and retry:
            self.tm.refresh()
            self.session.headers["Authorization"] = f"Bearer {self.tm.access_token}"
            return self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                retry=False,
                _rate_retries=_rate_retries,
                _retry_sleep_total=_retry_sleep_total,
            )

        if resp.status_code == 429 and _rate_retries < 3:
            wait = _retry_after_seconds(resp)
            if wait > 60 or _retry_sleep_total + wait > 60:
                logger.warning(
                    "smokeball_request_rejected reason=rate_limit status=429"
                )
                raise RateLimitError(wait)
            logger.warning(
                "smokeball_request_retry reason=rate_limit wait_seconds=%s", wait
            )
            time.sleep(wait)
            return self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                retry=retry,
                _rate_retries=_rate_retries + 1,
                _retry_sleep_total=_retry_sleep_total + wait,
            )

        if resp.status_code == 429:
            retry_after = _retry_after_seconds(resp)
            logger.warning("smokeball_request_rejected reason=rate_limit status=429")
            raise RateLimitError(retry_after)

        if resp.status_code == 204:
            return {}

        if not 200 <= resp.status_code < 300:
            logger.warning(
                "smokeball_request_rejected reason=upstream_status method=%s status=%s",
                method,
                resp.status_code,
            )
            if resp.status_code == 401:
                raise AuthenticationError("reauthorization_required")
            if resp.status_code == 403:
                raise AccessDeniedError("access_denied")
            raise VendorHTTPError(resp.status_code, _vendor_reason(resp))

        try:
            return resp.json()
        except ValueError:
            logger.warning(
                "smokeball_response_rejected reason=non_json status=%s",
                resp.status_code,
            )
            raise VendorHTTPError(
                resp.status_code, "The service returned invalid JSON."
            ) from None

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

    def _get_page(self, path, *, limit=50, offset=0, params=None):
        _validate_page(limit, offset)
        query = {"limit": limit, "offset": offset, **(params or {})}
        return _cap_page(self.get(path, query), limit)

    # ── Firm ──────────────────────────────────────────────────────────────────

    def get_firm(self):
        return self.get("/firm")

    def update_firm(self, **fields):
        return self.put("/firm", fields)

    def get_firm_user_mappings(self):
        return self.get("/firm/usermappings")

    def get_firm_user_mapping(self, mapping_id):
        return self.get(f"/firm/usermappings/{_path_id(mapping_id)}")

    def update_firm_user_mapping(self, mapping_id, **fields):
        return self.put(f"/firm/usermappings/{_path_id(mapping_id)}", fields)

    def delete_firm_user_mapping(self, mapping_id):
        return self.delete(f"/firm/usermappings/{_path_id(mapping_id)}")

    # ── Staff ─────────────────────────────────────────────────────────────────

    def search_staff(self, query=None, limit=50, offset=0):
        params = {}
        if query:
            params["query"] = query
        return self._get_page("/staff", limit=limit, offset=offset, params=params)

    def get_staff_member(self, staff_id):
        return self.get(f"/staff/{_path_id(staff_id)}")

    def create_staff_member(self, **fields):
        return self.post("/staff", fields)

    def update_staff_member(self, staff_id, **fields):
        return self.put(f"/staff/{_path_id(staff_id)}", fields)

    def delete_staff_member(self, staff_id):
        return self.delete(f"/staff/{_path_id(staff_id)}")

    # ── Users ─────────────────────────────────────────────────────────────────

    def get_user(self, user_id):
        return self.get(f"/users/{_path_id(user_id)}")

    def create_user(self, **fields):
        return self.post("/users", fields)

    def remove_user(self, user_id):
        return self.delete(f"/users/{_path_id(user_id)}")

    def resend_user_invitation(self, user_id):
        return self.post(f"/users/{_path_id(user_id)}/resend-invitation")

    # ── Contacts ──────────────────────────────────────────────────────────────

    def list_contacts(self, limit=50, offset=0):
        return self._get_page("/contacts", limit=limit, offset=offset)

    def get_contact(self, contact_id):
        return self.get(f"/contacts/{_path_id(contact_id)}")

    def create_contact(
        self,
        contact_type: str = "person",
        first_name: str = "",
        last_name: str = "",
        company_name: str = "",
        email: str = "",
        phone: str = "",
    ):
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
        return self.put(f"/contacts/{_path_id(contact_id)}", fields)

    def delete_contact(self, contact_id):
        return self.delete(f"/contacts/{_path_id(contact_id)}")

    def get_contact_relations(self, contact_id):
        return self.get(f"/contacts/{_path_id(contact_id)}/relations")

    def get_contact_relation(self, contact_id, relation_id):
        return self.get(
            f"/contacts/{_path_id(contact_id)}/relations/{_path_id(relation_id)}"
        )

    def create_contact_relation(self, contact_id, **fields):
        return self.post(f"/contacts/{_path_id(contact_id)}/relations", fields)

    def update_contact_relation(self, contact_id, relation_id, **fields):
        return self.put(
            f"/contacts/{_path_id(contact_id)}/relations/{_path_id(relation_id)}",
            fields,
        )

    def delete_contact_relation(self, contact_id, relation_id):
        return self.delete(
            f"/contacts/{_path_id(contact_id)}/relations/{_path_id(relation_id)}"
        )

    def get_contact_tags(self, contact_id):
        return self.get(f"/contacts/{_path_id(contact_id)}/tags")

    def add_contact_tags(self, contact_id, tags: list):
        return self.post(f"/contacts/{_path_id(contact_id)}/tags", tags)

    def remove_contact_tags(self, contact_id, tag_id: str):
        return self.delete(f"/contacts/{_path_id(contact_id)}/tags/{_path_id(tag_id)}")

    # ── Matters ───────────────────────────────────────────────────────────────

    def list_matters(self, limit=50, offset=0):
        return self._get_page("/matters", limit=limit, offset=offset)

    def get_matter(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}")

    def create_matter(
        self,
        number: str = "",
        matter_type_id: str = "",
        client_ids: list | None = None,
        description: str = "",
        status: str = "",
    ):
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
        return self.put(f"/matters/{_path_id(matter_id)}", fields)

    def patch_matter(self, matter_id, **fields):
        return self.patch(f"/matters/{_path_id(matter_id)}", fields)

    def delete_matter(self, matter_id):
        return self.delete(f"/matters/{_path_id(matter_id)}")

    def get_matter_billing_configuration(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/billingconfiguration")

    def update_matter_billing_configuration(self, matter_id, **fields):
        return self.put(f"/matters/{_path_id(matter_id)}/billingconfiguration", fields)

    def get_matter_tags(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/tags")

    def add_matter_tags(self, matter_id, tags: list):
        return self.post(f"/matters/{_path_id(matter_id)}/tags", tags)

    def remove_matter_tags(self, matter_id, tag_id: str):
        return self.delete(f"/matters/{_path_id(matter_id)}/tags/{_path_id(tag_id)}")

    # ── Leads ─────────────────────────────────────────────────────────────────

    def list_leads(self, limit=50, offset=0):
        return self._get_page("/leads", limit=limit, offset=offset)

    def get_lead(self, lead_id):
        return self.get(f"/leads/{_path_id(lead_id)}")

    def create_lead(self, matter_type_id: str = "", client_id: str = ""):
        body: dict[str, object] = {"isLead": True}
        if matter_type_id:
            body["matterTypeId"] = matter_type_id
        if client_id:
            body["clientIds"] = [client_id]
        return self.post("/matters", body)

    def update_lead(self, lead_id, **fields):
        return self.put(f"/leads/{_path_id(lead_id)}", fields)

    def patch_lead(self, lead_id, **fields):
        return self.patch(f"/leads/{_path_id(lead_id)}", fields)

    def delete_lead(self, lead_id):
        return self.delete(f"/leads/{_path_id(lead_id)}")

    # ── Matter Types ──────────────────────────────────────────────────────────

    def list_matter_types(self, limit=100, offset=0):
        return self._get_page("/mattertypes", limit=limit, offset=offset)

    def get_matter_type(self, matter_type_id):
        return self.get(f"/mattertypes/{_path_id(matter_type_id)}")

    def list_matter_type_categories(self):
        return self.get("/mattertypes/categories")

    # ── Stages ────────────────────────────────────────────────────────────────

    def list_stage_sets(self):
        return self.get("/stages")

    def get_stage_set(self, stage_set_id):
        return self.get(f"/stages/{_path_id(stage_set_id)}")

    def get_stage_in_set(self, stage_set_id, stage_id):
        return self.get(f"/stages/{_path_id(stage_set_id)}/stages/{_path_id(stage_id)}")

    def list_matter_stage_mappings(self):
        return self.get("/stages/matterstagesmapping")

    def get_matter_stage(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/stage")

    # ── Roles ─────────────────────────────────────────────────────────────────

    def get_roles_on_matter(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/roles")

    def get_role_on_matter(self, matter_id, role_id):
        return self.get(f"/matters/{_path_id(matter_id)}/roles/{_path_id(role_id)}")

    def add_role_to_matter(self, matter_id, **fields):
        return self.post(f"/matters/{_path_id(matter_id)}/roles", fields)

    def update_role_on_matter(self, matter_id, role_id, **fields):
        return self.put(
            f"/matters/{_path_id(matter_id)}/roles/{_path_id(role_id)}", fields
        )

    def remove_role_from_matter(self, matter_id, role_id):
        return self.delete(f"/matters/{_path_id(matter_id)}/roles/{_path_id(role_id)}")

    # ── Relationships ─────────────────────────────────────────────────────────

    def get_relationships_on_matter(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/relationships")

    def get_relationship_on_role(self, matter_id, role_id):
        return self.get(
            f"/matters/{_path_id(matter_id)}/roles/{_path_id(role_id)}/relationships"
        )

    def add_relationship_to_role(self, matter_id, role_id, **fields):
        return self.post(
            f"/matters/{_path_id(matter_id)}/roles/{_path_id(role_id)}/relationships",
            fields,
        )

    def update_relationship(self, matter_id, role_id, relationship_id, **fields):
        return self.put(
            f"/matters/{_path_id(matter_id)}/roles/{_path_id(role_id)}/relationships/{_path_id(relationship_id)}",
            fields,
        )

    def remove_relationship_from_role(self, matter_id, role_id, relationship_id):
        return self.delete(
            f"/matters/{_path_id(matter_id)}/roles/{_path_id(role_id)}/relationships/{_path_id(relationship_id)}"
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def get_tasks(self, matter_id=None, limit=50, offset=0):
        params = {}
        if matter_id:
            params["matterId"] = matter_id
        return self._get_page("/tasks", limit=limit, offset=offset, params=params)

    def get_task(self, task_id):
        return self.get(f"/tasks/{_path_id(task_id)}")

    def create_task(self, **fields):
        return self.post("/tasks", fields)

    def update_task(self, task_id, **fields):
        return self.put(f"/tasks/{_path_id(task_id)}", fields)

    def delete_task(self, task_id):
        return self.delete(f"/tasks/{_path_id(task_id)}")

    def get_subtasks(self, task_id):
        return self.get(f"/tasks/{_path_id(task_id)}/subtasks")

    def get_subtask(self, task_id, subtask_id):
        return self.get(f"/tasks/{_path_id(task_id)}/subtasks/{_path_id(subtask_id)}")

    def create_subtask(self, task_id, **fields):
        return self.post(f"/tasks/{_path_id(task_id)}/subtasks", fields)

    def update_subtask(self, task_id, subtask_id, **fields):
        return self.put(
            f"/tasks/{_path_id(task_id)}/subtasks/{_path_id(subtask_id)}", fields
        )

    def delete_subtask(self, task_id, subtask_id):
        return self.delete(
            f"/tasks/{_path_id(task_id)}/subtasks/{_path_id(subtask_id)}"
        )

    def get_task_documents(self, task_id):
        return self.get(f"/tasks/{_path_id(task_id)}/documents")

    def get_task_document(self, task_id, document_id):
        return self.get(f"/tasks/{_path_id(task_id)}/documents/{_path_id(document_id)}")

    def create_task_document(self, task_id, **fields):
        return self.post(f"/tasks/{_path_id(task_id)}/documents", fields)

    def delete_task_document(self, task_id, document_id):
        return self.delete(
            f"/tasks/{_path_id(task_id)}/documents/{_path_id(document_id)}"
        )

    # ── Events ────────────────────────────────────────────────────────────────

    def get_events(self, matter_id=None, limit=50, offset=0):
        params = {}
        if matter_id:
            params["matterId"] = matter_id
        return self._get_page("/events", limit=limit, offset=offset, params=params)

    def get_event(self, event_id):
        return self.get(f"/events/{_path_id(event_id)}")

    def create_event(self, **fields):
        return self.post("/events", fields)

    def update_event(self, event_id, **fields):
        return self.put(f"/events/{_path_id(event_id)}", fields)

    def delete_event(self, event_id):
        return self.delete(f"/events/{_path_id(event_id)}")

    def get_event_reminders(self, event_id):
        return self.get(f"/events/{_path_id(event_id)}/reminders")

    def create_event_reminder(self, event_id, **fields):
        return self.post(f"/events/{_path_id(event_id)}/reminders", fields)

    def update_event_reminder(self, event_id, reminder_id, **fields):
        return self.put(
            f"/events/{_path_id(event_id)}/reminders/{_path_id(reminder_id)}", fields
        )

    def delete_event_reminder(self, event_id, reminder_id):
        return self.delete(
            f"/events/{_path_id(event_id)}/reminders/{_path_id(reminder_id)}"
        )

    # ── Memos ─────────────────────────────────────────────────────────────────

    def get_memos_on_matter(self, matter_id, limit=50, offset=0):
        return self._get_page(
            f"/matters/{_path_id(matter_id)}/memos", limit=limit, offset=offset
        )

    def get_memo(self, memo_id):
        return self.get(f"/memos/{_path_id(memo_id)}")

    def create_memo(self, matter_id, **fields):
        return self.post(f"/matters/{_path_id(matter_id)}/memos", fields)

    def update_memo(self, memo_id, **fields):
        return self.put(f"/memos/{_path_id(memo_id)}", fields)

    def delete_memo(self, memo_id):
        return self.delete(f"/memos/{_path_id(memo_id)}")

    # ── Fees ──────────────────────────────────────────────────────────────────

    def get_fees(self, matter_id=None, limit=50, offset=0):
        params = {}
        if matter_id:
            params["matterId"] = matter_id
        return self._get_page("/fees", limit=limit, offset=offset, params=params)

    def get_fee(self, fee_id):
        return self.get(f"/fees/{_path_id(fee_id)}")

    def create_fee(self, **fields):
        return self.post("/fees", fields)

    def update_fee(self, fee_id, **fields):
        return self.put(f"/fees/{_path_id(fee_id)}", fields)

    def patch_fee(self, fee_id, **fields):
        return self.patch(f"/fees/{_path_id(fee_id)}", fields)

    def delete_fee(self, fee_id):
        return self.delete(f"/fees/{_path_id(fee_id)}")

    # ── Expenses ──────────────────────────────────────────────────────────────

    def get_expenses(self, matter_id=None, limit=50, offset=0):
        params = {}
        if matter_id:
            params["matterId"] = matter_id
        return self._get_page("/expenses", limit=limit, offset=offset, params=params)

    def get_expense(self, expense_id):
        return self.get(f"/expenses/{_path_id(expense_id)}")

    def create_expense(self, **fields):
        return self.post("/expenses", fields)

    def update_expense(self, expense_id, **fields):
        return self.put(f"/expenses/{_path_id(expense_id)}", fields)

    def patch_expense(self, expense_id, **fields):
        return self.patch(f"/expenses/{_path_id(expense_id)}", fields)

    def delete_expense(self, expense_id):
        return self.delete(f"/expenses/{_path_id(expense_id)}")

    # ── Invoices ──────────────────────────────────────────────────────────────

    def get_invoices(self, matter_id=None, limit=50, offset=0):
        params = {}
        if matter_id:
            params["matterId"] = matter_id
        return self._get_page("/invoices", limit=limit, offset=offset, params=params)

    def get_invoice(self, invoice_id):
        return self.get(f"/invoices/{_path_id(invoice_id)}")

    def get_invoice_download_url(self, invoice_id):
        return self.get(f"/invoices/{_path_id(invoice_id)}/downloadurl")

    # ── Activity Codes ────────────────────────────────────────────────────────

    def get_activity_codes(self, limit=100, offset=0):
        return self._get_page("/activitycodes", limit=limit, offset=offset)

    def get_activity_code(self, code_id):
        return self.get(f"/activitycodes/{_path_id(code_id)}")

    def create_activity_code(self, **fields):
        return self.post("/activitycodes", fields)

    def update_activity_code(self, code_id, **fields):
        return self.put(f"/activitycodes/{_path_id(code_id)}", fields)

    def delete_activity_code(self, code_id):
        return self.delete(f"/activitycodes/{_path_id(code_id)}")

    # ── Bank Accounts ─────────────────────────────────────────────────────────

    def get_bank_accounts(self, limit=50, offset=0):
        return self._get_page("/bankaccounts", limit=limit, offset=offset)

    def get_bank_account(self, account_id):
        return self.get(f"/bankaccounts/{_path_id(account_id)}")

    def get_bank_account_matter_balances(self, account_id):
        return self.get(f"/bankaccounts/{_path_id(account_id)}/matterbalances")

    def get_protected_bank_account_balance(self, account_id):
        return self.get(f"/bankaccounts/{_path_id(account_id)}/protectedbalance")

    def get_transactions(self, account_id, limit=50, offset=0):
        return self._get_page(
            f"/bankaccounts/{_path_id(account_id)}/transactions",
            limit=limit,
            offset=offset,
        )

    def get_transaction(self, account_id, transaction_id):
        return self.get(
            f"/bankaccounts/{_path_id(account_id)}/transactions/{_path_id(transaction_id)}"
        )

    def create_transaction(self, account_id, **fields):
        return self.post(f"/bankaccounts/{_path_id(account_id)}/transactions", fields)

    def create_requisition(self, account_id, **fields):
        return self.post(f"/bankaccounts/{_path_id(account_id)}/requisitions", fields)

    def protect_funds(self, account_id, **fields):
        return self.post(f"/bankaccounts/{_path_id(account_id)}/protect", fields)

    def unprotect_funds(self, account_id, **fields):
        return self.post(f"/bankaccounts/{_path_id(account_id)}/unprotect", fields)

    # ── Files ─────────────────────────────────────────────────────────────────

    def get_files_on_matter(self, matter_id, limit=50, offset=0):
        return self._get_page(
            f"/matters/{_path_id(matter_id)}/files", limit=limit, offset=offset
        )

    def get_file(self, file_id):
        return self.get(f"/files/{_path_id(file_id)}")

    def get_file_download_url(self, file_id):
        return self.get(f"/files/{_path_id(file_id)}/downloadurl")

    def get_file_upload_url(self, file_id):
        return self.get(f"/files/{_path_id(file_id)}/uploadurl")

    def get_file_history(self, matter_id, limit=50, offset=0):
        return self._get_page(
            f"/matters/{_path_id(matter_id)}/files/history", limit=limit, offset=offset
        )

    def add_file_to_matter(self, matter_id, **fields):
        return self.post(f"/matters/{_path_id(matter_id)}/files", fields)

    def add_files_to_matter(self, matter_id, files: list):
        return self.post(
            f"/matters/{_path_id(matter_id)}/files/batch", {"files": files}
        )

    def patch_file(self, file_id, **fields):
        return self.patch(f"/files/{_path_id(file_id)}", fields)

    def delete_file(self, file_id):
        return self.delete(f"/files/{_path_id(file_id)}")

    def create_preview_request(self, file_id):
        return self.post(f"/files/{_path_id(file_id)}/preview")

    def get_preview_info(self, file_id):
        return self.get(f"/files/{_path_id(file_id)}/preview")

    def get_preview_info_by_version(self, file_id, version_id):
        return self.get(
            f"/files/{_path_id(file_id)}/versions/{_path_id(version_id)}/preview"
        )

    # ── Folders ───────────────────────────────────────────────────────────────

    def get_root_folder_contents(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/folders")

    def get_folder_contents(self, matter_id, folder_id):
        return self.get(f"/matters/{_path_id(matter_id)}/folders/{_path_id(folder_id)}")

    def get_folder_path_hierarchy(self, matter_id, folder_id):
        return self.get(
            f"/matters/{_path_id(matter_id)}/folders/{_path_id(folder_id)}/path"
        )

    def get_folder_history(self, matter_id, limit=50, offset=0):
        return self._get_page(
            f"/matters/{_path_id(matter_id)}/folders/history",
            limit=limit,
            offset=offset,
        )

    def create_folder(self, matter_id, **fields):
        return self.post(f"/matters/{_path_id(matter_id)}/folders", fields)

    def update_folder(self, folder_id, **fields):
        return self.put(f"/folders/{_path_id(folder_id)}", fields)

    def patch_folder(self, folder_id, **fields):
        return self.patch(f"/folders/{_path_id(folder_id)}", fields)

    def delete_folder(self, folder_id):
        return self.delete(f"/folders/{_path_id(folder_id)}")

    # ── Archive ───────────────────────────────────────────────────────────────

    def get_matter_archive(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/archive")

    def update_matter_archive(self, matter_id, **fields):
        return self.put(f"/matters/{_path_id(matter_id)}/archive", fields)

    def patch_matter_archive(self, matter_id, **fields):
        return self.patch(f"/matters/{_path_id(matter_id)}/archive", fields)

    # ── Referral Types ────────────────────────────────────────────────────────

    def get_referral_types(self, limit=100, offset=0):
        return self._get_page("/referraltypes", limit=limit, offset=offset)

    def get_referral_type(self, referral_type_id):
        return self.get(f"/referraltypes/{_path_id(referral_type_id)}")

    # ── Authorization ─────────────────────────────────────────────────────────

    def get_authorization_groups(self):
        return self.get("/authorization/groups")

    def get_authorization_group(self, group_id):
        return self.get(f"/authorization/groups/{_path_id(group_id)}")

    def create_authorization_group(self, **fields):
        return self.post("/authorization/groups", fields)

    def update_authorization_group(self, group_id, **fields):
        return self.put(f"/authorization/groups/{_path_id(group_id)}", fields)

    def delete_authorization_group(self, group_id):
        return self.delete(f"/authorization/groups/{_path_id(group_id)}")

    def get_authorization_policy(self, reference):
        return self.get(f"/policies/{_path_id(reference)}")

    def create_authorization_policy(self, **fields):
        return self.post("/policies", fields)

    def update_authorization_policy(self, reference, **fields):
        return self.put(f"/policies/{_path_id(reference)}", fields)

    # ── Notifications ─────────────────────────────────────────────────────────

    def get_notification(self, notification_id):
        return self.get(f"/notifications/{_path_id(notification_id)}")

    def create_notification(self, **fields):
        return self.post("/notifications", fields)

    # ── Plugins ───────────────────────────────────────────────────────────────

    def get_plugins(self):
        return self.get("/plugins")

    def get_plugin(self, plugin_id):
        return self.get(f"/plugins/{_path_id(plugin_id)}")

    def create_plugin(self, **fields):
        return self.post("/plugins", fields)

    def update_plugin(self, plugin_id, **fields):
        return self.put(f"/plugins/{_path_id(plugin_id)}", fields)

    def delete_plugin(self, plugin_id):
        return self.delete(f"/plugins/{_path_id(plugin_id)}")

    def get_plugin_subscriptions(self):
        return self.get("/plugins/subscriptions")

    def get_plugin_subscription(self, subscription_id):
        return self.get(f"/plugins/subscriptions/{_path_id(subscription_id)}")

    def subscribe_to_plugin(self, plugin_id):
        return self.post(f"/plugins/{_path_id(plugin_id)}/subscribe")

    def unsubscribe_from_plugin(self, plugin_id):
        return self.delete(f"/plugins/{_path_id(plugin_id)}/subscribe")

    def request_plugin_url(self, plugin_id):
        return self.get(f"/plugins/{_path_id(plugin_id)}/url")

    # ── Portal ────────────────────────────────────────────────────────────────

    def create_portal_task(self, **fields):
        return self.post("/portal/tasks", fields)

    def patch_portal_task(self, task_id, **fields):
        return self.patch(f"/portal/tasks/{_path_id(task_id)}", fields)

    def send_portal_message(self, **fields):
        return self.post("/portal/messages", fields)

    # ── Layout Designs ────────────────────────────────────────────────────────

    def get_layout_designs(self):
        return self.get("/layoutdesigns")

    def get_layout_design(self, design_id):
        return self.get(f"/layoutdesigns/{_path_id(design_id)}")

    # ── Layout Matter Items ────────────────────────────────────────────────────

    def get_layouts_on_matter(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/layouts")

    def get_layout_on_matter(self, matter_id, layout_id):
        return self.get(f"/matters/{_path_id(matter_id)}/layouts/{_path_id(layout_id)}")

    def add_layout_to_matter(self, matter_id, **fields):
        return self.post(f"/matters/{_path_id(matter_id)}/layouts", fields)

    def add_contact_to_layout(self, matter_id, layout_id, **fields):
        return self.post(
            f"/matters/{_path_id(matter_id)}/layouts/{_path_id(layout_id)}/contacts",
            fields,
        )

    def get_layout_contacts(self, matter_id, layout_id):
        return self.get(
            f"/matters/{_path_id(matter_id)}/layouts/{_path_id(layout_id)}/contacts"
        )

    def merge_layout(self, matter_id, layout_id):
        return self.post(
            f"/matters/{_path_id(matter_id)}/layouts/{_path_id(layout_id)}/merge"
        )

    def remove_layout_from_matter(self, matter_id, layout_id):
        return self.delete(
            f"/matters/{_path_id(matter_id)}/layouts/{_path_id(layout_id)}"
        )

    # ── Matter Items ──────────────────────────────────────────────────────────

    def get_items_on_matter(self, matter_id):
        return self.get(f"/matters/{_path_id(matter_id)}/items")

    def get_item_on_matter(self, matter_id, item_id):
        return self.get(f"/matters/{_path_id(matter_id)}/items/{_path_id(item_id)}")

    # ── Integrated Search ─────────────────────────────────────────────────────

    def get_integrated_search_mapping(self):
        return self.get("/search/mapping")

    # ── Webhooks ──────────────────────────────────────────────────────────────

    def get_webhook_subscriptions(self):
        return self.get("/webhooks/subscriptions")

    def get_webhook_subscription(self, subscription_id):
        return self.get(f"/webhooks/subscriptions/{_path_id(subscription_id)}")

    def create_webhook_subscription(self, event_type, url, **fields):
        _validate_webhook_url(url)
        body = {"eventType": event_type, "url": url, **fields}
        return self.post("/webhooks/subscriptions", body)

    def update_webhook_subscription(self, subscription_id, **fields):
        if "url" in fields:
            _validate_webhook_url(fields["url"])
        return self.put(f"/webhooks/subscriptions/{_path_id(subscription_id)}", fields)

    def delete_webhook_subscription(self, subscription_id):
        return self.delete(f"/webhooks/subscriptions/{_path_id(subscription_id)}")

    def get_webhook_event_types(self):
        return self.get("/webhooks/eventtypes")

    def notify_webhook_subscription(self, subscription_id):
        return self.post(f"/webhooks/subscriptions/{_path_id(subscription_id)}/notify")
