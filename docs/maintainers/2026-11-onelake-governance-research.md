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
| Third-party catalogs | Partner products; no Fabric status | The 2026-11-12 announcement names Atlan, Alation, Collibra and Informatica. The RVAS lists them in that order and doesn't compare them. | [Tech Community][p1] |

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

### 1.5 Network and data exfiltration

| Capability | Status | What matters | Source |
|---|---|---|---|
| Tenant Private Link | GA | With the tenant setting "Block Public Internet Access" on, Fabric is reachable only through private endpoints. The Govern tab, Fabric IQ plan items, the Capacity Metrics app, cross-tenant shortcuts and OneLake data sharing aren't supported. Publish to web, email subscriptions and PDF or PowerPoint export are limited. | [Learn][l-pl], [use][l-pluse] |
| Workspace Private Link | GA | F SKU capacities. One Private Link service per workspace; up to 100 private endpoints per workspace and 500 per tenant. Deployment pipelines and semantic models aren't supported. Denying public access can take 30 minutes to apply. SQL database and Eventstream support is Preview. | [Learn][l-wspl], [support][l-wsplsupport] |
| Workspace IP firewall | GA | Up to 256 rules, public IP addresses only. Applies only when the inbound default action is Deny. | [Learn][l-fw] |
| Trusted workspace access | GA | F SKUs only, not Trial capacities. Resource instance rules can only be created with ARM templates or PowerShell. | [Learn][l-twa] |
| Resource instance rules for OneLake | GA (2026-07-23) | Named Azure resource instances reach OneLake over the public endpoint, and data permissions still apply. Terraform `fabric_workspace_inbound_azure_resource_rules` arrived in provider v1.14.0. | [blog 2026-07-23][b-rir] |
| Workspace outbound access protection | GA for data engineering items and Eventhouse; Preview for event flows, Real-Time Intelligence items, Operations Agent and Maps | F SKUs only, in Fabric Data Engineering regions. Not compatible with external data sharing. OneLake diagnostics work only when the diagnostics lakehouse is in the same workspace. With private links on, set data connection rules through the Outbound Gateway Rules API. | [Learn][l-oap], [Eventhouse][l-oapeh] |
| OneLake outbound access protection | GA (September 2026) | Blocks external shortcuts and copy operations by default and allows approved connections. | [Learn][l-oaponelake] |
| Managed private endpoints | GA; Eventstream Preview | Let Spark and other supported items reach private Azure sources from a workspace. | [Learn][l-mpe] |
| Network communication policy APIs | GA; some inbound rule calls Preview | `GET` and `PUT /v1/workspaces/{ws}/networking/communicationPolicy`, service principals supported. A PUT replaces the whole policy, and an omitted `defaultAction` becomes Allow, so always send it. The admin call `GET /v1/admin/workspaces/networking/communicationpolicies` (GA since 2026-09-01) lists public access, firewall, outbound, gateway and Git rules and managed private endpoints for every workspace. | [REST][r-getnetpol], [admin][r-adminnetpol], [blog 2026-09-01][b-net] |
| External data sharing | GA | Provider and admin APIs list and revoke shares; service principals supported; 10 requests a minute. The provider's labels and DLP aren't enforced in the consumer tenant. Not supported over tenant Private Link. Attribute-based sharing policies are a roadmap plan. | [Learn][l-eds], [admin REST][r-edsadmin] |
| IQ Sharing (OneLake shares) | Preview | Shares a whole lakehouse or warehouse with another tenant without copying data; each share needs an expiration date. Not available in 12 regions. | [Learn][l-iqshare] |
| Workspace customer-managed keys | GA; APIs GA (2026-08-19) | Enable, inspect, rotate and turn off CMK per workspace. Terraform `fabric_workspace_encryption` (preview mode) arrived in v1.14.0. | [Learn][l-cmk], [blog 2026-08-19][b-cmk] |
| Workspace identity | GA | An Entra identity owned by the workspace. Trusted workspace access and identity-based shortcuts use it. | [Learn][l-wsid] |
| Spark FQDN allowlist for outbound-protected workspaces | To verify | Announced on 2026-09-28 as "available in the coming weeks". Learn still says allowlists use managed private endpoints only. | [blog 2026-09-28][b-fc1] |

[l-pl]: https://learn.microsoft.com/fabric/security/security-private-links-overview
[l-pluse]: https://learn.microsoft.com/fabric/security/security-private-links-use
[l-wspl]: https://learn.microsoft.com/fabric/security/security-workspace-level-private-links-overview
[l-wsplsupport]: https://learn.microsoft.com/fabric/security/security-workspace-level-private-links-support
[l-fw]: https://learn.microsoft.com/fabric/security/security-workspace-level-firewall-overview
[l-twa]: https://learn.microsoft.com/fabric/security/security-trusted-workspace-access
[b-rir]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/simplify-onelake-network-security-for-azure-services-with-resource-instance-rule/5284830
[l-oap]: https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview
[l-oapeh]: https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-eventhouse
[l-oaponelake]: https://learn.microsoft.com/fabric/onelake/onelake-manage-outbound-access
[l-mpe]: https://learn.microsoft.com/fabric/security/security-managed-private-endpoints-overview
[r-getnetpol]: https://learn.microsoft.com/rest/api/fabric/core/workspaces/get-network-communication-policy
[r-adminnetpol]: https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-networking-communication-policies
[b-net]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/get-tenant-wide-visibility-into-workspace-networking-policies-with-the-admin-api/5361690
[l-eds]: https://learn.microsoft.com/fabric/governance/external-data-sharing-overview
[r-edsadmin]: https://learn.microsoft.com/rest/api/fabric/admin/external-data-shares-provider/list-external-data-shares
[l-iqshare]: https://learn.microsoft.com/fabric/onelake/iq-share/onelake-share-overview
[l-cmk]: https://learn.microsoft.com/fabric/security/workspace-customer-managed-keys
[b-cmk]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/customer-managed-key-cmk-apis-for-microsoft-fabric-workspaces-generally-availabl/5360035
[l-wsid]: https://learn.microsoft.com/fabric/security/workspace-identity
[b-fc1]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/build-deploy-and-govern-microsoft-fabric-at-scale/5369145

### 1.6 Monitoring and capacity

| Capability | Status | What matters | Source |
|---|---|---|---|
| Workspace monitoring | Preview | A monitoring item collects logs and metrics into an Eventhouse for KQL queries, with 30-day default retention. Needs the tenant setting "Workspace admins can turn on monitoring for their workspaces (preview)"; data collection is off when the item is created. The monitoring item REST APIs are Preview and accept service principals. | [Learn][l-wsmon], [REST][r-monitoring] |
| Admin monitoring workspace | Preview | A read-only workspace whose admin semantic models refresh daily. Not available with Private Link; access comes from direct workspace roles only. No API for its data. | [Learn][l-adminmon] |
| Feature usage and adoption report | Preview | Learn says this report won't become GA. | [Learn][l-fua] |
| Capacity Metrics app | To verify | GA in What's new; its own page still says preview. Item history (30 days) is Preview. No API for its data. | [Learn][l-metrics], [What's new][l-whatsnew] |
| Chargeback app | No status label found | Shows capacity usage by workspace, item, and domain or subdomain. Chargeback by tag is a roadmap plan. No API for its data. | [Learn][l-chargeback] |
| Surge protection | Workspace level GA (November 2026); email notifications Preview | Capacity admins cap, block, exempt and restore workspaces. REST: `GET` and `PATCH /v1/capacities/{id}/surgeProtection`, plus blocked and mission-critical actor endpoints. | [Learn][l-surge], [REST][r-surge] |
| Capacity events in Real-Time hub | Overview events GA (2026-08-12); operation events Preview (2026-09-03) | Stream capacity state and operation events to Eventstream and Activator for alerts. | [blog 2026-08-12][b-capov], [blog 2026-09-03][b-capop] |

[l-wsmon]: https://learn.microsoft.com/fabric/fundamentals/workspace-monitoring-overview
[r-monitoring]: https://learn.microsoft.com/rest/api/fabric/monitoring/items
[l-adminmon]: https://learn.microsoft.com/fabric/admin/monitoring-workspace
[l-fua]: https://learn.microsoft.com/fabric/admin/feature-usage-adoption
[l-metrics]: https://learn.microsoft.com/fabric/enterprise/metrics-app
[l-chargeback]: https://learn.microsoft.com/fabric/enterprise/chargeback-app
[l-surge]: https://learn.microsoft.com/fabric/enterprise/surge-protection
[r-surge]: https://learn.microsoft.com/rest/api/fabric/core/surge-protection
[b-capov]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/capacity-overview-events-in-real-time-hub-generally-available/5356729
[b-capop]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/capacity-operation-events-in-real-time-hub-preview/5364092

## 2. Fabric news, July to November 2026

This section keeps the platform-governance items from the [July][b-jul], [August][b-aug], [September][b-sep] and [November][b-nov] feature summaries, the FabCon Europe 2026 and Ignite 2026 posts, the 2026-11-12 data governance post and [What's new in Microsoft Fabric][l-whatsnew].

- The Posted column gives the post date, or the What's new month when there is no post. Event dates aren't used.
- Open-source tools show a release instead of a status.
- The Affects column lists existing challenges 00–08 and the proposed challenges: 09 catalog metadata, 10 OneLake security, 11 network and exfiltration, 12 tenant settings and policies, 13 Purview Data Governance transition.

### 2.1 OneLake catalog and metadata

| Item | Status | Posted | Source | Affects |
|---|---|---|---|---|
| Govern tab with governance insights and recommended actions | GA; its Policies Center is Preview | 2026-10-28 | [blog][b-govern] | 03, 07, 09, 12 |
| Govern, curation and protection skills for the catalog | To verify: the roadmap lists Govern skills as shipped; the posts give no label | 2026-10-28, 2026-11-17 | [blog][b-govern], [Ignite][b-ignite-onelake] | 06, 09 |
| Catalog search API, MCP tool and `fab find` | Preview | 2026-05-01, before the window; still Preview in November | [blog][b-srch], [REST][r-search] | 00, 09 |
| Table discovery in catalog search | Preview | 2026-09-09 | [blog][b-tbl] | 04, 09 |
| Granular exploration: tables, columns, data preview and quick actions | To verify: the FabCon posts read as GA; the roadmap plans it for Q3 | 2026-09-28 | [FabCon OneLake][b-fc2], [roadmap][roadmap] | 09 |
| Catalog mirroring and federation: AWS Glue, Azure Monitor, Dremio, Google lakehouse runtime catalog | To verify: Preview on Learn and in the July and August posts; the Ignite post lists GA | 2026-07-30, 2026-08-24, 2026-11-17 | [Azure Monitor and AWS Glue][b-azm], [Google][b-glr], [Ignite][b-ignite-onelake] | 04, 09 |
| Catalog in Excel, Teams, Foundry and Copilot Studio | Excel Preview; the others to verify | 2026-09-28 to 2026-11-17 | [FabCon OneLake][b-fc2], [Ignite][b-ignite-onelake] | 09, 13 |
| Third-party catalogs: Atlan, Alation, Collibra, Informatica | Partner products; no Fabric status | 2026-11-12 | [Tech Community][p1] | 09, 13 |
| Item relations API | Beta on Learn, Preview in the post | 2026-09-10 | [blog][b-relations] | 02, 08, 09 |
| Materialized lake view data-quality constraints | To verify: the constraints carry no label; materialized lake views are GA | Page updated 2026-11-09 | [Learn][l-mlvdq] | 05, 09 |
| Plans for data quality, glossary, granular lineage and guardrail policies | Roadmap | 2026-09-28, 2026-11-17 | [FabCon OneLake][b-fc2], [Ignite][b-ignite-onelake] | 09, 13 |

### 2.2 Tenant controls, domains and policies

| Item | Status | Posted | Source | Affects |
|---|---|---|---|---|
| Fabric policies: allow-only rules for item creation and workspace settings | Preview | 2026-09-28 | [September summary][b-sep], [Learn][l-policies] | 03, 04, 12 |
| Policy REST APIs, audit events and Git support | Preview. Rule definitions can live in Git, but Learn says a policy can't be activated through Git. | 2026-09-28 | [September summary][b-sep], [REST][l-policiesrest] | 01, 07, 12 |
| Connection authentication allowlist and tenant allowlist | GA | 2026-09-28 | [September summary][b-sep] | 00, 12 |
| Admin APIs for cloud connections | To verify: GA in What's new and the September summary; Preview on Learn and in the October gateway post | 2026-09-28, 2026-10-27 | [September summary][b-sep], [gateway post][b-gw], [Learn][l-dsm] | 00, 04, 12 |
| On-premises data gateway soft delete | Preview | 2026-09-17 | [blog][b-gwsd] | 11, 12 |
| Centralized app governance in the OneLake governance hub | To verify: no label | 2026-11-17 | [November summary][b-nov] | 09, 12 |
| Anonymous data access for Fabric apps | Preview | 2026-08-25 | [blog][b-apps-anon] | 04, 12 |
| Domains REST APIs: preview versions removed | Change notice | 2026-11-17 | [November summary][b-nov], [REST][r-domains] | 03 |
| Copilot in Power BI: the standalone setting turns off by default on 2026-12-08, and standalone Copilot retires on 2027-01-15 | Dated change | Learn, undated | [Learn][l-copilot] | 00, 06, 12 |

[b-jul]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/fabric-july-2026-feature-summary/5325823
[b-aug]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/fabric-august-2026-feature-summary/5325824
[b-sep]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/fabric-september-2026-feature-summary/5325825
[b-srch]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/discover-items-across-workspaces-with-the-onelake-catalog-search-api-mcp-and-cli/5176768
[b-tbl]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/get-ready-for-table-discovery-in-onelake-catalog-search-preview/5365764
[b-fc2]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/fabcon-and-sqlcon-barcelona-2026-what%e2%80%99s-new-in-microsoft-onelake-and-its-rapidly/5369146
[b-azm]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/bring-your-azure-monitor-and-aws-glue-data-to-onelake-preview/5326474
[b-glr]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/bring-your-google-lakehouse-runtime-catalog-data-to-onelake-preview/5360492
[l-mlvdq]: https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/data-quality
[b-gw]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/on-premises-data-gateway-october-2026-release/5376557
[b-gwsd]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/soft-delete-for-on-premises-data-gateways-in-microsoft-fabric-preview/5365712
[l-dsm]: https://learn.microsoft.com/fabric/data-factory/data-source-management
[b-apps-anon]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/introducing-anonymous-data-access-for-fabric-apps-preview/5361116
[r-domains]: https://learn.microsoft.com/rest/api/fabric/admin/domains

### 2.3 OneLake security, identity and Git permissions

| Item | Status | Posted | Source | Affects |
|---|---|---|---|---|
| OneLake security: Members and Data user experience | GA | September 2026 (What's new) | [Learn][l-olroles] | 04, 05, 10 |
| OneLake security with third-party engines | Preview | Learn, undated | [Learn][l-engines] | 04, 10 |
| Dynamic and multi-table row-level security; BigQuery security-role replication | Roadmap, planned for Q1 2027 | Roadmap | [roadmap][roadmap] | 04, 10 |
| Delegated OneLake shortcuts | Preview | 2026-07-02 | [blog][b-dlg] | 04, 10, 11 |
| Snowflake security-role mirroring | Preview | What's new, month not given | [What's new][l-whatsnew] | 04, 10 |
| Granular sharing of Eventhouse shortcut databases | GA | September 2026 (What's new) | [What's new][l-whatsnew] | 04 |
| OneLake table APIs: read, Iceberg REST and credential vending | To verify: Preview on Learn; the Ignite post lists GA | 2026-11-17 | [Learn][l-tblread], [Ignite][b-ignite-onelake] | 04, 05, 09 |
| COPY INTO with workspace identity (Warehouse) | GA | 2026-08-26 | [August summary][b-aug] | 04, 05 |
| Eventstream connections to Event Hubs with workspace identity | Preview | 2026-08-20 | [blog][b-eh-wi] | 04, 11 |
| Associate an identity with items | Beta | Learn, undated | [REST][r-assoc] | 02, 04, 12 |
| Git integration and deployment pipelines need read-write permission on items | Dated change. Learn says from 2027-02-28; the August summary said 2026-12-01. | 2026-08-26 | [August summary][b-aug], [Learn][l-git] | 01, 02, 03, 04, 08 |

[b-dlg]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/simplifying-secure-data-access-with-delegated-onelake-shortcuts-preview/5254632
[l-tblread]: https://learn.microsoft.com/fabric/onelake/table-apis/read-table-data-rest-api
[b-eh-wi]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/secure-azure-event-hubs-connections-in-eventstream-with-workspace-identity-previ/5359945
[r-assoc]: https://learn.microsoft.com/rest/api/fabric/articles/item-management/associate-item-identity
[l-git]: https://learn.microsoft.com/fabric/cicd/git-integration/git-integration-process

### 2.4 Purview and information protection

| Item | Status | Posted | Source | Affects |
|---|---|---|---|---|
| Purview Data Governance is retiring; support ends 12 November 2027 | Announcement. Purview remains the security and compliance layer. | 2026-11-12 | [Tech Community][p1], [Partner Center][p3] | 03, 13, capstone |
| Transition guidance from Purview Data Governance to the OneLake catalog | Guidance | 2026-11-13, updated 2026-11-16 | [Tech Community][p4] | 09, 13 |
| DLP policies that restrict access to Fabric items | GA; in Preview since 2026-03-23 | September 2026 (What's new) | [Learn][l-dlp], [March post][b-mar] | 03, 04 |
| DSPM for AI for Fabric Copilots and data agents | Preview | 2026-03-23, before the window | [March post][b-mar], [Learn][l-dspm] | 06, 07 |
| Domain default sensitivity label | Preview; no change in the window | Learn, 2024-11-11 | [Learn][l-domainlabel] | 03 |
| Labels and DLP applied in Copilot; Restrict from Copilot | To verify: no label | 2026-09-28 | [FabCon analytics][b-fc3] | 03, 06 |

### 2.5 Network, monitoring and capacity

Sections 1.5 and 1.6 give the limits. This table gives the dates.

| Item | Status | Posted | Source | Affects |
|---|---|---|---|---|
| Resource instance rules for OneLake | GA | 2026-07-23 | [blog][b-rir] | 01, 04, 11 |
| OneLake outbound access protection | GA | September 2026 (What's new) | [Learn][l-oaponelake] | 04, 11 |
| Workspace outbound access protection for event flows, Real-Time Intelligence items, Operations Agent and Maps | Preview | 2026-06-29, 2026-07-02, 2026-09-03 | [event flows][b-oap-ef], [Real-Time Intelligence][b-oap-rti], [Operations Agent and Maps][b-oap-ops] | 11 |
| Eventhouse outbound access protection, workspace Private Link and CMK | GA | September 2026 (What's new); restated 2026-11-17 | [Learn][l-oapeh], [Ignite][b-ig-rti] | 11 |
| Eventstream and SQL database workspace Private Link | Preview | What's new, month not given | [What's new][l-whatsnew] | 11 |
| Spark FQDN allowlist for outbound-protected workspaces | To verify: announced as "available in the coming weeks"; not on Learn | 2026-09-28 | [blog][b-fc1] | 11 |
| Admin API for workspace networking policies | GA | 2026-09-01 | [blog][b-net] | 07, 11, 12 |
| Workspace CMK APIs | GA | 2026-08-19 | [blog][b-cmk] | 01, 03, 11 |
| Policy-based external data sharing | Roadmap ("coming soon") | 2026-09-28 | [FabCon OneLake][b-fc2] | 11, 12 |
| Workspace monitoring | Preview | Coverage added September to November 2026 | [Learn][l-wsmon] | 07 |
| Workspace-level surge protection | GA; the 2026-09-28 post said it was coming | November 2026 (What's new) | [Learn][l-surge] | 03, 07 |
| Capacity events in Real-Time hub | Overview events GA; operation events Preview | 2026-08-12, 2026-09-03 | [overview][b-capov], [operations][b-capop] | 07 |
| SQL audit log improvements | GA | 2026-08-26 | [August summary][b-aug] | 07 |
| Capacity Metrics app enhancements | To verify: GA in What's new; preview on the app's page | September 2026 (What's new) | [Learn][l-metrics] | 03, 07 |

[p4]: https://techcommunity.microsoft.com/blog/analyticsonazure/from-purview-data-governance-to-the-fabric-onelake-catalog/4573422
[b-mar]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/new-data-protection-capabilities-in-microsoft-fabric-native-security-for-the-mod/5172177
[l-dspm]: https://learn.microsoft.com/purview/ai-copilot-fabric
[b-oap-ef]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/secure-azure-and-fabric-event-flows-across-workspaces-with-outbound-access-prote/5240305
[b-oap-rti]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/workspace-outbound-access-protection-oap-for-real-time-intelligence-preview/5241179
[b-oap-ops]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/workspace-outbound-access-protection-oap-for-operations-agent-and-fabric-maps-pr/5363817
[b-ig-rti]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/run-proactive-operations-with-real-time-intelligence-in-microsoft-fabric/5414256

### 2.6 Git, CI/CD and automation tooling

| Item | Status | Posted | Source | Affects |
|---|---|---|---|---|
| Branched workspaces, selective branching, compare and commit, bulk item definition APIs | GA | September 2026 (What's new) | [Learn][l-branch] | 01, 02, 08 |
| Deployment plans | Preview | What's new; the roadmap says shipped in Q4 | [What's new][l-whatsnew] | 08 |
| Fabric Core remote MCP server | GA | September 2026 (What's new) | [Learn][l-mcpcore] | 00, 04, 12 |
| Hosted OneLake MCP server | Preview | Page dated 2026-10-22 | [Learn][l-mcpol] | 00, 04, 06, 10 |
| Local Fabric MCP server | No status label; v1.8.0 | 2026-11-11 | [Learn][l-mcplocal] | 00 |
| Skills for Fabric | Released. Governance skills arrived between v0.3.15 and v0.3.22; `fabric-policies-cli` arrived in v0.3.22 (2026-11-18). Latest: v0.3.23. | 2026-09-06 to 2026-11-20 | [GitHub][gh-skills] | 00, 09, 12 |
| Terraform provider for Fabric | Released. v1.14.0 added inbound resource rules and workspace encryption. Latest: v1.15.1, with 71 resources. | 2026-07-08 to 2026-11-11 | [GitHub][gh-tf], [Registry][tf-registry] | 01, 02, 11 |
| fabric-cicd | Released. Latest: v1.4.0. What's new lists bulk publish mode as Preview. | 2026-06-30 to 2026-10-07 | [GitHub][gh-cicd] | 01, 02, 08 |
| Fabric CLI | Released. Latest: v1.9.0. | 2026-08-19 to 2026-11-04 | [GitHub][gh-cli] | 00, 01, 02 |

### 2.7 Data agents and Fabric IQ

| Item | Status | Posted | Source | Affects |
|---|---|---|---|---|
| Data agent observability | To verify: no overall label; the user-feedback view is Preview | 2026-11-17 | [November summary][b-nov], [Ignite IQ][b-ig-iq] | 06, 07 |
| Data agents in Microsoft Agent 365 | Preview | 2026-11-17 | [Ignite IQ][b-ig-iq] | 06, 12 |
| Service principal support for data agents | Preview | 2026-05-13, before the window | [blog][b-spn-da] | 04, 06 |
| Data agents in Copilot Studio | GA | 2026-09-02 | [blog][b-da-cs] | 06 |
| Fabric IQ MCP server | GA | September 2026 (What's new) | [What's new][l-whatsnew] | 06 |
| Ontology | Preview | 2026-11-17 | [Ignite IQ][b-ig-iq] | 06, 12 |

[l-branch]: https://learn.microsoft.com/fabric/cicd/git-integration/branched-workspace
[l-mcpcore]: https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server
[l-mcpol]: https://learn.microsoft.com/fabric/onelake/onelake-hosted-mcp
[l-mcplocal]: https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/pro-dev-local/overview-local-mcp-server
[gh-skills]: https://github.com/microsoft/skills-for-fabric/releases
[gh-tf]: https://github.com/microsoft/terraform-provider-fabric/releases
[tf-registry]: https://registry.terraform.io/providers/microsoft/fabric/latest/docs
[gh-cicd]: https://github.com/microsoft/fabric-cicd/releases
[gh-cli]: https://github.com/microsoft/fabric-cli/releases
[b-ig-iq]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/bringing-trusted-fabric-iq-context-to-wherever-people-and-agents-work/5423049
[b-spn-da]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/service-principal-support-for-data-agents-in-fabric-preview/5181634
[b-da-cs]: https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/fabric-data-agents-in-microsoft-copilot-studio-generally-available/5362882

### 2.8 Status conflicts

Where sources disagree, this report uses the status in the last column. Phase 2 should recheck these before a challenge depends on them.

| ID | Item | What the sources say | Status used |
|---|---|---|---|
| X1 | Govern tab | What's new has a Preview row and a GA row. The post and the roadmap say GA. | GA |
| X2 | Read-write rule for Git and deployment pipelines | The August summary says 2026-12-01. The Git and deployment pipeline pages say 2027-02-28. | 2027-02-28 |
| X3 | Resource instance rules for OneLake | GA in the post and What's new. The roadmap still plans GA for Q3. | GA |
| X4 | Table discovery in catalog search | The post title says Preview; the roadmap plans Preview for Q4. Timing only. | Preview |
| X5 | Catalog mirroring and federation | Preview on Learn and in the July and August posts. GA in the Ignite post. | Preview |
| X6 | Admin APIs for cloud connections | GA in What's new and the September summary. Preview on Learn, in the October gateway post and on the roadmap. | Preview |
| X7 | Associate an identity with items | Beta on Learn. The roadmap plans Preview for Q4 2026. | Beta |
| X8 | Gateway soft delete | Preview in the post and What's new. The roadmap says GA, shipped. | Preview |
| X9 | COPY INTO with workspace identity | GA in the August summary and What's new. Preview on the roadmap. | GA |
| X10 | Granular catalog exploration | The FabCon posts read as GA. The roadmap plans it for Q3. | To verify |
| X11 | Capacity Metrics app | GA in What's new. The app's page and the roadmap say preview. | To verify |
| X12 | OneLake table APIs | Preview on Learn and What's new. GA in the Ignite post. | Preview |
| X13 | Fabric policies and Git | The September summary says rule definitions support Git. Learn says a policy can't be activated through Git. Both hold: keep definitions in Git and activate through the API. | Preview |
| X14 | fabric-cicd bulk publish | Preview in What's new. "Production ready" in the September summary. | Preview |
| X15 | Catalog discovery through Skills for Fabric in GitHub Copilot CLI | GA in the FabCon post. The roadmap plans GA for Q4. Timing only. | GA |
| X16 | Data agents in Microsoft Agent 365 | Preview in the Ignite post. The roadmap plans Preview for Q4. Timing only. | Preview |
| X17 | Workspace tags | Learn's tags pages show no preview label. The workspace apply and unapply tags APIs are Preview, and the `onelake-catalog-cli` skill treats workspace tags as preview. | Preview for automation |
| X18 | Protection policies | Learn's overview page shows no preview label. This report's automation research recorded them as Preview. | GA, to recheck |
| X19 | Surge protection REST API | Learn has a REST reference for `surgeProtection` without a preview banner. The news posts don't mention an API. | To verify |
| X20 | Policy-based external data sharing | The FabCon post says "coming soon". A Fabric policy rule for external data sharing may already be listed as Preview; this wasn't confirmed. | Roadmap, to verify |

## 3. Automation surface

The RVAS teaches governance as code, so a challenge can only teach what a pipeline can drive or verify. For each capability, this section gives the REST API and whether a service principal can call it, the Terraform resource, the Fabric CLI command, the MCP tools and the Skills for Fabric skill.

- Versions checked 2026-11-27: Terraform provider v1.15.1, Fabric CLI v1.9.0, local Fabric MCP server v1.8.0, Skills for Fabric v0.3.23.
- SPN means service principal and MI managed identity. Core MCP is the Fabric Core remote MCP server ([tools][l-mcptools]). Local MCP is the local Fabric MCP server ([README][gh-mcp]).
- **UI-only** means no public API was found on Learn on 2026-11-27. The row says how a challenge can still verify the capability.

### 3.1 Catalog, metadata and tenant controls

| Capability | REST API, status and identity | Terraform | Fabric CLI | MCP | Skill |
|---|---|---|---|---|---|
| Catalog search | Core [Catalog Search][r-search], Preview. SPN and MI; 50 calls a minute. Results carry no endorsement, tag or label fields. | None | `fab find` | Core `search_catalog`; local `core_search-catalog` | `search-consumption-cli`, `onelake-catalog-cli` |
| Govern tab insights and recommended actions | **UI-only.** Insights come from the admin monitoring workspace, which has no API. | None | None | None | `onelake-catalog-cli` runs similar audits from REST; it doesn't read Govern data |
| Item and workspace descriptions | Core [Update Item][r-updateitem], GA. SPN and MI where the item type supports them. | `description` on item resources and on `fabric_workspace` | `fab set` with `-q description` | Core `update_item`, `update_workspace` | `onelake-catalog-cli` |
| Tags | Admin [Tags][r-tags], GA: bulk create, update, delete. Item [Apply Tags][r-applytags], GA. Workspace apply and unapply tags, Preview. SPN and MI. | `fabric_tag`; 40 item resources accept `tags`. No workspace tags. | `fab api` | None; local `core_get-workspace` reads workspace tags | `onelake-catalog-cli` |
| Endorsement | **UI-only to set.** Read it from the [scanner][l-scan] result (`endorsementDetails`). | None | None | None | `onelake-catalog-cli` reads it from the scanner |
| Table and column metadata | OneLake table API `additionalMetadata` ([Learn][l-tablemeta]), Preview. Storage token audience. A POST replaces all metadata. | None | None | Local OneLake table tools are read-only | `onelake-catalog-cli` |
| Item relations (lineage) | Core [Items][r-items] upstream and downstream relations, Beta. SPN and MI. | None | None | None | None |
| Metadata scanning | Power BI admin [scanner][l-scan]: modified, getInfo, scanStatus, scanResult. SPN with the read-only admin API settings. | None | `fab api -A powerbi` | None | `onelake-catalog-cli` uses it for labels and endorsement |
| Domains | Admin [Domains][r-domains], GA: create, update (including `defaultLabelId`), assign workspaces, roles. SPN and MI. **UI-only:** delegated domain settings and default-domain auto-assignment. | `fabric_domain`, `fabric_domain_role_assignments`, `fabric_domain_workspace_assignments` (preview) | `.Domain` virtual item with `mkdir`, `set`, `assign` | None; local `core_create-workspace` takes a domain | `onelake-catalog-cli` |
| Tenant settings and delegated overrides | Admin [Tenants][r-tenants], GA: list and update settings and capacity overrides. Domain and workspace overrides are list-only. SPN and MI. | `fabric_tenant_setting` (not preview) | `fab api` | None | None |
| Fabric policies (policy sets) | Core and admin [policy sets][r-policysets], Preview. Rules need `beta=true`; one active set per scope. SPN and MI. | None | `fab api` | None | `fabric-policies-cli` |

[l-mcptools]: https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server
[gh-mcp]: https://github.com/microsoft/mcp/blob/main/servers/Fabric.Mcp.Server/README.md
[r-tags]: https://learn.microsoft.com/rest/api/fabric/admin/tags
[r-items]: https://learn.microsoft.com/rest/api/fabric/core/items
[r-tenants]: https://learn.microsoft.com/rest/api/fabric/admin/tenants
[r-policysets]: https://learn.microsoft.com/rest/api/fabric/admin/policy-sets

### 3.2 Security, network and operations

| Capability | REST API, status and identity | Terraform | Fabric CLI | MCP | Skill |
|---|---|---|---|---|---|
| Workspace roles and workspace identity | Core role assignments and workspace identity, GA. SPN and MI. Admin access reports, Preview. **UI-only:** item-level sharing grants. | `fabric_workspace_role_assignment`; `identity` on `fabric_workspace` | `fab acl` | Core `list_workspace_roles` and the other role tools | None |
| OneLake security data access roles | Core [bulk create or update][r-roles] with `dryRun` and an ETag; it replaces every role. Single-role calls need `preview=true`. Principal access records, Preview. SPN and MI. | `fabric_onelake_data_access_security` (preview) | `fab api` | Core `onelake_create_or_update_data_access_roles` and three more role tools. Hosted OneLake MCP `onelake_get_principal_access` (Preview) can report `canRead: false` for a principal who can read, so don't use it as an access gate. | None |
| Shortcuts | Core [Shortcuts][r-shortcuts], GA. SPN and MI. The authentication mode isn't in the REST contract. | `fabric_shortcut` | `fab ln` | Core `onelake_create_shortcut` and five more shortcut tools | None |
| Sensitivity labels on items | Admin [bulk set and remove][r-labels], GA, and the [Power BI equivalent][r-pbilabels]: **user only**, no SPN or MI. For a pipeline, set a domain's `defaultLabelId` or the label policy settings instead. | `default_label_id` on `fabric_domain` only | `fab label` (Fabric admin user) | Local `core_create-item` can set a label at creation | `onelake-catalog-cli` |
| DLP | No REST API. Security & Compliance PowerShell [New-DlpCompliancePolicy][r-dlpps] with `-PowerBIDlpLocation`; app-only certificate authentication. | None | None | None | None |
| Protection policies, Insider Risk, DSPM for AI | **UI-only** (Purview portal) | None | None | None | None |
| Audit | Power BI [activity events][r-activity]: SPN; one UTC day per call; last 28 days. Also Microsoft Graph audit log queries and `Search-UnifiedAuditLog`. | None | `fab api -A powerbi` | None | None |
| Workspace network controls | Core communication policy ([Get][r-getnetpol]), GA. A PUT replaces the whole policy, and an omitted `defaultAction` becomes Allow. Inbound firewall and Azure resource rules, Preview. Admin [network policies list][r-adminnetpol], GA. SPN and MI. Private Link resources are Azure Resource Manager resources. | `fabric_workspace_network_communication_policy`, `fabric_workspace_firewall_rules`, `fabric_workspace_inbound_azure_resource_rules`, `fabric_workspace_outbound_cloud_connection_rules`, `fabric_workspace_outbound_gateway_rules`, `fabric_workspace_git_outbound_policy`, `fabric_workspace_managed_private_endpoint` | `.ManagedPrivateEndpoint`; `fab api` | Core `onelake_get_settings`, `onelake_modify_diagnostics` | None |
| External data sharing | Core [provider][r-eds] create, list and revoke; admin [list][r-edsadmin] and revoke; GA. SPN and MI. IQ Sharing, Preview. | `fabric_external_data_share` | `.ExternalDataShare` | None | `fabric-policies-cli` (sharing rule) |
| Workspace customer-managed keys | Core assign workspace encryption, GA | `fabric_workspace_encryption` (preview) | `fab api` | None | None |
| Monitoring | Monitoring items ([REST][r-monitoring]), Preview. SPN and MI. **UI-only:** admin monitoring workspace, Capacity Metrics and Chargeback. | None | None | None | `sqldw-cli` and `databasehub-cli`, in part |
| Capacities and surge protection | Core list capacities and assign workspace to capacity, GA. [Surge protection][r-surge] GET and PATCH, no preview banner. Azure Resource Manager `Microsoft.Fabric/capacities`. | azurerm `azurerm_fabric_capacity` | `.Capacity`; `fab assign` | Core `list_capacities`; local `core_assign-workspace-to-capacity` | None |
| Git integration and deployment pipelines | Core [Git][r-git]: an SPN can connect only with a configured connection. Branching API and admin Git connections list, Preview. [Deployment pipelines][r-dp]: up to 300 items per deploy; deployment plans Preview. | `fabric_workspace_git`, `fabric_deployment_pipeline` | `fab deploy`, `fab import`, `fab export` | Item definition tools only | `git-integration-operations-cli`, `deployment-pipelines-authoring-cli` |
| Data agents and ontology | [Data agent items][r-dataagent]: create and definition. Staging and publish, Preview. Ontology, Preview. SPN and MI. | `fabric_data_agent`; `fabric_ontology` (preview) | `.Ontology` | [Fabric IQ MCP][l-iqmcp], GA, read-only, no SPN | `fabriciq`, `ontology-cli` |
| Materialized lake view data-quality constraints | Spark SQL `CONSTRAINT … CHECK … ON MISMATCH DROP` or `FAIL`. The [MLV REST API][r-mlv] schedules runs. SPN and MI. | None | `fab job` | Local `jobs_run-on-demand-item-job` | `spark-cli` |

[r-shortcuts]: https://learn.microsoft.com/rest/api/fabric/core/onelake-shortcuts
[r-dlpps]: https://learn.microsoft.com/powershell/module/exchangepowershell/new-dlpcompliancepolicy
[r-activity]: https://learn.microsoft.com/rest/api/power-bi/admin/get-activity-events
[r-eds]: https://learn.microsoft.com/rest/api/fabric/core/external-data-shares-provider
[r-git]: https://learn.microsoft.com/rest/api/fabric/core/git
[r-dp]: https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines
[r-dataagent]: https://learn.microsoft.com/rest/api/fabric/dataagent/items
[l-iqmcp]: https://learn.microsoft.com/fabric/iq/connectors/fabric-iq-mcp
[r-mlv]: https://learn.microsoft.com/rest/api/fabric/lakehouse/materialized-lake-views

### 3.3 Limits that shape the challenges

1. **Labels from a pipeline.** The bulk label APIs and `fab label` need a Fabric admin user. A pipeline that runs as a service principal can set a domain's default label, or manage label policy settings with `Set-LabelPolicy`. Otherwise keep one manual admin step. Read labels with Get Item or the scanner.
2. **Endorsement.** A challenge can audit endorsement through the scanner and control who can certify through tenant settings. Setting endorsement stays in the UI.
3. **OneLake security.** Use the bulk PUT with `dryRun` and an ETag in a pipeline step. The Terraform resource and Git tracking are Preview. Entra members of roles don't travel through Git or fabric-cicd, and they carry across workspaces only when role names match.
4. **Preview switches.** Terraform needs `preview = true` for 15 resources. Single-role OneLake security calls need `preview=true`, and policy rules need `beta=true`.
5. **MCP coverage.** The Core MCP covers catalog search, workspaces, items, workspace roles, shortcuts, OneLake data access roles and OneLake settings. No MCP server covers tags, domains, tenant settings, labels, admin APIs, external data shares, networking, Git or policies, so those need REST, Terraform or `fab api`.
6. **Policy sets.** They're Preview and have no Terraform resource. Each scope has one active set, and Git can't activate one. Learn's pages disagree on how a policy set is created.
7. **Purview.** Protection policies, Insider Risk and DSPM for AI have no code path. DLP works through PowerShell with app-only certificate authentication; Learn doesn't say whether workload identity federation works.
8. **Identity setup.** Admin APIs need the admin API tenant settings and a security-group allow-list. Learn names the Fabric API setting two ways: "Service principals can use Fabric APIs" on the identity support page, and "Service principals can call Fabric public APIs" plus "Service principals can create workspaces, connections, and deployment pipelines" on the developer settings page. For the scanner and `fabric_domain`, the app registration must not hold Power BI permissions that need admin consent.
9. **Fabric IQ MCP.** It has no service principal or app-only support, so a pipeline can't call it.
10. **Git permissions.** From 2027-02-28, a user needs read-write permission on workspace items to use Git integration and deployment pipelines.

## 4. Purview Data Governance transition

Purview Data Governance is retiring; support ends 12 November 2027 ([Tech Community, 2026-11-12][p1]; [Partner Center][p3]). The retirement covers the Unified Catalog, Data Map, Workflows and the classic Azure Purview solutions. Existing capabilities stay in maintenance mode until then. The Learn banner says new data governance accounts can no longer be created, and gives no date for that change ([Learn][p2]).

Purview remains the security and compliance layer: Information Protection, DLP, Insider Risk Management and DSPM aren't affected ([Learn][p2]). Only sensitivity labels, protection policies and DLP need Purview licensing; everything else works with a Fabric license ([Learn][l-getstarted]). Metadata scanning needs no special license ([Learn][l-scan]).

For needs beyond Fabric, the announcement says Fabric integrates with third-party providers such as Atlan, Alation, Collibra and Informatica ([Tech Community][p1]). The RVAS lists them in that order and doesn't compare them.

Learn had no transition page on 2026-11-27. The announcement promises detailed transition guidance and asks customers with contractual obligations, or in highly regulated industries, to engage their Microsoft account team early.

### 4.1 The public method

The only public method is a Tech Community post dated 2026-11-13 and updated 2026-11-16 ([Tech Community][p4]). It isn't an official FAQ. Its steps:

1. Inventory sources, scans, collections, owners, glossary terms and critical data elements (CDEs), custom attributes, data products, lineage, data quality rules, workflows, access policies, API integrations, reports and evidence retention.
2. Classify each requirement: move now, coexist, bridge with a process or a partner, or redesign.
3. Design the target operating model.
4. Pilot one end-to-end scenario, including one identity that must be denied.
5. Migrate in waves. Retire a Purview dependency only after its acceptance criteria pass.

Challenge 13 teaches this method.

### 4.2 What maps to Fabric

| Purview Data Governance | Fabric construct | Status | As code | Gap | Source |
|---|---|---|---|---|---|
| Governance domains and collections | Domains, subdomains and workspaces | GA | Admin Domains API; `fabric_domain` | Domain assignment doesn't change who can see or open an item. Collection permission inheritance and Data Map roles have no equivalent. | [Learn][l-domains] |
| Data products | No single object: a domain, endorsement, a description and tags together | GA | Update Item, Apply Tags | No owner, terms-of-use or update-frequency fields. The post suggests keeping the data contract outside the catalog where needed. | [Tech Community][p4] |
| Glossary terms and CDEs | Tags and descriptions, partly | GA | Admin Tags API, Apply Tags, `fabric_tag` | Tags have no definition, hierarchy or steward. Limits: 10 per item, 10 per workspace, 10,000 per tenant. CDE types and lifecycle have no equivalent. Glossary curation is a stated plan with no date. | [Learn][l-tags], [blog][b-ignite-onelake] |
| Certification | Endorsement: Promoted, Certified, Master data | GA | Read through the scanner only | No write API. Certification can be delegated to domain admins. | [Learn][l-endorse] |
| Asset descriptions | Item descriptions | GA | Update Item; Terraform `description` | 256 characters at most, so measure Purview description lengths during the inventory. | [REST][r-updateitem] |
| Access policies, subscription requests and workflows | OneLake security roles, workspace roles, item sharing; Fabric policies | OneLake security: see 1.3. Fabric policies: Preview. | Data access roles bulk PUT; `fabric_workspace_role_assignment`; policy sets API | Learn says Fabric policies don't replace Purview access-request workflows. | [Learn][l-policies] |
| Classifications and sensitivity labels | Purview Information Protection labels on Fabric items; domain default labels | Labels GA; domain default label Preview | Label APIs, user identities only | Needs Purview licensing. Scan-based classification from the Data Map has no catalog equivalent. | [Learn][l-infoprot] |
| Lineage | Lineage view, impact analysis, item relations API | View GA; relations API Beta | Item relations API | Item level only. Spark granular lineage is announced as coming soon. | [Learn][l-lineage], [blog][b-fc2] |
| Data estate insights and health controls | Govern tab and its Insights report; `onelake-catalog-cli` audits | GA | Scanner and REST audits | No one-to-one health controls or action assignment. | [Learn][l-govern] |
| Data quality rules and scores | Materialized lake view constraints, partly | To verify | Spark SQL | No rules, profiling or scoring engine. Data quality is a stated plan with no date. | [Learn][l-mlvdq], [blog][b-ignite-onelake] |
| Data Map scans of non-Fabric sources | Shortcuts, mirroring, catalog federation, third-party catalogs | Federation: see X5 | `fabric_shortcut` | The post says "Data connectivity is not enterprise metadata scanning." The scanner covers Fabric items only. | [Tech Community][p4] |
| Audit, DLP, Insider Risk Management | Purview, unchanged | GA | See section 3.2 | None | [Learn][p2] |

[l-getstarted]: https://learn.microsoft.com/fabric/governance/get-started-with-fabric-governance

### 4.3 The Unified Catalog self-serve analytics export

Purview's self-serve analytics publishes Unified Catalog metadata as Delta Parquet tables to a OneLake lakehouse or to ADLS Gen2 ([Learn][p5]). It's the most complete public starting point for a transition inventory.

- **Status:** the setup path is labeled "Solution integrations (preview)", and the page states no other status. Treat it as Preview.
- **Contents:** the page lists 45 tables, though it gives no total. They cover governance domains; data products with owners, terms of use and update frequency; glossary terms; CDEs; OKRs; data assets and columns with classifications; data quality rules and runs; access policy sets and subscription requests; health actions; and a generic relationship table. Eight fixed reports come with it.
- **Not exported:** lineage, sensitivity label assignments, workflow definitions, collections, scans, data sources and custom metadata. The Unified Catalog REST API (Preview) ([Learn][p9]) and the backup endpoints ([Learn][p10]) cover part of that. A backup restores into another Purview account, not into Fabric.
- **Setup:** a Data Governance Administrator enables and schedules the export. The Purview managed identity needs Contributor on the target workspace, or Storage Blob Data Contributor on the ADLS Gen2 account.
- **Limits:** only governed assets are published. Publishing to a Fabric workspace isn't supported in tenants with managed private endpoints enabled, so use ADLS Gen2 there. A deleted and re-created asset gets a new ID. The page says role-based access control isn't enforced on the published data, so restrict the destination workspace.
- **Availability:** no public statement says whether the export stays available until support ends.

A challenge can use it this way: shortcut the tables into a lakehouse, count rows per construct, join the owner and approver tables to draft a RACI, and put each construct in one of the four buckets. Challenge 13 proposes a synthetic copy of the schema so learners don't need a Purview account.

### 4.4 Gaps

The transition post sums it up: "external metadata scanning, glossary and CDE depth, data quality workflows, and broad policy coverage are not one-to-one replacements today" ([Tech Community][p4]). Public documentation on 2026-11-27 adds these:

- Fabric has no data product object, no OKRs and no steward-type roles such as Data Steward or Data Source Administrator.
- Fabric policies have no access-request workflow.
- There's no API to set endorsement, and no typed custom attributes.
- Lineage stops at item level.
- Existing Purview API integrations need rework. The post says not to assume compatibility.

The assessment in challenge 13 gives each gap an owner and a decision: accept it, bridge it with a process, bridge it with a third-party catalog, or wait for a dated roadmap item.

[p5]: https://learn.microsoft.com/purview/unified-catalog-self-serve-analytics
[p9]: https://learn.microsoft.com/rest/api/purview/unified-catalog-api-overview
[p10]: https://learn.microsoft.com/purview/unified-catalog-disaster-recovery

## 5. Proposed new challenges

Five challenges cover the gaps that sections 1 to 4 found. Each one runs from a pull request, demonstrates at least one MCP server and one Skill, and has a GA path for every required task. The full outlines, each with a proposed `site/challenges.json` entry, are in [New challenge specs: November 2026](2026-11-new-challenge-specs.md).

| # | Folder | Stage | Duration | Depends | Tags |
|---|---|---|---|---|---|
| 09 | `09-onelake-catalog-metadata` | governed | 120–180 min | 00, 01, 03 | OneLake catalog, tags, endorsement |
| 10 | `10-onelake-security-as-code` | governed | 180–240 min | 00, 01, 02, 04 | OneLake security, shortcuts, dry run |
| 11 | `11-network-exfiltration-guardrails` | governed | 180–240 min | 00, 01 | outbound protection, Private Link, exfiltration |
| 12 | `12-tenant-settings-policies-as-code` | governed | 120–180 min | 00, 01, 03 | tenant settings, Fabric policies, drift |
| 13 | `13-purview-transition-assessment` | intelligent | 180–240 min | 00, 01, 03, 09 | Purview transition, inventory, RACI |

Challenge 11 sits in the governed stage because its blurb already covers access rules. Challenge 13 fits the intelligent stage, but that stage's blurb would need to mention the transition.

| # | Learners build | MCP | Skill | Preview parts and fallback |
|---|---|---|---|---|
| 09 | Tags, item descriptions and table metadata from manifests; an endorsement audit from the scanner; a check that every governed item has an owner, a description and a tag | Core `update_item` and `search_catalog` | `onelake-catalog-cli`, `search-consumption-cli` | Catalog Search API (Preview): check with the scanner instead. Table metadata API (Preview): stretch goal. Workspace tags API (Preview): use item and domain tags. |
| 10 | OneLake security roles from a manifest, applied with a dry run and an ETag; shortcut rules; a test that a denied identity can't read | Core `onelake_create_or_update_data_access_roles` with DryRun, `onelake_list_shortcuts` | `spark-cli` or `sqldw-cli` for the read test | Terraform resource (preview): use the GA bulk REST call. Principal access (Preview): rely on the denied-identity test. |
| 11 | A two-workspace exfiltration lab: outbound access protection, a managed private endpoint, inbound rules and an external share audit, each proven by a copy that fails | Core `onelake_get_settings` and `onelake_modify_diagnostics` | `spark-cli` runs the copy attempt; `fabric-policies-cli` for the sharing rule as a stretch goal | Inbound firewall and resource rule APIs (Preview): set the rules in the portal and record them as evidence. IQ Sharing (Preview): stretch goal. Needs an F SKU; a Trial won't work. |
| 12 | Tenant settings and capacity overrides as code with nightly drift detection; the 2026-12-08 Copilot setting change; a Fabric policy that blocks an item type | Core `create_item` as a negative test; Core `get_knowledge` and local `docs_*` for guidance | `fabric-policies-cli` | Fabric policies (Preview; Learn lists them as unavailable in West Europe, North Europe and West US): block item creation with a capacity override and a PR validator, and use `onelake-catalog-cli` in admin-audit mode as the Skill. |
| 13 | A Purview Data Governance transition assessment: an inventory from the self-serve analytics export, the four-bucket classification, a gap register, a steward RACI and a one-domain pilot | Hosted OneLake MCP (Preview) over the export lakehouse | `onelake-catalog-cli`, plus `spark-cli` or `sqldw-cli` for the inventory queries | Export (Preview): the challenge ships a synthetic dataset with the same schema. Hosted OneLake MCP (Preview): use Core `list_items` and `get_item`. |

### 5.1 Why these five

- 09 and 12 teach the controls Fabric now owns for data governance: catalog metadata, domains, tenant settings and policies.
- 10 and 11 turn the access and network controls in sections 1.3 and 1.5 into tested guardrails. Each control counts only when a denied action fails.
- 13 is an assessment, not a migration. It produces the evidence an owner needs to decide before support ends on 12 November 2027.
- Suggested build order: 09 and 12 first, because their required tasks are GA; then 10 and 13; then 11, which needs an F SKU and Azure network resources.

### 5.2 Considered and not proposed

- **A DLP and protection policy challenge.** Protection policies have no API, and DLP runs only through PowerShell. Section 6 extends challenge 03 instead.
- **A monitoring challenge.** The monitoring APIs are Preview and the admin monitoring workspace has no API. Section 6 extends challenge 07.
- **A data agent governance challenge.** Challenge 06 covers it; section 6 updates it for the recent data agent changes.
- **A third-party catalog challenge.** It would need partner products and accounts. Challenge 13 lists third-party catalogs as one way to bridge a gap, without comparing them.

## 6. Updates to existing challenges

These are task-level changes to challenges 00–08 and the capstone, based on sections 1–4. Line-level accuracy fixes belong to the parallel audit report, `2026-11-platform-governance-audit.md`.

The delivery guide's checklist asks each new challenge for at least one MCP tool reference and one Skill reference (`docs/delivery-guide.md`). Challenges 01, 03, 04 and 06 mention a Skill only as optional, so the changes below give each of them a Skill with a governance job.

### 6.1 Skill names and installation

Skills for Fabric moved to `{item}-cli` names in v0.3.11 (2026-08-06). The table maps the names in the challenges to v0.3.23 (2026-11-20), the latest release on 2026-11-27 ([releases][gh-skills]).

| Name in the challenges | Name in v0.3.23 | Challenges |
|---|---|---|
| `spark-authoring-cli`, `spark-operations-cli` | `spark-cli` | 00, 01, 02, 05, 08 |
| `sqldw-authoring-cli`, `sqldw-operations-cli` | `sqldw-cli` | 02, 05, 08 |
| `eventhouse-authoring-cli`, `eventhouse-consumption-cli` | `eventhouse-cli` | 00, 07 |
| `eventstream-authoring-cli` | `eventstream-cli` | 07 |
| `activator-authoring-cli` | `activator-cli` | 04, 07 |
| `powerbi-authoring-cli` | To verify: `semantic-model-authoring` for models, `powerbi-report-cli` for reports | 03, 05, 07 |
| `powerbi-consumption-cli` | To verify: `fabriciq` is the closest match | 06 |
| `e2e-medallion-architecture` | Unchanged | 05 |

In GitHub Copilot CLI, Skills for Fabric installs as plugin bundles: `/plugin marketplace add microsoft/skills-for-fabric`, then `/plugin install fabric-skills@fabric-collection`. Power BI authoring skills ship in a separate `powerbi-authoring` bundle, and `apm install microsoft/skills-for-fabric --skill <name> --target <tool>` installs a single skill ([README][gh-sff]). The README doesn't document `copilot skill install`, which challenge 00 uses.

### 6.2 Challenge 00: Setup

| Task | Change | Status and source |
|---|---|---|
| Task 2 (Enable tenant settings) | Learn names the service principal API setting two ways (section 3.3, item 8), so give both names. Add that, for the scanner and `fabric_domain`, the app registration must not hold Power BI permissions that need admin consent. | GA; [developer settings][l-devsettings], [admin API settings][l-adminapisettings] |
| Task 5 (Core MCP) | Say that the Core MCP server is GA. Offer the hosted OneLake MCP server as an optional per-item server for challenges 10 and 13. It uses an Azure Storage token, and its page makes no service principal statement. | Core GA, [Learn][l-mcpcore]; hosted OneLake Preview, [Learn][l-mcpol] |
| Task 6 (local MCP) | Version 1.8.0 has six `docs_*` tools: `docs_list-item-types`, `docs_item-api-spec`, `docs_platform-api-spec`, `docs_item-definitions`, `docs_best-practices` and `docs_api-examples`. | No status label; [README][gh-mcp] |
| Task 7 (Skills) | Use the plugin install from section 6.1. Suggest `onelake-catalog-cli` as the first governance Skill, because challenges 09 and 13 use it. | Released; [README][gh-sff] |
| Task 8 (Smoke test) | `docs_workloads` and `docs_workload-api-spec` aren't in v1.8.0. Use `docs_list-item-types` and `docs_item-api-spec`. | [README][gh-mcp] |

### 6.3 Challenge 01: Workspace as code

| Task | Change | Status and source |
|---|---|---|
| Stretch goals | Add a manifest field that provisions the workspace identity. Trusted workspace access and identity-based shortcuts use it (section 1.5). | GA; [Learn][l-wsid] |
| Skills tips | Replace the pointer to challenge 02's skill with `onelake-catalog-cli` in dataowner-audit mode. It reports the new workspace's capacity and domain assignment through the Core API, without tenant admin rights. | Released; [README][gh-sff] |

### 6.4 Challenge 02: Items as code

| Task | Change | Status and source |
|---|---|---|
| Task 1 (Design the item manifest) | `sensitivityLabel` defaults to the workspace's label, but Fabric labels items, not workspaces. Default it to the domain's default label or make it required. | Domain default label Preview; [Learn][l-domainlabel] |
| Task 5 (Scaffold real content with Skills) | Rename the skills, including the `@spark-authoring-cli` and `@sqldw-authoring-cli` prompts (section 6.1). | Released; [releases][gh-skills] |
| Stretch goals | Record each item's upstream and downstream relations with the item relations API. Challenge 09 can use them as lineage evidence. | Beta on Learn, Preview in the post; [blog 2026-09-10][b-relations] |

### 6.5 Challenge 03: Domains, capacities and sensitivity

| Task | Change | Status and source |
|---|---|---|
| Prerequisites | Membership of the label publishing scope doesn't let the service principal label items, because the bulk label APIs accept user identities only. Say that Task 5 needs a Fabric admin user or the domain default label. | GA, user only; [Fabric][r-labels], [Power BI][r-pbilabels] |
| Task 1 (Domains as code) | The preview versions of the Domains REST APIs are no longer available. Use the GA admin Domains API or `fabric_domain`, and add an optional `defaultLabelId` to the domain manifest. | Notice 2026-11-17, [November summary][b-nov]; API GA, [REST][r-domains]; default label Preview, [Learn][l-domainlabel] |
| Task 5 (Labels at provision time) | The `POST …/admin/workspaces/{id}/sensitivityLabel` call isn't in the Power BI REST reference, and the challenge's reference link returns 404. Labels apply to items. A service principal pipeline can set the domain's default label for new items; keep one admin step for existing items (section 3.3, item 1). The local MCP's `core_create-item` takes `sensitivity-label-settings`; whether a service principal can use it is to verify. | Bulk labels GA, [REST][r-labels]; default label Preview, [Learn][l-domainlabel] |
| Task 6 (Drift detection) | Read labels from Get Item or the scanner. Optionally add the capacity's surge protection settings from `GET /v1/capacities/{id}/surgeProtection`. | Scanner GA, [Learn][l-scan]; surge protection GA at workspace level, REST status to verify (X19), [REST][r-surge] |
| Stretch goals (Purview-side enforcement) | DLP for Fabric is GA, and `New-DlpCompliancePolicy` manages its policies with app-only certificate authentication. Protection policies have no API, so record them as a manual step. Only sensitivity labels, protection policies and DLP need Purview licensing. | DLP GA, [Learn][l-dlp], [PowerShell][r-dlpps]; protection policies GA, to recheck (X18), [Learn][l-protpol] |
| MCP tips | Catalog search filters on item type and workspace only, so it can't confirm a domain. Check domains with the admin Domains API or `onelake-catalog-cli`. | Catalog search Preview; [REST][r-search] |
| Skills tips | Replace `powerbi-authoring-cli` (section 6.1). Use `onelake-catalog-cli` in admin-audit mode for label coverage and domain assignment; it reads labels from the scanner. | Released; [README][gh-sff] |

### 6.6 Challenge 04: Access, RBAC and lifecycle

| Task | Change | Status and source |
|---|---|---|
| Task 3 (Provisioner reconciliation) | Item-level sharing has no Core REST API, so the provisioner can't reconcile it. Report item grants outside the manifest in the drift issue, using the admin access reports such as `GET /v1/admin/workspaces/{ws}/items/{id}/users`. | Access reports Preview, service principals supported; [REST][r-adminusers] |
| Task 4 (Quarterly access review) | For items with OneLake security roles (challenge 10), add role membership to the review. Read it with the Core MCP's `onelake_list_data_access_roles`. | GA; [REST][r-roles] |
| Task 5 (JIT break-glass) | Move the `activator-cli` expiry alert from Skills tips into the task, so the challenge demonstrates a Skill. | Released; [releases][gh-skills] |
| Task 6 (Verify via Fabric Core MCP) | Don't treat the hosted OneLake MCP's `onelake_get_principal_access` as proof: it can report `canRead: false` for a principal who can read. | Preview; [Learn][l-mcpol] |

[gh-sff]: https://github.com/microsoft/skills-for-fabric
[r-adminusers]: https://learn.microsoft.com/rest/api/fabric/admin/users

### 6.7 Challenge 05: Medallion architecture bootstrap

| Task | Change | Status and source |
|---|---|---|
| Prerequisites and Task 4 (Provisioner: call the Skill) | Rename `spark-authoring-cli` and `sqldw-authoring-cli` to `spark-cli` and `sqldw-cli`; for `powerbi-authoring-cli`, see section 6.1. `e2e-medallion-architecture` keeps its name. The Skills for Fabric README doesn't document `copilot skill run`, so check the invocation against it. | Released; [README][gh-sff] |
| Task 5 (Apply endorsement and labels) | Endorsement has no write API, in the Power BI admin API or anywhere else. Certify the Gold model in the UI, and limit who can certify through the certification tenant setting or by delegating it to domain admins. In CI, compare `endorsement` in the manifest with `endorsementDetails` from the scanner and fail on a mismatch. Labels follow challenge 03 (section 6.5). | GA, no write API; [endorsement][l-endorse], [scanner][l-scan] |
| Success criteria | Keep the rule that removing `endorsement: Certified` fails validation. Add that the scanner reports the Gold model as Certified. | GA; [scanner][l-scan] |
| Skills tips | Add `onelake-catalog-cli` in admin-audit mode to report label and endorsement coverage for the three workspaces. | Released; [README][gh-sff] |

### 6.8 Challenge 06: Fabric Data Agent governance

| Task | Change | Status and source |
|---|---|---|
| Learning objective 3 and Task 2 (Approved-source policy) | Labels apply to items, not workspaces, so `clearance` can't match "the workspace's sensitivity label". Compare it with each source item's label, read from Get Item or the scanner. For new items, the domain default label is the closest workspace-level value. | Labels GA, [Learn][l-infoprot]; domain default label Preview, [Learn][l-domainlabel] |
| Prerequisites | Add the dated Copilot change and check that the tenant settings the challenge needs still hold after it: on 2026-12-08 the standalone Copilot setting turns off by default, and standalone Power BI Copilot retires on 2027-01-15. | Dated change; [Learn][l-copilot] |
| Task 4 (Provisioner) | The provisioner runs as a service principal, and service principal support for data agents is Preview. Create the agent through the Core Items API with type `DataAgent`, or with `fabric_data_agent` in Terraform. Keep a user-run path in case the preview changes. | Preview; [blog][b-spn-da], [REST][r-dataagent] |
| Stretch goals | DSPM for AI is Preview and has no API, so the DSPM check is a manual review, not a pipeline gate. Extend the Microsoft 365 Copilot surfacing goal with Copilot Studio (GA) and Agent 365 (Preview), each behind its own CODEOWNERS approval. | DSPM for AI Preview, [Learn][l-dspm]; Copilot Studio GA 2026-09-02, [blog][b-da-cs]; Agent 365 Preview, [Ignite IQ][b-ig-iq] |
| MCP tips | The Fabric IQ MCP server is GA and read-only, with no service principal support. Mention it for checks a person runs, and keep the pipeline on the Core MCP's `get_item_definition`. | Core MCP GA, [Learn][l-mcpcore]; Fabric IQ MCP GA, [Learn][l-iqmcp] |
| Skills tips | Replace "No Skill is required" and `powerbi-consumption-cli`. To verify: `fabriciq` is the closest match for the smoke-test query. | Released; [README][gh-sff] |

### 6.9 Challenge 07: Audit & observability

| Task | Change | Status and source |
|---|---|---|
| Learning objectives, prerequisites, task prompts and references | Rename the skills to `eventhouse-cli`, `eventstream-cli` and `activator-cli`, and treat `powerbi-authoring-cli` as in section 6.1. Point the reference links at the new skill folders. | Released; [releases][gh-skills] |
| Task 4 (Ingest Fabric activity events) | State the Option A limits: a service principal can call `GET /admin/activityevents`, each call covers one UTC day, and only the last 28 days are available. Add three sources: OneLake diagnostics, which writes access events to a lakehouse within about an hour; workspace monitoring, which writes logs and metrics to an Eventhouse; and capacity events in Real-Time hub, which stream to Eventstream and Activator. | Activity events GA, [REST][r-activity]; diagnostics GA, [Learn][l-diag]; monitoring Preview, [Learn][l-wsmon], [REST][r-monitoring]; overview events GA, [blog][b-capov]; operation events Preview, [blog][b-capop] |
| Task 5 (Build the governance dashboard) | Add a tile from the admin network policies list that shows which workspaces restrict inbound or outbound access. Challenge 11 sets those policies. | GA; [REST][r-adminnetpol] |
| Task 6 (Activator alerts) | Add an alert on capacity overview events, for example a change in capacity state. | GA; [blog][b-capov] |
| Stretch goals | The cross-tenant audit through external data sharing needs a workspace without outbound access protection, in a tenant without tenant-level Private Link. | GA, with limits; [Learn][l-eds] |
| MCP tips | Add the Core MCP's `onelake_modify_diagnostics` and `onelake_get_settings`, which turn on OneLake diagnostics and check it from a prompt. | Core MCP GA; [tools][l-mcptools] |
