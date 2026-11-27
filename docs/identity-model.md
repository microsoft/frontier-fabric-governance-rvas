# Identity model

One app registration, `gh-fabric-workspace-provisioner`, is the only identity this repository uses to change Fabric. It writes only in the `provision` workflow, after a reviewed pull request merges to `main` and an approver releases the `production` environment. The `validate` and `drift` workflows only read, and each signs in to the same app with its own federated credential. [Pull request runs](#pull-request-runs) explains what that means for pull requests. Every challenge in the RVAS (Real Value Acceleration Solutions) program uses this model.

## Actors

| Actor | What it is | Role |
|---|---|---|
| Participant | A person with a Microsoft Entra ID account in the tenant | Opens and reviews pull requests, and asks the agent questions |
| `gh-fabric-workspace-provisioner` | The Entra app registration and its service principal | The identity every workflow signs in as |
| `sg-fabric-workspace-provisioner` | An Entra security group that contains the service principal | Receives the tenant settings and the capacity Contributor permissions |
| `fabric-gov` | A self-hosted GitHub Actions runner with that label | Runs the `validate`, `provision` and `drift` workflows |
| Code owner | A user or team listed in `.github/CODEOWNERS` | Approves pull requests before they merge |
| Environment approver | A required reviewer on the `production` environment | Releases each provisioning run after the merge |
| Entra administrator | A person who can grant admin consent for Microsoft Graph application permissions | Creates the app, the group and the federated credentials, and grants the Graph permissions |
| Fabric and capacity administrators | People in your organization | Turn on the tenant settings and grant the capacity permissions. The service principal never holds these roles. |

## Trust chain

```text
┌───────────────────────────────┐
│ Participant                   │
└───────────────┬───────────────┘
                │ opens and reviews pull requests,
                │ approves production runs
                ▼
┌───────────────────────────────┐
│ GitHub Actions on fabric-gov  │
│ validate, provision, drift    │
└───────────────┬───────────────┘
                │ GitHub OIDC token
                ▼
┌───────────────────────────────┐
│ Microsoft Entra ID            │
│ token exchange                │
└───────────────┬───────────────┘
                │ access tokens
                ▼
┌───────────────────────────────┐
│ Fabric REST APIs              │
│ Microsoft Graph               │
└───────────────────────────────┘
```

No step uses a client secret or certificate. In each job, `azure/login` signs the Azure CLI in to the app with the job's short-lived GitHub OIDC token. `DefaultAzureCredential` in the scripts then gets Fabric and Microsoft Graph tokens from that session.

## Federated credentials

The app has one federated credential per workflow:

| Workflow | Entity type | Subject | When it runs |
|---|---|---|---|
| `validate` | Pull request | `<prefix>:pull_request` | On each pull request that changes `workspaces/`, `rules/`, `schemas/`, `scripts/` or `validate.yml` |
| `provision` | Environment `production` | `<prefix>:environment:production` | After a push to `main` that changes `workspaces/`, `rules/`, `scripts/` or `provision.yml`, or a manual run, once an approver releases `production` |
| `drift` | Branch `main` | `<prefix>:ref:refs/heads/main` | Daily at 03:17 UTC, or a manual run from `main` |

`<prefix>` is `repo:<owner>@<owner-id>/<repo>@<repo-id>` if your repository uses GitHub's immutable subjects, as every repository created after 2026-07-15 does, and `repo:<owner>/<repo>` if it doesn't. All three use the audience `api://AzureADTokenExchange`. [One-time setup](setup.md#add-the-federated-credentials) shows how to add them.

## Pull request runs

The `validate` workflow asks for an OIDC token on each pull request that changes its paths, and GitHub runs the workflow and scripts as they are in the pull request. Anyone who can push a branch to your repository can therefore change them and sign in as `gh-fabric-workspace-provisioner`, with every permission the service principal holds, before anyone reviews the change and without the `production` approval.

To close that gap, choose one of these:

- Give pull request runs their own app. Register a second app with only the pull request federated credential. Add it to its own security group in "Service principals can call Fabric public APIs", and grant it `GroupMember.Read.All` (or `Group.Read.All`). Give it no capacity or workspace roles, and keep it out of `sg-fabric-workspace-provisioner`. Then remove the pull request credential from `gh-fabric-workspace-provisioner`, and in your copy of `validate.yml` set `client-id` to a repository variable that holds the second app's client ID.
- Don't add the pull request credential. The sign-in step then fails and the job carries on without it. With `LIVE_CHECKS` set to `false`, the default, `validate` needs no token. With `true`, the live checks report "live check skipped" warnings instead of running.

Either way, limit the `production` environment's deployments to `main`, as [One-time setup](setup.md#configure-the-repository) says. A pull request run then can't use that environment or its credential, even with an approval ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments#deployment-branches-and-tags)).

All three workflows also share the `fabric-gov` runner, so code from a pull request runs on the machine that later runs `provision`. GitHub warns that self-hosted runners "can be persistently compromised by untrusted code in a workflow" and should almost never be used for public repositories ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use#hardening-for-self-hosted-runners)). Keep your copy of this repository private, or give `validate` a runner of its own.

In a lab where everyone who can push to the repository is trusted, one app with all three credentials is enough.

## Tenant settings

`sg-fabric-workspace-provisioner` is enabled in four tenant settings:

| Setting | Why the service principal needs it |
|---|---|
| Service principals can create workspaces, connections, and deployment pipelines | `provision.py` creates workspaces. Off by default in new tenants. |
| Service principals can call Fabric public APIs | Every Fabric call the scripts make. With the setting above, it replaced "Service principals can use Fabric APIs". |
| Service principals can access read-only admin APIs | `drift.py` lists workspaces and their access. |
| Service principals can access admin APIs used for updates | Fabric admin APIs that change data, such as assigning workspaces to domains. Challenge 00 turns it on. The shipped scripts don't use it. |

The group also needs **Create workspaces**, because the Create Workspace API checks it. A Fabric administrator turns these on in **OneLake catalog** > **Govern** > **Configurations** > **Tenant settings**, or in the Admin portal where Govern isn't available. [One-time setup](setup.md#turn-on-the-tenant-settings) has the steps.

## What the service principal holds

| Grant | Where | Used for |
|---|---|---|
| Membership of `sg-fabric-workspace-provisioner` | Microsoft Entra ID | The tenant settings above |
| Contributor permissions, through the group | Each capacity in `approvedCapacities` | Creating workspaces on a capacity and assigning workspaces to it |
| Admin role | Each workspace it manages. It gets this role automatically on workspaces it creates. | Assigning the capacity and adding the owners from the manifest |
| `GroupMember.Read.All` (or `Group.Read.All`) and `User.Read.All` | Microsoft Graph application permissions, with admin consent | Checking that owner groups exist and looking up owner users' object IDs |

If a call returns 401 or 403, the scripts stop and report it. They never read either as "not found". [Troubleshooting](troubleshooting.md#sign-in-and-permissions) lists the usual causes.

## What it never gets

- The Fabric administrator role or a capacity administrator role.
- Power BI or Fabric API permissions that need admin consent, such as `Tenant.ReadWrite.All`. Admin APIs reject a service principal that has them.
- A place in a sensitivity label publishing policy. [Keep the service principal out of admin roles](setup.md#keep-the-service-principal-out-of-admin-roles) explains how items get labeled instead.
- A client secret or certificate.

## What participants don't get

- Ownership of the app registration, which would let them add a credential to it.
- Direct pushes to `main`. Branch protection requires a reviewed pull request.
- A provisioning run without an environment approver. [Pull request runs](#pull-request-runs) covers a way around that gate and how to close it.

## Day-2 changes

When a challenge needs the service principal to do more:

1. Turn on the tenant setting it needs for `sg-fabric-workspace-provisioner`. Don't add Power BI or Fabric API permissions to the app.
2. If a new workflow job uses its own environment, add a federated credential for that environment's subject, and limit the environment's deployments to `main`, as for `production` ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments#deployment-branches-and-tags)).
3. Record the change in that challenge's `challenge.md`.

To give a person one of the service principal's abilities, grant it to a security group they're in. Don't change the service principal for them.

## References

- [Create a trust relationship between an app and an external identity provider](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust)
- [OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect)
- [Developer admin settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-developer)
- [Enable service principal authentication for admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)
- [Identity support for logging into the Microsoft Fabric](https://learn.microsoft.com/rest/api/fabric/articles/identity-support)
- [Understand Microsoft Fabric admin roles](https://learn.microsoft.com/fabric/admin/roles)
- [Manage your Fabric capacity](https://learn.microsoft.com/fabric/admin/capacity-settings)
- [Microsoft Graph permissions reference](https://learn.microsoft.com/graph/permissions-reference)
- [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
