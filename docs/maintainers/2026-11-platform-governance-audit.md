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
