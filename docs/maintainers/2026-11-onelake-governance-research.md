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
