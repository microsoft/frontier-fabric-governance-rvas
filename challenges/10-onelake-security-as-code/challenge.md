# Challenge 10 — OneLake security as code

> **Outcome:** the OneLake security roles of every governed lakehouse live in manifests. Each PR gets a dry run, each merge applies the roles with an ETag, and a test proves that a denied identity can't read.

## Why this challenge exists

[Challenge 04](../04-access-rbac-lifecycle/challenge.md) governs who can open a workspace. Inside a lakehouse, OneLake security roles decide which tables, rows and columns a reader sees, and teams usually edit those roles by hand.

Three facts make hand edits risky:

- The bulk API call replaces every role on the item. A pipeline that doesn't own the full set deletes the roles people made in the portal.
- Role members are Entra object IDs. Git integration doesn't track them, so each environment keeps its own members.
- Roles restrict Viewers and users with item Read. Admins, Members and Contributors see all data ([Learn](https://learn.microsoft.com/fabric/onelake/security/data-access-control-model)), so the identity that proves a role works must be a Viewer.

Challenge 04 Task 4 reads role members in the quarterly access review. This challenge makes the roles themselves code.

## Learning objectives

1. Model OneLake security roles as code (`onelake-security/<workspace>/<item>.yaml`).
2. Apply them with the bulk API: a dry run on each PR, and a write guarded by an ETag on merge.
3. Explain which identities the roles restrict, and prove that a denied read fails.
4. Record each shortcut's target and access mode, and require approval for delegated shortcuts.
5. Inspect and dry-run roles from chat with the Core MCP.

## Prerequisites

- Challenges [00](../00-setup/challenge.md), [01](../01-workspace-as-code/challenge.md), [02](../02-items-as-code/challenge.md) and [04](../04-access-rbac-lifecycle/challenge.md) complete.
- `workspaces/dev-sales-core.yaml` from challenge 01, and a challenge 02 manifest in `items/dev-sales-core/` for the lakehouse `lh_sales` with `schemaEnabled: true`. The lakehouse holds three tables: `sales.orders` with a `region` column, `sales.customers` with an `email` column, and `sales.margins`.
- The SPN is an Admin or Member of `dev-sales-core`, because writing roles needs Reshare on the item. It keeps the Microsoft Graph permissions from challenge 04 (GroupMember.Read.All or Group.Read.All, and User.Read.All).
- Two Entra security groups, `sg-sales-readers` and `sg-sales-emea-readers`, neither mail-enabled. OneLake security on the SQL analytics endpoint doesn't support mail-enabled groups or distribution lists.
- A test user who is a Viewer of `dev-sales-core`, has no other access to `lh_sales`, and is a member of both groups.
- The SQL analytics endpoint of `lh_sales` uses User's identity access mode. New endpoints start in delegated identity mode, and an Admin or Member switches each endpoint once: open the endpoint, then Security > View data access mode > Data access mode settings > User's identity access mode > Apply.
- For Task 5, the tenant setting "Users can access data stored in OneLake with apps external to Fabric" is on, because OneLake security works with shortcuts only when it is ([Learn](https://learn.microsoft.com/fabric/onelake/security/get-started-security)). The setting is at OneLake catalog > Govern > Configurations > Tenant settings > OneLake settings; where Govern isn't available, use Settings > Admin portal > Tenant settings.

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

## Tasks

### Task 1 — Export the current roles

Ask the Core MCP:

> List the OneLake data access roles on lh_sales in dev-sales-core, with each role's members and permissions.

`onelake_list_data_access_roles` calls List Data Access Roles, which needs Read on the item, allows 100 requests a minute and returns an `ETag` header:

```text
GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/dataAccessRoles
```

Look for `DefaultReader` in the export. Learn explains what it does: "In an item with OneLake security enabled, ReadAll doesn't grant data access on its own. It grants access through the `DefaultReader` role. If you delete `DefaultReader`, users who relied on that role lose data access, even if they still have ReadAll permission."

Decide whether to keep it, and record the decision as `keepDefaultReader` in the Task 2 manifest. The bulk call in Task 3 deletes every role the request leaves out, so dropping `DefaultReader` from the manifest deletes it. If you keep it, follow Learn's rule: "When you add a user to a OneLake security role, remove them from the DefaultReader role. Otherwise, they keep full access to the data."

Compare the export with the roles people made by hand. Any role you don't put in the manifest disappears on the first apply.

### Task 2 — Roles as code

Save this as `onelake-security/dev-sales-core/lh_sales.yaml`:

```yaml
workspace: dev-sales-core
item: lh_sales
keepDefaultReader: false
roles:
  - name: OrdersEmea
    entraGroups: [sg-sales-emea-readers]
    tables:
      - table: sales.orders
        rowFilter: "SELECT * FROM sales.orders WHERE region = 'EMEA'"
  - name: CustomersNoEmail
    entraGroups: [sg-sales-readers]
    tables:
      - table: sales.customers
        visibleColumns: [customer_id, name, region, segment]
```

`visibleColumns` lists the columns a role can read, and every other column, like `email`, stays hidden. Column names are case-sensitive.

Each role covers one table. Roles add up: a user in two roles sees the tables of both, and row filters on the same table combine with OR. Columns are stricter, because the SQL analytics endpoint hides a column if any of the user's roles hides it. Spark rejects a user who gets a row filter from one role and column rules from another on the same table. One role per table keeps the result predictable.

Add `schemas/onelake-security.schema.json` and these validator rules:

- members are Entra security groups listed by name in `entraGroups`; the schema rejects any member that contains `@`;
- each group resolves in Microsoft Graph to exactly one group with `securityEnabled` true and `mailEnabled` false;
- role names start with a letter, use only letters and digits, are the same in every environment, and have at most 124 characters: the portal allows 128, but longer names fail to sync to the SQL analytics endpoint ([Learn](https://learn.microsoft.com/fabric/onelake/security/sql-analytics-endpoint-onelake-security#limitations));
- an item has at most 250 roles, and a role has at most 500 members and 500 permissions; Azure Support can raise the role limit to 1,000;
- no group is in two roles that put a row filter and column rules on the same table;
- the item's challenge 02 manifest has `schemaEnabled: true`.

Resolve groups with a new `graph_find_group(display_name)` in `scripts/_fabric.py`, next to `graph_group_exists()`:

```text
GET https://graph.microsoft.com/v1.0/groups?$filter=displayName eq '<name>'&$select=id,mailEnabled,securityEnabled
```

Run the Graph lookup only when `LIVE_CHECKS` is `true`, like the existing live checks. `validate.py` exits 2 on a live 401 or 403, so never read either as "not found".

Declare these rules in `rules/policy.yaml` and implement them in `scripts/validate.py`. Then copy `rules/policy.yaml` to `api/policy.yaml` so the two stay identical.

`changed_workspace_files()` in `scripts/validate.py` picks up only `workspaces/*.yaml`. Extend it to `onelake-security/**/*.yaml`, and add `onelake-security/**` to the `paths` in `.github/workflows/validate.yml`.

Add the entry to `.github/CODEOWNERS`:

```text
/onelake-security/ @your-org/fabric-security
```

**Deliberate failure:** open a PR that adds `megan@contoso.com` to the `entraGroups` of `OrdersEmea`. It must fail.

### Task 3 — Apply on merge, with an ETag

The Core MCP tools run from chat, not from a pipeline, so this task calls the REST APIs. Write `scripts/apply_onelake_security.py` and reuse `scripts/_fabric.py` for tokens and retries:

1. Resolve the workspace and lakehouse IDs from the manifest, and each group's object ID with `graph_find_group()`.
2. Build the request body. Each table becomes a `Path` permission on `/Tables/<schema>/<table>` with the `Read` action, a `rowFilter` becomes a row constraint, and `visibleColumns` becomes a column constraint with `columnEffect` set to `Permit`. With `keepDefaultReader: true`, copy the live `DefaultReader` role into the body unchanged.
3. Read the live roles and the `ETag` header with List Data Access Roles.
4. On a push to `main`, also build the body from the manifest's previous version (`git show <before-sha>:<path>`) and compare it with the live roles. A difference means someone changed the roles outside Git: report it, skip the write and exit 2.
5. Write the difference between the live roles and the new body to `onelake-security-report.md`.
6. On a PR, send the body with `dryRun=true` and stop there. On a push to `main`, send it with `If-Match` set to the ETag from step 3.

```text
PUT https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/dataAccessRoles?dryRun=true
PUT https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/dataAccessRoles
```

The body for `OrdersEmea` looks like this, with `bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb` standing for the object ID of `sg-sales-emea-readers`:

```json
{
  "value": [
    {
      "name": "OrdersEmea",
      "decisionRules": [
        {
          "effect": "Permit",
          "permission": [
            { "attributeName": "Path", "attributeValueIncludedIn": ["/Tables/sales/orders"] },
            { "attributeName": "Action", "attributeValueIncludedIn": ["Read"] }
          ],
          "constraints": {
            "rows": [
              { "tablePath": "/Tables/sales/orders", "value": "SELECT * FROM sales.orders WHERE region = 'EMEA'" }
            ]
          }
        }
      ],
      "members": {
        "microsoftEntraMembers": [
          { "tenantId": "11111111-1111-1111-1111-111111111111", "objectId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" }
        ]
      }
    }
  ]
}
```

For `CustomersNoEmail`, the `constraints` value holds a column rule instead:

```json
{
  "columns": [
    {
      "tablePath": "/Tables/sales/customers",
      "columnNames": ["customer_id", "name", "region", "segment"],
      "columnEffect": "Permit",
      "columnAction": ["Read"]
    }
  ]
}
```

The call needs Reshare on the item and the `OneLake.ReadWrite.All` scope. It allows 50 requests a minute, so back off on HTTP 429; `_fabric.py` already honors `Retry-After`. Stop on 401 or 403 with a clear error, and never read either as "not found".

`_fabric._request` has no headers argument. Add `headers: dict | None = None` and merge it into the request headers, so the script can send `If-Match`. Handle two error codes, matched on the `errorCode` in the error text because Learn doesn't document their HTTP status:

- `PreconditionFailed` means a role changed between your read and your write. Report it and exit 2.
- `DataAccessRoleChangeRestrictedByPolicy` means a policy blocks the change. Stop with a clear error, because a retry won't help.

> **Preview** (checked 2026-11-27): Create Or Update Single Data Access Role API — [Learn](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/create-or-update-single-data-access-role). GA route: the bulk PUT.

The single-role call changes one role and leaves the others alone: `POST .../dataAccessRoles?preview=true` with an `If-Match` ETag, where `dataAccessRoleConflictPolicy` chooses whether an existing role with the same name is overwritten or the call aborts. It needs Member or higher. Use it for an urgent fix to one role, then update the manifest. The pipeline keeps the bulk PUT, because only the bulk call also deletes the roles the manifest dropped.

Save this as `.github/workflows/onelake-security.yml`:

```yaml
name: onelake-security
on:
  pull_request:
    paths: ["onelake-security/**"]
  push:
    branches: [main]
    paths: ["onelake-security/**"]
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
  issues: write
  pull-requests: write
concurrency:
  group: onelake-security
  cancel-in-progress: false
jobs:
  roles:
    runs-on: [self-hosted, fabric-gov]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
      - name: Python
        run: |
          python3 -m venv .venv
          .venv/bin/pip install --quiet --upgrade pip
          .venv/bin/pip install --quiet -r scripts/requirements.txt
          echo "$GITHUB_WORKSPACE/.venv/bin" >> $GITHUB_PATH
      - uses: azure/login@7ddb5af1ef8758cf1353cf3b42f940aee27ba21c # v3.0.2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          allow-no-subscriptions: true
      - name: Dry run or apply
        id: apply
        env:
          MODE: ${{ github.event_name == 'pull_request' && 'dry-run' || 'apply' }}
          BEFORE_SHA: ${{ github.event.before }}
        run: |
          set +e
          python scripts/apply_onelake_security.py --mode "$MODE" --before "$BEFORE_SHA"
          rc=$?
          echo "rc=$rc" >> "$GITHUB_OUTPUT"
          if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then exit "$rc"; fi
      - name: Comment the dry run
        if: github.event_name == 'pull_request'
        uses: marocchino/sticky-pull-request-comment@5770ad5eb8f42dd2c4f34da00c94c5381e49af88 # v3.0.5
        with:
          header: onelake-security
          path: onelake-security-report.md
      - name: Open issue on drift
        if: github.event_name != 'pull_request' && steps.apply.outputs.rc == '2'
        uses: peter-evans/create-issue-from-file@fca9117c27cdc29c6c4db3b86c48e4115a786710 # v6.0.0
        with:
          title: OneLake security roles changed outside Git
          content-filepath: onelake-security-report.md
          labels: drift, governance, drift/onelake-security
```

Create the `drift/onelake-security` label in your repo first. A manual run has no previous commit, so the script skips step 4 when `--before` is empty.

Between merges, nobody runs the apply. Add a check to `scripts/drift.py` that compares each manifest with the live roles. Its findings join the nightly drift issue, and `drift.py` keeps exiting 2 on drift and 3 on 401 or 403.

### Task 4 — Prove a denied read fails

Admins, Members and Contributors bypass the roles. So do the consumers of an IQ Sharing Share (Preview): they get the whole item, because OneLake security rules on the source item aren't honored for them. When OneLake security is on, anyone with Write and Reshare on the item can create a Share ([Learn](https://learn.microsoft.com/fabric/onelake/iq-share/create-share)), so scope the External data sharing tenant setting, which controls who creates Shares, to a security group.

Run this test as the Viewer test user, whom the roles apply to. Sign in as that user with `az login --tenant <tenant-id> --allow-no-subscriptions`, then in a Copilot CLI session:

```text
/sqldw-cli
```

The skill runs T-SQL through the `fabric-sqlendpoint-execute_query` tool, which takes the workspace ID and the ID of the SQL analytics endpoint, not the lakehouse. Get Lakehouse returns it as `properties.sqlEndpointProperties.id`. Ask the skill to run these queries and record each result:

1. `SELECT TOP 5 email FROM sales.customers` fails, because `CustomersNoEmail` doesn't permit `email`.
2. `SELECT DISTINCT region FROM sales.orders` returns only `EMEA`.
3. `SELECT TOP 5 * FROM sales.margins` fails, because no role grants that table.

Save the results to `onelake-security/tests/<YYYY-MM-DD>.md` and link the file from the PR.

Role changes take about 5 minutes to apply. A change to a group's members takes about an hour, and engines with their own cache can take another hour. Wait that long before you debug a test that still reads too much. If a result still surprises you, work through [Troubleshoot OneLake security for SQL analytics endpoints](https://learn.microsoft.com/fabric/onelake/security/troubleshoot-onelake-security-for-sql-analytics-endpoints).

Three habits keep the endpoint consistent:

- Don't edit the `OLS_` database roles on the endpoint; OneLake security manages them.
- Renaming a table breaks the roles that point to it, so rename it in the manifest in the same change.
- Avoid `ALTER AUTHORIZATION` on the endpoint.

### Task 5 — Shortcuts and their access mode

A shortcut reads data stored somewhere else, so the target's security shapes what readers see ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-shortcut-security)):

- OneLake shortcuts in the same tenant use passthrough mode by default: OneLake checks the reader's own access on the target. Delegated mode can be chosen when the shortcut is created.
- In delegated mode, a reader sees only data that both they and the delegated identity can read.
- Shortcuts to external storage, and shortcuts to another tenant, are always delegated.
- The API doesn't return the mode, and changing it means deleting and recreating the shortcut. Record the mode when you create the shortcut.

Save this as `onelake-security/dev-sales-core/shortcuts.yaml`:

```yaml
workspace: dev-sales-core
item: lh_sales
shortcuts:
  - path: Tables/sales/fx_rates
    target: onelake://dev-fin-core/lh_fin_ref/Tables/finance/fx_rates
    mode: passthrough
    owner: "@your-org/sales-data"
  - path: Files/partner_feed
    target: https://stcontosoapproved.dfs.core.windows.net/partner-feed
    mode: delegated
    owner: "@your-org/sales-data"
    justification: "Partner files land in ADLS, and shortcuts to external storage are always delegated."
```

Add `schemas/onelake-shortcuts.schema.json` and these validator rules:

- `mode` is `passthrough` or `delegated`;
- a target outside OneLake, or in another tenant, has `mode: delegated`;
- a delegated shortcut has a `justification`.

The CODEOWNERS entry from Task 2 already makes `@your-org/fabric-security` approve every change in `onelake-security/`, delegated shortcuts included.

Add a check to `scripts/drift.py` that lists the shortcuts in each lakehouse and reports any the manifest doesn't list, or whose target differs:

```text
GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/shortcuts
```

Its findings join the same nightly drift issue, with the same exit codes. A separate `drift/shortcut` issue needs a change to `.github/workflows/drift.yml`: have `drift.py` also write the shortcut findings to `drift-shortcut.md`, create the `drift/shortcut` label, and add this step after the step that opens the drift issue:

```yaml
- name: Open shortcut drift issue
  if: steps.drift.outputs.rc == '2' && hashFiles('drift-shortcut.md') != ''
  uses: peter-evans/create-issue-from-file@fca9117c27cdc29c6c4db3b86c48e4115a786710 # v6.0.0
  with:
    title: OneLake shortcuts changed outside Git
    content-filepath: drift-shortcut.md
    labels: drift, governance, drift/shortcut
```

### Task 6 — Dry-run from chat

Ask the Core MCP:

> Dry-run the roles in onelake-security/dev-sales-core/lh_sales.yaml against lh_sales and tell me what would change.

`onelake_create_or_update_data_access_roles` replaces every role, like the bulk call, and takes a `DryRun` option. Check that the agent sets it. Without it, the chat writes to the lakehouse, and the pipeline is no longer the only writer.

Compare the answer with the dry-run comment on your last PR. They should match.

## Success criteria

- [ ] Merging a manifest change updates the roles on `lh_sales` with no portal clicks.
- [ ] Every PR that touches `onelake-security/` gets a dry-run comment.
- [ ] A role edited in the portal makes the next apply stop before it writes and open a `drift/onelake-security` issue.
- [ ] The denied-read test passes, and the Task 2 PR fails validation.
- [ ] Every shortcut in `lh_sales` is in `shortcuts.yaml` with its mode, and every delegated one has a justification.

## Stretch goals

> **Preview** (checked 2026-11-27): Terraform `fabric_onelake_data_access_security` resource (Preview in the `microsoft/fabric` provider) — [Learn](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/create-or-update-data-access-roles). GA route: the bulk REST call in Task 3.

- **Terraform.** Manage the same roles with the `fabric_onelake_data_access_security` resource of the [Terraform provider for Microsoft Fabric](https://registry.terraform.io/providers/microsoft/fabric/latest/docs), with `preview = true` in the provider block. Keep one writer per item: Terraform or the script, never both.

> **Preview** (checked 2026-11-27): OneLake security roles in lakehouse Git integration and deployment pipelines — [Learn](https://learn.microsoft.com/fabric/data-engineering/lakehouse-git-deployment-pipelines). GA route: the bulk REST call in Task 3.

- **Roles in Git integration.** Turn on data access roles in the lakehouse's `alm.settings.json`, so Git integration writes them to `data-access-roles.json`, and compare that file with your manifest. Git integration doesn't track Entra members and keeps them only when role names match exactly, so the manifest stays the source for members.

> **Preview** (checked 2026-11-27): Get authorized access for a principal — [Learn](https://learn.microsoft.com/fabric/onelake/security/authorized-access-for-principal-reference). GA route: none; stretch task.

- **Effective access report.** Ask the API which paths and actions the test user can reach, and attach the answer to the Task 4 test file. Use it as evidence, never as a gate.
- **Spark through a shortcut.** Create a passthrough shortcut to `lh_sales` in another lakehouse, then read it with `/spark-cli` as the test user. The row filter and the hidden column must still apply. Spark enforces OneLake security from Fabric Runtime 1.3 and blocks direct `abfss` reads of secured tables for users the roles restrict.

## MCP tips

- `onelake_list_data_access_roles`, `onelake_list_shortcuts` and `onelake_get_shortcut` only read. Use them to inspect an item before you write its manifest.
- `onelake_create_or_update_data_access_roles` replaces every role on the item. Use it with `DryRun` from chat, and leave writes to the pipeline.
- `onelake_create_or_update_single_data_access_role` and `onelake_delete_data_access_role` change one role. A change made from chat shows up as drift on the next run, so put it in the manifest first.

## Skills tips

- `sqldw-cli` runs queries as the signed-in identity, which makes it the tool for the denied-read test. Sign in as the test user first.
- `spark-cli` runs notebooks and Livy sessions for the Spark stretch goal.
- No Skill manages OneLake security roles, so writes use REST and the Core MCP.
- If the skills aren't installed, run these from a terminal:

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

## Repository files

This challenge extends these files in the repo root:

- `scripts/_fabric.py` (a `headers` argument for `_request`, and `graph_find_group()`)
- `scripts/validate.py`, `scripts/drift.py`
- `rules/policy.yaml` and its copy `api/policy.yaml`
- `.github/workflows/validate.yml`, `drift.yml`
- `.github/CODEOWNERS`

It adds:

- `onelake-security/<workspace>/<item>.yaml`, `onelake-security/<workspace>/shortcuts.yaml` and the test results in `onelake-security/tests/`
- `schemas/onelake-security.schema.json`, `schemas/onelake-shortcuts.schema.json`
- `scripts/apply_onelake_security.py`
- `.github/workflows/onelake-security.yml`

## References

- [Data security overview](https://learn.microsoft.com/fabric/onelake/security/get-started-security)
- [OneLake security roles: create and manage](https://learn.microsoft.com/fabric/onelake/security/create-manage-roles)
- [OneLake security roles, permissions, and scopes](https://learn.microsoft.com/fabric/onelake/security/data-access-control-model)
- [OneLake table, column, and row-level security](https://learn.microsoft.com/fabric/onelake/security/table-column-row-security)
- [OneLake security for SQL analytics endpoints](https://learn.microsoft.com/fabric/onelake/security/sql-analytics-endpoint-onelake-security)
- [Secure and manage OneLake shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcut-security)
- [Create Or Update Data Access Roles REST API](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/create-or-update-data-access-roles)
- [List Data Access Roles REST API](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/list-data-access-roles)
- [List Shortcuts REST API](https://learn.microsoft.com/rest/api/fabric/core/onelake-shortcuts/list-shortcuts)
- [Lakehouse Git integration and deployment pipelines](https://learn.microsoft.com/fabric/data-engineering/lakehouse-git-deployment-pipelines)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [`sqldw-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/sqldw-cli)
- [`spark-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/spark-cli)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
