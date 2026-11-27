# Fabric Workspace Governance Agent — deployment handoff

This record describes a deployment of the backend for the
[Microsoft 365 declarative agent](m365-agent.md). Replace each `<your-…>`
value with the names for your environment; `azd env get-values` lists them.

- **Date deployed:** `<YYYY-MM-DD>`
- **Subscription:** `<your-subscription>` (`00000000-0000-0000-0000-000000000000`)
- **Tenant:** `11111111-1111-1111-1111-111111111111`
- **Resource group:** `<your-resource-group>`, region `northeurope`. The
  Terraform module expects `rg-<azd environment name>`.

## What is live in Azure

| Resource | Name | Notes |
| --- | --- | --- |
| Function App (Flex Consumption FC1) | `<your-function-app>` | Python 3.11, v2 programming model, 4 HTTP triggers |
| User-assigned managed identity | `<your-identity>` | Client ID `22222222-2222-2222-2222-222222222222` |
| Key Vault (RBAC, 7-day soft delete) | `<your-key-vault>` | URL `https://<your-key-vault>.vault.azure.net/` |
| Storage account | `<your-storage-account>` | Blob container `app-package` holds the Function deployment package |
| Application Insights and Log Analytics | `<your-app-insights>` and `<your-log-analytics>` | Workspace-based |

The Function App reaches Storage and Key Vault through the user-assigned
identity, so its app settings hold no storage keys or secrets.

## Live API endpoints

Base URL: `https://<your-function-app>.azurewebsites.net/api`

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/healthz` | Anonymous | Liveness probe; returns `{"status":"ok"}` |
| GET | `/policy` | Anonymous | Approved teams, domains, sensitivity labels, cost centers, environments and capacities; the agent offers these as choices |
| POST | `/validate` | Anonymous | Schema and governance rule check; returns blocking and warning findings |
| POST | `/submit` | Anonymous | Validates, then opens a governance pull request on GitHub. While `DRY_RUN=true`, it returns a synthetic pull request URL without calling GitHub. |

## Smoke tests

Run these from the repository root after each deploy:

```bash
HOST=$(azd env get-value AZURE_FUNCTION_APP_HOSTNAME)
curl "https://$HOST/api/healthz"
curl "https://$HOST/api/policy"
curl -X POST "https://$HOST/api/validate" -H 'content-type: application/yaml' --data-binary @workspaces/dev-plt-sample-hello.yaml
curl -X POST "https://$HOST/api/validate" -H 'content-type: application/json' --data '{"name": "BAD-NAME"}'
```

Expected results, in order:

1. `{"status":"ok"}`.
2. The allow-lists from `rules/policy.yaml`.
3. `"passed": true` for the sample manifest.
4. `"passed": false`, with blocking findings for the missing required fields
   and the name pattern.

## Microsoft 365 agent package

The [Agent build](../.github/workflows/agent-build.yml) workflow builds
`fabric-workspace-provisioner.zip` from `agent/appPackage/` and attaches it to
the run; [Building the agent package](m365-agent.md#building-the-agent-package)
has the steps. The workflow sets the OpenAPI server URL from the
`FUNCTION_APP_HOST` repository variable and the app ID from `M365_APP_ID`.
Without `M365_APP_ID`, the package keeps the placeholder ID
`55555555-5555-5555-5555-555555555555`.

```text
manifest.json           Teams app manifest v1.19
declarativeAgent.json   Declarative agent v1.6 (instructions and plugin reference)
instructions.md         System prompt for the agent
plugin.json             API plugin v2.4 (auth.type = None)
openapi.yaml            OpenAPI 3.0; the server URL points to the Function App
color.png               192×192 color icon
outline.png             32×32 outline icon
```

## Remaining manual steps

While `DRY_RUN=true`, the agent validates input and returns a synthetic pull
request URL, so pull request creation on GitHub is untested. Complete these
steps to open real pull requests.

### 1. Create the GitHub App

1. In GitHub, go to **Settings** > **Developer settings** > **GitHub Apps** >
   **New GitHub App**.
2. Repository permissions: **Contents: Read and write**, **Pull requests: Read
   and write**, **Metadata: Read-only**.
3. Webhook: not required; clear **Active**.
4. Generate a private key (PEM). Note the **App ID**.
5. Install the app on the repository. Note the **Installation ID**; the URL of
   the installation's **Configure** page ends with it.

### 2. Upload the private key to Key Vault

```bash
az keyvault secret set \
  --vault-name "$(azd env get-value AZURE_KEY_VAULT_NAME)" \
  --name github-app-private-key \
  --file <your-private-key>.pem
```

The Function reads the secret name from the app setting
`GITHUB_PRIVATE_KEY_SECRET` (default `github-app-private-key`).

### 3. Set the IDs and turn off dry-run mode

`azd provision` writes the GitHub settings from the azd environment and sets
`DRY_RUN` back to `true`. Keep the IDs in the azd environment, provision, and
then turn off dry-run mode. Repeat the last command after every
`azd provision` or `azd up`.

```bash
azd env set GITHUB_APP_ID <your-app-id>
azd env set GITHUB_INSTALLATION_ID <your-installation-id>
azd env set GITHUB_OWNER <your-github-org-or-user>
azd env set GITHUB_REPO <your-repo-name>
azd provision
az functionapp config appsettings set \
  --resource-group "$(azd env get-value AZURE_RESOURCE_GROUP)" \
  --name "$(azd env get-value AZURE_FUNCTION_APP_NAME)" \
  --settings DRY_RUN=false
```

`GITHUB_BASE_BRANCH` defaults to `main`. Changing app settings restarts the
app, which then uses the new values.

### 4. Upload the agent

Run the Agent build workflow and download `fabric-workspace-provisioner.zip`
from the run's artifacts. Then upload it in either admin center:

- Microsoft 365 admin center: **Agents** > **All agents** > **Add agent**.
  Under **Publish**, select who can install it, such as **Just me** or a test
  group while you try it out. See
  [Upload custom agent](https://learn.microsoft.com/microsoft-agent-365/admin/agent-registry-overview#upload-custom-agent).
- Teams admin center: **Teams apps** > **Manage apps** > **Upload new app**.

### 5. Optional: require Entra ID on the Function

The four routes are anonymous because the plugin uses `auth.type = None`. To
require Entra ID, follow
[Configure Microsoft Entra SSO authentication](https://learn.microsoft.com/plugins/plugin-authentication-entra-sso):

1. In the Azure portal, open the Function App's **Authentication** page and
   add Microsoft as the identity provider. See
   [Configure Microsoft Entra authentication](https://learn.microsoft.com/azure/app-service/configure-authentication-provider-aad).
   The app registration it creates secures the API.
2. In the Teams developer portal, select **Tools** > **Microsoft Entra SSO
   client ID registration** and register that app's client ID, with
   `https://<your-function-app>.azurewebsites.net/api` as the base URL. The
   registration returns an auth config ID and an Application ID URI.
3. Update the app registration and the allowed token audiences as steps 3
   and 4 of the Learn page describe.
4. In `plugin.json`, set the runtime `auth` to `OAuthPluginVault`, with
   `reference_id` set to the auth config ID. No client secret goes in Key
   Vault or the package.
5. Run Agent build again and upload the new package.

## How the rule engine stays in sync

The PR check (`scripts/validate.py`) and the `/validate` endpoint run the same
`rules_engine.py`. The Function package needs flat copies of the canonical
files next to `function_app.py`:

- `scripts/rules_engine.py` → `api/rules_engine.py`
- `schemas/workspace.schema.json` → `api/workspace.schema.json`
- `rules/policy.yaml` → `api/policy.yaml`

The `prepackage` hook of the `api` service in `azure.yaml` copies these files
before each deploy. The copies are also committed to `api/`, because some azd
flows skip the hook, so a pull request that changes a canonical file must
update its copy too. After a change, run `azd deploy api`.

## Diagnostic commands

Read the names from the azd environment first:

```bash
RG=$(azd env get-value AZURE_RESOURCE_GROUP)
FUNC=$(azd env get-value AZURE_FUNCTION_APP_NAME)
HOST=$(azd env get-value AZURE_FUNCTION_APP_HOSTNAME)
APPI=$(az resource list -g "$RG" --resource-type Microsoft.Insights/components --query "[0].name" -o tsv)
ST=$(az resource list -g "$RG" --resource-type Microsoft.Storage/storageAccounts --query "[0].name" -o tsv)
```

Show the last 15 minutes of traces and exceptions from Application Insights:

```bash
APPID=$(az monitor app-insights component show -g "$RG" -a "$APPI" --query appId -o tsv)
az monitor app-insights query --app "$APPID" --analytics-query \
  "union traces, exceptions | where timestamp > ago(15m) | order by timestamp desc | take 50"
```

List the registered functions with the host master key:

```bash
KEY=$(az functionapp keys list -g "$RG" -n "$FUNC" --query masterKey -o tsv)
curl -sS -H "x-functions-key: $KEY" "https://$HOST/admin/functions"
```

List the deployed packages:

```bash
az storage blob list --account-name "$ST" --container-name app-package \
  --auth-mode login -o table
```

## Files of interest

- [api/function_app.py](../api/function_app.py) — HTTP backend
- [api/shared/github_app.py](../api/shared/github_app.py) — GitHub App auth and pull request creation
- [agent/appPackage/manifest.json](../agent/appPackage/manifest.json) — Teams app manifest
- [agent/appPackage/openapi.yaml](../agent/appPackage/openapi.yaml) — API contract for the plugin
- [agent/appPackage/instructions.md](../agent/appPackage/instructions.md) — agent system prompt
- [.github/workflows/agent-build.yml](../.github/workflows/agent-build.yml) — builds the agent package
- [infra/terraform/](../infra/terraform/) — the infrastructure azd deploys; [infra/bicep/main.bicep](../infra/bicep/main.bicep) is the Bicep equivalent
- [azure.yaml](../azure.yaml) — azd service and `prepackage` hook
