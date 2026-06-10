#!/usr/bin/env python3
"""Smokeball MCP Server — full Smokeball API coverage via FastMCP."""

import json
from mcp.server.fastmcp import FastMCP
from .client import SmokeBallClient

mcp = FastMCP(
    "smokeball-mcp",
    instructions=(
        "Full access to Smokeball practice management: matters, contacts, leads, tasks, "
        "events, fees, expenses, invoices, files, folders, bank accounts, staff, plugins, "
        "webhooks, portal, and more."
    ),
)


# ── Firm ──────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_firm() -> str:
    """Get this firm's profile and settings."""
    return json.dumps(SmokeBallClient().get_firm(), indent=2)


@mcp.tool()
def update_firm(
    name: str = "", phone: str = "", email: str = "", address: str = ""
) -> str:
    """Update firm profile fields. Only pass fields you want to change."""
    fields = {}
    if name:
        fields["name"] = name
    if phone:
        fields["phone"] = phone
    if email:
        fields["email"] = email
    if address:
        fields["address"] = address
    return json.dumps(SmokeBallClient().update_firm(**fields), indent=2)


@mcp.tool()
def get_firm_user_mappings() -> str:
    """List all user mappings for this firm."""
    return json.dumps(SmokeBallClient().get_firm_user_mappings(), indent=2)


@mcp.tool()
def get_firm_user_mapping(mapping_id: str) -> str:
    """Get a specific firm user mapping by ID."""
    return json.dumps(SmokeBallClient().get_firm_user_mapping(mapping_id), indent=2)


@mcp.tool()
def update_firm_user_mapping(
    mapping_id: str, staff_id: str = "", email: str = ""
) -> str:
    """Update a firm user mapping (link a staff member to a system user)."""
    fields = {}
    if staff_id:
        fields["staffId"] = staff_id
    if email:
        fields["email"] = email
    return json.dumps(
        SmokeBallClient().update_firm_user_mapping(mapping_id, **fields), indent=2
    )


@mcp.tool()
def delete_firm_user_mapping(mapping_id: str) -> str:
    """Delete a firm user mapping by ID."""
    return json.dumps(SmokeBallClient().delete_firm_user_mapping(mapping_id), indent=2)


# ── Staff ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def search_staff(query: str = "", limit: int = 50, offset: int = 0) -> str:
    """Search staff members. query: name or email fragment."""
    return json.dumps(
        SmokeBallClient().search_staff(query=query or None, limit=limit, offset=offset),
        indent=2,
    )


@mcp.tool()
def get_staff_member(staff_id: str) -> str:
    """Get a staff member by ID."""
    return json.dumps(SmokeBallClient().get_staff_member(staff_id), indent=2)


@mcp.tool()
def create_staff_member(
    first_name: str, last_name: str, email: str, role: str = ""
) -> str:
    """Create a new staff member."""
    fields = {"firstName": first_name, "lastName": last_name, "email": email}
    if role:
        fields["role"] = role
    return json.dumps(SmokeBallClient().create_staff_member(**fields), indent=2)


@mcp.tool()
def update_staff_member(
    staff_id: str,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    role: str = "",
) -> str:
    """Update a staff member's details."""
    fields = {}
    if first_name:
        fields["firstName"] = first_name
    if last_name:
        fields["lastName"] = last_name
    if email:
        fields["email"] = email
    if role:
        fields["role"] = role
    return json.dumps(
        SmokeBallClient().update_staff_member(staff_id, **fields), indent=2
    )


@mcp.tool()
def delete_staff_member(staff_id: str) -> str:
    """Delete a staff member by ID."""
    return json.dumps(SmokeBallClient().delete_staff_member(staff_id), indent=2)


# ── Users ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_user(user_id: str) -> str:
    """Get a user by ID."""
    return json.dumps(SmokeBallClient().get_user(user_id), indent=2)


@mcp.tool()
def create_user(email: str, first_name: str = "", last_name: str = "") -> str:
    """Create a new user (invite to the firm)."""
    fields = {"email": email}
    if first_name:
        fields["firstName"] = first_name
    if last_name:
        fields["lastName"] = last_name
    return json.dumps(SmokeBallClient().create_user(**fields), indent=2)


@mcp.tool()
def remove_user(user_id: str) -> str:
    """Remove a user from the firm."""
    return json.dumps(SmokeBallClient().remove_user(user_id), indent=2)


@mcp.tool()
def resend_user_invitation(user_id: str) -> str:
    """Resend an invitation email to a user."""
    return json.dumps(SmokeBallClient().resend_user_invitation(user_id), indent=2)


# ── Contacts ──────────────────────────────────────────────────────────────────


@mcp.tool()
def list_contacts(limit: int = 50, offset: int = 0) -> str:
    """List contacts with offset pagination."""
    return json.dumps(
        SmokeBallClient().list_contacts(limit=limit, offset=offset), indent=2
    )


@mcp.tool()
def get_contact(contact_id: str) -> str:
    """Get a contact by ID."""
    return json.dumps(SmokeBallClient().get_contact(contact_id), indent=2)


@mcp.tool()
def create_contact(
    contact_type: str = "person",
    first_name: str = "",
    last_name: str = "",
    company_name: str = "",
    email: str = "",
    phone: str = "",
) -> str:
    """Create a contact. contact_type: 'person' (default) or 'company'.
    For person: supply first_name / last_name. For company: supply company_name."""
    return json.dumps(
        SmokeBallClient().create_contact(
            contact_type=contact_type,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            email=email,
            phone=phone,
        ),
        indent=2,
    )


@mcp.tool()
def update_contact(
    contact_id: str,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    phone: str = "",
) -> str:
    """Update a contact's details."""
    fields = {}
    if first_name:
        fields["firstName"] = first_name
    if last_name:
        fields["lastName"] = last_name
    if email:
        fields["email"] = email
    if phone:
        fields["phone"] = phone
    return json.dumps(SmokeBallClient().update_contact(contact_id, **fields), indent=2)


@mcp.tool()
def delete_contact(contact_id: str) -> str:
    """Delete a contact by ID."""
    return json.dumps(SmokeBallClient().delete_contact(contact_id), indent=2)


@mcp.tool()
def get_contact_relations(contact_id: str) -> str:
    """Get all relationships for a contact."""
    return json.dumps(SmokeBallClient().get_contact_relations(contact_id), indent=2)


@mcp.tool()
def get_contact_relation(contact_id: str, relation_id: str) -> str:
    """Get a specific relationship for a contact."""
    return json.dumps(
        SmokeBallClient().get_contact_relation(contact_id, relation_id), indent=2
    )


@mcp.tool()
def create_contact_relation(
    contact_id: str, related_contact_id: str, relation_type: str = ""
) -> str:
    """Create a relationship between two contacts."""
    fields = {"relatedContactId": related_contact_id}
    if relation_type:
        fields["relationType"] = relation_type
    return json.dumps(
        SmokeBallClient().create_contact_relation(contact_id, **fields), indent=2
    )


@mcp.tool()
def update_contact_relation(
    contact_id: str, relation_id: str, relation_type: str
) -> str:
    """Update a contact relationship type."""
    return json.dumps(
        SmokeBallClient().update_contact_relation(
            contact_id, relation_id, relationType=relation_type
        ),
        indent=2,
    )


@mcp.tool()
def delete_contact_relation(contact_id: str, relation_id: str) -> str:
    """Delete a relationship from a contact."""
    return json.dumps(
        SmokeBallClient().delete_contact_relation(contact_id, relation_id), indent=2
    )


@mcp.tool()
def get_contact_tags(contact_id: str) -> str:
    """Get tags on a contact."""
    return json.dumps(SmokeBallClient().get_contact_tags(contact_id), indent=2)


@mcp.tool()
def add_contact_tags(contact_id: str, tags_csv: str) -> str:
    """Add tags to a contact. tags_csv: comma-separated tag strings."""
    tags = [t.strip() for t in tags_csv.split(",") if t.strip()]
    return json.dumps(SmokeBallClient().add_contact_tags(contact_id, tags), indent=2)


@mcp.tool()
def remove_contact_tags(contact_id: str, tag_id: str) -> str:
    """Remove a tag from a contact. tag_id: the ID of the tag to remove."""
    return json.dumps(
        SmokeBallClient().remove_contact_tags(contact_id, tag_id), indent=2
    )


# ── Matters ───────────────────────────────────────────────────────────────────


@mcp.tool()
def list_matters(limit: int = 50, offset: int = 0) -> str:
    """List matters with offset pagination."""
    return json.dumps(
        SmokeBallClient().list_matters(limit=limit, offset=offset), indent=2
    )


@mcp.tool()
def get_matter(matter_id: str) -> str:
    """Get a matter by ID."""
    return json.dumps(SmokeBallClient().get_matter(matter_id), indent=2)


@mcp.tool()
def create_matter(
    matter_type_id: str,
    client_ids_csv: str,
    number: str = "",
    description: str = "",
    status: str = "",
) -> str:
    """Create a matter.
    matter_type_id: from list_matter_types (required).
    client_ids_csv: comma-separated contact IDs to set as clients (required).
    number: optional matter reference number."""
    client_ids = [c.strip() for c in client_ids_csv.split(",") if c.strip()]
    return json.dumps(
        SmokeBallClient().create_matter(
            number=number,
            matter_type_id=matter_type_id,
            client_ids=client_ids,
            description=description,
            status=status,
        ),
        indent=2,
    )


@mcp.tool()
def update_matter(
    matter_id: str, name: str = "", status: str = "", description: str = ""
) -> str:
    """Update a matter's name, status, or description."""
    fields = {}
    if name:
        fields["name"] = name
    if status:
        fields["status"] = status
    if description:
        fields["description"] = description
    return json.dumps(SmokeBallClient().update_matter(matter_id, **fields), indent=2)


@mcp.tool()
def patch_matter(matter_id: str, status: str = "", stage_id: str = "") -> str:
    """Partially update a matter status or stage (PATCH). Use update_matter for name/description."""
    fields = {}
    if status:
        fields["status"] = status
    if stage_id:
        fields["stageId"] = stage_id
    return json.dumps(SmokeBallClient().patch_matter(matter_id, **fields), indent=2)


@mcp.tool()
def delete_matter(matter_id: str) -> str:
    """Delete a matter by ID."""
    return json.dumps(SmokeBallClient().delete_matter(matter_id), indent=2)


@mcp.tool()
def get_matter_billing_configuration(matter_id: str) -> str:
    """Get billing configuration for a matter."""
    return json.dumps(
        SmokeBallClient().get_matter_billing_configuration(matter_id), indent=2
    )


@mcp.tool()
def update_matter_billing_configuration(
    matter_id: str, billing_type: str = "", rate: float = 0.0
) -> str:
    """Update billing configuration for a matter. billing_type: Hourly | Fixed | Contingency."""
    fields = {}
    if billing_type:
        fields["billingType"] = billing_type
    if rate:
        fields["rate"] = rate
    return json.dumps(
        SmokeBallClient().update_matter_billing_configuration(matter_id, **fields),
        indent=2,
    )


@mcp.tool()
def get_matter_tags(matter_id: str) -> str:
    """Get tags on a matter."""
    return json.dumps(SmokeBallClient().get_matter_tags(matter_id), indent=2)


@mcp.tool()
def add_matter_tags(matter_id: str, tags_json: str) -> str:
    """Add tags to a matter. tags_json: JSON array of tag objects, each with keys:
    id (str), name (str), color (str), type (str).
    Example: [{"id": "abc", "name": "Urgent", "color": "red", "type": "custom"}]"""
    try:
        tags = json.loads(tags_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid tags_json: {e}"})
    if not isinstance(tags, list):
        return json.dumps({"error": "tags_json must be a JSON array"})
    return json.dumps(SmokeBallClient().add_matter_tags(matter_id, tags), indent=2)


@mcp.tool()
def remove_matter_tags(matter_id: str, tag_id: str) -> str:
    """Remove a tag from a matter. tag_id: the ID of the tag to remove."""
    return json.dumps(SmokeBallClient().remove_matter_tags(matter_id, tag_id), indent=2)


# ── Leads ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_leads(limit: int = 50, offset: int = 0) -> str:
    """List leads (potential new clients/matters)."""
    return json.dumps(
        SmokeBallClient().list_leads(limit=limit, offset=offset), indent=2
    )


@mcp.tool()
def get_lead(lead_id: str) -> str:
    """Get a lead by ID."""
    return json.dumps(SmokeBallClient().get_lead(lead_id), indent=2)


@mcp.tool()
def create_lead(matter_type_id: str = "", client_id: str = "") -> str:
    """Create a lead (created as a matter with isLead=true via POST /matters).
    matter_type_id: from list_matter_types.
    client_id: existing contact ID to associate as client."""
    return json.dumps(
        SmokeBallClient().create_lead(
            matter_type_id=matter_type_id,
            client_id=client_id,
        ),
        indent=2,
    )


@mcp.tool()
def update_lead(lead_id: str, status: str = "", notes: str = "") -> str:
    """Update a lead's status or notes."""
    fields = {}
    if status:
        fields["status"] = status
    if notes:
        fields["notes"] = notes
    return json.dumps(SmokeBallClient().update_lead(lead_id, **fields), indent=2)


@mcp.tool()
def patch_lead(lead_id: str, status: str = "", assigned_to_id: str = "") -> str:
    """Partially update a lead status or assignment (PATCH). Use update_lead for notes."""
    fields = {}
    if status:
        fields["status"] = status
    if assigned_to_id:
        fields["assignedToId"] = assigned_to_id
    return json.dumps(SmokeBallClient().patch_lead(lead_id, **fields), indent=2)


@mcp.tool()
def delete_lead(lead_id: str) -> str:
    """Delete a lead by ID."""
    return json.dumps(SmokeBallClient().delete_lead(lead_id), indent=2)


# ── Matter Types ──────────────────────────────────────────────────────────────


@mcp.tool()
def list_matter_types(limit: int = 100, offset: int = 0) -> str:
    """List all matter types configured for this firm."""
    return json.dumps(
        SmokeBallClient().list_matter_types(limit=limit, offset=offset), indent=2
    )


@mcp.tool()
def get_matter_type(matter_type_id: str) -> str:
    """Get a matter type by ID."""
    return json.dumps(SmokeBallClient().get_matter_type(matter_type_id), indent=2)


@mcp.tool()
def list_matter_type_categories() -> str:
    """List all matter type categories."""
    return json.dumps(SmokeBallClient().list_matter_type_categories(), indent=2)


# ── Stages ────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_stage_sets() -> str:
    """List all stage sets (workflow stage groups)."""
    return json.dumps(SmokeBallClient().list_stage_sets(), indent=2)


@mcp.tool()
def get_stage_set(stage_set_id: str) -> str:
    """Get a specific stage set by ID."""
    return json.dumps(SmokeBallClient().get_stage_set(stage_set_id), indent=2)


@mcp.tool()
def get_stage_in_set(stage_set_id: str, stage_id: str) -> str:
    """Get a specific stage within a stage set."""
    return json.dumps(
        SmokeBallClient().get_stage_in_set(stage_set_id, stage_id), indent=2
    )


@mcp.tool()
def list_matter_stage_mappings() -> str:
    """List all matter-to-stage mappings."""
    return json.dumps(SmokeBallClient().list_matter_stage_mappings(), indent=2)


@mcp.tool()
def get_matter_stage(matter_id: str) -> str:
    """Get the current stage of a matter."""
    return json.dumps(SmokeBallClient().get_matter_stage(matter_id), indent=2)


# ── Roles ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_roles_on_matter(matter_id: str) -> str:
    """List all roles assigned to a matter."""
    return json.dumps(SmokeBallClient().get_roles_on_matter(matter_id), indent=2)


@mcp.tool()
def get_role_on_matter(matter_id: str, role_id: str) -> str:
    """Get a specific role on a matter."""
    return json.dumps(
        SmokeBallClient().get_role_on_matter(matter_id, role_id), indent=2
    )


@mcp.tool()
def add_role_to_matter(matter_id: str, role_name: str, contact_id: str = "") -> str:
    """Add a role to a matter. contact_id: associate a contact to this role."""
    fields = {"roleName": role_name}
    if contact_id:
        fields["contactId"] = contact_id
    return json.dumps(
        SmokeBallClient().add_role_to_matter(matter_id, **fields), indent=2
    )


@mcp.tool()
def update_role_on_matter(matter_id: str, role_id: str, contact_id: str = "") -> str:
    """Update a role on a matter."""
    fields = {}
    if contact_id:
        fields["contactId"] = contact_id
    return json.dumps(
        SmokeBallClient().update_role_on_matter(matter_id, role_id, **fields), indent=2
    )


@mcp.tool()
def remove_role_from_matter(matter_id: str, role_id: str) -> str:
    """Remove a role from a matter."""
    return json.dumps(
        SmokeBallClient().remove_role_from_matter(matter_id, role_id), indent=2
    )


# ── Relationships ─────────────────────────────────────────────────────────────


@mcp.tool()
def get_relationships_on_matter(matter_id: str) -> str:
    """Get all contact relationships on a matter."""
    return json.dumps(
        SmokeBallClient().get_relationships_on_matter(matter_id), indent=2
    )


@mcp.tool()
def get_relationship_on_role(matter_id: str, role_id: str) -> str:
    """Get the contact relationship for a specific role on a matter."""
    return json.dumps(
        SmokeBallClient().get_relationship_on_role(matter_id, role_id), indent=2
    )


@mcp.tool()
def add_relationship_to_role(
    matter_id: str, role_id: str, contact_id: str, relation_type: str = ""
) -> str:
    """Add a contact relationship to a role on a matter."""
    fields = {"contactId": contact_id}
    if relation_type:
        fields["relationType"] = relation_type
    return json.dumps(
        SmokeBallClient().add_relationship_to_role(matter_id, role_id, **fields),
        indent=2,
    )


@mcp.tool()
def update_relationship(
    matter_id: str, role_id: str, relationship_id: str, relation_type: str
) -> str:
    """Update a contact relationship on a matter role."""
    return json.dumps(
        SmokeBallClient().update_relationship(
            matter_id, role_id, relationship_id, relationType=relation_type
        ),
        indent=2,
    )


@mcp.tool()
def remove_relationship_from_role(
    matter_id: str, role_id: str, relationship_id: str
) -> str:
    """Remove a contact relationship from a role on a matter."""
    return json.dumps(
        SmokeBallClient().remove_relationship_from_role(
            matter_id, role_id, relationship_id
        ),
        indent=2,
    )


# ── Tasks ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_tasks(matter_id: str = "", limit: int = 50, offset: int = 0) -> str:
    """List tasks. Filter by matter_id to get matter-specific tasks."""
    return json.dumps(
        SmokeBallClient().get_tasks(
            matter_id=matter_id or None, limit=limit, offset=offset
        ),
        indent=2,
    )


@mcp.tool()
def get_task(task_id: str) -> str:
    """Get a task by ID."""
    return json.dumps(SmokeBallClient().get_task(task_id), indent=2)


@mcp.tool()
def create_task(
    name: str,
    matter_id: str = "",
    due_date: str = "",
    assigned_to_id: str = "",
    notes: str = "",
) -> str:
    """Create a task. due_date: ISO 8601 (YYYY-MM-DD). assigned_to_id: staff ID."""
    fields = {"name": name}
    if matter_id:
        fields["matterId"] = matter_id
    if due_date:
        fields["dueDate"] = due_date
    if assigned_to_id:
        fields["assignedToId"] = assigned_to_id
    if notes:
        fields["notes"] = notes
    return json.dumps(SmokeBallClient().create_task(**fields), indent=2)


@mcp.tool()
def update_task(
    task_id: str,
    name: str = "",
    due_date: str = "",
    completed_str: str = "",
    notes: str = "",
) -> str:
    """Update a task. completed_str: 'true' to mark done, 'false' to unmark."""
    fields = {}
    if name:
        fields["name"] = name
    if due_date:
        fields["dueDate"] = due_date
    if completed_str.lower() in ("true", "false"):
        fields["completed"] = completed_str.lower() == "true"
    if notes:
        fields["notes"] = notes
    return json.dumps(SmokeBallClient().update_task(task_id, **fields), indent=2)


@mcp.tool()
def delete_task(task_id: str) -> str:
    """Delete a task by ID."""
    return json.dumps(SmokeBallClient().delete_task(task_id), indent=2)


@mcp.tool()
def get_subtasks(task_id: str) -> str:
    """Get all subtasks for a task."""
    return json.dumps(SmokeBallClient().get_subtasks(task_id), indent=2)


@mcp.tool()
def get_subtask(task_id: str, subtask_id: str) -> str:
    """Get a specific subtask."""
    return json.dumps(SmokeBallClient().get_subtask(task_id, subtask_id), indent=2)


@mcp.tool()
def create_subtask(task_id: str, name: str, due_date: str = "") -> str:
    """Create a subtask under a task."""
    fields = {"name": name}
    if due_date:
        fields["dueDate"] = due_date
    return json.dumps(SmokeBallClient().create_subtask(task_id, **fields), indent=2)


@mcp.tool()
def update_subtask(
    task_id: str, subtask_id: str, name: str = "", completed_str: str = ""
) -> str:
    """Update a subtask. completed_str: 'true' to mark done, 'false' to unmark."""
    fields = {}
    if name:
        fields["name"] = name
    if completed_str.lower() in ("true", "false"):
        fields["completed"] = completed_str.lower() == "true"
    return json.dumps(
        SmokeBallClient().update_subtask(task_id, subtask_id, **fields), indent=2
    )


@mcp.tool()
def delete_subtask(task_id: str, subtask_id: str) -> str:
    """Delete a subtask."""
    return json.dumps(SmokeBallClient().delete_subtask(task_id, subtask_id), indent=2)


@mcp.tool()
def get_task_documents(task_id: str) -> str:
    """Get documents attached to a task."""
    return json.dumps(SmokeBallClient().get_task_documents(task_id), indent=2)


@mcp.tool()
def get_task_document(task_id: str, document_id: str) -> str:
    """Get a specific document attached to a task."""
    return json.dumps(
        SmokeBallClient().get_task_document(task_id, document_id), indent=2
    )


@mcp.tool()
def create_task_document(task_id: str, file_id: str, name: str = "") -> str:
    """Attach a file to a task. file_id: from files API."""
    fields = {"fileId": file_id}
    if name:
        fields["name"] = name
    return json.dumps(
        SmokeBallClient().create_task_document(task_id, **fields), indent=2
    )


@mcp.tool()
def delete_task_document(task_id: str, document_id: str) -> str:
    """Remove a document attachment from a task."""
    return json.dumps(
        SmokeBallClient().delete_task_document(task_id, document_id), indent=2
    )


# ── Events ────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_events(matter_id: str = "", limit: int = 50, offset: int = 0) -> str:
    """List calendar events. Filter by matter_id for matter-specific events."""
    return json.dumps(
        SmokeBallClient().get_events(
            matter_id=matter_id or None, limit=limit, offset=offset
        ),
        indent=2,
    )


@mcp.tool()
def get_event(event_id: str) -> str:
    """Get a calendar event by ID."""
    return json.dumps(SmokeBallClient().get_event(event_id), indent=2)


@mcp.tool()
def create_event(
    name: str,
    start_date: str,
    end_date: str = "",
    matter_id: str = "",
    location: str = "",
    notes: str = "",
) -> str:
    """Create a calendar event. start_date/end_date: ISO 8601 datetime."""
    fields = {"name": name, "startDate": start_date}
    if end_date:
        fields["endDate"] = end_date
    if matter_id:
        fields["matterId"] = matter_id
    if location:
        fields["location"] = location
    if notes:
        fields["notes"] = notes
    return json.dumps(SmokeBallClient().create_event(**fields), indent=2)


@mcp.tool()
def update_event(
    event_id: str,
    name: str = "",
    start_date: str = "",
    end_date: str = "",
    location: str = "",
) -> str:
    """Update a calendar event."""
    fields = {}
    if name:
        fields["name"] = name
    if start_date:
        fields["startDate"] = start_date
    if end_date:
        fields["endDate"] = end_date
    if location:
        fields["location"] = location
    return json.dumps(SmokeBallClient().update_event(event_id, **fields), indent=2)


@mcp.tool()
def delete_event(event_id: str) -> str:
    """Delete a calendar event by ID."""
    return json.dumps(SmokeBallClient().delete_event(event_id), indent=2)


@mcp.tool()
def get_event_reminders(event_id: str) -> str:
    """Get all reminders for a calendar event."""
    return json.dumps(SmokeBallClient().get_event_reminders(event_id), indent=2)


@mcp.tool()
def create_event_reminder(
    event_id: str, minutes_before: int, reminder_type: str = "Notification"
) -> str:
    """Create a reminder for an event. reminder_type: Notification | Email."""
    return json.dumps(
        SmokeBallClient().create_event_reminder(
            event_id, minutesBefore=minutes_before, reminderType=reminder_type
        ),
        indent=2,
    )


@mcp.tool()
def update_event_reminder(event_id: str, reminder_id: str, minutes_before: int) -> str:
    """Update an event reminder's lead time."""
    return json.dumps(
        SmokeBallClient().update_event_reminder(
            event_id, reminder_id, minutesBefore=minutes_before
        ),
        indent=2,
    )


@mcp.tool()
def delete_event_reminder(event_id: str, reminder_id: str) -> str:
    """Delete an event reminder."""
    return json.dumps(
        SmokeBallClient().delete_event_reminder(event_id, reminder_id), indent=2
    )


# ── Memos ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_memos_on_matter(matter_id: str, limit: int = 50, offset: int = 0) -> str:
    """List memos (notes) on a matter."""
    return json.dumps(
        SmokeBallClient().get_memos_on_matter(matter_id, limit=limit, offset=offset),
        indent=2,
    )


@mcp.tool()
def get_memo(memo_id: str) -> str:
    """Get a memo by ID."""
    return json.dumps(SmokeBallClient().get_memo(memo_id), indent=2)


@mcp.tool()
def create_memo(matter_id: str, content: str, subject: str = "") -> str:
    """Create a memo (note) on a matter."""
    fields = {"content": content}
    if subject:
        fields["subject"] = subject
    return json.dumps(SmokeBallClient().create_memo(matter_id, **fields), indent=2)


@mcp.tool()
def update_memo(memo_id: str, content: str = "", subject: str = "") -> str:
    """Update a memo's content or subject."""
    fields = {}
    if content:
        fields["content"] = content
    if subject:
        fields["subject"] = subject
    return json.dumps(SmokeBallClient().update_memo(memo_id, **fields), indent=2)


@mcp.tool()
def delete_memo(memo_id: str) -> str:
    """Delete a memo by ID."""
    return json.dumps(SmokeBallClient().delete_memo(memo_id), indent=2)


# ── Fees (Time Entries) ────────────────────────────────────────────────────────


@mcp.tool()
def list_fees(matter_id: str = "", limit: int = 50, offset: int = 0) -> str:
    """List fee entries (billable time). Filter by matter_id for matter-specific fees."""
    return json.dumps(
        SmokeBallClient().get_fees(
            matter_id=matter_id or None, limit=limit, offset=offset
        ),
        indent=2,
    )


@mcp.tool()
def get_fee(fee_id: str) -> str:
    """Get a fee entry by ID."""
    return json.dumps(SmokeBallClient().get_fee(fee_id), indent=2)


@mcp.tool()
def create_fee(
    matter_id: str,
    staff_id: str,
    date: str,
    duration_minutes: int,
    description: str = "",
    activity_code_id: str = "",
    rate: float = 0.0,
    billable: str = "true",
) -> str:
    """Create a fee (time entry). date: YYYY-MM-DD. duration_minutes: time spent.
    billable: 'true' (default) or 'false'."""
    fields = {
        "matterId": matter_id,
        "staffId": staff_id,
        "date": date,
        "durationMinutes": duration_minutes,
        "billable": billable.lower() == "true",
    }
    if description:
        fields["description"] = description
    if activity_code_id:
        fields["activityCodeId"] = activity_code_id
    if rate:
        fields["rate"] = rate
    return json.dumps(SmokeBallClient().create_fee(**fields), indent=2)


@mcp.tool()
def update_fee(
    fee_id: str,
    description: str = "",
    duration_minutes: int = 0,
    billable: str = "",
    rate: float = 0.0,
) -> str:
    """Update a fee entry. billable: 'true' or 'false' to set; leave empty to skip."""
    fields = {}
    if description:
        fields["description"] = description
    if duration_minutes:
        fields["durationMinutes"] = duration_minutes
    if billable.lower() in ("true", "false"):
        fields["billable"] = billable.lower() == "true"
    if rate:
        fields["rate"] = rate
    return json.dumps(SmokeBallClient().update_fee(fee_id, **fields), indent=2)


@mcp.tool()
def patch_fee(fee_id: str, billable: str = "", billed: str = "") -> str:
    """Toggle a fee entry's billable or billed state (PATCH). Use 'true' or 'false'."""
    fields = {}
    if billable.lower() in ("true", "false"):
        fields["billable"] = billable.lower() == "true"
    if billed.lower() in ("true", "false"):
        fields["billed"] = billed.lower() == "true"
    return json.dumps(SmokeBallClient().patch_fee(fee_id, **fields), indent=2)


@mcp.tool()
def delete_fee(fee_id: str) -> str:
    """Delete a fee entry by ID."""
    return json.dumps(SmokeBallClient().delete_fee(fee_id), indent=2)


# ── Expenses ──────────────────────────────────────────────────────────────────


@mcp.tool()
def list_expenses(matter_id: str = "", limit: int = 50, offset: int = 0) -> str:
    """List expense entries. Filter by matter_id for matter-specific expenses."""
    return json.dumps(
        SmokeBallClient().get_expenses(
            matter_id=matter_id or None, limit=limit, offset=offset
        ),
        indent=2,
    )


@mcp.tool()
def get_expense(expense_id: str) -> str:
    """Get an expense entry by ID."""
    return json.dumps(SmokeBallClient().get_expense(expense_id), indent=2)


@mcp.tool()
def create_expense(
    matter_id: str,
    date: str,
    amount: float,
    description: str = "",
    billable: str = "true",
    activity_code_id: str = "",
) -> str:
    """Create an expense entry. date: YYYY-MM-DD. amount: dollar value.
    billable: 'true' (default) or 'false'."""
    fields = {
        "matterId": matter_id,
        "date": date,
        "amount": amount,
        "billable": billable.lower() == "true",
    }
    if description:
        fields["description"] = description
    if activity_code_id:
        fields["activityCodeId"] = activity_code_id
    return json.dumps(SmokeBallClient().create_expense(**fields), indent=2)


@mcp.tool()
def update_expense(
    expense_id: str, description: str = "", amount: float = 0.0, billable: str = ""
) -> str:
    """Update an expense entry. billable: 'true' or 'false' to set; leave empty to skip."""
    fields = {}
    if description:
        fields["description"] = description
    if amount:
        fields["amount"] = amount
    if billable.lower() in ("true", "false"):
        fields["billable"] = billable.lower() == "true"
    return json.dumps(SmokeBallClient().update_expense(expense_id, **fields), indent=2)


@mcp.tool()
def patch_expense(expense_id: str, billable: str = "", billed: str = "") -> str:
    """Toggle an expense entry's billable or billed state (PATCH). Use 'true' or 'false'."""
    fields = {}
    if billable.lower() in ("true", "false"):
        fields["billable"] = billable.lower() == "true"
    if billed.lower() in ("true", "false"):
        fields["billed"] = billed.lower() == "true"
    return json.dumps(SmokeBallClient().patch_expense(expense_id, **fields), indent=2)


@mcp.tool()
def delete_expense(expense_id: str) -> str:
    """Delete an expense entry by ID."""
    return json.dumps(SmokeBallClient().delete_expense(expense_id), indent=2)


# ── Invoices ──────────────────────────────────────────────────────────────────


@mcp.tool()
def list_invoices(matter_id: str = "", limit: int = 50, offset: int = 0) -> str:
    """List invoices. Filter by matter_id for matter-specific invoices."""
    return json.dumps(
        SmokeBallClient().get_invoices(
            matter_id=matter_id or None, limit=limit, offset=offset
        ),
        indent=2,
    )


@mcp.tool()
def get_invoice(invoice_id: str) -> str:
    """Get an invoice by ID."""
    return json.dumps(SmokeBallClient().get_invoice(invoice_id), indent=2)


@mcp.tool()
def get_invoice_download_url(invoice_id: str) -> str:
    """Get a download URL for an invoice PDF."""
    return json.dumps(SmokeBallClient().get_invoice_download_url(invoice_id), indent=2)


# ── Activity Codes ────────────────────────────────────────────────────────────


@mcp.tool()
def list_activity_codes(limit: int = 100, offset: int = 0) -> str:
    """List billing activity codes configured for this firm."""
    return json.dumps(
        SmokeBallClient().get_activity_codes(limit=limit, offset=offset), indent=2
    )


@mcp.tool()
def get_activity_code(code_id: str) -> str:
    """Get an activity code by ID."""
    return json.dumps(SmokeBallClient().get_activity_code(code_id), indent=2)


@mcp.tool()
def create_activity_code(code: str, description: str, rate: float = 0.0) -> str:
    """Create a billing activity code."""
    fields: dict[str, object] = {"code": code, "description": description}
    if rate:
        fields["rate"] = rate
    return json.dumps(SmokeBallClient().create_activity_code(**fields), indent=2)


@mcp.tool()
def update_activity_code(
    code_id: str, code: str = "", description: str = "", rate: float = 0.0
) -> str:
    """Update an activity code."""
    fields = {}
    if code:
        fields["code"] = code
    if description:
        fields["description"] = description
    if rate:
        fields["rate"] = rate
    return json.dumps(
        SmokeBallClient().update_activity_code(code_id, **fields), indent=2
    )


@mcp.tool()
def delete_activity_code(code_id: str) -> str:
    """Delete an activity code by ID."""
    return json.dumps(SmokeBallClient().delete_activity_code(code_id), indent=2)


# ── Bank Accounts ─────────────────────────────────────────────────────────────


@mcp.tool()
def list_bank_accounts(limit: int = 50, offset: int = 0) -> str:
    """List bank accounts (trust, operating) for this firm."""
    return json.dumps(
        SmokeBallClient().get_bank_accounts(limit=limit, offset=offset), indent=2
    )


@mcp.tool()
def get_bank_account(account_id: str) -> str:
    """Get a bank account by ID."""
    return json.dumps(SmokeBallClient().get_bank_account(account_id), indent=2)


@mcp.tool()
def get_bank_account_matter_balances(account_id: str) -> str:
    """Get per-matter balances for a bank account (trust accounting)."""
    return json.dumps(
        SmokeBallClient().get_bank_account_matter_balances(account_id), indent=2
    )


@mcp.tool()
def get_protected_bank_account_balance(account_id: str) -> str:
    """Get the protected (reserved) balance for a bank account."""
    return json.dumps(
        SmokeBallClient().get_protected_bank_account_balance(account_id), indent=2
    )


@mcp.tool()
def list_transactions(account_id: str, limit: int = 50, offset: int = 0) -> str:
    """List transactions for a bank account."""
    return json.dumps(
        SmokeBallClient().get_transactions(account_id, limit=limit, offset=offset),
        indent=2,
    )


@mcp.tool()
def get_transaction(account_id: str, transaction_id: str) -> str:
    """Get a specific transaction from a bank account."""
    return json.dumps(
        SmokeBallClient().get_transaction(account_id, transaction_id), indent=2
    )


@mcp.tool()
def create_transaction(
    account_id: str,
    matter_id: str,
    amount: float,
    description: str = "",
    transaction_type: str = "",
) -> str:
    """Create a bank account transaction. amount: positive for deposit, negative for withdrawal."""
    fields = {"matterId": matter_id, "amount": amount}
    if description:
        fields["description"] = description
    if transaction_type:
        fields["transactionType"] = transaction_type
    return json.dumps(
        SmokeBallClient().create_transaction(account_id, **fields), indent=2
    )


@mcp.tool()
def create_requisition(
    account_id: str,
    matter_id: str,
    amount: float,
    payee: str = "",
    description: str = "",
) -> str:
    """Create a trust fund requisition (draw-down request)."""
    fields = {"matterId": matter_id, "amount": amount}
    if payee:
        fields["payee"] = payee
    if description:
        fields["description"] = description
    return json.dumps(
        SmokeBallClient().create_requisition(account_id, **fields), indent=2
    )


@mcp.tool()
def protect_funds(
    account_id: str, matter_id: str, amount: float, reason: str = ""
) -> str:
    """Protect (reserve) funds in a trust account for a matter."""
    fields = {"matterId": matter_id, "amount": amount}
    if reason:
        fields["reason"] = reason
    return json.dumps(SmokeBallClient().protect_funds(account_id, **fields), indent=2)


@mcp.tool()
def unprotect_funds(account_id: str, matter_id: str, amount: float) -> str:
    """Release protected (reserved) funds back to available balance."""
    return json.dumps(
        SmokeBallClient().unprotect_funds(
            account_id, matterId=matter_id, amount=amount
        ),
        indent=2,
    )


# ── Files ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_files_on_matter(matter_id: str, limit: int = 50, offset: int = 0) -> str:
    """List files attached to a matter."""
    return json.dumps(
        SmokeBallClient().get_files_on_matter(matter_id, limit=limit, offset=offset),
        indent=2,
    )


@mcp.tool()
def get_file(file_id: str) -> str:
    """Get file metadata by ID."""
    return json.dumps(SmokeBallClient().get_file(file_id), indent=2)


@mcp.tool()
def get_file_download_url(file_id: str) -> str:
    """Get a pre-signed download URL for a file."""
    return json.dumps(SmokeBallClient().get_file_download_url(file_id), indent=2)


@mcp.tool()
def get_file_upload_url(file_id: str) -> str:
    """Get a pre-signed upload URL for a file version."""
    return json.dumps(SmokeBallClient().get_file_upload_url(file_id), indent=2)


@mcp.tool()
def get_file_history(matter_id: str, limit: int = 50, offset: int = 0) -> str:
    """Get file version history for a matter."""
    return json.dumps(
        SmokeBallClient().get_file_history(matter_id, limit=limit, offset=offset),
        indent=2,
    )


@mcp.tool()
def add_file_to_matter(matter_id: str, name: str, folder_id: str = "") -> str:
    """Register a new file on a matter (get upload URL separately)."""
    fields = {"name": name}
    if folder_id:
        fields["folderId"] = folder_id
    return json.dumps(
        SmokeBallClient().add_file_to_matter(matter_id, **fields), indent=2
    )


@mcp.tool()
def add_files_to_matter_batch(matter_id: str, files_csv: str) -> str:
    """Add multiple files to a matter in one request. files_csv: comma-separated file names."""
    files = [{"name": t.strip()} for t in files_csv.split(",") if t.strip()]
    return json.dumps(SmokeBallClient().add_files_to_matter(matter_id, files), indent=2)


@mcp.tool()
def patch_file(file_id: str, name: str = "", folder_id: str = "") -> str:
    """Update file metadata (name, folder)."""
    fields = {}
    if name:
        fields["name"] = name
    if folder_id:
        fields["folderId"] = folder_id
    return json.dumps(SmokeBallClient().patch_file(file_id, **fields), indent=2)


@mcp.tool()
def delete_file(file_id: str) -> str:
    """Delete a file by ID."""
    return json.dumps(SmokeBallClient().delete_file(file_id), indent=2)


@mcp.tool()
def create_file_preview_request(file_id: str) -> str:
    """Request generation of a preview (thumbnail/rendition) for a file."""
    return json.dumps(SmokeBallClient().create_preview_request(file_id), indent=2)


@mcp.tool()
def get_file_preview_info(file_id: str) -> str:
    """Get preview info (status and URL) for a file."""
    return json.dumps(SmokeBallClient().get_preview_info(file_id), indent=2)


@mcp.tool()
def get_file_preview_info_by_version(file_id: str, version_id: str) -> str:
    """Get preview info for a specific version of a file."""
    return json.dumps(
        SmokeBallClient().get_preview_info_by_version(file_id, version_id), indent=2
    )


# ── Folders ───────────────────────────────────────────────────────────────────


@mcp.tool()
def get_root_folder_contents(matter_id: str) -> str:
    """Get the root folder contents for a matter."""
    return json.dumps(SmokeBallClient().get_root_folder_contents(matter_id), indent=2)


@mcp.tool()
def get_folder_contents(matter_id: str, folder_id: str) -> str:
    """Get the contents of a specific folder on a matter."""
    return json.dumps(
        SmokeBallClient().get_folder_contents(matter_id, folder_id), indent=2
    )


@mcp.tool()
def get_folder_path_hierarchy(matter_id: str, folder_id: str) -> str:
    """Get the full path hierarchy (breadcrumb) to a folder."""
    return json.dumps(
        SmokeBallClient().get_folder_path_hierarchy(matter_id, folder_id), indent=2
    )


@mcp.tool()
def get_folder_history(matter_id: str, limit: int = 50, offset: int = 0) -> str:
    """Get folder activity history for a matter."""
    return json.dumps(
        SmokeBallClient().get_folder_history(matter_id, limit=limit, offset=offset),
        indent=2,
    )


@mcp.tool()
def create_folder(matter_id: str, name: str, parent_folder_id: str = "") -> str:
    """Create a folder in a matter. parent_folder_id: omit for root."""
    fields = {"name": name}
    if parent_folder_id:
        fields["parentFolderId"] = parent_folder_id
    return json.dumps(SmokeBallClient().create_folder(matter_id, **fields), indent=2)


@mcp.tool()
def update_folder(folder_id: str, name: str) -> str:
    """Rename a folder."""
    return json.dumps(SmokeBallClient().update_folder(folder_id, name=name), indent=2)


@mcp.tool()
def patch_folder(folder_id: str, parent_folder_id: str = "") -> str:
    """Move a folder to a different parent."""
    fields = {}
    if parent_folder_id:
        fields["parentFolderId"] = parent_folder_id
    return json.dumps(SmokeBallClient().patch_folder(folder_id, **fields), indent=2)


@mcp.tool()
def delete_folder(folder_id: str) -> str:
    """Delete a folder by ID."""
    return json.dumps(SmokeBallClient().delete_folder(folder_id), indent=2)


# ── Archive ───────────────────────────────────────────────────────────────────


@mcp.tool()
def get_matter_archive(matter_id: str) -> str:
    """Get archive status and metadata for a matter."""
    return json.dumps(SmokeBallClient().get_matter_archive(matter_id), indent=2)


@mcp.tool()
def archive_matter(matter_id: str, reason: str = "") -> str:
    """Archive a matter."""
    fields: dict[str, object] = {"archived": True}
    if reason:
        fields["reason"] = reason
    return json.dumps(
        SmokeBallClient().update_matter_archive(matter_id, **fields), indent=2
    )


@mcp.tool()
def unarchive_matter(matter_id: str) -> str:
    """Unarchive a matter."""
    return json.dumps(
        SmokeBallClient().update_matter_archive(matter_id, archived=False), indent=2
    )


@mcp.tool()
def patch_matter_archive(
    matter_id: str, retention_policy: str = "", destruction_date: str = ""
) -> str:
    """Update archive metadata fields on a matter (PATCH). destruction_date: YYYY-MM-DD."""
    fields = {}
    if retention_policy:
        fields["retentionPolicy"] = retention_policy
    if destruction_date:
        fields["destructionDate"] = destruction_date
    return json.dumps(
        SmokeBallClient().patch_matter_archive(matter_id, **fields), indent=2
    )


# ── Referral Types ────────────────────────────────────────────────────────────


@mcp.tool()
def list_referral_types(limit: int = 100, offset: int = 0) -> str:
    """List referral source types configured for this firm."""
    return json.dumps(
        SmokeBallClient().get_referral_types(limit=limit, offset=offset), indent=2
    )


@mcp.tool()
def get_referral_type(referral_type_id: str) -> str:
    """Get a referral type by ID."""
    return json.dumps(SmokeBallClient().get_referral_type(referral_type_id), indent=2)


# ── Authorization ─────────────────────────────────────────────────────────────


@mcp.tool()
def list_authorization_groups() -> str:
    """List all authorization groups for this firm."""
    return json.dumps(SmokeBallClient().get_authorization_groups(), indent=2)


@mcp.tool()
def get_authorization_group(group_id: str) -> str:
    """Get an authorization group by ID."""
    return json.dumps(SmokeBallClient().get_authorization_group(group_id), indent=2)


@mcp.tool()
def create_authorization_group(name: str, description: str = "") -> str:
    """Create an authorization group."""
    fields = {"name": name}
    if description:
        fields["description"] = description
    return json.dumps(SmokeBallClient().create_authorization_group(**fields), indent=2)


@mcp.tool()
def update_authorization_group(
    group_id: str, name: str = "", description: str = ""
) -> str:
    """Update an authorization group."""
    fields = {}
    if name:
        fields["name"] = name
    if description:
        fields["description"] = description
    return json.dumps(
        SmokeBallClient().update_authorization_group(group_id, **fields), indent=2
    )


@mcp.tool()
def delete_authorization_group(group_id: str) -> str:
    """Delete an authorization group by ID."""
    return json.dumps(SmokeBallClient().delete_authorization_group(group_id), indent=2)


@mcp.tool()
def get_authorization_policy(reference: str) -> str:
    """Get an authorization policy by reference."""
    return json.dumps(SmokeBallClient().get_authorization_policy(reference), indent=2)


@mcp.tool()
def create_authorization_policy(name: str, permissions_csv: str) -> str:
    """Create an authorization policy. permissions_csv: comma-separated permission strings."""
    permissions = [t.strip() for t in permissions_csv.split(",") if t.strip()]
    return json.dumps(
        SmokeBallClient().create_authorization_policy(
            name=name, permissions=permissions
        ),
        indent=2,
    )


@mcp.tool()
def update_authorization_policy(
    reference: str, name: str = "", permissions_csv: str = ""
) -> str:
    """Update an authorization policy. permissions_csv: comma-separated permission strings."""
    fields = {}
    if name:
        fields["name"] = name
    if permissions_csv:
        fields["permissions"] = [
            t.strip() for t in permissions_csv.split(",") if t.strip()
        ]
    return json.dumps(
        SmokeBallClient().update_authorization_policy(reference, **fields), indent=2
    )


# ── Notifications ─────────────────────────────────────────────────────────────


@mcp.tool()
def get_notification(notification_id: str) -> str:
    """Get a notification by ID."""
    return json.dumps(SmokeBallClient().get_notification(notification_id), indent=2)


@mcp.tool()
def create_notification(title: str, message: str, user_id: str = "") -> str:
    """Send a notification to a user or the firm."""
    fields = {"title": title, "message": message}
    if user_id:
        fields["userId"] = user_id
    return json.dumps(SmokeBallClient().create_notification(**fields), indent=2)


# ── Plugins ───────────────────────────────────────────────────────────────────


@mcp.tool()
def list_plugins() -> str:
    """List all available plugins for this firm."""
    return json.dumps(SmokeBallClient().get_plugins(), indent=2)


@mcp.tool()
def get_plugin(plugin_id: str) -> str:
    """Get a plugin by ID."""
    return json.dumps(SmokeBallClient().get_plugin(plugin_id), indent=2)


@mcp.tool()
def create_plugin(name: str, url: str, description: str = "") -> str:
    """Register a new plugin integration."""
    fields = {"name": name, "url": url}
    if description:
        fields["description"] = description
    return json.dumps(SmokeBallClient().create_plugin(**fields), indent=2)


@mcp.tool()
def update_plugin(plugin_id: str, name: str = "", url: str = "") -> str:
    """Update a plugin's details."""
    fields = {}
    if name:
        fields["name"] = name
    if url:
        fields["url"] = url
    return json.dumps(SmokeBallClient().update_plugin(plugin_id, **fields), indent=2)


@mcp.tool()
def delete_plugin(plugin_id: str) -> str:
    """Delete a plugin by ID."""
    return json.dumps(SmokeBallClient().delete_plugin(plugin_id), indent=2)


@mcp.tool()
def list_plugin_subscriptions() -> str:
    """List all active plugin subscriptions for this firm."""
    return json.dumps(SmokeBallClient().get_plugin_subscriptions(), indent=2)


@mcp.tool()
def get_plugin_subscription(subscription_id: str) -> str:
    """Get a specific plugin subscription by ID."""
    return json.dumps(
        SmokeBallClient().get_plugin_subscription(subscription_id), indent=2
    )


@mcp.tool()
def subscribe_to_plugin(plugin_id: str) -> str:
    """Subscribe this firm to a plugin."""
    return json.dumps(SmokeBallClient().subscribe_to_plugin(plugin_id), indent=2)


@mcp.tool()
def unsubscribe_from_plugin(plugin_id: str) -> str:
    """Unsubscribe this firm from a plugin."""
    return json.dumps(SmokeBallClient().unsubscribe_from_plugin(plugin_id), indent=2)


@mcp.tool()
def get_plugin_url(plugin_id: str) -> str:
    """Request the launch URL for a plugin (for embedded iframe display)."""
    return json.dumps(SmokeBallClient().request_plugin_url(plugin_id), indent=2)


# ── Portal ────────────────────────────────────────────────────────────────────


@mcp.tool()
def create_portal_task(
    title: str,
    matter_id: str,
    contact_id: str = "",
    due_date: str = "",
    description: str = "",
) -> str:
    """Create a client portal task (visible to client). due_date: YYYY-MM-DD."""
    fields = {"title": title, "matterId": matter_id}
    if contact_id:
        fields["contactId"] = contact_id
    if due_date:
        fields["dueDate"] = due_date
    if description:
        fields["description"] = description
    return json.dumps(SmokeBallClient().create_portal_task(**fields), indent=2)


@mcp.tool()
def update_portal_task(task_id: str, completed_str: str = "", title: str = "") -> str:
    """Update a client portal task status or title. completed_str: 'true' or 'false'."""
    fields = {}
    if completed_str.lower() in ("true", "false"):
        fields["completed"] = completed_str.lower() == "true"
    if title:
        fields["title"] = title
    return json.dumps(SmokeBallClient().patch_portal_task(task_id, **fields), indent=2)


@mcp.tool()
def send_portal_message(matter_id: str, message: str, contact_id: str = "") -> str:
    """Send a message to a client via the Smokeball client portal."""
    fields = {"matterId": matter_id, "message": message}
    if contact_id:
        fields["contactId"] = contact_id
    return json.dumps(SmokeBallClient().send_portal_message(**fields), indent=2)


# ── Layout Designs ────────────────────────────────────────────────────────────


@mcp.tool()
def list_layout_designs() -> str:
    """List all layout designs (document templates) available for this firm."""
    return json.dumps(SmokeBallClient().get_layout_designs(), indent=2)


@mcp.tool()
def get_layout_design(design_id: str) -> str:
    """Get a layout design by ID."""
    return json.dumps(SmokeBallClient().get_layout_design(design_id), indent=2)


# ── Layout Matter Items ────────────────────────────────────────────────────────


@mcp.tool()
def list_layouts_on_matter(matter_id: str) -> str:
    """List all layout instances on a matter (document merge records)."""
    return json.dumps(SmokeBallClient().get_layouts_on_matter(matter_id), indent=2)


@mcp.tool()
def get_layout_on_matter(matter_id: str, layout_id: str) -> str:
    """Get a specific layout instance on a matter."""
    return json.dumps(
        SmokeBallClient().get_layout_on_matter(matter_id, layout_id), indent=2
    )


@mcp.tool()
def add_layout_to_matter(matter_id: str, layout_design_id: str) -> str:
    """Add a layout design instance to a matter for document generation."""
    return json.dumps(
        SmokeBallClient().add_layout_to_matter(
            matter_id, layoutDesignId=layout_design_id
        ),
        indent=2,
    )


@mcp.tool()
def add_contact_to_layout(
    matter_id: str, layout_id: str, contact_id: str, role: str = ""
) -> str:
    """Add a contact to a layout instance (for merge field population)."""
    fields = {"contactId": contact_id}
    if role:
        fields["role"] = role
    return json.dumps(
        SmokeBallClient().add_contact_to_layout(matter_id, layout_id, **fields),
        indent=2,
    )


@mcp.tool()
def get_layout_contacts(matter_id: str, layout_id: str) -> str:
    """Get contacts associated with a layout instance."""
    return json.dumps(
        SmokeBallClient().get_layout_contacts(matter_id, layout_id), indent=2
    )


@mcp.tool()
def merge_layout(matter_id: str, layout_id: str) -> str:
    """Execute a layout merge (generate the document from template + matter data)."""
    return json.dumps(SmokeBallClient().merge_layout(matter_id, layout_id), indent=2)


@mcp.tool()
def remove_layout_from_matter(matter_id: str, layout_id: str) -> str:
    """Remove a layout instance from a matter."""
    return json.dumps(
        SmokeBallClient().remove_layout_from_matter(matter_id, layout_id), indent=2
    )


# ── Matter Items ──────────────────────────────────────────────────────────────


@mcp.tool()
def list_matter_items(matter_id: str) -> str:
    """List all items (checklist items, workflow steps) on a matter."""
    return json.dumps(SmokeBallClient().get_items_on_matter(matter_id), indent=2)


@mcp.tool()
def get_matter_item(matter_id: str, item_id: str) -> str:
    """Get a specific item on a matter."""
    return json.dumps(
        SmokeBallClient().get_item_on_matter(matter_id, item_id), indent=2
    )


# ── Integrated Search ─────────────────────────────────────────────────────────


@mcp.tool()
def get_search_mapping() -> str:
    """Get the integrated search field mapping (what fields are indexed for search)."""
    return json.dumps(SmokeBallClient().get_integrated_search_mapping(), indent=2)


# ── Webhooks ──────────────────────────────────────────────────────────────────


@mcp.tool()
def list_webhook_subscriptions() -> str:
    """List all active webhook subscriptions."""
    return json.dumps(SmokeBallClient().get_webhook_subscriptions(), indent=2)


@mcp.tool()
def get_webhook_subscription(subscription_id: str) -> str:
    """Get a webhook subscription by ID."""
    return json.dumps(
        SmokeBallClient().get_webhook_subscription(subscription_id), indent=2
    )


@mcp.tool()
def create_webhook_subscription(event_type: str, url: str, secret: str = "") -> str:
    """Create a webhook subscription. event_type: from list_webhook_event_types."""
    fields = {}
    if secret:
        fields["secret"] = secret
    return json.dumps(
        SmokeBallClient().create_webhook_subscription(event_type, url, **fields),
        indent=2,
    )


@mcp.tool()
def update_webhook_subscription(
    subscription_id: str, url: str = "", active: str = ""
) -> str:
    """Update a webhook subscription URL or active state. active: 'true' or 'false'."""
    fields = {}
    if url:
        fields["url"] = url
    if active.lower() in ("true", "false"):
        fields["active"] = active.lower() == "true"
    return json.dumps(
        SmokeBallClient().update_webhook_subscription(subscription_id, **fields),
        indent=2,
    )


@mcp.tool()
def delete_webhook_subscription(subscription_id: str) -> str:
    """Delete a webhook subscription by ID."""
    return json.dumps(
        SmokeBallClient().delete_webhook_subscription(subscription_id), indent=2
    )


@mcp.tool()
def list_webhook_event_types() -> str:
    """List all available webhook event types."""
    return json.dumps(SmokeBallClient().get_webhook_event_types(), indent=2)


@mcp.tool()
def test_webhook_subscription(subscription_id: str) -> str:
    """Send a test notification to a webhook subscription endpoint."""
    return json.dumps(
        SmokeBallClient().notify_webhook_subscription(subscription_id), indent=2
    )


# ── Resources ─────────────────────────────────────────────────────────────────


@mcp.resource("smokeball://matter_types", mime_type="application/json")
def matter_types_resource() -> str:
    """All matter types configured in this Smokeball firm — read-only reference data."""
    return json.dumps(SmokeBallClient().list_matter_types(), indent=2)


@mcp.resource("smokeball://activity_codes", mime_type="application/json")
def activity_codes_resource() -> str:
    """All billable activity codes configured in this Smokeball firm — read-only reference data."""
    return json.dumps(SmokeBallClient().get_activity_codes(), indent=2)


@mcp.resource("smokeball://security-notes", mime_type="text/markdown")
def security_notes_resource() -> str:
    """Security posture documentation for this Smokeball MCP server."""
    return """\
# Smokeball MCP — Security Notes

## Webhook SSRF Protection (SEC-E)

The `create_webhook_subscription` tool validates the `target_url` parameter before
registering any webhook subscription. The validation enforces:

- **HTTPS-only**: plain HTTP target URLs are rejected.
- **Blocked destinations**: private RFC-1918 ranges (10.x, 172.16-31.x,
  192.168.x), loopback (127.x, ::1), link-local (169.254.x), and cloud
  metadata endpoints (169.254.169.254) are all rejected.

Any call to `create_webhook_subscription` with an invalid target URL will return an
`{"error": "..."}` response and no webhook will be created. The same validation
applies to `update_webhook_subscription` when a new `target_url` is supplied.

**Agent guidance**: when registering webhooks, only use publicly routable
HTTPS URLs as the target. Attempts to route to internal infrastructure will
be blocked by the server.
"""


# ── Prompts ───────────────────────────────────────────────────────────────────


@mcp.prompt()
def daily_briefing() -> str:
    """Morning briefing: open matters needing attention, overdue tasks, and unbilled fees."""
    return """You are a legal assistant. Run a morning briefing using the Smokeball tools:

1. List all active matters (list_matters) — note any recently opened or recently modified
2. List all open tasks (list_tasks) — flag any overdue (due before today) with ⚠️
3. List unpaid invoices (list_invoices) — highlight any overdue amounts
4. List unbilled fees (list_fees) — identify work that has not yet been invoiced
5. Summarize: what needs attention today, ranked by urgency

Be specific — include matter names, task names, due dates, and amounts. Keep it concise."""


@mcp.prompt()
def intake_triage(matter_id: str) -> str:
    """Triage a new or recently opened matter: check contacts, billing setup, and key documents."""
    return f"""Triage matter {matter_id} to ensure it is properly set up:

1. Get the matter detail (get_matter with matter_id={matter_id})
2. List contacts on the matter (list_matter_contacts or list_contacts) — check that a client contact is assigned
3. List tasks on the matter (list_tasks with matter_id={matter_id}) — note any missing intake tasks
4. List fees on the matter (list_fees with matter_id={matter_id}) — confirm billing type and any existing time entries
5. List documents on the matter (list_matter_documents or list_documents with matter_id={matter_id}) — note required documents not yet uploaded

Output a checklist: ✅ complete, ⚠️ needs attention, ❌ missing. One line per item."""


@mcp.prompt()
def billing_summary(matter_id: str) -> str:
    """Billing summary for a matter: fees, expenses, invoices, and outstanding balances.

    Note: webhook registrations in this server validate target URLs against SSRF
    (HTTPS-only; private/loopback/link-local/metadata IPs are blocked).
    """
    return f"""Generate a billing summary for matter {matter_id}:

1. List all fees (list_fees with matter_id={matter_id}) — sum total billable time and amounts
2. List all expenses (list_expenses with matter_id={matter_id}) — sum total disbursements
3. List all invoices (list_invoices with matter_id={matter_id}) — identify paid vs unpaid
4. List bank accounts (list_bank_accounts) — note the trust account if funds are held in trust

Output: total unbilled fees, total unbilled expenses, total outstanding invoices,
and a one-line status (e.g. "Ready to invoice", "Invoice overdue", "Trust funds on hold").
Flag any discrepancies between fees recorded and invoices issued."""


# ── Entry point ───────────────────────────────────────────────────────────────


def main():
    mcp.run()
