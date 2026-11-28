# PR-based workspace approval workflow

> **RVAS note:** this is the **design reference** for **Challenge 01 —
> Workspace as code**. If you're an RVAS (Real Value Acceleration Solutions) participant, start with the
> lab instructions in [`../challenges/01-workspace-as-code/challenge.md`](../challenges/01-workspace-as-code/challenge.md)
> and use this document for deeper background.

Each governed workspace has a manifest, `workspaces/<name>.yaml`, in `main`. To create or change a workspace, open a pull request that changes its manifest. The `validate` workflow checks the manifest against the rules and comments with the results, and a code owner reviews the change. After the merge, the `provision` workflow applies the manifest as a service principal that signs in with OpenID Connect (OIDC), so no secret is stored. A daily `drift` check compares the tenant with the manifests and opens an issue when they differ.

The workflows, [`validate.yml`](../.github/workflows/validate.yml), [`provision.yml`](../.github/workflows/provision.yml) and [`drift.yml`](../.github/workflows/drift.yml), are blueprints. They run on a self-hosted runner labeled `fabric-gov` that you provide, and they're disabled in this repository. [One-time setup](setup.md#configure-the-repository) shows how to turn them on.

## 1. Architecture

### 1.1 Flow

```text
requester --> pull request --> validate --> code owner review --> merge to main
                                                                        |
                                                                        v
                                                               production approval
                                                                        |
                                                                        v
issue <-- drift (daily) <-- Fabric tenant <------------------------ provision
```

1. A requester opens a pull request that adds or changes a manifest, by hand or through the [Copilot Studio agent](copilot-studio-agent.md) or the [Microsoft 365 agent](m365-agent.md).
2. `validate` checks each changed manifest against the schema and the rules, and comments on the pull request with the results.
3. A code owner reviews the change. Branch protection on `main` requires that review and a passing `validate` check.
4. The merge starts `provision`, which waits until a required reviewer of the `production` environment approves it.
5. `provision.py` creates or updates each workspace, then adds missing role assignments and tags.
6. Each day, `drift.py` compares the tenant with the manifests, and the `drift` workflow opens an issue when they differ.

### 1.2 Tenant settings

A Fabric administrator enables each of these for specific security groups, including `sg-fabric-workspace-provisioner`, in **OneLake catalog** > **Govern** > **Configurations** > **Tenant settings**. Where Govern isn't available, use **Settings** > **Admin portal** > **Tenant settings**. [One-time setup](setup.md#turn-on-the-tenant-settings) has the steps.

| Setting | Section | Needed for |
|---|---|---|
| Service principals can call Fabric public APIs | Developer settings | Every Fabric call |
| Service principals can create workspaces, connections, and deployment pipelines | Developer settings | Creating workspaces. Off by default in new tenants. |
| Service principals can access read-only admin APIs | Admin API settings | The drift check |
| Service principals can access admin APIs used for updates | Admin API settings | Fabric admin APIs that change data, such as assigning workspaces to domains. The shipped scripts don't use it. |
| Create workspaces | Workspace settings | Creating workspaces. Limit it to the group and a break-glass group so requests go through the repository. |

A change can take up to 15 minutes to take effect ([About tenant settings](https://learn.microsoft.com/fabric/admin/about-tenant-settings)).

### 1.3 Identity model

- **App registration:** `gh-fabric-workspace-provisioner`. Its service principal is a member of `sg-fabric-workspace-provisioner`, the group the tenant settings above name.
- **Federated credentials (OIDC)**, so there are no client secrets. Each trusts GitHub Actions tokens for one subject, with the audience `api://AzureADTokenExchange`. There's one subject per workflow:
  - `<prefix>:pull_request` for `validate`
  - `<prefix>:ref:refs/heads/main` for `drift`
  - `<prefix>:environment:production` for `provision`

  `<prefix>` is `repo:<owner>@<owner-id>/<repo>@<repo-id>` for a repository that uses immutable subjects and `repo:<owner>/<repo>` otherwise. [One-time setup](setup.md#add-the-federated-credentials) has the issuer and shows how to find your prefix.
- **Capacities:** the group has Contributor permissions on each approved capacity. With the Admin role on the workspace, that's enough to assign a workspace to a capacity ([Assign To Capacity](https://learn.microsoft.com/rest/api/fabric/core/workspaces/assign-to-capacity)).
- **Microsoft Graph:** the application permissions `GroupMember.Read.All` (or `Group.Read.All`) and `User.Read.All`, to check owner groups and look up owner users.
- **Never:** the Fabric administrator role, a capacity administrator role, or Power BI or Fabric permissions that need admin consent, such as `Tenant.ReadWrite.All`. Admin APIs reject a service principal that has them. It isn't in a sensitivity label publishing policy either: labels go on items, and the admin label APIs accept only a user who is a Fabric administrator.

[Identity model](identity-model.md) explains each grant.

### 1.4 Extending the design

The shipped scripts govern workspaces only. The other challenges extend the same pull request flow:

- [Challenge 02](../challenges/02-items-as-code/challenge.md): every lakehouse, notebook and warehouse gets a manifest in `items/<workspace>/`.
- [Challenge 03](../challenges/03-domains-capacities-sensitivity/challenge.md): each workspace's domain, capacity and sensitivity label change only through a pull request. `provision.py` doesn't assign domains, and the service principal can't apply labels ([§9](#9-limitations-and-gotchas)).
- [Challenge 04](../challenges/04-access-rbac-lifecycle/challenge.md): role assignments live in `access/`, go to groups first and carry an `expiresOn` date. A quarterly review keeps them current, and stale assignments open remediation pull requests.
- [Challenge 05](../challenges/05-medallion-bootstrap/challenge.md): one pull request scaffolds the Bronze, Silver and Gold layers and their notebooks with the `e2e-medallion-architecture` Skill, and declares each layer's sensitivity label and endorsement.
- [Challenge 06](../challenges/06-data-agent-governance/challenge.md): data agents are created only through a pull request, with a data source allow list, responsible AI checks on their instructions and risk gating informed by Microsoft Purview. No public API returns Data Security Posture Management (DSPM) findings, so review them in the Purview portal.
- [Challenge 07](../challenges/07-audit-observability/challenge.md): events land in an Eventhouse, feed a Power BI dashboard and trigger Activator alerts. Fabric events come from [Real-Time hub](https://learn.microsoft.com/fabric/real-time-hub/explore-fabric-events). [Activity data](https://learn.microsoft.com/fabric/admin/track-user-activities) comes from the Microsoft Purview audit log or [Get Activity Events](https://learn.microsoft.com/rest/api/power-bi/admin/get-activity-events) (Power BI admin API; no Fabric API yet), which returns one UTC day per call, covers the last 28 days and allows 200 requests an hour. To bring in webhooks, relay them through an Azure Function or Logic App into the Eventstream [custom endpoint](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-source-custom-app). The HTTP source (Preview) polls an endpoint rather than receiving calls.
- [Challenge 08](../challenges/08-deployment-pipelines/challenge.md): content moves from dev to stg to prd through deployment pipelines, gated by pull request labels and the same `production` approval.

## 2. Repository layout

The workflow uses these files:

```text
.github/
  CODEOWNERS                     who reviews which paths
  workflows/
    validate.yml                 pull requests: runs validate.py
    provision.yml                merges to main: runs provision.py
    drift.yml                    daily: runs drift.py
rules/policy.yaml                rules and allow lists
schemas/workspace.schema.json    manifest schema
scripts/
  rules_engine.py                the rules
  validate.py                    checks manifests and writes the report
  provision.py                   creates and updates workspaces
  drift.py                       compares the tenant with the manifests
  _fabric.py                     Fabric and Microsoft Graph calls
  requirements.txt
workspaces/
  dev-plt-sample-hello.yaml      sample manifest
api/                             Microsoft 365 agent backend, with copies of the rules
```

`api/policy.yaml`, `api/rules_engine.py` and `api/workspace.schema.json` are copies of `rules/policy.yaml`, `scripts/rules_engine.py` and `schemas/workspace.schema.json` for the [Microsoft 365 agent](m365-agent.md). Keep each pair identical. The [Copilot Studio agent](copilot-studio-agent.md) doesn't use them; it opens pull requests through agent flows. Two other workflows, `agent-build.yml` and `pages.yml`, build the Microsoft 365 agent package and publish this site. Neither calls Fabric.

## 3. Rules

[Governance rules](governance-rules.md#rules) lists every rule, its level and what it checks. A blocking finding fails the check; a warning doesn't. These rules shape the workflow:

- Names follow `<environment>-<team>-<workload>`, such as `prd-fin-revenue` ([Workspace names](governance-rules.md#workspace-names)). The manifest's `environment` and `team` must equal the first two segments (`name-segments-match-fields`).
- Save each manifest as `workspaces/<name>.yaml`, where `<name>` is its `name`. `validate` blocks any other path (`manifest-filename`). `provision` and `drift` read only `.yaml` files, so they ignore a `.yml` manifest.
- A manifest with `environment: prd` needs the sensitivity label Confidential or Highly Confidential and at least two group owners (`prod-extra-controls`). Production rules key on `environment`, never on the name.
- `owner-groups-exist` and `tags-exist-in-tenant` check the tenant with the job's sign-in, and run only when the `LIVE_CHECKS` variable is `true`. Read [Pull request runs](identity-model.md#pull-request-runs) before you turn them on.
- No rule enforces `quotas.perGroupPerEnv` yet ([Capacities, environments and quotas](governance-rules.md#capacities-environments-and-quotas)).

## 4. Manifest

This manifest passes every rule while `LIVE_CHECKS` is off. To try it, save it as `workspaces/prd-fin-revenue.yaml`. Before you turn on the live checks, replace the placeholder object IDs and group names with your own groups.

```yaml
name: prd-fin-revenue
environment: prd
team: fin
domain: dom-fin-corp
subDomain: sdm-fin-rev
description: "Curated revenue tables and reports for finance month-end close."
capacity: contosoprodf4
region: northeurope
sensitivityLabel: Confidential
costCenter: CC-2042
owners:
  - principalType: Group
    identifier: 00000000-0000-0000-0000-000000000a01
    groupName: grp_fabric_prd_fin_admin
    role: Admin
  - principalType: Group
    identifier: 00000000-0000-0000-0000-000000000a02
    groupName: grp_fabric_prd_plt_admin
    role: Admin
  - principalType: Group
    identifier: 00000000-0000-0000-0000-000000000b01
    groupName: grp_fabric_prd_fin_member
    role: Member
  - principalType: Group
    identifier: 00000000-0000-0000-0000-000000000c01
    groupName: grp_powerbi_prd_fin_viewer
    role: Viewer
tags:
  - Finance
```

Validation reads every field. The scripts act on fewer:

| Field | `provision.py` | `drift.py` |
|---|---|---|
| `name` | Finds the workspace by exact name, or creates it | Matches the workspace by exact name |
| `description` | Sets it on every run | Compares it, if the service principal has a role on the workspace |
| `capacity` | Puts the workspace on it on every run | Doesn't compare it |
| `owners` | Adds missing role assignments | Reports owners with no access or another role, and anyone else with access |
| `tags` | Applies missing tags | Reports missing tags and extra tags |
| `domain`, `subDomain` | Doesn't assign them | Doesn't compare them |
| `sensitivityLabel` | Doesn't apply it; labels go on items | Doesn't compare it |
| `environment`, `team`, `region`, `costCenter` | Doesn't use them | Doesn't use them |

To check a manifest and preview the provisioning plan on your machine, run these from the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/validate.py workspaces/prd-fin-revenue.yaml
DRY_RUN=true .venv/bin/python scripts/provision.py
```

## 5. Validation

`validate` runs on each pull request that changes `workspaces/`, `rules/`, `schemas/`, `scripts/` or its own workflow file. It runs `python scripts/validate.py --changed-only`, which checks only the manifests the pull request adds or changes.

A pull request that changes only rules, the schema or scripts therefore gets "No workspace manifests changed in this PR", even if the change breaks existing manifests. Run `validate.py` with no arguments to check every manifest ([Troubleshooting](troubleshooting.md#validate-reports-no-workspace-manifests-changed-in-this-pr)).

With `LIVE_CHECKS` set to `true`, a failed sign-in doesn't fail the job: the live rules report "live check skipped" warnings instead ([Troubleshooting](troubleshooting.md#live-check-skipped)). A 401 or 403 from a live check stops validation with exit code 2, and the report says no manifest has a result.

`validate` posts its report as one comment and updates that comment on each run, even when the check fails. Warnings don't fail the check. For the manifest in [§4](#4-manifest), the comment reads:

```text
# Workspace request validation

**Overall:** ✅ PASS

## `workspaces/prd-fin-revenue.yaml`
- ✅ All rules passed.
```

Change these fields:

```yaml
capacity: contosononprodf2
sensitivityLabel: General
owners:
  - principalType: Group
    identifier: 00000000-0000-0000-0000-000000000a01
    groupName: finance-admins
    role: Admin
  - principalType: User
    identifier: owner@contoso.com
    role: Member
```

The check then fails:

```text
# Workspace request validation

**Overall:** ❌ FAIL

## `workspaces/prd-fin-revenue.yaml`
- ❌ **capacity-allowed-for-env** (block): capacity 'contosononprodf2' does not allow environment 'prd'
- ⚠️ **owner-group-naming** (warn): group display name 'finance-admins' does not match grp_<fabric|powerbi>_<env>_<team>_<role>
- ❌ **prod-extra-controls** (block): environment prd requires sensitivityLabel Confidential or Highly Confidential
- ❌ **prod-extra-controls** (block): environment prd requires at least 2 Group owners
```

## 6. Provisioning

`provision` runs when a push to `main` changes `workspaces/`, `rules/`, `scripts/` or its own workflow file, and when someone runs it from the **Actions** tab. A change to `schemas/` alone doesn't start it. Every run waits for approval of the `production` environment, then signs in and runs `provision.py`, which applies every manifest in `workspaces/`, not only the changed ones.

For each manifest, `provision.py`:

1. Resolves the capacity. A `capacity` that isn't in `approvedCapacities` in `rules/policy.yaml` is an error, even in a dry run. Otherwise it uses the entry's `capacityId`. While that's a placeholder, it uses the `FABRIC_CAPACITY_ID` variable, which applies to every such entry, production included. Without the variable, it looks for a capacity of that name that the service principal can see.
2. Finds the workspace by exact name among the workspaces the service principal has a role on. If there's none, it creates the workspace on the capacity. If there's one, it sets the description and assigns the workspace to the capacity.
3. Adds each owner's missing role assignment. For a `User` owner given by user principal name, it looks up the user's object ID in Microsoft Graph first.

> **Preview** (checked 2026-11-27): Apply Workspace Tags API — [Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/apply-workspace-tags). GA route: apply the tags in the Fabric portal, in the workspace settings under Tags.

4. Applies the manifest's missing tags, if it lists any. It looks each name up among the tenant tags first, then among the tags of the workspace's domain, and skips any other name with a warning.

`provision.py` never deletes a workspace, removes or changes a role assignment, removes a tag, assigns a domain or applies a sensitivity label. [What people still do](#62-what-people-still-do) covers those.

Some failures log a warning and don't fail the run, so read the log after each run. They cover a failed capacity assignment, a failed role assignment, a user it can't look up and a tag name it doesn't know. [Troubleshooting](troubleshooting.md) covers [capacity](troubleshooting.md#the-workspace-stays-on-its-old-capacity), [owner](troubleshooting.md#an-owner-isnt-added) and [tag](troubleshooting.md#a-tag-isnt-applied) warnings.

A 401 or 403 stops the run with exit code 3 and "Stopped: fix the permission above, then rerun." Any other error on a manifest makes the run exit with code 1 after it has tried the remaining manifests ([Exit codes](troubleshooting.md#exit-codes)).

To rehearse, set the `DRY_RUN` variable to `true`. The job still waits for approval and signs in, then `provision.py` logs what it would do and makes no API calls. The log has a section for each manifest. When you run it locally as in [§4](#4-manifest), the section for `prd-fin-revenue` reads:

```text
--- prd-fin-revenue ---
  [dry-run] would ensure workspace exists with capacity=<unresolved-dry-run>
  [dry-run] would set description: Curated revenue tables and reports for finance month-end clo...
  [dry-run] would assign role Admin to Group 00000000-0000-0000-0000-000000000a01
  [dry-run] would assign role Admin to Group 00000000-0000-0000-0000-000000000a02
  [dry-run] would assign role Member to Group 00000000-0000-0000-0000-000000000b01
  [dry-run] would assign role Viewer to Group 00000000-0000-0000-0000-000000000c01
  [dry-run] would apply tags: Finance
```

`<unresolved-dry-run>` means the entry's `capacityId` is still a placeholder and `FABRIC_CAPACITY_ID` isn't set. A real run would look the capacity up by name ([Troubleshooting](troubleshooting.md#not-in-approvedcapacities-or-could-not-resolve-the-capacity-id)).

### 6.1 REST calls

| Step | Call | Notes |
|---|---|---|
| Resolve the capacity | [List Capacities](https://learn.microsoft.com/rest/api/fabric/core/capacities/list-capacities) | Only while the `capacityId` is a placeholder and `FABRIC_CAPACITY_ID` isn't set |
| Find the workspace | [List Workspaces](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspaces) | Returns only workspaces the service principal has a role on |
| Create it | [Create Workspace](https://learn.microsoft.com/rest/api/fabric/core/workspaces/create-workspace) | With the description and capacity |
| Set the description | [Update Workspace](https://learn.microsoft.com/rest/api/fabric/core/workspaces/update-workspace) | On every run for an existing workspace |
| Assign the capacity | [Assign To Capacity](https://learn.microsoft.com/rest/api/fabric/core/workspaces/assign-to-capacity) | Needs Contributor permissions on the capacity and the Admin role on the workspace |
| Add role assignments | [List Workspace Role Assignments](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspace-role-assignments), [Add Workspace Role Assignment](https://learn.microsoft.com/rest/api/fabric/core/workspaces/add-workspace-role-assignment) | Adds only the missing pairs of principal and role |
| Look up a user | [Get user](https://learn.microsoft.com/graph/api/user-get) | Microsoft Graph, for a `User` owner given by user principal name |
| Apply tags | [List Tags](https://learn.microsoft.com/rest/api/fabric/core/tags/list-tags), [Get Workspace](https://learn.microsoft.com/rest/api/fabric/core/workspaces/get-workspace), [Apply Workspace Tags](https://learn.microsoft.com/rest/api/fabric/core/workspaces/apply-workspace-tags) (Preview) | List Tags allows 25 requests a minute, so the script reads it once per run |

`_fabric.py` makes up to five attempts when a call returns 429, 502, 503 or 504. It waits as long as `Retry-After` says, or 2 seconds doubling each time, then fails with "exhausted retries" ([Troubleshooting](troubleshooting.md#429-or-exhausted-retries)).

### 6.2 What people still do

- **Domains.** A Fabric or domain administrator assigns the workspace to its domain in Fabric. `provision.py` doesn't, although the service principal could ([§9](#9-limitations-and-gotchas)).
- **Sensitivity labels.** Label the workspace's items ([§9](#9-limitations-and-gotchas), [Troubleshooting](troubleshooting.md#the-workspace-has-no-sensitivity-label)).
- **Changing or removing access and tags.** Change the role, or remove the role assignment or tag, in Fabric. Change the manifest to match, or the next drift run reports the difference.
- **Retiring a workspace.** Deleting its manifest doesn't delete the workspace, and drift then reports it as unmanaged. Delete it in Fabric.
- **Renaming a workspace.** `provision.py` matches by name, so a new name in the manifest creates a new workspace. Rename the workspace in Fabric after the merge and before you approve the `production` deployment.

## 7. Approval model

A change reaches the tenant after two approvals: a code owner approves the pull request, and a required reviewer of the `production` environment approves the `provision` run.

The shipped `.github/CODEOWNERS` gives every path to one placeholder team:

```text
# Replace the placeholder handles below with your own team(s) or user(s),
# e.g. @your-org/fabric-platform-team or @your-github-handle.

# Default reviewer for all changes
*                       @your-org/fabric-governance-maintainers

# Policy / schema / scripts require platform owner review
/rules/                 @your-org/fabric-governance-maintainers
/schemas/               @your-org/fabric-governance-maintainers
/scripts/               @your-org/fabric-governance-maintainers
/.github/               @your-org/fabric-governance-maintainers

# Production workspace requests need extra scrutiny
/workspaces/prd-*.yaml  @your-org/fabric-governance-maintainers
```

GitHub applies the last pattern that matches a file, and an approval from any one owner of that pattern counts. It skips lines with errors; open the file on GitHub to see them highlighted ([About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)). The `production` environment also needs one approval from any required reviewer. **Prevent self-review** stops whoever started the run from approving it; for a merge, that's the person who merged ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments#required-reviewers)).

If one team owns the code and reviews `production`, one person can pass both gates. To require two people:

- Make a different team the required reviewers of `production`, and turn on **Prevent self-review**.
- Optionally, give `/workspaces/prd-*.yaml` its own team in `CODEOWNERS`, so a production request needs that team's review.

If a pull request merged without code owner review, see [Troubleshooting](troubleshooting.md#a-pull-request-merged-without-code-owner-review).

## 8. Drift detection

`drift` runs daily at 03:17 UTC and when someone runs it from the **Actions** tab. It runs `drift.py`, which compares the tenant's workspaces with the manifests ([Governance rules](governance-rules.md#drift)).

`drift.py` reads the tenant's workspaces and their tags with the admin [List Workspaces](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces) API. It counts only active workspaces of type `Workspace`, so personal workspaces (`Personal`) and the admin monitoring workspace (`AdminWorkspace`) don't count. It reads descriptions with the core [List Workspaces](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspaces), which returns only workspaces the service principal has a role on; the report lists the other managed workspaces as not visible. It doesn't compare capacity, domain or sensitivity label.

> **Preview** (checked 2026-11-27): List Workspace Access Details API — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details). GA route: List Workspace Role Assignments ([Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspace-role-assignments)), which needs Member or higher on each workspace.

`drift.py` reads each managed workspace's role assignments with List Workspace Access Details and ignores the service principal's own role. It makes one call per managed workspace, and the API allows 200 requests an hour. With more than about 200 managed workspaces, a run waits on `Retry-After` and takes more than an hour.

Unmanaged, missing, not visible and drifted workspaces all count as drift. A report looks like this:

```text
# Fabric workspace drift report

- Manifests: 2
- Active workspaces in the tenant: 2
- Unmanaged (in the tenant, no manifest): **1**
  - Sales sandbox
- Missing (manifest, no workspace): **1**
  - dev-plt-sample-hello
- Not visible (the service principal has no workspace role; description not checked): **0**
- Drifted: **1**
  - prd-fin-revenue

## prd-fin-revenue

- description differs from the manifest
- owner 00000000-0000-0000-0000-000000000b01 has Contributor; the manifest gives it Member
- owner 00000000-0000-0000-0000-000000000c01 (Group) has no access; the manifest gives it Viewer
- User Finance Analyst (analyst@contoso.com) has Admin but isn't an owner in the manifest
- tag 'Month-end close' is applied but isn't in the manifest
```

Each run that finds drift opens a new issue titled "Fabric workspace drift detected", labeled `drift` and `governance`, with the report as its body. It doesn't update or close earlier issues, so expect one a day until you fix the drift ([Troubleshooting](troubleshooting.md#a-new-drift-issue-every-day)).

A run fails without opening an issue when `drift.py` exits with code 3 after a 401 or 403, and the job summary says "The drift check didn't run: a call returned 401 or 403." It also fails when `drift.py` exits with code 1 on any other error; the log then has a traceback and there's no report.

### 8.1 Fixing drift

| Report line | What to do |
|---|---|
| Unmanaged | Adopt the workspace ([§8.2](#82-adopting-an-existing-workspace)), or delete it in Fabric if nobody needs it. |
| Missing | If someone renamed the workspace, rename it back. Otherwise run `provision`, which creates it, or delete the manifest. |
| Not visible | A workspace Admin adds the service principal with the Admin role, as in [§8.2](#82-adopting-an-existing-workspace). Until then, `provision` fails on the workspace because its name is taken. |
| `description differs from the manifest` | Run `provision`, which sets it again, or change the manifest to keep the new text. |
| `owner … has no access` | Run `provision`, which adds the role assignment. |
| `owner … has …; the manifest gives it …` | Change the role in Fabric or in the manifest so they agree. `provision` doesn't change existing roles. |
| `… has … but isn't an owner in the manifest` | Remove the access in Fabric, or add the principal to `owners`. |
| `tag '…' isn't applied` | Run `provision`, which applies it. |
| `tag '…' is applied but isn't in the manifest` | Remove the tag in Fabric, or add it to `tags`. |

### 8.2 Adopting an existing workspace

To bring a workspace created by hand under the repository:

1. Check that its name passes [Workspace names](governance-rules.md#workspace-names). If it doesn't, rename the workspace in Fabric first.
2. A workspace Admin adds `gh-fabric-workspace-provisioner` to the workspace with the Admin role.
3. Open a pull request with a manifest whose `name` is the workspace's exact name. List everyone who should keep access in `owners`, and the tags to keep in `tags`.
4. Merge it and approve the `production` deployment. `provision` sets the description and capacity from the manifest and adds missing owners and tags.
5. Run `drift` and fix what it still reports ([§8.1](#81-fixing-drift)).

## 9. Limitations and gotchas

- **Rate limits.** The admin APIs that `drift.py` calls allow 200 requests an hour, and List Tags allows 25 a minute. `_fabric.py` retries throttled calls ([§6.1](#61-rest-calls)).
- **Workspace names are unique in the tenant.** If a workspace the service principal can't see already has the name, creating the workspace fails ([Troubleshooting](troubleshooting.md#the-workspace-name-is-taken)).
- **Domain assignment doesn't need the Fabric administrator role.** The [Assign Domain Workspaces By Ids](https://learn.microsoft.com/rest/api/fabric/admin/domains/assign-domain-workspaces-by-ids) admin API accepts the service principal once "Service principals can access admin APIs used for updates" covers its group. A Fabric or domain administrator can also assign workspaces in Fabric.
- **The service principal can't apply sensitivity labels.** Labels go on items, not workspaces, and [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels) accepts only a user who is a Fabric administrator. Label items by hand, through that call, or with a domain default label (Preview). Keep the service principal out of label publishing policies.
- **Tenant settings propagate slowly.** Up to 15 minutes after a change. Don't run validation immediately after toggling settings.
- **Capacity assignment needs Contributor permissions on the target capacity**, plus the Admin role on the workspace. Give `sg-fabric-workspace-provisioner` Contributor permissions on each capacity. Don't make the service principal a capacity administrator.
- **No marker.** The scripts match workspaces to manifests by exact name. They don't write a `managed-by:` marker into the description.
- **A workspace can have up to 10 tags** ([Apply tags](https://learn.microsoft.com/fabric/governance/tags-apply)).
- **Make a group the Admin owner.** `owners-have-admin` needs one owner with the Admin role but accepts any principal type. If only one user or app holds Admin, managing the workspace depends on that identity.
- **OIDC subjects must match exactly.** If a credential's subject differs from the token's by one character, the sign-in fails ([Troubleshooting](troubleshooting.md#aadsts700213-or-aadsts70021-in-the-azure-login-step-oidc)).
- **Fabric and Power BI admin APIs overlap.** Prefer the Fabric admin APIs, such as [Tenants](https://learn.microsoft.com/rest/api/fabric/admin/tenants) and [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels), over Power BI ones such as [Set Labels As Admin](https://learn.microsoft.com/rest/api/power-bi/admin/information-protection-set-labels-as-admin). Activity data still needs Get Activity Events ([§1.4](#14-extending-the-design)). The shipped scripts call only Fabric and Microsoft Graph.

## 10. Implementation checklist

**Tenant & identity**
- [ ] Create the Entra security group `sg-fabric-workspace-provisioner`.
- [ ] Create the app registration `gh-fabric-workspace-provisioner` and add its service principal to the group.
- [ ] Add the three federated credentials in §1.3.
- [ ] Grant the Microsoft Graph application permissions `GroupMember.Read.All` (or `Group.Read.All`) and `User.Read.All`, with admin consent.
- [ ] Give the group Contributor permissions on each approved capacity.
- [ ] Turn on the tenant settings in §1.2 for the group, and allow 15 minutes for them to take effect.

**Repository**
- [ ] In `.github/CODEOWNERS`, replace `@your-org/fabric-governance-maintainers` with your team.
- [ ] Put each capacity's ID in `approvedCapacities`, in both `rules/policy.yaml` and `api/policy.yaml` ([Record your values](setup.md#record-your-values)).
- [ ] Replace the placeholder owners in `workspaces/dev-plt-sample-hello.yaml` ([Smoke test](setup.md#smoke-test)).

**GitHub**
- [ ] Add the repository variables, register the `fabric-gov` runner, create the `production` environment, protect `main` and enable the workflows ([Configure the repository](setup.md#configure-the-repository)).
- [ ] Make a second team the `production` reviewers and turn on **Prevent self-review** ([§7](#7-approval-model)).
- [ ] Decide how pull request runs sign in ([Pull request runs](identity-model.md#pull-request-runs)).

**First run**
- [ ] Run `drift` from the **Actions** tab to list the workspaces you already have.
- [ ] Adopt the ones to keep ([§8.2](#82-adopting-an-existing-workspace)).
- [ ] Run the [smoke test](setup.md#smoke-test).
- [ ] Run `drift` again and close the earlier drift issues.
