# Fabric Workspace Provisioner — Copilot Studio agent (Function-App-free)

This **Microsoft Copilot Studio** version of the Fabric Workspace Provisioner
uses **agent flows that call the GitHub REST API**:

```text
User in Teams / SharePoint / Power Apps
        │
        ▼
Copilot Studio agent  (this folder)
        │
        ├──► InvokeFlow → "FWG - Get Policy"                (agent flow)
        │                       └─ HTTP: GET contents/rules/policy.yaml
        │
        └──► InvokeFlow → "FWG - Submit Workspace Request"  (agent flow)
                                ├─ HTTP: GET git/ref/heads/main
                                ├─ HTTP: POST git/refs  (new branch)
                                ├─ HTTP: PUT contents/workspaces/<name>.yaml
                                └─ HTTP: POST pulls
                                          │
                                          ▼
                          .github/workflows/validate.yml  (the deterministic gate)
                                          │
                                          ▼
                       Reviewer approval → merge → provision.yml
```

Both flows first read a GitHub token from Azure Key Vault through a Secret
environment variable.

**This request path needs no Azure Function App.** The `api/`, `infra/`, and
`agent/appPackage/` folders support the alternative M365 agent path, not this
option. See "Migration" below before retiring them.

## Why this design

| Concern | Old design (Function App) | This design (agent flows) |
| --- | --- | --- |
| Compute we run | Azure Function (Python v2) + App Service Plan | None |
| Code we maintain | `api/`, `infra/`, OpenAPI plugin | Two agent flows built in the portal |
| GitHub credential storage | Function App settings + Key Vault | Fine-grained token in Key Vault, read by the flows through a Secret environment variable |
| Validation source of truth | Function App rules engine + CI workflow (drift risk) | CI workflow only |
| Pre-flight UX | HTTP call to `/api/validate` | Power Fx in topic, instant |
| Tenant isolation | Hosted in your Azure subscription | Hosted in your Power Platform environment |

The flows use the HTTP action because the Power Automate GitHub connector has
no actions to read or write repository files.

The policy gate is `.github/workflows/validate.yml`, which runs
`scripts/validate.py`. The agent's Power Fx checks give early feedback on
regex and enum errors; they do not replace CI validation.

## Copilot Studio capabilities

The agent uses:

1. **[Agent flows](https://learn.microsoft.com/microsoft-copilot-studio/advanced-flow)
   with the HTTP action**, which replace `/api/submit` and `/api/policy`.
2. **Power Fx in topics**, which replaces `/api/validate`.
3. **Knowledge sources (`FileKnowledgeSource`)** for grounded answers about
   the approval process and the reasons behind the policy.
4. **A conversation variable (`Global.PolicyCache`)** that caches the policy
   file once per conversation.
5. **Microsoft Entra ID authentication.** The request topic sends
   `System.User.Email` to the submit flow as `requesterEmail`. The variable
   has a value only when the agent authenticates users
   ([authentication variables](https://learn.microsoft.com/microsoft-copilot-studio/advanced-end-user-authentication#authentication-variables)).

"Optional enhancements" below covers approvals, Teams posts and other
additions.

## Prerequisites

- VS Code extension `ms-copilotstudio.vscode-copilotstudio`
- The `skills-for-copilot-studio` plugin under `~/.copilot/installed-plugins/`
- A Microsoft Copilot Studio environment in your tenant
- A fine-grained personal access token for a dedicated bot account, limited
  to the governance repo, with **Contents** and **Pull requests** set to
  read and write. Give it an expiry date and rotate it before then. Your
  organization must allow fine-grained tokens and may need to approve this
  one.
- An Azure Key Vault in the same tenant as the Power Platform environment

The flows use a token, not a GitHub App: an app needs a JWT signed with its
private key (RS256) to get each installation token, and flow expressions
can't sign one.

## Repository layout (this folder)

```text
agent/copilotstudio/
├── README.md                              # This runbook
├── agent.mcs.yml                          # Display name, instructions, starters
├── settings.mcs.yml                       # Stub, replaced by the clone
├── topics/
│   ├── greeting.topic.mcs.yml             # OnConversationStart welcome
│   ├── show-policy.topic.mcs.yml          # → FWG - Get Policy flow
│   ├── request-workspace.topic.mcs.yml    # Slot-fill, Power Fx pre-flight, → FWG - Submit Workspace Request flow
│   └── knowledge-search.topic.mcs.yml     # OnUnknownIntent generative answers
├── actions/
│   ├── get-policy.action.mcs.yml          # InvokeFlowTaskAction stub
│   └── submit-workspace.action.mcs.yml    # InvokeFlowTaskAction stub
├── knowledge/
│   └── governance-docs.knowledge.mcs.yml  # FileKnowledgeSource stub
└── variables/
    └── policy-cache.variable.mcs.yml      # Conversation-scoped cache
```

The `*.mcs.yml` files are **scaffolds**. The flow IDs and connection
references are filled in only after you create the corresponding objects
in the portal and run the plugin's `clone`.

Search for `<your-` to find the placeholders.
`crXXX_fabricWorkspaceProvisioner` stands for the agent's real
`schemaName`. The clone in step 6 writes the real `settings.mcs.yml`, and
step 7 sets the prefix in `variables/policy-cache.variable.mcs.yml`.

## Connect the agent and flows

The plugin model is **portal-first**: create the agent and the two agent
flows in Copilot Studio, then clone the agent and push YAML.

### 1. Create the agent shell

In Copilot Studio (`copilotstudio.microsoft.com`):

1. **+ Create → New agent → Skip to configure**.
2. Name: `Fabric Workspace Provisioner`.
3. Copy `agent.mcs.yml`'s `instructions` and `starters` into the portal.
4. **Save**. You now have an empty agent with a real `schemaName`.

New agents use Microsoft Entra ID authentication. Keep it on under
**Settings → Security → Authentication**: with **No authentication**,
`System.User.Email` is empty and the pull request doesn't name the
requester. **Authenticate with Microsoft** signs users in on Teams,
SharePoint, Power Apps and Microsoft Copilot. For other channels, such as a
website, choose **Authenticate manually**, or `System.User.Email` is empty
there.

### 2. Store the GitHub token

The flows read the token through an environment variable of type
**Secret** that points to a Key Vault secret
([Learn](https://learn.microsoft.com/power-apps/maker/data-platform/environmentvariables-azure-key-vault-secrets)).

1. Register the `Microsoft.PowerPlatform` resource provider in the vault's
   Azure subscription.
2. Use the **Azure role-based access control** permission model on the
   vault, and grant **Key Vault Secrets User** to:
   - the people who create or use the environment variable;
   - the Dataverse service principal, application ID
     `00000007-0000-0000-c000-000000000000`.
3. If the vault firewall is on, allow the Power Platform IP addresses. The
   "Trusted Services Only" option doesn't cover Power Platform.
4. Add the token to the vault as a secret, for example
   `<your-github-token-secret>`.
5. In Power Apps (`make.powerapps.com`), open the unmanaged solution you use
   for the agent and select **New → More → Environment variable**. Set
   **Data Type** to **Secret** and **Secret Store** to **Azure Key Vault**,
   then enter the subscription ID, resource group, vault name and secret
   name.
6. Note the variable's schema name, for example
   `<your-prefix>_GitHubToken`. The flows need this name, not the display
   name.

To rotate the token, add a new version of the Key Vault secret.

### 3. Build Flow A: "FWG - Get Policy"

In Copilot Studio, open the agent and select **Tools → Add tool → Agent
flow**. The designer opens with the **When an agent calls the flow** trigger
and the **Respond to the agent** action. Add these steps between them.
`<repo-url>` is the API URL of your governance repo; for the repo
`contoso/fabric-governance`, it's
`https://api.github.com/repos/contoso/fabric-governance`.

| Step | Action | Configuration |
| --- | --- | --- |
| Trigger | When an agent calls the flow | No inputs |
| 1 | Microsoft Dataverse → **Perform an unbound action**, renamed `GetSecret` | Action name: `RetrieveEnvironmentVariableSecretValue`. Environment variable name: the schema name from step 2. Settings: **Secure Outputs** on. |
| 2 | HTTP → **HTTP**, renamed `Get policy` | Method: `GET`. URI: `<repo-url>/contents/rules/policy.yaml?ref=main`. Headers: see below. Settings: **Secure Inputs** on. |
| 3 | Respond to the agent | Output `policyYaml` (Text): `base64ToString(replace(body('Get_policy')?['content'], decodeUriComponent('%0A'), ''))` |

Every HTTP step in both flows sends these headers:

| Header | Value |
| --- | --- |
| `Accept` | `application/vnd.github+json` |
| `Authorization` | Expression `concat('Bearer ', body('GetSecret')['EnvironmentVariableSecretValue'])` |
| `X-GitHub-Api-Version` | `2022-11-28` |

**Secure Inputs** keeps the token out of the run history. Leave **Secure
Outputs** off on the HTTP steps so the run history shows GitHub's error
messages.

In the **Respond to the agent** settings, keep **Asynchronous response** off
(under **Networking**). Name the flow `FWG - Get Policy` and select
**Publish**.

### 4. Build Flow B: "FWG - Submit Workspace Request"

Create a second agent flow the same way and add three **Text** inputs to the
trigger: `workspaceName`, `yamlBody` and `requesterEmail`.

In the steps below, replace each `<...>` with what it names: an input from
**Dynamic content**, or an expression in which an input name stands for that
input. `<repo-url>` is the same as in Flow A. Every HTTP
step sends the headers from step 3 plus `Content-Type: application/json`,
with **Secure Inputs** on.

1. **Compose**, renamed `Branch`:
   `request/<workspaceName>-<utcNow('yyyyMMddHHmmss')>`.
2. **Scope**, renamed `Try`. Steps 3 to 8 go inside it.
3. `GetSecret`, as in Flow A.
4. **HTTP**, renamed `Get main`: `GET <repo-url>/git/ref/heads/main`. The
   commit SHA is `body('Get_main')?['object']?['sha']`.
5. **HTTP**, renamed `Create branch`: `POST <repo-url>/git/refs` with this
   body:

   ```json
   {
     "ref": "refs/heads/<outputs('Branch')>",
     "sha": "<body('Get_main')?['object']?['sha']>"
   }
   ```

6. **HTTP**, renamed `Create file`:
   `PUT <repo-url>/contents/workspaces/<workspaceName>.yaml` with this body:

   ```json
   {
     "message": "Add workspace request <workspaceName>",
     "content": "<base64(yamlBody)>",
     "branch": "<outputs('Branch')>"
   }
   ```

   The body has no `sha`, so this step can only create a file. If
   `workspaces/<workspaceName>.yaml` already exists, GitHub returns 422.
7. **HTTP**, renamed `Open pull request`: `POST <repo-url>/pulls` with this
   body:

   ```json
   {
     "title": "Request workspace <workspaceName>",
     "head": "<outputs('Branch')>",
     "base": "main",
     "body": "Submitted via Copilot Studio by <requesterEmail>."
   }
   ```

8. **Respond to the agent** with these outputs:

   | Output | Type | Value |
   | --- | --- | --- |
   | `pullRequestUrl` | Text | `body('Open_pull_request')?['html_url']` |
   | `pullRequestNumber` | Text | `string(body('Open_pull_request')?['number'])` |
   | `branch` | Text | `outputs('Branch')` |
   | `submitted` | Yes/No | `true` |
   | `error` | Text | Empty (expression `''`) |

9. After `Try`, add a second **Respond to the agent** with the same five
   outputs: `submitted` is `false`, `error` is
   `The GitHub request failed. See the flow run history.`, and the others
   are empty. In its **Configure run after** settings, select **has
   failed**, **has timed out** and **is skipped** for `Try`, and clear **is
   successful**.

Keep **Asynchronous response** off in both **Respond to the agent** actions.
Name the flow `FWG - Submit Workspace Request` and select **Publish**.

A failed run can leave its `request/...` branch behind; delete it in GitHub.

### 5. Add both flows to the agent

A published flow isn't a tool yet. In the agent, select **Tools → Add a tool
→ Flow**, pick **FWG - Get Policy**, select **Add and configure**, and then
**Save**. Repeat for **FWG - Submit Workspace Request**.

For each, set the name and description from the matching YAML in
`actions/`.

On **FWG - Submit Workspace Request**, clear **Allow agent to decide
dynamically when to use the tool**: open the agent's **Tools** page, select
the tool, clear the option under **Details** and select **Save**. The agent
then uses the tool only when a topic calls it
([Learn](https://learn.microsoft.com/microsoft-copilot-studio/add-tools-custom-agent)),
so every submission passes the request topic's Power Fx pre-flight and
takes `requesterEmail` from `System.User.Email`. The option is selected by
default under generative orchestration; left on, it lets the agent call the
flow with a manifest it wrote and an email address taken from the chat.
Keep it selected for **FWG - Get Policy**.

### 6. Clone the agent locally

In a Copilot CLI session:

```text
/copilot-studio:copilot-studio-manage clone
```

The clone creates a folder for the agent and writes `.mcs/conn.json`, which
`push` and `pull` use to find the agent. Its action files carry each flow's
real `flowId`.

### 7. Merge in the topics and the variable

1. Copy the four files in this folder's `topics/` into the clone's
   `topics/` folder.
2. Copy `variables/policy-cache.variable.mcs.yml` into the clone's
   `variables/` folder, and create the folder if it's missing.
   `show-policy.topic.mcs.yml` uses `Global.PolicyCache`; without this file
   the topic has an error and the agent can't be published.
3. In the clone's copy of the variable file, replace
   `crXXX_fabricWorkspaceProvisioner` with the root `schemaName` from the
   clone's `settings.mcs.yml`.
4. Replace `<your-get-policy-flow-id>` in `show-policy.topic.mcs.yml` and
   `<your-submit-flow-id>` in `request-workspace.topic.mcs.yml` with the
   `flowId` values from step 6.

Then push:

```text
/copilot-studio:copilot-studio-manage push
```

### 8. Add the knowledge source

In the portal **Knowledge** tab, select **+ Add knowledge → Files** and
upload:

- `rules/policy.yaml`
- `docs/governance-rules.md`
- `docs/setup.md`
- `docs/workspace-approval-workflow.md`
- `schemas/workspace.schema.json`

Then pull to materialize `knowledge/governance-docs.knowledge.mcs.yml`
with the real Dataverse file IDs:

```text
/copilot-studio:copilot-studio-manage pull
```

### 9. Test

```text
/copilot-studio:copilot-studio-test
```

Cover at least:

- "What teams are approved?" calls **FWG - Get Policy** and shows the
  current `rules/policy.yaml`. Asked again in the same conversation, the
  agent skips "Looking up…" and shows the cached policy.
- "Request a new workspace" with cost center `12345`: the Power Fx
  pre-flight blocks the request before the flow runs.
- A fully valid request calls **FWG - Submit Workspace Request** and
  returns a pull request URL.

## Optional enhancements

Add these only if the delivery needs them:

| Goal | How |
| --- | --- |
| Approval before the pull request opens | The pull request review already gates provisioning. For an earlier approval, add **Approvals → Start and wait for an approval** to Flow B after **Respond to the agent**, and move the GitHub steps after it. An agent flow must respond within 100 seconds, but actions after the response keep running. The agent then gets no pull request URL, so change the topic's result messages and send the URL another way, such as a Teams post. |
| Add the requester as an owner | In the topic's YAML build, append `{"principalType":"User","identifier":"<System.User.Email>","role":"Member"}` to `Topic.OwnersJson`. The owner rules still apply, so users still provide the group owners. |
| Post the pull request URL to a governance Teams channel | Add **Microsoft Teams → Post message in a chat or channel** to Flow B after `Open pull request`. |
| Confirm or cancel with an adaptive card | In `request-workspace.topic`, after the YAML build and before the flow call, add an adaptive card that shows the manifest, and call the flow only when the user confirms. |
| Look up manager or department | Add **Office 365 Users → Get manager (V2)** to Flow B to add org context to the pull request description. |

## Migration: retiring the Function App and the M365 declarative agent

If Copilot Studio will replace the Function App at
`https://<your-function-app>.azurewebsites.net` and `agent/appPackage/`
(M365 declarative agent), use this order:

1. Deploy the Copilot Studio agent (steps 1-9 above) and pilot it with
   one team for a week.
2. Confirm `validate.yml` catches the same blocking findings as
   the old `/api/validate`. Compare the results before retiring that path.
3. Decide whether to keep the M365 declarative agent path:
   - **Keep both**: the Function App stays. Both UIs reach the same PR.
   - **Drop M365**: follow
     [Decommission the Function App](../../docs/copilot-studio-agent.md#decommission-the-function-app-when-ready).
     It removes the compute, the OpenAPI plugin and the GitHub App
     private-key wiring. The governance repo is unchanged.
4. If you dropped the M365 option, update the docs that describe it, such
   as `docs/m365-agent.md` and `docs/deployment-handoff.md`.

The CI workflows (`.github/workflows/validate.yml`,
`.github/workflows/provision.yml`) and the rules engine
(`scripts/validate.py`, `rules/policy.yaml`) are untouched by any
of this. They remain the governance contract.
