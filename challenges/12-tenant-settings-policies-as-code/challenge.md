# Challenge 12 — Tenant settings and policies as code

> **Outcome:** the tenant settings and capacity overrides your team owns live in YAML. Each PR gets a plan, each merge applies it, a nightly job reports drift, and a Fabric policy blocks an item type the platform hasn't approved.

## Why this challenge exists

[Challenge 00](../00-setup/challenge.md) switches tenant settings on by hand. Many of Fabric's governance decisions live in those settings: who can create items, which identities can call the APIs, who can use Copilot. A portal click gets no review, and nothing notices when an admin changes a setting later.

The tenant settings API is GA, supports service principals and allows 25 requests a minute ([Learn](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-tenant-settings)). Capacity overrides can be written; domain and workspace overrides can only be listed. Terraform has a `fabric_tenant_setting` resource, so settings can be managed like everything else in the repo.

Fabric policies add allow-only rules for item creation, external data sharing and workspace settings editing: once a policy has rules, any action no rule allows is denied. Fabric policies are in Preview and aren't available in West Europe, North Europe or West US, so tenant settings remain the GA control.

## Learning objectives

1. Export tenant settings with their capacity, domain and workspace overrides, and choose which settings the repo owns.
2. Apply settings and capacity overrides from YAML: a plan on every PR and an apply on merge, within the API's rate limit.
3. Report drift nightly, including the overrides the API can only list.
4. Handle the Copilot setting change due on 2026-12-08.
5. Block an item type with a Fabric policy, and know the GA route where policies aren't available.

## Prerequisites

- Challenges [00](../00-setup/challenge.md), [01](../01-workspace-as-code/challenge.md) and [03](../03-domains-capacities-sensitivity/challenge.md) complete.
- A test tenant, or a tenant where your team owns the settings you change. Tenant settings apply to everyone, so in a shared tenant run the apply job in plan-only mode.
- The SPN's group, `sg-fabric-workspace-provisioner`, is enabled in "Service principals can access read-only admin APIs" (to export) and "Service principals can access admin APIs used for updates" (to apply). The SPN isn't a Fabric administrator.
- For Task 6: a capacity used only for this lab, because the active policy applies to every workspace on it. A person on your team is its capacity admin and runs Task 6. The SPN isn't one; to assign a workspace to the capacity, it needs only Contributor permissions on the capacity and Admin on the workspace. Create `sbx-plt-policies` and `sbx-plt-policy-test` on that capacity with manifests, as in challenge 01. `sbx-plt-policies` stores the policy set; Learn recommends a secured, dedicated workspace for that, so only the platform team has a role on it.
- A Fabric administrator has turned on the Policies tenant setting, with the capacity admin included if the setting is limited to security groups: OneLake catalog > Govern > Configurations > Tenant settings, then search for "Policies". Where Govern isn't available, use Settings > Admin portal > Tenant settings.
- Fabric policies aren't available in West Europe, North Europe or West US. The sample capacity `contosononprodf2` is in North Europe; if your lab capacity is in one of those regions, do Task 7 instead of Task 6.

## Tasks

### Task 1 — Export

No MCP tool covers tenant settings or the admin APIs, so Tasks 1 to 4 call REST. Write `scripts/export_tenant_settings.py` and reuse `scripts/_fabric.py` for tokens and retries. It calls:

```text
GET https://api.fabric.microsoft.com/v1/admin/tenantsettings
GET https://api.fabric.microsoft.com/v1/admin/capacities/delegatedTenantSettingOverrides
GET https://api.fabric.microsoft.com/v1/admin/domains/delegatedTenantSettingOverrides
GET https://api.fabric.microsoft.com/v1/admin/workspaces/delegatedTenantSettingOverrides
```

Follow the continuation token on each list and save the result to `tenant/export/<YYYY-MM-DD>.json`. [Challenge 00](../00-setup/challenge.md) saves its baseline to the same folder in the same shape, so your first comparison is like for like. Each setting has a `settingName` for the API, a `title` as the portal shows it, `enabled`, `enabledSecurityGroups` and delegation flags. Stop on 401 or 403 with a clear error, and never read either as "not found".

Choose 8 to 10 settings your team owns, including the service principal settings from challenge 00. To check what a setting does, ask the Core MCP (`get_knowledge`) or the local MCP's `docs_*` tools:

> What does the tenant setting "Service principals can access admin APIs used for updates" allow, and who should be in its security group?

### Task 2 — Settings as YAML

Save this as `tenant/settings.yaml`:

```yaml
settings:
  - title: Service principals can call Fabric public APIs
    enabled: true
    enabledSecurityGroups: [sg-fabric-workspace-provisioner]
    owner: plt
  - title: Make Microsoft Copilot available in Power BI and Fabric
    enabled: true
    owner: plt
    justification: Approved for all users; see the decision record.
    decision: docs/decisions/copilot.md
```

`tenant/capacities/<capacity>.yaml` has the same shape plus a `capacity` key, for the settings the tenant delegates to capacity admins. A setting is delegated through domains or capacities, not both. The scripts resolve titles to API setting names from the latest export, and group names to object IDs from the export or Microsoft Graph. The Graph lookup needs the `GroupMember.Read.All` or `Group.Read.All` application permission.

Add `schemas/tenant-settings.schema.json` and these rules:

- Every setting has an `owner`.
- A setting turned on for the whole organization, with no `enabledSecurityGroups`, needs a `justification`.
- Every title exists in the latest export, so retired settings leave the file.

Declare the rules in `rules/policy.yaml` and implement them in `scripts/validate.py`. Then copy `rules/policy.yaml` to `api/policy.yaml` so the two stay identical.

**Deliberate failure:** open a PR that turns a setting on for the whole organization without a `justification`. It must fail.

### Task 3 — Plan on PR, apply on merge

Write `scripts/apply_tenant_settings.py`. On a PR, it compares the YAML with a fresh export and posts the changes as a comment. On merge, it calls:

```text
POST https://api.fabric.microsoft.com/v1/admin/tenantsettings/{tenantSettingName}/update
POST https://api.fabric.microsoft.com/v1/admin/capacities/{capacityId}/delegatedTenantSettingOverrides/{tenantSettingName}/update
DELETE https://api.fabric.microsoft.com/v1/admin/capacities/{capacityId}/delegatedTenantSettingOverrides/{tenantSettingName}
```

The update body sets `enabled` and lists `enabledSecurityGroups` as `graphId` and `name` pairs. The script never writes domain or workspace overrides, because the API can only list them. Keep to 25 requests a minute and back off on 429; `_fabric.py` already honors `Retry-After`. A tenant setting change can take up to 15 minutes to reach everyone ([Learn](https://learn.microsoft.com/fabric/admin/about-tenant-settings)). Add a plan-only switch for shared tenants.

The job can remove its own access. If a change takes the SPN's group out of one of its own settings, the next call returns 403. Plan-only shows that change in the PR before anyone merges it.

Add `.github/workflows/tenant-settings.yml`: it runs the plan on PRs that change `tenant/` and the apply on merge, with the same OIDC login as `provision.yml`. The PR job needs `pull-requests: write` to post its comment.

### Task 4 — Nightly drift

Extend `scripts/drift.py` to run the export every night and compare it with the YAML. Open a `drift/tenant-settings` issue with the differences, and list every domain and workspace override in it so a person reviews them. Create the label in your repo first.

To test it, change one of your settings in OneLake catalog > Govern > Configurations > Tenant settings; where Govern isn't available, for example with tenant Private Link, use Settings > Admin portal > Tenant settings. The next nightly run opens the issue.

### Task 5 — The Copilot change

> **Preview** (checked 2026-11-27): Microsoft Copilot in Power BI and Fabric — [Learn](https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric). GA route: record both settings as the export shows them on the day you run the task.

On 2026-12-08 the standalone Power BI Copilot setting turns off by default, and "Make Microsoft Copilot available in Power BI and Fabric" turns on by default. Admins can turn the standalone setting back on until standalone Power BI Copilot and App Copilot retire on 2027-01-15; turning it on doesn't extend that date. Copilot in the report pane isn't part of the change.

1. Find both settings in the export. Learn words the standalone setting's title two ways, so take the exact title from the export. Record the decision in `tenant/settings.yaml` and a short `docs/decisions/copilot.md` (what, who, when).
2. Record the Microsoft 365 side: unless a Microsoft 365 admin enables "Fabric data available in Microsoft Copilot", Copilot can't use Fabric data, and that setting isn't in the Fabric export. If standalone Copilot is restricted to approved items, Microsoft Copilot honors that during the preview, so include that setting in the decision.
3. Before 2026-12-08, compare the decision with the new defaults and prepare the PR where they differ. After that date, confirm the export and check the nightly drift report.

### Task 6 — Block an item type with a Fabric policy

> **Preview** (checked 2026-11-27): Fabric policies and the policy set APIs — [Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-overview). GA route: Task 7.

Run this task as the capacity admin. The Policies tenant setting lets Fabric administrators and capacity admins create policy sets, and a capacity admin activates a capacity-scoped set.

Fabric policies allow only what a rule lists. An item creation rule allows the operations it matches, and once a policy has rules, every other item creation is blocked. A capacity has one active policy set at a time, and changes take up to 15 minutes to apply.

Plan the set with the skill. In a Copilot CLI session:

```text
/fabric-policies-cli
```

Ask for a capacity-scoped item creation policy set for the lab capacity, stored in `sbx-plt-policies`, that allows the item types the lab uses and leaves out SQL database. Leave activation out of the plan. The workspace that stores a set isn't the scope it enforces, and a set's scope can't change after it's created. Learn disagrees on how sets are created: the get-started guide says only the workspace's New item > Policy set flow can create one, while the REST reference documents Create Policy Set. Let the skill discover the route that works, and don't hard-code one page's call.

Keep the definition in Git so the PR reviews it. Save this as `policies/lab-item-creation/policySet.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/policySet/definition/1.0.0/schema.json",
  "properties": {
    "scope": { "type": "Capacity" }
  },
  "policyRules": [
    {
      "displayName": "Approved lab item types",
      "policy": "ItemCreation",
      "conditions": [
        {
          "type": "Dynamic",
          "targetProperty": "item.type",
          "predicate": {
            "operator": "AnyOf",
            "values": ["Lakehouse", "Notebook", "DataPipeline", "SemanticModel", "Report"]
          }
        }
      ],
      "effects": [{ "type": "Allow" }]
    }
  ]
}
```

The file follows the [policy set definition schema](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/policyset-definition). Rule values are API item types, not portal names: a pipeline is `DataPipeline`. A condition matches any of its values (up to 50), every condition in a rule must match, and an action goes through if any rule allows it. Learn's pages show a rule's effect in different shapes, so let the skill build each API call from this file.

Paste the skill's plan into the PR. After the PR merges, approve the plan so the skill creates the set and adds the rule; it leaves the set inactive. If the API can't create the set, create it in `sbx-plt-policies` from New item > Policy set, with the scope set to your lab capacity, then let the skill add the rule. Ask it to read the rules back and check them against the file.

Git can't activate a policy set ([Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-rest-api)). Activate it yourself, as the capacity admin: open the set in `sbx-plt-policies` and select Activate, or call the capacity [Activate Policy Set API](https://learn.microsoft.com/rest/api/fabric/policyset/activation/activate). The SPN can't, because it isn't a capacity admin. A capacity has one active set, so activating yours can replace one that's already active; check the Policies Center (OneLake catalog > Govern) first. Your set appears there once it's active. Record in the PR who activated the set and when.

After 15 minutes, ask the Core MCP:

> Create a SQL database called sqldb_blocked and a lakehouse called lh_allowed in sbx-plt-policy-test.

The SQL database must fail and the lakehouse must succeed. Save both responses in the PR. Fabric audit logs also record each policy decision. If the lakehouse fails too, check the audit log for the denied operation before you change the rule.

### Task 7 — GA route without Fabric policies

Do this task only if Task 6 can't run, for example on a capacity in North Europe. It uses GA features only.

Override "Users can create Fabric items" on the lab capacity so only `sg-fabric-creators` can create items there; the setting is delegated to capacity admins automatically. Save this as `tenant/capacities/contosononprodf2.yaml`:

```yaml
capacity: contosononprodf2
settings:
  - title: Users can create Fabric items
    enabled: true
    enabledSecurityGroups: [sg-fabric-creators]
    owner: plt
```

Use your lab capacity's name in the file name and the `capacity` key. The apply job from Task 3 writes it as a capacity override. In the portal, it's at OneLake catalog > Govern > Capacities > your capacity > More options > Settings > Delegated tenant settings > Microsoft Fabric > Users can create Fabric items. Where Govern isn't available, use Settings > Admin portal > Capacity settings > Fabric capacity > your capacity > Delegated tenant settings.

The override controls who creates items, not which types, so add two checks:

- Add `blockedItemTypes: [SQLDatabase]` to `rules/policy.yaml`, copy the file to `api/policy.yaml` so the two stay identical, and make `scripts/validate.py` fail a PR that adds an item whose `.platform` file has a blocked `metadata.type`, such as `"type": "SQLDatabase"`.
- Add a nightly inventory to `scripts/drift.py`: list the workspaces on the lab capacity, call List Items with `type=SQLDatabase` on each, and open a `drift/item-types` issue for any result. List Items is GA, needs Viewer on the workspace and supports service principals, so it covers the workspaces where the SPN has a role.

```text
GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items?type=SQLDatabase
```

> **Preview** (checked 2026-11-27): Admin List Items API, which the `onelake-catalog-cli` admin-audit inventory calls — [Learn](https://learn.microsoft.com/rest/api/fabric/admin/items/list-items). GA route: the per-workspace inventory above.

For a tenant-wide view, if you're a Fabric administrator, run the skill in admin-audit mode. In a Copilot CLI session:

```text
/onelake-catalog-cli
```

Ask for every SQL database on the lab capacity. Admin-audit is read-only. Items in deleted workspaces can still show as Active, so join on the workspace ID.

## Success criteria

- [ ] A merged `tenant/settings.yaml` change updates the setting with no portal clicks, or posts a plan in plan-only mode.
- [ ] A portal change opens a `drift/tenant-settings` issue the next night, and the issue lists domain and workspace overrides.
- [ ] The SQL database request fails and the lakehouse request succeeds, or the Task 7 checks catch the SQL database.
- [ ] The Task 2 PR fails validation.

## Stretch goals

- **Terraform.** Manage the same settings with `fabric_tenant_setting` and compare `terraform plan` with the drift report.

> **Preview** (checked 2026-11-27): Policy Evaluation API — [Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-rest-api). GA route: none; stretch task.

- **Policy evaluation.** The REST article lists a Policy Evaluation API that the REST reference doesn't include yet. If your tenant has it, evaluate the blocked creation in the PR before activation.

## MCP tips

- The Core MCP has no tenant settings, admin or policy tools. Here it runs the negative test with `create_item` and answers questions with `get_knowledge`.
- `create_item` calls the Create Item API, so the test shows the error an API caller gets.
- The local MCP's `docs_list-item-types` checks the item type names in the policy rule. Start it with `npx -y @microsoft/fabric-mcp@latest server start --mode all`.

## Skills tips

- `fabric-policies-cli` makes no change until you approve its plan, so the plan can go in the PR. It creates the set inactive, adds the rules, reads them back and checks the active scope before any activation. One approval can include activation, so leave activation out of the plan and to the capacity admin (Task 6).
- `onelake-catalog-cli` admin-audit mode is read-only. Its item inventory lists items by type across the tenant.
- If the skills aren't installed, run these from a terminal:

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

## Repository files

This challenge reuses `scripts/_fabric.py` and extends these files in the repo root:

- `scripts/validate.py`, `scripts/drift.py`
- `rules/policy.yaml` and its copy `api/policy.yaml`
- `.github/workflows/drift.yml`

It adds:

- `tenant/settings.yaml`, `tenant/capacities/<capacity>.yaml` and the exports in `tenant/export/`
- `policies/lab-item-creation/policySet.json`
- `schemas/tenant-settings.schema.json`
- `scripts/export_tenant_settings.py`, `scripts/apply_tenant_settings.py`
- `.github/workflows/tenant-settings.yml`
- `docs/decisions/copilot.md`

## References

- [List Tenant Settings REST API](https://learn.microsoft.com/rest/api/fabric/admin/tenants/list-tenant-settings)
- [Update Tenant Setting REST API](https://learn.microsoft.com/rest/api/fabric/admin/tenants/update-tenant-setting)
- [Update Capacity Tenant Setting Override REST API](https://learn.microsoft.com/rest/api/fabric/admin/tenants/update-capacity-tenant-setting-override)
- [Tenant settings index](https://learn.microsoft.com/fabric/admin/tenant-settings-index)
- [Users can create Fabric items](https://learn.microsoft.com/fabric/admin/fabric-switch)
- [Capacity settings](https://learn.microsoft.com/fabric/admin/capacity-settings)
- [Fabric policies](https://learn.microsoft.com/fabric/governance/fabric-policies-overview)
- [Get started with Fabric policies](https://learn.microsoft.com/fabric/governance/fabric-policies-get-started)
- [Item creation policies](https://learn.microsoft.com/fabric/governance/fabric-policies-item-creation)
- [Fabric policies REST APIs](https://learn.microsoft.com/fabric/governance/fabric-policies-rest-api)
- [Policy set definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/policyset-definition)
- [Activate Policy Set REST API](https://learn.microsoft.com/rest/api/fabric/policyset/activation/activate)
- [Microsoft Copilot in Power BI and Fabric](https://learn.microsoft.com/fabric/iq/connectors/copilot-power-bi-fabric)
- [Copilot tenant settings](https://learn.microsoft.com/fabric/admin/service-admin-portal-copilot)
- [List Items REST API](https://learn.microsoft.com/rest/api/fabric/core/items/list-items)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Terraform provider for Fabric](https://registry.terraform.io/providers/microsoft/fabric/latest/docs)
- [`fabric-policies-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/fabric-policies-cli)
- [`onelake-catalog-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/onelake-catalog-cli)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
