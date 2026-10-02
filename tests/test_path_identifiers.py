"""Regression coverage for every ID-bearing client path call site.

The transport boundary is replaced, so rejected identifiers must fail before
any HTTP call, including a preliminary read in a merge/update operation.
"""

import inspect
from unittest.mock import Mock

import pytest
import requests

from smokeball_mcp.client import SmokeBallClient

CASES = [
    ("get_firm_user_mapping", "mapping_id"),
    ("update_firm_user_mapping", "mapping_id"),
    ("delete_firm_user_mapping", "mapping_id"),
    ("get_staff_member", "staff_id"),
    ("update_staff_member", "staff_id"),
    ("delete_staff_member", "staff_id"),
    ("get_user", "user_id"),
    ("remove_user", "user_id"),
    ("resend_user_invitation", "user_id"),
    ("get_contact", "contact_id"),
    ("update_contact", "contact_id"),
    ("delete_contact", "contact_id"),
    ("get_contact_relations", "contact_id"),
    ("get_contact_relation", "contact_id"),
    ("get_contact_relation", "relation_id"),
    ("create_contact_relation", "contact_id"),
    ("update_contact_relation", "contact_id"),
    ("update_contact_relation", "relation_id"),
    ("delete_contact_relation", "contact_id"),
    ("delete_contact_relation", "relation_id"),
    ("get_contact_tags", "contact_id"),
    ("add_contact_tags", "contact_id"),
    ("remove_contact_tags", "contact_id"),
    ("remove_contact_tags", "tag_id"),
    ("get_matter", "matter_id"),
    ("update_matter", "matter_id"),
    ("patch_matter", "matter_id"),
    ("delete_matter", "matter_id"),
    ("get_matter_billing_configuration", "matter_id"),
    ("update_matter_billing_configuration", "matter_id"),
    ("get_matter_tags", "matter_id"),
    ("add_matter_tags", "matter_id"),
    ("remove_matter_tags", "matter_id"),
    ("remove_matter_tags", "tag_id"),
    ("get_lead", "lead_id"),
    ("update_lead", "lead_id"),
    ("patch_lead", "lead_id"),
    ("delete_lead", "lead_id"),
    ("get_matter_type", "matter_type_id"),
    ("get_stage_set", "stage_set_id"),
    ("get_stage_in_set", "stage_id"),
    ("get_stage_in_set", "stage_set_id"),
    ("get_matter_stage", "matter_id"),
    ("get_roles_on_matter", "matter_id"),
    ("get_role_on_matter", "matter_id"),
    ("get_role_on_matter", "role_id"),
    ("add_role_to_matter", "matter_id"),
    ("update_role_on_matter", "matter_id"),
    ("update_role_on_matter", "role_id"),
    ("remove_role_from_matter", "matter_id"),
    ("remove_role_from_matter", "role_id"),
    ("get_relationships_on_matter", "matter_id"),
    ("get_relationship_on_role", "matter_id"),
    ("get_relationship_on_role", "role_id"),
    ("add_relationship_to_role", "matter_id"),
    ("add_relationship_to_role", "role_id"),
    ("update_relationship", "matter_id"),
    ("update_relationship", "relationship_id"),
    ("update_relationship", "role_id"),
    ("remove_relationship_from_role", "matter_id"),
    ("remove_relationship_from_role", "relationship_id"),
    ("remove_relationship_from_role", "role_id"),
    ("get_task", "task_id"),
    ("update_task", "task_id"),
    ("delete_task", "task_id"),
    ("get_subtasks", "task_id"),
    ("get_subtask", "subtask_id"),
    ("get_subtask", "task_id"),
    ("create_subtask", "task_id"),
    ("update_subtask", "subtask_id"),
    ("update_subtask", "task_id"),
    ("delete_subtask", "subtask_id"),
    ("delete_subtask", "task_id"),
    ("get_task_documents", "task_id"),
    ("get_task_document", "document_id"),
    ("get_task_document", "task_id"),
    ("create_task_document", "task_id"),
    ("delete_task_document", "document_id"),
    ("delete_task_document", "task_id"),
    ("get_event", "event_id"),
    ("update_event", "event_id"),
    ("delete_event", "event_id"),
    ("get_event_reminders", "event_id"),
    ("create_event_reminder", "event_id"),
    ("update_event_reminder", "event_id"),
    ("update_event_reminder", "reminder_id"),
    ("delete_event_reminder", "event_id"),
    ("delete_event_reminder", "reminder_id"),
    ("get_memos_on_matter", "matter_id"),
    ("get_memo", "memo_id"),
    ("create_memo", "matter_id"),
    ("update_memo", "memo_id"),
    ("delete_memo", "memo_id"),
    ("get_fee", "fee_id"),
    ("update_fee", "fee_id"),
    ("patch_fee", "fee_id"),
    ("delete_fee", "fee_id"),
    ("get_expense", "expense_id"),
    ("update_expense", "expense_id"),
    ("patch_expense", "expense_id"),
    ("delete_expense", "expense_id"),
    ("get_invoice", "invoice_id"),
    ("get_invoice_download_url", "invoice_id"),
    ("get_activity_code", "code_id"),
    ("update_activity_code", "code_id"),
    ("delete_activity_code", "code_id"),
    ("get_bank_account", "account_id"),
    ("get_bank_account_matter_balances", "account_id"),
    ("get_protected_bank_account_balance", "account_id"),
    ("get_transactions", "account_id"),
    ("get_transaction", "account_id"),
    ("get_transaction", "transaction_id"),
    ("create_transaction", "account_id"),
    ("create_requisition", "account_id"),
    ("protect_funds", "account_id"),
    ("unprotect_funds", "account_id"),
    ("get_files_on_matter", "matter_id"),
    ("get_file", "file_id"),
    ("get_file_download_url", "file_id"),
    ("get_file_upload_url", "file_id"),
    ("get_file_history", "matter_id"),
    ("add_file_to_matter", "matter_id"),
    ("add_files_to_matter", "matter_id"),
    ("patch_file", "file_id"),
    ("delete_file", "file_id"),
    ("create_preview_request", "file_id"),
    ("get_preview_info", "file_id"),
    ("get_preview_info_by_version", "file_id"),
    ("get_preview_info_by_version", "version_id"),
    ("get_root_folder_contents", "matter_id"),
    ("get_folder_contents", "folder_id"),
    ("get_folder_contents", "matter_id"),
    ("get_folder_path_hierarchy", "folder_id"),
    ("get_folder_path_hierarchy", "matter_id"),
    ("get_folder_history", "matter_id"),
    ("create_folder", "matter_id"),
    ("update_folder", "folder_id"),
    ("patch_folder", "folder_id"),
    ("delete_folder", "folder_id"),
    ("get_matter_archive", "matter_id"),
    ("update_matter_archive", "matter_id"),
    ("patch_matter_archive", "matter_id"),
    ("get_referral_type", "referral_type_id"),
    ("get_authorization_group", "group_id"),
    ("update_authorization_group", "group_id"),
    ("delete_authorization_group", "group_id"),
    ("get_authorization_policy", "reference"),
    ("update_authorization_policy", "reference"),
    ("get_notification", "notification_id"),
    ("get_plugin", "plugin_id"),
    ("update_plugin", "plugin_id"),
    ("delete_plugin", "plugin_id"),
    ("get_plugin_subscription", "subscription_id"),
    ("subscribe_to_plugin", "plugin_id"),
    ("unsubscribe_from_plugin", "plugin_id"),
    ("request_plugin_url", "plugin_id"),
    ("patch_portal_task", "task_id"),
    ("get_layout_design", "design_id"),
    ("get_layouts_on_matter", "matter_id"),
    ("get_layout_on_matter", "layout_id"),
    ("get_layout_on_matter", "matter_id"),
    ("add_layout_to_matter", "matter_id"),
    ("add_contact_to_layout", "layout_id"),
    ("add_contact_to_layout", "matter_id"),
    ("get_layout_contacts", "layout_id"),
    ("get_layout_contacts", "matter_id"),
    ("merge_layout", "layout_id"),
    ("merge_layout", "matter_id"),
    ("remove_layout_from_matter", "layout_id"),
    ("remove_layout_from_matter", "matter_id"),
    ("get_items_on_matter", "matter_id"),
    ("get_item_on_matter", "item_id"),
    ("get_item_on_matter", "matter_id"),
    ("get_webhook_subscription", "subscription_id"),
    ("update_webhook_subscription", "subscription_id"),
    ("delete_webhook_subscription", "subscription_id"),
    ("notify_webhook_subscription", "subscription_id"),
]


def client_and_arguments(method):
    client = object.__new__(SmokeBallClient)
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"id": "normal-id", "success": true}'
    request = Mock(return_value={"id": "normal-id", "success": True})
    send = Mock(return_value=response)
    client._request = request
    client._send = send
    kwargs = {}
    for key, param in inspect.signature(getattr(client, method)).parameters.items():
        if param.default is not inspect.Parameter.empty or param.kind in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            continue
        annotation = str(param.annotation)
        if "dict" in annotation or key in {"body", "fields", "overlay"}:
            kwargs[key] = {"name": "probe"}
        elif "int" in annotation:
            kwargs[key] = 1
        else:
            kwargs[key] = "normal-id"
    if "resource" in kwargs:
        kwargs["resource"] = "matters"
    if "path" in kwargs:
        kwargs["path"] = "/tasks"
    if method == "tag_call":
        kwargs["tag_ids"] = [1]
    if method == "update_contact" and SmokeBallClient.__name__ == "CloudTalkClient":
        kwargs["name"] = "probe"
    return client, kwargs, request, send


@pytest.mark.parametrize(("method", "parameter"), CASES)
@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "a/../b", "%2e%2e", "a?b", "a#b", "a\\b", " ", "a\n", None, True],
)
def test_invalid_path_id_never_reaches_transport(method, parameter, value):
    client, kwargs, request, send = client_and_arguments(method)
    kwargs[parameter] = value
    with pytest.raises(Exception) as caught:
        getattr(client, method)(**kwargs)
    error = caught.value
    assert parameter in str(error) or getattr(error, "field", None) == parameter
    assert "identifier" in str(error) or "identifier" in getattr(error, "expected", "")
    request.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize(("method", "parameter"), CASES)
@pytest.mark.parametrize(
    "value", ["normal-id", "550e8400-e29b-41d4-a716-446655440000", "123", 123]
)
def test_normal_path_id_reaches_transport(method, parameter, value):
    client, kwargs, request, send = client_and_arguments(method)
    kwargs[parameter] = value
    getattr(client, method)(**kwargs)
    calls = request.call_args_list + send.call_args_list
    assert calls
    assert any(str(value) in str(call) for call in calls)
