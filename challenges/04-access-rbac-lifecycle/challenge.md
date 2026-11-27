# Challenge 04 — Access & RBAC lifecycle

> **Outcome:** every Fabric workspace role assignment is declared in `access/`,
> Group-first, with an `expiresOn` date on every User binding, and so is each
> workspace identity. The provisioner applies the manifest, drift opens an
> issue, and expiring bindings open review PRs.

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
4. Run a quarterly access review from a scheduled workflow, covering bindings,
   OneLake security role members and item shares.
5. Grant break-glass access that expires on its own, and alert owners before
   time-bound grants expire.
6. Check live roles with the Fabric Core MCP, and audit admin coverage with the
   `onelake-catalog-cli` Skill.
7. Create each workspace's identity from its manifest, and review every Fabric
   identity in the tenant.

## Prerequisites

- Challenges 00–01 complete. You have the automation service principal (SPN),
  its group `sg-fabric-workspace-provisioner` enabled in the four tenant settings
  from [challenge 00](../00-setup/challenge.md), and the manifest
  `workspaces/dev-plt-myteam-playground.yaml`. Tasks 4 and 6 rely on the
  "Service principals can access read-only admin APIs" setting.
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
workspaceIdentity: true
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
- `workspaceIdentity`: boolean, default `false`. `true` gives the workspace a
  workspace identity (Task 7).
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
- Open one PR per workspace that removes those bindings, or an issue when
  nothing expires, so every workspace is reviewed each quarter. To keep a
  binding, the reviewer sets a new `expiresOn`, at most 90 days out, and updates
  its `justification` in the PR.
- If a binding is also in the workspace manifest's `owners`, the PR removes it
  there too, or `access-owners-declared` blocks it.
- List the workspace's Group bindings in the PR or issue, and ask the reviewer
  to confirm each group's membership is still right. Group owners manage
  membership in Microsoft Entra.
- Request review from the workspace's code owners, or mention them in the issue.

Removing a binding from the manifest removes the assignment only when
`allowRemovals: true` (Task 3).

The review also covers access that workspace roles don't show. To read it, the
workflow signs in as the SPN through OIDC, like `drift.yml`, and it never writes
to Fabric.

OneLake security roles decide what Viewers, and people who have only the Read
permission on an item, can see in a lakehouse, mirrored database or mirrored
catalog. Admins, Members and Contributors see all the data whatever the roles
say
([Learn](https://learn.microsoft.com/fabric/onelake/security/data-access-control-model)).
For each of those items, list its roles with List Data Access Roles
(`GET /v1/workspaces/{workspaceId}/items/{itemId}/dataAccessRoles`, following
`continuationToken`), and add each role's members to the PR or issue:

- `microsoftEntraMembers` are users and groups, by object ID. Resolve them to
  names through Microsoft Graph, as in Task 3.
- `fabricItemMembers` aren't people. Each entry stands for everyone who holds an
  item permission, such as `ReadAll`, on the item at `sourcePath`. A new
  lakehouse gets a DefaultReader role with such an entry, so everyone with
  ReadAll on it can read all its data while DefaultReader is unchanged.

The workflow calls REST because it runs unattended; from chat, the Core MCP
`onelake_list_data_access_roles` tool lists the same roles. This review only
reads roles; [challenge 10](../10-onelake-security-as-code/challenge.md) manages
them as code.

> **Preview** (checked 2026-11-27): Admin item access details API — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/items/list-item-access-details). GA route: review workspace roles and OneLake security roles only.

Sharing an item gives people access to it without a workspace role, and no Core
API manages item permissions. For each item, call
`GET /v1/admin/workspaces/{workspaceId}/items/{itemId}/users`, and list in the
PR or issue the principals that hold item permissions but have no binding in
`access/`. Pass `type` for reports, dashboards, semantic models, apps and
dataflows. The API allows 200 requests an hour, so pace the calls, and after a
429 wait as long as `Retry-After` says. The SPN can call it through the
"Service principals can access read-only admin APIs" setting.

Shares can't be declared in `access/`, so they aren't drift. The reviewer
decides which to keep and removes the rest in the Fabric portal.

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

If you also use the hosted OneLake MCP server (Preview), don't treat its
`onelake_get_principal_access` result as proof of access: it can report
`canRead: false` even when you can read the item. OneLake checks permissions on
each operation, so the operation's own result is the answer
([Learn](https://learn.microsoft.com/fabric/onelake/onelake-hosted-mcp)).

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

### Task 7 — Workspace identity

A workspace identity is a service principal that Fabric creates and manages for
one workspace. OneLake shortcuts, pipelines, semantic models and Dataflows Gen2
(CI/CD) in the workspace can authenticate with it when they connect to data
sources, and trusted workspace access relies on it. Only workspace Admins can
create or delete it, it starts with no workspace role, and My workspace can't
have one
([Learn](https://learn.microsoft.com/fabric/security/workspace-identity)).

1. Set `workspaceIdentity: true` in `access/dev-plt-myteam-playground.yaml`, as
   in Task 1.
2. In `scripts/provision.py`, call Get Workspace
   (`GET /v1/workspaces/{workspaceId}`). Its `workspaceIdentity` field holds
   the identity's `applicationId` and `servicePrincipalId`. If the manifest says
   `true` and the response has no identity, call
   `POST /v1/workspaces/{workspaceId}/provisionIdentity`. It returns 200 with
   the identity, or 202 with a `Location` URL to poll. It needs the workspace
   Admin role, which the SPN holds. No Core MCP tool creates an identity, so
   the script uses REST. With Terraform, set
   `identity = { type = "SystemAssigned" }` on `fabric_workspace` instead.
3. In the access section of `scripts/drift.py`, report each workspace whose
   identity doesn't match its flag: an identity the manifest doesn't declare,
   or `true` with no identity.
4. Never delete an identity from a script. Items that use it break, and a
   deleted identity can't be restored. To remove one, set
   `workspaceIdentity: false` in a reviewed PR; then a workspace Admin deletes
   it on the **Workspace identity** tab of the workspace settings. Until they
   do, the drift issue lists it.
5. Give the identity a workspace role only when a feature needs one. Add a
   `ServicePrincipal` binding whose `identifier` is its `servicePrincipalId`
   and whose `displayName` is the workspace name, which the identity shares.
   For example, OneLake shortcuts that use trusted workspace access need the
   identity as a Contributor, and the workspace on an F SKU capacity rather
   than a trial
   ([Learn](https://learn.microsoft.com/fabric/security/security-trusted-workspace-access)).
   [Challenge 11](../11-network-exfiltration-guardrails/challenge.md) uses
   trusted workspace access.

Check the result in a Copilot CLI session with the Fabric Core MCP connected:

```text
Use get_workspace for "dev-plt-myteam-playground" and show its workspaceIdentity. Does access/dev-plt-myteam-playground.yaml bind its servicePrincipalId to a role?
```

Keep these points in mind:

- Workspace Admins, Members and Contributors can pick the identity in
  connections, and anyone given access to it can act as it. Task 4's review of
  those bindings is also the review of who can use the identity.
- Fabric also creates a service principal and an app registration for the
  identity in Microsoft Entra ID. Don't change or delete either in Azure: items
  that use the identity stop working, and Fabric may revert the change. Adding
  API permissions there is supported.
- Deleting a workspace removes its identity only when the workspace is
  permanently deleted, normally when the retention period ends. A restored
  workspace needs a new identity, which the provisioner creates. If you delete
  workspaces and recreate them with the same name, delete the identity first,
  or ask a Fabric administrator to permanently delete the workspace during the
  retention period. Otherwise app registrations with the same name build up.

The manifests cover only managed workspaces, so review identities across the
tenant too. At each quarterly review, a Fabric administrator opens OneLake
catalog > **Govern** > **Configurations** > **Fabric identities** and selects
**Export** to download the list as a CSV file
([Learn](https://learn.microsoft.com/fabric/admin/fabric-identities-manage)).
Each identity should belong to a workspace whose access manifest says
`workspaceIdentity: true`, and its state should be Active. For any other
identity, bring its workspace under a manifest, or ask the workspace's Admins
whether they still need it. Get Workspace doesn't return the state, so the
export is where Inactive, Deleting, Unusable, Failed and DeleteFailed
identities show up. For a Failed identity, Learn's troubleshooting steps are to
wait an hour, delete it, and create it again at least 5 minutes later; the
provisioner's next run does the creating.

To see when identities were created, retrieved or deleted, and when tokens were
issued for them, search the **Activities - friendly names** field in Microsoft
Purview Audit for "fabric identity".

A tenant can have 10,000 Fabric identities by default. A Fabric administrator
can set a different maximum with the "Define maximum number of Fabric
identities in a tenant" setting, under Developer settings in OneLake catalog >
**Govern** > **Configurations** > **Tenant settings**, or in the Admin portal's
**Tenant settings**.

## Success criteria

- [ ] Every managed workspace has `access/<name>.yaml`, and validation passes.
- [ ] A PR that adds a User Admin to a workspace whose manifest says
      `environment: prd` is blocked.
- [ ] A User binding without `expiresOn`, or with one more than 90 days out, is
      blocked.
- [ ] After a merge, the workspace's role assignments match `access/`, and an
      assignment added outside the repo shows up in the drift report.
- [ ] Running the review workflow with a binding that expires before the next
      review opens a PR for that workspace, and a workspace with nothing
      expiring gets an issue.
- [ ] For a lakehouse in the workspace, the review lists the members of its
      OneLake security roles.
- [ ] A `break-glass`-labeled PR gets a 24-hour `expiresOn`, and within an hour
      of expiry the assignment is gone and a PR removes the binding.
- [ ] Moving a test binding's `expiresOn` from 10 days out to 5 days out
      triggers the Activator alert after the next provisioner run.
- [ ] The Core MCP answers match `access/`, and you can explain each gap that
      `/onelake-catalog-cli` reports.
- [ ] After a merge with `workspaceIdentity: true`, the provisioner has created
      the identity, and `get_workspace` shows its `servicePrincipalId`.
- [ ] The Fabric identities export matches the `workspaceIdentity` flags, and
      every identity is Active.

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
  The repo review covers what each workspace grants; Entra covers who is in
  each group.
- **Teams notification.** When the review workflow opens a PR or an issue, post
  a link in the workspace team's Teams channel.

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
- [OneLake security access control model](https://learn.microsoft.com/fabric/onelake/security/data-access-control-model)
- [List Data Access Roles (REST)](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/list-data-access-roles)
- [List Item Access Details (admin, Preview)](https://learn.microsoft.com/rest/api/fabric/admin/items/list-item-access-details)
- [Hosted OneLake MCP server (Preview)](https://learn.microsoft.com/fabric/onelake/onelake-hosted-mcp)
- [Workspace identity](https://learn.microsoft.com/fabric/security/workspace-identity)
- [Manage Fabric identities](https://learn.microsoft.com/fabric/admin/fabric-identities-manage)
- [Trusted workspace access](https://learn.microsoft.com/fabric/security/security-trusted-workspace-access)
