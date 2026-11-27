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
| Delegated OneLake-to-OneLake shortcuts | Preview ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-shortcut-security#shortcut-authentication-models)) | Task 5 | Allow passthrough shortcuts only |

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

A OneLake-to-OneLake shortcut is passthrough by default: the reader's identity reaches the target, and the target's roles apply. A delegated shortcut reads with its connection's identity, and cross-tenant shortcuts are always delegated ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-shortcut-security#shortcut-authentication-models)). The Shortcuts API (GA) doesn't return the mode.

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
