# Fabric Workspace Provisioner — Microsoft 365 declarative agent

> **Status: legacy.** This option needs the Azure Functions backend in
> [`api/`](../api/) and the infrastructure in [`infra/`](../infra/). The
> [Copilot Studio agent](copilot-studio-agent.md) opens the same pull request
> through agent flows that call the GitHub REST API, with no Azure compute.
> Keep this option if you need a declarative agent in Microsoft 365 Copilot.
> Otherwise use the Copilot Studio agent and, after a pilot, follow its
> [decommission steps](copilot-studio-agent.md#decommission-the-function-app-when-ready).

A Microsoft 365 Copilot **declarative agent** that lets employees request a new
Microsoft Fabric workspace through chat. The agent collects the answers, checks
them with the same rule engine that gates pull requests in this repository,
and opens a pull request on the user's behalf.

## Why this design

1. **Declarative agent (manifest v1.6) — not a custom engine agent.**
   - Built-in Microsoft 365 Copilot orchestration, no model hosting.
   - Follows the v1.6 schema: `name`, `description`, `instructions`,
     `conversation_starters`, `actions[]`. See
     [`agent/appPackage/declarativeAgent.json`](../agent/appPackage/declarativeAgent.json).
   - Tool calls are described in an **API plugin manifest v2.4**
     ([`plugin.json`](../agent/appPackage/plugin.json)) which points at an
     OpenAPI 3.0 spec ([`openapi.yaml`](../agent/appPackage/openapi.yaml)).

2. **GitHub App + Azure Functions Python v2 backend.**
   - Stateless backend with Managed Identity for Key Vault access.
   - GitHub App auth (JWT → installation token) gives auditable,
     least-privilege PR creation. See
     [`api/shared/github_app.py`](../api/shared/github_app.py).
   - The private key lives in **Key Vault**; the Function reads it through
     **User-Assigned Managed Identity** with the `Key Vault Secrets User` role.

3. **Dual-layer validation — agent-side AND backend-side.**
   - The agent calls `POST /validate` while the user is still chatting so
     mistakes are caught early and explained conversationally.
   - The backend re-runs the same checks inside `POST /submit` before opening
     the PR, regardless of the agent's earlier validation.
   - Both call into [`scripts/rules_engine.py`](../scripts/rules_engine.py),
     which is the single source of truth shared with the existing
     [`scripts/validate.py`](../scripts/validate.py) PR check.

## Repository layout

```text
frontier-fabric-governance-rvas/
├── .github/workflows/agent-build.yml  # Builds the agent package as a run artifact
├── agent/appPackage/             # M365 declarative agent package
│   ├── manifest.json             # Teams app manifest (wraps the agent)
│   ├── declarativeAgent.json     # v1.6 declarative agent manifest
│   ├── instructions.md           # Agent system prompt
│   ├── plugin.json               # v2.4 API plugin manifest
│   ├── openapi.yaml              # OpenAPI 3.0 spec for the backend
│   ├── color.png                 # 192×192 color icon
│   ├── outline.png               # 32×32 outline icon
│   └── ICONS.md                  # Icon requirements
├── api/                          # Azure Functions Python v2 backend
│   ├── function_app.py           # /validate /submit /policy /healthz
│   ├── shared/github_app.py      # GitHub App JWT + PR helpers
│   ├── rules_engine.py           # Copy of scripts/rules_engine.py
│   ├── policy.yaml               # Copy of rules/policy.yaml
│   ├── workspace.schema.json     # Copy of schemas/workspace.schema.json
│   ├── host.json
│   ├── requirements.txt
│   └── local.settings.sample.json
├── infra/terraform/              # Function App, Storage, Key Vault, identity, RBAC (azd uses this)
├── infra/bicep/                  # Bicep equivalent, kept for reference
├── azure.yaml                    # azd up / azd deploy
├── rules/policy.yaml             # Allow-lists, capacities, quotas
├── schemas/workspace.schema.json # JSON Schema for manifests
├── scripts/
│   ├── rules_engine.py           # Shared rule engine (CLI + Function)
│   ├── validate.py               # PR-check CLI (imports rules_engine)
│   ├── provision.py
│   ├── drift.py
│   └── _fabric.py
└── workspaces/                   # Manifest files PR'd by the agent
    └── dev-plt-sample-hello.yaml
```

## End-to-end flow

```text
Employee chats with Copilot
        │
        ▼
M365 declarative agent (instructions.md)
        │  GET  /policy            ← live approved values
        │  POST /validate          ← pre-flight check while chatting
        │  POST /submit            ← only on user confirmation
        ▼
Azure Functions backend (api/)
        │  validate via rules_engine.py (same code as PR check)
        │  Mint GitHub App JWT (key from Key Vault via UAMI)
        │  Branch + commit workspaces/<name>.yaml + open PR
        ▼
GitHub PR opened in this repo
        │
        ▼
PR validation workflow (.github/workflows + scripts/validate.py)
        │  Re-runs the SAME rule engine on the file in the PR
        ▼
Reviewer approves and merges  →  Workspace gets provisioned downstream
```

## Setting up the GitHub App (one-time)

1. **Create the App.** In GitHub, go to **Settings** > **Developer settings** >
   **GitHub Apps** > **New GitHub App**.
   - Repository permissions: `Contents: Read and write`, `Pull requests: Read and write`, `Metadata: Read-only`.
   - No webhooks needed.
   - Generate and download the **private key** (`.pem`).
2. **Install it on this repo only.**
3. Note the **App ID** and the **Installation ID**. To find the installation
   ID, open your organization's **Settings**, select **GitHub Apps** under
   **Third-party Access**, and select **Configure** next to the app. The page
   URL ends with the ID.

## Deploying the backend

You need the Azure CLI, the
[Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd),
the [Terraform CLI](https://developer.hashicorp.com/terraform/install) and
Python 3.11. azd deploys `infra/terraform/`; its
[Terraform support](https://learn.microsoft.com/azure/developer/azure-developer-cli/use-terraform-for-azd)
is in beta and needs no feature flag.

The Terraform module reads the resource group `rg-<environment name>` but
doesn't create it, so create it before the first `azd up`, in the same
subscription and region as the azd environment. Run these commands from the
repository root. The example uses the environment name `fwg-dev`.

```bash
az login
azd auth login
azd env new fwg-dev --subscription <your-subscription-id> --location northeurope
az group create --subscription <your-subscription-id> --name rg-fwg-dev --location northeurope
azd env set GITHUB_APP_ID <app-id>
azd env set GITHUB_INSTALLATION_ID <installation-id>
azd env set GITHUB_OWNER <org>
azd env set GITHUB_REPO frontier-fabric-governance-rvas
azd up
```

`azd up` provisions the infrastructure and deploys `api/`.

Store the GitHub App private key in Key Vault:

```bash
az keyvault secret set \
  --vault-name "$(azd env get-value AZURE_KEY_VAULT_NAME)" \
  --name github-app-private-key \
  --file <your-private-key>.pem
```

Then turn off dry-run mode so `/submit` opens pull requests. Each
`azd provision` or `azd up` sets `DRY_RUN` back to `true`, so repeat this step
after them.

```bash
az functionapp config appsettings set \
  --name "$(azd env get-value AZURE_FUNCTION_APP_NAME)" \
  --resource-group "$(azd env get-value AZURE_RESOURCE_GROUP)" \
  --settings DRY_RUN=false
```

Check that the backend answers:

```bash
HOST=$(azd env get-value AZURE_FUNCTION_APP_HOSTNAME)
curl "https://$HOST/api/healthz"
curl "https://$HOST/api/policy"
```

## Building the agent package

The [Agent build](../.github/workflows/agent-build.yml) workflow builds
`fabric-workspace-provisioner.zip` from `agent/appPackage/` and attaches it to
the run. The committed files keep placeholders: `openapi.yaml` points at
`https://<your-function-app>.azurewebsites.net/api`, and `manifest.json` has
the app ID `55555555-5555-5555-5555-555555555555`. The workflow fills in the
real values.

1. Under **Settings** > **Secrets and variables** > **Actions** > **Variables**,
   add two repository variables:
   - `FUNCTION_APP_HOST`: the output of
     `azd env get-value AZURE_FUNCTION_APP_HOSTNAME`, a host name without
     `https://`.
   - `M365_APP_ID`: a new GUID, for example from `uuidgen`. Keep the same
     value for every build, because the ID identifies the app in your tenant.
2. On the **Actions** tab, open **Agent build** and select **Run workflow**.
   You can enter the host and app ID as run inputs instead of setting the
   variables.
3. Download `fabric-workspace-provisioner.zip` from the run's artifacts.
4. In the Microsoft 365 admin center, go to **Agents** > **All agents** >
   **Add agent** and choose the ZIP file. Under **Publish**, select **Just me**
   or a test group while you try it out. See
   [Upload custom agent](https://learn.microsoft.com/microsoft-agent-365/admin/agent-registry-overview#upload-custom-agent).

The workflow also runs on pushes to `main` that change `agent/appPackage/`.
Without a host, it checks the files and uploads no package. Without an app
ID, it keeps the placeholder and warns. The icons are committed;
[`ICONS.md`](../agent/appPackage/ICONS.md) explains how to replace them.

## Running the backend locally

The sample settings file sets `DRY_RUN=true`, so `/submit` skips the GitHub
call and reports the pull request it would have opened. Use it to test the
agent against a local tunnel without touching the repository.

```bash
cd api
cp local.settings.sample.json local.settings.json
pip install -r requirements.txt
func start
```

## Verifying that the agent and the PR check stay in sync

Both run `validate_schema()` and `apply_rules()` from
[`scripts/rules_engine.py`](../scripts/rules_engine.py). The `prepackage` hook
in `azure.yaml` copies `rules_engine.py`, `workspace.schema.json` and
`policy.yaml` into `api/` before each deploy, so the Function runs
byte-identical rule code. Deploy after rule changes to keep the backend
aligned with the CLI.

To compare, run both on the same manifest:

```bash
HOST=$(azd env get-value AZURE_FUNCTION_APP_HOSTNAME)
python scripts/validate.py workspaces/dev-plt-sample-hello.yaml
curl -X POST "https://$HOST/api/validate" \
  -H 'content-type: application/yaml' \
  --data-binary @workspaces/dev-plt-sample-hello.yaml
```

Both must report the same findings, except `manifest-filename`: only
`validate.py` checks it, because the backend never sees a file name.

## Updating governance rules

Change `rules/policy.yaml`, `schemas/workspace.schema.json` or
`scripts/rules_engine.py` in a pull request, and copy the changed file into
`api/` in the same pull request so the committed copies stay byte-identical.
The PR check enforces the new rules immediately. Run `azd deploy api` to ship
them to the Microsoft 365 agent backend; the `prepackage` hook copies the
files again before packaging. There is no separate rule store.
