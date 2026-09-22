"""Permissions levels for chat/agent access.

Levels:
- workspace: limited to a chosen folder/dossier. File tools only within workspace.
- partial: workspace + safe productivity tools (web, notes, tasks, calendar, email read).
- full: all tools except admin-only when not owner.

This module defines the tool sets per level and a helper to compute disabled tools.
"""

from __future__ import annotations

from typing import Set

# Tool names that are considered file-system/workspace limited
WORKSPACE_FILE_TOOLS = {
    "read_file",
    "write_file",
    "edit_file",
    "apply_patch",
    "ls",
    "glob",
    "grep",
    "get_workspace",
}

# Safe productivity tools for partial level
PARTIAL_PRODUCTIVITY_TOOLS = {
    "web_search",
    "web_fetch",
    "manage_notes",
    "manage_tasks",
    "manage_calendar",
    "manage_contact",
    "resolve_contact",
    "list_email_accounts",
    "list_emails",
    "read_email",
    "reply_to_email",
    "archive_email",
    "delete_email",
    "mark_email_read",
    "send_email",
    "bulk_email",
    "manage_memory",
    "search_chats",
}

# Admin-only tools that should never be exposed to non-owner even on full
ADMIN_ONLY_TOOLS = {
    "manage_endpoints",
    "manage_mcp",
    "manage_webhooks",
    "manage_tokens",
    "manage_settings",
    "manage_skills",
    "manage_session",
    "create_session",
    "list_sessions",
    "send_to_session",
}

# Tools that are always allowed in full level
FULL_LEVEL_BASE = {
    "bash",
    "python",
    "todowrite",
    "create_document",
    "update_document",
    "edit_document",
    "suggest_document",
    "manage_documents",
    "ask_user",
    "update_plan",
    "chat_with_model",
    "ask_teacher",
    "list_models",
    "generate_image",
    "edit_image",
    "manage_bg_jobs",
    "ui_control",
    "app_api",
    "pipeline",
    "api_call",
    "vault_get",
    "vault_search",
    "vault_unlock",
}

# All tools known at this time – union of levels
ALL_KNOWN_TOOLS = WORKSPACE_FILE_TOOLS | PARTIAL_PRODUCTIVITY_TOOLS | FULL_LEVEL_BASE | ADMIN_ONLY_TOOLS

LEVELS = {
    "workspace": "workspace",
    "partial": "partial",
    "full": "full",
}

def tools_for_level(level: str, *, owner: bool = False) -> Set[str]:
    level = (level or "workspace").lower()
    if level == "workspace":
        return set(WORKSPACE_FILE_TOOLS)
    if level == "partial":
        return set(WORKSPACE_FILE_TOOLS) | set(PARTIAL_PRODUCTIVITY_TOOLS)
    if level == "full":
        allowed = set(WORKSPACE_FILE_TOOLS) | set(PARTIAL_PRODUCTIVITY_TOOLS) | set(FULL_LEVEL_BASE)
        if owner:
            allowed |= set(ADMIN_ONLY_TOOLS)
        return allowed
    # Fallback
    return set(WORKSPACE_FILE_TOOLS)

def disabled_tools_for_level(level: str, *, owner: bool = False, workspace_restricted: bool = True) -> Set[str]:
    allowed = tools_for_level(level, owner=owner)
    # Keep only known tools; unknown tools remain enabled by default
    disabled = ALL_KNOWN_TOOLS - allowed
    # Workspace restriction flag is kept for future file-system path enforcement
    # At the tool level we only disable tools, not paths.
    return disabled

def normalize_level(level: str | None) -> str:
    if not level:
        return "workspace"
    lvl = level.lower()
    if lvl in LEVELS:
        return lvl
    # Alias handling
    if lvl in {"folder", "dossier"}:
        return "workspace"
    if lvl in {"partial", "partiel", "limited"}:
        return "partial"
    if lvl in {"full", "complete", "complet", "admin"}:
        return "full"
    return "workspace"
