# Challenge 09 — OneLake catalog metadata

> **Outcome:** every governed item in the OneLake catalog has an owner, a description and approved tags, all set from a PR. A nightly audit catches endorsement that doesn't match the manifest.

## Why this challenge exists

Purview Data Governance is retiring; support ends 12 November 2027 ([Learn](https://learn.microsoft.com/purview/data-governance-overview)).

The OneLake catalog now holds the metadata people use to find and trust data: domains, tags, descriptions and endorsement. Edited by hand, that metadata drifts like any other configuration. This challenge puts it in manifests and applies it from a PR. [Challenge 13](../13-purview-transition-assessment/challenge.md) maps an existing Purview Data Governance estate to these features.

Endorsement has no write API, and only a person can certify an item. The challenge shows how to govern a setting you can only audit.

## Learning objectives

1. Model a tag taxonomy and per-item metadata as code (`catalog/tags.yaml`, `catalog/<workspace>.yaml`).
2. Create tags with the admin Tags API and apply them with Apply Tags, as the SPN.
3. Set item descriptions with Update Item.
4. Audit endorsement with the scanner, because no API can set it.
5. Check discoverability from chat with the Core MCP, and coverage with the `onelake-catalog-cli` skill.

## Prerequisites

- Challenges [00](../00-setup/challenge.md), [01](../01-workspace-as-code/challenge.md) and [03](../03-domains-capacities-sensitivity/challenge.md) complete.
- The SPN's group, `sg-fabric-workspace-provisioner`, is enabled in "Service principals can access admin APIs used for updates" (to create tags) and "Service principals can access read-only admin APIs" (for the scanner). The SPN isn't a Fabric administrator.
- A Fabric administrator has decided who can certify items, in the Certification tenant setting or by delegating certification to domain admins, and you can certify. The setting is at OneLake catalog > Govern > Configurations > Tenant settings > Export and sharing settings; where Govern isn't available, use Settings > Admin portal > Tenant settings.
- The production workspace `prd-fin-revenue` (`environment: prd`, domain `dom-fin-corp`) with at least three items, one of them a semantic model you can certify.

## Tasks

### Task 1 — Tag taxonomy as code

Save this as `catalog/tags.yaml`:

```yaml
tenant: [Gold, Contains-PII, Reviewed]
domains:
  dom-fin-corp: [Revenue, Forecast]
```

Add `schemas/tags.schema.json` and two validator rules:

- a domain tag can't reuse a tenant tag name;
- removing a tag needs approval from the CODEOWNERS entry for `catalog/tags.yaml`, because deleting a tag removes it from every item, with no undo.

Declare these rules, and the Task 2 rules, in `rules/policy.yaml` and implement them in `scripts/validate.py`. Then copy `rules/policy.yaml` to `api/policy.yaml` so the two stay identical.

Add the entry to `.github/CODEOWNERS`:

```text
/catalog/tags.yaml @your-org/fabric-governance-maintainers
```

### Task 2 — Item metadata manifests

Save this as `catalog/prd-fin-revenue.yaml`:

```yaml
workspace: prd-fin-revenue
items:
  - name: sm_gold_revenue
    type: SemanticModel
    owner: "@your-org/fin-data"
    description: "Revenue by product and region, refreshed daily from the Gold lakehouse."
    tags: [Gold, Revenue]
    endorsement: Certified
```

The owner is a GitHub team. Give it the manifest in CODEOWNERS, so the team approves every change to its items' metadata:

```text
/catalog/prd-fin-revenue.yaml @your-org/fin-data
```

For workspaces whose manifest in `workspaces/` has `environment: prd`, the validator requires that every item has:

- an `owner` that also owns the manifest in CODEOWNERS;
- a `description` of 1 to 256 characters;
- 1 to 10 tags from `catalog/tags.yaml`, where domain tags match the workspace's domain from challenge 03.

**Deliberate failure:** open a PR that adds one item with no description and another with 11 tags. Both must fail.

### Task 3 — Apply metadata on merge

No MCP tool covers tags, so this task calls the REST APIs. Write `scripts/apply_catalog.py` and reuse `scripts/_fabric.py` for tokens and retries:

1. List the tag definitions with List Tags (`GET /v1/tags`) and create missing ones with the admin Bulk Create Tags API. A domain tag takes a `Domain` scope with the domain's ID from challenge 03.
2. Read each item with Get Item, which returns `description` and `tags`. Treat a missing `tags` field as no tags.
3. Set changed descriptions with Update Item. Change tags with Apply Tags and Unapply Tags, which take tag IDs, so map names to IDs from step 1.

Write only what changed. Apply Tags and Unapply Tags need Contributor or higher on the workspace. The tag APIs allow 25 requests a minute, so back off on HTTP 429; `_fabric.py` already honors `Retry-After`. Stop on 401 or 403 with a clear error, and never read either as "not found". Update Item accepts a service principal only for some item types; note any type that rejects it in your repo's troubleshooting doc ([`docs/troubleshooting.md`](../../docs/troubleshooting.md)).

Run the script on merge to `main` from a new step in `provision.yml`, which already has the OIDC login, and add `catalog/**` to that workflow's `paths`.

### Task 4 — Audit endorsement

A person who can certify sets endorsement in the portal, and the pipeline checks it. No API writes endorsement, so never script it.

Extend `scripts/drift.py` to run a metadata scan with the scanner APIs (Power BI admin API; no Fabric API yet):

```text
POST https://api.powerbi.com/v1.0/myorg/admin/workspaces/getInfo
GET https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanStatus/{scanId}
GET https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanResult/{scanId}
```

Compare each item's `endorsementDetails` with the manifest. Open a `drift/endorsement` issue when the manifest says `Certified` and the item isn't, or when an item is endorsed and the manifest doesn't say so. Compare descriptions and tags from Get Item too, and open a `drift/catalog` issue for any difference. Create both labels in your repo first.

### Task 5 — Check discoverability from chat

> **Preview** (checked 2026-11-27): Catalog Search API, which the Core MCP `search_catalog` tool calls — [Learn](https://learn.microsoft.com/rest/api/fabric/core/catalog/search). GA route: List Items, which returns descriptions and tags.

Ask the Core MCP:

> Search the OneLake catalog for revenue items in prd-fin-revenue and show each item's description.

`search_catalog` matches display names, workspace names and descriptions, and returns only what the caller can read. It filters only by item type and workspace, and its results carry no tags, labels or endorsement. Learn says new and updated entries can take a couple of minutes to appear ([catalog search overview](https://learn.microsoft.com/rest/api/fabric/articles/onelakecatalog/overview)), but the `onelake-catalog-cli` skill warns that the index can lag up to 24 hours, so don't gate a PR on a search hit.

### Task 6 — Coverage report with the Skill

In a Copilot CLI session:

```text
/onelake-catalog-cli
```

Ask for an admin-audit of the `dom-fin-corp` domain, or a dataowner-audit if you aren't a Fabric administrator, that lists every item without a description or a tag. Save the report to `catalog/reports/<YYYY-MM-DD>.md` and link it from the nightly drift issue.

Compare the report with the **Govern** section of the OneLake catalog. A Fabric administrator sees the whole estate there, including description and endorsement coverage, refreshed daily. An item owner sees the curation state of their own items, refreshed when Govern opens. Govern isn't available when Private Link is activated; there, the skill's report is your view.

## Success criteria

- [ ] Merging a manifest change sets descriptions and tags with no portal clicks.
- [ ] The Task 2 PR fails validation.
- [ ] Removing certification in the portal opens a `drift/endorsement` issue on the next nightly run.
- [ ] `search_catalog` finds `sm_gold_revenue` by a word from its description.
- [ ] The coverage report shows no governed item without a description or a tag.

## Stretch goals

> **Preview** (checked 2026-11-27): Table metadata API — [Learn](https://learn.microsoft.com/fabric/onelake/table-apis/additional-table-metadata). GA route: none; stretch task.

- **Table and column descriptions.** Add descriptions for the Gold tables. A write replaces all of a table's metadata, so read, merge, then write.

> **Preview** (checked 2026-11-27): Apply Workspace Tags API, which `scripts/provision.py` calls — [Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/apply-workspace-tags). GA route: apply the tags in the workspace settings, under Tags.

- **Workspace tags.** `scripts/provision.py` applies the `tags` in each workspace manifest. Make the validator check them against `catalog/tags.yaml` too, with domain tags matching the workspace's domain. A tag that doesn't exist or belongs to another domain then fails the PR, instead of getting a warning and being skipped at provisioning.

> **Preview** (checked 2026-11-27): Item relations API (beta) — [Learn](https://learn.microsoft.com/rest/api/fabric/core/items). GA route: the scanner's lineage output.

- **Certified lineage.** Call Get Upstream Relations with `beta=true` for each Certified item, and fail the audit when one reads from an item that isn't endorsed.
- **Delegated certification.** Record which domains delegate certification in `domains/*.yaml`. In the drift run, check it against `delegateToDomain` in List Tenant Settings and against the domain overrides that `GET /v1/admin/domains/delegatedTenantSettingOverrides` lists.

## MCP tips

- `search_catalog` filters by item type and workspace only. Use it to confirm an item can be found, not to audit tags.
- `update_item` changes a description from chat. Use it to try wording, then put the text in the manifest so the pipeline stays the only writer.
- No MCP tool covers tags, endorsement or the scanner, so Tasks 3 and 4 call REST.

## Skills tips

- `onelake-catalog-cli` has two read-only audit modes (dataowner-audit and admin-audit) and three modes that write (curate, dataowner-remediate and admin-remediate). Use the audit modes here. Curate can draft descriptions and tags; copy them into the manifest and decline its writes.
- The skill reads endorsement from the scanner and won't offer to set it.
- `search-consumption-cli` runs the same catalog search from the terminal.
- If the skills aren't installed, run these from a terminal:

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

## Repository files

This challenge reuses `scripts/_fabric.py` and extends these files in the repo root:

- `scripts/validate.py`, `scripts/drift.py`
- `rules/policy.yaml` and its copy `api/policy.yaml`
- `.github/workflows/provision.yml`, `drift.yml`
- `.github/CODEOWNERS`

It adds:

- `catalog/tags.yaml`, `catalog/<workspace>.yaml` and the reports in `catalog/reports/`
- `schemas/tags.schema.json`
- `scripts/apply_catalog.py`

## References

- [Tags in Microsoft Fabric](https://learn.microsoft.com/fabric/governance/tags-overview)
- [Apply Tags REST API](https://learn.microsoft.com/rest/api/fabric/core/tags/apply-tags)
- [Admin Tags REST API](https://learn.microsoft.com/rest/api/fabric/admin/tags)
- [Endorsement](https://learn.microsoft.com/fabric/governance/endorsement-overview)
- [Update Item REST API](https://learn.microsoft.com/rest/api/fabric/core/items/update-item)
- [Catalog Search REST API](https://learn.microsoft.com/rest/api/fabric/core/catalog/search)
- [Metadata scanning](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview)
- [Govern in the OneLake catalog](https://learn.microsoft.com/fabric/governance/onelake-catalog-govern)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [`onelake-catalog-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/onelake-catalog-cli)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
