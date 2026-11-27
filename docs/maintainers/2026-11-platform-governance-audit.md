# Platform governance audit, November 2026

This report audits the Fabric Governance RVAS for platform governance and turns the results into a prioritized backlog for phase 2. The companion report, `docs/maintainers/2026-11-onelake-governance-research.md`, holds the new-challenge designs. This report gives only the gap and a one-line proposal for each new challenge.

## Summary

- The audit raises 42 findings: 14 high, 16 medium and 12 low. Most high findings break a core task. Three commands fail, 14 retired Skill names appear on 63 lines, and challenges rely on a workspace label API, an endorsement write API and a pipeline snapshot rollback that don't exist. Both event-ingest paths in challenge 07 fail as written.
- The setup over-privileges the service principal (SPN). It makes the SPN Fabric Administrator and capacity admin, grants it Power BI `Tenant.ReadWrite.All` and adds it to the label publishing scope. Admin API tenant settings scoped to a security group, plus the capacity contributor role, cover the same work.
- The repo teaches two naming standards. The rules engine and schema enforce a six-segment pattern, but challenge 01 and the approval workflow teach another, and most example names fail the enforced one. The CODEOWNERS rule for production manifests never matches.
- The repo's own rule fails in 7 places: challenges 01, 03, 04, 06 and 08 use no Skill in their core tasks, and 03 and 07 use no MCP server.
- Of 27 platform-governance capability areas, 7 are covered (4 of them teach a step that fails), 8 are partial and 12 are missing. The gaps cluster around OneLake catalog Govern, OneLake security, Fabric policies, tenant settings as code, network and exfiltration controls, lineage and data quality.
- Purview Data Governance is retiring; support ends 12 November 2027. Nothing in the RVAS covers the transition. Purview remains the security and compliance layer.
- The backlog has 28 items (12 P0, 15 P1, 1 P2) in 11 work packages with disjoint file ownership, so phase-2 sessions can run in parallel. Four items are new challenges.
- Text files hold no customer, person or tenant names and no subscription or tenant IDs. Two hygiene items need action: a committed build artifact under `dist/` (F-80) and sample values tied to one market and industry (F-81).

## Method

- Baseline: `main` at commit `b1280e5`.
- Sources: public only. Microsoft Learn (including the Fabric REST API reference and "What's new in Microsoft Fabric"), the Fabric blog, the Fabric roadmap, Tech Community, Partner Center announcements, the Terraform Registry and public GitHub.
- Dates: every status in this report was checked on 27 November 2026. Anything not confirmed is marked "to verify".
- Links: all 55 external links in the repo were requested with redirects followed.
- Tooling baselines: skills-for-fabric release v0.3.23 (20 November 2026, 28 skills) and Fabric MCP Server release 1.8.0 (11 November 2026).
- Scans: regular expressions for retired Skill names, naming patterns, identifiers and internal references.
- No live calls: nothing called a Fabric, Power BI, Azure or Entra API against a tenant.
- Severity: high means wrong or broken, medium means stale or incomplete, low means polish.
- Locations: `00:88` means `challenges/00-setup/challenge.md`, line 88, and the same form applies to challenges 01–08. `Cap` is `challenges/capstone/challenge.md`. `workflow.md` is `docs/workspace-approval-workflow.md`. Other files under `docs/` appear by file name.

## Recent platform changes that affect the RVAS

Statuses were checked on 27 November 2026. Where two public sources disagree, the row says so, and phase 2 should teach the more cautious status until they agree.

| Change | Status | Source | RVAS impact |
|---|---|---|---|
| Purview Data Governance is retiring; support ends 12 November 2027. The retirement covers Unified Catalog, Data Map, Workflows and Azure Purview, so Data Map scanning of Fabric ends too. Purview remains the security and compliance layer. | Retiring (announced 12 Nov 2026) | [Tech Community](https://techcommunity.microsoft.com/blog/microsoft-security-blog/a-next-step-in-the-evolution-of-the-microsoft-data-governance-strategy/4572227), [Partner Center](https://learn.microsoft.com/partner-center/announcements/2026-november#update-on-the-microsoft-data-governance-strategy) | Transition challenge (B-33) |
| OneLake catalog Govern brings tenant, domain, capacity, workspace, tag and policy administration together. Admin experiences move into it region by region, and the Purview hub redirects to it. Its insights refresh daily, and it isn't available with Private Link. | GA (Sep 2026); Policies center and Apps view Preview | [Govern](https://learn.microsoft.com/fabric/governance/onelake-catalog-govern) | F-34, B-18, B-30 |
| OneLake security data access roles, with the Members and Data experience | GA (Sep 2026); third-party engines Preview | [Access control model](https://learn.microsoft.com/fabric/onelake/security/data-access-control-model) | B-16 |
| OneLake outbound access protection | GA (Sep 2026) | [Outbound access protection](https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview) | B-31 |
| Fabric policies: allow-only rules for external data sharing, item creation and workspace settings editing (details below) | Preview | [Fabric policies](https://learn.microsoft.com/fabric/governance/fabric-policies-overview) | B-32, Q-6 |
| Tags, with the admin Tags API: 10,000 tags per tenant, 10 per item, names up to 40 characters | GA; Apply Workspace Tags API Preview | [Tags](https://learn.microsoft.com/fabric/governance/tags-overview), [Tags admin API](https://learn.microsoft.com/rest/api/fabric/admin/tags) | F-29, F-55, B-13, B-15 |
| Catalog Search API (50 requests a minute, SPN support), the Core MCP `search_catalog` tool and `fab find`; table discovery in the catalog | Preview | [Catalog search](https://learn.microsoft.com/rest/api/fabric/core/catalog/search) | Repo-rule steps for 01 and 03, B-30 |
| Domains Admin API, and a default sensitivity label per domain | API GA; default label Preview | [Domains admin API](https://learn.microsoft.com/rest/api/fabric/admin/domains), [Default label](https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label) | F-20, B-15 |
| Workspace-level surge protection | GA (Nov 2026) | [Surge protection](https://learn.microsoft.com/fabric/enterprise/surge-protection) | B-15 |
| Fabric apps, with an Apps view in Govern | Apps GA; Apps view Preview | [Fabric blog](https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/build-governed-data-apps-with-microsoft-fabric-apps-generally-available/5423011) | B-30 |
| Workspace customer-managed key APIs | GA (Aug 2026) | [Workspace CMK](https://learn.microsoft.com/fabric/security/workspace-customer-managed-keys) | B-31 |
| Eventhouse customer-managed keys | Sources disagree: the Fabric blog says GA, Learn says Preview (to verify) | [What's new](https://learn.microsoft.com/fabric/fundamentals/whats-new) | B-31 |
| Eventhouse outbound access protection, which blocks Copilot, cross-workspace queries and Eventstream push mode | GA | [What's new](https://learn.microsoft.com/fabric/fundamentals/whats-new) | B-31 |
| Cloud connection Admin APIs and the connection tenant allowlist | Sources disagree: What's new says GA (Sep 2026), the feature pages say Preview | [Data source management](https://learn.microsoft.com/fabric/data-factory/data-source-management) | B-31 |
| Networking communication policies Admin API | GA (Sep 2026) | [What's new](https://learn.microsoft.com/fabric/fundamentals/whats-new) | B-31 |
| Real-Time hub capacity overview events | GA (Aug 2026); capacity operation events Preview | [Fabric events](https://learn.microsoft.com/fabric/real-time-hub/explore-fabric-events) | F-25, B-18 |
| Materialized lake views with data quality constraints | GA (Sep 2026); constraints carry no preview label; PySpark authoring Preview | [Data quality](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/data-quality) | B-14, B-30 |
| Capacity Metrics app enhancements, including chargeback | GA (Sep 2026) | [Metrics app](https://learn.microsoft.com/fabric/enterprise/metrics-app), [Chargeback](https://learn.microsoft.com/fabric/enterprise/chargeback-app) | B-18 |
| Fabric data agent | GA | [Data agent](https://learn.microsoft.com/fabric/data-science/concept-data-agent) | F-27, B-17 |
| skills-for-fabric v0.3.23: one skill per workload; onelake-catalog-cli replaces onelake-catalog-govern-cli; includes fabric-policies-cli and search-consumption-cli | Released 20 Nov 2026 | [Changelog](https://github.com/microsoft/skills-for-fabric/blob/main/CHANGELOG.md) | F-01, repo-rule steps |
| Fabric MCP Server 1.8.0 (11 Nov 2026), after the 1.4.0 tool renames; the remote Core MCP server, including OneLake data access role tools | Local server GA; Core MCP GA | [Changelog](https://github.com/microsoft/mcp/blob/main/servers/Fabric.Mcp.Server/CHANGELOG.md), [Fabric MCP servers](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/fabric-mcp-servers-list) | F-03, F-04, B-16 |
| Terraform provider for Fabric v1.15.1 (11 Nov 2026); `fabric_domain_workspace_assignments` needs preview mode | Provider GA | [Registry](https://registry.terraform.io/providers/microsoft/fabric/latest/docs), [Releases](https://github.com/microsoft/terraform-provider-fabric/releases) | B-15, B-32 |
| fabric-cicd 1.4.0 (7 Oct 2026) and Fabric CLI 1.9.0 (4 Nov 2026) | Released; fabric-cicd bulk publish Preview | [fabric-cicd](https://microsoft.github.io/fabric-cicd/), [Fabric CLI releases](https://github.com/microsoft/fabric-cli/releases) | B-19 |
| The gh-copilot extension is retired; Copilot CLI installs Skills as plugins | Retired 25 Oct 2025 | [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) | F-02 |

Fabric policies (Preview) in more detail:

- There are three policies. Allow external data sharing works at tenant scope and blocks all sharing by default. Allow item creation works at capacity scope and allows all by default. Allow workspace settings editing works at tenant scope.
- Policies only allow, and each scope has one active policy. A Fabric admin or capacity admin activates a policy; Git can't.
- A tenant policy holds up to 100 rules, a capacity policy up to 50, and each condition up to 50 values. Changes apply within 15 minutes.
- Policies are items, so REST, Git and SPNs can manage them once the "Policies (preview)" tenant setting is on.
- They aren't available yet in West Europe, North Europe or West US.

## Findings

Each table gives the finding, its evidence and the fix. Long location lists and details follow each table.

### Tooling

| ID | Location | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| F-01 | 63 lines, listed below | High | Challenges and docs use 14 Skill names that skills-for-fabric retired when it merged its authoring, consumption and operations skills into one skill per workload. | [skills-for-fabric changelog](https://github.com/microsoft/skills-for-fabric/blob/main/CHANGELOG.md) | Rename with the mapping below. |
| F-02 | 00:88-91, 00:106, 00:108, 05:96, mcp-and-skills.md:58-61, :176-177 | High | Three commands fail. `gh copilot mcp add` belongs to the gh-copilot extension, which was retired and stopped working on 25 October 2025. Copilot CLI has no `skill install` or `skill run` command. | [Add MCP servers](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers), [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [Run Copilot CLI programmatically](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically) | Use the commands below. |
| F-03 | 00:96-97, 00:120-121, mcp-and-skills.md:94-95, :103-104, :113-115, :120 | Medium | The local MCP setup is stale. The npm package and start command changed, the VS Code extension is now "Fabric MCP Server", and release 1.4.0 renamed `docs_workloads` to `docs_list-item-types` and `docs_workload-api-spec` to `docs_item-api-spec`. | [Get started locally](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/pro-dev-local/get-started-local), [Fabric MCP changelog](https://github.com/microsoft/mcp/blob/main/servers/Fabric.Mcp.Server/CHANGELOG.md) | Start it with `npx -y @microsoft/fabric-mcp@latest server start --mode all`, name the extension `fabric.vscode-fabric-mcp-server` and rename the tools. |
| F-04 | mcp-and-skills.md:41, 08:143-144 | Medium | `get_operation_state` and `get_operation_result` aren't remote Core MCP tools; the local server has `core_get-operation-state` and `core_get-operation-result`. The docs also omit the Core MCP's OneLake data access role tools and don't say that it has no tools for domains, tags, tenant settings or labels. | [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server), [Fabric MCP servers](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/fabric-mcp-servers-list) | Name the right server for each tool and add the statuses below. |
| F-05 | README.md:5 | Low | The opening sentence is garbled ("by *skills-for-fabricAgents* help teams"). | README.md:5 | Rewrite the sentence. |
| F-06 | README.md:151-153, 03:21, 03:147-149, 07:145-147 | High | The README requires each challenge to demonstrate at least one MCP server and one Skill. Challenges 01, 03, 04, 06 and 08 use no Skill in core tasks, and 03 and 07 mention MCP only in objectives or tips. | README.md:151-153 | Add the core steps in "Repo-rule checks". |
| F-07 | README.md:141-147, challenges-overview.md:287-308 | Medium | The README tools table and the overview's Skills × Challenges matrix disagree about which challenge uses which tool. | Both files | Rebuild both from the fixed challenges (B-12). |
| F-08 | 00:141-142, 04:22-24, 04:125-128, 04:139, challenges-overview.md:306, delivery-guide.md:174, :220 | Medium | "Microsoft Graph MCP" is now the Microsoft MCP Server for IT Admins (GA); the Core MCP page calls it "Microsoft MCP Server for Enterprise". It needs your own app registration with `MCP.Server.Access` and `User.Read.All`, and works with delegated permissions only. | [Get started](https://learn.microsoft.com/graph/mcp-server/get-started) | Use the current name (mention both), add the setup and keep it optional (Q-9). |
| F-09 | copilot-studio-agent.md:25-26, agent/copilotstudio/README.md:163 | Low | The claim that agent flow inputs and outputs are limited to "String / Number / Boolean" can't be confirmed, and both links redirect. | [Agent flows](https://learn.microsoft.com/microsoft-copilot-studio/advanced-flow) | Re-check the claim and link the current page. |

#### F-01 details

Retired names appear on these 63 lines:

- 00:106, :108, :136; 01:133; 02:20, :27, :87, :90, :95, :98, :148, :149; 03:157; 04:133; 05:24, :25; 06:144.
- 07:15, :16, :18, :19, :20, :27, :28, :42, :61, :89, :105, :116, :119, :124, :160-163; 08:148.
- challenges-overview.md:293-302; delivery-guide.md:81; mcp-and-skills.md:153-166, :176, :188.

README.md:145 ("authoring / consumption / operations skills") and delivery-guide.md:250-251 ("Four authoring skills + one consumption skill") describe the old skill split and need rewording too.

| Retired names | Current skill |
|---|---|
| spark-authoring-cli, spark-consumption-cli, spark-operations-cli | spark-cli |
| sqldw-authoring-cli, sqldw-consumption-cli, sqldw-operations-cli | sqldw-cli |
| eventhouse-authoring-cli, eventhouse-consumption-cli | eventhouse-cli |
| eventstream-authoring-cli, eventstream-consumption-cli | eventstream-cli |
| activator-authoring-cli | activator-cli |
| dataflows-authoring-cli | dataflows-cli |
| powerbi-authoring-cli, powerbi-consumption-cli | Not in the current list. Use semantic-model-authoring or powerbi-report-cli to author, and fabriciq for questions over reports and models (to verify against the v0.3.23 skill list). |

This expression finds every retired name. It doesn't match current names such as deployment-pipelines-authoring-cli, search-consumption-cli or git-integration-operations-cli.

```text
\b(spark|sqldw|eventhouse|eventstream|activator|dataflows|powerbi)-(authoring|consumption|operations)-cli\b
```

The governance skills in v0.3.23 are search-consumption-cli (find items across the OneLake catalog), onelake-catalog-cli (tenant-admin and data-owner audits with guarded remediation, plus a curate mode; it replaces onelake-catalog-govern-cli) and fabric-policies-cli (turns intent into Fabric policy configurations).

#### F-02 commands

- Add the remote MCP server with `copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core`, with `/mcp add` inside a session, or in `~/.copilot/mcp-config.json`.
- Install Skills as a plugin: `copilot plugin marketplace add microsoft/skills-for-fabric`, then `copilot plugin install fabric-skills@fabric-collection` (or `/plugin` inside a session). APM also works: `apm install microsoft/skills-for-fabric --skill SKILL-NAME --target TOOL`. Invoke a skill with `/SKILL-NAME`.
- For the unattended run in 05:93-105, use `copilot -p` with a scoped `--allow-tool` list. Avoid `--allow-all` outside a sandbox. Authenticate with a fine-grained personal access token that has the "Copilot Requests" permission, in `COPILOT_GITHUB_TOKEN`; classic tokens aren't supported.

#### F-04 server statuses

| Server | Status (27 Nov 2026) |
|---|---|
| Remote: Core MCP, Fabric IQ MCP, data agent as an MCP server | GA |
| Remote: Data Warehouse, Eventhouse, Activator, operations agent, hosted Power BI authoring, Ontology | Preview |
| Local: Fabric MCP Server, Power BI authoring | GA |
| Local: Real-Time Intelligence, Data Factory | Preview |

The Core MCP tools that matter for governance are `search_catalog`, the workspace and workspace role tools, item tools including `bulk_move_items`, `list_capacities`, the shortcut tools, and the OneLake data access role tools. `onelake_create_or_update_single_data_access_role` changes one role; `onelake_create_or_update_data_access_roles` replaces every role on the item and supports a dry run. Role tools take Entra object IDs, not email addresses.

### Identity

| ID | Location | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| F-10 | 12 lines, listed below | High | Setup makes the SPN a Fabric Administrator. Admin APIs only need the SPN's security group enabled in "Service principals can access read-only admin APIs" and "Service principals can access admin APIs used for updates", which 00:56-57 already lists. | [Enable SPN admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis) | Drop the Fabric Administrator role and keep the tenant settings. |
| F-11 | workflow.md:111 | High | The workflow grants the SPN the Power BI `Tenant.ReadWrite.All` application permission. Admin APIs reject an SPN that holds admin-consented Power BI permissions. | [Enable SPN admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis) | Remove the permission. |
| F-12 | 00:55, identity-model.md:67, setup.md:23, workflow.md:90-92 | Medium | "Service principals can use Fabric APIs" is now two settings: "Service principals can create workspaces, connections, and deployment pipelines" (off by default for new tenants) and "Service principals can call Fabric public APIs". workflow.md:91-92 also paraphrases the admin API setting names. | [Developer tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-developer) | Use the current names. |
| F-13 | 12 lines, listed below | Medium | The SPN is made capacity admin. Assigning a workspace to a capacity needs the capacity contributor permission plus the workspace Admin role. | [Assign To Capacity](https://learn.microsoft.com/rest/api/fabric/core/workspaces/assign-to-capacity) | Grant capacity contributor instead. |
| F-14 | _fabric.py:131-144, rules_engine.py:287-289, provision.py:99 | Medium | The Graph group and user lookups need permissions that no doc lists, and a 401 or 403 response reads as "not found". | [Graph permissions](https://learn.microsoft.com/graph/permissions-reference) | Document `GroupMember.Read.All` (or `Group.Read.All`) and `User.Read.All`, and raise on 401 or 403. |
| F-15 | 10 lines, listed below | High | The docs add the SPN to a label publishing policy so it can label items. Bulk Set Labels accepts only a Fabric admin user. SPN support for the Power BI SetLabelsAsAdmin API is to verify. | [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels) | Have a human Fabric admin apply labels (Q-7), or use the domain default label. Take the SPN out of label policies. |

Locations:

- F-10: 00:62, :64; 03:28; delivery-guide.md:58, :204; glossary.md:23; identity-model.md:77, :83; setup.md:35-37; workflow.md:102, :649, :669.
- F-13: 00:62; delivery-guide.md:58, :325; glossary.md:11, :22; identity-model.md:78; setup.md:41, :43; troubleshooting.md:48; workflow.md:112, :652, :670.
- F-15: 03:26-27; identity-model.md:79; troubleshooting.md:82, :85; delivery-guide.md:59-60, :204-205; workflow.md:113, :650, :671.

### APIs and platform

| ID | Location | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| F-20 | 03:96-106, 03:163, workflow.md:66-67, :528, delivery-guide.md:208-209 | High | Challenge 03 sets a workspace sensitivity label through an API that doesn't exist, and its reference link returns 404. Labels apply to items. The domain assignment call at 03:89-90 is correct. | [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels), [Domain default label](https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label) | Teach the label routes below. |
| F-22 | 05:115-116 | High | Challenge 05 sets endorsement through an API. Fabric has no endorsement write API. | [Endorsement](https://learn.microsoft.com/fabric/governance/endorsement-overview) | Declare the intended endorsement in the manifest, check it with the scanner or the catalog, and have a certifier apply it in the UI. |
| F-23 | 11 places, listed below | High | Challenge 08 restores a pipeline stage from a "snapshot". Deployment pipelines have no snapshot restore. | [Rolling back changes](https://learn.microsoft.com/fabric/cicd/best-practices-cicd#rolling-back-changes) | Roll back with `git revert` or a reset, then sync and redeploy. Say that data may not roll back, that backward deployment works only to an empty stage and that List Operations returns at most 20 entries. |
| F-24 | 07:58-68, 07:76-77, delivery-guide.md:253-254, workflow.md:79 | High | Both ingest paths fail. The Eventstream custom endpoint (GA) speaks Event Hubs, AMQP or Kafka, so a GitHub webhook can't post to it directly. Option A's HTTP source (Preview) polls an endpoint and can't receive posts. | [Custom endpoint](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-source-custom-app), [Eventstream sources](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-manage-eventstream-sources) | Relay webhooks through an Azure Function or Logic App into the custom endpoint. |
| F-25 | 07:79-80 | High | The path "Purview Audit → Activity Explorer → Eventstream connector" doesn't exist. | [Fabric events](https://learn.microsoft.com/fabric/real-time-hub/explore-fabric-events), [Track user activities](https://learn.microsoft.com/fabric/admin/track-user-activities) | Use Real-Time hub Fabric events (workspace item, OneLake, job and capacity overview events are GA; capacity operation events are Preview) or Purview Audit search. |
| F-26 | 06:20, :27, :129-131, Cap:78, delivery-guide.md:243-244, :370, glossary.md:52 | Medium | Challenge 06 reads DSPM findings through an API. No public API returns them, and DSPM for AI is Preview. DSPM's Fabric data risk assessments also need the admin API tenant settings. | [Purview for Copilot in Fabric](https://learn.microsoft.com/purview/ai-copilot-fabric) | Review DSPM in the Purview portal and record the result as evidence. |
| F-27 | 06:26, delivery-guide.md:242 | Medium | The data agent prerequisites are incomplete. The data agent is GA, and an SPN can create one. | [Data agent tenant settings](https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings), [Data agent](https://learn.microsoft.com/fabric/data-science/concept-data-agent) | List an F2 or P1 capacity or larger, "Users can use Copilot and other features powered by Azure OpenAI", "Capacities can be designated as Fabric Copilot capacities", the two cross-geo settings (processing and storage) for capacities outside the EU Data Boundary and the US, and up to an hour for changes to apply. |
| F-28 | workflow.md:608-617, drift.py:32-40 | Medium | The workflow describes an admin-API drift check that compares capacity, roles, domain, label and description. drift.py calls the non-admin `GET /v1/workspaces` and compares descriptions only. | drift.py:32-40 | Align the doc with the code, or extend the code (B-20). |
| F-29 | workflow.md:655 | Medium | The workflow says workspaces have no native tags. Tags are GA: up to 10 per workspace, names up to 40 characters. The Apply Workspace Tags API is Preview and supports SPNs, and Admin List Workspaces and the scanner return tags. | [Tags](https://learn.microsoft.com/fabric/governance/tags-overview), [Apply Workspace Tags](https://learn.microsoft.com/rest/api/fabric/core/workspaces/apply-workspace-tags) | Map manifest tags to workspace tags (F-55). |
| F-30 | workflow.md:659 | Low | The note on which APIs are Power BI and which are Fabric is partly stale. The tenant settings Admin API (GA) and Bulk Set Labels are Fabric APIs; the activity events API and SetLabelsAsAdmin are still Power BI APIs. | [Tenants admin API](https://learn.microsoft.com/rest/api/fabric/admin/tenants) | Update the note. |
| F-31 | workflow.md:117-150, :140, :608, :611, :678, :689 | Low | The workflow shows a repository layout and file names that don't exist in this repo. | The repo tree | Match the real layout, or label it as an example. |
| F-32 | workflow.md:656 | Low | The workflow filters on `PersonalGroup`. The Fabric admin API returns the types Personal, Workspace and AdminWorkspace. | [Admin List Workspaces](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces) | Filter on `Personal`. |
| F-33 | 01:81-91, drift.py:32-40, _fabric.py:56-63 | Medium | Task 5 injects drift by removing an admin, but drift.py compares descriptions only. Its "unmanaged" list comes from the non-admin workspace list, so it misses workspaces the SPN can't see. | drift.py:32-40 | Change the task to edit the description until B-20 adds role drift. |
| F-34 | 00:52, identity-model.md:63, workflow.md:84, setup.md:5, :19, :21, glossary.md:13, :17 | Low | The docs send admins to "Fabric Admin Portal → Tenant settings". Tenant settings are also in OneLake catalog → Govern → Configurations (Govern is GA and rolling out by region). | [Govern](https://learn.microsoft.com/fabric/governance/onelake-catalog-govern), [Admin overview](https://learn.microsoft.com/fabric/admin/admin-overview) | Give the Govern path first and the Admin portal as the fallback. |

F-23 locations: 08:19-20, :110-116, :130; Cap:75; challenges-overview.md:28, :166, :169, :229, :324; delivery-guide.md:265; site/challenges.json:133-137.

Label routes for F-20:

- Bulk Set Labels, `POST /v1/admin/items/bulkSetLabels`: a Fabric admin user only, 25 requests an hour, up to 2,000 items a request. Status to verify.
- Power BI SetLabelsAsAdmin (GA): [Set Labels As Admin](https://learn.microsoft.com/rest/api/power-bi/admin/information-protection-set-labels-as-admin). SPN support is to verify.
- Domain default sensitivity label (Preview): labels new items in the domain. It doesn't label items that pipelines or Git create.
- Read item labels with the scanner (GA) to confirm the result.

### Naming and policy

| ID | Location | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| F-50 | rules_engine.py:53-57, :131-152, schemas/workspace.schema.json:26, governance-rules.md:80-83, 01:40, :50, workflow.md:168, and the lines below | High | The repo teaches two naming standards. The rules engine, the schema and governance-rules.md enforce the six-segment pattern below, but challenge 01 and the approval workflow teach a different one, and most example names fail the enforced pattern. Many tasks also treat a "prd-" prefix as production, while the engine decides production from the manifest's `environment` field (rules_engine.py:129, :162-165, :272-281). | rules_engine.py:53-57 | Confirm one standard (Q-2), fix every example and base production logic on `environment`. |
| F-51 | agent/appPackage/instructions.md:48 | Medium | The agent's subdomain rule disagrees with the rules engine. | rules_engine.py:61 | Align the instructions with the engine. |
| F-52 | agent/appPackage/instructions.md:68 | Low | The label name is written "HighlyConfidential". | instructions.md:68 | Use the label name exactly as the policy defines it. |
| F-53 | rules/policy.yaml:141, api/policy.yaml:141 | Low | The rule description says "prd-*", but the engine applies production rules from the `environment` field. | rules_engine.py:162-165 | Reword the description in both copies. |
| F-54 | rules_engine.py:59, schemas/workspace.schema.json:95 | Low | The group name pattern (`GROUP_NAME_RX`) leaves out the `poc` and `stg` environments that the workspace pattern allows. | rules_engine.py:59 | Add `poc` and `stg`. |
| F-55 | The sample manifest in `workspaces/`, lines 24-26 | Low | The manifest's free-form `tags:` don't map to Fabric workspace tags. | [Tags](https://learn.microsoft.com/fabric/governance/tags-overview) | Map them to workspace tags, which the Apply Workspace Tags API (Preview) sets (B-20). |
| F-56 | .github/CODEOWNERS:14 | High | The rule `/workspaces/prd-*.yaml` never matches a six-segment name, so production manifests get no required owner review. As workflow.md:658 notes, listing several teams on one rule needs approval from any one of them, not all. | .github/CODEOWNERS:14 | Use `/workspaces/*-prd-*.yaml`. |

The enforced pattern:

```text
^[a-z]{2}-[a-z]{2,4}-[a-z]{2,8}-(brz|slv|gld|ndf)-(poc|dev|sit|uat|stg|prd)-[a-z0-9]{1,6}$
```

Example names that fail it:

- 02:90, :98; 04:34-35; 05:45, :51, :57; 06:38, :50, :53, :105.
- 07:34, :42, :54, :61, :89, :98, :105; 08:40, :42, :44, :121; Cap:36, :39, :43.
- workflow.md:125, :279, :285, :396, :624; mcp-and-skills.md:189.

Production logic keyed on a "prd-" prefix:

- 03:123-125, :133; 04:59, :102, :111; 05:74; 07:107.
- delivery-guide.md:210, :222; workflow.md:256, :451, :546, :558.

### Links

| ID | Location | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| F-60 | identity-model.md:103, 03:163 | Medium | Two Learn links return 404: the service principal admin page and the workspace sensitivity label API (see F-20). The links to six retired skill folders, the `-authoring-cli` folders for activator, eventhouse, eventstream, powerbi, spark and sqldw, also return 404; the F-01 renames fix them. | Link check, 27 Nov 2026 | Replace the first with [Enable SPN admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis) and [Identity support](https://learn.microsoft.com/rest/api/fabric/articles/identity-support). Remove the second with F-20. |
| F-61 | 00:162, identity-model.md:102, 04:140, mcp-and-skills.md:226, :228, copilot-studio-agent.md:26, agent/copilotstudio/README.md:163, agent/appPackage/plugin.json:19, :36, :55 | Low | These links redirect. | Link check, 27 Nov 2026 | Point each one at its current page, listed below. |

Current targets:

- 00:162 and identity-model.md:102: [Create a trust relationship](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust).
- 04:140: [Configure PIM](https://learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-configure).
- mcp-and-skills.md:226 and :228: `what-is-fabric-mcp-server` now lands on the [Fabric MCP servers](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/fabric-mcp-servers-list) list, and `tools-local-mcp-server` lands on `overview-local-mcp-server`.
- copilot-studio-agent.md:26 and agent/copilotstudio/README.md:163: [Agent flows](https://learn.microsoft.com/microsoft-copilot-studio/advanced-flow).
- agent/appPackage/plugin.json:19, :36, :55: targets to verify.

### Site and hygiene

| ID | Location | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| F-71 | README.md:97, :112, challenges-overview.md:3, :63, :341, delivery-guide.md:427, :447, scripts/build-site.mjs:444 | Low | The count "10 challenges" is hard-coded in eight places and goes stale when the new challenges land. | The files listed | Update the count with the new challenges, or word it without a number. |
| F-72 | scripts/build-site.mjs:54, :64, :70-87, .github/workflows/pages.yml | Medium | The site build publishes every Markdown file under `docs/`, so `docs/maintainers/` and this report will appear on the public site once merged. The Pages workflow runs on any change to `docs/**`. | build-site.mjs:54-87 | Decide whether maintainer reports belong on the site (Q-1). If not, add the folder to `SKIP_DIRS`. |
| F-80 | dist/fabric-workspace-provisioner.zip, deployment-handoff.md:95 | High | A packaged build is committed under `dist/`. It no longer matches the source, and deployment-handoff.md:95 tells admins to upload it. | The repo tree | Build the package from source in CI, or stop committing `dist/` (Q-4). |
| F-81 | rules/policy.yaml, api/policy.yaml, 01:39, :143, governance-rules.md:106-108, m365-agent.md:76, :197, mcp-and-skills.md:70-71, setup.md:58, agent/appPackage/instructions.md:32, the sample manifest in `workspaces/` | Medium | The sample domain taxonomy and the country allow-list reflect one market and one industry. A neutral sample suits a public, reusable RVAS better and avoids hinting at an engagement. | The files listed | Replace them with a neutral sample taxonomy (Q-3, B-22). |

Apart from F-80 and F-81, the scan of text files found no customer, person or tenant names, no subscription or tenant IDs and no "Purview hub" framing. The GUIDs under `infra/terraform` are built-in Azure role definition IDs, and the docs use placeholder hostnames.

### Claims checked and still current

- Tenant setting changes take up to 15 minutes to apply.
- The domain Admin API's assign-workspaces call (GA) allows 10 requests a minute. It replaces a workspace's existing domain unless the domain override setting (Preview) blocks it.
- The activity events API (GA) returns one UTC day per call, goes back 28 days and allows 200 requests an hour.
- The e2e-medallion-architecture skill still exists in v0.3.23.
- The Core MCP endpoint is `https://api.fabric.microsoft.com/v1/mcp/core`.
- The data agent is GA, and an SPN can create one.
- An SPN can create and deploy deployment pipelines when "Service principals can create workspaces, connections, and deployment pipelines" is on. All supported item types deploy, up to 300 items per deployment.
- Admin List Workspaces (GA) supports SPNs, allows 200 requests an hour and returns tags and `domainId`.
- `infra/terraform` uses only the `azurerm` provider.
- The domain assignment at 03:89-90 and the admin API tenant settings at 00:56-57 are correct.
- site/challenges.json matches the challenge files for names, durations and dependencies.
