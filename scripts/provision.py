#!/usr/bin/env python3
"""Create or update Fabric workspaces from the manifests in workspaces/.

For each workspaces/*.yaml file:
  - Find the workspace by name. If it doesn't exist, create it on the
    manifest's capacity; otherwise update its description and capacity.
  - Add each owner role assignment that's missing. Roles that aren't in the
    manifest are left alone, so a run can't lock anyone out; drift.py reports them.
  - Apply the manifest's tags that aren't applied yet. A tenant tag wins over a
    domain tag of the same name; a domain tag applies only when the workspace is
    in that domain. Tags are never removed.

DRY_RUN=true logs the plan and makes no API calls.

Auth: DefaultAzureCredential. In CI, the azure/login step signs in the Azure CLI.

Exit codes: 0 every manifest applied; 1 at least one manifest failed;
3 a call returned 401 or 403, which stops the run.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fabric as fab  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = REPO_ROOT / "workspaces"
POLICY_PATH = REPO_ROOT / "rules" / "policy.yaml"

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
EXIT_AUTH = 3

# The repo ships placeholder capacity IDs such as 33333333-3333-3333-3333-333333333333.
PLACEHOLDER_ID = re.compile(r"^([0-9a-f])\1{7}-\1{4}-\1{4}-\1{4}-\1{12}$", re.IGNORECASE)


def log(msg: str) -> None:
    print(msg, flush=True)


def resolve_capacity_id(logical_name: str, policy: dict) -> str:
    cfg = policy.get("approvedCapacities", {}).get(logical_name)
    if not cfg:
        raise RuntimeError(f"capacity '{logical_name}' not in approvedCapacities")
    cap_id = cfg.get("capacityId") or ""
    if cap_id and cap_id != "FILL-ME-AT-FIRST-RUN" and not PLACEHOLDER_ID.match(cap_id):
        return cap_id
    fallback = os.environ.get("FABRIC_CAPACITY_ID")
    if fallback:
        return fallback
    if DRY_RUN:
        return "<unresolved-dry-run>"
    looked = fab.find_capacity_id_by_display_name(logical_name)
    if looked:
        return looked
    raise RuntimeError(
        f"could not resolve the capacity ID for '{logical_name}'. "
        "Set capacityId in rules/policy.yaml or the FABRIC_CAPACITY_ID variable."
    )


def resolve_tag_ids(names: list[str], domain_id: str | None) -> tuple[list[str], list[str]]:
    """Map tag names to IDs. Returns (ids, names with no usable tag)."""
    tags = fab.list_tags()
    ids, unknown = [], []
    for name in names:
        same = [t for t in tags if t.get("displayName") == name]
        tenant = [t for t in same if (t.get("scope") or {}).get("type") == "Tenant"]
        domain = [t for t in same if (t.get("scope") or {}).get("type") == "Domain" and domain_id
                  and str((t.get("scope") or {}).get("domainId", "")).lower() == domain_id.lower()]
        hit = (tenant or domain or [None])[0]
        if hit:
            ids.append(hit["id"])
        else:
            unknown.append(name)
    return ids, unknown


def reconcile_tags(ws_id: str, names: list[str]) -> None:
    ws = fab.get_workspace(ws_id)
    ids, unknown = resolve_tag_ids(names, ws.get("domainId"))
    for name in unknown:
        log(f"  warn: tag '{name}' isn't a tenant tag or a tag of this workspace's domain; skipping it")
    applied = {t.get("id") for t in ws.get("tags") or []}
    todo = [i for i in ids if i not in applied]
    if todo:
        log(f"  applying {len(todo)} tag(s)")
        fab.apply_workspace_tags(ws_id, todo)
    elif ids:
        log("  ok: tags")


def reconcile_workspace(manifest: dict, policy: dict) -> None:
    name = manifest["name"]
    desc = manifest["description"]
    cap_id = resolve_capacity_id(manifest["capacity"], policy)

    log(f"--- {name} ---")
    if DRY_RUN:
        log(f"  [dry-run] would ensure workspace exists with capacity={cap_id}")
        log(f"  [dry-run] would set description: {desc[:60]}...")
        for o in manifest.get("owners", []):
            log(f"  [dry-run] would assign role {o['role']} to {o['principalType']} {o['identifier']}")
        if manifest.get("tags"):
            log(f"  [dry-run] would apply tags: {', '.join(manifest['tags'])}")
        return

    existing = fab.get_workspace_by_name(name)
    if existing is None:
        log(f"  creating workspace (capacity={cap_id})")
        ws = fab.create_workspace(name, desc, capacity_id=cap_id)
        ws_id = ws["id"]
    else:
        ws_id = existing["id"]
        log(f"  exists: {ws_id} — updating description + capacity")
        fab.update_workspace(ws_id, description=desc)
        try:
            fab.assign_to_capacity(ws_id, cap_id)
        except fab.AuthError:
            raise
        except Exception as e:
            log(f"  warn: assignToCapacity: {e}")

    # Role assignments
    existing_keys = {(ra["principal"]["id"], ra["role"]) for ra in fab.list_role_assignments(ws_id)}
    for o in manifest.get("owners", []):
        pid = o["identifier"]
        ptype = o["principalType"]
        role = o["role"]
        # Fabric API requires object IDs (GUIDs), not UPNs — resolve if needed
        if ptype == "User" and "@" in pid:
            resolved = fab.graph_resolve_upn(pid)
            if resolved:
                log(f"  resolved {pid} -> {resolved}")
                pid = resolved
            else:
                log(f"  warn: could not resolve UPN {pid} to object ID, skipping")
                continue
        if (pid, role) in existing_keys:
            log(f"  ok: {ptype} {pid} {role}")
            continue
        log(f"  adding: {ptype} {pid} {role}")
        try:
            fab.add_role_assignment(ws_id, pid, ptype, role)
        except fab.AuthError:
            raise
        except Exception as e:
            log(f"  warn: role assignment failed for {pid}: {e}")

    if manifest.get("tags"):
        reconcile_tags(ws_id, manifest["tags"])


def main() -> int:
    policy = yaml.safe_load(POLICY_PATH.read_text())
    files = sorted(WORKSPACES_DIR.glob("*.yaml"))
    if not files:
        log("No manifests to provision.")
        return 0
    failed = 0
    for f in files:
        try:
            m = yaml.safe_load(f.read_text())
            reconcile_workspace(m, policy)
        except fab.AuthError as e:
            log(f"ERROR processing {f.name}: {e}")
            log("Stopped: fix the permission above, then rerun.")
            return EXIT_AUTH
        except Exception as e:
            log(f"ERROR processing {f.name}: {e}")
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
