# Fabric governance rules

This page defines the naming, taxonomy and access-group rules that the repo enforces on every workspace request. To change the standard, update this page and the files below in the same PR.

| File | Holds |
|---|---|
| `rules/policy.yaml` | Teams, domains, capacities, labels, cost centers, quotas and the rule list |
| `schemas/workspace.schema.json` | Manifest fields and their formats |
| `scripts/rules_engine.py` | Rule checks, shared by the PR check and the agent backend |
| `scripts/validate.py` | The PR check, which also checks the manifest file name |

The agent backend bundles copies of the first three files in `api/`. Keep `api/policy.yaml`, `api/workspace.schema.json` and `api/rules_engine.py` byte-identical to the originals.

## Hierarchy

Domains group workspaces by business area, and subdomains split a domain further. Every manifest names one domain and one subdomain. Environments aren't domains: the environment is the first segment of the workspace name, so one subdomain holds the dev, stg and prd copies of a workload.

```text
Fabric tenant
├── dom-fin-corp
│   ├── sdm-fin-rev    → dev-fin-revenue, stg-fin-revenue, prd-fin-revenue
│   └── sdm-fin-cost   → dev-fin-cost-model
└── dom-plt-data
    └── sdm-plt-sample → dev-plt-sample-hello
```

## Workspace names

```text
Pattern: <environment>-<team>-<workload>
Engine:  ^(?P<environment>prd|stg|dev|sbx)-(?P<team>[a-z0-9]{2,6})-(?P<workload>[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9]))$
Schema:  ^(prd|stg|dev|sbx)-[a-z0-9]{2,6}-[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$
```

| Segment | Format | Meaning |
|---|---|---|
| `environment` | `dev`, `stg`, `prd` or `sbx` | `dev` Development, `stg` Test, `prd` Production, `sbx` sandbox (never promoted) |
| `team` | 2–6 lowercase letters or digits | The owning team, from [Teams](#teams) |
| `workload` | 3–40 lowercase letters, digits and hyphens, starting and ending with a letter or digit | What the workspace is for. Put a layer or subject here (`prd-fin-revenue-gold`) or in [tags](#tags) |

- `<team>-<workload>` stays the same across stages: `dev-fin-revenue`, `stg-fin-revenue`, `prd-fin-revenue`.
- The manifest's `environment` and `team` fields must equal the first two segments.
- The manifest file is `workspaces/<name>.yaml`. Production names start with `prd-`, so the CODEOWNERS rule `/workspaces/prd-*.yaml` covers every production manifest.
- Production rules apply when `environment` is `prd`. They never read the name prefix.
- Names that contain `my`, `personal`, `mine` or `me` as a whole word are rejected. `dev-plt-myteam-playground` passes; `dev-plt-my-playground` doesn't.

Examples: `dev-plt-sample-hello`, `dev-sales-core`, `stg-fin-revenue`, `prd-fin-revenue-gold`, `sbx-sec-net-open`.

## Teams

`approvedTeams` in `rules/policy.yaml`:

| Code | Team |
|---|---|
| `plt` | Data platform |
| `fin` | Finance analytics |
| `sales` | Sales analytics |
| `mkt` | Marketing analytics |
| `hr` | People analytics |
| `ops` | Operations |
| `ai` | Data science and AI |
| `sec` | Security and compliance |

A team code outside this list raises a warning (`team-allow-list`), not a block. Add a team through a PR.

## Domains and subdomains

```text
Domain:    dom-<code>-<name>   ^dom-[a-z]{2,4}-[a-z0-9]{2,6}$
Subdomain: sdm-<code>-<name>   ^sdm-[a-z]{2,4}-[a-z0-9]{2,6}$
```

`domain` must be one of the eight `approvedDomains`. `subDomain` only has to match its pattern; the subdomains below are examples.

| Domain | Example subdomains |
|---|---|
| `dom-fin-corp` | `sdm-fin-rev`, `sdm-fin-cost` |
| `dom-hr-people` | `sdm-hr-talent`, `sdm-hr-pay` |
| `dom-sls-crm` | `sdm-sls-orders`, `sdm-sls-acct` |
| `dom-mkt-brand` | `sdm-mkt-camp`, `sdm-mkt-web` |
| `dom-ops-supply` | `sdm-ops-inv`, `sdm-ops-logi` |
| `dom-svc-care` | `sdm-svc-cases`, `sdm-svc-csat` |
| `dom-plt-data` | `sdm-plt-sample`, `sdm-plt-shared` |
| `dom-grc-risk` | `sdm-grc-audit`, `sdm-grc-priv` |

Team codes and domain codes differ on purpose (`sales` vs `sls`): the team says who owns the workspace, and the domain says which business area its data belongs to.

## Capacities, environments and quotas

`approvedCapacities`:

| Name | Capacity ID | Region | Environments | SKU |
|---|---|---|---|---|
| `contosononprodf2` | `33333333-3333-3333-3333-333333333333` | `northeurope` | `sbx`, `dev`, `stg` | F2 |
| `contosoprodf4` | `66666666-6666-6666-6666-666666666666` | `northeurope` | `prd` | F4 |

Replace each placeholder ID with your capacity's ID. In a lab, both entries can point to the same capacity. Use the Azure capacity name as the key: 3–63 lowercase letters or digits, starting with a letter.

A manifest's `capacity` must be one of these names, the capacity must allow the manifest's `environment`, and `region` must equal the capacity's region.

`quotas.perGroupPerEnv` caps the workspaces each owning group can hold per environment: `sbx` 50, `dev` 25, `stg` 10, `prd` 5. No rule checks the quota yet.

## Access groups

Workspace role groups:

```text
Pattern: grp_<fabric|powerbi>_<env>_<team>_<role>
Regex:   ^grp_(fabric|powerbi)_(sbx|dev|stg|prd)_[a-z0-9]{2,6}_(admin|member|contributor|viewer)$
```

| Segment | Values |
|---|---|
| Service | `fabric` or `powerbi` |
| Environment | `sbx`, `dev`, `stg` or `prd` |
| Team | A code from [Teams](#teams) |
| Role | `admin`, `member`, `contributor` or `viewer`, the workspace role the group holds |

Examples: `grp_fabric_dev_plt_admin`, `grp_fabric_prd_fin_member`, `grp_powerbi_stg_ai_viewer`.

Set `groupName` on each Group owner in the manifest. The `owner-group-naming` rule warns when it doesn't follow the pattern.

Security groups that scope tenant settings use `sg-<purpose>`. The automation service principal's group is `sg-fabric-workspace-provisioner`.

## Tags

`tags` is optional: a list of up to 10 unique Fabric tag names. A manifest can only use tags that already exist. Fabric admins create tenant-level tags; Fabric or domain admins create domain-level tags, which work only on workspaces assigned to that domain. See [Tags in Microsoft Fabric](https://learn.microsoft.com/fabric/governance/tags-overview).

```yaml
tags:
  - Finance
  - Certified source
```

> **Preview** (checked 2026-11-27): Apply Workspace Tags API — [Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/apply-workspace-tags). GA route: apply the tags in the Fabric portal, in the workspace settings under Tags.

`scripts/provision.py` applies each manifest tag the workspace doesn't have yet and never removes one. Names must match exactly. When a tenant tag and a domain tag share a name, it uses the tenant tag. It uses a domain tag only when the workspace is in that domain, and it doesn't assign domains. A name with no usable tag gets a warning and is skipped. The List Tags API allows 25 requests a minute, so each run lists the tags once.

## Rules

| Rule ID | Severity | Checks |
|---|---|---|
| `schema` | block | The manifest matches `schemas/workspace.schema.json`. The other rules, except `manifest-filename`, run only when it does. |
| `manifest-filename` | block | The file is `workspaces/<name>.yaml`. Only `scripts/validate.py` checks it, because the agent backend writes that path itself. |
| `naming-convention` | block | `name` matches `<environment>-<team>-<workload>` |
| `name-segments-match-fields` | block | The environment and team segments equal the `environment` and `team` fields |
| `capacity-allow-list` | block | `capacity` is in `approvedCapacities` |
| `capacity-allowed-for-env` | block | The capacity allows the manifest's `environment` |
| `region-matches-capacity` | block | `region` equals the capacity's region |
| `team-allow-list` | warn | `team` is in `approvedTeams` |
| `domain-allow-list` | block | `domain` is in `approvedDomains` |
| `subdomain-pattern` | block | `subDomain` matches `sdm-<code>-<name>` |
| `owners-min-two-groups` | block | At least 2 owners, at least one of them a Group |
| `owners-have-admin` | block | At least one owner has the Admin role |
| `owner-groups-exist` | block | Each Group owner exists in Microsoft Entra ID. Runs only with `LIVE_CHECKS=true`. |
| `owner-group-naming` | warn | Each `groupName` follows the [workspace role group pattern](#access-groups) |
| `sensitivity-required` | block | `sensitivityLabel` is set and in `approvedSensitivityLabels` |
| `cost-center-allow-list` | block | `costCenter` is in `approvedCostCenters` |
| `description-quality` | block | `description` has at least 30 characters |
| `no-personal-workspaces` | block | `name` has no whole word `my`, `personal`, `mine` or `me` |
| `prod-extra-controls` | block | With `environment: prd`, the label is Confidential or Highly Confidential and at least 2 owners are Groups |
| `tags-exist-in-tenant` | warn | Each name in `tags` exists in the tenant. Runs only with `LIVE_CHECKS=true`. |

Blocking findings fail the PR check. Warnings show in the report but don't fail it. With `LIVE_CHECKS=true`, a 401 or 403 from Microsoft Graph or Fabric stops validation: `scripts/validate.py` exits 2, and its report names the permission to fix.

## Sample manifest

`workspaces/dev-plt-sample-hello.yaml` passes every rule:

```yaml
name: dev-plt-sample-hello
environment: dev
team: plt
domain: dom-plt-data
subDomain: sdm-plt-sample
description: "Sample workspace created via PR-based governance to validate the end-to-end approval and provisioning workflow."
capacity: contosononprodf2
region: northeurope
sensitivityLabel: General
costCenter: CC-1001
owners:
  - principalType: Group
    identifier: 44444444-4444-4444-4444-444444444444   # Object ID of grp_fabric_dev_plt_admin (replace with your group's)
    role: Admin
    groupName: grp_fabric_dev_plt_admin
  - principalType: User
    identifier: workspace-owner@contoso.com   # UPN or Object ID of a workspace owner
    role: Member
```

## Automation permissions

`scripts/provision.py`, `scripts/drift.py` and the `LIVE_CHECKS=true` rules sign in as the automation service principal. Add its security group, `sg-fabric-workspace-provisioner`, to these tenant settings:

- Service principals can create workspaces, connections, and deployment pipelines (off by default in new tenants)
- Service principals can call Fabric public APIs
- Service principals can access read-only admin APIs
- Service principals can access admin APIs used for updates

To assign a capacity, the service principal needs Contributor permissions on the capacity and the Admin role on the workspace. Its app needs the Microsoft Graph application permissions `GroupMember.Read.All` (or `Group.Read.All`) and `User.Read.All`, with admin consent.

Keep the service principal out of the Fabric administrator and capacity admin roles and out of label publishing policies. Don't give it admin-consent Power BI API permissions such as `Tenant.ReadWrite.All`: admin APIs reject a service principal that has them.

The scripts stop on a 401 or 403 and print the permission the call needs. They never treat either as "not found".

## Drift

`scripts/drift.py` compares the tenant with `workspaces/*.yaml`. `.github/workflows/drift.yml` runs it daily on a self-hosted runner once you enable the workflow. It reports:

- Active workspaces that have no manifest, and manifests that have no workspace
- Managed workspaces the service principal holds no role on; their description isn't checked
- A description that differs from the manifest
- An owner with no access or a different role, and a principal with access that isn't an owner (the automation service principal is ignored)
- A manifest tag that isn't applied, and an applied tag that isn't in the manifest

It doesn't compare capacity, domain or sensitivity label, and it changes nothing.

It exits 0 when it finds no drift, 2 when it finds drift and 3 when a call returns 401 or 403. On exit 2 the workflow opens an issue from `drift-report.md`. On exit 3 the job fails, and the report says the check didn't run. `scripts/provision.py` also exits 3 on a 401 or 403.

The workspace list and applied tags come from the admin List Workspaces API, and roles from one List Workspace Access Details call per managed workspace. Each API allows 200 requests an hour. When Fabric throttles a call, the script waits for the `Retry-After` time and retries.

> **Preview** (checked 2026-11-27): List Workspace Access Details API — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspace-access-details). GA route: List Workspace Role Assignments ([Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/list-workspace-role-assignments)), which needs Member or higher on each workspace.
