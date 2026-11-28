# Challenge 05 — Medallion architecture bootstrap

> **Outcome:** one manifest declares the bronze, silver and gold layers of
> `dev-fin-revenue`: three lakehouses, the notebooks that fill them, gold
> materialized lake views and a Direct Lake semantic model. Validation blocks
> a gold item that isn't Certified and Confidential, schedules keep gold
> current, and the drift report audits endorsement.

## Why this challenge exists

[Challenge 02](../02-items-as-code/challenge.md) governs items one at a time,
but a medallion only works as a set: notebooks fill bronze and silver, gold
views read silver, and a semantic model reads gold. This challenge declares
the set in one manifest, checks it on every pull request, and holds gold to a
higher bar: certified by a person, labeled Confidential and refreshed on a
schedule. Each layer gets its own lakehouse in the same workspace, because
labels, endorsement and item permissions apply per item. One lakehouse split
into schemas can't make only gold Confidential and Certified.

## Learning objectives

1. Declare a medallion in `medallion/<name>.yaml` and validate it, with its
   items, on every pull request.
2. Build gold as materialized lake views and refresh them on a schedule.
3. Create a Direct Lake semantic model from files in the repo.
4. Govern gold: certified by a person, labeled Confidential and audited by
   the drift report.
5. Scaffold the layers with the `e2e-medallion-architecture` Skill, from chat
   and from a workflow, and check the result with the Fabric MCP servers.

## Prerequisites

- Challenges [00](../00-setup/challenge.md),
  [01](../01-workspace-as-code/challenge.md),
  [02](../02-items-as-code/challenge.md) and
  [03](../03-domains-capacities-sensitivity/challenge.md) complete. Challenge
  02's item manifests, `scripts/validate_items.py` and
  `scripts/provision_items.py` run in your repo, and challenge 03 added the
  item label scan to `scripts/drift.py`.
- The SPN's group, `sg-fabric-workspace-provisioner`, is enabled in "Service
  principals can call Fabric public APIs" and "Service principals can access
  read-only admin APIs", as in challenge 03. The SPN isn't a Fabric
  administrator.
- A Fabric administrator has decided who can certify items, in the
  Certification tenant setting or by delegating certification to domain
  admins, and you can certify. The setting is at OneLake catalog > Govern >
  Configurations > Tenant settings > Export and sharing settings; where Govern
  isn't available, use Settings > Admin portal > Tenant settings.
- The tenant tag `Gold` exists, as in challenge 02.
- You have Contributor or higher in `dev-fin-revenue`, to run notebooks and
  create schedules.

This challenge extends `dev-fin-revenue` from challenge 02. If you haven't
installed the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

The tasks also use the documentation, OneLake and job tools of the local
Fabric MCP server, which `--mode all` enables. If you didn't add it in
challenge 02, add it from a terminal:

```bash
copilot mcp add fabric-local -- npx -y @microsoft/fabric-mcp@latest server start --mode all
```

## Tasks

### Task 1 — Declare the medallion

Write `medallion/finance-revenue.yaml`:

```yaml
name: finance-revenue
description: "Finance revenue medallion: ERP invoices through bronze and silver to certified gold views and a semantic model."
team: fin
stages:
  dev: dev-fin-revenue
  stg: stg-fin-revenue
  prd: prd-fin-revenue
sourceSystem:
  type: AzureSql
  keyVault: https://kv-contoso-fin.vault.azure.net/
  secretName: fin-revenue-sql
tiers:
  bronze:
    lakehouse: lh_bronze_revenue
    notebooks: [nb_bronze_ingest_revenue]
  silver:
    lakehouse: lh_silver_revenue
    notebooks: [nb_silver_clean_revenue]
  gold:
    lakehouse: lh_gold_revenue
schedule:
  timeZone: UTC
  bronze: "02:00"
  silver: "03:00"
  gold: "04:00"
```

- `stages` maps each environment to its workspace. The items live in the
  first stage, `dev-fin-revenue`, and
  [challenge 08](../08-deployment-pipelines/challenge.md) promotes the gold
  layer through `stg-fin-revenue` to `prd-fin-revenue`.
- `sourceSystem` says where bronze comes from and which Key Vault secret
  holds the connection. This lab's ingest notebook writes sample rows instead.
- `tiers` names each layer's lakehouse and the notebooks that fill it. Task 4
  adds `notebooks: [nb_gold_mlv_revenue]` to gold, and Task 5 adds
  `semanticModels: [sm_gold_revenue]`.
- `schedule` sets the daily start of each layer.

The warehouse from challenge 02, `wh_gold_revenue`, stays outside the
medallion. Gold here is a lakehouse, because materialized lake views live in
lakehouses.

Write `schemas/medallion.schema.json`, in the style of challenge 02's
`schemas/item.schema.json`, so that:

- `name`, `description`, `team`, `stages`, `tiers` and `schedule` are
  required, `sourceSystem` is optional, and no other fields are allowed.
- `name` matches `^[a-z0-9-]{3,40}$`, and `description` is 30–256 characters.
- The keys of `stages` are environments: exactly one of `sbx` and `dev`,
  which holds the items, plus optional `stg` and `prd`.
- `tiers.bronze` is required, and `tiers.gold` requires `tiers.silver`. Each
  tier has a `lakehouse` and optional `notebooks`; gold may also list
  `semanticModels`.
- `schedule` has a `timeZone` and an `"HH:MM"` start for each tier.

Extend challenge 02's schema and rules for the gold items:

- In `schemas/item.schema.json`, add `SemanticModel` to `type`, with a
  `semanticModel` block whose `source` names its definition folder (Task 5).
  Add an optional `endorsement`, `Promoted` or `Certified`, after
  `sensitivityLabel`.
- In `rules/items.yaml`, add `SemanticModel: '^sm_[a-z0-9_]{3,40}$'` to
  `namePatterns`.

The `stg` stage needs a workspace manifest. Challenge 03 declared
`prd-fin-revenue`; add `workspaces/stg-fin-revenue.yaml` so that challenge
01's pipeline creates the staging workspace:

```yaml
name: stg-fin-revenue
environment: stg
team: fin
domain: dom-fin-corp
subDomain: sdm-fin-rev
description: "Staging workspace for finance revenue reporting, promoted from dev by the deployment pipeline."
capacity: contosononprodf2
region: northeurope
sensitivityLabel: Confidential
costCenter: CC-2042
owners:
  - principalType: Group
    identifier: <object-id-of-grp_fabric_stg_fin_admin>
    role: Admin
    groupName: grp_fabric_stg_fin_admin
  - principalType: Group
    identifier: <object-id-of-grp_fabric_stg_fin_member>
    role: Member
    groupName: grp_fabric_stg_fin_member
```

Replace the placeholders with your Entra group object IDs.

### Task 2 — Validate the medallion

Extend `scripts/validate_items.py` to check every `medallion/*.yaml` against
its schema, its workspaces and its items. Run these checks even with
`--changed-only`, so that a pull request that edits only
`lh_gold_revenue.yaml` still meets the gold rules. Findings go in the same
`items-report.md` and sticky comment as challenge 02's, and a blocking
finding exits 1. In `.github/workflows/validate.yml`, add `'medallion/**'` to
`on.pull_request.paths`.

Add these rules to `rules/items.yaml`, each with `severity: block`:

| Rule | Fails when |
| --- | --- |
| `medallion-schema` | The manifest breaks `schemas/medallion.schema.json`, or `name` isn't the file name. |
| `medallion-stages` | A stage's workspace has no manifest under `workspaces/`, its `environment` isn't the stage key, or its `team` isn't the medallion's. |
| `medallion-tier-items` | A tier names an item with no manifest under `items/<workspace>/` for the `sbx` or `dev` stage, or the manifest's `type` doesn't fit the tier. |
| `medallion-gold-schema-enabled` | The gold lakehouse doesn't set `lakehouse.schemaEnabled: true`. |
| `gold-metadata-minimum` | A gold lakehouse or semantic model lacks `endorsement: Certified`, or its label comes before Confidential in `approvedSensitivityLabels`. |
| `medallion-schedule-order` | A tier starts at or before the tier it reads from. |

Key `medallion-stages` on each workspace manifest's `environment`, never on a
name prefix. `gold-metadata-minimum` orders labels the way challenge 02's
`item-label-at-least-workspace` does. Gold notebooks are exempt: people read
gold through the lakehouse and the model.

The medallion names items that Task 3 writes, so open one pull request for
Tasks 1 to 3.

### Task 3 — Scaffold bronze and gold

Ask the local Fabric MCP server:

> Use docs_item-definitions to show the Lakehouse and Notebook definition parts.

In a Copilot CLI session:

```text
/e2e-medallion-architecture
```

Ask it to write files only, for the existing `dev-fin-revenue`:

- three schema-enabled lakehouses in that workspace, one per layer;
- challenge 02's `lh_bronze_revenue`, `lh_silver_revenue` and
  `nb_silver_clean_revenue`, unchanged;
- manifests in challenge 02's format for `lh_gold_revenue` and a bronze
  ingest notebook, `nb_bronze_ingest_revenue`;
- no items, workspaces or runs in Fabric.

The Skill prefers one schema-enabled lakehouse with a schema per layer, and
calls a workspace per layer the legacy layout. This lab uses three lakehouses
in one workspace: labels and endorsement apply per item, and challenge 08
promotes one workspace per stage. Check the result against these files and
fix any difference.

`items/dev-fin-revenue/lh_gold_revenue.yaml`:

```yaml
workspace: dev-fin-revenue
type: Lakehouse
name: lh_gold_revenue
description: "Gold materialized lake views for revenue reporting: daily net revenue by product, region and currency, with a date dimension."
owner: grp_fabric_dev_fin_admin
sensitivityLabel: Confidential
endorsement: Certified
tags: [Gold]
lakehouse:
  schemaEnabled: true
```

`items/dev-fin-revenue/nb_bronze_ingest_revenue.yaml`:

```yaml
workspace: dev-fin-revenue
type: Notebook
name: nb_bronze_ingest_revenue
description: "Loads ERP invoices into lh_bronze_revenue.erp.invoices. In this lab it writes sample rows instead of reading the ERP."
owner: grp_fabric_dev_fin_contributor
sensitivityLabel: General
tags: []
notebook:
  source: nb_bronze_ingest_revenue.py
```

`items/dev-fin-revenue/nb_bronze_ingest_revenue.py`, in challenge 02's
notebook format with no default lakehouse:

```python
# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

from datetime import date

from pyspark.sql import functions as F

spark.sql("CREATE SCHEMA IF NOT EXISTS lh_bronze_revenue.erp")

rows = [
    ("INV-1001", "C-001", date(2026, 11, 2), "P-10", "EMEA", "GBP", 1250.00),
    ("INV-1001", "C-001", date(2026, 11, 2), "P-10", "EMEA", "GBP", 1250.00),
    ("INV-1002", None, date(2026, 11, 2), "P-11", "EMEA", "CHF", 830.50),
    ("INV-1003", "C-002", date(2026, 11, 3), "P-10", "EMEA", "gbp ", 410.00),
    ("INV-1004", "C-003", date(2026, 11, 3), "P-12", "APAC", "JPY", 98000.00),
    ("INV-1005", "C-004", date(2026, 11, 4), "P-11", "EMEA", "chf", 275.25),
]
columns = [
    "invoice_id",
    "customer_id",
    "invoice_date",
    "product_id",
    "region",
    "currency_code",
    "net_amount",
]

df = (
    spark.createDataFrame(rows, columns)
    .withColumn("net_amount", F.col("net_amount").cast("decimal(18,2)"))
    .withColumn("ingested_at", F.current_timestamp())
)
df.write.mode("append").saveAsTable("lh_bronze_revenue.erp.invoices")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
```

The sample rows include a duplicate invoice, a missing customer and untidy
currency codes, so challenge 02's silver notebook has work to do. A real
ingest reads the source with
`notebookutils.credentials.getSecret("https://kv-contoso-fin.vault.azure.net/", "fin-revenue-sql")`,
never with a connection string in the file.

**Deliberate failure:** remove `endorsement: Certified` from
`lh_gold_revenue.yaml`, or set its `sensitivityLabel` to `General`.
`gold-metadata-minimum` blocks the pull request. `General` alone still passes
`item-label-at-least-workspace`, because `dev-fin-revenue` is labeled
General: the workspace floor isn't enough for gold. Restore both before you
merge.

After the merge, challenge 02's provisioner creates the new items. The SPN
can't apply labels, so label `lh_gold_revenue` Confidential through one of
the routes in [challenge 03](../03-domains-capacities-sensitivity/challenge.md),
Task 5.

Then run bronze, then silver. Ask the local server:

> Run nb_bronze_ingest_revenue in dev-fin-revenue with jobs_run-on-demand-item-job and job type RunNotebook, then check it with jobs_get-item-job-instance until it finishes.

When it succeeds, do the same for `nb_silver_clean_revenue`. The job tools
don't retry or poll on their own, and each call starts a new run: check
`jobs_list-item-job-instances` before you submit again. Bronze appends, so a
second run duplicates rows, and silver's deduplication drops them. Over REST
the call is
`POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/jobs/instances?jobType=RunNotebook`,
and the job type is case sensitive.

### Task 4 — Build gold as materialized lake views

In a Copilot CLI session:

```text
/spark-cli
```

Ask it to write `items/dev-fin-revenue/nb_gold_mlv_revenue.py` in challenge
02's notebook format, with no default lakehouse. The notebook defines two
materialized lake views in `lh_gold_revenue.gold`. The Skill's authoring mode
writes the definitions; its `mlv` mode helps you schedule, refresh, monitor
and diagnose them later. Check the notebook's cells against this Spark SQL:

```sql
CREATE SCHEMA IF NOT EXISTS lh_gold_revenue.gold;

CREATE OR REPLACE MATERIALIZED LAKE VIEW lh_gold_revenue.gold.fact_revenue
COMMENT "Daily net revenue by product, region and currency"
AS
SELECT
    invoice_date,
    product_id,
    region,
    currency_code,
    SUM(net_amount) AS net_amount,
    COUNT(*) AS invoice_count
FROM lh_silver_revenue.revenue.invoices
GROUP BY invoice_date, product_id, region, currency_code;

CREATE OR REPLACE MATERIALIZED LAKE VIEW lh_gold_revenue.gold.dim_date
COMMENT "One row per day from the first to the last invoice date"
AS
WITH bounds AS (
    SELECT MIN(invoice_date) AS first_date, MAX(invoice_date) AS last_date
    FROM lh_silver_revenue.revenue.invoices
),
days AS (
    SELECT explode(sequence(first_date, last_date, interval 1 day)) AS calendar_date
    FROM bounds
)
SELECT
    calendar_date,
    year(calendar_date) AS year,
    month(calendar_date) AS month,
    date_format(calendar_date, 'yyyy-MM') AS year_month
FROM days;
```

- The views read another lakehouse, so name every table in full:
  `lakehouse.schema.table`, or `workspace.lakehouse.schema.table` across
  workspaces.
- Schema names can't be all uppercase: `gold` works, `GOLD` doesn't.
- Scheduled refresh ignores `spark.conf.set` in the notebook. Set any Spark
  property the views need on the lakehouse or the workspace.
- Dropping or renaming a view affects its lineage and scheduled refresh, so
  keep the names stable.

`items/dev-fin-revenue/nb_gold_mlv_revenue.yaml`:

```yaml
workspace: dev-fin-revenue
type: Notebook
name: nb_gold_mlv_revenue
description: "Defines the gold materialized lake views in lh_gold_revenue.gold: fact_revenue and dim_date."
owner: grp_fabric_dev_fin_contributor
sensitivityLabel: General
tags: []
notebook:
  source: nb_gold_mlv_revenue.py
```

Add `notebooks: [nb_gold_mlv_revenue]` to the gold tier in
`medallion/finance-revenue.yaml`, and merge.

After the merge, run `nb_gold_mlv_revenue` once with `RunNotebook`, as in
Task 3. The run creates the views and fills them. Run it again only when a
definition changes: refreshes don't need the notebook. Check the result in
the lakehouse's **Materialized lake views** tab, or ask the local server:

> Use onelake_list-tables to list the tables in lh_gold_revenue in dev-fin-revenue.

**Schedule gold.** The lakehouse refreshes its views through the job
scheduler. Ask the local server first:

> Use jobs_list-item-schedules to list the RefreshMaterializedLakeViews schedules of lh_gold_revenue in dev-fin-revenue.

If there's none, create one. The create call isn't idempotent, so list first
every time:

> Use jobs_create-item-schedule on lh_gold_revenue in dev-fin-revenue with job type RefreshMaterializedLakeViews, enabled true and configuration {"type": "Daily", "startDateTime": "2026-12-01T00:00:00Z", "endDateTime": "2027-12-01T00:00:00Z", "localTimeZoneId": "UTC", "times": ["04:00"]}.

Set `startDateTime` in the future, because an enabled schedule with a past
start can trigger a run at once. `endDateTime` is required, a lakehouse takes
up to 20 schedules, and each runs independently. In the UI the same schedule
is under the lakehouse's **Materialized lake views** tab > **Manage** >
**Manage schedules**. Over REST it's
`POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/jobs/RefreshMaterializedLakeViews/schedules`.

**Schedule the notebooks.** Learn documents no schedule API for notebooks, so
use each notebook's **Schedule** menu: `nb_bronze_ingest_revenue` daily at
02:00 UTC and `nb_silver_clean_revenue` at 03:00 UTC. Schedules don't wait
for each other, so leave each layer time to finish. Under **Failure
notifications**, add `grp_fabric_dev_fin_contributor`. Notifications cover
all of a notebook's schedules and are sent only for scheduled runs.

**Know who runs each schedule.** A notebook runs as the person who created or
last updated its schedule. Ask `jobs_list-item-schedules` for each item's
schedules and owners, and plan for these rules:

- Creating or changing a schedule needs Contributor or higher in the
  workspace, or Write permission on the item.
- A schedule expires if its owner doesn't sign in to Fabric for 90
  consecutive days.
- Taking over an item doesn't transfer its schedules or their
  authentication context. Update each schedule after a takeover.
- After repeated failures, typically 10 in a row, Fabric disables a schedule.
  Fix the cause, then enable it again.
- A successful on-demand run doesn't prove that a schedule can run.

A deployment includes an item's schedules, so gold's refresh schedule goes
with `lh_gold_revenue` to each stage. A lakehouse deployment doesn't carry
tables or Spark views, and the views read `lh_silver_revenue` in their own
workspace. After challenge 08 deploys gold, check each stage's schedules and
owners the same way, and disable the refresh schedule in any stage where the
views don't exist.

### Task 5 — Create the semantic model from files

In a Copilot CLI session:

```text
/semantic-model-authoring
```

Ask it for a Direct Lake semantic model, `sm_gold_revenue`, over
`gold.fact_revenue` and `gold.dim_date` in `lh_gold_revenue`, as TMDL files
only, with a relationship from `fact_revenue[invoice_date]` to
`dim_date[calendar_date]`. Decline its offer to deploy: its deploy isn't
idempotent, and a second run leaves two models with the same name. Keep only
`items/dev-fin-revenue/sm_gold_revenue.SemanticModel/`, and delete any
`.Report` folder or `.pbip` file it adds. The folder holds:

```text
sm_gold_revenue.SemanticModel/
  definition.pbism
  definition/
    database.tmdl
    model.tmdl
    expressions.tmdl
    relationships.tmdl
    tables/
      fact_revenue.tmdl
      dim_date.tmdl
```

There's no `.platform` file, diagram layout or report. A `definition/` folder
and a `model.bim` file are mutually exclusive, and the model needs
compatibility level 1604 or higher, set in `database.tmdl`.
`definition.pbism`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  "version": "5.0",
  "settings": {
    "qnaEnabled": false
  }
}
```

The Direct Lake connection is a shared expression in
`definition/expressions.tmdl`. Indent TMDL with tabs:

```tmdl
expression 'DirectLake - sm_gold_revenue' =
		let
		    Source = AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/<workspace-id>/<lakehouse-id>", [HierarchicalNavigation = true])
		in
		    Source
```

Each table ends with a Direct Lake partition that reads one view. In
`definition/tables/fact_revenue.tmdl`:

```tmdl
	partition fact_revenue = entity
		mode: directLake
		source
			entityName: fact_revenue
			schemaName: gold
			expressionSource: 'DirectLake - sm_gold_revenue'
```

Use the lakehouse's ID in the URL, not the ID of its SQL analytics endpoint.
In [challenge 08](../08-deployment-pipelines/challenge.md), Task 1 replaces
the URL with a parameter, and Task 6 sets it in each stage so that each stage
reads its own lakehouse.

`items/dev-fin-revenue/sm_gold_revenue.yaml`:

```yaml
workspace: dev-fin-revenue
type: SemanticModel
name: sm_gold_revenue
description: "Certified Direct Lake model over the gold revenue views in lh_gold_revenue, for finance revenue reports."
owner: grp_fabric_dev_fin_admin
sensitivityLabel: Confidential
endorsement: Certified
tags: [Gold]
semanticModel:
  source: sm_gold_revenue.SemanticModel
```

Add `semanticModels: [sm_gold_revenue]` to the gold tier in
`medallion/finance-revenue.yaml`.

Extend `scripts/provision_items.py` and `scripts/_fabric.py` for semantic
models:

1. Create the model only when List Items doesn't return it. Send every file
   in the folder as an `InlineBase64` part, with its path relative to the
   folder, and poll the `Location` URL as challenge 02 does.
2. After that, manage only its description and tags. The definition Fabric
   returns can differ from the files you sent, so comparing them could
   rewrite the model on every run.
3. Once challenge 08 connects `dev-fin-revenue` to Git, Git owns the
   definition. Until then, change it from chat with the Core MCP's
   `update_item_definition`. It replaces the whole definition, so send every
   part, and commit the same change.

After the merge, check the model's settings:

- Direct Lake reads OneLake with each user's identity by default, so report
  readers need read access to the gold data. A cloud connection with a fixed
  identity is the alternative.
- **Keep your Direct Lake data up to date** is on by default, so the model
  picks up each refresh of the views without a refresh schedule of its own.
  Framing runs as the model's owner.
- Anyone who can query the lakehouse's SQL analytics endpoint reads gold
  without the model's permissions, so grant lakehouse access with the same
  care.

Then ask the Core MCP:

> Get sm_gold_revenue in dev-fin-revenue and its definition, decode definition/expressions.tmdl, and confirm that its URL holds the ID of lh_gold_revenue.

The answer comes from `list_items`, `get_item` and `get_item_definition`.

### Task 6 — Certify, label and audit gold

Endorsement follows the same rule everywhere. Declare it in the manifest,
audit it with the scanner API or catalog search, and have a person who can
certify apply it in the UI. There's no endorsement write API; never script
one.

**Certify.** Open the settings of `lh_gold_revenue` in `dev-fin-revenue`,
expand **Endorsement**, select **Certified**, and select **Apply**. Do the
same for `sm_gold_revenue`. You need write permission on each item as well as
the right to certify; if you can't certify, ask someone who can.

**Label.** Label `sm_gold_revenue` Confidential through a route from
challenge 03, Task 5, as you did for `lh_gold_revenue`.

**Audit in `drift.py`.** No MCP tool runs the scanner, so `drift.py` calls it
over REST. The metadata scanner (Power BI admin API; no Fabric API yet) that
challenge 03, Task 6, uses for labels also returns each item's
`endorsementDetails`, so reuse that scan rather than adding a second one.
Compare `endorsementDetails.endorsement` with each manifest's `endorsement`,
and write mismatches under `## Items` with the expected and actual values. A
semantic model without `endorsementDetails` is unendorsed. If a lakehouse
comes back without it, report the lakehouse as unchecked, not as drift.

Count the mismatches as drift. `drift.py` then exits 2, and the shipped
`drift.yml` opens a new "Fabric workspace drift detected" issue, labeled
`drift` and `governance`; on 401 or 403 it still exits 3. `drift.yml` doesn't
change. [Challenge 09](../09-onelake-catalog-metadata/challenge.md), Task 4,
later adds an `## Endorsement` section for the whole estate.

**Deliberate failure:** remove the certification from `sm_gold_revenue` in
the UI and run the drift workflow from the Actions tab. The new issue lists
the mismatch under `## Items`. Certify the model again, rerun the workflow,
and close the issue after a clean run.

**Find gold in the catalog.** In OneLake catalog > Explore, filter on
**Endorsed items** and show the **Endorsement** and **Sensitivity** columns:
both gold items show Certified and Confidential.

> **Preview** (checked 2026-11-27): Catalog Search API, which the Core MCP `search_catalog` tool calls — [Learn](https://learn.microsoft.com/rest/api/fabric/core/catalog/search). GA route: List Items, which returns descriptions and tags.

Ask the Core MCP:

> Use search_catalog to find the gold revenue items, then get the description of each.

`search_catalog` matches names, workspace names and descriptions. Its results
carry no tags, labels or endorsement, and its index can lag by up to 24
hours, so the scan stays the audit of record.

**Audit with the Skill.** In a Copilot CLI session:

```text
/onelake-catalog-cli
```

Ask it to audit endorsement and sensitivity labels in `dev-fin-revenue`. Its
admin-audit mode calls `/v1/admin/*` and needs a Fabric administrator; as an
item owner, use its dataowner-audit mode. It only reads. Make any fix it
suggests through a manifest and the routes above.

Deployment doesn't copy endorsement, so each stage needs its own
certification: [challenge 08](../08-deployment-pipelines/challenge.md), Task
9, covers it.

### Task 7 — Scaffold medallions from a workflow

Add `.github/workflows/medallion-scaffold.yml`. It runs the Skill unattended
and pushes a branch for review:

```yaml
name: Medallion scaffold

on:
  workflow_dispatch:
    inputs:
      name:
        description: "Medallion name, such as sales-orders"
        required: true
      workspace:
        description: "Existing sbx or dev workspace for the items"
        required: true
      description:
        description: "What the medallion is for, 30 to 256 characters"
        required: true

permissions:
  contents: write

jobs:
  scaffold:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    env:
      NAME: ${{ inputs.name }}
      WORKSPACE: ${{ inputs.workspace }}
      DESCRIPTION: ${{ inputs.description }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

      - name: Check inputs
        run: |
          [[ "$NAME" =~ ^[a-z0-9-]{3,40}$ ]] || { echo "Invalid medallion name"; exit 1; }
          [[ "$WORKSPACE" =~ ^[a-z0-9-]{3,60}$ ]] || { echo "Invalid workspace name"; exit 1; }
          test -f "workspaces/$WORKSPACE.yaml" || { echo "No manifest for $WORKSPACE"; exit 1; }
          grep -Eq '^environment: (sbx|dev)$' "workspaces/$WORKSPACE.yaml" || { echo "Use an sbx or dev workspace"; exit 1; }
          test ! -e "medallion/$NAME.yaml" || { echo "medallion/$NAME.yaml exists"; exit 1; }

      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
        with:
          node-version: "22"

      - name: Install Copilot CLI and the Skills
        env:
          COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_PAT }}
        run: |
          npm install -g @github/copilot
          copilot plugin marketplace add microsoft/skills-for-fabric
          copilot plugin install fabric-skills@fabric-collection

      - name: Scaffold
        env:
          COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_PAT }}
        run: |
          PROMPT="Use the e2e-medallion-architecture skill to write files only. Follow medallion/finance-revenue.yaml, schemas/medallion.schema.json, schemas/item.schema.json and rules/items.yaml. Write medallion/$NAME.yaml with the description \"$DESCRIPTION\" and one stage: the environment in workspaces/$WORKSPACE.yaml, mapped to $WORKSPACE. Write the item manifests and notebook sources it names under items/$WORKSPACE/, with three schema-enabled lakehouses, one per layer. Don't create anything in Fabric."
          copilot -p "$PROMPT" -s --no-ask-user --allow-tool='write' --deny-tool='shell'

      - name: Keep changes inside items and medallion
        run: |
          git add -A
          if git diff --cached --name-only | grep -vE '^(items|medallion)/'; then
            echo "Copilot changed files outside items/ and medallion/"
            exit 1
          fi
          if git diff --cached --quiet; then
            echo "Copilot wrote no files"
            exit 1
          fi

      - name: Push a branch
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898283+github-actions[bot]@users.noreply.github.com"
          git switch -c "medallion/$NAME"
          git commit -m "Scaffold medallion $NAME"
          git push origin "medallion/$NAME"
```

Store a fine-grained personal access token with the **Copilot Requests**
permission as the repository secret `COPILOT_PAT`; the CLI reads it from
`COPILOT_GITHUB_TOKEN`. The run is unattended, so it allows only the `write`
tool and denies `shell`. Don't use `--allow-all` here: the job holds a token
that can push to the repo. The check step fails the run if Copilot changed
anything outside `items/` and `medallion/`, or wrote nothing.

The workflow pushes a branch and stops. Open the pull request from
`medallion/<name>` yourself: events from `GITHUB_TOKEN` don't start other
workflows, so a pull request the workflow opened wouldn't be validated.

Run it from the Actions tab for a test medallion in a sandbox or dev
workspace you own. Open the pull request, read what validation reports, and
close it without merging.

## Success criteria

- [ ] `medallion/finance-revenue.yaml` passes validation, and a pull request
      that drops `endorsement: Certified` from a gold item, or labels it
      General, fails `gold-metadata-minimum`.
- [ ] Bronze, silver and gold hold data, gold refreshes on its 04:00 UTC
      schedule, and `jobs_list-item-schedules` shows who owns each schedule.
- [ ] `sm_gold_revenue` was created from the files in the repo and reads
      gold in Direct Lake mode.
- [ ] Both gold items are Certified and labeled Confidential, and the drift
      report flags an endorsement mismatch until you certify again.
- [ ] A branch from `medallion-scaffold.yml` changes only files under
      `items/` and `medallion/`.

## Stretch goals

- **Tag the medallion.** Add a tenant tag named after the medallion to every
  item it lists, and make the validator require it.
- **Test the notebooks.** Run the silver logic against the sample rows with
  PySpark in a pull request check.
- **Template it.** Turn `finance-revenue` into a template that the scaffold
  workflow fills in, so every medallion starts from the same files.
- **Silver as a view.** Rewrite `nb_silver_clean_revenue` as a materialized
  lake view in `lh_silver_revenue`, and compare the lineage.
- **Schedules as code.** Create the gold schedule from the provisioner so the
  SPN owns it, have `drift.py` compare List Item Schedules with the
  medallion's `schedule`, and check the `.schedules` part that challenge 08's
  Git integration writes.
- **Create the model in one call.** Create `sm_gold_revenue` with
  `POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/semanticModels`,
  which takes the definition in its request, and compare it with Create Item.

> **Preview** (checked 2026-11-27): Event-triggered materialized lake view refresh — [Learn](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/schedule-lineage-run). GA route: a time-based schedule.

- **Refresh on change.** Refresh gold when silver changes instead of at a
  fixed time.
- **Schedule across lakehouses.** Once silver is a view, schedule silver and
  gold together from gold's lineage, which shows one level of parents in
  other lakehouses. Scheduling an upstream view needs Contributor on its
  lakehouse.
- **Add a report.** Add `rpt_gold_revenue` over `sm_gold_revenue` as a
  manifest and definition. Challenge 08 creates it if you don't.

## MCP tips

- The local server's `docs_item-definitions` shows each item type's
  definition parts, and `docs_best-practices` covers long-running operations
  and throttling. Neither has a medallion topic.
- The `jobs_` tools run as you, aren't idempotent, and don't retry or poll.
  List runs or schedules before you submit again, and give a new schedule a
  future start: an enabled schedule with a past start runs at once.
- `onelake_list-tables` and `onelake_get-table` show what the views wrote
  without opening a notebook.
- `get_item_definition` returns each part in Base64. Ask Copilot to decode it
  before comparing it with the repo.
- The Core MCP's `update_item_definition` replaces the whole definition. Send
  every part, and commit the same change.
- No MCP tool sets endorsement, labels or tags, or runs the scanner. The
  scripts call REST for tags and the scanner, and people apply endorsement
  and labels.

## Skills tips

- Ask `e2e-medallion-architecture` only for the layers you need, and state
  the layout: three schema-enabled lakehouses in one workspace. Decline its
  offers to create items or run notebooks.
- `spark-cli` writes view definitions in its authoring mode; its `mlv` mode
  helps you schedule, refresh, monitor and diagnose them.
- Use `semantic-model-authoring` for files only, let the provisioner create
  the model, and delete the report scaffold.
- `onelake-catalog-cli` audits endorsement and labels without changing them.
  Its admin-audit mode needs a Fabric administrator.
- If the Skills aren't installed, run these from a terminal:

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

## Repository files

This challenge extends these files in the repo root:

- `schemas/item.schema.json` and `rules/items.yaml`
- `scripts/validate_items.py`, `scripts/provision_items.py` and
  `scripts/_fabric.py`
- `scripts/drift.py`
- `.github/workflows/validate.yml`

It adds:

- `medallion/finance-revenue.yaml` and `schemas/medallion.schema.json`
- `workspaces/stg-fin-revenue.yaml`
- In `items/dev-fin-revenue/`: `lh_gold_revenue.yaml`,
  `nb_bronze_ingest_revenue.yaml` and `.py`, `nb_gold_mlv_revenue.yaml` and
  `.py`, `sm_gold_revenue.yaml` and `sm_gold_revenue.SemanticModel/`
- `.github/workflows/medallion-scaffold.yml`

## References

- [Materialized lake views overview](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/overview-materialized-lake-view)
- [Get started with materialized lake views](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/get-started-with-materialized-lake-views)
- [Refresh materialized lake views](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/refresh-materialized-lake-view)
- [Schedule a lineage run](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/schedule-lineage-run)
- [Materialized lake view lineage](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/view-lineage)
- [Job scheduler](https://learn.microsoft.com/fabric/fundamentals/job-scheduler)
- [Notebook public API](https://learn.microsoft.com/fabric/data-engineering/notebook-public-api)
- [Run On Demand Item Job REST API](https://learn.microsoft.com/rest/api/fabric/core/job-scheduler/run-on-demand-item-job)
- [Create Item Schedule REST API](https://learn.microsoft.com/rest/api/fabric/core/job-scheduler/create-item-schedule)
- [Semantic model definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/semantic-model-definition)
- [Direct Lake overview](https://learn.microsoft.com/fabric/fundamentals/direct-lake-overview)
- [Endorsement overview](https://learn.microsoft.com/fabric/governance/endorsement-overview)
- [Promote or certify items](https://learn.microsoft.com/fabric/fundamentals/endorsement-promote-certify)
- [Metadata scanning](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview)
- [Explore the OneLake catalog](https://learn.microsoft.com/fabric/governance/onelake-catalog-explore)
- [The deployment process](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/understand-the-deployment-process)
- [Lakehouse Git integration and deployment pipelines](https://learn.microsoft.com/fabric/data-engineering/lakehouse-git-deployment-pipelines)
- [Medallion lakehouse architecture](https://learn.microsoft.com/fabric/onelake/onelake-medallion-lakehouse-architecture)
- [Lakehouse schemas](https://learn.microsoft.com/fabric/data-engineering/lakehouse-schemas)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [MCP servers and Skills](../../docs/mcp-and-skills.md)
- [`e2e-medallion-architecture` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/e2e-medallion-architecture)
- [`spark-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/spark-cli)
- [`semantic-model-authoring` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/semantic-model-authoring)
- [`onelake-catalog-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/onelake-catalog-cli)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
