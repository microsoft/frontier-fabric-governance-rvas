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

### 1.2 Domains, tenant settings and Fabric policies

| Capability | Status | What matters | Source |
|---|---|---|---|
| Domains and subdomains | GA | Names up to 40 characters, descriptions up to 256. Domain admins can't rename or delete a domain or manage its admins. Subdomains have no admins of their own. | [Learn][l-domains] |
| Assign workspaces to a domain by ID | GA | Fabric admin; service principals supported; 10 requests a minute. Overrides existing assignments unless a domain management tenant setting blocks bulk reassignment. | [REST][r-assignws] |
| Domains REST APIs, preview versions | Removed | The November 2026 feature summary says "Preview versions of Domains REST APIs are no longer available". The Learn reference carries no note. | [blog 2026-11-17][b-nov] |
| Domain default sensitivity label | Preview | Domain admins set a default label for new items in their domain when the tenant setting allows it. Update Domain sets it through `defaultLabelId`, with service principals supported. Items that deployment pipelines or Git integration create don't get it. | [Learn][l-domainlabel] |
| Tenant settings API | GA | List and update settings, including security-group scope and delegation to capacity, domain and workspace admins. Service principals supported; 25 requests a minute. | [REST][r-listsettings], [index][l-settingsindex] |
| Service principal tenant settings | GA | Current names: "Service principals can call Fabric public APIs", "Service principals can create workspaces, connections, and deployment pipelines", "Service principals can access read-only admin APIs" and "Service principals can access admin APIs used for updates". | [Developer][l-devsettings], [Admin API][l-adminapisettings] |
| Fabric policies | Preview | Allow-only rules for item creation and workspace settings at tenant or capacity scope. An action no rule allows is denied. One active policy per scope; up to 100 rules at tenant scope and 50 at capacity scope. Changes apply in about 15 minutes. Unavailable in West Europe, North Europe and West US. Not a replacement for Purview access-request workflows. External data sharing policies are "coming soon". | [Learn][l-policies] |
| Fabric policies REST APIs | Preview | Create policy sets and rules, activate a set at a scope, and evaluate an action. Users, service principals and managed identities. Policy items work with Git integration, but "you can't activate a policy through Git": a Fabric admin or capacity admin activates it by API. No operation-level reference yet. | [Learn][l-policiesrest] |
| Connection authentication and tenant allowlists | GA | Admins limit the authentication methods connections can use and keep an allowlist of up to 100 tenant IDs. | [What's new][l-whatsnew] |
| Cloud connection admin APIs | To verify | GA in What's new; Preview on the data source management page. | [What's new][l-whatsnew], [Learn][l-datasource] |
| Copilot in Power BI and Fabric settings | Dated change | On 2026-12-08 the standalone Copilot setting turns off by default and "Make Microsoft Copilot available in Power BI and Fabric" turns on. Standalone Power BI Copilot and App Copilot retire on 2027-01-15. The Learn page is labeled preview. | [Learn][l-copilot] |

[l-domains]: https://learn.microsoft.com/fabric/governance/domains
[r-assignws]: https://learn.microsoft.com/rest/api/fabric/admin/domains/assign-domain-workspaces-by-ids
[b-nov]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/fabric-november-2026-feature-summary/5414311
[l-domainlabel]: https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label
[r-listsettings]: https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-tenant-settings
[l-settingsindex]: https://learn.microsoft.com/fabric/admin/tenant-settings-index
[l-devsettings]: https://learn.microsoft.com/fabric/admin/service-admin-portal-developer
[l-adminapisettings]: https://learn.microsoft.com/fabric/admin/service-admin-portal-admin-api-settings
[l-policies]: https://learn.microsoft.com/fabric/governance/fabric-policies-overview
[l-policiesrest]: https://learn.microsoft.com/fabric/governance/fabric-policies-rest-api
[l-datasource]: https://learn.microsoft.com/fabric/data-factory/data-source-management
[l-copilot]: https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric

### 1.3 OneLake security and shortcuts

| Capability | Status | What matters | Source |
|---|---|---|---|
| OneLake security roles | GA for the members and data experience (September 2026) | Up to 250 roles per item, with 500 members and 500 permissions per role. | [Learn][l-olsec], [roles][l-olroles] |
| Data access roles API | GA; single-role calls Preview | `PUT .../dataAccessRoles?dryRun=true` validates a role set before it's applied. Needs Reshare permission and the OneLake.ReadWrite.All scope; service principals supported; 50 requests a minute. | [REST][r-roles] |
| Effective access for a principal | Preview | Returns what one principal can access in an item. Reflects role changes after about 5 minutes and group changes after about 1 hour. The hosted OneLake MCP server exposes it as `onelake_get_principal_access`. | [Learn][l-principal] |
| External engine integration | Preview | Lets non-Fabric engines read data with OneLake security applied. | [Learn][l-engines] |
| Dynamic and multi-table row-level security | Roadmap | Stated plan for Q1 2027. | [Roadmap][roadmap] |
| Shortcut authentication | GA; delegated mode Preview | Same-tenant shortcuts pass the caller's identity through by default; delegated mode is chosen when the shortcut is created. Cross-tenant shortcuts are delegated only. | [Learn][l-shortcutsec], [What's new][l-whatsnew] |
| OneLake SAS | GA | Valid for up to 1 hour, backed by an Entra identity, scoped to one item. | [Learn][l-sas] |
| OneLake table APIs | To verify | Preview on Learn; GA in the Ignite 2026 OneLake post. | [Learn][l-iceberg], [blog 2026-11-17][b-ignite-onelake] |
| OneLake diagnostics | GA | Access events reach a lakehouse within about 1 hour; logs can be made immutable. | [Learn][l-diag] |

[l-olsec]: https://learn.microsoft.com/fabric/onelake/security/get-started-security
[l-olroles]: https://learn.microsoft.com/fabric/onelake/security/create-manage-roles
[r-roles]: https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/create-or-update-data-access-roles
[l-principal]: https://learn.microsoft.com/fabric/onelake/security/authorized-access-for-principal-reference
[l-engines]: https://learn.microsoft.com/fabric/onelake/security/onelake-security-integrations-external-engines
[roadmap]: https://roadmap.fabric.microsoft.com/
[l-shortcutsec]: https://learn.microsoft.com/fabric/onelake/onelake-shortcut-security
[l-sas]: https://learn.microsoft.com/fabric/onelake/onelake-shared-access-signature-overview
[l-iceberg]: https://learn.microsoft.com/fabric/onelake/table-apis/iceberg-table-apis-overview
[l-diag]: https://learn.microsoft.com/fabric/onelake/onelake-diagnostics-overview

### 1.4 Labels, DLP and Purview

| Capability | Status | What matters | Source |
|---|---|---|---|
| Sensitivity labels and inheritance | GA | A more restrictive upstream label is inherited unless the downstream label was set manually. | [Learn][l-infoprot] |
| Default and mandatory label policies | GA | Set in Purview, or with `Set-LabelPolicy` in Security & Compliance PowerShell. A default label isn't applied to existing items. | [Learn][l-mandatory] |
| Bulk label APIs | GA | Fabric `bulkSetLabels` and `bulkRemoveLabels`, and the Power BI admin setLabels and removeLabels: user identities only, not service principals or managed identities. 25 calls an hour, up to 2,000 items a call. The `fab label` commands call the same endpoints. | [REST][r-labels], [Power BI][r-pbilabels] |
| Protection policies | GA | Only the users and groups a policy lists keep access to items with its label. | [Learn][l-protpol] |
| DLP for Fabric | GA | The restrict-access action has been GA since September 2026. | [Learn][l-dlp] |
| Purview audit and DSPM for AI | Audit GA; DSPM for AI Preview | Fabric activity appears in the Purview audit log. | [Learn][l-purview] |
| Labels and DLP in Copilot | No status stated | Labels, DLP policies and information protection controls now apply in Microsoft Copilot experiences. "Restrict from Copilot" lets admins choose which semantic models take part in AI experiences. | [blog 2026-09-28][b-fc3] |
| Conditional Access | GA | Needs Microsoft Entra ID P1. | [Learn][l-ca] |
| Purview Data Governance | Retiring | Purview Data Governance is retiring; support ends 12 November 2027. See section 4. | [Learn][p2], [Partner Center][p3] |

[l-infoprot]: https://learn.microsoft.com/fabric/governance/information-protection
[l-mandatory]: https://learn.microsoft.com/fabric/governance/mandatory-label-policy
[r-labels]: https://learn.microsoft.com/rest/api/fabric/admin/labels
[r-pbilabels]: https://learn.microsoft.com/rest/api/power-bi/admin/information-protection-set-labels-as-admin
[l-protpol]: https://learn.microsoft.com/fabric/governance/protection-policies-overview
[l-dlp]: https://learn.microsoft.com/fabric/governance/data-loss-prevention-overview
[l-purview]: https://learn.microsoft.com/fabric/governance/microsoft-purview-fabric
[l-ca]: https://learn.microsoft.com/fabric/security/security-conditional-access
[b-fc3]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/bringing-governed-analytics-into-the-flow-of-work-fabric-analytics-at-fabcon-eur/5368918
[p2]: https://learn.microsoft.com/purview/data-governance-overview
[p3]: https://learn.microsoft.com/partner-center/announcements/2026-november#update-on-the-microsoft-data-governance-strategy
