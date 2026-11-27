# OneLake governance research: November 2026

This report records what Microsoft Fabric offers for platform governance on 2026-11-27, what the Fabric news from July to November 2026 adds, and what both mean for the RVAS challenges. Maintainers use it to plan changes to existing challenges and to add new ones.

- The proposed challenge outlines are in [New challenge specs: November 2026](2026-11-new-challenge-specs.md).
- Accuracy fixes to existing content are in a separate report, `docs/maintainers/2026-11-platform-governance-audit.md`.
- Every source is public: Microsoft Learn, the Fabric blog, the Fabric roadmap, Tech Community, Partner Center announcements, the Terraform Registry and public GitHub. Every claim was checked on 2026-11-27.

## How to read the status column

| Status | Meaning |
|---|---|
| GA | Generally available. The Learn page carries no preview label. |
| Preview | Labeled preview on Learn or in the announcing post. Pair any control built on it with a fallback. |
| Beta | The REST operation needs `?beta=true`. |
| Roadmap | A plan on [roadmap.fabric.microsoft.com](https://roadmap.fabric.microsoft.com/), not a shipped feature. |
| To verify | Sources disagree, or none states a status. Section 2 lists the conflicts. |

Fabric blog links point to community.fabric.microsoft.com, where blog.fabric.microsoft.com now redirects. Learn links omit the locale.

## Key findings

1. **Fabric is now the data governance product.** Purview Data Governance is retiring; support ends 12 November 2027. Purview remains the security and compliance layer, and only sensitivity labels, protection policies and DLP need Purview licensing. See section 4.
2. **The Govern tab in the OneLake catalog is GA** and replaced the Purview hub. It isn't available when tenant Private Link is on.
3. **Most governance controls run as code with a service principal:** domains, tags, tenant settings, OneLake security roles, network rules, external share revocation and Fabric policies (Preview). Terraform provider v1.15.1 covers domains, tags, tenant settings, OneLake security roles and network rules. Section 3 maps each control.
4. **Two controls can't run in a service principal pipeline.** Endorsement has no write API, and the bulk sensitivity label APIs accept user identities only. Challenges must audit endorsement and run labeling as a user step.
5. **Fabric policies (Preview) add allow-only rules** for item creation and workspace settings at tenant or capacity scope. Learn lists them as unavailable in West Europe, North Europe and West US, so tenant settings remain the GA control.
6. **Network isolation has trade-offs a lab should show.** Workspace outbound access protection doesn't work with external data sharing. Workspace Private Link doesn't support deployment pipelines or semantic models. Tenant Private Link removes the Govern tab. Several network controls need an F SKU and don't work on a Trial.
7. **OneLake security is ready for code, with preview parts.** The data access roles API accepts service principals and supports a dry run. The effective-access API and the Terraform resource are Preview.
8. **Dated changes affect existing challenges.** On 2026-12-08 the standalone Copilot in Power BI setting turns off by default, and standalone Power BI Copilot retires on 2027-01-15. From 2027-02-28, users without read-write permission on workspace items lose Git integration and, for workspaces with protection policies, deployment pipelines.
9. **Skill and API names have moved.** Skills for Fabric switched to `{item}-cli` names in v0.3.11 (2026-08-06), so most skill names in challenges 00–08 are out of date. The preview versions of the Domains REST APIs are no longer available.
10. **Five new challenges are proposed (09–13):** catalog metadata, OneLake security, network and exfiltration guardrails, tenant settings and policies, and the Purview Data Governance transition. See section 5.

## 1. Capability baseline

One table per area. Each row gives the status, the limits that shape a challenge, and the source. All rows were checked on 2026-11-27.

### 1.1 OneLake catalog and metadata

| Capability | Status | What matters | Source |
|---|---|---|---|
| Govern tab | GA, rolling out by region | Replaced the Purview hub. Insights refresh daily. Not available with tenant Private Link or to guest users. Its Policies Center is Preview. | [Learn][l-govern], [blog 2026-10-28][b-govern] |
| Tags | GA | 10,000 per tenant and 10 per item. Domain tags can't reuse tenant tag names. Bulk Create Tags and Apply Tags allow 25 requests a minute and accept service principals. | [Learn][l-tags], [REST][r-applytags] |
| Workspace tags | To verify | Up to 10 per workspace, set by workspace admins. Learn shows no preview label; the `onelake-catalog-cli` skill treats them as preview. | [Learn][l-tags] |
| Endorsement | GA | Promoted, Certified and Master data. Certification can be delegated to domain admins. There's no write API, so automation can only audit it. | [Learn][l-endorse] |
| Item descriptions | GA | Update Item sets descriptions of up to 256 characters. Service principal support depends on the item type. | [REST][r-updateitem] |
| Table metadata API | Preview | The `onelake-catalog-cli` skill warns that a write replaces all existing metadata: read, merge, then write. | [Learn][l-tablemeta] |
| Catalog Search API | Preview | `POST /v1/catalog/search`. Users, service principals and managed identities; 50 requests a minute; up to 1,000 results a page. Results carry no domain, tags, labels or endorsement. Table results need the tenant setting "Users can find objects in search". | [REST][r-search] |
| Item relations API | Beta on Learn, Preview in the blog | Upstream and downstream edges of type Shortcut, PushData or Orchestration; 50 requests a minute. | [blog 2026-09-10][b-relations] |
| Lineage and metadata scanning | GA | The scanner admin APIs remain the tenant-wide export for lineage and metadata. | [Lineage][l-lineage], [scanning][l-scan] |
| Federated catalogs: AWS Glue, Azure Monitor, Dremio, Google lakehouse runtime catalog | To verify | Preview on Learn; GA in the Ignite 2026 OneLake post. | [What's new][l-whatsnew], [blog 2026-11-17][b-ignite-onelake] |
| Third-party catalogs | Atlan connector GA | The 2026-11-12 announcement names Atlan, Alation, Collibra and Informatica. | [Tech Community][p1], [What's new][l-whatsnew] |

[l-govern]: https://learn.microsoft.com/fabric/governance/onelake-catalog-govern
[b-govern]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/govern-your-microsoft-fabric-data-estate-from-one-place-with-the-onelake-catalog/5377369
[l-tags]: https://learn.microsoft.com/fabric/governance/tags-overview
[r-applytags]: https://learn.microsoft.com/rest/api/fabric/core/tags/apply-tags
[l-endorse]: https://learn.microsoft.com/fabric/governance/endorsement-overview
[r-updateitem]: https://learn.microsoft.com/rest/api/fabric/core/items/update-item
[l-tablemeta]: https://learn.microsoft.com/fabric/onelake/table-apis/additional-table-metadata
[r-search]: https://learn.microsoft.com/rest/api/fabric/core/catalog/search
[b-relations]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/lineage-aware-ai-with-the-fabric-item-relations-api-preview/5366064
[l-lineage]: https://learn.microsoft.com/fabric/governance/lineage
[l-scan]: https://learn.microsoft.com/fabric/governance/metadata-scanning-overview
[l-whatsnew]: https://learn.microsoft.com/fabric/fundamentals/whats-new
[b-ignite-onelake]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/onelake-the-unified-foundation-for-data-context-governance-and-ai/5423035
[p1]: https://techcommunity.microsoft.com/blog/microsoft-security-blog/a-next-step-in-the-evolution-of-the-microsoft-data-governance-strategy/4572227
