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

- **Drift** — divergence between declared (manifest) state and live (tenant) state.
- **Unmanaged** — a tenant resource with no manifest in the repo.
- **Orphan manifest** — a manifest in the repo whose tenant resource was deleted out of band.
- **Adoption** — bringing an existing tenant resource under repo management by writing
  a manifest and applying the `managed-by:` marker.
- **DLP** — Data Loss Prevention; Purview policies that block sensitive data movement.
- **DSPM** — Data Security Posture Management; Purview signals about risk in data sources.
- **Audit log** — Fabric + Purview record of every action with actor identity.

## MCP / Skills

- **MCP** — Model Context Protocol; a standard for AI agents to call typed tools.
- **MCP server** — process exposing tools to MCP clients. May be remote (Fabric Core)
  or local (Fabric local MCP).
- **MCP tool** — a single typed operation an agent can invoke.
- **Skill (for Fabric)** — a packaged set of agent instructions + tool calls that
  solves a workload-specific task (e.g., "create a KQL database with these tables").

## This repo

- **Manifest** — a YAML file under `workspaces/`, `items/`, `domains/`, etc. that
  declares the desired state of one resource.
- **Policy** — `rules/policy.yaml`; declarative rules the validator enforces.
- **Validator** — `scripts/validate.py`; schema + policy checker that runs in PRs.
- **Provisioner** — `scripts/provision.py`; idempotent applier that runs on merge.
- **Drift detector** — `scripts/drift.py`; nightly reconciliation between repo and tenant.
- **Marker** — `managed-by:gh:<org>/<repo>@<sha>` string written into a workspace
  description so drift can identify repo-managed resources.
