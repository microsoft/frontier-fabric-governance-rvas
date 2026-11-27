# Challenge 04 — Access & RBAC lifecycle

> **Outcome:** every Fabric workspace role assignment is declared in `access/`,
> Group-first, with an `expiresOn` date on every User binding. The provisioner
> applies the manifest, drift opens an issue, and expiring bindings open review
> PRs.

## Why this challenge exists

Role sprawl builds up quietly: contractors added straight to a workspace and
never removed, user accounts as the only admins, and "temporary" elevation that
becomes permanent. Declaring roles in Git with expiry dates makes the sprawl
visible, and every change gets a reviewer.

## Learning objectives

1. Declare workspace role assignments as code, with an expiry date on every User
   binding.
2. Enforce "Group preferred, User by exception" in validation.
3. Reconcile workspaces with their manifests, and report drift before removing
   anything.
4. Run a quarterly access review as pull requests opened by a scheduled workflow.
5. Grant break-glass access that expires on its own, and alert owners before
   time-bound grants expire.
6. Check live roles with the Fabric Core MCP, and audit admin coverage with the
   `onelake-catalog-cli` Skill.

## Prerequisites

- Challenges 00–01 complete. You have the automation service principal (SPN),
  its group `sg-fabric-workspace-provisioner` enabled in the four tenant settings
  from [challenge 00](../00-setup/challenge.md), and the manifest
  `workspaces/dev-plt-myteam-playground.yaml`. Task 6 relies on the "Service
  principals can access read-only admin APIs" setting.
- The SPN has the Microsoft Graph application permissions `GroupMember.Read.All`
  (or `Group.Read.All`) and `User.Read.All`, with admin consent. The scripts use
  them to resolve UPNs to object IDs.
- The Fabric Core MCP server and Skills for Fabric, installed as shown below.
- Optional: the Microsoft MCP Server for IT Admins, so chat can look up users and
  groups by name. It signs in as you, so the workflows can't use it, and no task
  needs it. Setup is in [MCP tips](#mcp-tips).

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

## Tasks

### Task 1 — Access manifest and schema

Add `schemas/access.schema.json` and one manifest per workspace under `access/`,
named after the workspace. Start with `access/dev-plt-myteam-playground.yaml`:

```yaml
workspace: dev-plt-myteam-playground
allowRemovals: false
bindings:
  - principalType: Group
    identifier: 44444444-4444-4444-4444-444444444444
    displayName: grp_fabric_dev_plt_admin
    role: Admin
    expiresOn: null
  - principalType: Group
    identifier: 77777777-7777-7777-7777-777777777777
    displayName: grp_fabric_dev_plt_member
    role: Member
    expiresOn: null
  - principalType: Group
    identifier: 88888888-8888-8888-8888-888888888888
    displayName: grp_fabric_dev_plt_viewer
    role: Viewer
    expiresOn: null
  - principalType: ServicePrincipal
    identifier: 99999999-9999-9999-9999-999999999999   # service principal object ID, not the app (client) ID
    displayName: gh-fabric-workspace-provisioner
    role: Admin
    expiresOn: null
  - principalType: User
    identifier: workspace-owner@contoso.com
    displayName: Workspace owner
    role: Member
    expiresOn: "2027-02-19"
    justification: "Pilot owner for the playground; re-justify at each review."
```

Replace the placeholder IDs with the object IDs of your groups and your SPN.
List every `owners` entry from the workspace manifest here too, with the same
principal and role; Task 2 checks it.

The schema enforces these fields:

- `workspace`: the workspace name.
- `allowRemovals`: boolean, default `false` (Task 3).
- `principalType`: `Group`, `User` or `ServicePrincipal`.
- `identifier`: an object ID. `User` bindings may use a UPN instead.
- `displayName`: the group, SPN or person name, so reviewers can read the
  bindings. Task 2 checks group names against it.
- `role`: `Admin`, `Member`, `Contributor` or `Viewer`.
- `expiresOn`: `null`, a date such as `"2027-02-19"`, or a UTC date-time such as
  `"2026-11-28T14:00:00Z"` for break-glass (Task 5). Quote it, so YAML loaders
  keep it a string.
- `justification`: required on `User` bindings.
- `breakGlass`: optional boolean that only the Task 5 workflow sets.

The workspace's `environment`, `team` and `owners` stay in
`workspaces/dev-plt-myteam-playground.yaml`, and the validator reads them from
there. Pick an `expiresOn` within 90 days of the day you open the PR.

### Task 2 — Validation rules

Extend `scripts/validate.py` to check `access/*.yaml`, and add `access/**` to
the `paths` filter in `.github/workflows/validate.yml`. The rule IDs are
suggestions. Each rule fires when:

- `access-workspace-declared` (block): the file name doesn't match `workspace`,
  or `workspaces/<workspace>.yaml` doesn't exist.
- `access-min-two-admins` (block): no Admin binding is a Group, and fewer than
  two are Users. Service principals don't count: the provisioner is always an
  Admin, and it can't stand in for a person.
- `access-group-name` (warn): a Group `displayName` doesn't follow
  `grp_<fabric|powerbi>_<env>_<team>_<role>` with the workspace manifest's
  `environment` and `team` and the binding's role, such as
  `grp_fabric_dev_plt_admin`. It's the pattern the rules engine checks for
  `owners[].groupName`:
  `^grp_(fabric|powerbi)_(sbx|dev|stg|prd)_[a-z0-9]{2,6}_(admin|member|contributor|viewer)$`.
- `access-group-preferred` (warn): a User binding has the Admin role.
- `access-user-must-expire` (block): a User binding has no `expiresOn`.
- `access-expiry-within-90-days` (block): a User binding's `expiresOn` is more
  than 90 days after the day validation runs.
- `access-justification-for-users` (block): a User binding has no
  `justification`, or one shorter than 30 characters.
- `access-owners-declared` (block): an `owners` entry in the workspace manifest
  is missing here, or has a different role. Task 3 explains why.
- `prd-no-user-admins` (block): a User binding has the Admin role on a workspace
  whose manifest says `environment: prd`. Decide production from that field,
  never from the name.

### Task 3 — Reconcile and report drift

Extend `scripts/provision.py` so each `access/<workspace>.yaml` drives that
workspace's role assignments. Add `access/**` to the `paths` filter in
`.github/workflows/provision.yml`, and a daily `schedule` so expiry takes effect
without a merge.

1. Resolve the workspace ID and list its role assignments
   (`GET /v1/workspaces/{workspaceId}/roleAssignments`, following
   `continuationToken`).
2. Resolve UPNs to object IDs through Microsoft Graph. On 401 or 403, stop with
   an error that names the missing permission. Never treat either as "user not
   found".
3. Treat a binding whose `expiresOn` has passed as absent.
4. Add missing bindings (`POST`) and fix roles that differ
   (`PATCH .../roleAssignments/{roleAssignmentId}`).
5. Delete assignments that aren't declared, or have expired, only when the
   manifest says `allowRemovals: true`. Never delete the provisioner's own
   assignment.

With `DRY_RUN=true`, print the additions, updates and removals without applying
them.

When `access/<workspace>.yaml` exists, skip the `owners` loop in
`reconcile_workspace`. Otherwise the next run adds back an owner you removed.
`owners` still seeds workspaces that have no access manifest yet.

Extend `scripts/drift.py`, which `drift.yml` runs daily, with an access section
in `drift-report.md`: assignments that aren't declared, declared bindings that
are missing, role mismatches, and expired bindings that are still live. Any of
them makes the script exit non-zero, so the workflow opens its drift issue.

Start each workspace with `allowRemovals: false` and read its drift issue. Once
the list of removals is right, set `allowRemovals: true` in a reviewed PR. From
then on the manifest is authoritative.

The scripts call the REST API rather than the Core MCP because they run
unattended in GitHub Actions as the SPN; use the MCP for checks from chat
(Task 6). If you manage workspaces with Terraform, the
`fabric_workspace_role_assignment` resource is the alternative.

### Task 4 — Quarterly access review

Add `.github/workflows/access-review.yml`:

- Triggers: cron `0 9 1 */3 *` (09:00 UTC on the first day of January, April,
  July and October), plus `workflow_dispatch` so you can test it.
- For each `access/*.yaml`, list the bindings that have expired or expire before
  the next review.
- Open one PR per workspace that removes those bindings. To keep a binding, the
  reviewer sets a new `expiresOn`, at most 90 days out, and updates its
  `justification` in the same PR.
- If a binding is also in the workspace manifest's `owners`, the PR removes it
  there too, or `access-owners-declared` blocks it.
- List the workspace's Group bindings in the PR body, and ask the reviewer to
  confirm each group's membership is still right. Group owners manage membership
  in Microsoft Entra.
- Request review from the workspace's code owners.

Removing a binding from the manifest removes the assignment only when
`allowRemovals: true` (Task 3). This workflow reads only the YAML files, so it
needs no Fabric access.

### Task 5 — JIT break-glass

Add `.github/PULL_REQUEST_TEMPLATE/jit-break-glass.md`, which asks for the
incident link, the person, the role, the reason and the approver. Then add
`.github/workflows/access-jit.yml`:

1. When a PR gets the `break-glass` label, the workflow sets `breakGlass: true`
   and an `expiresOn` 24 hours ahead (UTC date-time) on every User binding the PR
   adds, and commits that change to the PR branch.
2. After merge, the provisioner adds the assignment (Task 3).
3. An hourly job deletes break-glass assignments whose `expiresOn` has passed,
   with the same REST calls as Task 3 and even when `allowRemovals` is `false`,
   then opens a PR that removes the binding.

Each break-glass grant leaves three linked records: the PR that granted it, the
provisioning run that applied it and the PR that removed it.

Next, alert owners a week before a time-bound grant expires. With the Core MCP
`create_item` tool, create an Eventhouse named `eh_gov_access` in
`dev-plt-myteam-playground`. It comes with a KQL database of the same name
([Learn](https://learn.microsoft.com/fabric/real-time-intelligence/create-eventhouse)).

In a Copilot CLI session:

```text
/eventhouse-cli In workspace "dev-plt-myteam-playground", create the table AccessGrants(workspace:string, principal:string, role:string, breakGlass:bool, expiresOn:datetime, observedAt:datetime) in the KQL database eh_gov_access.
```

After each run, `scripts/provision.py` appends one row per time-bound binding
with `.set-or-append` or `.ingest inline` through the KQL management endpoint.
The SPN's workspace Admin role covers it. Run the provisioner once, so the table
has rows before you create the alert.

In a Copilot CLI session:

```text
/activator-cli In workspace "dev-plt-myteam-playground", create an Activator named act_gov_access_expiry with a KQL source on the KQL database eh_gov_access. Run this query in time-axis mode on observedAt every 3600 seconds, returning all rows. Use grantId as the object ID, and email the workspace owners when daysLeft becomes less than 7.
declare query_parameters(startTime:datetime, endTime:datetime);
AccessGrants
| where observedAt between (startTime .. endTime)
| extend daysLeft = datetime_diff('day', expiresOn, observedAt)
| extend grantId = strcat(workspace, "/", principal, "/", role)
```

### Task 6 — Check live roles from chat

In a Copilot CLI session with the Fabric Core MCP connected:

```text
Use list_workspace_roles for "dev-plt-myteam-playground". Group the assignments by role, compare them with access/dev-plt-myteam-playground.yaml and list every difference.
Which User principals hold Admin on workspaces whose manifest under workspaces/ says environment: prd?
```

The answers should match `access/`. A difference is drift, and Task 3's drift
report should list it too.

Then audit admin coverage across workspaces with a Skill. It calls admin APIs,
so run it signed in as a Fabric administrator, or as the SPN.

> **Preview** (checked 2026-11-27): Admin workspace access details API — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details). GA route: count Admins per workspace with list_workspace_roles.

In a Copilot CLI session:

```text
/onelake-catalog-cli Find workspace admin gaps for the workspaces listed in access/, with a threshold of 2 admins. Show single-admin workspaces, workspaces with no human admin, and service principal admins separately.
```

Read the results with these points in mind:

- The Skill counts a group admin as one admin and doesn't resolve its members,
  so a Group-first workspace shows one admin and no human admin. Check the
  group's members in Microsoft Entra before you call it a gap.
- Service principal admins are counted separately: they meet a numeric
  threshold but add no accountable person. That's why `access-min-two-admins`
  ignores them.
- Single-admin workspaces are the main finding. The Skill can't fix them,
  because no admin API writes workspace roles. Send fixes to the workspace
  admins as PRs that change `access/`.

## Success criteria

- [ ] Every managed workspace has `access/<name>.yaml`, and validation passes.
- [ ] A PR that adds a User Admin to a workspace whose manifest says
      `environment: prd` is blocked.
- [ ] A User binding without `expiresOn`, or with one more than 90 days out, is
      blocked.
- [ ] After a merge, the workspace's role assignments match `access/`, and an
      assignment added outside the repo shows up in the drift report.
- [ ] Running the review workflow with a binding that expires before the next
      review opens a PR for that workspace.
- [ ] A `break-glass`-labeled PR gets a 24-hour `expiresOn`, and within an hour
      of expiry the assignment is gone and a PR removes the binding.
- [ ] Moving a test binding's `expiresOn` from 10 days out to 5 days out
      triggers the Activator alert after the next provisioner run.
- [ ] The Core MCP answers match `access/`, and you can explain each gap that
      `/onelake-catalog-cli` reports.

## Stretch goals

- **Time-bound elevation with PIM for Groups.** Bind a group to the Admin role
  and let people activate its membership for a few hours with Privileged
  Identity Management
  ([Learn](https://learn.microsoft.com/entra/id-governance/privileged-identity-management/concept-pim-for-groups)).
  Compare it with Task 5: PIM elevates through group membership, so `access/`
  doesn't change.
- **Entra access reviews.** Review the members of the `grp_fabric_*` groups with
  Microsoft Entra access reviews
  ([Learn](https://learn.microsoft.com/entra/id-governance/access-reviews-overview)).
  The repo review covers bindings; Entra covers who is in each group.
- **Per-item access.** Report item-level sharing, such as Build on a semantic
  model, next to workspace roles. No Core API changes item sharing, so keep it
  report-only.
- **Teams notification.** When the review workflow opens a PR, post a link in
  the workspace team's Teams channel.

## MCP tips

- The Core MCP role tools (`list_workspace_roles`, `get_workspace_role`,
  `add_workspace_role`, `update_workspace_role` and `delete_workspace_role`) take
  object IDs, not emails or group names.
- A role change made from chat is drift until `access/` changes too. With
  `allowRemovals: true`, the next provisioner run removes it. Use chat to look,
  and PRs to change.
- **Microsoft MCP Server for IT Admins (optional).** It lets chat resolve users
  and groups by name; the Core MCP tools page calls it the Microsoft MCP Server
  for Enterprise. It supports delegated permissions only, so it runs as you,
  never as the SPN, and no task needs it. To set it up:
  1. A Cloud Application Administrator or Application Administrator registers an
     app for "Accounts in this organizational directory only".
  2. In the app's **Manifest**, add `http://127.0.0.1` to
     `publicClient.redirectUris`. The portal's redirect URI box rejects it.
  3. Add the delegated Microsoft Graph permissions `MCP.Server.Access`,
     `User.Read` and `EntitlementMgmt-SubjectAccess.ReadWrite`, plus what your
     prompts need, such as `User.Read.All`. Grant admin consent on the
     **API permissions** page.
  4. Add the server under `mcpServers` in `~/.copilot/mcp-config.json`, as shown
     below.

```json
{
  "mcpServers": {
    "mcp-admin": {
      "type": "http",
      "url": "https://mcp.svc.cloud.microsoft/admin",
      "headers": {},
      "tools": ["*"],
      "oauthClientId": "<REGISTERED_APP_CLIENT_ID>",
      "oauthPublicClient": true
    }
  }
}
```

In the Copilot app, use **Customize** > **MCP** > **Add server** > **HTTP** with
the same name, URL and client ID. The older `/enterprise` URL is being replaced
by `/admin`.

## Skills tips

- `/eventhouse-cli` creates tables and runs management commands in an existing
  KQL database. It doesn't create the Eventhouse; use the Core MCP `create_item`
  tool for that.
- `/activator-cli` needs the KQL database's item ID and its workspace ID, not
  the Eventhouse ID. Return all rows from the query, and let a "becomes"
  condition do the filtering, so the alert fires once per crossing. Use
  `startTime` and `endTime` in time-axis mode instead of `ago()`.
- `/onelake-catalog-cli` reads tenant-wide admin APIs, so run it as a Fabric
  administrator or as the SPN. It only reports; changes go through `access/`.

## References

- [Add Workspace Role Assignment (REST)](https://learn.microsoft.com/rest/api/fabric/core/workspaces/add-workspace-role-assignment)
- [Roles in workspaces](https://learn.microsoft.com/fabric/fundamentals/roles-workspaces)
- [Core MCP server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Get started with the Microsoft MCP Server for IT Admins](https://learn.microsoft.com/graph/mcp-server/get-started)
- [List Workspace Access Details (admin, Preview)](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details)
- [Privileged Identity Management](https://learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-configure)
