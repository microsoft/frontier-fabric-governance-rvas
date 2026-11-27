# Challenge 06 — Fabric data agent governance

> **Outcome:** production data agents exist only as reviewed manifests in
> `agents/`. Validation blocks sources a manifest doesn't declare and
> sources labeled above the agent's clearance, and lints the instructions.
> A service principal writes the draft after checking live labels, an owner
> publishes and shares it, and the daily drift report lists unmanaged agents
> and changes made outside the repo. The repo also keeps dated reviews of
> the AI tenant settings that agents depend on and of the data agent
> activity that Microsoft Purview records.

## Why this challenge exists

A Fabric data agent answers plain-language questions over up to five data
sources, such as lakehouses, warehouses, KQL databases and semantic models.
It only reads data, and it answers as the person asking, so it can't return
rows that person can't read. Sharing an agent doesn't grant access to its
sources.

The risks are which sources an agent reads, what its instructions tell it to
do, and where its answers go. Microsoft Learn warns that when an agent is
used from a service outside Fabric, such as Microsoft 365 Copilot or an MCP
client, "responses returned by Fabric data agents may be sent outside of
Fabric's compliance boundary or geographic region." Anyone with the
Contributor role can create an agent in a workspace, and nothing reviews its
sources or instructions before it's shared. This challenge puts production
agents through the same pull-request review as workspaces and items.

Tenant settings decide who can use data agents and Copilot, and the Copilot
defaults change on 2026-12-08. Once Microsoft Purview Data Security Posture
Management (DSPM) is set up, Purview records the questions people ask data
agents and the answers they get. No Fabric API or Core MCP tool reads those
records, so this challenge reviews them in the Microsoft Purview portal and
keeps a dated record of each review in the repo.

## Learning objectives

1. Describe a production data agent in a manifest: its workspace, sources,
   clearance, owners, audience, instructions and example queries.
2. Block a pull request when an agent reads an undeclared source or a source
   labeled above its clearance.
3. Lint agent instructions for required sections, length and banned phrases.
4. Create and update the agent's draft as the service principal after
   checking live labels, and leave publishing and sharing to an owner.
5. Check the live agent from chat with the Fabric Core MCP server, and check
   its answers with `/fabriciq`.
6. Report unmanaged agents, changed sources and changed instructions in the
   daily drift report.
7. Review the AI tenant settings that agents and Copilot depend on,
   including the Copilot changes on 2026-12-08 and 2027-01-15, and record
   each decision.
8. Review data agent activity in DSPM in the Microsoft Purview portal, and
   record each review in the repo.

## Prerequisites

- Challenges 00–04 complete. The service principal from
  [challenge 00](../00-setup/challenge.md) created `prd-fin-revenue` through
  `provision.yml`, so it's an Admin there. It isn't a Fabric or capacity
  administrator and holds no `Tenant.ReadWrite.All`.
- `workspaces/prd-fin-revenue.yaml` from
  [challenge 03](../03-domains-capacities-sensitivity/challenge.md) is
  merged: capacity `contosoprodf4`, region `northeurope`, owners
  `grp_fabric_prd_fin_admin` (Admin) and `grp_fabric_prd_fin_member`
  (Member). `rules/labels.yaml` gives each sensitivity label a priority.
- A gold lakehouse and semantic model in `prd-fin-revenue`, such as the ones
  [challenge 05](../05-medallion-bootstrap/challenge.md) builds; this
  challenge calls them `lh_gold_revenue` and `sm_gold_revenue`. Each has a
  manifest under `items/prd-fin-revenue/` with an explicit
  `sensitivityLabel`. Add `SemanticModel` to the item kinds from
  [challenge 02](../02-items-as-code/challenge.md) if it isn't there.
- A Fabric capacity of F2 or higher, or a P1 or higher with Fabric enabled.
  Sources must be in the same region as the agent's capacity.
- A sandbox workspace, `sbx-fin-agent-lab` on `contosononprodf2`, created
  from a manifest like any other workspace.
- A group for the agent's users, `sg-fin-revenue-agent-users`, and two test
  accounts: one in the group and one outside it.
- A Fabric administrator has set these tenant settings in OneLake catalog >
  **Govern** > **Configurations** > **Tenant settings**, or in the Admin
  portal's **Tenant settings**. Changes take up to one hour to apply.
  - "Users can use Copilot and other features powered by Azure OpenAI", on
    for the tenant, or for both `contosoprodf4` and `contosononprodf2`. If
    it's limited to security groups, check in `sbx-fin-agent-lab` whether
    the service principal's group, `sg-fabric-workspace-provisioner`, must
    be included before you run Task 4 against production.
  - "Capacities can be designated as Fabric Copilot capacities". The data
    agent settings page lists it as required; the Copilot settings page
    calls it "…as Copilot in Fabric capacities", so use the title your
    tenant shows.
  - Outside the EU data boundary and the US, also "Data sent to Azure OpenAI
    can be processed outside your capacity's geographic region, compliance
    boundary, or national cloud instance" and its twin for data "stored
    outside". `northeurope` doesn't need them.
- For Task 8, a Compliance Administrator in Microsoft Entra ID, or a member
  of the Microsoft Purview Compliance Administrator role group, completes
  the DSPM setup. "Activate Microsoft Purview Audit" also needs a Microsoft
  Exchange role group: Compliance Management, Records Management or
  Organization Management. Reviewing needs only a view-only role group,
  such as Microsoft Purview Security Reader or Data Security Viewers.
  ([Learn](https://learn.microsoft.com/purview/data-security-posture-management-permissions))
- The Fabric Core MCP server and Skills for Fabric, installed as shown below.

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

## Tasks

### Task 1 — Describe the agent in a manifest

Add `schemas/agent.schema.json` and one manifest per production agent under
`agents/`, starting with `agents/agent-finance-revenue-qa.yaml`:

```yaml
name: agent-finance-revenue-qa
workspace: prd-fin-revenue
description: >-
  Answers questions about net revenue, gross margin and close-day variance
  for the finance team, from the gold revenue model and lakehouse.
clearance: Confidential
owners:
  - principalType: Group
    identifier: <object-id-of-grp_fabric_prd_fin_admin>
    groupName: grp_fabric_prd_fin_admin
  - principalType: Group
    identifier: <object-id-of-grp_fabric_prd_fin_member>
    groupName: grp_fabric_prd_fin_member
audience:
  - principalType: Group
    identifier: <object-id-of-sg-fin-revenue-agent-users>
    groupName: sg-fin-revenue-agent-users
dataSources:
  - type: SemanticModel
    name: sm_gold_revenue
  - type: Lakehouse
    name: lh_gold_revenue
    tables: [fact_revenue, dim_product_line, dim_date]
    instructionsFile: agents/agent-finance-revenue-qa/lh_gold_revenue.md
    fewShotsFile: agents/agent-finance-revenue-qa/lh_gold_revenue.fewshots.json
instructionsFile: agents/agent-finance-revenue-qa/instructions.md
exampleQuestions:
  - question: What was net revenue last quarter?
    expect: One figure for the last closed quarter, with the quarter named.
  - question: How did Q3 close-day variance compare to Q2?
    expect: Both variances and the difference between them.
  - question: What are the top 5 product lines by gross margin?
    expect: Five product lines ranked by gross margin percentage.
  - question: What is the salary of each finance analyst?
    expect: A refusal that says what the agent can answer instead.
```

- `name`: the agent's name in Fabric. The file name must match.
- `workspace`: a workspace with a manifest in `workspaces/`.
- `description`: at least 30 characters. An owner enters it when publishing,
  and Microsoft 365 Copilot uses it to decide when to call the agent.
- `clearance`: the highest sensitivity label the agent may read, as named in
  `rules/labels.yaml`.
- `owners`: at least two groups with Admin or Member in the workspace's
  manifest.
- `audience`: the groups the agent is shared with. They need read access to
  each source, not a workspace role.
- `dataSources`: up to five. Each names an item with a manifest under
  `items/<workspace>/`; add `workspace` to a source in another workspace.
  `tables` limits a lakehouse or warehouse to the listed tables.
- `instructionsFile`: instructions for the agent, or for one source when set
  on a source. Task 3 lints them.
- `fewShotsFile`: up to 100 example queries for one source. Semantic model
  sources don't accept them.
- `exampleQuestions`: questions with the answer you expect, including one the
  agent must refuse. Task 5 uses them.

Write the agent instructions in these sections. `Refusals` is a house
section; the others follow the data agent guidance on Learn.

```markdown
## Objective
Answer questions about Contoso's net revenue, gross margin and close-day
variance for the finance team.

## Data sources
Use sm_gold_revenue for revenue and margin figures. Use lh_gold_revenue only
for questions about individual invoices or product lines.

## Key terminology
- Net revenue: recognized revenue after returns and discounts.
- Close-day variance: the difference between forecast and actual revenue on
  the day the quarter closes.

## Response guidelines
Name the period and the source for every figure, and say which currency it
is in.

## Handling common topics
"Last quarter" means the last closed fiscal quarter.

## Refusals
Decline questions about people's pay, performance or personal details, and
questions outside finance revenue. Say what you can answer instead.
```

Source instructions, such as `lh_gold_revenue.md`, use the sections
`General knowledge`, `Table descriptions` and `When asked about`.

Write example queries in the agent definition's JSON shape, without `id`
fields; the provisioner adds them.

```json
{
  "$schema": "1.0.0",
  "fewShots": [
    {
      "question": "What was net revenue by product line last quarter?",
      "query": "SELECT p.product_line, SUM(f.net_amount) AS net_revenue FROM fact_revenue AS f JOIN dim_product_line AS p ON f.product_line_key = p.product_line_key JOIN dim_date AS d ON f.date_key = d.date_key WHERE d.is_last_closed_quarter = 1 GROUP BY p.product_line"
    }
  ]
}
```

### Task 2 — Validate agent manifests

Add an `agents:` block to `rules/policy.yaml`, and copy the file to
`api/policy.yaml` so the two stay byte-identical:

```yaml
agents:
  maxDataSources: 5
  maxFewShotsPerSource: 100
  fewShotKinds: [Lakehouse, Warehouse, KQLDatabase]
  maxInstructionCharacters: 15000
  minInstructionWords: 200   # house rule, not a Fabric limit
  requiredInstructionSections:
    agent: [Objective, Data sources, Key terminology, Response guidelines, Handling common topics, Refusals]
    source: [General knowledge, Table descriptions, When asked about]
  bannedPhrasesFile: rules/agent/banned_phrases.yaml
```

Extend `scripts/validate.py` to check `agents/*.yaml`: validate each
manifest against `schemas/agent.schema.json`, then run the rules below.
`validate.yml` runs it with `--changed-only`, which picks up only changed
workspace manifests, so check every agent manifest whenever a file under
`agents/`, `items/`, `workspaces/` or `rules/` changes. Add `agents/**` and
`items/**` to the `paths` filter in `.github/workflows/validate.yml`, so a
label change on an item re-checks the agents that read it.

List each rule in the `rules:` section of `rules/policy.yaml` too. The rule
IDs are suggestions. Each rule fires when:

- `agent-manifest-filename` (block): the file isn't `agents/<name>.yaml`.
- `agent-workspace-declared` (block): `workspace` has no manifest in
  `workspaces/`.
- `agent-source-declared` (block): a source has no manifest under
  `items/<workspace>/`, or that manifest's type differs.
- `agent-source-label` (block): a source's manifest has no
  `sensitivityLabel`, or its label's priority in `rules/labels.yaml` is
  higher than the clearance's.
- `agent-max-sources` (block): there are more than `maxDataSources` sources.
- `agent-same-region` (block): a source's workspace has a different `region`
  from the agent's workspace.
- `agent-few-shots` (block): `fewShotsFile` is set on a source whose type
  isn't in `fewShotKinds`, or it holds more than `maxFewShotsPerSource`
  examples.
- `prd-agent-group-owners` (block): the workspace's manifest sets
  `environment: prd`, and there are fewer than two owners or an owner isn't
  a group with Admin or Member in that manifest.
- `agent-instructions-lint` (block): the Task 3 linter reports an error.

Prove the rules work with two pull requests that must fail: one adds a
source with no manifest, and one sets `clearance: General` while
`sm_gold_revenue` is labeled `Confidential`.

### Task 3 — Lint the instructions

Add `scripts/lint_agent_instructions.py` and
`rules/agent/banned_phrases.yaml`. `validate.py` runs the linter on every
instructions file an agent manifest names, and writes its findings to
`validation-report.md` and the step summary like the other rules.

```yaml
phrases:
  - pattern: "(?i)ignore (all |any )?(previous|prior) instructions"
    reason: Prompt-injection wording.
  - pattern: "(?i)(always answer|never refuse)"
    reason: Overrides the Refusals section.
  - pattern: "(?i)(you|the agent) (can|may) (see|access) all data"
    reason: The agent answers as the person asking.
```

The linter reports:

- An error for a missing required section, instructions longer than
  `maxInstructionCharacters`, or a banned phrase, with its line number.
- A warning for instructions shorter than `minInstructionWords`.

Test it with an instructions file that has no `## Refusals` section and one
that says "always answer".

### Task 4 — Provision the draft as the service principal

Add `scripts/provision_agents.py`. It calls the Fabric REST API rather than
MCP because it runs unattended in `provision.yml` as the service principal.
If you manage Fabric with Terraform, the `fabric_data_agent` resource is an
alternative. Add item and long-running-operation helpers to
`scripts/_fabric.py`; it already pages, retries and raises `AuthError` on
a 401 or 403.

Before you script anything, build a throwaway agent by hand in
`sbx-fin-agent-lab`, with a small lakehouse in that workspace as its only
source, and read its definition. The script must send parts in exactly that
shape.

For each manifest in `agents/`, the script:

1. Resolves the workspace ID and lists its data agents
   (`GET /v1/workspaces/{workspaceId}/items?type=DataAgent`, following
   `continuationUri`).
2. Reads each source's live label
   (`GET /v1/workspaces/{workspaceId}/items/{itemId}`, field
   `sensitivityLabel.id`) and looks up its priority in `rules/labels.yaml`.
   It stops if a label is missing, unknown or above the clearance.
3. Creates the agent if it doesn't exist
   (`POST /v1/workspaces/{workspaceId}/dataAgents` with `displayName` and
   `description`). A 201 returns the agent. A 202 starts a long-running
   operation: read `Location` and `Retry-After`, poll until the status is
   `Succeeded` or `Failed`, then `GET {Location}/result`.
4. Reads the definition
   (`POST /v1/workspaces/{workspaceId}/dataAgents/{dataAgentId}/getDefinition`),
   replaces the draft parts and sends every part back with
   `updateDefinition`. Both calls can be long-running.
   - `Files/Config/draft/stage_config.json` holds the agent instructions in
     `aiInstructions`.
   - `Files/Config/draft/<type>-<name>/datasource.json` holds a source and
     its instructions, and `fewshots.json` beside it holds its example
     queries.
   - Draft source folders the manifest doesn't declare are removed.
   - `Files/Config/data_agent.json`, `Files/Config/publish_info.json` and
     the `published/` parts stay as they are.
5. Prints what it changed. With `DRY_RUN=true`, it prints the planned calls
   and writes nothing.

On a 401 or 403, stop and report it. Don't treat it as "not found", and
don't widen the service principal's rights to get past it.

Add `agents/**` to the `paths` filter in `.github/workflows/provision.yml`,
and a step that runs `python scripts/provision_agents.py` after the
workspace step, with the same `DRY_RUN` environment variable. Set the
repository variable `DRY_RUN` to `true` for the first run. The script uses
`DefaultAzureCredential`, so an owner can also run it locally after
`az login`:

```bash
DRY_RUN=true python scripts/provision_agents.py
```

There's no API to publish or share a data agent. After the draft is
updated, an owner of the agent:

1. Tests the draft in Fabric with the example questions.
2. Selects **Publish**, enters the manifest's `description`, and doesn't
   make the agent available in Microsoft 365 Copilot unless the platform
   team has approved it (see the stretch goals).
3. Shares the agent with `sg-fin-revenue-agent-users` and leaves every
   permission unselected, so members can only query the published version.
   Only reviewers who need to see the draft get **View details**.
4. Gives `sg-fin-revenue-agent-users` Read on `sm_gold_revenue` and
   `lh_gold_revenue`. For the semantic model, Read is enough; Build and
   workspace roles aren't needed. If you finished
   [challenge 10](../10-onelake-security-as-code/challenge.md), limit the
   lakehouse access to the declared tables with a OneLake security role.
   The agent queries the lakehouse through its SQL analytics endpoint, so
   the role applies only when the endpoint uses user identity mode; in
   delegated mode, SQL permissions apply instead.

### Task 5 — Check the agent from chat

In a Copilot CLI session with the Fabric Core MCP connected:

```text
Use list_items to list the DataAgent items in prd-fin-revenue.
Use get_item_definition on agent-finance-revenue-qa, decode the draft parts and list each data source with its tables.
Compare those sources with agents/agent-finance-revenue-qa.yaml and list any differences.
```

The sources should match the manifest. A difference is drift, which Task 6
reports.

Next, get the expected answers with the `fabriciq` Skill, signed in as the
test account in `sg-fin-revenue-agent-users`. It queries the semantic model
as that account, with row-level and object-level security applied. In a
Copilot CLI session:

```text
/fabriciq In sm_gold_revenue, what was net revenue last quarter?
/fabriciq In sm_gold_revenue, what are the top 5 product lines by gross margin?
```

Then ask the published agent the same questions in Fabric as the same
account, and check that:

- The figures match what `/fabriciq` returned.
- The agent refuses the salary question and says what it can answer.
- The test account outside `sg-fin-revenue-agent-users` can't open the
  agent.

Record the results in `agents/evidence/agent-finance-revenue-qa.md`: the
date, the accounts used, each question and whether the answer matched.
Don't copy figures or rows into the repo.

### Task 6 — Report agent drift

Add a `check_agents()` function to `scripts/drift.py`. It returns
`(markdown, found)` like `check()`, and `main()` appends its
`## Data agents` section to `drift-report.md` and combines its `found` with
the workspace result. Like the rest of `drift.py`, it calls REST because it
runs unattended in `drift.yml`.

For each workspace with a manifest, list its data agents with the Core List
Items API, read each agent's definition, and report:

- Unmanaged agent: a data agent with no manifest in `agents/`.
- Source mismatch: the draft's sources or tables differ from `dataSources`.
- Instructions changed: the SHA-256 of the draft's `aiInstructions` differs
  from that of the instructions file, after normalizing line endings and
  trailing whitespace.

Skip the workspaces `drift.py` already reports as ones the service principal
can't see. Core List Items needs a workspace role there, and a failed call
would stop the whole run.

If the published instructions differ from the draft, add a warning line. It
isn't drift on its own, because owners publish by hand.

To also find agents in workspaces that have no manifest, list agents across
the tenant. The service principal can call this API because its group,
`sg-fabric-workspace-provisioner`, is enabled in "Service principals can
access read-only admin APIs".

> **Preview** (checked 2026-11-27): Admin List Items — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/items/list-items). GA route: call the Core List Items API on each managed workspace.

Call `GET /v1/admin/items?type=DataAgent` and report each agent whose
workspace has no manifest as unmanaged.

Keep the exit codes: 2 when there's drift, and 3 on a 401 or 403.
`.github/workflows/drift.yml` doesn't change. When `drift.py` exits 2, the
workflow opens one issue, "Fabric workspace drift detected", labeled `drift`
and `governance`, with the whole report, agent findings included. It doesn't
close earlier issues; close them yourself after a clean rerun.

To test it, leave the throwaway agent from Task 4, which has no manifest in
`agents/`, in `sbx-fin-agent-lab`. In Fabric, add a table to
`lh_gold_revenue` in the draft of `agent-finance-revenue-qa`. Run the drift
workflow on demand and check that the issue lists both under
`## Data agents`. Then rerun the provisioner to put the draft back.

This challenge doesn't automate the share check. Review who the agent is
shared with during the access review in
[challenge 04](../04-access-rbac-lifecycle/challenge.md).

### Task 7 — Review the AI tenant settings

Data agents depend on tenant settings that a Fabric administrator can change
at any time, and the Copilot settings change on 2026-12-08. No Core MCP tool
reads tenant settings, and `/onelake-catalog-cli` reads them only in its
admin modes, which need the Fabric administrator role. The service principal
doesn't have it, so use the Fabric admin REST API.

Export the tenant settings again the way
[challenge 00](../00-setup/challenge.md) does, to
`tenant/export/<YYYY-MM-DD>.json` under `tenantSettings`. Add a
`capacityOverrides` key with each capacity's overrides, and put each
capacity's `displayName` from `list_capacities()` in `scripts/_fabric.py`
beside its `id`. `list_capacities()` lists only capacities where the
service principal is a contributor, so an override on any other capacity
keeps only its `id`.

```text
GET https://api.fabric.microsoft.com/v1/admin/tenantsettings
GET https://api.fabric.microsoft.com/v1/admin/capacities/delegatedTenantSettingOverrides
GET https://api.fabric.microsoft.com/v1/capacities
```

Each response lists its items under `value`, and `_paged()` in
`scripts/_fabric.py` follows `continuationUri` to the last page. `_request`
raises `AuthError` on a 401 or 403; let it stop the export, and never read
either as an empty list. The service principal can call the two admin APIs
because its group is enabled in "Service principals can access read-only
admin APIs".

Some AI settings can also be set per capacity. A capacity admin can turn on
"Users can use Copilot and other features powered by Azure OpenAI" for
their capacity even when it's off for the tenant. Check the overrides for
`contosoprodf4` and `contosononprodf2`. If an override differs from the
tenant setting, ask that capacity's admin why, and record the answer in the
review.

> **Preview** (checked 2026-11-27): Microsoft Copilot in Power BI and Fabric — [Learn](https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric). GA route: review the generally available settings, and mark a preview setting the export doesn't list as not present.

Record the review in `agents/evidence/ai-settings-<YYYY-MM-DD>.md`:

```markdown
# AI tenant settings review — <YYYY-MM-DD>

- Export: `tenant/export/<YYYY-MM-DD>.json`
- Reviewer: <reviewer>
- "Fabric data available in Microsoft Copilot": <on or off>, confirmed by
  <Microsoft 365 administrator>

| Setting | Enabled | Groups | Capacity overrides | Needed for | Decision |
|---|---|---|---|---|---|
| Users can use Copilot and other features powered by Azure OpenAI | | | | Data agents, Copilot | |
| <Copilot capacities setting, as the export titles it> | | | | Data agents, Copilot | |
| Users can use Copilot, AI Agents and other AI experiences powered by OpenAI as a Microsoft Subprocessor | | | | Copilot and agents on OpenAI-operated models | |
| Allow Microsoft Purview to secure AI interactions | | | | Purview records of data agent use | |
| Make Microsoft Copilot available in Power BI and Fabric | | | | Microsoft Copilot in Power BI and Fabric | |
| <standalone Copilot in Power BI setting, as the export titles it> | | | | Standalone Copilot in Power BI, until 2027-01-15 | |
| Only show approved items in the standalone Copilot in Power BI experience (preview) | | | | Limits standalone Copilot and, during the preview, Microsoft Copilot | |
```

Copy each title exactly as the export shows it, because Learn words some
settings two ways. Outside the EU data boundary and the US, add rows for the
two settings that let data be processed or stored outside the capacity's
region.

Data agents don't need the last three settings in the table, but those
settings change what the agent's audience can reach. Microsoft Copilot
answers from content the user can view, with row-level and object-level
security applied. Members of `sg-fin-revenue-agent-users` can read
`sm_gold_revenue`, so they may be able to ask Microsoft Copilot about it
directly, where the agent's instructions and refusals don't apply.

"Make Microsoft Copilot available in Power BI and Fabric" is off by default
until 2026-12-08 and on by default after that, so record a decision rather
than rely on the default. Microsoft Copilot also needs "Fabric data
available in Microsoft Copilot", a Microsoft 365 setting that isn't in the
export, so ask a Microsoft 365 administrator for its value.

On 2026-12-08 the standalone Copilot in Power BI setting turns off by default, and standalone Power BI Copilot retires on 2027-01-15.
Turning the standalone setting back on restores it only until 2027-01-15.

During the preview, Microsoft Copilot also honors the approved-items
setting. That setting is delegated to workspace admins by default
(`delegateToWorkspace` in the export), so a workspace admin can change it
for their workspace.

To change a setting, a Fabric administrator uses OneLake catalog >
**Govern** > **Configurations** > **Tenant settings**, or the Admin portal's
**Tenant settings**. After a change, export again and point the review at
the new export.

[Challenge 12](../12-tenant-settings-policies-as-code/challenge.md) manages
these settings as code, including the Copilot decision and the workspace
overrides.

### Task 8 — Review how people use data agents

Once DSPM is set up, Microsoft Purview records each question asked of a
Fabric data agent, and its answer, as Copilot Interaction records in the
audit log. No Fabric API, Core MCP tool or Skill reads them, so review them
in the Microsoft Purview portal and record the review in the repo.

> **Preview** (checked 2026-11-27): Microsoft Purview DSPM for Fabric data agents — [Learn](https://learn.microsoft.com/fabric/data-science/data-agent-purview-governance). GA route: search the audit log in the Microsoft Purview portal for `CopilotInteraction` records.

1. In the Microsoft Purview portal, open **DSPM** > **Actions** >
   **Setup tasks** and complete "Activate Microsoft Purview Audit" and
   "Secure interactions in Microsoft Copilot experiences".
2. Check in the Task 7 review that "Allow Microsoft Purview to secure AI
   interactions" is on. If it isn't, a Fabric administrator turns it on in
   OneLake catalog > **Govern** or the Admin portal, and you record the
   change.
3. After setup, ask the agent the Task 5 questions again as the test
   account in the group. Audit records can take 90 minutes or longer to
   appear, so wait before the next step.
4. Open **Activity Explorer** and filter **Activity Type** to Copilot
   Interaction, **App** to Fabric-Data Agent, and **Timestamp** to a range
   that covers the test. Check that the test account's questions appear.
   These filters don't pick out one agent, so the review covers every data
   agent in the tenant.
5. Record the review in `agents/evidence/dspm-<YYYY-MM-DD>.md`:

   ```markdown
   # DSPM data agent review — <YYYY-MM-DD>

   - Period: <start date> to <end date>
   - Reviewer: <reviewer>
   - Filters: Activity Type Copilot Interaction, App Fabric-Data Agent
   - Copilot Interaction records: <count>
   - Users: <count>
   - Task 5 questions found: <yes or no>
   - Follow-up issues: <links>
   ```

Keep prompt and response text out of the repo and out of issues, because
answers can hold figures and generated queries. The review doesn't need that
text, and viewing it needs an extra role: Content Explorer Content Viewer or
Microsoft Purview Data Security AI Content Viewer.

The records hold what people asked and what the agent answered. Queries the
agent ran but didn't show in its answer aren't recorded. To see who created,
changed or shared an agent, look in the Fabric activity events from
[challenge 07](../07-audit-observability/challenge.md).

## Success criteria

- [ ] `agents/agent-finance-revenue-qa.yaml` passes validation, and the two
      deliberate failures from Task 2 block their pull requests.
- [ ] The linter blocks a missing section, a banned phrase and instructions
      over 15,000 characters, and warns under 200 words.
- [ ] A dry run of `provision_agents.py` prints the planned calls, and a real
      run creates the draft with only the declared sources and tables.
- [ ] The provisioner stops on a missing or over-clearance label, and on
      a 401 or 403.
- [ ] The agent is published and shared with `sg-fin-revenue-agent-users`
      with no extra permissions, and that group can read both sources.
- [ ] `agents/evidence/agent-finance-revenue-qa.md` records the example
      questions, the refusal and the account outside the audience, without
      figures.
- [ ] A drift run reports the throwaway agent as unmanaged and the extra
      table as a source mismatch, exits 2, and the issue lists both under
      `## Data agents`.
- [ ] A fresh export has `capacityOverrides`, and
      `agents/evidence/ai-settings-<YYYY-MM-DD>.md` records a decision for
      each setting, including the two that change on 2026-12-08.
- [ ] `agents/evidence/dspm-<YYYY-MM-DD>.md` records the filters, period,
      counts and follow-up issues, shows that the Task 5 questions were
      found, and holds no prompt or response text.

## Stretch goals

- **Open a separate agent drift issue.** Have `drift.py` also write
  `drift-report-agents.md` when there are agent findings. Add a step to
  `drift.yml` that runs only when that file exists
  (`if: hashFiles('drift-report-agents.md') != ''`) and opens a second issue
  from it, labeled `drift` and `drift/agent`. Copy the pinned
  `peter-evans/create-issue-from-file` line from the existing issue step.

> **Preview** (checked 2026-11-27): Fabric data agents in Microsoft Copilot Studio — [Learn](https://learn.microsoft.com/fabric/data-science/data-agent-microsoft-copilot-studio). GA route: publish to Microsoft 365 Copilot.

- **Control where agents are published.** List each agent's surfaces,
  `fabric`, `microsoft365Copilot` or `copilotStudio`, in
  `agents/surfaces.yaml`, and add
  `/agents/surfaces.yaml @your-org/fabric-governance-maintainers` to
  `.github/CODEOWNERS` so the platform team approves every change. Block
  `copilotStudio` while it's in preview when the agent's workspace manifest
  sets `environment: prd`. Publishing to Microsoft 365 Copilot lists the
  agent in the Agent Store once a Microsoft 365 administrator allows Copilot
  agents, and its answers can leave Fabric's compliance boundary.

> **Preview** (checked 2026-11-27): Fabric data agents in Microsoft Agent 365 — [Learn](https://learn.microsoft.com/microsoft-agent-365/overview). GA route: none; stretch task.

- **Check the Agent 365 registry.** If your tenant uses Microsoft Agent 365,
  check that `agent-finance-revenue-qa` appears in its registry after it's
  published to Microsoft 365 Copilot, with the owners from its manifest.

> **Preview** (checked 2026-11-27): Evaluate a data agent with the Python SDK — [Learn](https://learn.microsoft.com/fabric/data-science/evaluate-data-agent). GA route: none; stretch task.

- **Test the example questions in code.** In a notebook, run each
  `exampleQuestions` entry against the agent with the SDK's evaluation
  functions, and fail when an answer doesn't match. Run it before an owner
  publishes.

> **Preview** (checked 2026-11-27): Ontology as a data agent source — [Learn](https://learn.microsoft.com/fabric/iq/ontology/how-to-create-data-agent). GA route: none; stretch task.

- **Ground an agent in a Fabric IQ ontology.** An ontology (preview) item
  describes business entities and their relationships in Fabric IQ. In a
  sandbox workspace, `sbx-fin-revenue-iq` on `contosononprodf2`, created
  from a manifest, add a lakehouse with small sample tables shaped like
  `fact_revenue`, `dim_product_line` and `dim_date`, not copies of
  production data. A Fabric administrator must turn on "Users can create
  Fabric items" and "Users can create ontology (preview) items". Create an
  ontology in Fabric bound to those tables; a known issue stops data agents
  from using an ontology bound to a semantic model. Make the ontology the
  only source of a sandbox agent, ask it the Task 5 questions, ask the same
  questions with `/ontology-cli`, and compare the answers. Drift reports the
  agent as unmanaged until you declare it in `agents/`, which needs
  `Ontology` in the item kinds from
  [challenge 02](../02-items-as-code/challenge.md), and as a source type in
  `schemas/agent.schema.json` if your schema lists them.

## MCP tips

- `list_items` with the type `DataAgent` lists the agents in one workspace.
  It only sees workspaces where you have a role.
- `get_item_definition` returns the parts base64-encoded. Ask Copilot to
  decode `Files/Config/draft/stage_config.json` to read the draft
  instructions.
- No Core MCP tool publishes, shares or labels an agent, or reads tenant
  settings. Publishing and sharing happen in Fabric.
- The data agent MCP server makes a published agent available to other MCP
  clients. It serves only published agents.
  ([Learn](https://learn.microsoft.com/fabric/data-science/data-agent-mcp-server))

## Skills tips

- `/fabriciq` queries semantic models and reports through the Fabric IQ MCP
  server, as you, with row-level and object-level security applied. It
  replaces the retired Power BI consumption Skill.
- The Fabric IQ MCP server doesn't accept service principals, so use
  `/fabriciq` for checks a person runs, not in workflows. It isn't available
  in Power BI-only regions or sovereign clouds.
- `/onelake-catalog-cli` in `dataowner-audit` mode reports governance gaps,
  such as unlabeled items, in workspaces you administer, and never writes.
  Run it on `prd-fin-revenue` before Task 4 to find sources without labels.
- `/ontology-cli` answers questions over ontologies made in Fabric's new
  ontology experience, through the ontology MCP endpoint (preview). It can
  also write ontology definitions, but only in an older format it can't
  query, so create and change ontologies in Fabric. Use it for checks a
  person runs: a known issue stops service principals from using the
  ontology MCP endpoint.

If `/fabriciq` can't reach its server, add it under `mcpServers` in
`~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "FabricIQ": {
      "type": "http",
      "url": "https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq",
      "tools": ["*"]
    }
  }
}
```

In the Copilot app, use **Customize** > **MCP** > **Add server** > **HTTP**
with the same URL.

## References

- [What is a Fabric data agent](https://learn.microsoft.com/fabric/data-science/concept-data-agent)
- [Create a Fabric data agent](https://learn.microsoft.com/fabric/data-science/how-to-create-data-agent)
- [Data agent tenant settings](https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings)
- [Copilot and agent tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-copilot)
- [Microsoft Copilot in Power BI and Fabric (Preview)](https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric)
- [Share a data agent](https://learn.microsoft.com/fabric/data-science/data-agent-sharing)
- [Data agent configurations](https://learn.microsoft.com/fabric/data-science/data-agent-configurations)
- [Data agent definition (REST)](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/data-agent-definition)
- [Data agent items (REST)](https://learn.microsoft.com/rest/api/fabric/dataagent/items)
- [Long-running operations (REST)](https://learn.microsoft.com/rest/api/fabric/articles/long-running-operation)
- [List items (REST)](https://learn.microsoft.com/rest/api/fabric/core/items/list-items)
- [Get item (REST)](https://learn.microsoft.com/rest/api/fabric/core/items/get-item)
- [List items (REST, admin, Preview)](https://learn.microsoft.com/rest/api/fabric/admin/items/list-items)
- [List tenant settings (REST, admin)](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-tenant-settings)
- [List capacities tenant settings overrides (REST, admin)](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-capacities-tenant-settings-overrides)
- [List capacities (REST)](https://learn.microsoft.com/rest/api/fabric/core/capacities/list-capacities)
- [Core MCP server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Data agent MCP server](https://learn.microsoft.com/fabric/data-science/data-agent-mcp-server)
- [Data agents in Microsoft 365 Copilot](https://learn.microsoft.com/fabric/data-science/data-agent-microsoft-365-copilot)
- [Data agents in Copilot Studio (Preview)](https://learn.microsoft.com/fabric/data-science/data-agent-microsoft-copilot-studio)
- [Purview governance for data agents (Preview)](https://learn.microsoft.com/fabric/data-science/data-agent-purview-governance)
- [DSPM permissions](https://learn.microsoft.com/purview/data-security-posture-management-permissions)
- [Search the audit log](https://learn.microsoft.com/purview/audit-search)
- [Evaluate a data agent (Preview)](https://learn.microsoft.com/fabric/data-science/evaluate-data-agent)
- [Fabric IQ MCP server](https://learn.microsoft.com/fabric/iq/connectors/fabric-iq-mcp)
- [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)
- [Ontology as a data agent source (Preview)](https://learn.microsoft.com/fabric/iq/ontology/how-to-create-data-agent)
- [Required tenant settings for ontology (Preview)](https://learn.microsoft.com/fabric/iq/ontology/overview-tenant-settings)
- [Ontology as an MCP server (Preview)](https://learn.microsoft.com/fabric/iq/ontology/how-to-use-ontology-mcp-server)
- [Microsoft Agent 365](https://learn.microsoft.com/microsoft-agent-365/overview)
- [Terraform fabric_data_agent](https://registry.terraform.io/providers/microsoft/fabric/latest/docs/resources/data_agent)
- [fabriciq Skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/fabriciq)
- [onelake-catalog-cli Skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/onelake-catalog-cli)
- [ontology-cli Skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/ontology-cli)
