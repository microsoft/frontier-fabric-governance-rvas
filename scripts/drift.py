#!/usr/bin/env python3
"""Nightly drift check: compares the tenant's workspaces with workspaces/*.yaml.

It reports:
  - unmanaged: active workspaces that have no manifest
  - missing: manifests that have no workspace
  - not visible: managed workspaces the service principal holds no role on,
    so their description can't be read
  - description: the workspace description differs from the manifest
  - roles: an owner has no access or a different role, or a principal that
    isn't an owner has access (the automation service principal is ignored)
  - tags: a manifest tag isn't applied, or an applied tag isn't in the manifest

Capacity, domain and sensitivity label aren't compared.

The inventory, tags and roles come from read-only admin APIs: List Workspaces
and List Workspace Access Details (Preview), one call per managed workspace.
Each allows 200 requests an hour.

Writes drift-report.md and the GitHub step summary. Exit codes: 0 no drift;
2 drift found; 3 a call returned 401 or 403, so the check didn't run.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fabric as fab  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = REPO_ROOT / "workspaces"
REPORT_PATH = REPO_ROOT / "drift-report.md"

EXIT_CLEAN, EXIT_DRIFT, EXIT_AUTH = 0, 2, 3


def load_manifests() -> dict[str, dict]:
    manifests = {}
    for f in sorted(WORKSPACES_DIR.glob("*.yaml")):
        m = yaml.safe_load(f.read_text())
        manifests[m["name"]] = m
    return manifests


def is_active_workspace(w: dict) -> bool:
    return (str(w.get("type", "")).lower() == "workspace"
            and str(w.get("state", "")).lower() == "active")


def _principal_keys(p: dict) -> set[str]:
    upn = (p.get("userDetails") or {}).get("userPrincipalName") or ""
    return {str(p.get("id") or "").lower(), upn.lower()} - {""}


def _principal_label(p: dict) -> str:
    ident = (p.get("userDetails") or {}).get("userPrincipalName") or p.get("id") or "?"
    name = p.get("displayName")
    return f"{name} ({ident})" if name and name != ident else ident


def role_drift(manifest: dict, access: list[dict], own_app_id: str | None) -> list[str]:
    """Compare manifest owners with the workspace's access details."""
    entries = [(a.get("principal") or {}, (a.get("workspaceAccessDetails") or {}).get("workspaceRole"))
               for a in access]
    issues, matched = [], set()
    for o in manifest.get("owners") or []:
        ident = str(o["identifier"]).lower()
        hits = [i for i, (p, _) in enumerate(entries) if ident in _principal_keys(p)]
        if not hits:
            issues.append(f"owner {o['identifier']} ({o['principalType']}) has no access; "
                          f"the manifest gives it {o['role']}")
            continue
        matched.update(hits)
        roles = sorted({str(entries[i][1]) for i in hits})
        if o["role"] not in roles:
            issues.append(f"owner {o['identifier']} has {', '.join(roles)}; the manifest gives it {o['role']}")
    for i, (p, role) in enumerate(entries):
        if i in matched:
            continue
        app_id = (p.get("servicePrincipalDetails") or {}).get("aadAppId") or ""
        if own_app_id and p.get("type") == "ServicePrincipal" and app_id.lower() == own_app_id.lower():
            continue
        issues.append(f"{p.get('type', 'principal')} {_principal_label(p)} has {role} "
                      "but isn't an owner in the manifest")
    return issues


def tag_drift(manifest: dict, workspace: dict) -> list[str]:
    """Compare manifest tag names with the tags applied to the workspace."""
    wanted = set(manifest.get("tags") or [])
    applied = {t.get("displayName") for t in workspace.get("tags") or [] if t.get("displayName")}
    return ([f"tag '{t}' isn't applied" for t in sorted(wanted - applied)]
            + [f"tag '{t}' is applied but isn't in the manifest" for t in sorted(applied - wanted)])


def description_drift(manifest: dict, workspace: dict) -> list[str]:
    if (workspace.get("description") or "").strip() != (manifest.get("description") or "").strip():
        return ["description differs from the manifest"]
    return []


def check() -> tuple[str, bool]:
    manifests = load_manifests()
    tenant = {w["name"]: w for w in fab.admin_list_workspaces()
              if is_active_workspace(w) and w.get("name")}
    visible = {w["id"]: w for w in fab.list_workspaces() if w.get("id")}
    own_app_id = fab.caller_app_id()

    unmanaged = sorted(set(tenant) - set(manifests))
    missing = sorted(set(manifests) - set(tenant))
    not_visible: list[str] = []
    drifted: dict[str, list[str]] = {}
    for name in sorted(set(manifests) & set(tenant)):
        m, w = manifests[name], tenant[name]
        issues = []
        core = visible.get(w["id"])
        if core is None:
            not_visible.append(name)
        else:
            issues += description_drift(m, core)
        issues += role_drift(m, fab.admin_list_workspace_access(w["id"]), own_app_id)
        issues += tag_drift(m, w)
        if issues:
            drifted[name] = issues

    lines = ["# Fabric workspace drift report", ""]
    lines.append(f"- Manifests: {len(manifests)}")
    lines.append(f"- Active workspaces in the tenant: {len(tenant)}")
    for label, names in (("Unmanaged (in the tenant, no manifest)", unmanaged),
                         ("Missing (manifest, no workspace)", missing),
                         ("Not visible (the service principal has no workspace role; "
                          "description not checked)", not_visible),
                         ("Drifted", list(drifted))):
        lines.append(f"- {label}: **{len(names)}**")
        lines.extend(f"  - {n}" for n in names)
    for name, issues in drifted.items():
        lines += ["", f"## {name}", ""]
        lines.extend(f"- {i}" for i in issues)
    return "\n".join(lines) + "\n", bool(unmanaged or missing or not_visible or drifted)


def write_report(md: str) -> None:
    REPORT_PATH.write_text(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(md)


def main() -> int:
    try:
        md, found = check()
    except fab.AuthError as e:
        write_report("# Fabric workspace drift report\n\n"
                     "The drift check didn't run: a call returned 401 or 403.\n\n"
                     f"{e}\n")
        print(f"error: {e}", file=sys.stderr)
        return EXIT_AUTH
    write_report(md)
    print(md)
    return EXIT_DRIFT if found else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
