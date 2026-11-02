# Challenge 01 — Workspace as code

> **Outcome:** you can create, update, and decommission Fabric workspaces by opening
> Pull Requests against YAML manifests. The tenant has zero workspaces that aren't in
> `main`.

## Why this challenge exists

Workspaces are the unit of access control, capacity assignment, and domain placement
in Fabric. Govern who creates them and how before adding controls within them.

Every later challenge reuses this workflow:

```
PR → schema check → policy check → CODEOWNERS approval →
merge → environment approval → OIDC token → Fabric REST → marker written →
nightly drift reconciliation
```

## Learning objectives

1. Author a workspace manifest that conforms to `schemas/workspace.schema.json`.
2. Read the validation feedback posted as a sticky PR comment and fix issues.
3. Trace a successful provision through GitHub Actions, Entra OIDC, and Fabric REST.
4. Use the Fabric Core MCP Server from chat to **verify** that the live tenant
   matches your manifest.
5. Detect and remediate drift introduced out-of-band.

## Prerequisites

- All of Challenge 00 complete.
- You can run `python scripts/validate.py` locally without auth errors
  (`LIVE_CHECKS=false` is fine for local).

## Tasks

### Task 1 — Reproduce the sample manifest

Read `workspaces/pt-nlyt-sample-ndf-dev-hello1.yaml`. Then open a PR
that adds **a second** manifest, e.g. `workspaces/dev-plt-myteam-playground.yaml`,
following the same shape.

Watch the `validate` workflow run. The sticky PR comment summarises every rule from
`rules/policy.yaml` with ✅ / ⚠️ / ❌. Fix any blocking issues.

### Task 2 — Get a deliberate policy failure and fix it

Try one of these and confirm `validate` blocks the PR:

- A name that doesn't match `^(prd|stg|dev|sbx)-[a-z0-9]{2,6}-[a-z0-9-]{3,40}$`.
- A `costCenter` that isn't in `rules/policy.yaml`'s `approvedCostCenters`.
- A single owner (the rule requires ≥ 2).
- `environment: prd` with sensitivity `General` (prod requires Confidential+).

Then fix the manifest and confirm the PR turns green.

### Task 3 — Merge and provision

1. Get the PR reviewed by a CODEOWNERS-listed teammate.
2. Merge. The `provision` workflow starts and pauses at the **`production`**
   environment gate.
3. Approve the environment. Provisioning runs; check the run logs to see:
   - `azure/login@v2` exchanging the OIDC token,
   - `POST /workspaces` returning the new workspace ID,
   - `assignToCapacity` posting,
   - role assignments reconciled,
   - description ending in `managed-by:gh:<org>/<repo>@<sha>`.

### Task 4 — Verify via the Fabric Core MCP

In VS Code chat, ask:

```
Get the workspace called "<your-new-workspace-name>" and show me its description.
List the role assignments for that workspace.
```

The description should end with the `managed-by:` marker. The role assignments
should match your manifest's `owners` array.

### Task 5 — Detect drift

In the Fabric portal, manually change something about the workspace (e.g., remove
an admin or change the description). Trigger `drift.yml` from the Actions tab
(`workflow_dispatch`).

Confirm an issue is opened tagged `drift/configuration` with a diff body.

Open a PR that either reverts the live change or updates the manifest to match
the new desired state. Merge, re-run drift, and confirm the issue closes or stays
closed because there is no longer drift.

### Task 6 — Decommission

Open a PR that removes a manifest. Decide as a team what removal means:

- Option A (default): keep the workspace in the tenant, but stop managing it.
  Manifest deletion only removes governance, not the workspace.
- Option B: extend the provisioner to delete the workspace on manifest removal.
  This is *destructive*; only do it if your team controls the data.

Document the chosen behavior in `docs/`.

## Success criteria

- [ ] One workspace you created via PR exists in the tenant and shows the
      `managed-by:` marker.
- [ ] You can reproduce a blocking policy failure on demand.
- [ ] You can detect injected drift via `drift.yml`.
- [ ] You can describe what the SPN does on `validate` vs. `provision` vs. `drift`.

## Stretch goals

- **New blocking rule.** Add a rule to `rules/policy.yaml` (e.g., prd workspaces
  must reference a cost center starting `CC-9`). Implement it in `scripts/validate.py`,
  prove it fails then passes with a PR.
- **Adoption.** Pick an existing tenant workspace (created outside the repo) and
  write an `adopt.py` that adds the manifest + writes the marker without
  re-creating the workspace.
- **PR template tweaks.** Customize `.github/pull_request_template.md` to ask the
  requester for the business justification, expected lifespan, and data
  classification.

## MCP tips

- `list_workspaces` returns paginated results; for tenants with many workspaces,
  ask the agent to filter by display name prefix.
- The agent can call `delete_workspace` if you ask it to. **Do not** use
  chat to manage prod; use the workflow and environment gate.

## Skills tips

- Skills aren't required here. Challenge 02 uses `spark-authoring-cli` to scaffold
  notebook contents; if you have spare time, install it and ask for a Notebook template.

## Repository files

This challenge uses these files in the repo root:

- `schemas/workspace.schema.json`
- `rules/policy.yaml`
- `scripts/validate.py`, `scripts/provision.py`, `scripts/drift.py`, `scripts/_fabric.py`
- `workspaces/pt-nlyt-sample-ndf-dev-hello1.yaml`
- `.github/workflows/validate.yml`, `provision.yml`, `drift.yml`
- `.github/CODEOWNERS`, `.github/pull_request_template.md`

For the design walkthrough, see
[`docs/workspace-approval-workflow.md`](../../docs/workspace-approval-workflow.md).

## References

- [`docs/workspace-approval-workflow.md`](../../docs/workspace-approval-workflow.md)
- [`docs/setup.md`](../../docs/setup.md)
- [`docs/identity-model.md`](../../docs/identity-model.md)
- [Fabric REST API — workspaces](https://learn.microsoft.com/rest/api/fabric/core/workspaces)
