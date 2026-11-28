# Challenge 02 — Items as code

> **Outcome:** every lakehouse, notebook and warehouse in `dev-fin-revenue`
> comes from a reviewed manifest under `items/` that names its owner group,
> description, sensitivity label and tags. A daily drift report shows where
> Fabric no longer matches the repo.

## Why this challenge exists

[Challenge 01](../01-workspace-as-code/challenge.md) governs workspaces, but
the items inside them still appear by hand: a lakehouse nobody can explain, a
storage key pasted into a notebook cell, a warehouse created with a collation
that can't change. This challenge gives every item a manifest and a PR check.
The SPN creates the item on merge, and a daily run compares Fabric with the
repo.

## Learning objectives

1. Describe lakehouses, notebooks and warehouses in manifests under
   `items/<workspace>/`, validated by `schemas/item.schema.json`.
2. Enforce item rules from `rules/items.yaml` on every PR with
   `scripts/validate_items.py`.
3. Create and update items on merge with `scripts/provision_items.py`, which
   calls the Fabric REST APIs as the SPN.
4. Report item drift from `scripts/drift.py`.
5. Write item code with the `spark-cli` and `sqldw-cli` Skills, and check the
   result from chat with the Fabric Core MCP.

## Prerequisites

- Challenges [00](../00-setup/challenge.md) and
  [01](../01-workspace-as-code/challenge.md) complete: `scripts/validate.py`,
  `scripts/provision.py` and `scripts/drift.py` run in your repo.
- The SPN's group, `sg-fabric-workspace-provisioner`, is enabled in "Service
  principals can call Fabric public APIs", as in challenge 00. The SPN isn't a
  Fabric administrator.
- The tenant tag `Gold` exists.
  [Challenge 09](../09-onelake-catalog-metadata/challenge.md) manages tags as
  code; until then, a Fabric administrator creates the tag in the admin portal.

This challenge works in `dev-fin-revenue`. Merge its manifest,
`workspaces/dev-fin-revenue.yaml`, so that challenge 01's pipeline creates it:

```yaml
name: dev-fin-revenue
environment: dev
team: fin
domain: dom-fin-corp
subDomain: sdm-fin-rev
description: "Development workspace for finance revenue reporting, from raw invoices to gold tables."
capacity: contosononprodf2
region: northeurope
sensitivityLabel: General
costCenter: CC-1001
owners:
  - principalType: Group
    identifier: <object-id-of-grp_fabric_dev_fin_admin>
    role: Admin
    groupName: grp_fabric_dev_fin_admin
  - principalType: Group
    identifier: <object-id-of-grp_fabric_dev_fin_contributor>
    role: Contributor
    groupName: grp_fabric_dev_fin_contributor
```

Replace the placeholders with your Entra group object IDs. The SPN creates
the workspace, so it's an Admin there; Task 4 needs Contributor or higher.

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

Task 1 also uses the documentation tools of the local Fabric MCP server. Add it
from a terminal:

```bash
copilot mcp add fabric-local -- npx -y @microsoft/fabric-mcp@latest server start --mode all
```

## Tasks

### Task 1 — Describe each item

Add `schemas/item.schema.json` for manifests saved as
`items/<workspace>/<name>.yaml`, one per item:

- `workspace`: matches the folder name and a manifest in `workspaces/`.
- `type`: `Lakehouse`, `Notebook` or `Warehouse`.
- `name`: the item's display name.
- `description`: 30 to 256 characters. Fabric caps item descriptions at 256.
- `owner`: the accountable group, one of the `groupName` values in the
  workspace manifest's `owners`. Fabric has no API to set an item's owner, so
  the manifest records it.
- `sensitivityLabel`: required. Items don't inherit the workspace manifest's
  label.
- `tags`: up to 10 tag names, the most Fabric allows on an item.
- One block for the type: `lakehouse.schemaEnabled`, `notebook.source` (the
  notebook file, in the same folder) or `warehouse.collation`.

Save this as `items/dev-fin-revenue/lh_bronze_revenue.yaml`:

```yaml
workspace: dev-fin-revenue
type: Lakehouse
name: lh_bronze_revenue
description: "Raw invoice and payment extracts from the finance ERP, landed daily and kept unchanged for replay and audit."
owner: grp_fabric_dev_fin_admin
sensitivityLabel: General
tags: []
lakehouse:
  schemaEnabled: true
```

Add `lh_silver_revenue.yaml` the same way, with the description "Cleaned and
deduplicated invoices with standard currency codes, one row per invoice, ready
for the gold tables."

Save the warehouse as `items/dev-fin-revenue/wh_gold_revenue.yaml`:

```yaml
workspace: dev-fin-revenue
type: Warehouse
name: wh_gold_revenue
description: "Gold tables for revenue reporting: a date dimension and daily revenue by product, region and currency."
owner: grp_fabric_dev_fin_admin
sensitivityLabel: Confidential
tags: [Gold]
warehouse:
  collation: Latin1_General_100_CI_AS_KS_WS_SC_UTF8
```

Two settings are fixed when an item is created: whether a lakehouse has
schemas, and a warehouse's collation. Challenge 05's materialized lake views
need schema-enabled lakehouses, and Fabric can't yet add schemas to an existing
lakehouse. This warehouse is case-insensitive; the default collation,
`Latin1_General_100_BIN2_UTF8`, is case-sensitive. To change either setting,
create a new item and move the data.

Save the notebook's manifest as
`items/dev-fin-revenue/nb_silver_clean_revenue.yaml`:

```yaml
workspace: dev-fin-revenue
type: Notebook
name: nb_silver_clean_revenue
description: "Cleans bronze invoices into the silver lakehouse: drops rows without a customer, keeps one row per invoice and upper-cases currency codes."
owner: grp_fabric_dev_fin_contributor
sensitivityLabel: General
tags: []
notebook:
  source: nb_silver_clean_revenue.py
```

Before writing the notebook, check what Fabric expects. Ask the local Fabric
MCP server:

> Use docs_item-definitions and docs_item-api-spec to show what a Notebook definition contains, and which creationPayload fields Lakehouse and Warehouse accept.

In a Copilot CLI session:

```text
/spark-cli
```

Ask it to write `items/dev-fin-revenue/nb_silver_clean_revenue.py` in the
Fabric Git source format, with no default lakehouse. The notebook reads
`lh_bronze_revenue.erp.invoices`, drops rows without a `customer_id`, keeps
one row per `invoice_id`, trims and upper-cases `currency_code`, and writes
`lh_silver_revenue.revenue.invoices`. Ask for the file only: the provisioner
creates the notebook in Task 4. The file must start with
`# Fabric notebook source`, like this:

```python
# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

from pyspark.sql import functions as F

spark.sql("CREATE SCHEMA IF NOT EXISTS lh_silver_revenue.revenue")

invoices = (
    spark.read.table("lh_bronze_revenue.erp.invoices")
    .where(F.col("customer_id").isNotNull())
    .dropDuplicates(["invoice_id"])
    .withColumn("currency_code", F.upper(F.trim(F.col("currency_code"))))
)

invoices.write.mode("overwrite").saveAsTable("lh_silver_revenue.revenue.invoices")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
```

With no default lakehouse, the notebook names each table as
`lakehouse.schema.table` and holds no lakehouse or workspace IDs. If it needs a
secret, it reads it at run time with
`notebookutils.credentials.getSecret("https://kv-contoso-fin.vault.azure.net/", "<secret-name>")`.
Task 2 adds a rule that fails any PR with a key pasted in.

From now on, these manifests are the only way the items change. A description
or tag edited in the portal or from chat is drift, and the next provisioning
run puts the manifest's value back.

### Task 2 — Item rules

Keep item rules in a file of their own, `rules/items.yaml`, so that
`rules/policy.yaml` and its identical copy `api/policy.yaml` stay about
workspaces:

```yaml
namePatterns:
  Lakehouse: '^lh_[a-z0-9_]{3,40}$'
  Notebook: '^nb_[a-z0-9_]{3,60}$'
  Warehouse: '^wh_[a-z0-9_]{3,40}$'
description:
  minLength: 30
  maxLength: 256
maxTags: 10
environments: [sbx, dev]
immutableFields:
  Lakehouse: [lakehouse.schemaEnabled]
  Warehouse: [warehouse.collation]
secretPatterns:
  - 'AccountKey='
  - 'SharedAccessSignature='
  - 'sig=[A-Za-z0-9%]{20,}'
  - 'client_secret\s*='
  - 'PRIVATE KEY-----'
```

Add a `rules` list in the format of `rules/policy.yaml`, with one entry for
each rule below, each with `severity: block`:

| Rule | Fails when |
|---|---|
| `item-manifest-path` | The file isn't at `items/<workspace>/<name>.yaml`, or `workspaces/` has no manifest for `<workspace>`. |
| `item-schema` | The manifest doesn't match `schemas/item.schema.json`. |
| `item-naming` | The name doesn't match the pattern for its type. |
| `item-description-length` | The description is shorter than 30 or longer than 256 characters. |
| `item-owner-group` | `owner` isn't the `groupName` of a Group in the workspace manifest's `owners`. |
| `item-label-at-least-workspace` | The label isn't in `approvedSensitivityLabels` in `rules/policy.yaml`, or comes before the workspace manifest's label in that list. |
| `item-tags` | There are more than 10 tags. With `LIVE_CHECKS=true`, also a tag that List Tags doesn't return. |
| `item-environment` | The workspace manifest's `environment` isn't `sbx` or `dev`. |
| `notebook-source-format` | The notebook file is missing, doesn't start with `# Fabric notebook source`, or sets `default_lakehouse` in its metadata. |
| `notebook-no-hardcoded-secret` | The notebook file matches an entry in `secretPatterns`. |
| `warehouse-must-set-collation` | A warehouse manifest has no `collation`. |
| `immutable-field-changed` | A field in `immutableFields` differs from the manifest on `main`, read with `git show origin/main:<path>`. |

Items reach `stg` and `prd` through deployment pipelines in
[challenge 08](../08-deployment-pipelines/challenge.md), so `items/` covers
only `sbx` and `dev` workspaces.
[Challenge 09](../09-onelake-catalog-metadata/challenge.md) keeps production
item descriptions and tags in `catalog/`.

### Task 3 — Check every PR

Write `scripts/validate_items.py`, modeled on `scripts/validate.py`. It checks
the manifests under `items/` (only the changed ones with `--changed-only`),
writes `items-report.md`, and exits 0 when every rule passes, 1 on a failure
and 2 when a live check gets a 401 or 403. Add `items-report.md` to
`.gitignore`.

In `.github/workflows/validate.yml`, add `'items/**'` to
`on.pull_request.paths`, and add two steps at the end of the job:

```yaml
      - name: Validate items
        if: always()
        env:
          LIVE_CHECKS: ${{ vars.LIVE_CHECKS || 'false' }}
        run: python scripts/validate_items.py --changed-only

      - name: Sticky PR comment (items)
        if: ${{ always() && hashFiles('items-report.md') != '' }}
        uses: marocchino/sticky-pull-request-comment@5770ad5eb8f42dd2c4f34da00c94c5381e49af88 # v3.0.5
        with:
          header: item-validation
          path: items-report.md
```

`always()` runs the item checks even when the workspace checks fail, so a PR
shows both reports.

Open a PR with the files from Tasks 1 to 3, and merge it when the check
passes.

**Deliberate failure:** open a second PR that cuts the notebook's description
to 20 characters, adds `AccountKey=not-a-real-key` to its source, and changes
the warehouse's collation to `Latin1_General_100_BIN2_UTF8`. All three must
fail.

### Task 4 — Provision items on merge

The workflow runs unattended as the SPN, and no MCP tool runs there, so the
provisioner calls the Fabric REST APIs. Write `scripts/provision_items.py`:

1. Add item helpers to `scripts/_fabric.py`, built on `_request` and `_paged`
   so they keep its retries and raise `AuthError` on 401 or 403:
   `list_items`, `get_item`, `create_item`, `update_item`,
   `get_item_definition`, `update_item_definition`, `apply_item_tags` and
   `unapply_item_tags`.
2. For each folder under `items/`, find the workspace with
   `get_workspace_by_name`. If the SPN can't see it, fail that folder's
   manifests and go on.
3. Call List Items once per workspace, and match manifests on type and display
   name.
4. Create each missing item with Create Item
   (`POST /v1/workspaces/{workspaceId}/items`). A lakehouse gets
   `"creationPayload": {"enableSchemas": true}`, because REST doesn't enable
   schemas unless asked. A warehouse gets
   `"creationPayload": {"defaultCollation": "<collation>"}`. A notebook gets a
   definition with one part, `notebook-content.py`, holding the file as
   `InlineBase64`. A request can't carry both a definition and a creation
   payload. Create Item can answer 202: poll the `Location` URL, honoring
   `Retry-After`, until the operation succeeds or fails.
5. For existing items, read the description and tags with Get Item, and update
   a changed description with Update Item. For a notebook, compare Get Item
   Definition with the file, and call Update Item Definition when they differ.
6. Map tag names to IDs with one List Tags call, as `provision.py` does. Apply
   missing tags with Apply Tags and remove extra ones with Unapply Tags.

Write only what changed. Apply Tags and Unapply Tags need Contributor or higher
on the workspace. The tag APIs allow 25 requests a minute, so back off on HTTP
429; `_fabric.py` already honors `Retry-After`.

Exit 0 when every manifest applied, 1 when any manifest failed, and 3 on a 401
or 403, which stops the run, as `provision.py` does. With `DRY_RUN=true`, log
the plan and call no API. Never delete an item: one without a manifest shows up
in the drift report, and a person decides what to do with it.

The provisioner doesn't set sensitivity labels: the SPN isn't in a label
publishing policy, so it can't apply one. Create Item accepts a
`sensitivityLabelSettings` object, but leave it out: its default strategy,
`ApplyOrFail`, fails the whole request when the label can't be applied. Apply
each item's label by hand in its settings.
[Challenge 03](../03-domains-capacities-sensitivity/challenge.md), Task 5,
covers the other routes.

Once [challenge 08](../08-deployment-pipelines/challenge.md) connects
`dev-fin-revenue` to Git, Git owns the notebook's content: remove the
definition update, and keep descriptions and tags.

In `.github/workflows/provision.yml`, add `'items/**'` to `paths`, and add this
step after "Provision workspaces":

```yaml
      - name: Provision items
        env:
          DRY_RUN: ${{ vars.DRY_RUN || 'false' }}
        run: python scripts/provision_items.py
```

Merging this change starts the workflow, because it touches `scripts/**`.
Check that the four items exist, then run the workflow again from the Actions
tab: the second run must write nothing.

### Task 5 — Report item drift

Extend `check()` in `scripts/drift.py`. For each managed workspace with a
folder under `items/`, take its ID from the inventory `check()` already builds.
Skip a workspace the SPN can't see: `drift.py` already lists it as not visible.
Call List Items, then Get Item for each item. Skip `SQLEndpoint` items, which
Fabric creates with each lakehouse.

Report:

- items with no manifest, and manifests with no item;
- descriptions and tags that differ from the manifest;
- items with no sensitivity label.

Once challenge 03 has added `rules/labels.yaml`, also flag an item whose label
ID isn't the one for its manifest's label. Challenge 03 checks the label floor
across the workspace.

Write the findings under `## Items`, add an "Items with drift" bullet to the
summary, and count them as drift in what `check()` returns.

When it finds drift, `drift.py` exits 2, and the shipped `drift.yml` opens a
new issue, "Fabric workspace drift detected", labeled `drift` and
`governance`, with the report as its body. Each run opens a new issue until the
drift is gone, and the workflow never closes them, so close them yourself after
a clean rerun. On 401 or 403 `drift.py` exits 3, which fails the job instead;
keep those codes for the new checks.

### Task 6 — Build the gold tables and check from chat

In a Copilot CLI session:

```text
/sqldw-cli
```

Ask it to create two tables in `wh_gold_revenue`, and to save the DDL to
`items/dev-fin-revenue/wh_gold_revenue.sql`:

```sql
CREATE TABLE dbo.dim_date (
    date_key int NOT NULL,
    calendar_date date NOT NULL,
    calendar_year smallint NOT NULL,
    calendar_quarter smallint NOT NULL,
    calendar_month smallint NOT NULL,
    month_name varchar(9) NOT NULL
);

CREATE TABLE dbo.fact_revenue (
    date_key int NOT NULL,
    product_id varchar(20) NOT NULL,
    region_code varchar(10) NOT NULL,
    currency_code char(3) NOT NULL,
    invoice_count int NOT NULL,
    revenue_amount decimal(18, 2) NOT NULL
);
```

The Skill connects as you, so you need a role in `dev-fin-revenue` through one
of its owner groups. Merge the `.sql` file through a PR: it's the reviewed
record of the schema, because the provisioner doesn't run DDL. From challenge
08, Git integration stores the warehouse schema as a SQL database project.

Then ask the Core MCP:

> List the items in dev-fin-revenue with each one's description, sensitivity label and tags. Then get the definition of nb_silver_clean_revenue, decode notebook-content.py, and compare it with items/dev-fin-revenue/nb_silver_clean_revenue.py in this repo.

The answer comes from `list_items`, `get_item` and `get_item_definition`. If it
shows no sensitivity label for an item, check with Get Item over REST.
Promoting these items to `stg-fin-revenue` and `prd-fin-revenue` is
[challenge 08](../08-deployment-pipelines/challenge.md).

## Success criteria

- [ ] The four items exist in `dev-fin-revenue` with the descriptions, tags
      and labels from their manifests.
- [ ] The three changes in the Task 3 deliberate failure each fail validation.
- [ ] A second provisioning run writes nothing.
- [ ] An item you create by hand appears under `## Items` in the drift report,
      and the provisioner leaves it alone.
- [ ] A tag you remove in the portal shows up as drift, and a manual
      `provision.yml` run puts it back.
- [ ] From chat, the Core MCP confirms that the notebook in Fabric matches
      `items/dev-fin-revenue/nb_silver_clean_revenue.py`.

## Stretch goals

- **Column descriptions.** Challenge 09's stretch goal for table and column
  descriptions also applies to the silver and gold tables here.
- **Row-level security.** Ask `/sqldw-cli` for a security policy on
  `fact_revenue` that filters rows by `region_code`, and keep the DDL in
  `wh_gold_revenue.sql`.

> **Preview** (checked 2026-11-27): Workspace folder REST APIs — [Learn](https://learn.microsoft.com/rest/api/fabric/core/folders). GA route: none; stretch task.

- **Folders.** Add an optional `folder` to the manifest. Have the provisioner
  create missing folders and move items into them with Bulk Move Items, up to
  50 items per call. The Core MCP tools are `create_folder` and
  `bulk_move_items`.

> **Preview** (checked 2026-11-27): Item relations API (beta) — [Learn](https://learn.microsoft.com/rest/api/fabric/core/items). GA route: the scanner's lineage output.

- **Lineage check.** In `drift.py`, call Get Upstream Relations with
  `beta=true` for each item that has a manifest, and flag any upstream item
  that has none.

## MCP tips

- The local server's `docs_` tools read bundled documentation and never touch
  your tenant.
- `create_item` and `update_item` work from chat, but an item or description
  changed that way is drift until a manifest says so. Try things in chat, then
  put the result in a manifest.
- `get_item_definition` returns each part in Base64. Ask Copilot to decode it
  before comparing it with the repo.
- No MCP tool covers tags or sensitivity labels, so the scripts call REST.

## Skills tips

- Ask `spark-cli` for the Fabric Git source format and no default lakehouse,
  and decline its offers to create or run the notebook in Fabric: the
  provisioner creates it.
- `sqldw-cli` runs as you, not as the SPN. Keep every DDL change in
  `wh_gold_revenue.sql`, so the PR review sees it.
- If the Skills aren't installed, run these from a terminal:

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

## Repository files

This challenge extends these files in the repo root:

- `scripts/_fabric.py` (item helpers) and `scripts/drift.py`
- `.github/workflows/validate.yml` and `.github/workflows/provision.yml`
- `.gitignore`

It adds:

- `items/<workspace>/*.yaml`, with each notebook's `.py` file and each
  warehouse's `.sql` file
- `schemas/item.schema.json`
- `rules/items.yaml`
- `scripts/validate_items.py` and `scripts/provision_items.py`

## References

- [Item management overview](https://learn.microsoft.com/rest/api/fabric/articles/item-management/item-management-overview)
- [List Items REST API](https://learn.microsoft.com/rest/api/fabric/core/items/list-items)
- [Create Item REST API](https://learn.microsoft.com/rest/api/fabric/core/items/create-item)
- [Get Item REST API](https://learn.microsoft.com/rest/api/fabric/core/items/get-item)
- [Update Item REST API](https://learn.microsoft.com/rest/api/fabric/core/items/update-item)
- [Notebook definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/notebook-definition)
- [Warehouse definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/warehouse-definition)
- [Lakehouse schemas](https://learn.microsoft.com/fabric/data-engineering/lakehouse-schemas)
- [Warehouse collation](https://learn.microsoft.com/fabric/data-warehouse/collation)
- [Apply Tags REST API](https://learn.microsoft.com/rest/api/fabric/core/tags/apply-tags)
- [Unapply Tags REST API](https://learn.microsoft.com/rest/api/fabric/core/tags/unapply-tags)
- [List Tags REST API](https://learn.microsoft.com/rest/api/fabric/core/tags/list-tags)
- [Notebook source control and deployment](https://learn.microsoft.com/fabric/data-engineering/notebook-source-control-deployment)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [MCP servers and Skills](../../docs/mcp-and-skills.md)
- [`spark-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/spark-cli)
- [`sqldw-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/sqldw-cli)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
