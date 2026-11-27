# Fabric Workspace Provisioner — Copilot Studio agent runbook

Use this runbook to set up the **Copilot Studio agent**: it opens
governance pull requests through two agent flows that call the GitHub REST
API, with **no Azure Function App**. The alternative is the
[Microsoft 365 declarative agent](m365-agent.md), which needs the Function
App in `api/`.

The click-by-click steps, the architecture diagram, the Power Fx
pre-flight and the file layout are in
[`../agent/copilotstudio/README.md`](../agent/copilotstudio/README.md).

## What you will build

```text
Copilot Studio agent
    ├── Topic: Show Policy            → Flow A: FWG - Get Policy
    ├── Topic: Request Workspace      → Flow B: FWG - Submit Workspace Request
    └── Knowledge: docs + policy.yaml (Dataverse files)
```

Both flows are
[agent flows](https://learn.microsoft.com/microsoft-copilot-studio/advanced-flow)
with the **When an agent calls the flow** trigger:

- **FWG - Get Policy** reads `rules/policy.yaml` from `main` and returns it
  as `policyYaml`.
- **FWG - Submit Workspace Request** takes `workspaceName`, `yamlBody` and
  `requesterEmail`. It creates a `request/...` branch, adds
  `workspaces/<workspaceName>.yaml` and opens a pull request, then returns
  `pullRequestUrl`, `pullRequestNumber`, `branch`, `submitted` and `error`.

The flows use the HTTP action because the Power Automate GitHub connector
has no actions to read or write repository files. They read the GitHub
token from Azure Key Vault through a Secret environment variable.

## Constraints to remember

1. An agent flow must answer the agent within 100 seconds, with
   **Asynchronous response** off
   ([create an agent flow](https://learn.microsoft.com/microsoft-copilot-studio/advanced-flow-create)).
   Don't put a long wait, such as an approval, before **Respond to the
   agent**.
2. The repo's policy engine is the **only** source of truth.
   `.github/workflows/validate.yml` runs `scripts/validate.py` on every PR.
   Don't re-implement the rules in Power Fx; only do regex and enum sanity
   checks.
3. The GitHub token is a security boundary. Use a fine-grained personal
   access token limited to the governance repo, with **Contents** and
   **Pull requests** set to read and write. Keep it in Key Vault, turn on
   **Secure Inputs** on every HTTP step, and rotate it before it expires.
4. `System.User.Email` has a value only when the agent authenticates users.
   Keep Microsoft Entra ID authentication on, or the pull request doesn't
   name the requester.

## Steps

Follow "Connect the agent and flows" in the README:

1. Create the agent shell and check its authentication.
2. Store the GitHub token in Key Vault and create a Secret environment
   variable for it.
3. Build and publish **FWG - Get Policy**.
4. Build and publish **FWG - Submit Workspace Request**.
5. Add both flows to the agent as tools.
6. Pull the agent locally.
7. Merge in the topics from `agent/copilotstudio/topics/`, set the two flow
   IDs, and push.
8. Add the knowledge files, then pull again.
9. Test with the three cases in the README.

## Decommission the Function App (when ready)

Once you have piloted the Copilot Studio agent and decided to drop the
Microsoft 365 declarative agent:

1. Delete `agent/appPackage/` and `.github/workflows/agent-build.yml`,
   which builds its package.
2. Run `azd down` in the azd environment you deployed with, or
   `terraform destroy` in `infra/terraform/` if you applied it without azd.
   Either command deletes the Key Vault the module created, so first move
   the Copilot Studio token if you stored it there. The resource group
   `rg-<environment name>` stays, because the module reads it but doesn't
   create it; delete it if nothing else uses it.
3. Delete the GitHub App that the Function App used, or uninstall it from
   the governance repo. The token in Key Vault is then the only credential.
4. Remove `api/`, `infra/` and `azure.yaml` from the repo in a follow-up
   PR, and update the docs that describe the Microsoft 365 option.

Keep the repository's `validate.yml`, `provision.yml`, `drift.yml`,
`scripts/`, `rules/`, `schemas/`, and `workspaces/` unchanged.
They define the governance contract for both options.
