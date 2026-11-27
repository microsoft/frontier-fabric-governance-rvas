# Troubleshooting

Causes and fixes for errors you may hit in the challenges. For MCP errors, start with [Check that it works](mcp-and-skills.md#check-that-it-works): it calls the endpoint without your MCP client and lists the protocol errors. If your error isn't here, open a pull request that adds it.

## MCP servers and Skills

### `401` from the `fabric` server

The token expired, or you signed in with an account outside the tenant. Sign in again with an account in the tenant. In a Copilot CLI session:

```text
/mcp auth fabric
```

If that doesn't help, remove the server and add it again:

```bash
copilot mcp remove fabric
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
```

`copilot mcp remove` only removes servers in `~/.copilot/mcp-config.json`. If `copilot mcp list` shows `fabric` under Workspace, edit the repository's `.mcp.json` or `.github/mcp.json` instead. In VS Code, open **Chat: Open Customizations** > **MCP Servers** and choose **Uninstall** from the server's **...** menu, or delete its entry from `.vscode/mcp.json`. Then add it again with **MCP: Add Server**.

### A tool can't find a workspace

`WorkspaceNotFound` or `EntityNotFound` means the ID is wrong or your role doesn't let you see the workspace. Tools take IDs, not names: ask the agent to run `list_workspaces` and use the `id` it returns. Role tools take Entra object IDs, not email addresses.

### A Skill says a tool or server isn't available

The Skill expects an MCP server your client hasn't loaded. `copilot mcp list` shows your servers grouped by where they're configured: User, Workspace, Plugin and Builtin. To list your Skills, in a Copilot CLI session:

```text
/skills list
```

Then check these:

- The `fabric-skills` plugin doesn't add the Core MCP Server. Add `fabric` as in [Install](mcp-and-skills.md#install).
- APM without `-g` writes the server to `.vscode/mcp.json`, which Copilot CLI doesn't read. Install again with `-g`.
- The local Fabric MCP Server needs Node.js 22 or later. It reads `--namespace` and `--read-only` when it starts, so restart it or start a new session after you change them.

## Sign-in and permissions

### `AADSTS700213` or `AADSTS70021` in the Azure login step (OIDC)

Entra has no federated credential whose subject matches the token GitHub sent. Matching is case-sensitive, and the error shows the subject GitHub sent ([Breaking changes, August 2024](https://learn.microsoft.com/entra/identity-platform/reference-breaking-changes#august-2024)). Compare it with the subjects on the app:

```bash
APP_ID=$(az ad app list --display-name gh-fabric-workspace-provisioner --query "[0].appId" -o tsv)
az ad app federated-credential list --id "$APP_ID" --query "[].subject" -o tsv
```

Each workflow needs its own credential, with a subject that ends like this:

| Workflow | Subject ends with |
|---|---|
| `validate.yml` | `:pull_request` |
| `drift.yml` | `:ref:refs/heads/main` |
| `provision.yml` | `:environment:production` |

A job that uses an environment sends the environment name instead of the branch ([OpenID Connect reference](https://docs.github.com/en/actions/reference/security/oidc#filtering-for-a-specific-environment)). If the subject GitHub sent starts with `repo:<owner>@<owner-id>/`, the repository uses [immutable subject claims](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims), and every credential needs that prefix. Fix or add the credentials as in [Add the federated credentials](setup.md#add-the-federated-credentials).

A new or changed credential takes a short time to propagate, and sign-ins in that window can fail with `AADSTS70021`. Wait a few minutes and rerun the job ([Time for federated credential changes to propagate](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-considerations#time-for-federated-credential-changes-to-propagate)).

The `validate` login step continues on error, so with `LIVE_CHECKS=true` a failed sign-in shows up later as [`live check skipped`](#live-check-skipped).

### `AADSTS700016` in the Azure login step

The tenant has no app with that client ID. Check the `AZURE_CLIENT_ID` and `AZURE_TENANT_ID` repository variables against the values you [recorded](setup.md#record-your-values).

### Sign-in works, but a call returns 401 or 403

The scripts stop and print the call, the status, the error and a hint about what's missing. The service principal needs:

| Call | What the service principal needs |
|---|---|
| Any Fabric call | Its group in the tenant setting "Service principals can call Fabric public APIs" |
| Create Workspace | Its group in "Service principals can create workspaces, connections, and deployment pipelines" and in **Create workspaces**, and Contributor permissions on the capacity |
| Assign To Capacity | The Admin role on the workspace and Contributor permissions on the capacity |
| Update Workspace, Add Workspace Role Assignment, Apply Workspace Tags (Preview) | The Admin role on the workspace |
| Admin List Workspaces and List Workspace Access Details (Preview), in `drift.py` | Its group in "Service principals can access read-only admin APIs", and no Power BI or Fabric API permissions that need admin consent |
| Microsoft Graph groups (`validate.py` live checks) | `GroupMember.Read.All` or `Group.Read.All`, with admin consent |
| Microsoft Graph users (`provision.py`) | `User.Read.All`, with admin consent |

A tenant setting change can take up to 15 minutes to apply. [What the service principal holds](identity-model.md#what-the-service-principal-holds) explains each grant. Don't fix a 403 by making the service principal a Fabric administrator or a capacity administrator.

### Exit codes

| Script | Exit code | Meaning |
|---|---|---|
| `validate.py` | 0 | Every manifest passes the blocking rules. Warnings don't change the exit code. |
| `validate.py` | 1 | At least one manifest fails a blocking rule. |
| `validate.py` | 2 | A live check returned 401 or 403, so validation stopped and no manifest has a result. |
| `provision.py` | 0 | No manifest failed. Lines with `warn:` don't change the exit code, so read the log. |
| `provision.py` | 1 | At least one manifest failed: search the log for `ERROR processing`. The other manifests were still processed. |
| `provision.py` | 3 | A call returned 401 or 403. The run stopped at that manifest. |
| `drift.py` | 0 | No drift. |
| `drift.py` | 1 | The script crashed. Read the traceback in the job log. |
| `drift.py` | 2 | Drift found. The workflow opens an issue. |
| `drift.py` | 3 | A call returned 401 or 403, so the check didn't run. |

## Fabric REST

### `429` or `exhausted retries`

Fabric limits how many calls a caller can make. `_request` in `scripts/_fabric.py` makes up to five attempts on 429, 502, 503 and 504, waiting for `Retry-After`, or without it 2 seconds, doubling each time. If the last attempt fails too, the error says `exhausted retries` and gives the last status. List Tags allows 25 requests a minute, and each admin workspace API allows 200 requests an hour. Wait and rerun. Route any call you add through `_request`.

### The workspace name is taken

Workspace names must be unique ([Create a workspace](https://learn.microsoft.com/fabric/fundamentals/create-workspaces)). `provision.py` looks for the name only among workspaces the service principal has a role on. If someone else's workspace has the name, the script tries to create it, and the log shows `ERROR processing` with the error Fabric returned. Rename the manifest and its file, or have an Admin of that workspace add the service principal as Admin. The next run then updates the workspace's description and capacity, and adds the missing owners and tags.

### `not in approvedCapacities` or `could not resolve the capacity ID`

The manifest's `capacity` must be an entry in `approvedCapacities` in `rules/policy.yaml`. `provision.py` uses that entry's `capacityId` unless it's empty or a placeholder. Next it tries the `FABRIC_CAPACITY_ID` variable, then a capacity whose name matches the entry. List Capacities only returns capacities the caller is an administrator or contributor of, so the name lookup needs the [Contributor permissions](setup.md#give-the-group-contributor-permissions-on-each-capacity).

Put the real capacity IDs in `rules/policy.yaml`, and copy the file to `api/policy.yaml`, which must stay identical. In a lab, you can set `FABRIC_CAPACITY_ID` instead: it applies to every entry whose `capacityId` is empty or a placeholder.

### The workspace stays on its old capacity

Assign To Capacity is asynchronous: Fabric accepts the request and moves the workspace afterward ([Assign To Capacity](https://learn.microsoft.com/rest/api/fabric/core/workspaces/assign-to-capacity)). A `warn: assignToCapacity:` line in the log means the request failed and the run went on. A move to a capacity in another region fails while the workspace holds items that can't move between regions ([Capacity reassignment restrictions](https://learn.microsoft.com/fabric/admin/portal-workspace-capacity-reassignment#restrictions-on-moving-workspaces-around)). `drift.py` doesn't compare capacities, so check the workspace in Fabric.

### An owner isn't added

Look for these lines in the provision log:

- `warn: could not resolve UPN … to object ID, skipping`: Microsoft Graph found no user with that user principal name. Check the spelling, or use the user's object ID.
- `warn: role assignment failed for …`: Fabric rejected the assignment. The message after it says why.

`provision.py` only adds missing role assignments, so a run can't lock anyone out. It doesn't change a role someone already holds or remove anyone. `drift.py` reports those differences until you fix them in Fabric.

### A tag isn't applied

`warn: tag '…' isn't a tenant tag or a tag of this workspace's domain; skipping it` means no tag with that name is in scope. `provision.py` looks for a tenant tag first, then a tag of the workspace's domain. It doesn't assign domains, so a domain tag applies only once the workspace is in that domain.

A Fabric administrator creates tenant tags, and a Fabric or domain administrator creates domain tags ([Define tags](https://learn.microsoft.com/fabric/governance/tags-define)). A workspace takes up to 10 tags ([Apply tags](https://learn.microsoft.com/fabric/governance/tags-apply)). With `LIVE_CHECKS=true`, `validate.py` warns about unknown tags before the merge. `provision.py` never removes tags, and `drift.py` reports missing and extra tags.

### The workspace has no sensitivity label

That's expected. Labels apply to items, Fabric has no workspace label API, and the scripts don't apply the manifest's `sensitivityLabel`. [Keep the service principal out of admin roles](setup.md#keep-the-service-principal-out-of-admin-roles) lists the ways to label the items.

## GitHub

### A job stays queued

All three workflows run on a self-hosted runner with the label `fabric-gov`. Check that one is online under **Settings** > **Actions** > **Runners**. A `provision` job that's waiting for review needs a required reviewer of the `production` environment to approve it.

### `validate` doesn't run, or its required check stays pending

`validate` runs only when a pull request changes `workspaces/`, `rules/`, `schemas/`, `scripts/` or `.github/workflows/validate.yml`. GitHub keeps a skipped required check pending ([Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushpull_requestpull_request_targetpathspaths-ignore)), so a pull request that changes only other files needs someone allowed to bypass the rule to merge it. See [Configure the repository](setup.md#configure-the-repository).

### `validate` reports "No workspace manifests changed in this PR"

The workflow checks only the manifests a pull request changes. A pull request that changes only rules, schemas or scripts doesn't recheck the existing manifests, so check them all locally. With the virtual environment from [`ModuleNotFoundError`](#modulenotfounderror), run:

```bash
.venv/bin/python scripts/validate.py
```

### `provision` or `drift` never runs

Under **Actions**, select the workflow, and if it's disabled, choose **Enable workflow**. `provision` runs when a push to `main` changes `workspaces/`, `rules/`, `scripts/` or its workflow file, or when you run it from **Actions**. Scheduled runs use the workflow file on the default branch, and in a public repository GitHub disables them after 60 days without repository activity ([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)).

### A new drift issue every day

`drift` opens a new issue each day it finds drift, and never updates or closes an earlier one. It counts every active workspace in the tenant that has no manifest as unmanaged, and every managed workspace the service principal has no role on as not visible. `drift.py` has no exclusion list, so in a shared tenant it finds drift every day. To bring a workspace under management, have one of its Admins add the service principal as Admin, then merge a manifest for it. After you fix the drift, run **drift** from **Actions** and close the old issues.

### A pull request merged without code owner review

A branch protection rule or ruleset must require review from Code Owners. GitHub skips invalid lines in `CODEOWNERS`, owners need write access, and teams must be visible ([About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)). List the errors:

```bash
gh api repos/{owner}/{repo}/codeowners/errors
```

### A push that changes `.github/workflows/` is refused

GitHub refuses it when your token lacks the `workflow` scope. If Git signs in with the GitHub CLI, add the scope:

```bash
gh auth refresh --scopes workflow
```

With a fine-grained personal access token, give it the Workflows permission with read and write access.

## Scripts

### `ModuleNotFoundError`

The scripts need the packages in `scripts/requirements.txt`. The workflows install them. Locally, create a virtual environment and run the scripts from it:

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/validate.py
```

### `live check skipped`

With `LIVE_CHECKS=true`, a live check that fails for a reason other than 401 or 403 becomes this warning, and validation goes on. Usually the sign-in failed. In CI, read the log of the "Azure login (OIDC, optional live checks)" step. Locally, sign in with `az login --allow-no-subscriptions`, or leave `LIVE_CHECKS` unset: it's `false` by default.

### `group … not found in Entra`

With `LIVE_CHECKS=true`, `validate.py` looks up each group owner in Microsoft Graph by object ID, and blocks the manifest when Graph doesn't find it. A display name doesn't work, and neither does the placeholder `44444444-4444-4444-4444-444444444444` in the sample manifest. Replace it with the object ID of a real group, as in the [Smoke test](setup.md#smoke-test). To look up a group's object ID by its name, here `grp_fabric_dev_plt_admin`:

```bash
az ad group show --group grp_fabric_dev_plt_admin --query id -o tsv
```
