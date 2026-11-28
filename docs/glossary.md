# Glossary

Quick reference for terms used across the RVAS (Real Value Acceleration Solutions) program.

## Microsoft Fabric

- **Workspace** — the unit of collaboration and access control in Fabric. Hosts items.
- **Item** — anything inside a workspace: lakehouse, warehouse, notebook, semantic model,
  pipeline, eventhouse, KQL database, eventstream, reflex/activator, dataflow, mirror, etc.
- **Capacity** — the compute, sold as F SKUs (F2, F4, F64…), that runs one or more
  workspaces. Most Fabric workloads need one. Capacity administrators manage it, and
  capacity contributors can add workspaces to it.
- **Domain / subdomain** — a grouping of workspaces by business area, for governance and
  discovery. A Fabric administrator creates domains in **OneLake catalog** > **Govern** >
  **Domains** and names their domain administrators.
- **OneLake** — the single, tenant-wide data lake underneath Fabric. Items that contain
  data (lakehouses, warehouses, KQL DBs) are projections over OneLake.
- **OneLake catalog** — searchable index of items across the tenant. Its **Govern**
  section shows governance insights and, depending on your role, admin experiences such
  as tenant settings, domains and capacities.
- **Tenant setting** — a switch that turns a Fabric feature on for the entire
  organization or for specific security groups, or off. A Fabric administrator sets it in
  **OneLake catalog** > **Govern** > **Configurations** > **Tenant settings**, or in
  **Settings** > **Admin portal** > **Tenant settings** where Govern isn't available.
- **Endorsement** — Promoted or Certified label on an item that signals trust.
- **Sensitivity label** — a Microsoft Purview Information Protection label, such as
  Public, General, Confidential or Highly Confidential, plus sublabels. In Fabric, labels
  apply to items, not workspaces. A label's protection settings can encrypt data and
  restrict access.
- **Capacity administrator** — manages a capacity's settings and contributors, and can
  add or remove its workspaces. The RVAS service principal is never one.
- **Capacity contributor** — a user or security group in a capacity's Contributor
  permissions, which can add workspaces to the capacity. Assign To Capacity needs this
  and the Admin role on the workspace.
- **Fabric administrator** — the Microsoft Entra role with full access to Fabric
  management, including tenant settings and domains. A user who calls an admin API needs
  it. A service principal doesn't: its security group needs the admin API tenant settings
  instead, so the RVAS service principal is never one.
- **Deployment pipeline** — Fabric-native promotion mechanism between dev / test / prod
  workspaces.
- **Fabric Data Agent** — a configurable, governed Q&A agent that queries lakehouses,
  warehouses, semantic models, KQL DBs or ontologies on behalf of users.

## Identity

- **Service principal (SPN)** — the identity of an Entra app registration in a tenant.
  The RVAS uses one, for the app registration `gh-fabric-workspace-provisioner`, as a
  member of the security group `sg-fabric-workspace-provisioner`. The group holds the
  tenant settings and the capacity Contributor permissions, and the service principal is
  Admin of the workspaces it manages. See [Identity model](identity-model.md).
- **Federated credential** — a setting on an Entra app registration that trusts tokens
  from an external issuer, here GitHub Actions, for one subject. The subject starts with
  the repository, as `repo:<owner>/<repo>` or, with immutable subject claims,
  `repo:<owner>@<owner-id>/<repo>@<repo-id>`. It ends with the branch, the environment or
  `pull_request`, so each workflow needs its own credential.
- **OIDC** — OpenID Connect. GitHub gives each workflow job a short-lived OIDC token, and
  Entra exchanges it for an access token when a federated credential matches its subject.
  The workflows need no secrets.
- **CODEOWNERS** — a GitHub file that names the owners of paths in the repository. A
  branch protection rule or ruleset that requires review from Code Owners makes their
  approval mandatory.
- **Branch protection** — a branch protection rule or ruleset on `main`. Here it requires
  a pull request, review from Code Owners and the `validate` status check.
- **GitHub environment** — a deployment target with optional required reviewers, wait
  timers, and secrets. The RVAS uses `production` as the approval gate for `provision`. A
  job that uses an environment sends its name in the OIDC subject.

## Governance / Purview

- **Drift** — a difference between what a manifest declares and what the tenant has.
- **Unmanaged** — an active workspace of type `Workspace` that has no manifest. Personal
  workspaces don't count.
- **Missing workspace (orphan manifest)** — a manifest with no active workspace of its
  name in the tenant, for example because someone deleted the workspace outside the
  repository.
- **Not visible** — a managed workspace the service principal has no role on, so
  `drift.py` can't read its description.
- **Adoption** — bringing an existing workspace under repository management. One of its
  Admins adds the service principal as Admin, then you merge a manifest with the
  workspace's exact name. The next provisioning run updates its description and capacity,
  and adds the missing owners and tags.
- **DLP** — Data Loss Prevention; Purview policies that block sensitive data movement.
- **DSPM** — Data Security Posture Management, a Microsoft Purview solution that reports
  data security risks, including in Fabric. Once it's set up, its Activity Explorer also
  shows interactions with Copilot in Fabric and Fabric data agents. Purview support is GA
  for Copilot for Power BI and Preview for the rest. No public API returns its findings,
  so review them in the Purview portal and record what you find as evidence.
- **Audit log** — Fabric + Purview record of every action with actor identity.

## MCP / Skills

- **MCP** — Model Context Protocol; a standard for AI agents to call typed tools.
- **MCP server** — a process that exposes tools to MCP clients. It runs remotely, like
  the Fabric Core MCP Server, or on your machine, like the Fabric MCP Server. See
  [Fabric MCP servers and Skills](mcp-and-skills.md).
- **MCP tool** — a single typed operation an agent can invoke.
- **Skill (for Fabric)** — a packaged set of agent instructions + tool calls that
  solves a workload-specific task (e.g., "create a KQL database with these tables").

## This repo

- **Manifest** — a YAML file that declares the desired state of one resource. The
  shipped scripts read workspace manifests, each saved as `workspaces/<name>.yaml`, such
  as `workspaces/dev-plt-sample-hello.yaml`.
- **Policy** — `rules/policy.yaml`: the rules and allow lists the validator applies.
  The agent backend in `api/` has a copy, `api/policy.yaml`, which must stay identical.
- **Validator** — `scripts/validate.py`: checks manifests against the schema and the
  rules. The `validate` workflow runs it on pull requests and comments with the results.
- **Provisioner** — `scripts/provision.py`: creates or updates each workspace from its
  manifest. The `provision` workflow runs it after a merge to `main`, once someone
  approves the `production` environment.
- **Drift detector** — `scripts/drift.py`: compares the tenant's workspaces with the
  manifests. The `drift` workflow runs it daily and opens an issue when it finds drift.
- **Marker** — a `managed-by:` string at the end of a workspace description that names
  the managing repository and commit. The shipped scripts don't use one: `provision.py`
  sets the description from the manifest, and `drift.py` matches workspaces to
  manifests by name.
