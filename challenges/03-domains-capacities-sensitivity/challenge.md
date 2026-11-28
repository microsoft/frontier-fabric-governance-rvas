# Challenge 03 — Domains, capacities and sensitivity labels

> **Outcome:** every workspace sits in the subdomain and on the capacity its
> manifest declares, and only a PR changes either. Its items carry at least the
> label the manifest declares, applied by a domain default label or by people
> with label rights, and a nightly scan proves it. Production runs on its own
> capacity, both capacities have surge protection, Finance's domain admins
> choose who certifies Finance items, and a DLP policy for Highly Confidential
> items runs in simulation mode.

## Why this challenge exists

Domains decide where a workspace appears in the OneLake catalog and who
governs it. Capacities decide who pays for it and what compute it gets.
Sensitivity labels follow the data when it's exported to supported file types,
and Purview policies act on them. A domain or capacity changed in the portal
breaks chargeback and the audit trail, and an unlabeled item escapes those
policies.

Labels need a different approach from placement. Fabric labels items, not
workspaces, and the automation service principal (SPN) has no label rights.
So the SPN places workspaces, people with label rights apply labels, and a
scan checks both.

Other controls stay with people too, because the SPN lacks the rights or no
API sets them. A capacity admin turns on surge protection, which limits the
compute that background operations use, to keep resources available for
interactive work. A domain's admins override, in the portal, the tenant
settings that a Fabric administrator delegates to them, such as who certifies
items. People with a DLP role create DLP policies, which act on labels, in
Microsoft Purview.

## Learning objectives

1. Design domains, subdomains and domain roles, declare them as code
   (`domains/*.yaml`), and create them from the manifests.
2. Declare capacities as code (`capacities/*.yaml`), keep production on its
   own capacity, and turn on surge protection.
3. Validate placement before merge, with production rules keyed on the
   `environment` field.
4. Assign each workspace to its subdomain when the provisioner creates it.
5. Label items through the supported routes, and prove coverage with the
   metadata scanner.
6. Detect domain, capacity and label drift nightly, and flag label downgrades
   in the PR.
7. Set a default domain, delegate certification to a domain's admins, and test
   a DLP policy in simulation mode.
8. Check placement from chat with the Fabric Core MCP, and audit domains and
   labels with the `onelake-catalog-cli` Skill.

## Prerequisites

- Challenges 00–01 complete. The SPN's group, `sg-fabric-workspace-provisioner`,
  is enabled in the four tenant settings from
  [challenge 00](../00-setup/challenge.md):
  - Service principals can create workspaces, connections, and deployment pipelines
  - Service principals can call Fabric public APIs
  - Service principals can access read-only admin APIs
  - Service principals can access admin APIs used for updates

  The two admin API settings let the SPN call the domain and scanner APIs
  without being a Fabric administrator
  ([Learn](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)).
- The SPN isn't a Fabric administrator or a capacity admin, has no
  admin-consent Power BI permissions and isn't in any label publishing policy.
  It has Contributor permissions on both capacities and is Admin of the
  workspaces it manages. It also has the Microsoft Graph application
  permissions `GroupMember.Read.All` (or `Group.Read.All`) and `User.Read.All`.
- A Fabric administrator who signs in as a user and has the labels below in
  their label publishing policy. Tasks 1, 5, 6 and 8 have steps for this
  person.
- Two capacities that match `approvedCapacities` in `rules/policy.yaml`:
  `contosononprodf2` for sbx, dev and stg, and `contosoprodf4` for prd. In a
  lab, both entries can point to the same capacity. Task 2 needs a capacity
  admin of each.
- Sensitivity labels published in Microsoft Purview, at least Public, General,
  Confidential and Highly Confidential, and a compliance admin who can run
  `Get-Label` in Security & Compliance PowerShell.
- A member of `grp_fabric_prd_fin_admin`, the Finance domain's admin group,
  for Tasks 8 and 9. For Task 9, Highly Confidential must be in their label
  publishing policy.
- The security groups `sg-fabric-fin-engineers` and
  `sg-fabric-fin-certifiers`, for Task 8.
- For Task 9, a person with a DLP role, such as Compliance administrator.
  Learn lists the roles and licenses
  ([Learn](https://learn.microsoft.com/fabric/governance/data-loss-prevention-configure)).
- The Fabric Core MCP server and Skills for Fabric, installed as shown below.

Purview remains the security and compliance layer. Only sensitivity labels, protection policies and DLP need Purview licensing; everything else works with a Fabric license.

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

## Tasks

### Task 1 — Domains as code

Design the domains before you declare them. Learn's
[domain best practices](https://learn.microsoft.com/fabric/governance/domains-best-practices)
describe structures by business function, product or project, process or
region, or a mix, and help you decide whether you need subdomains. This repo
allows one level of subdomains, and the schema enforces it. Three roles govern
a domain:

| Role | In this challenge | Can |
| --- | --- | --- |
| Fabric administrator | People who sign in as users, not the SPN | Create, rename and delete domains, set their admins and contributors, and assign any workspace |
| Domain admin | `grp_fabric_prd_fin_admin` for Finance | Create subdomains, edit the description and contributors, assign workspaces, set the default domain and override delegated settings, but not rename or delete the domain or change its admins |
| Domain contributor | Nobody after step 5 below, except through a default domain (Task 8) | Assign workspaces they're admins of to the domain |

Domains don't control access. Assigning a workspace to a domain doesn't change
who can see or open its items, and every user in the tenant sees every domain.

Add `schemas/domain.schema.json` and one manifest per domain under `domains/`,
named `<name>.yaml`. Start with `domains/dom-plt-data.yaml`, the domain of the
sample workspace `dev-plt-sample-hello`, with the subdomain `sdm-plt-sample`.
Then add a Finance domain:

```yaml
name: dom-fin-corp
displayName: Finance
description: Finance reporting, planning and cost data.
defaultLabel: Confidential
admins:
  - groupName: grp_fabric_prd_fin_admin
subdomains:
  - name: sdm-fin-rev
    displayName: Revenue
    description: Revenue reporting and forecasts.
  - name: sdm-fin-cost
    displayName: Cost
    description: Cost allocation and chargeback.
```

The schema enforces Fabric's limits and the repo's names:

- `name` matches `^dom-[a-z]{2,4}-[a-z0-9]{2,6}$` and each subdomain `name`
  matches `^sdm-[a-z]{2,4}-[a-z0-9]{2,6}$`, the patterns the rules engine uses.
- `displayName` has 40 characters or fewer, and `description` 256 or fewer.
- `defaultLabel` is one of `approvedSensitivityLabels` in `rules/policy.yaml`.
- `id`, on a domain or a subdomain, is optional and holds the Fabric domain ID
  once the domain exists.
- A subdomain can't have `subdomains`.

The rules engine keeps reading `approvedDomains` in `rules/policy.yaml`; the
manifests add what the scripts need. Add a check to `scripts/validate.py` that
fails when `domains/` and `approvedDomains` don't list the same domains.

Then write `scripts/apply_domains.py`. It runs as the SPN after a merge to
`main`:

1. List the domains with `GET /v1/admin/domains`. Match each manifest domain
   and subdomain on its `id` when it has one. Otherwise match a domain on
   `displayName`, and a subdomain on `displayName` and `parentDomainId`.
2. Create what's missing. A subdomain is a domain with a `parentDomainId`:

   ```http
   POST https://api.fabric.microsoft.com/v1/admin/domains
   Content-Type: application/json

   {
     "displayName": "Revenue",
     "description": "Revenue reporting and forecasts.",
     "parentDomainId": "{domainId}"
   }
   ```

3. Resolve each admin `groupName` to an object ID with Microsoft Graph. Stop if
   no group, or more than one, has that name.
4. Make the groups admins of their domain:

   ```http
   POST https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/roleAssignments/bulkAssign
   Content-Type: application/json

   {
     "type": "Admins",
     "principals": [{ "id": "{groupId}", "type": "Group" }]
   }
   ```

   Subdomains have no admins of their own: a subdomain's admins are the
   admins of its parent domain
   ([Learn](https://learn.microsoft.com/fabric/governance/domains)).

5. Remove the domain contributors. By default, everyone in the organization
   is a contributor of a new domain, so any workspace admin can assign their
   workspace to it. For each domain and subdomain, list the role assignments
   with `GET /v1/admin/domains/{domainId}/roleAssignments`, following
   `continuationUri` until a response has none. Unassign every `Contributor`,
   passing its principal's `id` and `type`:

   ```http
   POST https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/roleAssignments/bulkUnassign
   Content-Type: application/json

   {
     "type": "Contributors",
     "principals": [{ "id": "{principalId}", "type": "{principalType}" }]
   }
   ```

   List them again, and stop with an error if a `Contributor` is left. Then
   only Fabric administrators and the domain's admins can assign workspaces to
   it in the portal. The provisioner in Task 4 uses the admin API, which
   doesn't need contributor rights. This step runs on every provision run, so
   it also removes contributors that someone adds in the portal.

6. Print a map from each manifest name to its domain ID.

After the first run, copy the printed IDs into the manifests as `id`, in a
follow-up PR. Until a domain has its `id`, a rename in the portal looks like a
missing domain, and the script would create a second one.

The script never renames or deletes a domain. It reports a Fabric domain that
no manifest describes, and a manifest whose `displayName` differs from Fabric's,
and a Fabric administrator decides what to do. Give it a `--dry-run` flag that
prints the plan without calling a write API, so reviewers see a new domain
before it exists. Stop on 401 or 403 with a clear error, and never treat either
as "not found".

Wire it into the workflows. Add `domains/**` and `capacities/**` to the path
filters in `.github/workflows/validate.yml` and
`.github/workflows/provision.yml`. In validate, run
`python scripts/apply_domains.py --dry-run` when `LIVE_CHECKS` is true. In
provision, run `python scripts/apply_domains.py` before `scripts/provision.py`.

No Core MCP tool manages domains, so this task calls the admin REST APIs, which
the SPN reaches through the admin API tenant settings.

Check the domains as a Fabric administrator. In a Copilot CLI session:

```text
/onelake-catalog-cli Find ownerless domains and domains whose contributor scope is the entire tenant.
```

Every domain in `domains/` should pass. A subdomain listed without admins is
expected: its admins are those of its parent domain. If a domain has no
admins, add an admin group to its manifest. If one still has the whole tenant
as a contributor, check the `apply_domains.py` step of the last provision run.

### Task 2 — Capacities as code

Add one manifest per capacity under `capacities/`, named after its key in
`approvedCapacities`. Draft them from chat. In a Copilot CLI session with the
Fabric Core MCP connected:

```text
Use list_capacities and draft one YAML file per capacity for capacities/, with name, capacityId, region and sku. Name them contosononprodf2 and contosoprodf4.
```

Then add the environments each capacity accepts:

```yaml
name: contosononprodf2
capacityId: 33333333-3333-3333-3333-333333333333
region: northeurope
sku: F2
allowedEnvironments: [sbx, dev, stg]
```

```yaml
name: contosoprodf4
capacityId: 66666666-6666-6666-6666-666666666666
region: northeurope
sku: F4
allowedEnvironments: [prd]
```

The rules engine reads `approvedCapacities` in `rules/policy.yaml`, so keep that
block. Add a check to `scripts/validate.py` that fails when it and
`capacities/` disagree on a field they share. If you change
`rules/policy.yaml`, copy it to `api/policy.yaml`; the two files must stay
identical.

These capacities follow the environment model of
[challenge 08](../08-deployment-pipelines/challenge.md): one workspace per
stage (dev, stg and prd), Git on dev only, a deployment pipeline that promotes
to stg and prd, and sbx workspaces that are never promoted.
`allowedEnvironments` keeps production alone on `contosoprodf4`, because
throttling and capacity-level surge protection act on a whole capacity, and
Learn recommends isolating critical solutions in their own capacity
([Learn](https://learn.microsoft.com/fabric/enterprise/surge-protection)). A
lab with one capacity has no such isolation.

**Surge protection.** When a capacity's 24-hour background percentage reaches
the rejection threshold, surge protection rejects new background operations
until the percentage drops below the recovery threshold. Without it, the
capacity lets the percentage reach 100% before it rejects them. Declare the
thresholds in both manifests:

```yaml
surgeProtection:
  state: Enabled
  rejectionThreshold: 80
  recoveryThreshold: 60
```

Make `scripts/validate.py` check that `rejectionThreshold` is between 15 and
100, and that `recoveryThreshold` is above 5 and below `rejectionThreshold`.
80 and 60 are a starting point for capacities with no history. Tune them from
the **Background rejection**, **Interactive rejection** and **Utilization**
charts on the Compute page of the Capacity Metrics app.

A capacity admin applies the settings, because the SPN isn't one and no MCP
tool or Skill covers surge protection. In Settings > Admin portal >
**Capacity settings**, select the capacity, expand **Surge protection**, set
**Background Operations** to **On**, enter the thresholds and select
**Apply**. Or call the API:

```bash
az login
capacity=33333333-3333-3333-3333-333333333333
az rest --method patch --url "https://api.fabric.microsoft.com/v1/capacities/$capacity/surgeProtection" --resource https://api.fabric.microsoft.com --body '{"state": "Enabled", "rejectionThreshold": 80, "recoveryThreshold": 60}'
az rest --method get --url "https://api.fabric.microsoft.com/v1/capacities/$capacity/surgeProtection" --resource https://api.fabric.microsoft.com
```

Repeat with `capacity=66666666-6666-6666-6666-666666666666`. Both calls need
a capacity admin, so the drift job can't check these settings.

In the Capacity Metrics app, the **System events** table on the Compute page
shows `SurgeProtectionActive` when surge protection starts rejecting and
`NotOverloaded` when the capacity is back below all thresholds. Jobs that are
already running continue, so the percentage can pass the threshold. Surge
protection doesn't block operations billed with autoscale or affect OneLake
activities, and it doesn't guarantee that interactive requests aren't delayed
or rejected.

### Task 3 — Validate placement

The rules engine already blocks a misplaced workspace. These rules from the
[governance rules](../../docs/governance-rules.md) cover this challenge:

| Rule | Blocks a manifest when |
| --- | --- |
| `capacity-allow-list` | `capacity` isn't in `approvedCapacities` |
| `capacity-allowed-for-env` | the capacity doesn't allow the manifest's `environment` |
| `region-matches-capacity` | `region` isn't the capacity's region |
| `domain-allow-list` | `domain` isn't in `approvedDomains` |
| `subdomain-pattern` | `subDomain` doesn't match `sdm-<code>-<name>` |
| `sensitivity-required` | `sensitivityLabel` is missing or not in `approvedSensitivityLabels` |
| `prod-extra-controls` | `environment` is `prd` and the label is below Confidential, or fewer than two owners are groups |

Production rules key on the `environment` field, never on the `prd-` name
prefix. `name-segments-match-fields` makes the prefix agree with `environment`,
so a rule that reads the field covers every production workspace.

Add two rules to `scripts/validate.py`:

- `domain-manifest-exists` (block): `domains/<domain>.yaml` exists.
- `subdomain-in-domain-manifest` (block): `subDomain` is one of the subdomains
  in that manifest.

They belong in `scripts/validate.py` rather than the rules engine, because they
read `domains/`. `scripts/rules_engine.py` must stay identical to its copy,
`api/rules_engine.py`, which runs without the repo's `domains/` folder.

Test with a production manifest on the wrong capacity,
`workspaces/prd-fin-revenue.yaml`:

```yaml
name: prd-fin-revenue
environment: prd
team: fin
domain: dom-fin-corp
subDomain: sdm-fin-rev
description: "Revenue reporting for Finance, promoted from stg by the deployment pipeline."
capacity: contosononprodf2
region: northeurope
sensitivityLabel: Confidential
costCenter: CC-2042
owners:
  - principalType: Group
    identifier: <object-id-of-grp_fabric_prd_fin_admin>
    role: Admin
    groupName: grp_fabric_prd_fin_admin
  - principalType: Group
    identifier: <object-id-of-grp_fabric_prd_fin_member>
    role: Member
    groupName: grp_fabric_prd_fin_member
```

`python scripts/validate.py workspaces/prd-fin-revenue.yaml` fails on
`capacity-allowed-for-env`. With `capacity: contosoprodf4` it passes, and with
`sensitivityLabel: General` it fails again, on `prod-extra-controls`.

### Task 4 — Assign each workspace to its subdomain

Extend `scripts/provision.py`. After it creates the workspace and assigns the
capacity, it assigns the workspace to the subdomain in `subDomain`, not to the
parent domain:

```http
POST https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/assignWorkspaces
Content-Type: application/json

{ "workspacesIds": ["{workspaceId}"] }
```

Here `{domainId}` is the subdomain's `id` from its domain manifest. Read the
workspace first with Get Workspace, and skip the call when its `domainId`
already matches. The API allows 10 requests a minute, so put all the
workspaces of a subdomain in one call.

Fix the error handling too. Today `reconcile_workspace()` prints
`warn: assignToCapacity` and carries on, so a workspace can end up on the wrong
capacity, or none, without failing the run. Make a failed capacity or domain
assignment fail the run. A 401 or 403 already stops the run with exit code 3;
make the domain calls with `_request()` from `scripts/_fabric.py`, and they do
the same.

A new workspace has no domain, so the call assigns it. A workspace someone
moved to another domain in the portal is different: the drift job in Task 6
reports it, and the next provision run moves it back. Start that run by hand
from the Actions tab rather than waiting for the next merge.

> **Preview** (checked 2026-11-27): Allow tenant and domain admins to override workspace assignments — [Learn](https://learn.microsoft.com/fabric/admin/service-admin-portal-domain-management-settings). GA route: unassign the workspace from its current domain, then assign it.

The domain APIs respect the domain management setting **Allow tenant and
domain admins to override workspace assignments (preview)**. While it's on,
the default, the assign call moves the workspace in one step. When it's off,
the call can't move a workspace that's already in a domain, so the provisioner
first removes it from its current domain:

```http
POST https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/unassignWorkspaces
Content-Type: application/json

{ "workspacesIds": ["{workspaceId}"] }
```

Here `{domainId}` is the domain the workspace is in now, from Get Workspace.
Then it assigns the workspace as above.

Check the result from chat. In a Copilot CLI session with the Fabric Core MCP
connected:

```text
Use get_workspace for "dev-plt-sample-hello" and show its domainId and capacityId. Compare them with the sdm-plt-sample ID that apply_domains.py printed and with contosononprodf2 in rules/policy.yaml.
```

If the answer leaves out `domainId`, call Get Workspace over REST; it returns
`domainId` and `capacityId`.

Then audit domain coverage with a Skill. In a Copilot CLI session:

```text
/onelake-catalog-cli Which workspaces I administer are not assigned to a domain?
```

Every managed workspace should have a domain. For the others, ask for a plan
without applying it:

```text
/onelake-catalog-cli Show a dry run for assigning these workspaces to the Finance domain, including current assignments.
```

Bring a workspace under management with a manifest PR rather than the Skill's
remediation, so the repo stays the source of truth.

### Task 5 — Label items

Fabric labels items, not workspaces: no API puts a label on a workspace. So
treat the manifest's `sensitivityLabel` as a floor: every item in the
workspace carries that label or a higher one. The SPN isn't in a label
publishing policy, so it can't apply labels. People apply them through three
routes, and the scanner checks the result.

First, map label names to IDs. A compliance admin runs, in PowerShell:

```powershell
Connect-IPPSSession -UserPrincipalName compliance-admin@contoso.com
Get-Label | Format-Table -Property DisplayName, Guid, Priority
```

Record each label's `Guid` and `Priority` in `rules/labels.yaml`. A higher
priority means a more sensitive label. Copy what `Get-Label` returns; your
priorities differ if your labels have sublabels.

```yaml
labels:
  Public:
    id: <public-label-id>
    priority: 0
  General:
    id: 77777777-7777-7777-7777-777777777777
    priority: 1
  Confidential:
    id: 88888888-8888-8888-8888-888888888888
    priority: 2
  Highly Confidential:
    id: 99999999-9999-9999-9999-999999999999
    priority: 3
```

**Route 1 — a domain default label for new items.**

> **Preview** (checked 2026-11-27): Domain default sensitivity label — [Learn](https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label). GA route: Bulk Set Labels run by a Fabric administrator user, or the documented manual labeling step.

A Fabric administrator turns on the tenant setting **Domain admins can set
default sensitivity labels for their domains (preview)**, in this section:
OneLake catalog > Govern > Configurations > Tenant settings > Information
protection; where Govern isn't available, use Settings > Admin portal > Tenant
settings. Then a domain admin sets the manifest's `defaultLabel` in the
domain's settings, or a Fabric administrator signed in as a user sets it with
Update Domain:

```http
PATCH https://api.fabric.microsoft.com/v1/admin/domains/{domainId}
Content-Type: application/json

{ "defaultLabelId": "88888888-8888-8888-8888-888888888888" }
```

Set it on the parent domain, because subdomains have general settings only. To
remove a default, send `00000000-0000-0000-0000-000000000000`.

Learn says the default applies to items in workspaces that belong to the
domain. It doesn't say whether that includes its subdomains' workspaces, and
Task 4 puts every workspace in a subdomain. Test it once: create a lakehouse in
a subdomain's workspace and check that it carries the parent domain's default
label. If it doesn't, routes 2 and 3 label new items too.

The default label applies when someone creates and saves a new item, or saves
an unlabeled one. It never replaces a label someone applied by hand, or a
higher label. Items that Git integration or deployment pipelines create don't
get it, so routes 2 and 3 cover them.

**Route 2 — Bulk Set Labels for existing items.** A Fabric administrator signed
in as a user labels the items that already exist, and those that Git or a
pipeline created. The API doesn't accept a service principal, and the label
must be in the administrator's own label publishing policy. Each request takes
up to 2,000 items, and the API allows 25 requests an hour. Save the body as
`labels-request.json`:

```json
{
  "items": [
    { "id": "{itemId}", "type": "Lakehouse" },
    { "id": "{itemId}", "type": "SemanticModel" }
  ],
  "labelId": "88888888-8888-8888-8888-888888888888"
}
```

Then run:

```bash
az login
az rest --method post --url https://api.fabric.microsoft.com/v1/admin/items/bulkSetLabels --resource https://api.fabric.microsoft.com --body @labels-request.json
```

**Route 3 — label one item by hand.** Someone who can edit the item, and has
the label in their policy, sets it in the item's settings. Note the item in the
PR or issue that asked for the label.

**Prove it with the scanner.** The drift job in Task 6 reads every item's label
with the metadata scanner (Power BI admin API; no Fabric API yet). The SPN calls
it through the **Service principals can access read-only admin APIs** setting,
with a token for `https://analysis.windows.net/powerbi/api/.default`:

```http
POST https://api.powerbi.com/v1.0/myorg/admin/workspaces/getInfo
Content-Type: application/json

{ "workspaces": ["{workspaceId}"] }
```

Poll `GET https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanStatus/{scanId}`
until the scan succeeds, then read
`GET https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanResult/{scanId}`.
In each workspace, walk every item list and read `sensitivityLabel.labelId`.
An item with no label, or with a lower priority than the manifest's label, is a
gap. One request covers up to 100 workspaces, and the API allows 500 requests
an hour and 16 at a time.

Spot-check items from chat. In a Copilot CLI session with the Fabric Core MCP
connected:

```text
Use list_items for "dev-plt-sample-hello", then get_item for each item, and show each item's sensitivity label ID next to the IDs in rules/labels.yaml.
```

If an answer leaves out `sensitivityLabel`, call Get Item over REST; it returns
the label's `id`.

### Task 6 — Detect drift

`scripts/drift.py` reports unmanaged and missing workspaces, workspaces the
SPN can't see, description differences, role drift and missing or extra tags.
It doesn't compare domain, capacity or sensitivity label, and it doesn't check
items. Add these checks:

- **Domain:** the workspace's `domainId` against the `id` of its manifest's
  subdomain.
- **Capacity:** the workspace's `capacityId` against the `capacityId` in
  `capacities/<capacity>.yaml`.
- **Item labels:** the scan from Task 5 against each manifest's
  `sensitivityLabel`.
- **Domain default labels:** each domain's `defaultLabelId` against its
  manifest's `defaultLabel`, through `rules/labels.yaml`.
- **Domains:** Fabric domains that no manifest describes, and manifests with no
  Fabric domain.

Read `domainId` and `capacityId` from the admin List Workspaces entries that
`check()` already fetches, in `tenant[name]`, not from Get Workspace. The
entries carry both fields even for workspaces the SPN holds no role on, and
reading them adds no calls against the API's limit of 200 requests an hour.

The other checks need two new calls. Add a helper for each to
`scripts/_fabric.py`, built on `_request()`, and pass `hint=HINT_ADMIN_READ`
so a permission error names the tenant setting to check:

- Admin List Domains, `GET /v1/admin/domains`, once per run. It returns each
  domain's `defaultLabelId` and allows 25 requests a minute. Match the domains
  to the manifests as `apply_domains.py` does, so a subdomain that has no `id`
  yet still gets an expected ID.
- The metadata scanner from Task 5, once per run for all the managed
  workspaces. It's a Power BI admin API, so pass `scope=PBI_SCOPE`.

In `check()`, add each workspace's findings to its `issues` list, with the
expected and actual values, so they appear under the workspace's heading in
`drift-report.md`. Put the domain findings under a new `## Domains` heading,
and include them in the `found` value that `check()` returns.

Keep the exit codes: `drift.py` exits with code 2 when it finds drift, and
with code 3 when `_request()` raises `AuthError` on a 401 or 403. Don't change
`.github/workflows/drift.yml`. On code 2 it opens an issue, "Fabric workspace
drift detected", labeled `drift` and `governance`, so your findings land in
that issue. Any other non-zero code fails the job, so a permission problem
fails the run instead of showing up as drift. The workflow opens a new issue
on every run that finds drift and never closes one, so close each one after a
clean rerun.

Compare the report with the Skill's view of the whole tenant. In a Copilot CLI
session, signed in as a Fabric administrator:

```text
/onelake-catalog-cli Find unlabeled items tenant-wide and explain which remediations require a tenant admin versus a data owner.
```

Items in managed workspaces should match the drift report; send the rest to
their owners. Don't apply the Skill's bulk label changes: they don't support a
service principal, and labels go through Task 5's routes.

### Task 7 — Review label changes

Lowering a label removes protection, so make it visible in the PR:

1. Add a `label-downgrade` rule (warn) to `scripts/validate.py`. For each
   changed workspace manifest, read the base branch's version with
   `git show origin/main:workspaces/<name>.yaml`, and warn when the new
   `sensitivityLabel` has a lower priority in `rules/labels.yaml`.
2. Production already has a floor: `prod-extra-controls` blocks a manifest with
   `environment: prd` and a label below Confidential.
3. In `.github/CODEOWNERS`, add the security team to the production manifests,
   and cover the domain manifests and the label map:

   ```text
   /workspaces/prd-*.yaml  @your-org/fabric-governance-maintainers @your-org/fabric-security
   /domains/               @your-org/fabric-governance-maintainers @your-org/fabric-security
   /rules/labels.yaml      @your-org/fabric-security
   ```

CODEOWNERS matches paths, not fields, and the `prd-*.yaml` path is safe here:
`manifest-filename` and `name-segments-match-fields` tie the file name to
`environment`, so every manifest with `environment: prd` is named `prd-*.yaml`.

### Task 8 — Default domain and delegated settings

A domain's **Domain settings** pane holds two settings that no API, MCP tool
or Skill sets: the default domain and the delegated settings. Subdomains have
general settings only, so both go on the parent domain. A member of
`grp_fabric_prd_fin_admin` opens the OneLake catalog, selects **Govern** >
**Domains**, opens Finance and selects **Domain settings**. Where Govern isn't
available, use Settings > Admin portal > **Domains**.

**Default domain.** A default domain puts the workspaces that a group's
members create into a domain, so the domain's default label and delegated
settings apply to them from the start. Select **Default domain**, add
`sg-fabric-fin-engineers` and select **Apply**. Unassigned workspaces whose
admin is in the group, and new workspaces its members create, then go to
Finance. Workspaces already in a domain stay there.

Learn says the group's members generally become domain contributors of those
workspaces too, so a default domain changes permissions as well as placement.
The drift job lists the new workspaces as unmanaged, because they have no
manifest. Bring each one in with a manifest PR, or have its owner delete it.
No API reads the default domain, so it has no manifest field and no drift
check.

**Delegated certification.** A Fabric administrator decides which tenant
settings a domain's admins can override. Delegate certification so that
Finance's own certifiers certify Finance items:

1. Add an optional `certification` object to the domain schema, for domains
   but not subdomains, and record the delegation in
   `domains/dom-fin-corp.yaml`:

   ```yaml
   certification:
     delegated: true
     securityGroups: [sg-fabric-fin-certifiers]
     documentationUrl: https://contoso.sharepoint.com/sites/finance/certification
   ```

2. A Fabric administrator opens the OneLake catalog, selects **Govern** >
   **Configurations** > **Tenant settings** and, under Export and sharing
   settings, expands **Certification**. Where Govern isn't available, use
   Settings > Admin portal > **Tenant settings**. If certification is off,
   they turn it on with the tenant's documentation URL and certifier groups.
   Then they select **Domain admins can enable/disable** and **Apply**.
   Without that option no domain can override the setting. With it, a
   domain's admins can override all of it, including turning certification
   off.
3. The domain admin opens Finance's **Domain settings** >
   **Delegated settings**, expands **Certification**, selects
   **Override tenant admin selection**, enters the documentation URL and
   `sg-fabric-fin-certifiers`, and selects **Apply**.
4. A Fabric administrator checks the override:

   ```bash
   az login
   az rest --method get --url https://api.fabric.microsoft.com/v1/admin/domains/delegatedTenantSettingOverrides --resource https://api.fabric.microsoft.com --query "value[].{domain: id, certification: tenantSettings[?settingName=='CertifyDatasets']}"
   ```

   Finance's domain ID should appear with `enabled: true` and
   `sg-fabric-fin-certifiers` in `enabledSecurityGroups`.

Certifiers then certify items in each item's settings; no API writes
endorsement. [Challenge 09](../09-onelake-catalog-metadata/challenge.md) tags
items from `catalog/tags.yaml`, and its "Delegated certification" stretch goal
checks this `certification` block against the tenant setting and the domain
overrides. [Challenge 12](../12-tenant-settings-policies-as-code/challenge.md)
reports drift in every domain's overrides nightly.

### Task 9 — Test a DLP policy in simulation

Labels mark items, and DLP policies act on them. A policy in simulation mode
reports the items it matches but doesn't restrict access to them. No MCP
tool, Skill or Fabric API manages DLP, so the person with a DLP role uses the
Microsoft Purview portal. If `prd-fin-revenue` doesn't exist yet, merge Task
3's manifest with `capacity: contosoprodf4` first.

1. Open the data loss prevention policies page and select
   **+ Create policy**. Choose the **Custom** category and the
   **Custom policy** template, select **Next**, and name the policy
   `dlp-fabric-fin-highly-confidential`.
2. Select **Next** at **Assign admin units**, because DLP for Fabric doesn't
   support admin units. Choose the location
   **Fabric and Power BI workspaces**, which turns the other locations off.
   Select **Edit**, and include only `prd-fin-revenue`.
3. Select **Create or customize advanced DLP rules** > **Create rule** >
   **Add condition** > **Content contains** > **Add** >
   **Sensitivity labels**, and choose Highly Confidential.
4. Turn on **User notifications**, select
   **Notify users in Office 365 service with a policy tip or email notifications**,
   and then **Policy tips**. Under **Incident reports**, set a severity and
   keep the email to admins. Leave the restrict access action for the stretch
   goal.
5. Select **Run the policy in simulation mode** and the option to show policy
   tips in simulation. Don't select the option that turns the policy on if
   it isn't edited within 15 days. Select **Next** > **Submit**.

DLP evaluates a semantic model when it's published, republished or refreshed,
but not when a service principal starts the event or owns the model, and not
for DirectQuery, live connection or mixed-storage models. So DLP doesn't check
the models that the SPN deploys or owns. To test, a member of
`grp_fabric_prd_fin_admin` publishes a small import model to
`prd-fin-revenue`, labels it Highly Confidential and refreshes it. Open the
policy, which shows **In simulation**, and select **View simulation** >
**Items for review**. The first results can take hours. A simulation runs for
up to 15 days, evaluates only items updated after it starts, and keeps its
results for 30 days. Delete the test model afterward.

## Success criteria

- [ ] `domains/` and `capacities/` validate and match `approvedDomains` and
      `approvedCapacities`, and a second `apply_domains.py --dry-run` plans no
      changes.
- [ ] No domain or subdomain lists a `Contributor`, and the Skill finds no
      ownerless domain and none whose contributor is the entire tenant.
- [ ] Get Capacity Surge Protection returns the state and thresholds in each
      capacity's manifest.
- [ ] `prd-fin-revenue` on `contosononprodf2` fails `capacity-allowed-for-env`,
      and with `sensitivityLabel: General` it fails `prod-extra-controls`.
- [ ] A manifest whose `subDomain` isn't in its domain manifest fails
      `subdomain-in-domain-manifest`.
- [ ] After a merge, Get Workspace shows the declared subdomain's `domainId` and
      the declared capacity's `capacityId`, with no portal steps.
- [ ] The scan shows every item in a managed workspace at or above its
      manifest's label.
- [ ] Moving a workspace to another domain in the portal, or removing an item's
      label, makes the next drift run exit with code 2 and open a drift issue
      that lists the change.
- [ ] A PR that lowers a label gets the `label-downgrade` warning, and a change
      to a `prd-*.yaml` manifest needs the security team's approval.
- [ ] A workspace that a member of `sg-fabric-fin-engineers` creates lands in
      Finance, and the next drift run lists it as unmanaged.
- [ ] The domain overrides list Finance's certification override with
      `sg-fabric-fin-certifiers`.
- [ ] The DLP simulation lists the Highly Confidential test model under
      **Items for review**.
- [ ] The SPN isn't a Fabric administrator or a capacity admin and is in no
      label publishing policy. People with those rights run the label, surge
      protection and tenant setting steps.

## Stretch goals

- **Capacity scale as code.** Add `desiredSku` to the capacity manifests and
  reconcile it through Azure Resource Manager (`Microsoft.Fabric/capacities`).
  Use a separate Azure identity with Contributor on the capacity resource, not
  the Fabric SPN, and make a change above F8 need CODEOWNERS approval.
- **Domains in Terraform.** Manage Finance and its subdomains with the
  `microsoft/fabric` Terraform provider. Add `managedBy: terraform` to the
  domain schema and to `domains/dom-fin-corp.yaml`, and make
  `apply_domains.py` leave that domain and its subdomains to Terraform, apart
  from their roles. Save this as `terraform/domains/main.tf`:

  ```hcl
  terraform {
    required_version = ">= 1.8, < 2.0"
    required_providers {
      fabric = {
        source  = "microsoft/fabric"
        version = "1.15.1"
      }
    }
  }

  provider "fabric" {}

  locals {
    fin  = yamldecode(file("${path.module}/../../domains/dom-fin-corp.yaml"))
    subs = { for s in local.fin.subdomains : s.name => s }
  }

  import {
    to = fabric_domain.fin
    id = local.fin.id
  }

  import {
    for_each = { for k, s in local.subs : k => s.id if try(s.id, null) != null }
    to       = fabric_domain.fin_sub[each.key]
    id       = each.value
  }

  resource "fabric_domain" "fin" {
    display_name = local.fin.displayName
    description  = local.fin.description

    lifecycle {
      ignore_changes  = [display_name, default_label_id]
      prevent_destroy = true
    }
  }

  resource "fabric_domain" "fin_sub" {
    for_each         = local.subs
    display_name     = each.value.displayName
    description      = each.value.description
    parent_domain_id = fabric_domain.fin.id

    lifecycle {
      ignore_changes  = [display_name, default_label_id]
      prevent_destroy = true
    }
  }
  ```

  The `import` blocks adopt the domains that `apply_domains.py` created, so
  the manifests need their `id`s; Terraform creates a subdomain that has none.
  `ignore_changes` and `prevent_destroy` leave renames and deletes to Fabric
  administrators, and the default label to Task 5. Roles stay in
  `apply_domains.py`, because `fabric_domain_role_assignments` can't be
  imported and the API rejects a role that a principal already has. Keep the
  state in a remote backend, such as `azurerm`, and run Terraform as the SPN
  with OIDC like `provision.yml`: `id-token: write`, `FABRIC_USE_OIDC=true`,
  and `FABRIC_TENANT_ID` and `FABRIC_CLIENT_ID` from `vars.AZURE_TENANT_ID`
  and `vars.AZURE_CLIENT_ID`.
- **Workspace surge limits.** Stop one workspace from using up
  `contosononprodf2`, which sbx, dev and stg share. A capacity admin opens the
  OneLake catalog, selects **Govern** > **Capacities** > `contosononprodf2`
  and, under **Surge protection**, turns on **Workspace consumption**.
  **Rejection Threshold** is the share of the capacity's compute that one
  workspace can use over a rolling 24 hours (on an F2, 5% is 2.4 CU hours a
  day), and **Block** sets how long a workspace that passes it stays blocked,
  in hours or indefinitely. Fabric checks usage every five minutes, so the
  limit is soft, and it excludes autoscale compute and some items, such as
  Dataflow Gen1 and paginated reports. Raising the limit doesn't unblock a
  blocked workspace, and the 24-hour window doesn't reset when a block ends.
  So raise the limit first, and then unblock the workspace: Settings > Admin
  portal > **Capacity settings** > the capacity > the workspace in
  **Workspaces** > **Unblock**.
- **Enforce the DLP policy.** When the simulation shows the matches you
  expect, edit the policy. Expand
  **Restrict access or encrypt the content in Microsoft 365 locations**,
  select
  **Block users from receiving email, or accessing shared SharePoint, OneDrive, and Teams files, and Power BI items**,
  and choose whether to block everyone or only people outside your
  organization. Restricting access automatically allows user overrides. At
  the last step, select **Turn it on right away**.

> **Preview** (checked 2026-11-27): Protection policies — [Learn](https://learn.microsoft.com/fabric/governance/protection-policies-create). GA route: none; stretch task.

- **Protection policies.** A protection policy denies access to items with a
  label, except for the users and groups it lists. Someone with at least the
  Information Protection Admin role opens **Protection policies (preview)** in
  the Microsoft Purview portal and selects **New protection policy**. Choose
  Highly Confidential (one label per policy) and the data source
  **Microsoft Fabric**, select **Allow users to retain full control**, and add
  `grp_fabric_prd_fin_admin` and `sg-fabric-workspace-provisioner`. A service
  principal can be added only through a security group, so leave out the
  provisioner group and the SPN loses access to Highly Confidential items.
  The policy covers supported items with the label in every workspace and
  can take up to 24 hours to apply, so try it in a lab tenant.

## MCP tips

- `list_capacities` returns the capacities you can see, with SKU and region.
  Use it to draft `capacities/*.yaml`.
- `get_workspace`, `list_items` and `get_item` check one workspace or item from
  chat. If an answer leaves out `domainId` or `sensitivityLabel`, call the REST
  API.
- No Core MCP tool covers domains, tags, tenant settings, sensitivity labels,
  surge protection or DLP
  ([tool list](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)).
  The scripts call REST, as they would anyway, because they run unattended as
  the SPN. Use the MCP server from chat.
- `search_catalog` (Preview) finds items by name, but it can't confirm a
  workspace's domain. Use Get Workspace or the admin Domains APIs for that.

## Skills tips

- `/onelake-catalog-cli` has audit and remediation modes for data owners and
  admins. Use the audit modes here, and make changes through the manifests.
  Admin audits read tenant-wide APIs, so run them as a Fabric administrator.
  No Fabric API exposes capacity usage or DLP violations, so the Skill can't
  audit them; use the Capacity Metrics app and DLP alerts in Purview.
- For a governance health report on label coverage and domain assignment, run
  `copilot plugin install powerbi-authoring@fabric-collection`. Then build the
  model with `/semantic-model-authoring` and the report with
  `/powerbi-report-cli`.

## Repository files

- [`.github/workflows/validate.yml`](../../.github/workflows/validate.yml) and
  [`.github/workflows/provision.yml`](../../.github/workflows/provision.yml):
  Task 1 runs `apply_domains.py` from them.
- [`scripts/provision.py`](../../scripts/provision.py): Task 4 adds domain
  assignment and makes assignment failures fatal.
- [`scripts/drift.py`](../../scripts/drift.py): Task 6 adds the domain,
  capacity and label checks.
- [`scripts/_fabric.py`](../../scripts/_fabric.py): the API helpers. Task 6
  adds List Domains and the scanner.
- [`.github/workflows/drift.yml`](../../.github/workflows/drift.yml): runs
  `drift.py` nightly and opens the drift issue. No task changes it.
- [`scripts/validate.py`](../../scripts/validate.py): the checks and rules from
  Tasks 1, 2, 3 and 7.
- [`rules/policy.yaml`](../../rules/policy.yaml): `approvedDomains`,
  `approvedCapacities` and `approvedSensitivityLabels`.
- [`.github/CODEOWNERS`](../../.github/CODEOWNERS): Task 7.
- New in this challenge: `domains/`, `capacities/`,
  `schemas/domain.schema.json`, `rules/labels.yaml` and
  `scripts/apply_domains.py`.

## References

- [Fabric domains](https://learn.microsoft.com/fabric/governance/domains)
- [Domains best practices](https://learn.microsoft.com/fabric/governance/domains-best-practices)
- [Domains admin REST API](https://learn.microsoft.com/rest/api/fabric/admin/domains)
- [List Domains](https://learn.microsoft.com/rest/api/fabric/admin/domains/list-domains)
- [Create Domain](https://learn.microsoft.com/rest/api/fabric/admin/domains/create-domain)
- [Update Domain](https://learn.microsoft.com/rest/api/fabric/admin/domains/update-domain)
- [Role Assignments Bulk Assign](https://learn.microsoft.com/rest/api/fabric/admin/domains/role-assignments-bulk-assign)
- [List Role Assignments](https://learn.microsoft.com/rest/api/fabric/admin/domains/list-role-assignments)
- [Role Assignments Bulk Unassign](https://learn.microsoft.com/rest/api/fabric/admin/domains/role-assignments-bulk-unassign)
- [Assign Domain Workspaces By IDs](https://learn.microsoft.com/rest/api/fabric/admin/domains/assign-domain-workspaces-by-ids)
- [Unassign Domain Workspaces By IDs](https://learn.microsoft.com/rest/api/fabric/admin/domains/unassign-domain-workspaces-by-ids)
- [Domain management tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-domain-management-settings)
- [List Domains Tenant Settings Overrides](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-domains-tenant-settings-overrides)
- [Enable item certification](https://learn.microsoft.com/fabric/admin/endorsement-certification-enable)
- [Govern tab](https://learn.microsoft.com/fabric/governance/onelake-catalog-govern)
- [Get Workspace](https://learn.microsoft.com/rest/api/fabric/core/workspaces/get-workspace)
- [List Workspaces (admin)](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces)
- [Surge protection](https://learn.microsoft.com/fabric/enterprise/surge-protection)
- [Get Capacity Surge Protection](https://learn.microsoft.com/rest/api/fabric/core/surge-protection/get-capacity-surge-protection)
- [Update Capacity Surge Protection](https://learn.microsoft.com/rest/api/fabric/core/surge-protection/update-capacity-surge-protection)
- [Domain default sensitivity label (Preview)](https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label)
- [Information protection in Fabric](https://learn.microsoft.com/fabric/governance/information-protection)
- [Information protection tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-information-protection)
- [DLP for Fabric](https://learn.microsoft.com/fabric/governance/data-loss-prevention-configure)
- [Get started with DLP for Fabric and Power BI](https://learn.microsoft.com/purview/dlp-powerbi-get-started)
- [DLP simulation mode](https://learn.microsoft.com/purview/dlp-simulation-mode-learn)
- [Get started with simulation mode](https://learn.microsoft.com/purview/dlp-simulation-mode-get-started)
- [Protection policies](https://learn.microsoft.com/fabric/governance/protection-policies-overview)
- [Create a protection policy](https://learn.microsoft.com/fabric/governance/protection-policies-create)
- [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels)
- [Get Item](https://learn.microsoft.com/rest/api/fabric/core/items/get-item)
- [Get-Label](https://learn.microsoft.com/powershell/module/exchangepowershell/get-label)
- [Metadata scanning](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview)
- [Post Workspace Info (scanner)](https://learn.microsoft.com/rest/api/power-bi/admin/workspace-info-post-workspace-info)
- [Enable service principal access to admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)
- [Core MCP server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Terraform fabric_domain](https://registry.terraform.io/providers/microsoft/fabric/latest/docs/resources/domain)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
