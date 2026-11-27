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

## Coverage matrix

C means a core task covers the capability. P means it's mentioned, optional or incomplete. A blank cell means it's absent. "Broken" means the covering task fails as written.

| # | Capability | Status | 00 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | Cap | Overall | Backlog |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Catalog explore and Search API | Explore GA; Search API Preview | | | | P | | P | | | | | Partial | B-30 |
| 2 | OneLake catalog Govern | GA | | | | | | | | | | | Missing | B-18, B-30 |
| 3 | Descriptions, tags, endorsement | GA | | P | P | | | C | | | | P | Covered, broken (F-22) | B-04, B-14, B-30 |
| 4 | Table and column metadata | Preview | | | | | | | | | | | Missing | B-30 |
| 5 | Domains | GA | | | | C | | | | | | | Covered | B-15 |
| 6 | Delegated domain settings | GA | | | | | | | | | | | Missing | B-15 |
| 7 | Workspace roles | GA | | P | | | C | | | | | | Covered | B-16 |
| 8 | Workspace identity, trusted workspace access | GA | | | | | | | | | | | Missing | B-16, B-31 |
| 9 | OneLake security | GA; third-party engines Preview | | | | | | | | | | | Missing | B-16 |
| 10 | Shortcut authentication | Passthrough GA; delegated Preview | | | P | | | | | | | | Partial | B-14 |
| 11 | Fabric policies | Preview | | | | | | | | | | | Missing | B-32 |
| 12 | Tenant settings as code | Admin API GA | P | | | | | | | | | | Partial | B-13, B-32 |
| 13 | Sensitivity labels | GA; domain default Preview | | | | C | | P | | | | | Covered, broken (F-20) | B-05, B-15 |
| 14 | Protection policies, DLP | To verify | | | | P | | | P | | | | Partial | B-15 |
| 15 | Audit, Insider Risk Management, DSPM | Audit GA; DSPM for AI Preview | | | | | | | P | C | | P | Covered, broken (F-24, F-25) | B-08, B-18 |
| 16 | Lineage, impact analysis | GA | | | | | | | | | | | Missing | B-14, B-30 |
| 17 | Data quality | MLV GA | | | | | | | | | | | Missing | B-14, B-30 |
| 18 | Monitoring, chargeback | GA; monitoring workspaces Preview | | | | P | | | | P | | | Partial | B-18 |
| 19 | Capacity and surge protection | GA | P | | | C | | | | | | | Partial (no surge) | B-15 |
| 20 | Network controls | GA | | | | | | | | | | | Missing | B-31 |
| 21 | External sharing | To verify | | | | | | | P | P | | | Partial | B-31, B-32 |
| 22 | Scanner and third-party catalogs | Scanner GA | | | | | | | | | | | Missing | B-30 |
| 23 | Automation tooling | Mixed | P | P | P | P | P | P | P | P | P | P | Partial | B-01, B-15, B-19 |
| 24 | Lifecycle: Git, pipelines, variable libraries | GA; deployment plans Preview | | | | | | | | | C | P | Covered, broken (F-23) | B-09, B-19 |
| 25 | Data agent and Copilot governance | GA | | | | | | | C | | | | Covered (no Copilot settings) | B-07, B-17 |
| 26 | Fabric IQ | Workload Preview; MCP GA | | | | | | | | | | | Missing | B-17 |
| 27 | Purview Data Governance transition | Retiring | | | | | | | | | | | Missing | B-33 |

Totals: 7 covered (4 of them broken), 8 partial and 12 missing.

Notes:

- Row 23: every challenge calls REST or MCP, Skills appear only in 00, 02, 05 and 07, and no challenge uses Terraform, fabric-cicd or the Fabric CLI.
- Row 22: the public blog lists Atlan, Alation, Collibra and Informatica as third-party catalogs that read OneLake metadata ([Fabric blog](https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/onelake-the-unified-foundation-for-data-context-governance-and-ai/5423035)).
- Rows 13 to 15: Purview remains the security and compliance layer. Learn's governance overview says only sensitivity labels, protection policies and DLP need Purview licensing ([Get started with Fabric governance](https://learn.microsoft.com/fabric/governance/get-started-with-fabric-governance)).

## Field patterns

| Field pattern | RVAS today | Backlog |
|---|---|---|
| Domain design | Partial: challenge 03 creates domains, without subdomain rules, domain roles or delegated settings | B-15 |
| Environment model | Partial: names encode environments, but no challenge teaches the choice | B-15, Q-5 |
| One front door for workspace requests | Partial: the approval workflow and agents exist, but their docs disagree with the code | B-11, B-21 |
| Workspace templates | Partial: manifests exist, without tenant setting or tag baselines | B-13 |
| Minimum metadata for gold items | Missing | B-14, B-30 |
| Default label and a first DLP scope | Partial, and the label step fails (F-20) | B-05, B-15 |
| External sharing rules | Missing | B-31, B-32 |
| Exfiltration lab | Missing | B-31 |
| Naming and group conventions | Partial: two standards (F-50) and a group pattern gap (F-54) | B-10 |
| Persona training plan | Missing | B-34 |
| Purview Data Governance transition | Missing | B-33 |

## Repo-rule checks

The README requires each challenge to demonstrate at least one MCP server and at least one Skill (README.md:151-153). The table shows what each challenge does today and the core step that would satisfy the rule.

| Challenge | MCP server | Skill | Proposed core step |
|---|---|---|---|
| 00 | Yes, but the add command fails (F-02) | Yes, but with retired names and a failing install command | Fix F-01 and F-02. |
| 01 | Yes | No | Use search-consumption-cli to confirm the provisioned workspace and its items are findable, and to spot unmanaged workspaces. |
| 02 | Yes | Yes, but with retired names | Fix F-01. |
| 03 | No | No | MCP: use the Core MCP `list_capacities` and `search_catalog` tools. Skill: run onelake-catalog-cli in tenant-admin audit mode. |
| 04 | Yes | No | Skill: run an onelake-catalog-cli audit, or use fabric-policies-cli for "Allow workspace settings editing" (Preview, not in every region). MCP: move to the Core MCP role tools, such as `list_workspace_roles` and `add_workspace_role`, and the OneLake data access role tools. |
| 05 | Yes | Yes (e2e-medallion-architecture) | Fix the `skill run` command (F-02). |
| 06 | Yes | No | Run an onelake-catalog-cli data-owner audit of the data agent's sources, or use fabriciq. |
| 07 | No | Yes, but with retired names | MCP: use the local server's `docs_item-api-spec` tool to look up the Eventstream and Eventhouse item APIs. |
| 08 | Yes, but with tools from the wrong server (F-04) | No | Use deployment-pipelines-authoring-cli and git-integration-operations-cli. |
| Capstone | Not applicable | Not applicable | Cap:57 requires "both Fabric MCP and at least 2 Skills". Keep or relax it (Q-10). |

The challenge files follow the repo's challenge structure, and site/challenges.json matches them:

| Challenge | Duration (minutes) | Depends on |
|---|---|---|
| 00 | 90–120 | None |
| 01 | 90–120 | 00 |
| 02 | 120–180 | 00, 01 |
| 03 | 120–180 | 00, 01 |
| 04 | 120–180 | 00, 01 |
| 05 | 180–240 | 00, 01, 02 |
| 06 | 180–240 | 00, 01, 02, 03, 04 |
| 07 | 240–300 | 00, 01, 02 |
| 08 | 180–240 | 00, 01, 02 |
| Capstone | 240–360 | Any five or more |

The README and challenges-overview.md disagree about which challenge uses which tool (F-07).

## Prioritized backlog

P0 items fix something wrong or broken, or a failure of the repo's own rule. P1 items close a platform-governance gap. P2 items can follow. S means under half a day, M half a day to a day and L more than a day. WP names the work package that owns the item's files.

| ID | Priority | Type | WP | Findings | Target files | Size | Depends on | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|
| B-01 | P0 | Fix | WP-1 | F-01, F-02, F-03, F-04, F-08, F-50, F-61 | docs/mcp-and-skills.md | M | Q-9 | Only skills-for-fabric v0.3.23 Skill names appear. Every install, add and start command works with the current Copilot CLI and Fabric MCP Server 1.8.0. Each tool sits under the server that has it, with its status. Example names pass the enforced pattern, and no link redirects. |
| B-02 | P0 | Fix | WP-1 | F-10 to F-15, F-34, F-60, F-61 | docs/setup.md, identity-model.md, troubleshooting.md, glossary.md, workspace-approval-workflow.md | M | Q-7 | The SPN isn't a Fabric Administrator or capacity admin, holds no Power BI application permissions and isn't in a label policy. It gets capacity contributor and the admin API tenant settings through its security group. Tenant settings carry their current names, with the Govern path first. The Graph permissions are listed, and the 404 and redirecting links are replaced. |
| B-03 | P0 | Fix | WP-3 | F-01, F-02, F-03, F-06, F-08, F-10, F-12, F-13, F-33, F-34, F-50, F-61 | Challenges 00 and 01 | M | Q-2 | Challenge 00 runs end to end with the current Copilot CLI and a least-privilege SPN. Challenge 01 has a core Skill step. Task 5 injects drift that drift.py detects, a description edit until B-20 lands. Example names pass. |
| B-04 | P0 | Fix | WP-4 | F-01, F-02, F-22, F-50 | Challenges 02 and 05 | M | Q-2 | Skill names and the 05:96 command work. Endorsement is declared in the manifest, checked with the scanner or the catalog and applied by a certifier in the UI. Example names pass. |
| B-05 | P0 | Fix | WP-5 | F-01, F-06, F-10, F-15, F-20, F-50, F-60 | Challenge 03 | M | Q-2, Q-7 | Core tasks use an MCP server and a Skill. Labels follow one of the F-20 routes and are checked with the scanner, and no workspace label call remains. Production rules key on `environment`. |
| B-06 | P0 | Fix | WP-6 | F-01, F-06, F-08, F-50, F-61 | Challenge 04 | S | Q-2, Q-9 | A core task uses a Skill. The IT admin MCP server has its current name, its setup steps and an "optional" label. The PIM link is current, and example names pass. |
| B-07 | P0 | Fix | WP-7 | F-01, F-06, F-26, F-27, F-50 | Challenge 06 | M | Q-2 | A core task uses a Skill. DSPM results come from the Purview portal as recorded evidence, not from an API. The data agent prerequisites are complete, and example names pass. |
| B-08 | P0 | Fix | WP-8 | F-01, F-06, F-24, F-25, F-50 | Challenge 07 | L | Q-2 | Webhook events reach the Eventstream custom endpoint through a relay. Audit events come from Real-Time hub Fabric events or Purview Audit search. A core task uses an MCP server, and example names pass. |
| B-09 | P0 | Fix | WP-9 | F-01, F-04, F-06, F-23, F-50 | Challenge 08 | M | Q-2 | Rollback uses `git revert` or a reset, then sync and redeploy, and states the limits in F-23. Operation tools name the right server. A core task uses a Skill, and example names pass. |
| B-10 | P0 | Fix | WP-2 | F-50 (code side), F-51 to F-54, F-56 | scripts/rules_engine.py and its api/ copy, both policy.yaml copies, schemas/, docs/governance-rules.md, agent/appPackage/instructions.md, .github/CODEOWNERS | M | Q-2 | One naming standard holds across the engine, schema, policy, rules doc and agent. The group pattern allows `poc` and `stg`. CODEOWNERS matches six-segment production manifests. The rules/ and api/ copies stay identical, and the sample manifest passes validate.py. |
| B-11 | P0 | Fix | WP-2 | F-09, F-61 (agent files), F-80 | dist/, docs/deployment-handoff.md, docs/copilot-studio-agent.md, agent/ | M | Q-4 | CI builds the package from source, or `dist/` is gone, and deployment-handoff.md says where to get the build. Agent links point to current pages. The flow input and output claim is confirmed or removed. |
| B-12 | P0 | Fix | WP-11 | Listed below | README.md, docs/challenges-overview.md, docs/delivery-guide.md, site/challenges.json, challenges/capstone/ | L | B-01 to B-11 | Every finding listed below is fixed. The README tools table and the overview matrix match the fixed challenges. |
| B-13 | P1 | Extend existing | WP-3 | F-12, F-29, F-55 | Challenges 00 and 01 | M | B-03, B-20 | Challenge 00 lists the tenant settings and permissions each API in the RVAS needs, and exports a tenant settings baseline with the tenant settings Admin API (GA). Challenge 01 declares workspace tags in the manifest, and drift.py reports role drift. Coverage rows: 12. |
| B-14 | P1 | Extend existing | WP-4 | None | Challenges 02 and 05 | L | B-04 | Challenge 02 compares the shortcut authentication modes, passthrough (GA) and delegated (Preview), and notes that a shortcut's mode can't change after creation. Challenge 05 sets a metadata minimum for gold items (description, owner, endorsement, label and tags), adds materialized lake view data quality constraints (GA) and runs a lineage impact analysis (GA) before a change. Coverage rows: 3, 10, 16 and 17. |
| B-15 | P1 | Extend existing | WP-5 | None | Challenge 03 | L | B-05, Q-5 | Domain design follows Learn: one subdomain level, domain names of 40 characters or fewer, a default domain and domain roles, with rename and delete left to Fabric admins. The delegated domain settings are configured and items are tagged. The challenge teaches the environment model chosen in Q-5, sets a default label (domain default label Preview) and a first DLP scope, and adds protection policies (status to verify) and surge protection. An optional Terraform stretch lives in the challenge 03 folder. Coverage rows: 5, 6, 13, 14, 19 and 23. |
| B-16 | P1 | Extend existing | WP-6 | None | Challenge 04 | L | B-06 | OneLake security roles (GA) are kept as code and applied with the bulk PUT, which replaces every role, using dryRun and the ETag. The challenge decides what to keep of DefaultReader, stays within 250 roles per item and 500 members per role, and allows about five minutes for changes to apply. It states that roles restrict only Viewers and users with the Read item permission. It compares the Core MCP single-role upsert (Preview) with the replace-all bulk call, and sets up a workspace identity (GA). Coverage rows: 7, 8 and 9. |
| B-17 | P1 | Extend existing | WP-7 | None | Challenge 06 | M | B-07 | Challenge 06 reviews the Copilot and data agent tenant settings and records DSPM for AI (Preview) evidence from the Purview portal. A stretch task uses Fabric IQ (workload Preview; its MCP server GA). Coverage rows: 25 and 26. |
| B-18 | P1 | Extend existing | WP-8 | None | Challenge 07 | L | B-08 | Challenge 07 adds the admin monitoring workspace and workspace monitoring (Preview), the Capacity Metrics app (GA), chargeback by domain (status to verify), Purview Audit and Insider Risk Management, Govern insights, Real-Time hub Fabric events and an audit check on new external data shares (to verify). Coverage rows: 2, 15 and 18. |
| B-19 | P1 | Extend existing | WP-9 | None | Challenge 08 | M | B-09 | Challenge 08 lists what Git integration and deployment pipelines carry and what they don't, including OneLake security role members and sensitivity labels. It adds variable libraries (GA), deployment plans (Preview) and fabric-cicd. Coverage rows: 23 and 24. |
| B-20 | P1 | Extend existing | WP-2 | F-14 (code side), F-28, F-29, F-33, F-55 | scripts/drift.py, scripts/_fabric.py, scripts/provision.py, scripts/rules_engine.py, api/rules_engine.py | M | B-10 | drift.py reports role drift through the admin APIs. A 401 or 403 stops the scripts with a clear error instead of reporting no drift. Manifest tags map to Fabric workspace tags. The two rules_engine.py copies stay identical. |
| B-21 | P1 | Docs | WP-1 | F-20, F-24, F-26, F-28 to F-32, F-50 (docs side) | docs/workspace-approval-workflow.md, docs/glossary.md | M | B-20 (for F-28) | Every listed finding is fixed in both files. The workflow describes what the scripts do after B-20, and example names pass the enforced pattern. |
| B-22 | P1 | Fix | WP-2 | F-81 | rules/policy.yaml, api/policy.yaml, docs/governance-rules.md, docs/m365-agent.md, agent/appPackage/instructions.md, the sample manifest in workspaces/ | S | Q-3 | The taxonomy chosen in Q-3 replaces the sample one in every listed file. The two policy.yaml copies stay identical, and the sample manifest passes validate.py. |
| B-23 | P1 | Site | WP-11 | F-71, F-72 | site/challenges.json, scripts/build-site.mjs | M | B-12, B-30 to B-34, Q-1, Q-11 | site/challenges.json lists each new challenge with a name, duration and dependencies that match its file. The build publishes docs/maintainers only if Q-1 says so. `npm ci && npm run build:site` passes, and no generated HTML is edited by hand. |
| B-30 | P1 | New challenge | WP-10 | None | New challenge folder | L | Q-11 | Gap: no challenge uses Govern, the catalog Search API, table and column metadata, lineage, data quality or the scanner. Proposal: find, describe, tag, endorse and trace items with Govern (GA), the catalog Search API (Preview) and the scanner (GA), then feed a third-party catalog. Coverage rows: 1 to 4, 16, 17 and 22. |
| B-31 | P1 | New challenge | WP-10 | None | New challenge folder | L | Q-11 | Gap: nothing covers network controls, trusted workspace access or external sharing. Proposal: an exfiltration lab that copies data from a protected workspace to another one, then blocks it with outbound access protection, data connection rules, the connection Admin APIs (to verify) and the tenant allowlist. Coverage rows: 8, 20 and 21. |
| B-32 | P1 | New challenge | WP-10 | None | New challenge folder | L | Q-11 | Gap: tenant settings are managed only by hand, and no challenge covers Fabric policies. Proposal: export and compare tenant settings with the Admin API (GA), delegate settings to domains and capacities, and apply Fabric policies (Preview) with fabric-policies-cli. Whether Terraform has a tenant-setting resource is to verify. Coverage rows: 11, 12 and 21. |
| B-33 | P1 | New challenge | WP-10 | None | New challenge folder | M | Q-11 | Gap: Purview Data Governance is retiring; support ends 12 November 2027, and no content covers the move. Proposal: export the Purview Data Governance estate with Unified Catalog self-serve analytics, map it to OneLake catalog features and record a decision for each gap. Coverage rows: 27. |
| B-34 | P2 | Docs | WP-10 | None | docs/persona-training-plan.md (new) | M | None | Each persona maps to Learn training and to the DP-600, DP-700 and SC-401 certifications. Every link is checked before merge. Whether a governance Applied Skill exists is to verify. |

B-12 fixes these findings in the shared files:

- README.md: F-05, F-06, F-07 and F-71, and the retired Skill framing at README.md:145 (F-01).
- docs/challenges-overview.md: F-01, F-07, F-08, F-23 and F-71.
- docs/delivery-guide.md: F-01, F-08, F-10, F-13, F-15, F-20, F-23, F-24, F-26, F-27, F-50 and F-71.
- site/challenges.json: F-23.
- challenges/capstone/: F-23, F-26 and F-50, plus the Skill count rule at Cap:57 (Q-10).

Each package also fixes these in its own files, including lines that a finding's location list misses: retired Skill names (F-01), failing commands (F-02), example names and "prd-" logic (F-50), the sample taxonomy (F-81), redirecting links (F-61) and Admin portal paths (F-34). The maintainer settles Q-2 and Q-3 before phase 2 starts, so every package uses the same naming pattern and taxonomy.

Each new challenge (B-30 to B-33) follows the repo's challenge format and uses at least one MCP server and one Skill in its core tasks. Its design comes from the research report, docs/maintainers/2026-11-onelake-governance-research.md, so this audit gives only the gap and a one-line proposal.

## Work packages

Each package owns its files, so phase-2 sessions can work in parallel without editing the same file. A file that no package lists belongs to WP-11. Every package waits for Q-2 and Q-3; the last column lists anything else it waits for.

| Package | Files it owns | Backlog | Also waits for |
|---|---|---|---|
| WP-1 Docs | docs/mcp-and-skills.md, docs/setup.md, docs/identity-model.md, docs/troubleshooting.md, docs/glossary.md, docs/workspace-approval-workflow.md | B-01, B-02, B-21 | Q-7, Q-9; B-20 before B-21 |
| WP-2 Code, rules and agents | docs/governance-rules.md, docs/m365-agent.md, docs/copilot-studio-agent.md, docs/deployment-handoff.md, rules/, api/, schemas/, workspaces/, agent/, dist/, scripts/*.py, scripts/requirements.txt, .github/CODEOWNERS, .github/workflows/validate.yml, provision.yml and drift.yml | B-10, B-11, B-20, B-22 | Q-4 |
| WP-3 Challenges 00 and 01 | The challenge 00 and 01 folders | B-03, B-13 | B-20 before B-13 |
| WP-4 Challenges 02 and 05 | The challenge 02 and 05 folders | B-04, B-14 | None |
| WP-5 Challenge 03 | The challenge 03 folder | B-05, B-15 | Q-5, Q-7 |
| WP-6 Challenge 04 | The challenge 04 folder | B-06, B-16 | Q-9 |
| WP-7 Challenge 06 | The challenge 06 folder | B-07, B-17 | None |
| WP-8 Challenge 07 | The challenge 07 folder | B-08, B-18 | None |
| WP-9 Challenge 08 | The challenge 08 folder | B-09, B-19 | None |
| WP-10 New content | New challenge folders, docs/persona-training-plan.md | B-30 to B-34 | Q-6, Q-11 |
| WP-11 Integration | README.md, docs/challenges-overview.md, docs/delivery-guide.md, site/, challenges/capstone/, scripts/*.mjs and every unlisted file | B-12, B-23 | WP-1 to WP-10; Q-1, Q-10, Q-11 |

Sequencing:

1. The maintainer answers Q-2 and Q-3 before phase 2 starts, and each other open question before the package that waits for it.
2. WP-1 to WP-10 run in parallel. Inside each package, the P0 fix lands before the P1 extension. WP-10 can split into one session per new challenge.
3. B-13 (WP-3) and B-21 (WP-1) build on B-20 (WP-2), the only dependencies that cross packages. WP-2 lands B-20 early, or those two items follow it.
4. WP-11 runs last, once the other packages merge. It brings the shared files in line with the changed challenges and checks the site with `npm ci && npm run build:site`. It doesn't edit generated HTML by hand and leaves .github/workflows/pages.yml unchanged.

## Open questions for the maintainer

| ID | Question | Context | Blocks |
|---|---|---|---|
| Q-1 | Should docs/maintainers appear on the public Pages site? | The site build publishes every Markdown file under docs/, so this report goes public once merged (F-72). | B-23 |
| Q-2 | Is the six-segment pattern that the rules engine and schema enforce the canonical naming standard? | Challenge 01 and the approval workflow teach a different one (F-50). | Every package |
| Q-3 | Should a neutral sample taxonomy replace the current one? | The sample domain taxonomy and country allow-list reflect one market and one industry (F-81). | Every package, B-22 |
| Q-4 | Should dist/ leave the repo, with CI building the agent package from source? | The committed package no longer matches the source, and deployment-handoff.md tells admins to upload it (F-80). | B-11 |
| Q-5 | Which environment model should the RVAS teach? | Workspace names encode environments, but no challenge teaches how to choose a model. | B-15 |
| Q-6 | Can core tasks rely on Preview features? | Fabric policies (Preview) aren't available in every region, and several P1 items and new challenges use Preview features. Until it's answered, packages label each Preview step and keep a GA route for core tasks where one exists. | WP-10 |
| Q-7 | Is a human step acceptable for applying sensitivity labels? | Bulk Set Labels takes a Fabric admin user only, and whether a service principal can call SetLabelsAsAdmin is to verify (F-20). | B-02, B-05 |
| Q-8 | Should the RVAS keep Power BI admin APIs where no Fabric API exists yet? | Tenant settings and Bulk Set Labels now have Fabric admin APIs, but the activity events API and SetLabelsAsAdmin are still Power BI admin APIs (F-30). | None; informs B-20 and B-21 |
| Q-9 | Should the IT admin MCP server stay optional? | It supports delegated sign-in only, so a service principal can't run it. | B-01, B-06 |
| Q-10 | Should the capstone keep "both Fabric MCP and at least 2 Skills" (Cap:57)? | Five challenges use no Skill in their core tasks today. | B-12 |
| Q-11 | Where do the new challenges sit: numbering, stage and dependencies? | The placement drives site/challenges.json, the README and the overview. | B-23, B-30 to B-33 |

## Sources

The "Recent platform changes" table links the announcements, release notes and changelogs. The coverage matrix statuses come from these pages, checked on 27 November 2026.

| Row | Capability | Status sources |
|---|---|---|
| 1 | Catalog explore and Search API | [Explore](https://learn.microsoft.com/fabric/governance/onelake-catalog-explore), [Catalog search](https://learn.microsoft.com/rest/api/fabric/core/catalog/search) |
| 2 | OneLake catalog Govern | [Govern](https://learn.microsoft.com/fabric/governance/onelake-catalog-govern) |
| 3 | Descriptions, tags, endorsement | [Item details](https://learn.microsoft.com/fabric/governance/onelake-catalog-item-details), [Tags](https://learn.microsoft.com/fabric/governance/tags-overview), [Endorsement](https://learn.microsoft.com/fabric/governance/endorsement-overview) |
| 4 | Table and column metadata | [Additional table metadata](https://learn.microsoft.com/fabric/onelake/table-apis/additional-table-metadata) |
| 5, 6 | Domains, delegated domain settings | [Domains](https://learn.microsoft.com/fabric/governance/domains), [Domains admin API](https://learn.microsoft.com/rest/api/fabric/admin/domains) |
| 7 | Workspace roles | [Workspace roles](https://learn.microsoft.com/fabric/fundamentals/roles-workspaces) |
| 8 | Workspace identity, trusted workspace access | [Workspace identity](https://learn.microsoft.com/fabric/security/workspace-identity), [Trusted workspace access](https://learn.microsoft.com/fabric/security/security-trusted-workspace-access) |
| 9 | OneLake security | [Access control model](https://learn.microsoft.com/fabric/onelake/security/data-access-control-model) |
| 10 | Shortcut authentication | [Shortcut security](https://learn.microsoft.com/fabric/onelake/onelake-shortcut-security) |
| 11 | Fabric policies | [Fabric policies](https://learn.microsoft.com/fabric/governance/fabric-policies-overview) |
| 12 | Tenant settings as code | [Tenants admin API](https://learn.microsoft.com/rest/api/fabric/admin/tenants), [Tenant settings](https://learn.microsoft.com/fabric/admin/about-tenant-settings) |
| 13 | Sensitivity labels | [Information protection](https://learn.microsoft.com/fabric/governance/information-protection), [Domain default label](https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label) |
| 14 | Protection policies, DLP | [Protection policies](https://learn.microsoft.com/fabric/governance/protection-policies-overview), [DLP for Fabric and Power BI](https://learn.microsoft.com/purview/dlp-powerbi-get-started) |
| 15 | Audit, Insider Risk Management, DSPM | [Track user activities](https://learn.microsoft.com/fabric/admin/track-user-activities), [Insider Risk Management indicators](https://learn.microsoft.com/purview/insider-risk-management-settings-policy-indicators#microsoft-fabric-indicators), [Purview for Copilot in Fabric](https://learn.microsoft.com/purview/ai-copilot-fabric) |
| 16 | Lineage, impact analysis | [Lineage](https://learn.microsoft.com/fabric/governance/lineage), [Impact analysis](https://learn.microsoft.com/fabric/governance/impact-analysis) |
| 17 | Data quality | [Data quality](https://learn.microsoft.com/fabric/data-engineering/materialized-lake-views/data-quality) |
| 18 | Monitoring, chargeback | [Admin monitoring workspace](https://learn.microsoft.com/fabric/admin/monitoring-workspace), [Workspace monitoring](https://learn.microsoft.com/fabric/fundamentals/workspace-monitoring-overview), [Metrics app](https://learn.microsoft.com/fabric/enterprise/metrics-app), [Chargeback](https://learn.microsoft.com/fabric/enterprise/chargeback-app) |
| 19 | Capacity and surge protection | [Surge protection](https://learn.microsoft.com/fabric/enterprise/surge-protection) |
| 20 | Network controls | [Private links](https://learn.microsoft.com/fabric/security/security-private-links-overview), [Outbound access protection](https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview) |
| 21 | External sharing | [External data sharing](https://learn.microsoft.com/fabric/governance/external-data-sharing-overview) |
| 22 | Scanner and third-party catalogs | [Metadata scanning](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview), [Fabric blog](https://community.fabric.microsoft.com/blog/fbc_fabricupdatesblogs/onelake-the-unified-foundation-for-data-context-governance-and-ai/5423035) |
| 23 | Automation tooling | [Fabric MCP servers](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/fabric-mcp-servers-list), [skills-for-fabric changelog](https://github.com/microsoft/skills-for-fabric/blob/main/CHANGELOG.md), [Terraform Registry](https://registry.terraform.io/providers/microsoft/fabric/latest/docs), [fabric-cicd](https://microsoft.github.io/fabric-cicd/), [Fabric CLI releases](https://github.com/microsoft/fabric-cli/releases) |
| 24 | Lifecycle: Git, pipelines, variable libraries | [Git integration](https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration), [Deployment pipelines](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines), [Variable libraries](https://learn.microsoft.com/fabric/cicd/variable-library/variable-library-overview) |
| 25 | Data agent and Copilot governance | [Data agent](https://learn.microsoft.com/fabric/data-science/concept-data-agent), [Data agent tenant settings](https://learn.microsoft.com/fabric/data-science/data-agent-tenant-settings) |
| 26 | Fabric IQ | [Fabric IQ](https://learn.microsoft.com/fabric/iq/overview), [Fabric IQ MCP server](https://learn.microsoft.com/fabric/iq/connectors/fabric-iq-mcp) |
| 27 | Purview Data Governance transition | [Tech Community](https://techcommunity.microsoft.com/blog/microsoft-security-blog/a-next-step-in-the-evolution-of-the-microsoft-data-governance-strategy/4572227), [Partner Center](https://learn.microsoft.com/partner-center/announcements/2026-november#update-on-the-microsoft-data-governance-strategy), [Unified Catalog self-serve analytics](https://learn.microsoft.com/purview/unified-catalog-self-serve-analytics) |
