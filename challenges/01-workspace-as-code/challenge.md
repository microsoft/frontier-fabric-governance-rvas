# Challenge 01 — Workspace as code

> **Outcome:** Your Fabric workspaces are created and changed only through pull
> requests against YAML manifests, and a daily drift check reports changes made
> anywhere else.

## Why this challenge exists

Each workspace is a YAML manifest in `workspaces/`, and every change to it
follows one path:

```text
pull request that adds or changes workspaces/<name>.yaml
  → validate: schema and governance rules, result posted as a comment
  → code owner review, merge to main
  → provision waits for approval in the production environment
  → provision.py signs in as the SPN through OIDC and calls the Fabric REST API
  → drift.py compares the tenant with the manifests every day
```

The manifest is the source of truth. A change made in the portal or from chat
is drift until a manifest says the same or someone undoes the change.

The SPN has a different job in each workflow. In validate, it runs the live
checks: Microsoft Graph confirms that owner groups exist, and List Tags confirms
that tags exist. In provision, it creates and updates workspaces. In drift, it
lists every workspace and reads each managed workspace's access through the
read-only admin APIs.

## Learning objectives

1. Write a workspace manifest that passes the schema and the governance rules.
2. Read the `validate` result and fix a change the rules block.
3. Provision through an approved deployment and read the log.
4. Check the result from chat with the Core MCP server and
   `onelake-catalog-cli`.
5. Detect drift, fix it and close the drift issues.
6. Retire a managed workspace and record the decision in a pull request.

## Prerequisites

- [Challenge 00](../00-setup/challenge.md) complete: the validate, provision and
  drift workflows run in your copy of this repository.
- A test user in your tenant who isn't in either group you create in Task 1.
  Task 5 gives it access in the portal.

## Tasks

### Task 1 — Declare your playground workspace

A manifest describes one workspace. Read
[Governance rules](../../docs/governance-rules.md), then the schema in
[`schemas/workspace.schema.json`](../../schemas/workspace.schema.json) and the
rules in [`rules/policy.yaml`](../../rules/policy.yaml). The fields to get
right:

- `name` is `<environment>-<team>-<workload>`, and its first two segments must
  equal the `environment` and `team` fields. The file is
  `workspaces/<name>.yaml`.
- `domain` and `subDomain` say where the workspace belongs. Challenge 03
  assigns them in Fabric.
- `capacity` is a logical name from `rules/policy.yaml`. That capacity must
  allow the environment, and `region` must be the capacity's region.
- `owners` has at least two entries, at least one of them a group and at least
  one with the Admin role.

Workspace roles go to Microsoft Entra security groups, named
`grp_<fabric|powerbi>_<environment>_<team>_<role>`. The Core MCP server has no
tools for Microsoft Entra ID, so use the Azure CLI. Create an admin group and a
member group, add yourself to the admin group, and print both object IDs:

```bash
az ad group create --display-name grp_fabric_dev_plt_admin --mail-nickname grp_fabric_dev_plt_admin
az ad group create --display-name grp_fabric_dev_plt_member --mail-nickname grp_fabric_dev_plt_member
az ad group member add --group grp_fabric_dev_plt_admin --member-id "$(az ad signed-in-user show --query id -o tsv)"
az ad group show --group grp_fabric_dev_plt_admin --query id -o tsv
az ad group show --group grp_fabric_dev_plt_member --query id -o tsv
```

Create `workspaces/dev-plt-myteam-playground.yaml`:

```yaml
name: dev-plt-myteam-playground
environment: dev
team: plt
domain: dom-plt-data
subDomain: sdm-plt-sample
description: "Playground where the data platform team tries workspace changes before it proposes them for shared workspaces."
capacity: contosononprodf2
region: northeurope
sensitivityLabel: General
costCenter: CC-1001
owners:
  - principalType: Group
    identifier: 44444444-4444-4444-4444-444444444444
    role: Admin
    groupName: grp_fabric_dev_plt_admin
  - principalType: Group
    identifier: 77777777-7777-7777-7777-777777777777
    role: Member
    groupName: grp_fabric_dev_plt_member
```

Replace `44444444-4444-4444-4444-444444444444` with the admin group's object ID
and `77777777-7777-7777-7777-777777777777` with the member group's.

The sample manifest, `workspaces/dev-plt-sample-hello.yaml`, makes
`workspace-owner@contoso.com` a Member. That user isn't in your tenant, so
provision.py would skip it and drift.py would report it. Replace the sample's
`owners` with your two groups:

```yaml
owners:
  - principalType: Group
    identifier: 44444444-4444-4444-4444-444444444444
    role: Admin
    groupName: grp_fabric_dev_plt_admin
  - principalType: Group
    identifier: 77777777-7777-7777-7777-777777777777
    role: Member
    groupName: grp_fabric_dev_plt_member
```

Use your groups' object IDs here too. Then check both files:

```bash
.venv/bin/python scripts/validate.py
```

The report says `**Overall:** ✅ PASS`, with `- ✅ All rules passed.` for each
file.

Turn on the live checks, so that the `validate` check also confirms that each
owner group exists in Microsoft Entra ID:

```bash
gh variable set LIVE_CHECKS --body true
```

From now on, a manifest that still holds a placeholder ID fails in the pull
request with `group <id> not found in Entra`. Your local runs skip the live
checks, because the variable applies only to the workflows.

Open a pull request with both files:

```bash
git switch -c add-playground
git add workspaces/dev-plt-myteam-playground.yaml workspaces/dev-plt-sample-hello.yaml
git commit -m "Add the playground workspace and set the sample's owners"
git push -u origin add-playground
gh pr create --web
```

`gh pr create --web` opens the pull request form in the browser, filled in from
the repository's pull request template. Fill in the type, business purpose and
workspace fields, then create the pull request. Watch the check and read its
comment:

```bash
sleep 15
gh pr checks --watch
gh pr view --comments
```

The `validate` check passes, and its comment lists both files with
`- ✅ All rules passed.` Leave the pull request open for Task 2.

### Task 2 — See the rules block a change

No MCP tool runs this repository's rules, so use validate.py. In the playground
manifest, change `costCenter` to `CC-3000`, then check the file:

```bash
.venv/bin/python scripts/validate.py workspaces/dev-plt-myteam-playground.yaml
echo $?
```

The change is blocked, and the exit code is 1:

```text
# Workspace request validation

**Overall:** ❌ FAIL

## `workspaces/dev-plt-myteam-playground.yaml`
- ❌ **cost-center-allow-list** (block): costCenter 'CC-3000' not in approvedCostCenters
```

Undo the change:

```bash
git restore workspaces/dev-plt-myteam-playground.yaml
```

Try each change below the same way, and restore the file after each one:

| Change | Rule | Message |
| ------ | ---- | ------- |
| `environment: stg` | `name-segments-match-fields` | `name segment 'environment' is 'dev' but field 'environment' is 'stg'` |
| `capacity: contosoprodf4` | `capacity-allowed-for-env` | `capacity 'contosoprodf4' does not allow environment 'dev'` |
| `role: Member` for the admin group | `owners-have-admin` | `at least one owner must have role=Admin` |
| `principalType: User` for both owners | `owners-min-two-groups` | `need >= 2 owners and at least one Group` |

Three more change the name or the owner list:

- Delete the second owner. The schema check fails, reported as `schema`,
  because `owners` needs at least two entries.
- Set `name: dev-plt-my-playground`. `manifest-filename` fails because the file
  name no longer matches, and `no-personal-workspaces` fails because the
  segment `my` looks personal.
- Set `name: plt-dev-playground`. The name fails the schema's pattern, and
  `manifest-filename` fails too.

[`rules/policy.yaml`](../../rules/policy.yaml) lists each rule and its
severity. A `block` finding fails the check, and validate.py exits with 1. A
`warn` finding is only reported: set the member group's `groupName` to
`fabric-plt-members`, and `owner-group-naming` warns while the report still
says PASS and the exit code is 0. Exit code 2 means a live check got 401 or
403.

Now let the same rule block the pull request. Set `costCenter` to `CC-3000`
again, then commit and push:

```bash
git commit -am "Use cost center CC-3000"
git push
sleep 15
gh pr checks --watch
```

The `validate` check fails, its comment shows the same finding, and the
ruleset blocks the merge. Don't merge with your bypass: it stands in only for
the second reviewer a solo lab doesn't have. Revert the commit:

```bash
git revert --no-edit HEAD
git push
sleep 15
gh pr checks --watch
```

The check passes again.

Production requests get extra rules. A manifest with `environment: prd` needs a
capacity that allows prd, which in the shipped policy is only `contosoprodf4`.
It also needs the sensitivity label Confidential or Highly Confidential and at
least two group owners (`prod-extra-controls`). These rules key on the
`environment` field, and `name-segments-match-fields` keeps the name's prefix in
line with it. In [`.github/CODEOWNERS`](../../.github/CODEOWNERS), the
`/workspaces/prd-*.yaml` line can name a separate reviewer for production
requests.

### Task 3 — Merge and provision

No MCP tool takes part here: provision.py makes the changes as the SPN.

Merge the pull request. `--admin` uses the bypass you set in challenge 00,
because a solo lab has no second reviewer:

```bash
gh pr merge --merge --admin --delete-branch
git switch main
git pull
sleep 15
RUN_ID=$(gh run list --workflow provision.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --web
```

The merge started the provision workflow, which waits for approval in the
`production` environment. In the browser, select **Review deployments**, check
`production` and select **Approve and deploy**. Then follow the run:

```bash
gh run watch "$RUN_ID"
```

In the browser, open the **Provision workspaces** step. It created both
workspaces and gave both groups their roles:

```text
--- dev-plt-myteam-playground ---
  creating workspace (capacity=<capacity-id>)
  adding: Group <admin-group-id> Admin
  adding: Group <member-group-id> Member
--- dev-plt-sample-hello ---
  creating workspace (capacity=<capacity-id>)
  adding: Group <admin-group-id> Admin
  adding: Group <member-group-id> Member
```

provision.py works like this:

- It only adds. It never removes a role or a tag and never deletes a workspace.
- A rerun logs `exists: <workspace-id> — updating description + capacity` and
  `ok:` for each role that's already in place.
- The SPN is Admin of each workspace because it created it. It holds no Fabric
  or capacity administrator role.
- Exit code 3 means a call returned 401 or 403. The log names the API and the
  setting or permission to check.
- With the repository variable `DRY_RUN` set to `true`, it logs
  `[dry-run] would …` lines and calls no API.

### Task 4 — Check the result from chat

In a Copilot CLI session, send each prompt and check which tool answers it:

| Prompt | Server | Tool |
| ------ | ------ | ---- |
| List the Fabric workspaces I can access. | `fabric` | `list_workspaces` |
| Show the details of the workspace dev-plt-myteam-playground. | `fabric` | `get_workspace` |
| List the role assignments on dev-plt-myteam-playground. | `fabric` | `list_workspace_roles` |

Both workspaces are in the list, because you're in the admin group. The details
show the manifest's description and your capacity's ID. The role assignments
show the admin group as Admin, the member group as Member and the SPN as Admin.
If a workspace is missing from the list, check that you're a member of
`grp_fabric_dev_plt_admin`.

Then run the governance Skill. In a Copilot CLI session:

```text
/onelake-catalog-cli In dataowner-audit mode, check dev-plt-myteam-playground: which domain is it assigned to, and does it contain any items?
```

The Skill reports that the workspace has no domain, because challenge 03
assigns it, and no items.

### Task 5 — Detect and fix drift

A change made outside a pull request is drift. In the Fabric portal, make three
changes to `dev-plt-myteam-playground`:

1. In **Workspace settings**, change the description.
2. In **Manage access**, remove `grp_fabric_dev_plt_member`.
3. In **Manage access**, add your test user with the Admin role.

The Core MCP tools `update_workspace`, `delete_workspace_role` and
`add_workspace_role` would make the same changes from chat, and they'd be drift
too. No MCP tool compares workspaces with their manifests, so use the drift
workflow. drift.py reads each workspace's access through an admin API in
preview:

> **Preview** (checked 2026-11-27): List Workspace Access Details API — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details). GA route: List Workspace Role Assignments ([Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspace-role-assignments)), which needs Member or higher on each workspace.

```bash
gh workflow run drift.yml
sleep 15
RUN_ID=$(gh run list --workflow drift.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID"
ISSUE=$(gh issue list --label drift --json number --jq '.[0].number')
gh issue view "$ISSUE"
```

The run opens an issue, **Fabric workspace drift detected**, labeled `drift`
and `governance`. Its report lists the playground under Drifted, then gives
each drifted workspace its own section, with one line per change:

```text
- Drifted: **1**
  - dev-plt-myteam-playground

## dev-plt-myteam-playground

- description differs from the manifest
- owner <member-group-id> (Group) has no access; the manifest gives it Member
- User <test-user-name> (<test-user-upn>) has Admin but isn't an owner in the manifest
```

provision.py restores what the manifest declares. Run it on demand:

```bash
gh workflow run provision.yml
sleep 15
RUN_ID=$(gh run list --workflow provision.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --web
```

Approve the `production` deployment as in Task 3, then follow the run:

```bash
gh run watch "$RUN_ID"
```

The **Provision workspaces** step sets the description again and adds the
member group back:

```text
--- dev-plt-myteam-playground ---
  exists: <playground-id> — updating description + capacity
  ok: Group <admin-group-id> Admin
  adding: Group <member-group-id> Member
--- dev-plt-sample-hello ---
  exists: <sample-id> — updating description + capacity
  ok: Group <admin-group-id> Admin
  ok: Group <member-group-id> Member
```

provision.py never removes access, so the test user still has Admin. Remove it
in **Manage access**. To keep a role like that instead, add it to the manifest
in a pull request.

Run the drift check again:

```bash
gh workflow run drift.yml
sleep 15
RUN_ID=$(gh run list --workflow drift.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID"
```

The new report shows `- Drifted: **0**` and has no section for the playground.
While your tenant has workspaces without a manifest, they're listed under
Unmanaged, drift.py still exits with code 2 and the run opens another issue. So
a clean rerun means that none of your managed workspaces is under Missing, Not
visible or Drifted.

The drift workflow also runs every day at 03:17 UTC. Each run that finds
anything opens a new issue, and the workflow never closes one. Close all open
drift issues:

```bash
for n in $(gh issue list --label drift --state open --json number --jq '.[].number'); do gh issue close "$n"; done
```

### Task 6 — Retire a workspace

A workspace's retirement belongs in the same history as its creation. There are
two ways to retire one:

- **Stop managing it.** Delete the manifest in a pull request. The workspace
  stays, and drift.py lists it under Unmanaged.
- **Delete it.** Delete the manifest in a pull request, merge it, and only then
  delete the workspace. In the other order, the next provision run creates the
  workspace again, because its manifest still exists.

Either way, write the reason in the pull request description.

A deleted workspace isn't gone at once. Fabric keeps it for the retention
period, 7 days by default. A Fabric administrator can set 7 to 90 days under
**Define workspace retention period**, in **OneLake catalog** > **Govern** >
**Configurations** > **Tenant settings** > **Workspace settings**. Lowering the
period permanently deletes, at the next check, workspaces deleted longer ago
than the new period. During retention, a Fabric administrator can restore a
workspace in **OneLake catalog** > **Govern** > **Workspaces**: filter the
status to **Deleted**, select **Restore**, then name the workspace and choose
at least one Admin. A workspace identity, with its service principal and app
registration, stays until the workspace is permanently deleted.

Practice on a throwaway workspace. Copy the playground manifest:

```bash
git switch -c add-decom-test
cp workspaces/dev-plt-myteam-playground.yaml workspaces/dev-plt-decom-test.yaml
```

In the copy, set `name: dev-plt-decom-test` and
`description: "Throwaway workspace where the platform team practices retiring a managed workspace."`
Then check it and open a pull request:

```bash
.venv/bin/python scripts/validate.py workspaces/dev-plt-decom-test.yaml
git add workspaces/dev-plt-decom-test.yaml
git commit -m "Add dev-plt-decom-test"
git push -u origin add-decom-test
gh pr create --fill
sleep 15
gh pr checks --watch
```

When the check passes, merge the pull request and open the provision run:

```bash
gh pr merge --merge --admin --delete-branch
git switch main
git pull
sleep 15
RUN_ID=$(gh run list --workflow provision.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --web
```

Approve the deployment as in Task 3. The log shows `creating workspace` for
`dev-plt-decom-test` and `exists:` for the other two.

Now retire it by deleting it. First remove the manifest in a pull request that
says why:

```bash
git switch -c retire-decom-test
git rm workspaces/dev-plt-decom-test.yaml
git commit -m "Retire dev-plt-decom-test"
git push -u origin retire-decom-test
gh pr create --title "Retire dev-plt-decom-test" --body "Delete the workspace after this merges. It's a practice workspace with no items."
sleep 15
gh pr checks --watch
```

The check passes, and its comment says that no workspace manifests changed:
validate.py checks only the manifests that still exist. Merge the pull request
and open the provision run:

```bash
gh pr merge --merge --admin --delete-branch
git switch main
git pull
sleep 15
RUN_ID=$(gh run list --workflow provision.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --web
```

The merge changed `workspaces/`, so provision runs again. Approve it: it
updates the playground and the sample and deletes nothing.

Then delete the workspace from chat. In a Copilot CLI session:

```text
Delete the Fabric workspace dev-plt-decom-test.
```

Copilot calls `delete_workspace` on the `fabric` server. The tool acts at once,
so check the workspace name before you approve the call.

Run the drift check once more:

> **Preview** (checked 2026-11-27): List Workspace Access Details API — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details). GA route: List Workspace Role Assignments ([Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspace-role-assignments)), which needs Member or higher on each workspace.

```bash
gh workflow run drift.yml
sleep 15
RUN_ID=$(gh run list --workflow drift.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID"
```

`dev-plt-decom-test` is under neither Missing nor Unmanaged: it has no
manifest, and drift.py counts only active workspaces, so a deleted one drops
out. Close the drift issues as in Task 5.

Don't retire the playground or the sample: challenges 03 and 04 use them.

## Success criteria

- [ ] `dev-plt-myteam-playground` and `dev-plt-sample-hello` exist, and their
      role assignments match their manifests.
- [ ] You reproduced a blocking rule locally and in a pull request, then
      reverted it.
- [ ] A drift report listed your three portal changes. After the fix, the
      playground wasn't under Drifted, and you closed the drift issues.
- [ ] You can explain what the SPN does in the validate, provision and drift
      workflows.
- [ ] A merged pull request records why `dev-plt-decom-test` was retired, and
      the workspace is deleted.

## Stretch goals

- **Add a rule.** Require production workspaces to use a cost center that
  starts with `CC-9`. In [`rules/policy.yaml`](../../rules/policy.yaml), add an
  entry under `rules:`, which lists every rule with its severity. In
  [`scripts/rules_engine.py`](../../scripts/rules_engine.py), add the check to
  the `if env == "prd":` block of `apply_rules`: a `block` finding when
  `cc and not cc.startswith("CC-9")`. The agent backend in `api/` keeps its own
  copies, and [Governance rules](../../docs/governance-rules.md) asks you to
  keep them identical:

  ```bash
  cp scripts/rules_engine.py rules/policy.yaml api/
  ```

  Test the rule with a production manifest you don't commit, then open a pull
  request with your changes.

- **Adopt an existing workspace.** To manage a workspace someone created in the
  portal, first give the SPN the Admin role on it in **Manage access**, then
  add a manifest that matches it. provision.py logs `exists:` and adds any
  missing owners. Without the role, drift.py lists the workspace under Not
  visible. After adoption, drift.py reports any access the manifest doesn't
  list.

- **Shape the pull request template.** Change
  [`.github/pull_request_template.md`](../../.github/pull_request_template.md)
  so its fields and checklist match what your reviewers check.

- **Workspace identity.** Manifests don't declare a workspace identity.
  [Challenge 04](../04-access-rbac-lifecycle/challenge.md) declares it with the
  workspace's access, in `access/<workspace>.yaml` (Task 7).

> **Preview** (checked 2026-11-28): Apply Workspace Tags API — [Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/apply-workspace-tags). GA route: apply the tags in the Fabric portal, in the workspace settings under Tags.

- **Tag the playground.** A manifest can list up to 10 tags, and provision.py
  applies the ones the workspace doesn't have yet. Each tag must already exist,
  as a tenant tag or a tag of the workspace's domain. Fabric administrators
  create tenant tags; Fabric administrators and domain admins create a domain's
  tags. provision.py doesn't assign domains, so the playground isn't in one
  until challenge 03. As a Fabric administrator, create a tenant tag named
  `playground`: in the admin portal, select **Tags**, then **New tag**. Add it
  to the playground's manifest in a pull request:

  ```yaml
  tags:
    - playground
  ```

  If the tag is missing, the `validate` comment warns
  `tag 'playground' doesn't exist in the tenant`. That live check reads tags
  with the core List Tags API, which needs no admin API setting. After you
  merge and approve the deployment, provision.py logs `applying 1 tag(s)`, and
  `ok: tags` on later runs. It skips a missing tag with a warning and never
  removes a tag.

  To see tag drift, remove the tag in the workspace settings under **Tags**.
  Only workspace Admins can change tags, and the admin group makes you one. The
  next drift report says `tag 'playground' isn't applied`, and the next
  provision run applies it again. A tag someone adds in the portal shows up as
  `tag '<name>' is applied but isn't in the manifest` until you add it to the
  manifest or remove it.

## MCP tips

- `list_workspaces` has no name filter: it returns every workspace you can
  access, and Copilot picks the one you name.
- The role tools take object IDs, not names. Look them up with
  `az ad group show`, or with the Microsoft MCP Server for IT Admins from the
  challenge 00 stretch goals.
- `delete_workspace` acts at once, as you.
- Don't change prd workspaces from chat. The change is drift, and it skips the
  review that production requests get.

## Skills tips

- The dataowner-audit mode of `/onelake-catalog-cli` reads the Core API as you
  and changes nothing.
- The dataowner-remediate mode changes workspaces as you. A tag it applies
  shows up as drift unless the manifest lists it, the next provision run
  reverts a capacity it changes, and drift.py doesn't compare the domain it
  assigns.

## Repository files

- [`scripts/validate.py`](../../scripts/validate.py) and
  [`scripts/rules_engine.py`](../../scripts/rules_engine.py)
- [`scripts/provision.py`](../../scripts/provision.py),
  [`scripts/drift.py`](../../scripts/drift.py) and
  [`scripts/_fabric.py`](../../scripts/_fabric.py)
- [`rules/policy.yaml`](../../rules/policy.yaml) and
  [`schemas/workspace.schema.json`](../../schemas/workspace.schema.json)
- `workspaces/dev-plt-sample-hello.yaml`
- [`.github/workflows/validate.yml`](../../.github/workflows/validate.yml),
  [`provision.yml`](../../.github/workflows/provision.yml) and
  [`drift.yml`](../../.github/workflows/drift.yml)
- [`.github/CODEOWNERS`](../../.github/CODEOWNERS) and
  [`.github/pull_request_template.md`](../../.github/pull_request_template.md)

## References

- [Governance rules](../../docs/governance-rules.md)
- [Identity model](../../docs/identity-model.md)
- [Workspaces - REST API (Core)](https://learn.microsoft.com/rest/api/fabric/core/workspaces)
- [List Workspace Role Assignments](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspace-role-assignments)
- [Delete Workspace](https://learn.microsoft.com/rest/api/fabric/core/workspaces/delete-workspace)
- [List Workspace Access Details (Admin)](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details)
- [Roles in workspaces in Microsoft Fabric](https://learn.microsoft.com/fabric/fundamentals/roles-workspaces)
- [Give users access to workspaces](https://learn.microsoft.com/fabric/fundamentals/give-access-workspaces)
- [Workspace retention](https://learn.microsoft.com/fabric/admin/workspace-retention)
- [Tags in Microsoft Fabric](https://learn.microsoft.com/fabric/governance/tags-overview)
- [Create and manage a set of tags](https://learn.microsoft.com/fabric/governance/tags-define)
- [Apply Workspace Tags](https://learn.microsoft.com/rest/api/fabric/core/workspaces/apply-workspace-tags)
- [List Tags](https://learn.microsoft.com/rest/api/fabric/core/tags/list-tags)
- [Fabric Core MCP Server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Reviewing deployments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
