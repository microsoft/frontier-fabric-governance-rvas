# Challenge 00 — Tenant, identity, and tooling setup

> **Outcome:** Your tenant is ready for workspace-as-code. A private copy of
> this repository signs in to Fabric as a least-privilege service principal
> through OpenID Connect (OIDC), with no stored secret, and Copilot CLI has the
> Fabric MCP servers and Skills working. The copy also holds a baseline of your
> tenant settings.

## Why this challenge exists

Every later challenge changes Fabric through one chain:

```text
pull request
  → GitHub Actions workflow on your self-hosted runner
  → OIDC token from GitHub, exchanged for a Microsoft Entra token
  → service principal gh-fabric-workspace-provisioner
  → Fabric REST API
```

The service principal (SPN) gets only what the workflows need. It's never a
Fabric administrator or a capacity administrator. Instead, its security group is
enabled in four tenant settings and has Contributor permissions on the capacity.
There's no client secret to leak: each workflow run gets a short-lived token
through OIDC.

Copilot CLI is your console for the rest of the challenges. Its MCP tools and
Skills act as you, with your Fabric permissions, not as the SPN. Use chat to
look, and pull requests to change.

## Learning objectives

1. Make a private copy of this repository and run its validator.
2. Connect Copilot CLI to the Fabric Core MCP server and the local Fabric MCP
   server, and install the Fabric Skills.
3. Create an SPN that signs in from GitHub Actions through OIDC, with no secret
   and no admin role.
4. Enable the four service principal tenant settings for one security group,
   starting from **Govern** in the OneLake catalog.
5. Give that group Contributor permissions on a capacity.
6. Configure the repository: variables, code owners, the `production`
   environment, a self-hosted runner and a ruleset that protects `main`.
7. Match each API call the scripts make to the tenant setting, role or
   permission it needs.
8. Save a baseline of your tenant settings with the admin API.

## Prerequisites

- A Fabric tenant where you're a Fabric administrator, and a capacity where
  you're a capacity administrator. You use both roles for this setup only.
- The capacity is an F SKU, F2 or larger, not a trial.
- In Microsoft Entra ID, you can create app registrations and security groups,
  and a Privileged Role Administrator or Global Administrator can grant admin
  consent for Microsoft Graph application permissions.
- A GitHub organization on GitHub Enterprise Cloud where you can create private
  repositories. Required reviewers on environments in private repositories need
  Enterprise Cloud.
- A Copilot plan, with Copilot CLI allowed by your organization or enterprise
  policy.
- A workstation with Node.js 22 or later, Python 3.12 or later, Git, the Azure
  CLI (`az`) and the GitHub CLI (`gh`).
- A machine for a self-hosted GitHub Actions runner, with Python 3.12 or later
  (including `venv`) and the Azure CLI. Your workstation works for a lab.

## Tasks

### Task 1 — Make a private copy

This repository is a blueprint. Work in a private copy in your organization,
and keep Actions off until Task 7 has configured it. In a terminal:

```bash
git clone https://github.com/microsoft/frontier-fabric-governance-rvas.git fabric-governance
cd fabric-governance
git remote rename origin upstream
gh repo create your-org/fabric-governance --private
gh api --method PUT repos/your-org/fabric-governance/actions/permissions -F enabled=false
git remote add origin https://github.com/your-org/fabric-governance.git
gh repo set-default your-org/fabric-governance
git push -u origin main
```

Replace `your-org` with your organization, here and in later commands.
`gh repo set-default` makes later `gh` commands in this folder target your
copy. Without it, `gh` picks the `upstream` remote, this repository.

Create a Python environment and run the validator:

```bash
python3 -m venv .venv
.venv/bin/pip install --quiet -r scripts/requirements.txt
.venv/bin/python scripts/validate.py
```

It checks every manifest in `workspaces/`, so far only the sample
`workspaces/dev-plt-sample-hello.yaml`, and prints a report with
`**Overall:** ✅ PASS`.

### Task 2 — Connect Copilot CLI to Fabric

Install Copilot CLI and start it:

```bash
npm install -g @github/copilot
copilot
```

In a Copilot CLI session:

```text
/login
```

For other install options, such as WinGet, Homebrew and an install script, see
[Installing GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli).

Add the Fabric Core MCP server. It's generally available, Microsoft hosts it,
and it acts as you. Then add the local Fabric MCP server
(`@microsoft/fabric-mcp`, v1.8.0). Its docs tools need no sign-in, and its live
tools use your `az login` session.

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot mcp add fabric-local -- npx -y @microsoft/fabric-mcp@latest server start --mode all
copilot mcp list
```

`copilot mcp list` shows both servers. You can also add servers with `/mcp add`
in a session, or by editing `~/.copilot/mcp-config.json`. In VS Code, the
extension `fabric.vscode-fabric-mcp-server` runs the local server.

Sign in to the Core server. In a Copilot CLI session:

```text
/mcp auth fabric
```

### Task 3 — Install the Fabric Skills

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

For the Power BI authoring Skills, also run
`copilot plugin install powerbi-authoring@fabric-collection`.

In a Copilot CLI session:

```text
/skills list
```

The list includes `onelake-catalog-cli`, the first governance Skill you'll use.
You run a Skill as `/SKILL-NAME` followed by your request. To update the
Skills, run `copilot plugin update --all`.

`gh copilot` stopped working on 2025-10-25, and the commands
`copilot skill install` and `copilot skill run` don't exist.

### Task 4 — Create the service principal

No MCP tool covers Microsoft Entra ID, so use the Azure CLI. Create the app, its
service principal and its security group:

```bash
az login --allow-no-subscriptions
APP_ID=$(az ad app create --display-name gh-fabric-workspace-provisioner --query appId -o tsv)
SP_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
az ad group create --display-name sg-fabric-workspace-provisioner --mail-nickname sg-fabric-workspace-provisioner
az ad group member add --group sg-fabric-workspace-provisioner --member-id "$SP_ID"
```

Add a federated credential for each way a workflow signs in. GitHub issues an
OIDC token, and Microsoft Entra ID exchanges it for an access token, so the
repository stores no secret:

```bash
az ad app federated-credential create --id "$APP_ID" --parameters '{"name":"github-pull-request","issuer":"https://token.actions.githubusercontent.com","subject":"repo:your-org/fabric-governance:pull_request","audiences":["api://AzureADTokenExchange"]}'
az ad app federated-credential create --id "$APP_ID" --parameters '{"name":"github-main","issuer":"https://token.actions.githubusercontent.com","subject":"repo:your-org/fabric-governance:ref:refs/heads/main","audiences":["api://AzureADTokenExchange"]}'
az ad app federated-credential create --id "$APP_ID" --parameters '{"name":"github-production","issuer":"https://token.actions.githubusercontent.com","subject":"repo:your-org/fabric-governance:environment:production","audiences":["api://AzureADTokenExchange"]}'
```

| Workflow  | Runs for                                         | Credential subject                                       |
| --------- | ------------------------------------------------ | -------------------------------------------------------- |
| validate  | pull requests                                    | `repo:your-org/fabric-governance:pull_request`           |
| drift     | `main`, daily or on demand                       | `repo:your-org/fabric-governance:ref:refs/heads/main`    |
| provision | merges to `main`, after approval in `production` | `repo:your-org/fabric-governance:environment:production` |

If your organization customizes the OIDC subject claim, use its format instead.

The scripts check groups and resolve users through Microsoft Graph. In the
Microsoft Entra admin center, open **App registrations** >
`gh-fabric-workspace-provisioner` > **API permissions** > **Add a permission** >
**Microsoft Graph** > **Application permissions**. Add `GroupMember.Read.All`
(or `Group.Read.All`) and `User.Read.All`, then select **Grant admin consent**.
A Privileged Role Administrator or Global Administrator grants it.

The SPN gets nothing else. It:

- isn't a Fabric administrator or a capacity administrator;
- has no Power BI Service permissions that need admin consent, such as
  `Tenant.ReadWrite.All`, because admin APIs reject service principals that
  have them;
- has no client secret or certificate;
- isn't included in a sensitivity label policy.

### Task 5 — Turn on the service principal tenant settings

No MCP tool covers tenant settings, so use the Fabric portal. Open the OneLake
catalog, select **Govern**, then **Configurations** > **Tenant settings**. If
**Govern** isn't there, for example because tenant-level Private Link is on,
use **Settings** (⚙) > **Admin portal** > **Tenant settings**.

Enable each setting below for **Specific security groups**, with only
`sg-fabric-workspace-provisioner`:

| Setting | Section | Why the SPN needs it |
| ------- | ------- | -------------------- |
| Service principals can create workspaces, connections, and deployment pipelines | Developer settings | provision.py creates workspaces. It's off by default in new tenants. |
| Service principals can call Fabric public APIs | Developer settings | The scripts' other core API calls, such as adding workspace roles. Task 10 lists them. |
| Service principals can access read-only admin APIs | Admin API settings | drift.py lists every workspace and its access. |
| Service principals can access admin APIs used for updates | Admin API settings | Challenge 03 assigns workspaces to domains. |

The first two replaced the single setting **Service principals can use Fabric
APIs**. If **Create workspaces**, under Workspace settings, is limited to
specific security groups, add `sg-fabric-workspace-provisioner` there too.
Changes take up to 15 minutes to apply.

The updates setting lets the SPN call every admin API that changes the tenant,
including Update Tenant Setting. Keep only this SPN in the group, and limit who
can change the repository's workflows and approve the `production` environment.

### Task 6 — Give the group capacity Contributor permissions

Open your capacity in **Govern** > **Configurations** > **Capacities**, or in
**Admin portal** > **Capacity settings** > **Fabric capacity**. Under
**Contributor permissions**, select **Specific users or security groups** and
add `sg-fabric-workspace-provisioner`. If the group isn't accepted, add the SPN
`gh-fabric-workspace-provisioner` itself.

Don't make either one a capacity administrator. Contributor permissions let the
SPN create workspaces on the capacity, and assign a workspace to it when the SPN
is that workspace's Admin.

Find the capacity ID. In a Copilot CLI session with the Fabric Core MCP
connected:

```text
List my Fabric capacities and show each one's ID, SKU, region and state.
```

Copilot calls `list_capacities`. Save the ID as a repository variable, with
your capacity's ID in place of the placeholder value:

```bash
CAPACITY_ID=33333333-3333-3333-3333-333333333333
gh variable set FABRIC_CAPACITY_ID --body "$CAPACITY_ID"
```

[`rules/policy.yaml`](../../rules/policy.yaml) approves two capacities with
placeholder IDs: `contosononprodf2` for `sbx`, `dev` and `stg`, and
`contosoprodf4` for `prd`. While the IDs are placeholders, provision.py uses
`FABRIC_CAPACITY_ID`, so both resolve to your lab capacity. Leave the file as it
is.

### Task 7 — Configure the repository

No MCP tool covers GitHub settings, so use `gh` and the repository settings.

Set the variables the workflows read:

```bash
APP_ID=$(az ad app list --display-name gh-fabric-workspace-provisioner --query "[0].appId" -o tsv)
gh variable set AZURE_CLIENT_ID --body "$APP_ID"
gh variable set AZURE_TENANT_ID --body "$(az account show --query tenantId -o tsv)"
```

Leave `LIVE_CHECKS` and `DRY_RUN` unset, so both are `false`. Challenge 01 turns
on live checks.

Code owners approve every change. In
[`.github/CODEOWNERS`](../../.github/CODEOWNERS), replace
`@your-org/fabric-governance-maintainers` with your team or your GitHub handle,
then push the file:

```bash
git add .github/CODEOWNERS
git commit -m "Set code owners"
git push
```

Create the labels the drift workflow puts on its issues:

```bash
gh label create drift
gh label create governance
```

Create the approval gate for provisioning. In **Settings** > **Environments**,
create `production` and add yourself or your team under **Required reviewers**.
Under **Deployment branches and tags**, choose **Selected branches and tags**
and add `main`.

Turn Actions back on, and turn off the workflow that publishes this
repository's website, which your copy doesn't need:

```bash
gh api --method PUT repos/your-org/fabric-governance/actions/permissions -F enabled=true
gh workflow disable pages.yml
```

The validate, provision and drift workflows run on a self-hosted runner with
the label `fabric-gov`. In **Settings** > **Actions** > **Runners** > **New
self-hosted runner**, follow the commands for the runner machine's operating
system. When the configuration script asks for labels, enter `fabric-gov`.

Each job signs the Azure CLI in as the SPN, and the `azure/login` action clears
every sign-in from the Azure CLI profile when the job ends. A runner that runs
as your own user shares your profile, so each job would sign you out too. Give
the runner its own profile. In the runner folder, run:

```bash
echo "AZURE_CONFIG_DIR=$HOME/.azure-fabric-gov-runner" >> .env
```

The runner reads `.env` when it starts, so restart it if it's already running.

### Task 8 — Smoke test the chain

In a Copilot CLI session with both Fabric MCP servers connected, send each
prompt and check which tool answers it:

| Prompt | Server | Tool |
| ------ | ------ | ---- |
| List the Fabric workspaces I can access. | `fabric` | `list_workspaces` |
| List my Fabric capacities. | `fabric` | `list_capacities` |
| What Fabric item types are available? | `fabric-local` | `docs_list-item-types` |
| Show the API specification for the Lakehouse item type. | `fabric-local` | `docs_item-api-spec` |

Then run the governance Skill. In a Copilot CLI session:

```text
/onelake-catalog-cli In dataowner-audit mode, which workspaces I administer have no domain assigned?
```

The dataowner-audit mode calls the Core API as you, so it covers the workspaces
you administer. Challenge 03 assigns domains to the workspaces this repository
manages.

Now test the OIDC chain with a pull request that changes a manifest:

```bash
git switch -c smoke-test
printf '\n' >> workspaces/dev-plt-sample-hello.yaml
git commit -am "Smoke test the validate workflow"
git push -u origin smoke-test
gh pr create --draft --fill
sleep 15
gh pr checks smoke-test --watch
```

`gh pr checks` stops with "no checks reported" if the run hasn't started yet;
run it again. The `validate` check passes and posts a comment with
`**Overall:** ✅ PASS`. In the run's log, the
**Azure login (OIDC, optional live checks)** step shows
`Azure CLI login succeeds by using OIDC.` That step can fail without failing
the check, so read it. Then close the pull request:

```bash
git switch main
gh pr close smoke-test --delete-branch
```

Run the drift check on demand:

```bash
gh workflow run drift.yml
```

The run succeeds and opens an issue, **Fabric workspace drift detected**,
labeled `drift` and `governance`. drift.py exited with code 2 because it found
differences: the report lists the sample under Missing, because nothing has
provisioned it yet, and your tenant's other workspaces under Unmanaged. Close
the issue:

```bash
ISSUE=$(gh issue list --label drift --json number --jq '.[0].number')
gh issue close "$ISSUE"
```

If the run fails with exit code 3, a call returned 401 or 403. The log names the
API and the setting to check; settings can take 15 minutes to apply.

### Task 9 — Protect main

Now that `validate` has run once, require it. In **Settings** > **Rules** >
**Rulesets**, select **New ruleset** > **New branch ruleset**:

1. Name it `protect-main`, set **Enforcement status** to **Active**, and add
   the default branch under **Target branches**.
2. Turn on **Require a pull request before merging**, with 1 required approval
   and **Require review from Code Owners**.
3. Turn on **Require status checks to pass** and add `validate`.
4. Turn on **Block force pushes**.
5. In a solo lab you can't approve your own pull requests. Add **Repository
   admin** to the bypass list with **For pull requests only**, so you can merge
   your pull requests but can't push to `main` directly.

`validate` runs only when a pull request changes `workspaces/`, `rules/`,
`schemas/`, `scripts/` or the workflow file. A pull request that changes other
files never reports the check, so merging it also needs the bypass.

### Task 10 — Check permissions and save a tenant settings baseline

Each call the scripts make needs a tenant setting, a role or a permission.
When a call returns 401 or 403, find it here:

| Call | Made by | Tenant setting | Role or permission |
| ---- | ------- | -------------- | ------------------ |
| Create Workspace | provision.py | Service principals can create workspaces, connections, and deployment pipelines | Contributor permissions on the capacity |
| Update Workspace | provision.py | Service principals can call Fabric public APIs | Admin of the workspace |
| Assign to Capacity | provision.py | Service principals can call Fabric public APIs | Admin of the workspace and Contributor permissions on the capacity |
| Add Workspace Role Assignment | provision.py | Service principals can call Fabric public APIs | Member or higher; only an Admin adds an Admin |
| List Workspace Role Assignments | provision.py | Service principals can call Fabric public APIs | Member or higher |
| Get Workspace | provision.py | Service principals can call Fabric public APIs | Viewer or higher |
| List Workspaces | provision.py, drift.py | Service principals can call Fabric public APIs | None; it lists only the workspaces the caller has a role on |
| List Capacities | provision.py, if it has no capacity ID | Service principals can call Fabric public APIs | None; it lists only the capacities the caller administers or has Contributor permissions on |
| List Tags | provision.py, validate.py live checks | Service principals can call Fabric public APIs | None |
| Apply Workspace Tags (Preview) | provision.py | Service principals can call Fabric public APIs | Admin of the workspace |
| Admin List Workspaces, List Workspace Access Details (Preview) | drift.py | Service principals can access read-only admin APIs | None |
| Get group (Microsoft Graph) | validate.py live checks | None | `GroupMember.Read.All` or `Group.Read.All` |
| Get user (Microsoft Graph) | provision.py | None | `User.Read.All` |
| List Tenant Settings | export_tenant_settings.py, run as you | None | Fabric administrator |

Tasks 4 to 6 gave the SPN its settings and permissions, and it's Admin of each
workspace it creates. Admin List Workspaces and List Workspace Access Details
each allow 200 requests an hour, and drift.py calls Access Details once for
each managed workspace. List Tags and List Tenant Settings allow 25 requests a
minute. When a call returns 429, `_fabric.py` waits and retries. Challenge 03
adds admin calls for domains and the metadata scanner, which need the two
admin API settings from Task 5.

A Fabric administrator can change any tenant setting in the portal, with no
pull request or review. Save a baseline now, while the settings are as you set
them in Task 5, so challenge 12 can compare later exports with it. No MCP tool
reads tenant settings, so a script calls the admin REST API. Work on a branch:

```bash
git switch -c tenant-baseline
```

Save this as `scripts/export_tenant_settings.py`. It reuses the sign-in,
retries and paging in `_fabric.py`:

```python
#!/usr/bin/env python3
"""Save the tenant settings to tenant/export/<YYYY-MM-DD>.json.

Run it as a Fabric administrator. The file holds one JSON object with the
settings under "tenantSettings". Exit codes: 0 saved; 3 a call returned 401 or 403.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import _fabric as fab

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = REPO_ROOT / "tenant" / "export"
EXIT_AUTH = 3
HINT = ("Run this as a Fabric administrator, or as a service principal in the tenant "
        "setting 'Service principals can access read-only admin APIs'.")


def main() -> int:
    try:
        settings = fab._paged(f"{fab.FABRIC_BASE}/admin/tenantsettings", hint=HINT)
    except fab.AuthError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_AUTH
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = EXPORT_DIR / f"{date.today().isoformat()}.json"
    out.write_text(json.dumps({"tenantSettings": settings}, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(settings)} tenant settings to {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run it as yourself. `_fabric.py` uses your Azure CLI sign-in from Task 4; if
it has expired, run `az login --allow-no-subscriptions` again:

```bash
.venv/bin/python scripts/export_tenant_settings.py
```

It prints how many settings it saved and the file's path, such as
`tenant/export/2026-11-27.json`. Exit code 3 means the call returned 401 or
403: check that you signed in with a Fabric administrator account.

Check the four settings from Task 5 in the file:

```bash
.venv/bin/python - <<'EOF'
import glob, json
path = sorted(glob.glob("tenant/export/*.json"))[-1]
for s in json.load(open(path))["tenantSettings"]:
    title = s.get("title") or ""
    if "service principal" in title.lower():
        groups = ", ".join(g["name"] for g in s.get("enabledSecurityGroups") or [])
        print(f"{title} | {s['enabled']} | {groups}")
EOF
```

Each of the four shows `True` and `sg-fabric-workspace-provisioner`, with no
other group. Other settings about service principals may print too. The file
names your tenant's security groups, so keep it in your private copy.

Commit the script and the baseline, and open a pull request:

```bash
git add scripts/export_tenant_settings.py tenant/export
git commit -m "Save the tenant settings baseline"
git push -u origin tenant-baseline
gh pr create --fill
sleep 15
gh pr checks --watch
```

The pull request changes `scripts/`, so `validate` runs. Its comment says that
no workspace manifests changed. When the check passes, merge the pull request
and open the provision run:

```bash
gh pr merge --merge --admin --delete-branch
git switch main
git pull
sleep 15
RUN_ID=$(gh run list --workflow provision.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --web
```

The merge changed `scripts/`, so the provision workflow started and waits for
approval in the `production` environment. Challenge 01 provisions the first
workspaces, so don't approve this run. In the browser, select
**Review deployments**, check `production` and select **Reject**. The run
fails, as expected.

## Success criteria

- [ ] `copilot mcp list` shows `fabric` and `fabric-local`, and the smoke test
      prompts called tools from both.
- [ ] `/skills list` shows `onelake-catalog-cli`, and its dataowner-audit
      prompt answered.
- [ ] `gh-fabric-workspace-provisioner` has three federated credentials, no
      secret or certificate, and no admin role.
- [ ] The four service principal settings are enabled for
      `sg-fabric-workspace-provisioner` only, and the group has Contributor
      permissions on your capacity.
- [ ] The smoke test pull request's `validate` check passed after an OIDC
      login.
- [ ] A manual drift run opened an issue labeled `drift` and `governance`, and
      you closed it.
- [ ] A ruleset requires a reviewed pull request and the `validate` check to
      change `main`.
- [ ] `tenant/export/` on `main` holds a baseline with your tenant settings
      under `tenantSettings`, and the four service principal settings in it
      are enabled for `sg-fabric-workspace-provisioner` only.

## Stretch goals

- **Microsoft MCP Server for IT Admins.** It lets chat find users and groups by
  name and look up the object IDs that the Core MCP role tools take. It
  supports delegated permissions only, so it runs as you, never as the SPN, and
  no task needs it. To set it up:
  1. A Cloud Application Administrator or Application Administrator registers
     an app for "Accounts in this organizational directory only".
  2. In the app's **Manifest**, add `http://127.0.0.1` to
     `publicClient.redirectUris`. The portal's redirect URI box rejects it.
  3. Add the delegated Microsoft Graph permissions `MCP.Server.Access`,
     `User.Read` and `EntitlementMgmt-SubjectAccess.ReadWrite`, plus what your
     prompts need, such as `User.Read.All`. Grant admin consent.
  4. Add the server under `mcpServers` in `~/.copilot/mcp-config.json`:

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

  If you set up Microsoft MCP Server for Enterprise at
  `https://mcp.svc.cloud.microsoft/enterprise`, move to `/admin`. The older
  endpoint keeps working for a few months.

- **See the tenant as an administrator.** As a Fabric administrator, run
  `/onelake-catalog-cli` in admin-audit mode and compare the result with
  dataowner-audit. The admin-audit mode reads admin APIs and covers every
  workspace.
- **Unattended runs.** Run a read-only prompt from a script with
  `copilot -p "List my Fabric capacities."`, and allow only the tools it needs
  with `--allow-tool`. Keep `--allow-all` for a sandbox. In automation, sign in
  with a fine-grained personal access token that has the **Copilot Requests**
  permission, in `COPILOT_GITHUB_TOKEN`.

## MCP tips

- The Core server lists only what you can access. The drift check uses admin
  APIs to see every workspace.
- Only the local server has the docs tools (`docs_list-item-types`,
  `docs_item-api-spec`, `docs_platform-api-spec`, `docs_item-definitions`,
  `docs_best-practices` and `docs_api-examples`) and
  `core_get-operation-state`.
- No MCP tool covers tags, domains, tenant settings, sensitivity labels, admin
  APIs, external data shares, network rules, Git integration or Fabric
  policies. Those steps use the portal, REST, the Fabric CLI or Terraform.
- Write tools such as `delete_workspace` act at once, as you. A change made in
  chat is drift until a manifest says the same.
- `/mcp` in a session shows each server's status.

## Skills tips

- `/onelake-catalog-cli` has data owner modes, which use the Core API and see
  the workspaces you administer, and admin modes, which need a Fabric
  administrator.
- Skill names in older notes may no longer exist. `/skills list` shows the
  current ones.
- `fabric-skills` registers its own MCP servers (FabricIQ, powerbi-modeling-mcp
  and fabric-sqlendpoint), not the Core server you added in Task 2.

## Repository files

- [`scripts/validate.py`](../../scripts/validate.py),
  [`scripts/provision.py`](../../scripts/provision.py),
  [`scripts/drift.py`](../../scripts/drift.py) and
  [`scripts/_fabric.py`](../../scripts/_fabric.py)
- `scripts/export_tenant_settings.py` and `tenant/export/`, which Task 10 adds
- [`rules/policy.yaml`](../../rules/policy.yaml)
- `workspaces/dev-plt-sample-hello.yaml`
- [`.github/workflows/validate.yml`](../../.github/workflows/validate.yml),
  [`provision.yml`](../../.github/workflows/provision.yml) and
  [`drift.yml`](../../.github/workflows/drift.yml)
- [`.github/CODEOWNERS`](../../.github/CODEOWNERS)

## References

- [Identity model](../../docs/identity-model.md)
- [MCP servers and Skills](../../docs/mcp-and-skills.md)
- [Troubleshooting](../../docs/troubleshooting.md)
- [About tenant settings](https://learn.microsoft.com/fabric/admin/about-tenant-settings)
- [Developer tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-developer)
- [Admin API tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-admin-api-settings)
- [Enable service principal authentication for admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)
- [List Tenant Settings](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-tenant-settings)
- [Roles in workspaces in Microsoft Fabric](https://learn.microsoft.com/fabric/fundamentals/roles-workspaces)
- [Govern in the OneLake catalog](https://learn.microsoft.com/fabric/governance/onelake-catalog-govern)
- [Capacity settings](https://learn.microsoft.com/fabric/admin/capacity-settings)
- [Configure a federated identity credential](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust)
- [Grant tenant-wide admin consent](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent)
- [Fabric Core MCP Server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server)
- [Get started with the Fabric Core MCP Server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/get-started-core)
- [Fabric Core MCP Server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Get started with the local Fabric MCP Server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/pro-dev-local/get-started-local)
- [Get started with Microsoft MCP Server for IT Admins](https://learn.microsoft.com/graph/mcp-server/get-started)
- [Installing GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)
- [Adding MCP servers for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)
- [Adding skills to GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
- [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Reviewing deployments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
- [Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)
- [Adding self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners)
- [Running scripts before or after a job](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/run-scripts)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
