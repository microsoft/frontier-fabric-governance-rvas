# Challenge 03 — Domains, capacities and sensitivity labels

> **Outcome:** every workspace sits in the subdomain and on the capacity its
> manifest declares, and only a PR changes either. Its items carry at least the
> label the manifest declares, applied by a domain default label or by people
> with label rights, and a nightly scan proves it.

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

## Learning objectives

1. Declare domains, subdomains and capacities as code (`domains/*.yaml`,
   `capacities/*.yaml`), and create the domains from the manifests.
2. Validate placement before merge, with production rules keyed on the
   `environment` field.
3. Assign each workspace to its subdomain when the provisioner creates it.
4. Label items through the supported routes, and prove coverage with the
   metadata scanner.
5. Detect domain, capacity and label drift nightly, and flag label downgrades
   in the PR.
6. Check placement from chat with the Fabric Core MCP, and audit domains and
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
  their label publishing policy. Task 5's label steps need this person.
- Two capacities that match `approvedCapacities` in `rules/policy.yaml`:
  `contosononprodf2` for sbx, dev and stg, and `contosoprodf4` for prd. In a
  lab, both entries can point to the same capacity.
- Sensitivity labels published in Microsoft Purview, at least Public, General,
  Confidential and Highly Confidential, and a compliance admin who can run
  `Get-Label` in Security & Compliance PowerShell.
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

5. Print a map from each manifest name to its domain ID.

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

Last, restrict who can add workspaces to each domain. By default the whole
organization is a domain contributor, so any workspace Admin can move a
workspace into the domain. In the admin portal's **Domains** page, open each
domain's settings, select **Contributors** and limit them to tenant and domain
admins. The provisioner in Task 4 uses the admin assign API, which doesn't
depend on this setting.

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
`capacities/` disagree on any field. If you change `rules/policy.yaml`, copy it
to `api/policy.yaml`; the two files must stay identical.

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

## Success criteria

- [ ] `domains/` and `capacities/` validate and match `approvedDomains` and
      `approvedCapacities`, and a second `apply_domains.py --dry-run` plans no
      changes.
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
- [ ] The SPN isn't a Fabric administrator or a capacity admin and is in no
      label publishing policy. People with those rights run the label steps.

## Stretch goals

- **Capacity scale as code.** Add `desiredSku` to the capacity manifests and
  reconcile it through Azure Resource Manager (`Microsoft.Fabric/capacities`).
  Use a separate Azure identity with Contributor on the capacity resource, not
  the Fabric SPN, and make a change above F8 need CODEOWNERS approval.

## MCP tips

- `list_capacities` returns the capacities you can see, with SKU and region.
  Use it to draft `capacities/*.yaml`.
- `get_workspace`, `list_items` and `get_item` check one workspace or item from
  chat. If an answer leaves out `domainId` or `sensitivityLabel`, call the REST
  API.
- No Core MCP tool covers domains, tags, tenant settings or sensitivity labels.
  The scripts call REST for those, and they'd call REST anyway, because they run
  unattended as the SPN. Use the MCP server from chat.
- `search_catalog` (Preview) finds items by name, but it can't confirm a
  workspace's domain. Use Get Workspace or the admin Domains APIs for that.

## Skills tips

- `/onelake-catalog-cli` has audit and remediation modes for data owners and
  admins. Use the audit modes here, and make changes through the manifests.
  Admin audits read tenant-wide APIs, so run them as a Fabric administrator.
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
- [Domains admin REST API](https://learn.microsoft.com/rest/api/fabric/admin/domains)
- [List Domains](https://learn.microsoft.com/rest/api/fabric/admin/domains/list-domains)
- [Create Domain](https://learn.microsoft.com/rest/api/fabric/admin/domains/create-domain)
- [Update Domain](https://learn.microsoft.com/rest/api/fabric/admin/domains/update-domain)
- [Role Assignments Bulk Assign](https://learn.microsoft.com/rest/api/fabric/admin/domains/role-assignments-bulk-assign)
- [Assign Domain Workspaces By IDs](https://learn.microsoft.com/rest/api/fabric/admin/domains/assign-domain-workspaces-by-ids)
- [Unassign Domain Workspaces By IDs](https://learn.microsoft.com/rest/api/fabric/admin/domains/unassign-domain-workspaces-by-ids)
- [Domain management tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-domain-management-settings)
- [Get Workspace](https://learn.microsoft.com/rest/api/fabric/core/workspaces/get-workspace)
- [List Workspaces (admin)](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces)
- [Domain default sensitivity label (Preview)](https://learn.microsoft.com/fabric/governance/domain-default-sensitivity-label)
- [Information protection in Fabric](https://learn.microsoft.com/fabric/governance/information-protection)
- [Information protection tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-information-protection)
- [Bulk Set Labels](https://learn.microsoft.com/rest/api/fabric/admin/labels/bulk-set-labels)
- [Get Item](https://learn.microsoft.com/rest/api/fabric/core/items/get-item)
- [Get-Label](https://learn.microsoft.com/powershell/module/exchangepowershell/get-label)
- [Metadata scanning](https://learn.microsoft.com/fabric/governance/metadata-scanning-overview)
- [Post Workspace Info (scanner)](https://learn.microsoft.com/rest/api/power-bi/admin/workspace-info-post-workspace-info)
- [Enable service principal access to admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)
- [Core MCP server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
