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
