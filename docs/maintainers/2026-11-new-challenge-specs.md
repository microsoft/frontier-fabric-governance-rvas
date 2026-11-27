# New challenge specs: November 2026

These outlines expand section 5 of the [OneLake governance research report](2026-11-onelake-governance-research.md). Phase 2 can copy each one into `challenges/<folder>/challenge.md`, promoting each heading by one level. Statuses were checked on 2026-11-27; recheck them before publishing.

Each outline:

- follows the format of the existing challenges, including a deliberate failure that a PR check must block;
- demonstrates at least one MCP server and one Skill;
- has a GA path for every required task, and lists its preview features with a fallback;
- includes a proposed `site/challenges.json` entry.

Paths such as `catalog/` and `onelake-security/` are proposals. The capstone rows in section 6.11 of the report use the same paths.

## Challenge 09 — OneLake catalog metadata

> **Outcome:** every governed item in the OneLake catalog has an owner, a description and approved tags, all set from a PR. A nightly audit catches endorsement that doesn't match the manifest.

| Field | Value |
|---|---|
| Folder | `challenges/09-onelake-catalog-metadata/` |
| Stage, duration, depends | governed; 120–180 min; 00, 01, 03 |
| MCP server | Fabric Core MCP: `search_catalog`, `update_item` |
| Skill | `onelake-catalog-cli`; `search-consumption-cli` |

```json
{
  "id": "09",
  "name": "OneLake Catalog Metadata",
  "stage": "governed",
  "tagline": "Set tags and descriptions from manifests and audit endorsement.",
  "outcome": "Tag taxonomy and item metadata as code; endorsement audited from the scanner; a PR check for metadata coverage.",
  "duration": "120–180 min",
  "depends": "00, 01, 03",
  "value": "Keep the OneLake catalog accurate now that Fabric holds the metadata people use to find and trust data.",
  "tags": ["OneLake catalog", "tags", "endorsement"],
  "path": "challenges/09-onelake-catalog-metadata/challenge.md"
}
```

| Preview feature | Status | Where | Fallback |
|---|---|---|---|
| Catalog Search API, behind Core MCP `search_catalog` | Preview ([REST](https://learn.microsoft.com/rest/api/fabric/core/catalog/search)) | Task 5 | List Items, which returns descriptions and tags |
| Table metadata API | Preview ([Learn](https://learn.microsoft.com/fabric/onelake/table-apis/additional-table-metadata)) | Stretch goal | Leave column descriptions out |
| Workspace apply and unapply tags | Preview, to verify ([Learn](https://learn.microsoft.com/fabric/governance/tags-overview)) | Stretch goal | Item and domain tags |
| Item relations API | Beta ([REST](https://learn.microsoft.com/rest/api/fabric/core/items)) | Stretch goal | Scanner lineage |

### Why this challenge exists

Purview Data Governance is retiring; support ends 12 November 2027 ([Tech Community](https://techcommunity.microsoft.com/blog/microsoft-security-blog/a-next-step-in-the-evolution-of-the-microsoft-data-governance-strategy/4572227)). The OneLake catalog now holds the metadata people use to find and trust data: domains, tags, descriptions and endorsement. Edited by hand, that metadata drifts like any other configuration. This challenge puts it in manifests and applies it from a PR.

Endorsement has no write API, and only a person can certify an item. The challenge shows how to govern a setting you can only audit.

### Learning objectives

1. Model a tag taxonomy and per-item metadata as code (`catalog/tags.yaml`, `catalog/<workspace>.yaml`).
2. Create tags with the admin Tags API and apply them with Apply Tags, as the SPN.
3. Set item descriptions with Update Item.
4. Audit endorsement from the scanner, because no API can set it.
5. Check discoverability from chat with the Core MCP, and coverage with the `onelake-catalog-cli` skill.

### Prerequisites

- Challenges 00, 01 and 03 complete.
- The SPN is in the security groups for "Service principals can access admin APIs used for updates" (tag definitions) and "Service principals can access read-only admin APIs" (scanner).
- A Fabric admin has decided who can certify items, through the certification tenant setting or by delegating certification to domain admins.
- A production workspace from challenge 01 with at least three items, one of them a semantic model you can certify.

### Tasks

#### Task 1 — Tag taxonomy as code

```yaml
# catalog/tags.yaml
tenant: [Gold, Contains-PII, Reviewed]
domains:
  Finance: [Revenue, Forecast]
```

Add `schemas/tags.schema.json` and two validator rules:

- a domain tag can't reuse a tenant tag name;
- removing a tag needs approval from the CODEOWNERS entry for `catalog/tags.yaml`, because deleting a tag detaches it from every item, with no undo.

#### Task 2 — Item metadata manifests

```yaml
# catalog/prd-fin-revenue.yaml
workspace: prd-fin-revenue
items:
  - name: sm_gold_revenue
    type: SemanticModel
    owner: "@org/finance-data"
    description: "Revenue by product and region, refreshed daily from the Gold lakehouse."
    tags: [Gold, Revenue]
    endorsement: Certified
```

For `prd-*` workspaces, the validator requires that every item has an `owner` that also owns the manifest in CODEOWNERS, a `description` of 1–256 characters, and 1–10 tags from `catalog/tags.yaml`. Domain tags must match the workspace's domain from challenge 03.

**Deliberate failure:** open a PR that adds one item with no description and another with 11 tags. Both must fail.

#### Task 3 — Apply metadata on merge

Write `scripts/apply_catalog.py`:

1. Create missing tag definitions with the admin Bulk Create Tags API.
2. Read each item with Get Item, which returns `description` and `tags`. An item with no tags has no `tags` field.
3. Set changed descriptions with Update Item, and change tags with Apply Tags and Unapply Tags.

Write only what changed. Bulk Create Tags and Apply Tags allow 25 requests a minute, so back off on HTTP 429. Update Item accepts a service principal only for some item types; record any type that rejects it in `docs/troubleshooting.md`.

#### Task 4 — Audit endorsement

A certifier sets endorsement in the portal, and the pipeline checks it. Extend `scripts/drift.py` to run a scan (getInfo, scanStatus, scanResult) and compare each item's `endorsementDetails` with the manifest. Open a `drift/endorsement` issue when the manifest says `Certified` and the item isn't, or when an item is endorsed and the manifest doesn't say so. Compare descriptions and tags from Get Item too, and open a `drift/catalog` issue for any difference.

#### Task 5 — Check discoverability from chat

Ask the Core MCP:

> Search the OneLake catalog for revenue items in prd-fin-revenue and show each item's description.

`search_catalog` matches display names, workspace names and descriptions. It filters only by item type and workspace, and its results carry no tags, labels or endorsement. Learn says changes appear after a couple of minutes, but the `onelake-catalog-cli` skill warns the index can lag up to 24 hours, so don't gate a PR on a search hit.

#### Task 6 — Coverage report with the Skill

Run `onelake-catalog-cli` in admin-audit mode for the governed domains, or in dataowner-audit mode if you aren't a Fabric admin. Save the report to `catalog/reports/<date>.md` and link it from the nightly drift issue.

### Success criteria

- [ ] Merging a manifest change sets descriptions and tags with no portal clicks.
- [ ] The Task 2 PR fails validation.
- [ ] Removing certification in the portal opens a `drift/endorsement` issue on the next nightly run.
- [ ] `search_catalog` finds `sm_gold_revenue` by a word from its description.
- [ ] The coverage report shows no governed item without a description or a tag.

### Stretch goals

- **Table and column descriptions.** Use the table metadata API (Preview). A write replaces all metadata, so read, merge, then write.
- **Workspace tags.** Apply them with the workspace apply tags API (Preview).
- **Certified lineage.** With the item relations API (Beta), fail the audit when a Certified item reads from an item that isn't endorsed.
- **Delegated certification.** Record which domains delegate certification in `domains/*.yaml`, and check it against List Tenant Settings in the drift run.

### MCP tips

- `search_catalog` filters by item type and workspace only. Use it to confirm an item can be found, not to audit tags.
- `update_item` changes a description from chat. Use it to try wording, then put the text in the manifest so the pipeline stays the only writer.

### Skills tips

- `onelake-catalog-cli` has two read-only audit modes (dataowner-audit, admin-audit) and three modes that write (curate, dataowner-remediate, admin-remediate). Use the audit modes here; curate can draft descriptions and tags for the manifest.
- The skill reads endorsement from the scanner and won't offer to set it.
- `search-consumption-cli` runs the same search from the terminal.

### References

- [Tags in Microsoft Fabric](https://learn.microsoft.com/fabric/governance/tags-overview)
- [Apply Tags REST API](https://learn.microsoft.com/rest/api/fabric/core/tags/apply-tags)
- [Admin Tags REST API](https://learn.microsoft.com/rest/api/fabric/admin/tags)
- [Endorsement](https://learn.microsoft.com/fabric/governance/endorsement-overview)
- [Update Item REST API](https://learn.microsoft.com/rest/api/fabric/core/items/update-item)
- [Catalog Search REST API](https://learn.microsoft.com/rest/api/fabric/core/catalog/search)
- [Metadata scanning](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)

## Challenge 10 — OneLake security as code

> **Outcome:** the OneLake security roles of every governed lakehouse live in manifests. Each PR gets a dry run, each merge applies the roles with an ETag, and a test proves that a denied identity can't read.

| Field | Value |
|---|---|
| Folder | `challenges/10-onelake-security-as-code/` |
| Stage, duration, depends | governed; 180–240 min; 00, 01, 02, 04 |
| MCP server | Fabric Core MCP: `onelake_list_data_access_roles`, `onelake_create_or_update_data_access_roles` (DryRun), `onelake_list_shortcuts` |
| Skill | `sqldw-cli` for the denied-read test; `spark-cli` for the Spark path |

```json
{
  "id": "10",
  "name": "OneLake Security as Code",
  "stage": "governed",
  "tagline": "Manage OneLake data access roles from manifests and prove a denied read fails.",
  "outcome": "OneLake security roles applied from manifests with a dry run and an ETag; shortcut rules; a denied-read test.",
  "duration": "180–240 min",
  "depends": "00, 01, 02, 04",
  "value": "Keep table, row and column access in one reviewed place, and prove it holds with a test that must fail.",
  "tags": ["OneLake security", "shortcuts", "dry run"],
  "path": "challenges/10-onelake-security-as-code/challenge.md"
}
```

| Preview feature | Status | Where | Fallback |
|---|---|---|---|
| Terraform `fabric_onelake_data_access_security` | Preview ([Registry](https://registry.terraform.io/providers/microsoft/fabric/latest/docs)) | Stretch goal | The bulk REST call (GA) in Task 3 |
| Effective access for a principal, and hosted OneLake MCP `onelake_get_principal_access` | Preview ([Learn](https://learn.microsoft.com/fabric/onelake/security/authorized-access-for-principal-reference)) | Stretch goal | The denied-read test. The tool can report `canRead: false` for a principal who can read, so it can't be a gate. |
| Git tracking of data access roles | Preview ([Learn](https://learn.microsoft.com/fabric/data-engineering/lakehouse-git-deployment-pipelines)) | Stretch goal | Manifests applied through REST |
| Delegated OneLake-to-OneLake shortcuts | Preview ([blog](https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/simplifying-secure-data-access-with-delegated-onelake-shortcuts-preview/5254632)) | Task 5 | Allow passthrough shortcuts only |

### Why this challenge exists

Challenge 04 governs who can open a workspace. Inside a lakehouse, OneLake security roles decide which tables, rows and columns a reader sees, and teams usually edit those roles by hand. Two API facts make hand edits risky:

- The bulk roles call replaces every role on the item. A pipeline that doesn't own the full role set deletes hand-made roles, and the next run overwrites hand edits.
- Entra members of a role don't travel through Git or fabric-cicd ([Learn](https://learn.microsoft.com/fabric/data-engineering/lakehouse-git-deployment-pipelines)). Promoting a lakehouse doesn't promote who can read it.

OneLake security restricts readers in the Viewer workspace role. Admins, Members and Contributors see all data ([Learn](https://learn.microsoft.com/fabric/onelake/security/data-access-control-model)), so the test identity here is a Viewer.

### Learning objectives

1. Model OneLake security roles as code (`onelake-security/<workspace>/<item>.yaml`), with table access, row filters and hidden columns.
2. Apply the full role set with the bulk API (GA): a dry run on every PR, and an ETag on merge so a stale write fails.
3. Explain which identities OneLake security restricts, and prove it with an identity that must be denied.
4. Record each shortcut's target and authentication mode, and require approval for delegated shortcuts.
5. Inspect roles and shortcuts from chat with the Core MCP.

### Prerequisites

- Challenges 00, 01, 02 and 04 complete.
- A lakehouse with schemas and two Delta tables: `sales.orders` with a `region` column, and `sales.customers` with an `email` column.
- The SPN is workspace Admin or Member, which gives the Reshare permission the bulk call needs.
- A test identity in the Viewer workspace role, such as a second service principal in a security group. Whether a service principal can be a role member is to verify; if it can't, run the test as a test user and save the output.
- The lakehouse's SQL analytics endpoint uses user's identity mode, so OneLake security applies to T-SQL ([Learn](https://learn.microsoft.com/fabric/onelake/security/troubleshoot-onelake-security-for-sql-analytics-endpoints)).

### Tasks

#### Task 1 — Export the current roles

Read the roles the lakehouse has today with List Data Access Roles, or ask the Core MCP:

> List the OneLake data access roles on lh_sales in dev-sales-core, with each role's members and permissions.

Save the result as the first manifest. The bulk call deletes every role the manifest leaves out, including any role Fabric created by default, so each role you keep must be in the file.

#### Task 2 — Role manifests

```yaml
# onelake-security/dev-sales-core/lh_sales.yaml
item: lh_sales
roles:
  - name: SalesReaders
    members:
      entraGroups: [sg-sales-readers]
    tables: [sales.orders, sales.customers]
    rowFilters:
      sales.orders: "SELECT * FROM sales.orders WHERE region = 'EMEA'"
    hiddenColumns:
      sales.customers: [email]
```

Add `schemas/onelake-security.schema.json` and validator rules:

- members are security groups, never individual users;
- role names are the same in every environment, because members carry across workspaces only when role names match exactly;
- a table gets row filters and hidden columns from one role only, because Learn allows combining them within a role but not across roles.

**Deliberate failure:** open a PR that adds a user directly to `SalesReaders`. It must fail.

#### Task 3 — Dry run on PR, apply on merge

Write `scripts/apply_onelake_security.py`:

1. Read the current roles and keep the ETag from the response.
2. On a PR, call the bulk PUT with `dryRun=true` and post the result as a PR comment.
3. On merge, call the bulk PUT with `If-Match` set to that ETag. If someone changed the roles in the portal since the read, the call fails with `PreconditionFailed`. Stop, and open a `drift/onelake-security` issue instead of overwriting.

The API allows 50 requests a minute ([REST](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/create-or-update-data-access-roles)).

#### Task 4 — Prove a denied read

Signed in as the test identity, use `sqldw-cli` to run three queries against the SQL analytics endpoint:

1. `SELECT email FROM sales.customers` fails.
2. `SELECT DISTINCT region FROM sales.orders` returns only `EMEA`.
3. A query on a table outside the role fails.

Save the output to `onelake-security/tests/<date>.md`, and run the same test after every apply. Learn's principal access reference lists about 5 minutes for role changes and about an hour for group changes, so allow for that before you debug a failure.

#### Task 5 — Shortcut rules

A OneLake-to-OneLake shortcut is passthrough by default: the reader's identity reaches the target, and the target's roles apply. A delegated shortcut reads with its connection's identity, and cross-tenant shortcuts are always delegated ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-shortcut-security)). The Shortcuts API (GA) doesn't return the mode.

1. List shortcuts with `onelake_list_shortcuts` or the Shortcuts API.
2. Record each one in `onelake-security/<workspace>/shortcuts.yaml` with its target, its mode (taken from the portal) and an owner.
3. A delegated shortcut needs a `justification` and approval from the security CODEOWNERS entry, because anyone the source item's roles allow can read the target's data through it.
4. The nightly drift run opens a `drift/shortcut` issue for any shortcut that isn't in the file.

#### Task 6 — Dry run from chat

> Dry-run the roles in onelake-security/dev-sales-core/lh_sales.yaml against lh_sales and tell me what would change.

### Success criteria

- [ ] Merging a manifest change updates the roles with no portal clicks.
- [ ] Every PR that touches `onelake-security/` gets a dry-run comment.
- [ ] A role edited in the portal makes the next apply stop with `PreconditionFailed` and open a drift issue.
- [ ] The denied-read test passes, and the Task 2 PR fails validation.

### Stretch goals

- **Terraform.** Manage the same roles with `fabric_onelake_data_access_security` (preview).
- **Git tracking.** Turn on `DataAccessRoles` in the lakehouse's `alm.settings.json` (Preview) and show that role definitions travel through Git while Entra members don't.
- **Principal access.** Compare the test results with the principal access API (Preview). Record mismatches; don't gate on it.
- **Spark path.** Repeat the denied-read test with `spark-cli` from a notebook in another workspace, reading through a passthrough shortcut.

### MCP tips

- `onelake_list_data_access_roles` and `onelake_list_shortcuts` only read.
- `onelake_create_or_update_data_access_roles` replaces every role on the item. Use it with DryRun from chat, and leave real writes to the pipeline.

### Skills tips

- `sqldw-cli` queries SQL endpoints as the signed-in identity, which makes it the quickest denied-read test.
- No Skill manages OneLake security roles yet, so the writes use REST and the Core MCP.

### References

- [OneLake security: get started](https://learn.microsoft.com/fabric/onelake/security/get-started-security)
- [Create and manage OneLake security roles](https://learn.microsoft.com/fabric/onelake/security/create-manage-roles)
- [Bulk create or update data access roles REST API](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/create-or-update-data-access-roles)
- [OneLake Shortcuts REST API](https://learn.microsoft.com/rest/api/fabric/core/onelake-shortcuts)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)

## Challenge 11 — Network exfiltration guardrails

> **Outcome:** a lab workspace can send data only to approved destinations, and accepts traffic only from approved networks. Each control is set from a PR and counts only when an attempt that should fail does fail.

| Field | Value |
|---|---|
| Folder | `challenges/11-network-exfiltration-guardrails/` |
| Stage, duration, depends | governed; 180–240 min; 00, 01 |
| MCP server | Fabric Core MCP: `onelake_get_settings`, `onelake_modify_diagnostics` |
| Skill | `spark-cli` for the copy attempts; `fabric-policies-cli` in a stretch goal |

```json
{
  "id": "11",
  "name": "Network Exfiltration Guardrails",
  "stage": "governed",
  "tagline": "Block unapproved data movement and prove each control with a failed copy.",
  "outcome": "Workspace network policy as code; outbound protection with one approved private endpoint; network and external share audits; a tenant Private Link decision record.",
  "duration": "180–240 min",
  "depends": "00, 01",
  "value": "Stop data leaving through notebooks, shortcuts and shares, with evidence that each block works.",
  "tags": ["outbound protection", "Private Link", "exfiltration"],
  "path": "challenges/11-network-exfiltration-guardrails/challenge.md"
}
```

| Preview or unconfirmed feature | Status | Where | Fallback |
|---|---|---|---|
| Inbound firewall and Azure resource rule APIs | Preview ([Learn](https://learn.microsoft.com/fabric/security/security-workspace-level-firewall-overview)) | Task 5 | Set the rules in the portal, record them in the manifest and save screenshots as evidence |
| Outbound protection for event flows, Real-Time Intelligence items, Operations Agent and Maps | Preview ([Learn](https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview)) | Not used | The lab uses lakehouses and notebooks, which are GA |
| Spark FQDN allowlist for outbound-protected workspaces | To verify; announced 2026-09-28 | Not used | Managed private endpoints |
| IQ Sharing | Preview ([Learn](https://learn.microsoft.com/fabric/onelake/iq-share/onelake-share-overview)) | Stretch goal | External data sharing audit (GA) |
| Fabric policy rules for external data sharing | Roadmap, to verify ([Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-overview)) | Stretch goal | External share audit in Task 6 |

### Why this challenge exists

Challenges 04 and 10 decide who can read data. Network controls decide where that data can go. A reader who can run a notebook can copy a table to any storage account unless the workspace blocks the destination. Fabric now has workspace-level controls for both directions, and each one has limits worth testing:

- Outbound access protection needs an F SKU in a region with Fabric Data Engineering, and it's incompatible with external data sharing ([Learn](https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview)).
- A communication policy PUT replaces the whole policy, and an omitted `defaultAction` becomes Allow ([REST](https://learn.microsoft.com/rest/api/fabric/core/workspaces/set-network-communication-policy)).
- With "Block Public Internet Access" on, tenant Private Link makes the Govern tab, the Capacity Metrics app, cross-tenant shortcuts and OneLake data sharing unavailable across the whole tenant ([Learn](https://learn.microsoft.com/fabric/security/security-private-links-overview)). The challenge treats it as a design decision, not a lab step.

### Learning objectives

1. Model a workspace's inbound and outbound network policy as code (`network/<workspace>.yaml`).
2. Apply it with the communication policy API (GA), always sending the full policy.
3. Prove outbound protection with copies and shortcuts that fail, and allow one destination through a managed private endpoint.
4. Audit network policies and external data shares across the tenant with the admin APIs (GA).
5. Decide when tenant Private Link is worth what it turns off.

### Prerequisites

- Challenges 00 and 01 complete.
- An F SKU capacity in a region with Fabric Data Engineering. A Trial capacity won't work.
- Two lab workspaces on that capacity: `sbx-sec-net-protected` and `sbx-sec-net-open`, each with a lakehouse and a notebook. Don't use a production workspace: these controls affect every user of the workspace.
- An Azure subscription with two ADLS Gen2 accounts: `stcontosoapproved`, reached through a managed private endpoint, and `stcontosoother`, which stays unapproved. You need permission to approve a private endpoint connection on `stcontosoapproved`.
- The SPN is Admin of both lab workspaces and can call the read-only admin APIs.

### Tasks

#### Task 1 — Network policy as code

```yaml
# network/sbx-sec-net-protected.yaml
workspace: sbx-sec-net-protected
inbound:
  defaultAction: Allow
outbound:
  defaultAction: Deny
  managedPrivateEndpoints:
    - name: mpe-stcontosoapproved
      target: stcontosoapproved
      subresource: dfs
```

Add `schemas/network.schema.json` and validator rules: both `defaultAction` fields are required, and every `prd-*` workspace has an outbound `defaultAction` of `Deny`.

**Deliberate failure:** open a PR that leaves out `outbound.defaultAction`. It must fail, because the API would turn the omission into Allow.

#### Task 2 — Apply the policy

Write `scripts/apply_network.py`: get the current communication policy, merge the manifest into it, and PUT the whole policy. Create the managed private endpoint through the Fabric REST API or Terraform (`fabric_workspace_managed_private_endpoint`), then approve the connection on `stcontosoapproved` in Azure.

#### Task 3 — Prove outbound protection

With `spark-cli`, run the same notebook in both workspaces. It writes a small file to `stcontosoother`, then reads from `stcontosoapproved` through the managed private endpoint.

| Attempt | `sbx-sec-net-open` | `sbx-sec-net-protected` |
|---|---|---|
| Write to `stcontosoother` | Succeeds | Fails |
| Read `stcontosoapproved` through the private endpoint | Not needed | Succeeds |
| Create a shortcut to `stcontosoother` | Succeeds | Fails, because OneLake outbound access protection blocks external shortcuts ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-manage-outbound-access)) |

Save each error message to `network/evidence/<date>/`.

#### Task 4 — Diagnostics in the same workspace

With outbound protection on, OneLake diagnostics work only when the diagnostics lakehouse is in the same workspace. Ask the Core MCP:

> Show the OneLake diagnostics settings for sbx-sec-net-protected, then turn diagnostics on and send them to its lakehouse.

Access events reach the lakehouse within about an hour ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-diagnostics-overview)). Add the test reads from Task 3 to the evidence.

#### Task 5 — Inbound rules

Set the inbound `defaultAction` of `sbx-sec-net-protected` to `Deny`, with one firewall rule for your public IP. The firewall applies only when the default action is Deny, and allows up to 256 rules. Allow time for the change to apply, then read a lakehouse file from your machine and from a network that isn't on the list, such as a hosted CI runner. The second read must fail.

Whether the deny also blocks the pipeline's own API calls is to verify. If it does, run the apply from an allowed network, or set the rules in the portal and keep the manifest as the record.

#### Task 6 — Tenant audits

Add a nightly job:

1. List every workspace's network policy with the admin API (GA since 2026-09-01) and open a `drift/network` issue for any `prd-*` workspace whose outbound default is Allow ([REST](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-networking-communication-policies)).
2. List external data shares with the admin API (GA; 10 requests a minute) and open a `drift/external-share` issue for any share that isn't in `network/external-shares.yaml` ([REST](https://learn.microsoft.com/rest/api/fabric/admin/external-data-shares-provider/list-external-data-shares)).
3. Try to create an external data share from `sbx-sec-net-protected`. Learn lists external data sharing as incompatible with outbound protection, so the attempt must be refused. If it isn't, record a finding.

#### Task 7 — Tenant Private Link decision record

Write `docs/network-design.md` in your repo: what tenant Private Link with "Block Public Internet Access" would protect, what it would turn off, which challenges it would affect, and whether the workspace controls in this challenge are enough. Don't turn it on in a shared tenant.

### Success criteria

- [ ] Merging `network/sbx-sec-net-protected.yaml` sets the policy with no portal clicks.
- [ ] Every "Fails" cell in the Task 3 table has a saved error, and the private endpoint read succeeds.
- [ ] The read from an unlisted network fails.
- [ ] An unlisted external share, or a `prd-*` workspace with outbound Allow, opens a drift issue.
- [ ] The Task 1 PR fails validation.

### Stretch goals

- **Fabric policy.** Fabric policy rules for external data sharing are announced as coming soon. When they're available, plan one with `fabric-policies-cli` that allows sharing only from approved workspaces. Fabric policies are Preview and unavailable in West Europe, North Europe and West US.
- **IQ Sharing.** Where IQ Sharing (Preview) is available, try to share the lakehouse in `sbx-sec-net-protected` with another tenant, and record whether outbound protection blocks it. Every share needs an expiration date, and 12 regions don't have IQ Sharing yet.
- **Trusted workspace access.** Read `stcontosoapproved` through the workspace identity and a resource instance rule, which needs ARM or PowerShell ([Learn](https://learn.microsoft.com/fabric/security/security-trusted-workspace-access)).
- **Terraform.** Manage the policy with `fabric_workspace_network_communication_policy`.

### MCP tips

- The Core MCP has no network tools. Use it for the OneLake settings, and REST or Terraform for the policy.

### Skills tips

- `spark-cli` runs the copy attempts and returns the error text for the evidence folder.
- No Skill manages network rules yet.

### References

- [Workspace outbound access protection](https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview)
- [Managed private endpoints](https://learn.microsoft.com/fabric/security/security-managed-private-endpoints-overview)
- [Workspace Private Link](https://learn.microsoft.com/fabric/security/security-workspace-level-private-links-overview)
- [External data sharing](https://learn.microsoft.com/fabric/governance/external-data-sharing-overview)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)

## Challenge 12 — Tenant settings and policies as code

> **Outcome:** the tenant settings and capacity overrides your team owns live in YAML. Each PR gets a plan, each merge applies it, a nightly job reports drift, and a Fabric policy blocks an item type the platform hasn't approved.

| Field | Value |
|---|---|
| Folder | `challenges/12-tenant-settings-policies-as-code/` |
| Stage, duration, depends | governed; 120–180 min; 00, 01, 03 |
| MCP server | Fabric Core MCP: `create_item` for the negative test, `get_knowledge` for guidance; local Fabric MCP `docs_*` tools |
| Skill | `fabric-policies-cli`; `onelake-catalog-cli` in admin-audit mode for the fallback |

```json
{
  "id": "12",
  "name": "Tenant Settings & Policies as Code",
  "stage": "governed",
  "tagline": "Manage tenant settings from YAML, catch portal drift and block unapproved item types.",
  "outcome": "Tenant settings and capacity overrides applied from YAML; a nightly drift report; a Fabric policy that blocks an item type.",
  "duration": "120–180 min",
  "depends": "00, 01, 03",
  "value": "Review every tenant-wide switch in a PR and notice when someone changes one in the portal.",
  "tags": ["tenant settings", "Fabric policies", "drift"],
  "path": "challenges/12-tenant-settings-policies-as-code/challenge.md"
}
```

| Preview or dated feature | Status | Where | Fallback |
|---|---|---|---|
| Fabric policies and the policy set APIs | Preview; unavailable in West Europe, North Europe and West US ([Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-overview)) | Task 6 | Task 7: a capacity override, a PR validator and an admin-audit inventory |
| Copilot setting change on 2026-12-08 | Announced; the Learn page is labeled preview ([Learn](https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric)) | Task 5 | Record what the export shows on the day you run the task |

### Why this challenge exists

Challenge 00 switches tenant settings on by hand in the admin portal. Many of Fabric's governance decisions live in those settings: who can create items, which identities can call the APIs, who can use Copilot. A portal click gets no review, and nothing notices when an admin changes one later.

The tenant settings API is GA, supports service principals and allows 25 requests a minute ([REST](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-tenant-settings)). Capacity overrides can be written; domain and workspace overrides can only be listed. Terraform has a `fabric_tenant_setting` resource, so settings can be managed like everything else in the repo.

Fabric policies (Preview) add allow-only rules for item creation and workspace settings: any action no rule allows is denied. They're unavailable in three regions, so tenant settings remain the GA control.

### Learning objectives

1. Export tenant settings and their capacity, domain and workspace overrides, and choose which ones the repo owns.
2. Apply settings and capacity overrides from YAML: a plan on every PR and an apply on merge, within the API's rate limit.
3. Report drift nightly, including the overrides the API can only list.
4. Handle the Copilot setting change due on 2026-12-08.
5. Block an item type with a Fabric policy, and know the fallback where policies aren't available.

### Prerequisites

- Challenges 00, 01 and 03 complete.
- A test tenant, or a tenant where your team owns the settings you change. Tenant settings apply to everyone, so in a shared tenant run the apply job in plan-only mode.
- The SPN is in the security groups of "Service principals can access read-only admin APIs" and "Service principals can access admin APIs used for updates".
- For Task 6: a capacity used only for this lab, because the active policy applies to every workspace on it. The SPN is a capacity admin of it.

### Tasks

#### Task 1 — Export

Write `scripts/export_tenant_settings.py`. It lists tenant settings, capacity overrides, domain overrides and workspace overrides, and saves them to `tenant/export/<date>.json`. Choose 8 to 10 settings your team owns, including the service principal settings from challenge 00. To check what a setting does, ask the Core MCP (`get_knowledge`) or the local MCP's `docs_*` tools:

> What does the tenant setting "Service principals can access admin APIs used for updates" allow, and who should be in its security group?

#### Task 2 — Settings as YAML

```yaml
# tenant/settings.yaml
settings:
  - title: Service principals can call Fabric public APIs
    enabled: true
    enabledSecurityGroups: [sg-fabric-workspace-provisioner]
    owner: plt
  - title: Make Microsoft Copilot available in Power BI and Fabric
    enabled: true
    owner: plt
    decision: docs/decisions/copilot.md
```

`tenant/capacities/<capacity>.yaml` has the same shape, for the settings the tenant delegates to capacity admins. The scripts resolve titles to API setting names and group names to IDs from the latest export.

Add `schemas/tenant-settings.schema.json` and validator rules:

- every setting has an `owner`;
- a setting turned on for the whole organization, with no `enabledSecurityGroups`, needs a `justification`;
- every title exists in the latest export, so retired settings leave the file.

**Deliberate failure:** open a PR that turns a setting on for the whole organization without a `justification`. It must fail.

#### Task 3 — Plan on PR, apply on merge

Write `scripts/apply_tenant_settings.py`. On a PR, it compares the YAML with a fresh export and posts the changes as a comment. On merge, it updates each changed setting, at most 25 calls a minute, and each changed capacity override. It never writes domain or workspace overrides, because the API can only list them.

#### Task 4 — Nightly drift

Run the export every night and compare it with the YAML. Open a `drift/tenant-settings` issue with the difference, and list every domain and workspace override in the issue so a person reviews them. Test it by changing a setting in the admin portal.

#### Task 5 — The Copilot change

On 2026-12-08 the standalone Copilot setting turns off by default and "Make Microsoft Copilot available in Power BI and Fabric" turns on. Standalone Power BI Copilot and App Copilot retire on 2027-01-15.

1. Find both settings in the export and record your organization's decision for each in the YAML, with a short `docs/decisions/copilot.md`.
2. Before 2026-12-08, the drift job shows whether the change will move your tenant away from that decision. After it, confirm the new defaults in the export.

#### Task 6 — Block an item type with a Fabric policy

Fabric policies allow only what a rule lists. One policy is active per scope, and changes take about 15 minutes to apply.

1. With `fabric-policies-cli`, plan a policy set for the lab capacity. It allows the item types the lab uses and leaves out SQL database. The skill discovers the current API contract. Learn's pages disagree on whether the API or only the workspace item-creation experience can create a policy set, so don't hard-code one page's call.
2. Keep the policy set definition in Git. Activate it through the API: Git can't activate a policy ([Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-rest-api)). The REST reference documents only tenant-scope activation so far ([REST](https://learn.microsoft.com/rest/api/fabric/admin/policy-sets)). If the skill can't find the capacity-scope call, activate the set in the Policies Center and say so in the PR.
3. After 15 minutes, ask the Core MCP to create a SQL database and a lakehouse in a workspace on that capacity:

   > Create a SQL database called sqldb_blocked and a lakehouse called lh_allowed in sbx-plt-policy-test.

   The SQL database must fail and the lakehouse must succeed. Save both responses.

#### Task 7 — Fallback where Fabric policies aren't available

Required only if Task 6 can't run. A capacity override of the item creation tenant setting limits who can create items on the lab capacity to `sg-fabric-creators`; the setting's exact name is to verify. The override controls who creates items, not which types, so add two more checks:

- a PR validator that reads the item type in each `.platform` file and rejects SQL databases;
- a nightly `onelake-catalog-cli` admin-audit run that lists SQL databases across the tenant.

### Success criteria

- [ ] Merging a change to `tenant/settings.yaml` updates the setting with no portal clicks, or posts a plan in plan-only mode.
- [ ] A setting changed in the portal opens a drift issue the next night, and the issue lists domain and workspace overrides.
- [ ] The SQL database request fails and the lakehouse request succeeds, or the Task 7 checks catch the SQL database.
- [ ] The Task 2 PR fails validation.

### Stretch goals

- **Terraform.** Manage the same settings with `fabric_tenant_setting` and compare `terraform plan` with the drift report.
- **Policy evaluation.** The REST article lists a policy evaluation API that the reference doesn't include yet (to verify). If it's available, evaluate the blocked action in the PR before activation.

### MCP tips

- The Core MCP has no tenant settings or policy tools. Here it runs the negative test and answers questions about settings.

### Skills tips

- `fabric-policies-cli` maps a scenario to rules and acts only after approval, so its plan can go in the PR.
- `onelake-catalog-cli` admin-audit mode is read-only. Its item inventory lists items by type across the tenant.

### References

- [Tenant settings REST API](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-tenant-settings)
- [Tenant settings index](https://learn.microsoft.com/fabric/admin/tenant-settings-index)
- [Fabric policies](https://learn.microsoft.com/fabric/governance/fabric-policies-overview)
- [Fabric policies REST APIs](https://learn.microsoft.com/fabric/governance/fabric-policies-rest-api)
- [Copilot in Power BI and Fabric settings](https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric)
- [Terraform provider for Fabric](https://registry.terraform.io/providers/microsoft/fabric/latest/docs)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)

## Challenge 13 — Purview Data Governance transition assessment

> **Outcome:** an inventory of what your organization uses in Purview Data Governance, with each construct in one of four buckets, a gap register with owners and decisions, a steward RACI, and one domain piloted in Fabric with its acceptance results.

| Field | Value |
|---|---|
| Folder | `challenges/13-purview-transition-assessment/` |
| Stage, duration, depends | intelligent; 180–240 min; 00, 01, 03, 09 |
| MCP server | Hosted OneLake MCP (Preview) on the export lakehouse; fallback Fabric Core MCP `list_items` and `get_item` |
| Skill | `onelake-catalog-cli`; `sqldw-cli` or `spark-cli` for the inventory queries |

```json
{
  "id": "13",
  "name": "Purview Transition Assessment",
  "stage": "intelligent",
  "tagline": "Inventory Purview Data Governance, sort it into four buckets and pilot one domain in Fabric.",
  "outcome": "An inventory, a gap register with owners and decisions, a steward RACI and a one-domain pilot.",
  "duration": "180–240 min",
  "depends": "00, 01, 03, 09",
  "value": "Decide what moves to Fabric, what stays in Purview and what needs a bridge before support ends on 12 November 2027.",
  "tags": ["Purview transition", "inventory", "RACI"],
  "path": "challenges/13-purview-transition-assessment/challenge.md"
}
```

| Preview feature | Status | Where | Fallback |
|---|---|---|---|
| Unified Catalog self-serve analytics export | Preview: the setup path is labeled "Solution integrations (preview)" ([Learn](https://learn.microsoft.com/purview/unified-catalog-self-serve-analytics)) | Task 1 | The synthetic dataset in the challenge folder |
| Hosted OneLake MCP server | Preview ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-hosted-mcp)) | Task 2 | Core MCP `list_items` and `get_item` |
| Unified Catalog REST API | Preview ([Learn](https://learn.microsoft.com/rest/api/purview/unified-catalog-api-overview)) | Stretch goals | Record the export's blind spots as gaps |

### Why this challenge exists

Purview Data Governance is retiring; support ends 12 November 2027 ([Tech Community](https://techcommunity.microsoft.com/blog/microsoft-security-blog/a-next-step-in-the-evolution-of-the-microsoft-data-governance-strategy/4572227)). The retirement covers the Unified Catalog, Data Map, Workflows and the classic Azure Purview solutions. It doesn't affect Information Protection, DLP, Insider Risk Management or DSPM ([Learn](https://learn.microsoft.com/purview/data-governance-overview)). Purview remains the security and compliance layer. Only sensitivity labels, protection policies and DLP need Purview licensing; everything else works with a Fabric license ([Learn](https://learn.microsoft.com/fabric/governance/get-started-with-fabric-governance)).

The OneLake catalog covers much of the rest, but not all of it. A public transition post says "external metadata scanning, glossary and CDE depth, data quality workflows, and broad policy coverage are not one-to-one replacements today" ([Tech Community](https://techcommunity.microsoft.com/blog/analyticsonazure/from-purview-data-governance-to-the-fabric-onelake-catalog/4573422)). This challenge teaches the method it describes: inventory, classify, design the operating model, pilot, then migrate in waves.

The announcement asks organizations with contractual obligations, or in highly regulated industries, to contact their Microsoft account team early. This assessment gives that conversation its facts.

### Learning objectives

1. Load the Purview self-serve analytics export, or its synthetic copy, into a restricted lakehouse.
2. Count each Purview construct and record what the export can't show.
3. Put each construct in one of four buckets, with a source for every decision.
4. Give each gap an owner role and a decision.
5. Map Purview governance roles to Fabric roles and process roles in a RACI.
6. Pilot one domain, including one identity that must be denied, and retire a Purview dependency only when its acceptance criteria pass.

### Prerequisites

- Challenges 00, 01, 03 and 09 complete. Challenge 10 is optional; Task 6 reuses its roles if you did it.
- A workspace, `sbx-plt-purview-assess`, with a lakehouse, `purview_export`. Limit access to the assessment team: the export doesn't enforce role-based access on the data it publishes.
- For the real export only: an existing Purview account with the Unified Catalog, the Data Governance Administrator role, and Contributor on the workspace for the Purview managed identity. New data governance accounts can no longer be created ([Learn](https://learn.microsoft.com/purview/data-governance-overview)), so most learners use the synthetic dataset.

### Tasks

#### Task 1 — Load the export

Choose one path.

- **Synthetic (default).** Load the CSV files in `data/purview-export/` into Delta tables in `purview_export` with the notebook in the challenge folder. They use the export's table names and keys and describe a fictional organization.
- **Real export.** In the Purview portal, open Settings, Unified Catalog, Solution integrations (preview), and publish to `purview_export`. If your tenant has managed private endpoints enabled, publish to ADLS Gen2 and shortcut the tables in: publishing to a Fabric workspace isn't supported there.

The export publishes governed assets only. It holds 45 tables, covering domains, data products, glossary terms, CDEs, OKRs, assets and columns with classifications, data quality rules and runs, access policy sets, subscription requests and health actions. A deleted and re-created asset gets a new ID, so match assets by name as well as ID when you compare two runs.

The owner tables identify people. Keep them out of Git and commit role or group names only.

#### Task 2 — Inventory

Connect the hosted OneLake MCP server to `purview_export` and check what the export wrote:

> List the tables in purview_export and flag any that are empty.

With `sqldw-cli` against the SQL analytics endpoint, or `spark-cli` in a notebook, write `transition/inventory.csv`, one row per construct:

```csv
construct,purview_tables,count,with_owner,fabric_target,bucket,gap_ids,source
Governance domains,Business Domain,12,12,Domains and subdomains,,,
Glossary terms,Glossary Term; Relationship,340,295,Tags and descriptions,,,
Lineage,not exported,,,Lineage view and item relations,,,
```

The values are examples. Count at least domains, data products, glossary terms, CDEs, OKRs, data quality rules, access policy sets, subscription requests and health actions. Count descriptions longer than 256 characters, the limit for a Fabric item description. Add a `not exported` row for each thing the export leaves out: lineage, sensitivity label assignments, workflow definitions, collections, scans, data sources and custom metadata.

#### Task 3 — Four buckets

The transition post sorts each requirement into one of four buckets. This challenge uses these working definitions:

| Bucket | Use it when |
|---|---|
| Move now | A GA Fabric construct meets the need. |
| Coexist | It stays in Purview. This fits the security and compliance features; for Data Governance features, coexistence ends on 12 November 2027. |
| Bridge | A process or a third-party catalog covers what Fabric doesn't. |
| Redesign | A different Fabric construct or operating model meets the need. |

Fill `bucket`, `gap_ids` and `source` for every row. Two examples:

- **Governance domains: move now.** Domains and subdomains are GA, with an admin API and `fabric_domain` ([Learn](https://learn.microsoft.com/fabric/governance/domains)). Domain assignment doesn't change who can open an item, so access is a separate row.
- **Data quality rules: bridge or redesign.** Fabric has no rules, profiling or scoring engine. Materialized lake view constraints cover part of it (status to verify) ([Learn](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/data-quality)), and data quality is an announced plan with no date ([blog](https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/onelake-the-unified-foundation-for-data-context-governance-and-ai/5423035)).

Write `scripts/validate_transition.py`. It checks that every row has a bucket and a source, that every row outside "move now" has a gap ID in the gap register, that every gap has an owner role and a decision, and that a `wait` decision links a dated item on the Fabric roadmap.

**Deliberate failure:** open a PR that gives the data quality gap the decision `wait` and cites the announced plan, which has no date. It must fail.

#### Task 4 — Gap register

Write `transition/gap-register.md`, one row per gap:

```markdown
| ID | Gap | Constructs (count) | Owner role | Decision | Source |
|---|---|---|---|---|---|
| G-01 | No data product object: no owner, terms-of-use or update-frequency fields | Data products (48) | Governance lead | Process bridge: data contracts in the repo | [Tech Community](https://techcommunity.microsoft.com/blog/analyticsonazure/from-purview-data-governance-to-the-fabric-onelake-catalog/4573422) |
```

Start with the documented gaps:

- no data product object;
- tags cover glossary terms and CDEs only partly, with no definition, hierarchy or steward, and 10 tags per item;
- Fabric policies have no access-request workflow ([Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-overview));
- no API sets endorsement;
- lineage stops at item level;
- no data quality engine;
- Data Map scans of non-Fabric sources have no Fabric equivalent;
- existing Purview API integrations need rework.

Then add any the inventory reveals. Each gap gets one decision: accept, process bridge, third-party catalog bridge, or `wait` for a dated roadmap item. For third-party catalogs, the announcement names Atlan, Alation, Collibra and Informatica. The challenge doesn't compare them, and choosing one is out of scope.

#### Task 5 — Steward RACI

Join the Owner, Owner Assignment and Policy Set Approver tables to count who holds each responsibility today, by role. Then write `transition/raci.md`, with activities as rows and roles as columns. Cover at least: create a domain, assign a workspace to a domain, certify an item, maintain tags, approve access, define data quality checks and apply sensitivity labels.

This role mapping is the RVAS's reading, not a Microsoft table:

| Purview role | Fabric counterpart |
|---|---|
| Governance Domain Creator | Fabric admin, because domain admins can't create or delete top-level domains |
| Governance Domain Owner | Domain admin |
| Data Product Owner | A workspace role plus domain contributor |
| Data Steward, Data Health Owner, Data Health Reader, Data Source Administrator | None; a process role in the RACI |

#### Task 6 — Pilot one domain

Choose one domain whose rows are mostly "move now".

1. Run `onelake-catalog-cli` in admin-audit mode, or dataowner-audit if you aren't a Fabric admin. Save the domain's coverage report to `transition/pilot/before.md`.
2. Write the acceptance criteria in `transition/pilot.md` before changing anything. For example: every pilot item has a description and tags from `catalog/tags.yaml`, the items behind each data product are certified, and a user outside the domain's access group is denied.
3. Apply the "move now" rows as code, with challenge 03's domain assignment and challenge 09's manifests. Endorsement has no write API, so a certifier sets it in the portal and challenge 09's drift job checks it.
4. Prove one identity is denied. Sign in as the lab's test user, who has no access to the pilot items, try to read a pilot table and save the error. If you did challenge 10, test a principal its OneLake security role excludes.
5. Run the Skill again and save `transition/pilot/after.md`. Mark each criterion pass or fail. In `transition/pilot.md`, list as retirable only the Purview dependencies whose criteria all pass.

### Success criteria

- [ ] `transition/inventory.csv` covers every construct in the export and the seven it leaves out, and every row has a bucket and a source.
- [ ] Every row outside "move now" points to a gap with an owner role and a decision.
- [ ] Every activity in `transition/raci.md` has exactly one accountable role, and no person's name is in the repo.
- [ ] The acceptance criteria predate the pilot changes, the denied read is saved, and only dependencies whose criteria all pass are listed as retirable.
- [ ] The Task 3 PR fails validation.

### Stretch goals

- **Fill the blind spots.** Use the Unified Catalog REST API (Preview) to recover part of what the export leaves out, and record what neither source covers. The backup endpoints restore into another Purview account, not into Fabric ([Learn](https://learn.microsoft.com/purview/unified-catalog-disaster-recovery)).
- **Wave plan.** Turn the buckets into migration waves, one domain per wave, each with acceptance criteria and a date before 12 November 2027.

### MCP tips

- The hosted OneLake MCP server works on one item, so connect it to `purview_export`. OneLake checks your permissions on every operation, and connecting an agent grants it no extra access.
- Four of its 15 tools create or delete files and directories. Approve only the read-only tools here.
- Its page doesn't say whether service principals are supported, so connect with your own account.
- Without it, ask the Core MCP to list the items in `sbx-plt-purview-assess` and get the lakehouse, then query its SQL analytics endpoint with `sqldw-cli`.

### Skills tips

- `sqldw-cli` covers SQL analytics endpoints and `spark-cli` covers notebooks. Either can build the inventory.
- `onelake-catalog-cli` audit modes never write. Pick admin-audit or dataowner-audit by the APIs you can call, not by job title.

### References

- [A next step in the evolution of the Microsoft data governance strategy](https://techcommunity.microsoft.com/blog/microsoft-security-blog/a-next-step-in-the-evolution-of-the-microsoft-data-governance-strategy/4572227)
- [From Purview Data Governance to the Fabric OneLake catalog](https://techcommunity.microsoft.com/blog/analyticsonazure/from-purview-data-governance-to-the-fabric-onelake-catalog/4573422)
- [Purview data governance overview](https://learn.microsoft.com/purview/data-governance-overview)
- [Unified Catalog self-serve analytics](https://learn.microsoft.com/purview/unified-catalog-self-serve-analytics)
- [Unified Catalog REST API](https://learn.microsoft.com/rest/api/purview/unified-catalog-api-overview)
- [Hosted OneLake MCP server](https://learn.microsoft.com/fabric/onelake/onelake-hosted-mcp)
- [Fabric domains](https://learn.microsoft.com/fabric/governance/domains)
- [Get started with Fabric governance](https://learn.microsoft.com/fabric/governance/get-started-with-fabric-governance)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
