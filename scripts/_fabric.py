"""Thin Fabric and Microsoft Graph REST client.

Auth: DefaultAzureCredential. In GitHub Actions, the azure/login step signs in
the Azure CLI with OIDC, and DefaultAzureCredential uses that session. Locally,
run `az login` first.

Errors: a 401 or 403 response raises AuthError, whose message names the
permission the call needs. Callers stop on it and never read it as "not found".
"""
from __future__ import annotations

import base64
import functools
import json as jsonlib
import time
import urllib.parse
from typing import Any, Optional

import requests
from azure.identity import DefaultAzureCredential

FABRIC_BASE = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# What to fix when a call returns 401 or 403. The automation service principal
# is never a Fabric administrator; its group holds these tenant settings.
_GROUP = "sg-fabric-workspace-provisioner"
HINT_FABRIC = (
    f"Check that {_GROUP} is in the tenant setting 'Service principals can call Fabric public APIs'. "
    "Workspace calls also need a workspace role: Admin to change a workspace or its roles.")
HINT_CREATE = (
    f"Check that {_GROUP} is in the tenant setting 'Service principals can create workspaces, "
    "connections, and deployment pipelines' and that the service principal has Contributor "
    "permissions on the capacity.")
HINT_CAPACITY = (
    "Assigning a capacity needs the Admin role on the workspace and Contributor permissions "
    "on the capacity.")
HINT_ADMIN_READ = (
    f"Check that {_GROUP} is in the tenant setting 'Service principals can access read-only admin "
    "APIs'. Admin APIs reject a service principal that has admin-consent Power BI API permissions, "
    "so remove any it has.")
HINT_TAGS = "Applying workspace tags needs the Admin role on the workspace."
HINT_GRAPH_GROUP = (
    "Grant the app the Microsoft Graph application permission GroupMember.Read.All "
    "(or Group.Read.All) with admin consent.")
HINT_GRAPH_USER = (
    "Grant the app the Microsoft Graph application permission User.Read.All with admin consent.")


class AuthError(PermissionError):
    """A Fabric or Graph call returned 401 or 403."""


_credential: Optional[DefaultAzureCredential] = None


def _cred() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return _credential


def token(scope: str = FABRIC_SCOPE) -> str:
    return _cred().get_token(scope).token


def _error_detail(r: requests.Response) -> str:
    """The error code and message from a Fabric or Graph error body."""
    try:
        body = r.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):  # Microsoft Graph
            return f"{err.get('code', '')}: {err.get('message', '')}".strip(": ")
        if body.get("errorCode") or body.get("message"):  # Fabric
            return f"{body.get('errorCode', '')}: {body.get('message', '')}".strip(": ")
    return (r.text or "").strip()[:300]


def _request(method: str, url: str, *, scope: str = FABRIC_SCOPE,
             json: Any = None, params: dict | None = None,
             expect: tuple[int, ...] = (200, 201, 202, 204),
             retries: int = 5, hint: str = HINT_FABRIC) -> requests.Response:
    headers = {"Authorization": f"Bearer {token(scope)}", "Content-Type": "application/json"}
    backoff = 2.0
    for attempt in range(retries):
        r = requests.request(method, url, headers=headers, json=json, params=params, timeout=60)
        if r.status_code in expect:
            return r
        if r.status_code in (401, 403):
            raise AuthError(f"{method} {url} returned {r.status_code} ({_error_detail(r)}). {hint}")
        if r.status_code in (429, 502, 503, 504):
            wait = float(r.headers.get("Retry-After", backoff))
            time.sleep(wait)
            backoff *= 2
            continue
        raise RuntimeError(f"{method} {url} returned {r.status_code}: {_error_detail(r)}")
    raise RuntimeError(f"{method} {url} exhausted retries; last status {r.status_code}: {_error_detail(r)}")


def _paged(url: str, key: str = "value", *, hint: str = HINT_FABRIC) -> list[dict]:
    """GET every page, following continuationUri as returned."""
    out: list[dict] = []
    while url:
        body = _request("GET", url, hint=hint).json()
        out.extend(body.get(key) or [])
        url = body.get("continuationUri")
    return out


# ---------- Workspaces ----------
def list_workspaces() -> list[dict]:
    """Workspaces the caller holds a role on."""
    return _paged(f"{FABRIC_BASE}/workspaces")


def get_workspace(workspace_id: str) -> dict:
    """One workspace, with its description, capacityId, domainId and applied tags."""
    return _request("GET", f"{FABRIC_BASE}/workspaces/{workspace_id}").json()


def get_workspace_by_name(name: str) -> dict | None:
    for w in list_workspaces():
        if w.get("displayName") == name:
            return w
    return None


def create_workspace(display_name: str, description: str, capacity_id: str | None = None) -> dict:
    body = {"displayName": display_name, "description": description}
    if capacity_id:
        body["capacityId"] = capacity_id
    r = _request("POST", f"{FABRIC_BASE}/workspaces", json=body, expect=(201, 200), hint=HINT_CREATE)
    return r.json()


def update_workspace(workspace_id: str, *, description: str | None = None) -> None:
    body = {}
    if description is not None:
        body["description"] = description
    if not body:
        return
    _request("PATCH", f"{FABRIC_BASE}/workspaces/{workspace_id}", json=body)


def assign_to_capacity(workspace_id: str, capacity_id: str) -> None:
    _request("POST", f"{FABRIC_BASE}/workspaces/{workspace_id}/assignToCapacity",
             json={"capacityId": capacity_id}, hint=HINT_CAPACITY)


def list_role_assignments(workspace_id: str) -> list[dict]:
    return _paged(f"{FABRIC_BASE}/workspaces/{workspace_id}/roleAssignments")


def add_role_assignment(workspace_id: str, principal_id: str, principal_type: str, role: str) -> None:
    """principal_type: User | Group | ServicePrincipal ; role: Admin|Member|Contributor|Viewer"""
    body = {"principal": {"id": principal_id, "type": principal_type}, "role": role}
    _request("POST", f"{FABRIC_BASE}/workspaces/{workspace_id}/roleAssignments",
             json=body, expect=(201, 200))


# ---------- Tags ----------
@functools.lru_cache(maxsize=None)
def list_tags() -> list[dict]:
    """The tenant's tags, each with a Tenant or Domain scope.

    Cached for the run: the API allows 25 requests a minute. Don't modify the result.
    """
    return _paged(f"{FABRIC_BASE}/tags")


def apply_workspace_tags(workspace_id: str, tag_ids: list[str]) -> None:
    """Apply Workspace Tags (Preview). Adds tags and never removes one."""
    _request("POST", f"{FABRIC_BASE}/workspaces/{workspace_id}/applyTags",
             json={"tags": tag_ids}, hint=HINT_TAGS)


# ---------- Admin (read-only) ----------
def admin_list_workspaces() -> list[dict]:
    """Every workspace in the tenant, with its type, state and applied tags.

    200 requests an hour. Filter on type and state in the caller.
    """
    return _paged(f"{FABRIC_BASE}/admin/workspaces", "workspaces", hint=HINT_ADMIN_READ)


def admin_list_workspace_access(workspace_id: str) -> list[dict]:
    """List Workspace Access Details (Preview): each principal's workspace role. 200 requests an hour."""
    return _paged(f"{FABRIC_BASE}/admin/workspaces/{workspace_id}/users", "accessDetails",
                  hint=HINT_ADMIN_READ)


# ---------- Capacities ----------
def list_capacities() -> list[dict]:
    return _paged(f"{FABRIC_BASE}/capacities")


def find_capacity_id_by_display_name(display_name: str) -> str | None:
    for c in list_capacities():
        if c.get("displayName") == display_name:
            return c.get("id")
    return None


# ---------- Caller ----------
def caller_app_id() -> str | None:
    """The signed-in app's client ID, from the Fabric token's appid or azp claim."""
    try:
        payload = token().split(".")[1]
        claims = jsonlib.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return None
    return claims.get("appid") or claims.get("azp")


# ---------- Microsoft Graph ----------
def graph_group_exists(object_id: str) -> bool:
    """True if the group exists, False on 400 or 404. Raises AuthError on 401 or 403."""
    r = _request("GET", f"{GRAPH_BASE}/groups/{urllib.parse.quote(object_id, safe='')}",
                 scope=GRAPH_SCOPE, params={"$select": "id"}, expect=(200, 400, 404),
                 hint=HINT_GRAPH_GROUP)
    return r.status_code == 200


def graph_resolve_upn(upn: str) -> str | None:
    """The user's object ID, or None on 400 or 404. Raises AuthError on 401 or 403."""
    r = _request("GET", f"{GRAPH_BASE}/users/{urllib.parse.quote(upn, safe='@')}",
                 scope=GRAPH_SCOPE, params={"$select": "id"}, expect=(200, 400, 404),
                 hint=HINT_GRAPH_USER)
    return r.json().get("id") if r.status_code == 200 else None
