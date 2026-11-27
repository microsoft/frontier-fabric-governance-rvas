# Fabric MCP servers and Skills for Fabric

Set these up in Challenge 00. Come back when a challenge needs a server or a Skill.

## TL;DR

- The **Fabric Core MCP Server** (remote, GA) manages workspaces, workspace roles, folders and items, plus OneLake shortcuts, data access roles and settings. It acts as the identity you sign in with, usually you.
- The **Fabric MCP Server** (local, GA) adds offline API docs, OneLake files and tables, jobs and Data Factory tools.
- **Skills for Fabric** (v0.3.23) teach the agent one workload each. Invoke a Skill with `/SKILL-NAME`.
- Use the agent to look and to draft. Change the tenant through pull requests.

## Fabric MCP servers

Challenge 00 installs the first two servers. The rest are optional. Statuses were checked on 2026-11-27 on each server's Learn page; the [Fabric MCP servers list](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/fabric-mcp-servers-list) has the current set.

| Server | Runs | Status | Use it to |
|---|---|---|---|
| [Fabric Core MCP Server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server) | Remote | GA | Manage workspaces, workspace roles, folders, items, and OneLake shortcuts, data access roles and settings |
| [Fabric MCP Server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/pro-dev-local/overview-local-mcp-server) | Local | GA | Read API docs offline, work with OneLake files and tables, run jobs and use Data Factory tools |
| [Hosted OneLake MCP](https://learn.microsoft.com/fabric/onelake/onelake-hosted-mcp) | Remote | Preview | Browse files, inspect table metadata and manage directories in one item |
| [Data Warehouse MCP](https://learn.microsoft.com/fabric/data-warehouse/data-warehouse-mcp-server) | Remote | Preview | Run T-SQL against a warehouse or SQL analytics endpoint |
| [Eventhouse MCP](https://learn.microsoft.com/fabric/real-time-intelligence/mcp-remote-eventhouse) | Remote | Preview | Discover schemas and run KQL against Eventhouse data |
| [Activator MCP](https://learn.microsoft.com/fabric/real-time-intelligence/mcp-remote-activator) | Remote | Preview | Create and manage monitoring rules |
| [Operations agent MCP](https://learn.microsoft.com/fabric/real-time-intelligence/mcp-overview) | Remote | Preview | Configure operations agent instructions, playbooks and monitoring |
| [Fabric IQ MCP](https://learn.microsoft.com/fabric/iq/connectors/fabric-iq-mcp) | Remote | GA | Find reports and semantic models and run read-only DAX queries as the signed-in user |
| [Power BI Authoring MCP](https://learn.microsoft.com/power-bi/developer/mcp/power-bi-authoring-mcp) | Remote or local | Remote Preview, local GA | Author semantic models |
| [Data agent MCP](https://learn.microsoft.com/fabric/data-science/data-agent-mcp-server) | Remote | GA | Ask a published data agent questions grounded in its data sources |
| [Ontology MCP](https://learn.microsoft.com/fabric/iq/ontology/how-to-use-ontology-mcp-server) | Remote | Preview | Give the agent an ontology's entities, relationships and definitions |
| [Real-Time Intelligence MCP](https://learn.microsoft.com/fabric/real-time-intelligence/mcp-local-server) | Local | Preview | Work with Eventhouse, Eventstreams, Activator, maps and Azure Data Explorer |
| [DataFactory MCP](https://github.com/microsoft/DataFactory.MCP) | Local | Preview | Manage Data Factory connections, dataflows, pipelines, copy jobs and Airflow jobs |

The Microsoft MCP Server for IT Admins is a Microsoft Graph server, not a Fabric one. It has its own optional section below.

## Fabric Core MCP Server

The endpoint is `https://api.fabric.microsoft.com/v1/mcp/core`. Calls run as the identity your MCP client signs in with, usually you. The server applies your tenant settings, access controls and audit logs, and adds none of its own.

### Tools

| Area | Tools |
|---|---|
| Catalog | `search_catalog` |
| Workspaces | `list_workspaces`, `get_workspace`, `create_workspace`, `update_workspace`, `delete_workspace` |
| Workspace roles | `list_workspace_roles`, `get_workspace_role`, `add_workspace_role`, `update_workspace_role`, `delete_workspace_role` |
| Items | `list_items`, `get_item`, `create_item`, `update_item`, `delete_item`, `get_item_definition`, `update_item_definition`, `bulk_move_items` |
| Folders | `list_folders`, `get_folder`, `create_folder`, `update_folder`, `move_folder`, `delete_folder` |
| Capacities | `list_capacities` |
| OneLake shortcuts | `onelake_list_shortcuts`, `onelake_get_shortcut`, `onelake_create_shortcut`, `onelake_create_shortcuts_in_bulk`, `onelake_delete_shortcut`, `onelake_reset_shortcut_cache` |
| OneLake data access roles | `onelake_list_data_access_roles`, `onelake_create_or_update_single_data_access_role`, `onelake_create_or_update_data_access_roles`, `onelake_delete_data_access_role` |
| OneLake settings | `onelake_get_settings`, `onelake_modify_default_tier`, `onelake_modify_diagnostics`, `onelake_modify_immutability_policy` |
| Guidance | `get_knowledge` |

- The workspace role tools take Microsoft Entra object IDs, not email addresses. To look up an object ID from chat, add the optional IT admin server described below.
- The Core server has no tools for long-running operations. Use the local server's `core_get-operation-state` and `core_get-operation-result`, or [Get Operation State](https://learn.microsoft.com/rest/api/fabric/core/long-running-operations/get-operation-state) in REST.
- `get_knowledge` returns Fabric guidance and best practices, such as for item types.

`onelake_create_or_update_data_access_roles` replaces every data access role on the item. A role you leave out of the request loses its access grants. Set `DryRun` to `true` first to validate the replacement without applying it. In REST, the same call also takes the roles' ETag in `If-Match`, so it fails if someone changed the roles after you read them. It needs Reshare permission on the item.

> **Preview** (checked 2026-11-27): single data access role calls — [Learn](https://learn.microsoft.com/rest/api/fabric/core/onelake-data-access-security/create-or-update-single-data-access-role). GA route: onelake_create_or_update_data_access_roles with a dry run first.

To change one role and leave the others alone, use `onelake_create_or_update_single_data_access_role`. It needs Member or higher on the workspace. Both role calls need `OneLake.ReadWrite.All` and allow 50 calls a minute. An item can have 250 roles with 500 members each, and a change takes about 5 minutes to apply.

### Permissions

The delegated scopes `Catalog.Read.All`, `Workspace.ReadWrite.All`, `Item.ReadWrite.All`, `Capacity.Read.All` and `OneLake.ReadWrite.All` cover every tool. Your MCP client handles the token, consent and Conditional Access. If sign-in says the client needs admin approval, ask an Entra administrator to consent. A service principal or managed identity can also connect once the tenant setting "Service principals can call Fabric public APIs" includes it; [setup](setup.md) shows where to turn it on. Details: [Core MCP permissions](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/permissions-core-mcp-server).

### Install

In a terminal, add the server to Copilot CLI:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
```

In a Copilot CLI session:

```text
/mcp add
```

In the form, enter the name `fabric`, choose **HTTP**, paste the URL, leave **Tools** as `*` and press Ctrl+S. The server is available without a restart. Copilot CLI asks you to sign in with Microsoft Entra ID; to sign in again later, run `/mcp auth fabric` in a session.

Both ways write the server to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "fabric": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/core",
      "headers": {},
      "tools": ["*"]
    }
  }
}
```

A repository can also define servers in `.mcp.json` or `.github/mcp.json`. Project config wins over `~/.copilot/mcp-config.json`, `.mcp.json` wins over `.github/mcp.json`, and Copilot CLI loads either one only after you trust the folder. Reference secrets as `${VAR}` instead of writing them into the file.

In VS Code, run **MCP: Add Server**, choose **HTTP**, enter the URL and name the server `fabric`. Or add it to `.vscode/mcp.json`:

```json
{
  "servers": {
    "fabric": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/core"
    }
  }
}
```

Copilot CLI doesn't read `.vscode/mcp.json`.

### Check that it works

Ask the agent:

```text
List my Fabric workspaces.
Show the role assignments for the workspace "dev-plt-sample-hello".
What items are in "dev-plt-sample-hello"?
What tools do you have for Fabric?
```

The second and third prompts work once Challenge 01 creates `dev-plt-sample-hello`.

If the agent can't connect, call the endpoint yourself with an Azure CLI token:

```bash
TOKEN=$(az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)
curl -s https://api.fabric.microsoft.com/v1/mcp/core \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

A list of tools means your identity and tenant settings work, so the problem is in the client config.

| Error | Cause | Fix |
|---|---|---|
| `401` with `TokenIsMissing` | The client sent no token | Run `/mcp auth fabric`, or remove and re-add the server |
| `401` with JSON-RPC code `-32600` | The token is invalid or expired | Run `/mcp auth fabric`, or remove and re-add the server |
| `-32602`, `Tool <name> not found` | The tool name is wrong or the client's tool list is stale | Check the name in the tools table and reconnect the server |
| `WorkspaceNotFound` or `EntityNotFound` | The ID is wrong, or your role doesn't let you see it | Check the ID and your workspace role |

Most errors arrive inside the tool result with `isError` set to `true`, not as an HTTP error, so read the tool output. [Troubleshooting](troubleshooting.md) has more fixes.

Workspace and role changes you make in chat skip review, and `scripts/drift.py` reports them as drift. Use chat to look, and pull requests to change.

## Fabric MCP Server (local)

The local server runs on your machine and needs Node.js 22 or later:

```bash
npx -y @microsoft/fabric-mcp@latest server start --mode all
```

| Toolset | Covers | Sign-in |
|---|---|---|
| `docs` | Offline API specs, item definitions, examples and best practices | None |
| `core` | Workspaces, role assignments, items and definitions, folders, capacities, catalog search, and long-running operations | Yes |
| `jobs` | On-demand jobs, job instances and schedules | Yes |
| `onelake` | Files, directories, tables, shortcuts, data access roles and settings | Yes |
| `datafactory` | Pipelines and Dataflow Gen2 | Yes |

The `docs` tools are `docs_list-item-types`, `docs_item-api-spec`, `docs_platform-api-spec`, `docs_item-definitions`, `docs_best-practices` and `docs_api-examples`.
Older prompts may use `docs_workloads` (now `docs_list-item-types`) and `docs_workload-api-spec` (now `docs_item-api-spec`).

Add it to Copilot CLI:

```bash
copilot mcp add fabric-local -- npx -y @microsoft/fabric-mcp@latest server start --mode all
```

To load fewer tools, add `--namespace <toolset>` once for each toolset you want, such as `--namespace docs --namespace onelake`. Add `--read-only` to turn off the tools that change resources. Both options apply when the server starts, so restart it or start a new Copilot CLI session, then check the tool list.

In VS Code, install the [Fabric MCP Server](https://marketplace.visualstudio.com/items?itemName=fabric.vscode-fabric-mcp-server) extension, which needs GitHub Copilot Chat. Choose toolsets in `fabricMcp.enabledServices` (empty means all) and set `fabricMcp.readOnly` to `true` for read-only mode. If an old setting lists `publicapis`, replace it with `docs`. The server is also a .NET tool: `dotnet tool install --global Microsoft.Fabric.Mcp` installs the `fabmcp` command.

The live toolsets use your `az login` session, or a service principal from `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` and `AZURE_CLIENT_CERTIFICATE_PATH` (or `AZURE_CLIENT_SECRET`). Tools act as that identity. Some tools read and write local files, and the local server doesn't emit Fabric audit logs. Running it locally doesn't keep your data local: your MCP client and model still process the tool results. Review each tool call before you approve it.

| You want to | Use |
|---|---|
| Change workspaces, roles, items or folders | Core |
| Change OneLake shortcuts or data access roles | Core |
| Search the OneLake catalog | Core |
| Look up an API spec, item definition or best practice | Local `docs` |
| Read or upload OneLake files and tables | Local `onelake` |
| Track a long-running operation | Local `core` |
| Run a job or manage a schedule | Local `jobs` |

## Hosted OneLake MCP

> **Preview** (checked 2026-11-27): Hosted OneLake MCP — [Learn](https://learn.microsoft.com/fabric/onelake/onelake-hosted-mcp). GA route: the local Fabric MCP Server's onelake tools, or the Core MCP Server for shortcuts and data access roles.

This server works inside one item, at `{oneLakeHost}/v1.0/workspaces/{workspaceId}/items/{itemId}/mcp`. To connect, you need:

- An MCP client that supports Streamable HTTP and can attach a bearer token. The client gets and refreshes the token itself.
- A Microsoft Entra token for the Azure Storage audience. A token for the Fabric API doesn't work.
- An identity with permission for the operations you need on the item's data.

Four of its 15 tools are marked destructive, and file and blob deletion can't be undone, so keep tool approval on. Start with `onelake_list_items_data`, then `onelake_list_files`. `onelake_get_principal_access` can report `canRead: false` for a caller who can read the item, so never use it as an access check.

## Optional: Microsoft MCP Server for IT Admins

No challenge needs this server. It reads and manages Microsoft Entra data and reads Intune data through Microsoft Graph, for example to find the object ID behind an email address. It uses delegated permissions only, so it always runs as a signed-in user and never as the automation service principal. It asks you to confirm each change and works only in the global cloud. The Core tools page still calls it the Microsoft MCP Server for Enterprise, and its older `/enterprise` endpoint is being replaced by `/admin`.

Set it up once per tenant:

1. A Cloud Application Administrator or Application Administrator registers an app for **Accounts in this organizational directory only**.
2. Add the redirect URI under **Mobile and desktop applications**, not **Web**. Copilot CLI and the GitHub Copilot app use `http://127.0.0.1`, which the **Redirect URIs** box rejects, so add it to `publicClient.redirectUris` in the app's **Manifest**. VS Code uses `http://localhost`.
3. Under **API permissions**, add the delegated Microsoft Graph permissions `MCP.Server.Access`, `User.Read` and `EntitlementMgmt-SubjectAccess.ReadWrite` (for `request_access`), plus the permissions your scenario needs, such as `User.Read.All`.
4. Grant admin consent.
5. Optional: in **Enterprise applications**, set **Assignment required?** to **Yes** and assign users or groups.

Users also need the Entra roles for the Graph operations they run. Dynamic client registration isn't supported.

For Copilot CLI, add the server to `~/.copilot/mcp-config.json` with your app's client ID:

```json
{
  "mcpServers": {
    "mcp-admin": {
      "type": "http",
      "url": "https://mcp.svc.cloud.microsoft/admin",
      "headers": {},
      "tools": ["*"],
      "oauthClientId": "<REGISTERED_APP_CLIENT_ID>",
      "oauthPublicClient": true
    }
  }
}
```

In the GitHub Copilot app, use **Customize** > **MCP** > **Add server** > **HTTP** with the same name, URL and client ID. In VS Code, put the client ID in `oauth.clientId` in `mcp.json`. See the [overview](https://learn.microsoft.com/graph/mcp-server/overview) and [Get started](https://learn.microsoft.com/graph/mcp-server/get-started).

## What no MCP tool covers

No MCP server has tools for these tasks. Use REST, a Skill, the [Fabric CLI](https://microsoft.github.io/fabric-cli/) (v1.9.0) or the [Terraform provider](https://registry.terraform.io/providers/microsoft/fabric/latest/docs) `microsoft/fabric` (v1.15.1).

| Task | Use |
|---|---|
| Tags | Read them with [List Tags](https://learn.microsoft.com/rest/api/fabric/core/tags/list-tags): `Tag.Read.All`, 25 requests a minute, service principals supported, no admin setting. A Fabric or domain administrator creates tags in the Admin portal or with the [admin Tags APIs](https://learn.microsoft.com/rest/api/fabric/admin/tags). An item takes at most 10 tags. |
| Domains | The GA [Domains admin APIs](https://learn.microsoft.com/rest/api/fabric/admin/domains). The Preview Domains APIs were retired. |
| Tenant settings | **OneLake catalog** > **Govern** > **Configurations** > **Tenant settings**, or the Admin portal. For code, Terraform `fabric_tenant_setting` (GA, works with a service principal) or [REST](https://learn.microsoft.com/rest/api/fabric/admin/tenants) (25 requests a minute). |
| Sensitivity labels | A manual step in the item's settings, a domain default label (Preview), or admin [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels), which only a Fabric administrator user can call. Labels apply to items; there's no workspace label API. |
| Admin APIs | REST or `/onelake-catalog-cli`. Activity events return one UTC day per call, for the last 28 days. |
| External data shares | [REST](https://learn.microsoft.com/rest/api/fabric/admin/external-data-shares-provider), 10 requests a minute. |
| Network rules | [REST](https://learn.microsoft.com/rest/api/fabric/core/workspaces/set-network-communication-policy), with the workspace Admin role. A PUT replaces the whole policy, and an omitted `defaultAction` becomes `Allow`, so get the policy first and send all of it back. |
| Git integration | `/git-integration-operations-cli` or the Fabric CLI. |
| Fabric policies | `/fabric-policies-cli`. Fabric policies are in Preview. REST activates policy sets at tenant scope (Admin Policy Sets, by a Fabric admin) and at capacity scope ([PolicySet Activation](https://learn.microsoft.com/rest/api/fabric/policyset/activation/activate), by a capacity admin); Git can't activate them. The skill keeps external data sharing policies design-only, because its bundled beta REST `PolicyType` enum lacks the type. A Fabric admin [creates the policy set](https://learn.microsoft.com/fabric/governance/fabric-policies-get-started) from a workspace on a Fabric capacity (New item > Policy set, Fabric tenant scope), adds the rules and activates it from that workspace. The Policies Center manages active policies but doesn't create policy sets. Policies aren't available in North Europe (the sample region), West Europe or West US. |

## Unattended runs

Copilot CLI can run a prompt with no one at the keyboard:

```bash
copilot -p "List the workspaces whose names start with dev-plt-" --allow-tool 'fabric(list_workspaces)'
```

In a `-p` run, any tool call that would ask for approval is denied, so allow each tool the prompt needs with `--allow-tool`. `--deny-tool` wins over `--allow-tool`. Use `--allow-all` only in a sandbox. Authenticate with a fine-grained personal access token that you own and that has the "Copilot Requests" permission, in `COPILOT_GITHUB_TOKEN`; classic tokens aren't supported. See [Run Copilot CLI programmatically](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically) and [Authenticate Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli).

This repository's workflows don't use an agent. They call the Fabric REST API with OIDC.

## Skills for Fabric

Install Skills for Fabric v0.3.23 as Copilot CLI plugins:

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
copilot plugin install powerbi-authoring@fabric-collection
```

In a Copilot CLI session:

```text
/plugin marketplace add microsoft/skills-for-fabric
/plugin install fabric-skills@fabric-collection
/plugin install powerbi-authoring@fabric-collection
/skills list
```

`powerbi-authoring` adds `semantic-model-authoring`, `powerbi-report-cli` and a local Power BI modeling server. Update with `copilot plugin update --all`. The older plugin names `skills-for-fabric`, `fabric-authoring`, `fabric-consumption` and `fabric-operations` resolve to `fabric-skills`.

`fabric-skills` also registers three MCP servers: `FabricIQ` (Fabric IQ MCP), `powerbi-modeling-mcp` (the remote Power BI Authoring MCP) and `fabric-sqlendpoint` (the Data Warehouse MCP). It doesn't register the Core MCP Server, so add `fabric` as shown above.

To install single Skills with [APM](https://github.com/microsoft/apm) instead, install them globally and sign in to Azure:

```bash
apm install microsoft/skills-for-fabric --skill spark-cli --target copilot -g
az login
```

Without `-g`, APM writes the MCP config to `.vscode/mcp.json`, which Copilot CLI doesn't read.

Invoke a Skill with `/SKILL-NAME`, followed by your request.
`gh copilot` stopped working on 2025-10-25, and there's no `copilot skill install` or `skill run`.

| Skill | Use it for |
|---|---|
| `onelake-catalog-cli` | Tenant and data-owner audits through the Admin, Core and Power BI APIs, with guarded fixes and a curate mode |
| `search-consumption-cli` | Finding items across the OneLake catalog |
| `fabric-policies-cli` | Fabric policies and PolicySet items |
| `deployment-pipelines-authoring-cli` | Deployment pipelines |
| `git-integration-operations-cli` | Workspace Git integration |
| `e2e-medallion-architecture` | An end-to-end medallion build |
| `spark-cli` | Notebooks and Livy sessions |
| `sqldw-cli` | Warehouses, SQL analytics endpoints and Query Insights |
| `eventhouse-cli` | KQL databases |
| `eventstream-cli` | Eventstreams |
| `activator-cli` | Activator (Reflex) rules |
| `dataflows-cli` | Dataflow Gen2 |
| `semantic-model-authoring` | Semantic models, DAX and Direct Lake |
| `powerbi-report-cli` | Power BI reports in PBIR format |
| `fabriciq` | Natural-language questions over reports and semantic models |

- `/eventhouse-cli` works inside an existing KQL database. Create the Eventhouse first with the Core server's `create_item`.
- `/activator-cli` needs the KQL database item ID and the workspace ID. Use a "becomes" condition and explicit `startTime` and `endTime` values, not `ago()`.
- For tenant-wide audits, `/onelake-catalog-cli` calls admin APIs, so run it as a Fabric administrator or as a service principal allowed to call read-only admin APIs.
- No Skill manages OneLake security roles or network rules. Change roles with the Core server and network rules with REST, then prove the result with `spark-cli` or `sqldw-cli`.

For example:

```text
/eventhouse-cli In the KQL database "gov_audit" in workspace "dev-plt-audit", create the tables "pr_events" and "fabric_activity".
```

The Skill chooses its tools, often Core MCP tools and Fabric REST calls, and reports what it did.

### Retired Skill names

Older material uses retired names. Use the current ones:

| Retired | Current |
|---|---|
| `spark-*-cli` | `spark-cli` |
| `sqldw-*-cli` | `sqldw-cli` |
| `eventhouse-*-cli` | `eventhouse-cli` |
| `eventstream-*-cli` | `eventstream-cli` |
| `activator-authoring-cli` | `activator-cli` |
| `dataflows-authoring-cli` | `dataflows-cli` |
| `powerbi-authoring-cli` | `semantic-model-authoring` (models) or `powerbi-report-cli` (reports) |
| `powerbi-consumption-cli` | `fabriciq` (natural-language questions) or `semantic-model-authoring` (DAX `INFO` metadata) |
| `onelake-catalog-govern-cli` | `onelake-catalog-cli` |

(`*` is authoring, consumption or operations). None ships in v0.3.23. They changed across releases v0.3.2 to v0.3.20, so never attribute them to a single release.

## How the pieces fit

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Author or reviewer                                                   │
│  • opens a PR with a workspace manifest                              │
│  • asks the agent whether the tenant matches the manifest            │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Agent in VS Code or Copilot CLI                                      │
│  • picks the MCP tool or Skill                                       │
│  • reads tenant state, drafts items, edits the YAML manifest         │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ GitHub: validate.yml checks naming and policy rules on the PR        │
│         provision.yml applies merged manifests (OIDC, Fabric REST)   │
│         drift.yml reports drift daily in an issue, changes nothing   │
└──────────────────────────────────────────────────────────────────────┘
```

Explore and draft with the agent. Change the tenant through pull requests.

## Further reading

- [Fabric MCP servers](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/fabric-mcp-servers-list)
- [Fabric Core MCP Server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Get started with Fabric Core MCP Server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/get-started-core)
- [Get started with Fabric MCP Server (local)](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/pro-dev-local/get-started-local)
- [Fabric MCP Server tool list](https://github.com/microsoft/mcp/blob/main/servers/Fabric.Mcp.Server/README.md#available-tools)
- [Add MCP servers to Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)
- [Copilot CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
- [Fabric REST API reference](https://learn.microsoft.com/rest/api/fabric/articles/)
