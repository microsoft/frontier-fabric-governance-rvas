# Challenge 11 — Network exfiltration guardrails

> **Outcome:** a lab workspace sends data only to approved destinations and accepts traffic only from approved networks. Each control is set from a PR, and a control counts only when an attempt that should fail does fail.

## Why this challenge exists

[Challenge 04](../04-access-rbac-lifecycle/challenge.md) and [challenge 10](../10-onelake-security-as-code/challenge.md) decide who can read data. Network controls decide where that data can go. A reader who can run a notebook can copy a table to any storage account unless the workspace blocks the destination.

Three facts shape the design:

- Outbound access protection works only on F SKU capacities, not trials, and it doesn't work with external data sharing ([Learn](https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview)).
- The call that sets a workspace's network policy replaces the whole policy, and a `defaultAction` left out of the body becomes `Allow` ([Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/set-network-communication-policy)). A pipeline must send the full policy every time.
- Tenant-level Private Link with Block Public Internet Access protects every workspace, and it also turns off Govern in the OneLake catalog, the Capacity Metrics app, cross-tenant shortcuts and OneLake data sharing for the whole tenant ([Learn](https://learn.microsoft.com/fabric/security/security-private-links-overview)). That's a design decision for the tenant, not a lab step.

## Learning objectives

1. Model a workspace's inbound and outbound network policy as code (`network/<workspace>.yaml`).
2. Apply it with the network communication policy API, always sending the full policy.
3. Prove outbound access protection with copies and shortcuts that must fail, and allow one destination through a managed private endpoint.
4. Audit network policies and external data shares across the tenant with the admin APIs.
5. Decide when tenant-level Private Link is worth what it turns off.

## Prerequisites

- Challenges [00](../00-setup/challenge.md) and [01](../01-workspace-as-code/challenge.md) complete.
- An F SKU capacity, `contosononprodf2`, in a region where Fabric Data Engineering is available. A trial capacity won't work.
- Two workspaces on that capacity, `sbx-sec-net-protected` and `sbx-sec-net-open`, created from manifests in `workspaces/` as in challenge 01. Each holds a notebook and a lakehouse named `lh_net` with the file `Files/landing/sample.csv`. Use lab workspaces, never production: these controls apply to every user of the workspace.
- You and the SPN are Admins of both workspaces, because network rules and managed private endpoints need the Admin role.
- You've re-registered `Microsoft.Network` on your Azure subscription, as the outbound access protection overview asks: "Ensure you re-register the Microsoft.Network feature on your subscription in the Azure portal."
- Two ADLS Gen2 storage accounts: `stcontosoapproved`, where you can approve private endpoint connections, and `stcontosoother`. You have Storage Blob Data Reader on `stcontosoapproved` and Storage Blob Data Contributor on `stcontosoother`. With those roles the writes from the open workspace succeed, so a failure in the protected workspace comes from the network rule.
- Three tenant settings in the Advanced networking section are on: "Configure workspace-level outbound network rules", "Configure workspace-level inbound network rules" and "Configure workspace-level IP firewall rules and trusted resource instances". The inbound setting is off by default and can take up to 15 minutes to apply. The settings are at OneLake catalog > Govern > Configurations > Tenant settings > Advanced networking; where Govern isn't available, use Settings > Admin portal > Tenant settings.
- For Task 6, the tenant setting "External data sharing", in the Export and sharing settings section, is on for you. Then a refused share proves that the workspace blocked it, not the tenant.
- Through `sg-fabric-workspace-provisioner`, the SPN is allowed by the tenant setting "Service principals can access read-only admin APIs", in the Admin API settings section. It's never a Fabric admin.

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

## Tasks

### Task 1 — Network policy as code

Save this as `network/sbx-sec-net-protected.yaml`:

```yaml
workspace: sbx-sec-net-protected
inbound:
  defaultAction: Allow
outbound:
  defaultAction: Deny
  managedPrivateEndpoints:
    - name: mpe-stcontosoapproved
      targetResourceId: /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/stcontosoapproved
      subresource: dfs
```

Save `network/sbx-sec-net-open.yaml` the same way, with `Allow` in both directions and no endpoints. It's the control group for Task 3.

Add `schemas/network.schema.json` for these files. The validator checks that:

- `inbound.defaultAction` and `outbound.defaultAction` are both present, and each is `Allow` or `Deny`;
- the workspace has a manifest in `workspaces/`;
- a workspace whose `workspaces/` manifest has `environment: prd` has `outbound.defaultAction: Deny`;
- each managed private endpoint has a `name`, a `targetResourceId` and a `subresource`.

Declare these rules in `rules/policy.yaml` and implement them in `scripts/validate.py`. Then copy `rules/policy.yaml` to `api/policy.yaml` so the two stay identical.

Extend `changed_workspace_files()` in `validate.py` to return changed `network/*.yaml` files, and add `network/*.yaml` to the `paths` of `.github/workflows/validate.yml`.

Add this line to `.github/CODEOWNERS`, so the security team approves every network change:

```text
/network/ @your-org/fabric-security
```

**Deliberate failure:** open a PR that deletes `defaultAction` from the `outbound` block of `network/sbx-sec-net-protected.yaml`. It must fail, because the API would turn the missing value into `Allow`.

### Task 2 — Apply the policy

No MCP tool covers network rules, so this task calls the REST APIs. Write `scripts/apply_network.py` and reuse `scripts/_fabric.py` for tokens and retries:

1. Resolve the workspace ID from the manifest.
2. Read the live policy and its `ETag` header, and list the workspace's managed private endpoints.
3. Build the policy body from the manifest, with both directions every time.
4. Write the differences to `network-report.md`: policy changes, endpoints to create, and endpoints that exist but aren't in the manifest, so a reviewer decides whether to delete them.
5. On a PR, stop there. On a push to `main`, send the policy with `If-Match` set to the ETag from step 2, then create the missing endpoints.

```text
GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/networking/communicationPolicy
PUT https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/networking/communicationPolicy
GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/managedPrivateEndpoints
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/managedPrivateEndpoints
```

The policy body for `sbx-sec-net-protected`:

```json
{
  "inbound": {
    "publicAccessRules": {
      "defaultAction": "Allow"
    }
  },
  "outbound": {
    "publicAccessRules": {
      "defaultAction": "Deny"
    }
  }
}
```

Setting the policy needs the Admin role on the workspace and allows 200 requests a minute, so back off on HTTP 429; `_fabric.py` already honors `Retry-After`. Stop on 401 or 403 with a clear error and exit 3, and never read either as "not found". If the write fails because the ETag changed, someone edited the policy after your read: stop with a clear error and rerun the workflow. You can't turn on outbound access protection while the workspace holds an item type it doesn't support, so keep the lab workspace to a lakehouse and a notebook.

`_fabric._request` has no headers argument unless you added one in challenge 10. Add `headers: dict | None = None` and merge it into the request headers, so the script can send `If-Match`.

The endpoint body:

```json
{
  "name": "mpe-stcontosoapproved",
  "targetPrivateLinkResourceId": "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/stcontosoapproved",
  "targetSubresourceType": "dfs",
  "requestMessage": "Fabric workspace sbx-sec-net-protected, from network/sbx-sec-net-protected.yaml"
}
```

Creating an endpoint needs the Admin role and allows 50 requests a minute, and the call returns 201. The endpoint then waits for the storage account's owner, who approves it in the Azure portal under the storage account's Networking > Private endpoint connections. Approve it before Task 3.

Save this as `.github/workflows/network.yml`:

```yaml
name: network
on:
  pull_request:
    paths: ["network/*.yaml"]
  push:
    branches: [main]
    paths: ["network/*.yaml"]
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
  pull-requests: write
concurrency:
  group: network
  cancel-in-progress: false
jobs:
  network:
    runs-on: [self-hosted, fabric-gov]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - name: Python
        run: |
          python3 -m venv .venv
          .venv/bin/pip install --quiet --upgrade pip
          .venv/bin/pip install --quiet -r scripts/requirements.txt
          echo "$GITHUB_WORKSPACE/.venv/bin" >> $GITHUB_PATH
      - uses: azure/login@7ddb5af1ef8758cf1353cf3b42f940aee27ba21c # v3.0.2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          allow-no-subscriptions: true
      - name: Plan or apply
        env:
          MODE: ${{ github.event_name == 'pull_request' && 'plan' || 'apply' }}
        run: python scripts/apply_network.py --mode "$MODE"
      - name: Comment the plan
        if: github.event_name == 'pull_request'
        uses: marocchino/sticky-pull-request-comment@5770ad5eb8f42dd2c4f34da00c94c5381e49af88 # v3.0.5
        with:
          header: network
          path: network-report.md
```

### Task 3 — Prove outbound protection

Run the same notebook in both workspaces. Each attempt must match its cell:

| Attempt | `sbx-sec-net-open` | `sbx-sec-net-protected` |
| --- | --- | --- |
| Write `sample.csv` to `stcontosoother` | Succeeds | Fails |
| Read a file from `stcontosoapproved` | Succeeds | Succeeds, through `mpe-stcontosoapproved` |
| Create a shortcut in `lh_net` to a container in `stcontosoother` | Succeeds | Fails |

The first cell copies the sample file out:

```python
src = "abfss://<workspace-id>@onelake.dfs.fabric.microsoft.com/<lakehouse-id>/Files/landing/sample.csv"
df = spark.read.option("header", True).csv(src)
df.write.mode("overwrite").option("header", True).csv("abfss://<container>@stcontosoother.dfs.core.windows.net/exfil-test/")
```

The second cell reads from the approved account, so a failed write doesn't stop the read:

```python
spark.read.option("header", True).csv("abfss://<container>@stcontosoapproved.dfs.core.windows.net/reference/sample.csv").show(5)
```

Replace `<workspace-id>` with the workspace's ID and `<lakehouse-id>` with the ID of `lh_net` in that workspace, and `<container>` with a container in each storage account. Under outbound access protection, OneLake paths use IDs, not names.

Use the `spark-cli` skill to run the notebook and return the full error text. In a Copilot CLI session:

```text
/spark-cli
```

Then ask:

> Run the notebook in sbx-sec-net-open, then the one in sbx-sec-net-protected, and show me every error in full.

Create the shortcuts from each lakehouse in the portal, with New shortcut > Azure Data Lake Storage Gen2. Outbound access protection covers OneLake shortcuts too ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-manage-outbound-access)).

Expect two side effects in the protected workspace. Sessions take about 3–5 minutes to start, because outbound access protection turns off starter pools, and `pip install` from PyPI fails.

Save each error, with the time and the workspace, in `network/evidence/<date>/`. A Fails cell counts only when its error is saved.

### Task 4 — Diagnostics in the same workspace

Ask the Core MCP:

> Show the OneLake diagnostics settings for sbx-sec-net-protected, then turn diagnostics on and send the events to lh_net in the same workspace.

`onelake_get_settings` reads the settings, and `onelake_modify_diagnostics` changes them, which needs the Admin role on the workspace. Under outbound access protection, the lakehouse that receives the events must be in the same workspace.

Rerun the Task 3 notebook after you turn diagnostics on. The event for its read of `Files/landing/sample.csv` reaches `lh_net` in about an hour. Add it to the evidence folder.

### Task 5 — Inbound rules

> **Preview** (checked 2026-11-27): Set Firewall Rules API — [Learn](https://learn.microsoft.com/rest/api/fabric/core/workspaces/set-firewall-rules). GA route: set the rules in the portal under Workspace settings > Inbound networking.

Restrict inbound traffic to your network. Change the `inbound` block of `network/sbx-sec-net-protected.yaml`, and replace `203.0.113.10`, an address reserved for documentation, with your public IP:

```yaml
inbound:
  defaultAction: Deny
  firewallRules:
    - displayName: corpip
      value: 203.0.113.10
```

Add a rule to `rules/policy.yaml`, its copy `api/policy.yaml` and `validate.py`: a manifest with `firewallRules` has `inbound.defaultAction: Deny` and at most 256 rules. Then extend `apply_network.py` to send the list too:

```text
PUT https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/networking/communicationPolicy/inbound/firewall
```

```json
{
  "rules": [
    {
      "displayName": "corpip",
      "value": "203.0.113.10"
    }
  ]
}
```

The call replaces the whole list, and the rules apply only while inbound is `Deny`. They cover inbound traffic only, and they don't support Azure Databricks Unity Catalog mirrored items, OneLake security, or Power BI and Copilot experiences ([Learn](https://learn.microsoft.com/fabric/security/security-workspace-level-firewall-overview)).

Check that your IP is in the list before you merge. If a bad rule locks you out, Learn's advice is to fix it through the API: "In case a workspace is inaccessible due to misconfiguration of IP rules, use the API to update IP firewall rules."

Check whether inbound `Deny` also blocks the pipeline's own calls from the self-hosted runner. If the next run fails with 403, add the runner's public IP to the list, or set the rules in the portal and keep the manifest as the record.

Test the rule. Save this as `scripts/onelake_read_test.py`:

```python
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

service = DataLakeServiceClient("https://onelake.dfs.fabric.microsoft.com", credential=DefaultAzureCredential())
workspace = service.get_file_system_client("sbx-sec-net-protected")
data = workspace.get_file_client("lh_net.Lakehouse/Files/landing/sample.csv").download_file().readall()
print(f"Read {len(data)} bytes")
```

Run it from your machine, then upload it to Azure Cloud Shell, a network that isn't on the list, and run it there ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-access-python)). In both places, run these from the folder that holds the script:

```bash
python3 -m venv ~/onelake-test
~/onelake-test/bin/pip install --quiet azure-identity azure-storage-file-datalake
~/onelake-test/bin/python onelake_read_test.py
```

The read from your machine must succeed and the read from Cloud Shell must fail. Save both results in the evidence folder.

### Task 6 — Tenant audits

Anyone with the Admin role on a workspace can change its network policy or share its data between merges. Two nightly audits cover the tenant.

Add a check to `scripts/drift.py` that lists every workspace's network policy with the admin API. The call works with read-only admin API access and pages with `continuationUri`:

```text
GET https://api.fabric.microsoft.com/v1/admin/workspaces/networking/communicationpolicies
```

Report a workspace whose default actions differ from its manifest in `network/`, and any workspace whose `workspaces/` manifest has `environment: prd` while its outbound default is `Allow`, whether or not it has a network manifest. The findings join the nightly drift issue, and `drift.py` keeps exiting 2 on drift and 3 on 401 or 403. A separate `drift/network` issue needs a change to `.github/workflows/drift.yml`: have `drift.py` also write these findings to `drift-network.md`, create the `drift/network` label, and add this step after the step that opens the drift issue:

```yaml
- name: Open network drift issue
  if: steps.drift.outputs.rc == '2' && hashFiles('drift-network.md') != ''
  uses: peter-evans/create-issue-from-file@fca9117c27cdc29c6c4db3b86c48e4115a786710 # v6.0.0
  with:
    title: Workspace network policy drift
    content-filepath: drift-network.md
    labels: drift, governance, drift/network
```

External data shares need more than read-only admin access. Learn sets a condition on the admin call that lists them: "To use this API, enable the External data sharing admin switch for the calling principal." For the SPN, that means adding `sg-fabric-workspace-provisioner` to the "External data sharing" tenant setting. That setting also decides who can create shares, so the SPN could then create them in its workspaces. Decide who runs the audit, the SPN every night or a Fabric admin on demand, and record the decision in Task 7. If you choose the SPN, check that the call accepts a service principal before you schedule it.

Write `scripts/audit_external_shares.py`. It lists the shares, a call that allows 10 requests a minute, and compares them with `network/external-shares.yaml`:

```text
GET https://api.fabric.microsoft.com/v1/admin/items/externalDataShares
```

Start that file with an empty list, `shares: []`. Each entry you add later names the workspace, item, paths and recipient of one approved share. It isn't a workspace manifest, so `validate.py`, `apply_network.py` and the drift check skip it. The script writes any share that isn't on the list to `drift-external-share.md` and exits 2. It exits 3 on 401 or 403, and 0 when every share is approved.

Keep it out of `drift.py`, so a 403 from this call doesn't hide the network findings. If the SPN runs the audit, create the `drift/external-share` label and add these steps to `.github/workflows/drift.yml` after the network drift step:

```yaml
- name: Audit external data shares
  id: shares
  run: |
    set +e
    python scripts/audit_external_shares.py
    rc=$?
    echo "rc=$rc" >> "$GITHUB_OUTPUT"
    if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then exit "$rc"; fi
- name: Open external share issue
  if: steps.shares.outputs.rc == '2'
  uses: peter-evans/create-issue-from-file@fca9117c27cdc29c6c4db3b86c48e4115a786710 # v6.0.0
  with:
    title: External data shares not in Git
    content-filepath: drift-external-share.md
    labels: drift, governance, drift/external-share
```

Last, try to share `Files/landing` from both workspaces. Save this as `share.json`:

```json
{
  "paths": ["Files/landing"],
  "recipient": {
    "userPrincipalName": "partner@fabrikam.com"
  }
}
```

Send it as yourself with the Azure CLI, once per workspace:

```bash
az rest --method post --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces/<workspace-id>/items/<lakehouse-id>/externalDataShares" --body @share.json
```

In `sbx-sec-net-open` the call returns 201. That share isn't in `network/external-shares.yaml`, so the next audit must report it; once it has, revoke the share. In `sbx-sec-net-protected` the call must be refused, and the refusal goes in the evidence folder. If it returns 201 there, the workspace isn't protected: record a finding and revoke the share.

### Task 7 — Decide on tenant-level Private Link

Tenant-level Private Link with Block Public Internet Access protects every workspace at once and turns features off for everyone. Don't turn it on in a shared tenant. Write the decision record instead: save this as `docs/network-design.md` in your repo and fill it in.

```markdown
# Network design

## Context

## What tenant Private Link with Block Public Internet Access protects

## What it turns off

## Affected challenges

## Trade-offs

| Control | Scope | Limits |
| --- | --- | --- |
| Outbound access protection | Workspace, outbound | F SKU only; no external data sharing; no PyPI; starter pools off |
| IP firewall rules | Workspace, inbound | API in preview; doesn't support OneLake security, Power BI or Copilot |
| Workspace-level Private Link | Workspace, inbound | F SKU only; one Private Link service per workspace; no deployment pipelines or Power BI semantic models |
| Tenant Private Link with Block Public Internet Access | Tenant | Turns off Govern, the Capacity Metrics app, cross-tenant shortcuts and OneLake data sharing |

## External data share audit

## Decision

## Review date
```

Under Affected challenges, list the challenges in your repo that use a feature the setting turns off. Under External data share audit, record who runs the Task 6 audit and why. Set a review date, and check the [tenant](https://learn.microsoft.com/fabric/security/security-private-links-overview) and [workspace](https://learn.microsoft.com/fabric/security/security-workspace-level-private-links-support) Private Link limits on Learn again then, because they can change.

## Success criteria

- [ ] Merging a change to `network/sbx-sec-net-protected.yaml` sets the workspace policy with no portal clicks, and each PR that changes a network manifest gets a plan comment.
- [ ] Every Fails cell in Task 3 has a saved error in `network/evidence/`, and the read through `mpe-stcontosoapproved` succeeds.
- [ ] The Task 5 read from your IP succeeds, and the read from a network that isn't on the list fails.
- [ ] The audit reports the share from `sbx-sec-net-open` as unapproved, and a workspace with `environment: prd` and outbound `Allow` opens a drift issue.
- [ ] The protected workspace refuses the external data share, and the Task 1 PR fails validation.
- [ ] `docs/network-design.md` records the tenant Private Link decision and who runs the external share audit.

## Stretch goals

> **Preview** (checked 2026-11-27): Fabric policies — [Learn](https://learn.microsoft.com/fabric/governance/fabric-policies-overview). GA route: none; stretch task.

- **External sharing policy.** Policy rules for external data sharing are announced but not available yet. When they are, plan one with the `fabric-policies-cli` skill that allows external sharing only from approved workspaces, and manage it as in [challenge 12](../12-tenant-settings-policies-as-code/challenge.md). Fabric policies aren't available in West Europe, North Europe or West US.

> **Preview** (checked 2026-11-27): IQ Sharing — [Learn](https://learn.microsoft.com/fabric/onelake/iq-share/onelake-share-overview). GA route: none; stretch task.

- **IQ Sharing.** Try to share `lh_net` in the protected workspace with another tenant, and record whether outbound access protection blocks it. Every share needs an expiration date, and IQ Sharing isn't available in 12 regions, so check yours first.
- **Trusted workspace access.** In `sbx-sec-net-open`, turn on the firewall of `stcontosoapproved`, add a resource instance rule for the workspace with an ARM template or PowerShell, and create a shortcut to the account. Use the open workspace, because outbound access protection blocks external shortcuts in the protected one. The feature needs a purchased F SKU, not a trial, and Learn says: "Ensure that the workspace identity has Contributor access to the workspace." [Challenge 04](../04-access-rbac-lifecycle/challenge.md) Task 7 creates the workspace identity. The identity the shortcut uses needs Storage Blob Data Owner, Contributor or Reader on the storage account ([Learn](https://learn.microsoft.com/fabric/security/security-trusted-workspace-access)).
- **Terraform.** Manage the policy and the endpoints with the `fabric_workspace_network_communication_policy` and `fabric_workspace_managed_private_endpoint` resources of the [Terraform provider for Microsoft Fabric](https://registry.terraform.io/providers/microsoft/fabric/latest/docs). Keep one writer per workspace: Terraform or the script, never both.

## MCP tips

- The Core MCP has no tools for network rules. Use REST or Terraform for the policy, the firewall rules and the managed private endpoints.
- Use the Core MCP for OneLake diagnostics: `onelake_get_settings` only reads, and `onelake_modify_diagnostics` changes the settings. Read first, then write.

## Skills tips

- `spark-cli` runs the Task 3 attempts and returns the full error text for the evidence folder.
- `fabric-policies-cli` plans Fabric policies for the external sharing stretch goal.
- No Skill manages network rules, so writes use REST.
- If the skills aren't installed, run these from a terminal:

```bash
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

## Repository files

This challenge extends these files in the repo root:

- `scripts/_fabric.py` (a `headers` argument for `_request`, unless challenge 10 added it)
- `scripts/validate.py`, `scripts/drift.py`
- `rules/policy.yaml` and its copy `api/policy.yaml`
- `.github/workflows/validate.yml`, `drift.yml`
- `.github/CODEOWNERS`

It adds:

- `network/<workspace>.yaml`, `network/external-shares.yaml` and the evidence in `network/evidence/`
- `schemas/network.schema.json`
- `scripts/apply_network.py`, `scripts/audit_external_shares.py`, `scripts/onelake_read_test.py`
- `.github/workflows/network.yml`
- `docs/network-design.md`

## References

- [Workspace outbound access protection overview](https://learn.microsoft.com/fabric/security/workspace-outbound-access-protection-overview)
- [Manage outbound access from OneLake with outbound access protection](https://learn.microsoft.com/fabric/onelake/onelake-manage-outbound-access)
- [Overview of managed private endpoints for Microsoft Fabric](https://learn.microsoft.com/fabric/security/security-managed-private-endpoints-overview)
- [About workspace IP firewall rules](https://learn.microsoft.com/fabric/security/security-workspace-level-firewall-overview)
- [Overview of workspace-level private links](https://learn.microsoft.com/fabric/security/security-workspace-level-private-links-overview)
- [Supported scenarios for workspace private links](https://learn.microsoft.com/fabric/security/security-workspace-level-private-links-support)
- [About private Links for secure access to Fabric](https://learn.microsoft.com/fabric/security/security-private-links-overview)
- [Trusted workspace access in Microsoft Fabric](https://learn.microsoft.com/fabric/security/security-trusted-workspace-access)
- [External Data Sharing in Microsoft Fabric](https://learn.microsoft.com/fabric/governance/external-data-sharing-overview)
- [OneLake diagnostics](https://learn.microsoft.com/fabric/onelake/onelake-diagnostics-overview)
- [Access OneLake with Python](https://learn.microsoft.com/fabric/onelake/onelake-access-python)
- [Microsoft Fabric policies](https://learn.microsoft.com/fabric/governance/fabric-policies-overview)
- [IQ Sharing overview](https://learn.microsoft.com/fabric/onelake/iq-share/onelake-share-overview)
- [Get Network Communication Policy REST API](https://learn.microsoft.com/rest/api/fabric/core/workspaces/get-network-communication-policy)
- [Set Network Communication Policy REST API](https://learn.microsoft.com/rest/api/fabric/core/workspaces/set-network-communication-policy)
- [Set Firewall Rules REST API](https://learn.microsoft.com/rest/api/fabric/core/workspaces/set-firewall-rules)
- [Create Workspace Managed Private Endpoint REST API](https://learn.microsoft.com/rest/api/fabric/core/managed-private-endpoints/create-workspace-managed-private-endpoint)
- [List Workspace Managed Private Endpoints REST API](https://learn.microsoft.com/rest/api/fabric/core/managed-private-endpoints/list-workspace-managed-private-endpoints)
- [List Networking Communication Policies admin REST API](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-networking-communication-policies)
- [List External Data Shares admin REST API](https://learn.microsoft.com/rest/api/fabric/admin/external-data-shares-provider/list-external-data-shares)
- [Create External Data Share REST API](https://learn.microsoft.com/rest/api/fabric/core/external-data-shares-provider/create-external-data-share)
- [Core MCP tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [`spark-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/spark-cli)
- [`fabric-policies-cli` skill](https://github.com/microsoft/skills-for-fabric/tree/main/skills/fabric-policies-cli)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
