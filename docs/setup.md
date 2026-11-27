# One-time setup

These steps prepare a tenant and your copy of this repository for the challenges. They need three roles, held by three people or by one:

- An Entra administrator who can grant admin consent for Microsoft Graph application permissions, such as a Privileged Role Administrator ([Grant admin consent](https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent)). They create the app registration, the security group and the federated credentials.
- A Fabric administrator, who turns on the tenant settings.
- A capacity administrator for each capacity, who gives the security group Contributor permissions on it.

The service principal holds none of these roles. [Identity model](identity-model.md) lists what it holds instead.

## Record your values

| Item | Value |
|---|---|
| Tenant ID | `<your-tenant-id>` |
| App registration | `gh-fabric-workspace-provisioner` |
| Application (client) ID | `<your-app-client-id>` |
| Service principal object ID | `<your-spn-object-id>` |
| Security group, with the service principal as a member | `sg-fabric-workspace-provisioner` |
| Security group object ID | `<your-security-group-id>` |
| Non-production capacity ID | `<your-nonprod-capacity-id>`, for the `contosononprodf2` entry (F2, `northeurope`; sbx, dev and stg workspaces) |
| Production capacity ID | `<your-prod-capacity-id>`, for the `contosoprodf4` entry (F4, `northeurope`; prd workspaces) |

Put the two capacity IDs in `approvedCapacities` in `rules/policy.yaml`, in place of `33333333-3333-3333-3333-333333333333` and `66666666-6666-6666-6666-666666666666`, and make the same change in `api/policy.yaml`: the two files must stay identical. In a lab, both entries can point to the same capacity. While an entry still holds a placeholder, `scripts/provision.py` uses the `FABRIC_CAPACITY_ID` variable instead, or failing that, a capacity the service principal can see whose name matches the entry, such as `contosononprodf2`.

## Turn on the tenant settings

A Fabric administrator opens **OneLake catalog** > **Govern** > **Configurations** > **Tenant settings**. Where Govern hasn't rolled out yet, or the tenant uses Private Link, which removes the Govern tab, use **Settings** > **Admin portal** > **Tenant settings** instead ([Govern](https://learn.microsoft.com/fabric/governance/onelake-catalog-govern)).

For each setting below, select **Enabled**, choose **Specific security groups**, add `sg-fabric-workspace-provisioner` and select **Apply**. A setting that's already enabled for the entire organization covers the group. Leave it as it is, because other apps may rely on it.

| Setting | Section | Used by |
|---|---|---|
| Service principals can call Fabric public APIs | Developer settings | Every call the scripts make. On by default in new tenants. |
| Service principals can create workspaces, connections, and deployment pipelines | Developer settings | `scripts/provision.py`, to create workspaces. Off by default in new tenants. |
| Service principals can access read-only admin APIs | Admin API settings | `scripts/drift.py` |
| Service principals can access admin APIs used for updates | Admin API settings | None of the shipped scripts. Challenge 00 turns it on for Fabric admin APIs that change data, such as assigning workspaces to domains. |

The two Developer settings replaced "Service principals can use Fabric APIs" ([Developer admin settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-developer)). [Enable service principal authentication for admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis) covers the other two.

**Create workspaces**, under Workspace settings, must also cover the group, because the Create Workspace API checks it ([Workspace admin settings](https://learn.microsoft.com/fabric/admin/portal-workspace)). To route workspace requests through this repository, limit it to `sg-fabric-workspace-provisioner` and a break-glass group of people who still need to create workspaces by hand.

A change can take up to 15 minutes to take effect ([About tenant settings](https://learn.microsoft.com/fabric/admin/about-tenant-settings)).

## Give the group Contributor permissions on each capacity

A capacity administrator does this for each capacity in `approvedCapacities`:

1. Open **Settings** > **Admin portal** > **Capacity settings**, choose the tab for the capacity type and select the capacity.
2. Under **Contributor permissions**, choose **Specific users or security groups** and add `sg-fabric-workspace-provisioner`. If it's set to **The entire organization**, the group is already covered.

> **Preview** (checked 2026-11-27): Manage your capacities in the OneLake catalog — [Learn](https://learn.microsoft.com/fabric/governance/onelake-catalog-capacities). GA route: the Admin portal steps above.

You can also set contributors in **OneLake catalog** > **Govern** > **Capacities**.

Contributors can add workspaces to the capacity. Changing its settings and contributors stays with capacity administrators, so don't make the service principal one ([Manage your Fabric capacity](https://learn.microsoft.com/fabric/admin/capacity-settings)).

Assigning a workspace to a capacity also needs the Admin role on the workspace ([Assign To Capacity](https://learn.microsoft.com/rest/api/fabric/core/workspaces/assign-to-capacity)). The service principal is Admin of each workspace it creates. To manage an existing workspace from this repository, first have one of its Admins add the service principal itself as Admin. Don't add its group instead: `drift.py` reports every principal with access that isn't an owner, and ignores only the service principal.

## Grant Microsoft Graph permissions

With `LIVE_CHECKS=true`, `scripts/validate.py` checks that each owner group exists. `scripts/provision.py` looks up each owner user's object ID from their user principal name. An Entra administrator who can grant admin consent for Graph application permissions sets this up:

1. In the Microsoft Entra admin center, open **App registrations**, select `gh-fabric-workspace-provisioner` and open **API permissions**.
2. Select **Add a permission** > **Microsoft Graph** > **Application permissions**, and add `GroupMember.Read.All` (or `Group.Read.All`) and `User.Read.All` ([Microsoft Graph permissions reference](https://learn.microsoft.com/graph/permissions-reference)).
3. Select **Grant admin consent** for your tenant.

Don't add Power BI Service or Fabric permissions that need admin consent, such as `Tenant.ReadWrite.All`. Admin APIs reject a service principal that has them.

## Keep the service principal out of admin roles

The service principal is never a Fabric administrator or a capacity administrator, and it isn't in any sensitivity label publishing policy. The tenant settings, the capacity Contributor permissions and the workspace Admin role cover everything the scripts do.

The scripts don't apply a manifest's `sensitivityLabel`: labels apply to items, and Fabric has no workspace label API. Label the items in each workspace in one of these ways:

- Item owners apply the label by hand in Fabric.
- A user who is a Fabric administrator calls [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels), which doesn't accept service principals.
- A domain administrator sets a default label for the workspace's domain, as described next.

> **Preview** (checked 2026-11-27): Domain-level default sensitivity labels — [Learn](https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label). GA route: label items by hand, or have a Fabric administrator call Bulk Set Labels.

A Fabric administrator first turns on the tenant setting "Domain admins can set default sensitivity labels for their domains (preview)". The domain's default label then goes on new items, and on unlabeled items when someone saves them, in the domain's workspaces. It doesn't support deployment pipelines or Git integration. `scripts/provision.py` doesn't assign workspaces to domains. A Fabric or domain administrator assigns each workspace to its manifest's domain in Fabric. A script can also do it as the service principal with [Assign Domain Workspaces By Ids](https://learn.microsoft.com/rest/api/fabric/admin/domains/assign-domain-workspaces-by-ids), once "Service principals can access admin APIs used for updates" covers its group.

## Add the federated credentials

Each workflow signs in with its own federated credential. The credential's subject must match the `sub` claim in the token GitHub issues, including case ([Create a trust relationship between an app and an external identity provider](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust)). Before you add the pull request credential, read [Pull request runs](identity-model.md#pull-request-runs).

| Workflow | Subject |
|---|---|
| `validate.yml` | `<prefix>:pull_request` |
| `drift.yml` | `<prefix>:ref:refs/heads/main` |
| `provision.yml` | `<prefix>:environment:production` |

The prefix depends on the repository. GitHub uses `repo:<owner>@<owner-id>/<repo>@<repo-id>` for repositories created, renamed or transferred after 2026-07-15, and for older ones that opted in to immutable subjects. Other repositories use `repo:<owner>/<repo>` ([OpenID Connect reference](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims)).

The Entra administrator adds the credentials from a clone of your repository, with the GitHub CLI and the Azure CLI. First, sign in and set the prefix:

```bash
az login --allow-no-subscriptions
SUBJECT_PREFIX=$(gh api repos/{owner}/{repo} --jq '"repo:\(.owner.login)@\(.owner.id)/\(.name)@\(.id)"')
echo "$SUBJECT_PREFIX"
```

Check that it names your repository. If it names the repository you forked, run `gh repo set-default`, pick yours and set the prefix again. If your repository was created before 2026-07-15, hasn't been renamed or transferred since and hasn't opted in, set the prefix with this line instead:

```bash
SUBJECT_PREFIX=$(gh api repos/{owner}/{repo} --jq '"repo:\(.full_name)"')
```

Then add the three credentials:

```bash
APP_ID=$(az ad app list --display-name gh-fabric-workspace-provisioner --query "[0].appId" -o tsv)
az ad app federated-credential create --id "$APP_ID" --parameters "{\"name\":\"github-pull-request\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"${SUBJECT_PREFIX}:pull_request\",\"audiences\":[\"api://AzureADTokenExchange\"]}"
az ad app federated-credential create --id "$APP_ID" --parameters "{\"name\":\"github-main\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"${SUBJECT_PREFIX}:ref:refs/heads/main\",\"audiences\":[\"api://AzureADTokenExchange\"]}"
az ad app federated-credential create --id "$APP_ID" --parameters "{\"name\":\"github-production\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"${SUBJECT_PREFIX}:environment:production\",\"audiences\":[\"api://AzureADTokenExchange\"]}"
```

If a sign-in fails with `AADSTS700213` or `AADSTS70021`, the error shows the subject GitHub sent. [Troubleshooting](troubleshooting.md#sign-in-and-permissions) has the fix. To move an older repository to immutable subjects later, follow [Migrate GitHub Actions federated credentials to immutable subjects](https://learn.microsoft.com/entra/workload-id/workload-identities-github-immutable-subjects).

## Configure the repository

In **Settings** > **Secrets and variables** > **Actions**, add these repository variables on the **Variables** tab. The workflows need no secrets.

| Variable | Value |
|---|---|
| `AZURE_TENANT_ID` | The tenant ID |
| `AZURE_CLIENT_ID` | The application (client) ID |
| `FABRIC_CAPACITY_ID` | Optional. The capacity ID that `provision.py` uses for an `approvedCapacities` entry that still holds a placeholder. |
| `DRY_RUN` | Optional, `false` by default. With `true`, `provision.py` logs what it would do and makes no API calls. |
| `LIVE_CHECKS` | Optional, `false` by default. With `true`, `validate.py` checks owner groups and tags against the tenant. |

Then:

1. Register a self-hosted runner with the label `fabric-gov`, with Python 3 and the Azure CLI installed. All three workflows run on it, including on pull requests, so read [Pull request runs](identity-model.md#pull-request-runs) first.
2. Before the first merge, create the `production` environment under **Settings** > **Environments**, add required reviewers and limit deployments to the `main` branch. If the environment doesn't exist, the first provisioning run creates it with no protection. In a private repository, required reviewers need GitHub Enterprise, and deployment branch limits need GitHub Pro, Team or Enterprise ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments#required-reviewers)).
3. Protect `main` with a branch protection rule or ruleset that requires a pull request, review from Code Owners and the `validate` status check. The `validate` workflow runs only when a pull request changes `workspaces/`, `rules/`, `schemas/`, `scripts/` or the workflow file. GitHub keeps a skipped required check pending, so a pull request that changes only other files can't merge unless someone allowed to bypass the rule merges it ([Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushpull_requestpull_request_targetpathspaths-ignore)).
4. In `.github/CODEOWNERS`, replace `@your-org/fabric-governance-maintainers` with a team that has write access to the repository.
5. Under **Actions**, select any workflow marked as disabled and choose **Enable workflow**.

## Smoke test

1. Create a branch from `main`.
2. In `workspaces/dev-plt-sample-hello.yaml`, replace `44444444-4444-4444-4444-444444444444` with the object ID of a real group and `groupName` with that group's name, and replace `workspace-owner@contoso.com` with a real user's user principal name. A group name that doesn't follow `grp_<fabric|powerbi>_<env>_<team>_<role>` gets a warning, not a block.
3. Open a pull request. The `validate` workflow comments with its results.
4. Merge it, then approve the `production` deployment. The `provision` workflow creates `dev-plt-sample-hello` on the capacity in the `contosononprodf2` entry.
5. In Fabric, check that the workspace exists on that capacity with the owners you set.

To rehearse without changing the tenant, set `DRY_RUN` to `true` before you merge and read the plan in the provision log. Then set it back to `false` and run **provision** again from the **Actions** tab.
