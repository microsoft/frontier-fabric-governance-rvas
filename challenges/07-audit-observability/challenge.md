# Challenge 07 — Audit & observability

> **Outcome:** GitHub and Fabric governance events land in one Eventhouse,
> `eh_gov_audit`. A Governance Health report shows pull request throughput,
> provisioning, drift, Fabric item changes and access, and Activator emails
> the governance team when a control slips.

## Why this challenge exists

The earlier challenges put workspaces, items and access under Git. Nobody can
see yet whether those controls hold: pull requests merged without review,
provisioning runs that keep failing, drift left open for a week, items
changed outside Git.

Two obvious shortcuts don't work:

- A GitHub webhook can't post straight into an Eventstream. A custom endpoint
  speaks the Event Hubs, AMQP or Kafka protocol, and the HTTP source only
  polls. An Azure Function relays the webhooks instead.
- Purview Audit has no Eventstream connector. Fabric audit data comes from
  Real-Time hub workspace item events, the activity log and OneLake
  diagnostics instead.

## Learning objectives

1. Keep the audit store's schema in Git and apply it with the
   `eventhouse-cli` Skill.
2. Relay GitHub webhooks into an Eventstream custom endpoint built with the
   `eventstream-cli` Skill.
3. Collect Fabric audit events from workspace item events, the activity log
   and OneLake diagnostics.
4. Build a Governance Health report with the `semantic-model-authoring` and
   `powerbi-report-cli` Skills.
5. Alert when a control slips with the `activator-cli` Skill.
6. Answer audit questions from chat with the Fabric Core MCP server and the
   `eventhouse-cli` Skill.

## Prerequisites

- Challenges 00–02 complete. You have the service principal (SPN) and its
  group, `sg-fabric-workspace-provisioner`, from
  [challenge 00](../00-setup/challenge.md), and the `provision` and `drift`
  workflows and the `dev-plt-myteam-playground` workspace from
  [challenge 01](../01-workspace-as-code/challenge.md).
- `sg-fabric-workspace-provisioner` is allowed to use "Service principals can
  access read-only admin APIs". Find the setting in OneLake catalog >
  **Govern** > **Configurations**, or in Admin portal > **Tenant settings**
  if your tenant doesn't show it there yet.
- The SPN holds no Power BI API permissions that need admin consent. The
  read-only admin APIs reject a service principal that has them.
- You're Admin of `dev-plt-myteam-playground` (Task 6 needs it) and at least
  Viewer of every workspace you want to watch.
- An Azure subscription where you can create a resource group, a Function app
  and a key vault, plus Python 3.11, Azure Functions Core Tools 4.12 or later,
  Azure CLI 2.87.0 or later, and `gh` signed in with admin rights on your fork
  (to create the webhook and repository variables).

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
copilot plugin install powerbi-authoring@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

## Tasks

### Task 1 — Create the audit workspace

Add this manifest as `workspaces/dev-plt-gov-audit.yaml` in a pull request.
Replace the group's Object ID with your admin group's, and
`workspace-owner@contoso.com` with your own UPN.

```yaml
name: dev-plt-gov-audit
environment: dev
team: plt
domain: dom-grc-risk
subDomain: sdm-grc-audit
description: "Governance audit store: GitHub and Fabric audit events, the Governance Health report and alerts."
capacity: contosononprodf2
region: northeurope
sensitivityLabel: Confidential
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

When the pull request merges, the `provision` workflow pauses at the
`production` environment. Approve the run and it creates the workspace.

Check the roles. In a Copilot CLI session with the Fabric Core MCP connected:

```text
List the role assignments of workspace "dev-plt-gov-audit".
```

The Core MCP `list_workspace_roles` tool answers. Expect your group as Admin,
you as Member and the SPN as Admin, because the SPN created the workspace.
Task 5 relies on that SPN role.

### Task 2 — Build the audit store

With the Core MCP `create_item` tool, create an Eventhouse named
`eh_gov_audit` in `dev-plt-gov-audit`. It comes with a KQL database of the
same name
([Learn](https://learn.microsoft.com/fabric/real-time-intelligence/create-eventhouse)).
In a Copilot CLI session with the Fabric Core MCP connected:

```text
Create an Eventhouse named "eh_gov_audit" in workspace "dev-plt-gov-audit", then list the items in the workspace with their IDs.
```

Note the KQL database's item ID from the `list_items` answer. Tasks 3, 4 and
8 need it.

Save the schema as `items/dev-plt-gov-audit/eh_gov_audit.kql`. It creates two
raw tables, keeps 90 days of data and turns on streaming ingestion, then
defines the functions that the report, the alerts and your questions use.
`events()` keeps one row per source and delivery ID, so a redelivered webhook
or a rerun export doesn't count twice.

```text
.create-merge table gov_events (
    received_at: datetime, source: string, event: string,
    delivery: string, repo: string, payload: dynamic)

.create-merge table fabric_item_events (
    id: string, source: string, subject: string, type: string,
    ['time']: datetime, specversion: string, dataschemaversion: string,
    datacontenttype: string, data: dynamic)

.alter-merge table gov_events policy retention softdelete = 90d

.alter-merge table fabric_item_events policy retention softdelete = 90d

.alter table gov_events policy streamingingestion enable

.alter table fabric_item_events policy streamingingestion enable

.create-or-alter function with (folder = "gov") events() {
    gov_events
    | summarize arg_max(received_at, *) by source, delivery
}

.create-or-alter function with (folder = "gov") pr_events() {
    events()
    | where source == "github" and event == "pull_request"
    | project received_at, repo,
        action = tostring(payload.action),
        number = toint(payload.pull_request.number),
        pr_title = tostring(payload.pull_request["title"]),
        author = tostring(payload.pull_request.user.login),
        created_at = todatetime(payload.pull_request.created_at),
        merged_at = todatetime(payload.pull_request.merged_at),
        merged_by = tostring(payload.pull_request.merged_by.login),
        merge_sha = tostring(payload.pull_request.merge_commit_sha),
        labels = payload.pull_request.labels
}

.create-or-alter function with (folder = "gov") pr_reviews() {
    events()
    | where source == "github" and event == "pull_request_review"
    | project repo,
        number = toint(payload.pull_request.number),
        reviewer = tostring(payload.review.user.login),
        state = tostring(payload.review.state),
        submitted_at = todatetime(payload.review.submitted_at)
}

.create-or-alter function with (folder = "gov") merged_prs() {
    pr_events()
    | where action == "closed" and isnotnull(merged_at)
    | summarize arg_max(received_at, *) by repo, number
    | project repo, number, pr_title, author, merged_by, merged_at, merge_sha,
        week = startofweek(merged_at),
        hoursToMerge = round((merged_at - created_at) / 1h, 1)
}

.create-or-alter function with (folder = "gov") workflow_runs() {
    events()
    | where source == "github" and event == "workflow_run"
        and tostring(payload.action) == "completed"
    | project repo,
        workflow = tostring(payload.workflow_run.name),
        run_id = tolong(payload.workflow_run.id),
        conclusion = tostring(payload.workflow_run.conclusion),
        head_sha = tostring(payload.workflow_run.head_sha),
        started_at = todatetime(payload.workflow_run.run_started_at),
        updated_at = todatetime(payload.workflow_run.updated_at)
}

.create-or-alter function with (folder = "gov") provision_runs() {
    workflow_runs()
    | where workflow == "provision"
    | summarize arg_max(updated_at, *) by repo, run_id
    | project repo, run_id, conclusion, head_sha, started_at, updated_at,
        week = startofweek(updated_at)
}

.create-or-alter function with (folder = "gov") provision_failure_streaks() {
    provision_runs()
    | order by repo asc, updated_at asc
    | extend failed = conclusion == "failure"
    | extend streak = row_cumsum(iff(failed, 1, 0), repo != prev(repo) or not(failed))
    | summarize arg_max(updated_at, streak) by repo
    | project repo, failureStreak = streak
}

.create-or-alter function with (folder = "gov") drift_issues() {
    events()
    | where source == "github" and event == "issues"
    | extend number = toint(payload.issue.number),
        updated_at = todatetime(payload.issue.updated_at)
    | mv-apply label = payload.issue.labels on (
        extend name = tostring(label.name)
        | summarize isDrift = countif(name == "drift"),
            category = take_anyif(substring(name, 6), name startswith "drift/"))
    | summarize arg_max(updated_at, payload), isDrift = max(isDrift),
        category = take_anyif(category, isnotempty(category)) by repo, number
    | where isDrift > 0
    | project repo, number,
        issue_title = tostring(payload.issue["title"]),
        state = tostring(payload.issue.state),
        created_at = todatetime(payload.issue.created_at),
        closed_at = todatetime(payload.issue.closed_at),
        category = iff(isempty(category), "uncategorized", category)
}

.create-or-alter function with (folder = "gov") drift_issue_age() {
    drift_issues()
    | summarize
        openIssues = countif(state == "open"),
        oldestOpenDays = maxif(toint((now() - created_at) / 1d), state == "open"),
        nightsWithDrift30d = dcountif(startofday(created_at), created_at > ago(30d))
        by repo
    | extend oldestOpenDays = coalesce(oldestOpenDays, 0)
}

.create-or-alter function with (folder = "gov") activity() {
    events()
    | where source == "fabric-activity"
    | project
        CreationTime = todatetime(payload.CreationTime),
        Operation = tostring(payload.Operation),
        Activity = tostring(payload.Activity),
        UserId = tostring(payload.UserId),
        IsSuccess = tobool(payload.IsSuccess),
        WorkspaceId = tostring(payload.WorkspaceId),
        WorkSpaceName = tostring(payload.WorkSpaceName),
        ItemName = tostring(payload.ItemName),
        ArtifactKind = tostring(payload.ArtifactKind)
}

.create-or-alter function with (folder = "gov") workspace_snapshots() {
    events()
    | where source == "fabric-snapshot" and event == "workspace_snapshot"
    | project
        snapshotDate = todatetime(payload.snapshotDate),
        workspaceId = tostring(payload.workspaceId),
        name = tostring(payload.name),
        capacityId = tostring(payload.capacityId),
        domainId = tostring(payload.domainId),
        managed = tobool(payload.managed),
        environment = tostring(payload.environment),
        roles = payload.roles
}

.create-or-alter function with (folder = "gov") workspace_envs() {
    let lastDate = toscalar(workspace_snapshots() | summarize max(snapshotDate));
    workspace_snapshots()
    | where snapshotDate == lastDate
}

.create-or-alter function with (folder = "gov") role_assignments() {
    workspace_envs()
    | where managed
    | mv-expand r = roles
    | project workspaceId, name, environment,
        principalType = tostring(r.principalType),
        principalName = tostring(r.principalName),
        principalId = tostring(r.principalId),
        role = tostring(r.role)
}

.create-or-alter function with (folder = "gov") prd_user_admins() {
    role_assignments()
    | where environment == "prd" and principalType == "User" and role == "Admin"
    | summarize userAdmins = count(), workspaces = make_set(name)
}

.create-or-alter function with (folder = "gov") unmanaged_new_last_day() {
    let days = workspace_snapshots() | distinct snapshotDate | top 2 by snapshotDate desc;
    let lastDate = toscalar(days | summarize max(snapshotDate));
    let prevDate = toscalar(days | summarize min(snapshotDate));
    workspace_snapshots()
    | where snapshotDate == lastDate and not(managed)
    | join kind=leftanti (
        workspace_snapshots() | where snapshotDate == prevDate
    ) on workspaceId
    | summarize newUnmanaged = count(), workspaces = make_set(name)
}

.create-or-alter function with (folder = "gov") item_changes() {
    fabric_item_events
    | summarize arg_max(['time'], *) by id
    | project ['time'],
        change = extract(@"^Microsoft\.Fabric\.Item(\w+?)(Succeeded|Failed)$", 1, type),
        outcome = extract(@"(Succeeded|Failed)$", 1, type),
        itemKind = tostring(data.itemKind),
        itemName = tostring(data.itemName),
        workspaceId = tostring(data.workspaceId),
        workspaceName = tostring(data.workspaceName),
        principalId = tostring(data.executingPrincipalId),
        principalType = tostring(data.executingPrincipalType)
}
```

Apply the script. In a Copilot CLI session:

```text
/eventhouse-cli In KQL database "eh_gov_audit" of workspace "dev-plt-gov-audit", run the management script items/dev-plt-gov-audit/eh_gov_audit.kql, then list the tables and functions.
```

The script is safe to rerun: `.create-merge` and `.create-or-alter` change
only what differs. To see what Fabric holds, ask the Core MCP for the KQL
database's definition. `get_item_definition` returns its schema script, which
you can compare with Git
([Learn](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/kql-database-definition)).

### Task 3 — Relay GitHub webhooks

An Eventstream custom endpoint accepts Event Hubs, AMQP and Kafka clients, not
HTTP webhooks
([Learn](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-source-custom-app)).
An Azure Function receives each webhook, checks GitHub's signature and sends
the payload to the custom endpoint with the Event Hubs SDK.

Create the eventstream. In a Copilot CLI session:

```text
/eventstream-cli In workspace "dev-plt-gov-audit", create an eventstream "es_gov_audit" with two custom endpoint sources, "GitHubRelay" and "AuditExport", and an Eventhouse destination "GovEvents" that writes JSON events to table gov_events in KQL database "eh_gov_audit" (item ID <kql-database-id>) with event processing before ingestion.
```

`GitHubRelay` takes the webhooks and `AuditExport` takes the Fabric export in
Task 5. Open `GitHubRelay` in the eventstream, select **SAS Key
Authentication** and copy **Connection string-primary key**. You paste it
below.

Create the Function project:

```bash
func init relay --python
```

Replace `relay/function_app.py` with:

```python
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

import azure.functions as func
from azure.eventhub import EventData, EventHubProducerClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
producer = EventHubProducerClient.from_connection_string(os.environ["EVENTSTREAM_CONNECTION"])


@app.route(route="github", methods=["POST"])
def github(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_body()
    secret = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, req.headers.get("X-Hub-Signature-256", "")):
        return func.HttpResponse(status_code=401)
    event = req.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return func.HttpResponse(status_code=204)
    payload = json.loads(body)
    record = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "source": "github",
        "event": event,
        "delivery": req.headers.get("X-GitHub-Delivery", ""),
        "repo": payload.get("repository", {}).get("full_name", ""),
        "payload": payload,
    }
    batch = producer.create_batch()
    try:
        batch.add(EventData(json.dumps(record)))
    except ValueError:
        return func.HttpResponse("Payload too large for one event.", status_code=413)
    producer.send_batch(batch)
    return func.HttpResponse(status_code=202)
```

Replace `relay/requirements.txt` with:

```text
azure-functions
azure-eventhub
```

The function rejects any delivery whose `X-Hub-Signature-256` header doesn't
match an HMAC of the body with the webhook secret, as GitHub describes
([GitHub Docs](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)).
The webhook sends four events:

- `pull_request` for throughput and merges without review.
- `pull_request_review` for who approved.
- `workflow_run` for provisioning runs and their outcome.
- `issues` for the issues the `drift` workflow opens.

Create a resource group `rg-gov-audit` in `northeurope` and a Python 3.11
Function app on the Flex Consumption plan, as the quickstart shows
([Learn](https://learn.microsoft.com/azure/azure-functions/how-to-create-function-azure-cli?pivots=programming-language-python)).
Run the next blocks from the folder that holds `relay/`, in one shell.

Create a key vault and give yourself the right to write secrets. Put your
Function app's name in `APP`:

```bash
RG=rg-gov-audit
APP="<your-function-app>"
VAULT=kv-gov-relay-$(openssl rand -hex 3)
az keyvault create --name "$VAULT" --resource-group "$RG" --location northeurope --enable-rbac-authorization true
VAULT_ID=$(az keyvault show --name "$VAULT" --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --assignee-object-id "$ME" --assignee-principal-type User --role "Key Vault Secrets Officer" --scope "$VAULT_ID"
```

Run this command on its own, paste the `GitHubRelay` connection string and
press Enter. Nothing echoes. Pasted together with other lines, `read` would
take the next line as the value.

```bash
read -rs EVENTSTREAM_CONNECTION
```

Store both secrets, let the Function app read them through Key Vault
references
([Learn](https://learn.microsoft.com/azure/app-service/app-service-key-vault-references))
and publish the function. If `secret set` returns 403, your role assignment
hasn't applied yet; wait a minute and run the block again.

```bash
GITHUB_WEBHOOK_SECRET=$(openssl rand -hex 32)
az keyvault secret set --vault-name "$VAULT" --name eventstream-connection --value "$EVENTSTREAM_CONNECTION" --output none
az keyvault secret set --vault-name "$VAULT" --name github-webhook-secret --value "$GITHUB_WEBHOOK_SECRET" --output none
az functionapp identity assign --name "$APP" --resource-group "$RG"
PRINCIPAL=$(az functionapp identity show --name "$APP" --resource-group "$RG" --query principalId -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL" --assignee-principal-type ServicePrincipal --role "Key Vault Secrets User" --scope "$VAULT_ID"
az functionapp config appsettings set --name "$APP" --resource-group "$RG" --settings "EVENTSTREAM_CONNECTION=@Microsoft.KeyVault(VaultName=$VAULT;SecretName=eventstream-connection)" "GITHUB_WEBHOOK_SECRET=@Microsoft.KeyVault(VaultName=$VAULT;SecretName=github-webhook-secret)"
cd relay && func azure functionapp publish "$APP" && cd ..
```

Create the webhook on your fork, list it and post an unsigned request
([GitHub Docs](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks)):

```bash
HOST=$(az functionapp show --name "$APP" --resource-group "$RG" --query defaultHostName -o tsv)
gh api --method POST 'repos/{owner}/{repo}/hooks' -f name=web -F active=true -f 'events[]=pull_request' -f 'events[]=pull_request_review' -f 'events[]=workflow_run' -f 'events[]=issues' -f "config[url]=https://$HOST/api/github" -f 'config[content_type]=json' -f "config[secret]=$GITHUB_WEBHOOK_SECRET"
gh api 'repos/{owner}/{repo}/hooks' --jq '.[] | {id, events, last_response}'
curl -s -o /dev/null -w '%{http_code}\n' -X POST "https://$HOST/api/github" -d '{}'
```

GitHub pings a new webhook, so `last_response` shows code 204 once the ping
arrives. The unsigned post prints 401.

Open a pull request on your fork, then check that its events arrived. In a
Copilot CLI session:

```text
/eventhouse-cli In KQL database "eh_gov_audit" of workspace "dev-plt-gov-audit", show the latest 10 rows of table gov_events with received_at, event, repo and delivery.
```

### Task 4 — Capture Fabric item events

Fabric workspace item events report each Create, Update, Delete, SoftDelete
and Recover of an item, as Succeeded or Failed. Each event names who acted in
`executingPrincipalId` and `executingPrincipalType`, so you can tell a person
from the SPN
([Learn](https://learn.microsoft.com/fabric/real-time-hub/explore-fabric-workspace-item-events)).
Semantic models, paginated reports, reports, apps, dashboards and Dataflow
Gen1 emit no item events; the activity log in Task 5 covers them.

A workspace item events source watches one workspace and needs Viewer on it.
A source for the whole tenant needs the Global Administrator role
([Learn](https://learn.microsoft.com/fabric/real-time-hub/fabric-events-subscribe-permission)),
so add one source per workspace you watch.

Create the eventstream. In a Copilot CLI session:

```text
/eventstream-cli In workspace "dev-plt-gov-audit", create an eventstream "es_fabric_items" with two Fabric workspace item events sources, "WorkspaceItemsAudit" for workspace "dev-plt-gov-audit" and "WorkspaceItemsPlayground" for workspace "dev-plt-myteam-playground", each subscribed to all item event types, and an Eventhouse destination "ItemEvents" that writes JSON events to table fabric_item_events in KQL database "eh_gov_audit" (item ID <kql-database-id>).
```

Test it: create a notebook in `dev-plt-myteam-playground`, delete it and wait
a few minutes. Then, in a Copilot CLI session:

```text
/eventhouse-cli In KQL database "eh_gov_audit" of workspace "dev-plt-gov-audit", run item_changes() | where ['time'] > ago(1h) | order by ['time'] desc.
```

Expect the create and the delete, each with you as the principal.

### Task 5 — Export the activity log and a workspace snapshot

The activity log records what people and service principals do across the
tenant, including the semantic models and reports that item events skip
([Learn](https://learn.microsoft.com/fabric/admin/track-user-activities)). Its
API serves only the last 28 days, so a nightly workflow copies it into the
audit store. The same run takes a snapshot of every workspace: whether a
manifest manages it, its environment and, for managed workspaces, its role
assignments.

The script reads the activity log with Get Activity Events
(Power BI admin API; no Fabric API yet) and lists workspaces with the Fabric
admin List Workspaces API
([Learn](https://learn.microsoft.com/rest/api/power-bi/admin/get-activity-events),
[Learn](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces)).
Get Activity Events covers one UTC day per call, allows 200 requests an hour
and pages with `continuationUri`, so the script asks for one day at a time.
It goes back at most 27 days, the whole UTC days inside the 28-day window.
The workflow calls REST because it runs unattended, and no Core MCP tool
covers admin APIs.

Role assignments come from List Workspace Role Assignments, which needs a role
in the workspace. The SPN is Admin of every workspace it provisioned, so the
script reads roles for managed workspaces only. A workspace counts as
production when its manifest says `environment: prd`, never because of its
name.

Save the script as `scripts/audit_export.py`. On 401 or 403 it stops with
exit code 3 and a hint, so a missing permission never looks like an empty
tenant.

```python
"""Send Fabric activity events and a workspace snapshot to the audit Eventstream."""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time

import requests
import yaml
from azure.eventhub import EventData, EventHubProducerClient
from azure.identity import DefaultAzureCredential

sys.path.insert(0, os.path.dirname(__file__))
import _fabric as fab  # noqa: E402

ACTIVITY_URL = "https://api.powerbi.com/v1.0/myorg/admin/activityevents"
HINT = ("Check that sg-fabric-workspace-provisioner may use read-only admin APIs, "
        "that the SPN holds no Power BI permissions that need admin consent, "
        "and that it has a role in every managed workspace.")


def get(url, scope, params=None):
    """GET a URL; retry on 429 and stop with exit code 3 on 401 or 403."""
    while True:
        r = requests.get(url, params=params, timeout=60,
                         headers={"Authorization": f"Bearer {fab.token(scope)}"})
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", "60")))
            continue
        if r.status_code in (401, 403):
            print(f"{r.status_code} from {url.split('?')[0]}. {HINT}", file=sys.stderr)
            sys.exit(3)
        r.raise_for_status()
        return r.json()


def activity(day):
    """Yield every activity event of one UTC day."""
    params = {"startDateTime": f"'{day:%Y-%m-%d}T00:00:00.000Z'",
              "endDateTime": f"'{day:%Y-%m-%d}T23:59:59.999Z'"}
    page = get(ACTIVITY_URL, fab.PBI_SCOPE, params)
    while True:
        yield from page.get("activityEventEntities", [])
        done = page.get("lastResultSet")
        if done is None:
            done = not page.get("activityEventEntities")
        if done or not page.get("continuationUri"):
            return
        page = get(page["continuationUri"], fab.PBI_SCOPE)


def paged(url, key, params=None):
    """Yield every entry of a paged Fabric API."""
    while url:
        page = get(url, fab.FABRIC_SCOPE, params)
        yield from page.get(key, [])
        url, params = page.get("continuationUri"), None


def workspaces():
    """Yield every active workspace from the Fabric admin API."""
    yield from paged(f"{fab.FABRIC_BASE}/admin/workspaces", "workspaces",
                     {"type": "Workspace", "state": "Active"})


def roles(workspace_id):
    """Yield the role assignments of a workspace where the SPN has a role."""
    yield from paged(f"{fab.FABRIC_BASE}/workspaces/{workspace_id}/roleAssignments", "value")


def environments():
    """Map each manifest's workspace name to its environment."""
    envs = {}
    for path in pathlib.Path("workspaces").glob("*.yaml"):
        manifest = yaml.safe_load(path.read_text())
        envs[manifest["name"]] = manifest["environment"]
    return envs


def record(source, event, delivery, received_at, payload):
    return {"received_at": received_at, "source": source, "event": event,
            "delivery": delivery, "repo": "", "payload": payload}


def events(days):
    today = dt.datetime.now(dt.timezone.utc).date()
    for n in range(days, 0, -1):
        for e in activity(today - dt.timedelta(days=n)):
            yield record("fabric-activity", e.get("Operation", ""), e["Id"],
                         e.get("CreationTime"), e)
    envs, now = environments(), dt.datetime.now(dt.timezone.utc).isoformat()
    for ws in workspaces():
        env = envs.get(ws["name"])
        members = [] if env is None else [
            {"principalType": a["principal"]["type"],
             "principalName": a["principal"].get("displayName", ""),
             "principalId": a["principal"]["id"], "role": a["role"]}
            for a in roles(ws["id"])]
        yield record("fabric-snapshot", "workspace_snapshot",
                     f"snapshot/{ws['id']}/{today}", now,
                     {"snapshotDate": str(today), "workspaceId": ws["id"],
                      "name": ws["name"], "capacityId": ws.get("capacityId", ""),
                      "domainId": ws.get("domainId", ""), "managed": env is not None,
                      "environment": env or "", "roles": members})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="UTC days to export, 1-27")
    days = parser.parse_args().days
    if not 1 <= days <= 27:
        parser.error("--days must be between 1 and 27")
    producer = EventHubProducerClient(
        fully_qualified_namespace=os.environ["EVENTSTREAM_NAMESPACE"],
        eventhub_name=os.environ["EVENTSTREAM_HUB"],
        credential=DefaultAzureCredential())
    sent = 0
    with producer:
        batch = producer.create_batch()
        for item in events(days):
            data = EventData(json.dumps(item))
            try:
                batch.add(data)
            except ValueError:
                producer.send_batch(batch)
                batch = producer.create_batch()
                batch.add(data)
            sent += 1
        if len(batch):
            producer.send_batch(batch)
    print(f"Sent {sent} events.")


if __name__ == "__main__":
    main()
```

Add the Event Hubs SDK to `scripts/requirements.txt`:

```text
azure-eventhub>=5.11.0
```

The workflow signs in to the custom endpoint with its Entra token instead of
a key, so it uses the Entra ID details of `AuditExport`
([Learn](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/custom-endpoint-entra-id-auth)).
The SPN needs Contributor or higher on the eventstream's workspace; it's
already Admin. Open `AuditExport`, show its Entra ID details and store the
event hub namespace and name as repository variables:

```bash
gh variable set EVENTSTREAM_NAMESPACE --body "<your-namespace>.servicebus.windows.net"
gh variable set EVENTSTREAM_HUB --body "<your-event-hub>"
```

Save the workflow as `.github/workflows/audit-export.yml`. It runs daily at
02:41 UTC and exports the previous UTC day.

```yaml
name: audit-export

# ── Blueprint reference workflow — dormant in the canonical public repo ──────────────
# Sends Fabric activity events and a daily workspace snapshot to the audit Eventstream
# from a customer-provided [self-hosted, fabric-gov] runner via Azure OIDC (no
# long-lived secrets). Enable it in a fork that has the runner and repo variables.
# ─────────────────────────────────────────────────────────────────────────────────────

on:
  schedule:
    - cron: '41 2 * * *'
  workflow_dispatch:
    inputs:
      days:
        description: 'UTC days to export (1-27)'
        default: '1'

permissions:
  contents: read
  id-token: write

jobs:
  export:
    runs-on: [self-hosted, fabric-gov]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

      - name: Setup Python venv
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

      - name: Export audit events
        env:
          DAYS: ${{ inputs.days || '1' }}
          EVENTSTREAM_NAMESPACE: ${{ vars.EVENTSTREAM_NAMESPACE }}
          EVENTSTREAM_HUB: ${{ vars.EVENTSTREAM_HUB }}
        run: python scripts/audit_export.py --days "$DAYS"
```

Merge these files in a pull request. The merge changes `scripts/`, so the
`provision` workflow runs too; approve it at `production`. Then backfill the
last seven days:

```bash
gh workflow run audit-export.yml -f days=7
```

When the run finishes, `activity()` and `workspace_snapshots()` return rows.

### Task 6 — Turn on OneLake diagnostics

The activity log doesn't record every OneLake read and write
([Learn](https://learn.microsoft.com/fabric/admin/operation-list)). OneLake
diagnostics do: they write each read, write and delete in a workspace as JSON
files to a lakehouse you choose
([Learn](https://learn.microsoft.com/fabric/onelake/onelake-diagnostics-overview)).
The lakehouse must be on the same capacity as the watched workspace. You need
Admin on the watched workspace and Contributor on the lakehouse's workspace.

In a Copilot CLI session with the Fabric Core MCP connected:

```text
Create a Lakehouse named "lh_gov_diag" in workspace "dev-plt-gov-audit".
Turn on OneLake diagnostics for workspace "dev-plt-myteam-playground" and send the logs to lakehouse "lh_gov_diag" in workspace "dev-plt-gov-audit".
Show the OneLake settings of workspace "dev-plt-myteam-playground".
```

The Core MCP answers with `create_item`, `onelake_modify_diagnostics` and
`onelake_get_settings`. Logs arrive within about an hour, under
`Files/DiagnosticLogs/OneLake/Workspaces/<workspace-id>/y=YYYY/m=MM/d=DD/h=HH/m=00/PT1H.json`.

The tenant setting "Include end-user identifiers in OneLake diagnostic logs"
decides whether `executingUPN` and `callerIPAddress` are filled. Find it in
OneLake catalog > **Govern** > **Configurations**, or in Admin portal >
**Tenant settings**. Moving the watched workspace to another capacity turns
diagnostics off, so turn them on again after a move.

Append this external table to `items/dev-plt-gov-audit/eh_gov_audit.kql`,
replace the two IDs and rerun the Task 2 prompt. Both IDs are in the
lakehouse's address in the browser:
`…/groups/<audit-workspace-id>/lakehouses/<lh_gov_diag-id>`.

```text
.create-or-alter external table onelake_access (
    workspaceId: string, itemId: string, itemType: string,
    executingPrincipalId: string, executingUPN: string,
    executingPrincipalType: string, operationName: string,
    operationCategory: string, originatingApp: string, Resource: string,
    accessStartTime: datetime, httpStatusCode: int, isShortcut: bool,
    callerIPAddress: string)
kind = storage
dataformat = multijson
(
    h@'https://onelake.dfs.fabric.microsoft.com/<audit-workspace-id>/<lh_gov_diag-id>/Files/DiagnosticLogs/OneLake/Workspaces;impersonate'
)
with (fileExtension = ".json")
```

`;impersonate` reads the files as the person who runs the query
([Learn](https://learn.microsoft.com/kusto/management/external-tables-azure-storage?view=microsoft-fabric)),
so query `onelake_access` from chat (Task 9), not from Activator.

### Task 7 — Build the Governance Health report

The report reads the KQL functions through a semantic model in DirectQuery
mode, so it always shows current data and needs no refresh schedule. The
model and the report live in Git as a Power BI project (PBIP)
([Learn](https://learn.microsoft.com/power-bi/developer/projects/projects-overview)).

Open `eh_gov_audit` in Fabric and copy the **Query URI** from the
**Database details** card
([Learn](https://learn.microsoft.com/fabric/real-time-intelligence/access-database-copy-uri)).
It replaces `<kql-query-uri>` below.

Create the model. Ask for DirectQuery by name; otherwise the Skill builds an
Import model. In a Copilot CLI session:

```text
/semantic-model-authoring Create a semantic model "sm_governance_health" in DirectQuery mode on KQL database "eh_gov_audit" at <kql-query-uri>, with one table per function: merged_prs(), provision_runs(), provision_failure_streaks(), drift_issues(), drift_issue_age(), item_changes(), role_assignments() and prd_user_admins(). Save it as a PBIP project in items/dev-plt-gov-audit/ and deploy it to workspace "dev-plt-gov-audit".
```

The deploy isn't idempotent. If you see "There are multiple datasets named",
a retry created a second model; delete the extra copies so one remains. If
the model can't reach the database, open the model's settings in the
workspace and sign in under **Data source credentials**
([Learn](https://learn.microsoft.com/power-bi/connect-data/refresh-scheduled-refresh)).

Saving as PBIP also writes a placeholder report next to the model. Delete it;
the next prompt builds the real one:

```bash
rm -rf items/dev-plt-gov-audit/sm_governance_health.Report items/dev-plt-gov-audit/sm_governance_health.pbip
```

Build the report on the local model. In a Copilot CLI session:

```text
/powerbi-report-cli Create report "rpt_governance_health" on the local semantic model items/dev-plt-gov-audit/sm_governance_health.SemanticModel, saved in items/dev-plt-gov-audit/, with five pages. PR throughput: merged PRs per week and average hoursToMerge. Provisioning: runs per week by conclusion, and failureStreak by repo. Drift: open drift issues by repo and category, with openIssues, oldestOpenDays and nightsWithDrift30d. Fabric changes: item changes by principalType and workspaceName. Access: userAdmins against a target of 0, and the role_assignments() rows where environment is prd, principalType is User and role is Admin.
```

The Skill writes its plan to `_brief/report-spec.md` in the current folder
and waits. Read the plan and reply to approve it. The Skill then builds the
pages and screenshots each one in a preview host: Power BI Desktop on
Windows, otherwise the Power BI service against the published model. For the
service it asks for the workspace ID, `<audit-workspace-id>` from Task 6,
and the model's item ID. To get the item ID, in a Copilot CLI session with
the Fabric Core MCP connected:

```text
List the items in workspace "dev-plt-gov-audit" with their IDs.
```

Publish the report and connect it to the deployed model. In a Copilot CLI
session:

```text
/powerbi-report-cli Publish items/dev-plt-gov-audit/rpt_governance_health.pbip to workspace "dev-plt-gov-audit" and connect it to the existing semantic model "sm_governance_health".
```

When the Skill asks, choose to connect to the existing model and keep the
default name. Publishing rewrites `definition.pbir` to point at the published
model's ID. If a visual comes up empty, ask the Skill to check its field
bindings.

Commit the project in a pull request. Keep Power BI Desktop's local settings
and cache out of Git, and stage only these paths, so `_brief/` stays out:

```bash
printf '%s\n' '**/.pbi/localSettings.json' '**/.pbi/cache.abf' >> .gitignore
git add .gitignore items/dev-plt-gov-audit/
```

The Drift page reads the issues that challenge 01's `drift` workflow opens.
The workflow runs daily at 03:17 UTC and on demand. Each run that finds
drift opens a new "Fabric workspace drift detected" issue labeled `drift`
and `governance`. It doesn't update or close earlier issues, so drift that
lasts several nights opens one issue a night; close them after a clean run.
An issue's category comes from a `drift/<category>` label if your
`drift.yml` adds one; an issue without one counts as `uncategorized`.
`nightsWithDrift30d` counts the UTC days in the last 30 that opened a drift
issue, on-demand runs included.

### Task 8 — Alert with Activator

Activator runs a KQL query against the database on a schedule, and its rules
check each result
([Learn](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/ingestion/ingestion-kql-querysets)).
These sources return current state with no time column, so they run in
snapshot mode.

The Skill checks that each source returns rows before it builds the rules.
`unmanaged_new_last_day()` and `prd_user_admins()` always return one row,
and `provision_failure_streaks()` has the run from Task 5.
`drift_issue_age()` has no rows until a drift issue event arrives, so open
one:

```bash
gh label create drift --force
gh issue create --title "Drift alert seed" --label drift --body "Seed for the drift alert. Close it after Task 8."
```

The seed counts as a night with drift for the next 30 days.

Create the activator. Use your team's address instead of
`governance@contoso.com`. In a Copilot CLI session:

```text
/activator-cli In workspace "dev-plt-gov-audit" (workspace ID <audit-workspace-id>), create an activator "act_gov_alerts" with four KQL sources on KQL database "eh_gov_audit" (item ID <kql-database-id>), each in snapshot mode and queried every 3600 seconds: unmanaged_new_last_day(), prd_user_admins(), provision_failure_streaks() and drift_issue_age(). Add one rule per source that emails governance@contoso.com when the value becomes greater than its threshold: newUnmanaged above 5, userAdmins above 0, failureStreak above 2 and oldestOpenDays above 7.
```

Each rule uses a change condition, so it fires when the value rises past the
threshold. A state condition such as **Is greater than** fires on every
result where it holds, which here means an email an hour
([Learn](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-detection-conditions)).
New drift issues don't reset the age of the oldest open one, so drift that
persists fires the drift rule once, when the oldest open issue passes
7 days, not once a night. The rules assume one watched repo; for several,
ask the Skill to track each repo as its own object.

Test the provisioning rule. Start three `provision` runs:

```bash
gh workflow run provision.yml
gh workflow run provision.yml
gh workflow run provision.yml
```

Reject each one at the gate: open the run, select **Review deployments**,
select `production` and then **Reject**. A rejected job fails the run
([GitHub Docs](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)).
Check that all three failed:

```bash
gh run list --workflow provision.yml --limit 3
```

The email arrives after the next hourly query. To reset the streak, start
one more run and approve it. If `production` has **Prevent self-review**
turned on, someone else must approve a run you started
([GitHub Docs](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)).
Then close the seed issue.

### Task 9 — Answer audit questions from chat

In a Copilot CLI session:

```text
/eventhouse-cli In KQL database "eh_gov_audit" of workspace "dev-plt-gov-audit", which pull requests merged in the last 30 days had no approving review, and who merged them?
```

Expect an anti-join: the `merged_prs()` rows with no `pr_reviews()` row in
state `approved` for the same repo and number. Then ask in the same session:

- What's the weekly median, in hours, from a pull request opening to the
  successful `provision` run on its merge commit? `pr_events()` has
  `created_at` and `merge_sha`, and `provision_runs()` has `head_sha`.
- Which items did a person, not a service principal, change in the last
  7 days, and in which environment? Join `item_changes()` to
  `workspace_envs()` on `workspaceId`. Production items change through the
  promotion workflow, so a person's change in a `prd` workspace deserves a
  look once `es_fabric_items` watches one.
- Who read files in `dev-plt-myteam-playground` in the last 7 days? Query
  `external_table('onelake_access')` for `operationCategory` Read, join it
  to `workspace_envs()` on `workspaceId` and group by `executingUPN` and
  `operationName`.

A `FabricWorkloadAccess` row records only that a Fabric engine was granted
temporary access. What the engine read is in its own logs
([Learn](https://learn.microsoft.com/fabric/onelake/onelake-diagnostics-overview)).

Compare live roles with the snapshot. In a Copilot CLI session with the
Fabric Core MCP connected:

```text
List the role assignments of workspace "dev-plt-myteam-playground".
```

Then, in a Copilot CLI session:

```text
/eventhouse-cli In KQL database "eh_gov_audit" of workspace "dev-plt-gov-audit", run role_assignments() | where name == "dev-plt-myteam-playground".
```

The snapshot is up to a day old, so a role changed since the last export
shows up only in the live answer.

## Success criteria

- [ ] `dev-plt-gov-audit` exists from a merged pull request, with your group
      as Admin, you as Member and the SPN as Admin.
- [ ] `items/dev-plt-gov-audit/eh_gov_audit.kql` is in Git, and rerunning it
      succeeds.
- [ ] A pull request on your fork shows up in `pr_events()`, and an unsigned
      post to the relay returns 401.
- [ ] The notebook you created and deleted in Task 4 shows up in
      `item_changes()` as a create and a delete.
- [ ] After an `audit-export` run, `activity()` and `workspace_snapshots()`
      return rows, and `workspace_envs()` shows each managed workspace with
      its manifest's environment.
- [ ] `onelake_access` returns reads from `dev-plt-myteam-playground` within
      about an hour.
- [ ] The model and the report are in Git as a PBIP project, the report has
      five pages, and its Drift page shows open issues, the oldest open age
      and nights with drift.
- [ ] `act_gov_alerts` has four rules, and the three rejected `provision`
      runs sent an email within the hour.
- [ ] You answered the Task 9 questions from chat, and the Core MCP's roles
      for `dev-plt-myteam-playground` match `role_assignments()` as of the
      last export.

## Stretch goals

- **Search Purview Audit.** Audit (Standard) keeps Fabric activity for
  180 days; the activity events API serves only 28. Searching needs the
  Audit Logs role in Exchange Online, which the Compliance Management and
  Organization Management role groups have by default
  ([Learn](https://learn.microsoft.com/fabric/admin/track-user-activities),
  [Learn](https://learn.microsoft.com/purview/audit-solutions-overview)).
- **Query the audit log with Microsoft Graph.**
  `POST /security/auditLog/queries` (v1.0) runs the same search from code.
  Filter on the record type `powerBIAudit` and grant
  `AuditLogsQuery.Read.All`; no Power BI-specific permission exists
  ([Learn](https://learn.microsoft.com/graph/api/security-auditcoreroot-post-auditlogqueries?view=graph-rest-1.0)).
- **Make the diagnostic logs immutable.** The Core MCP
  `onelake_modify_immutability_policy` tool sets how long OneLake diagnostic
  files can't be changed or deleted. The policy can't be changed once set,
  and deleting a file inside the period fails with HTTP 409. Storage keeps
  growing, so plan a cleanup that skips files still in their period.
  Immutability doesn't stop an admin from deleting the lakehouse or its
  workspace, and deleting a watched workspace deletes its diagnostics, so
  keep both admin lists short. Changes to the diagnostic settings are
  audited as `ModifyOneLakeDiagnosticSettings`
  ([Learn](https://learn.microsoft.com/fabric/onelake/onelake-diagnostics-overview)).
- **Spot unusual activity.** Count `activity()` events per day and flag
  outliers with `series_decompose_anomalies`
  ([Learn](https://learn.microsoft.com/kusto/query/series-decompose-anomalies-function?view=microsoft-fabric)).

## MCP tips

- The Core MCP tools in this challenge are `list_workspace_roles` (Tasks 1
  and 9), `create_item` (Tasks 2 and 6), `list_items` (Tasks 2 and 7),
  `get_item_definition` (Task 2), and `onelake_modify_diagnostics` and
  `onelake_get_settings` (Task 6)
  ([Learn](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)).
- No Core MCP tool covers admin APIs, so `audit_export.py` calls them as the
  SPN.
- `get_item_definition` shows what Fabric holds. Compare it with Git to find
  changes made outside a pull request.
- Use chat to look, and pull requests to change.

## Skills tips

- `/eventhouse-cli` runs management scripts and queries in an existing KQL
  database. It doesn't create the Eventhouse; Task 2 uses the Core MCP.
- `/eventstream-cli` needs the KQL database's item ID for an Eventhouse
  destination.
- `/semantic-model-authoring` builds Import models unless you ask for
  DirectQuery. Without the Power BI modeling MCP server it writes TMDL and
  deploys over REST. Its deploy isn't idempotent, so deploy once. It stops on
  a credentials error for you to fix in the service. Saving as PBIP also
  writes a placeholder report.
- `/powerbi-report-cli` works on a local model. It writes its plan to
  `_brief/report-spec.md` and waits for approval, screenshots every page and
  publishes only when you ask. At publish it asks whether to publish the
  model too or connect to an existing one, and it rewrites `definition.pbir`.
- `/activator-cli` needs the workspace ID and the KQL database's item ID, and
  checks that each source returns rows. It uses a time axis when the rows
  have a timestamp; ask for snapshot mode when they hold current state. It
  builds one stream unless you ask for objects, and it prefers change
  conditions, which fire on a crossing.

## Repository files

- [`.github/workflows/provision.yml`](../../.github/workflows/provision.yml):
  you approve its runs in Tasks 1 and 5, and in Task 8 you reject three and
  approve one.
- [`.github/workflows/drift.yml`](../../.github/workflows/drift.yml): opens
  the drift issues on the Task 7 Drift page.
- [`scripts/_fabric.py`](../../scripts/_fabric.py): the token helper that
  `audit_export.py` imports in Task 5.
- [`scripts/requirements.txt`](../../scripts/requirements.txt): Task 5 adds
  `azure-eventhub`.
- [`.gitignore`](../../.gitignore): Task 7 adds the PBIP local files.
- New in this challenge: `workspaces/dev-plt-gov-audit.yaml`,
  `items/dev-plt-gov-audit/eh_gov_audit.kql`, the PBIP project in
  `items/dev-plt-gov-audit/`, `relay/function_app.py`,
  `relay/requirements.txt`, `scripts/audit_export.py` and
  `.github/workflows/audit-export.yml`.

## References

- [Create an eventhouse](https://learn.microsoft.com/fabric/real-time-intelligence/create-eventhouse)
- [Add a custom endpoint or custom app source to an eventstream](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/add-source-custom-app)
- [Connect to Eventstream using Microsoft Entra ID authentication](https://learn.microsoft.com/fabric/real-time-intelligence/event-streams/custom-endpoint-entra-id-auth)
- [Explore Fabric workspace item events in Real-Time hub](https://learn.microsoft.com/fabric/real-time-hub/explore-fabric-workspace-item-events)
- [Subscribe permission for Azure and Fabric events](https://learn.microsoft.com/fabric/real-time-hub/fabric-events-subscribe-permission)
- [Track user activities in Microsoft Fabric](https://learn.microsoft.com/fabric/admin/track-user-activities)
- [Operation list](https://learn.microsoft.com/fabric/admin/operation-list)
- [Get Activity Events (REST)](https://learn.microsoft.com/rest/api/power-bi/admin/get-activity-events)
- [List Workspaces (admin REST)](https://learn.microsoft.com/rest/api/fabric/admin/workspaces/list-workspaces)
- [OneLake diagnostics](https://learn.microsoft.com/fabric/onelake/onelake-diagnostics-overview)
- [KQL Database item definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/kql-database-definition)
- [Access an existing KQL database](https://learn.microsoft.com/fabric/real-time-intelligence/access-database-copy-uri)
- [Create and alter Azure Storage external tables](https://learn.microsoft.com/kusto/management/external-tables-azure-storage?view=microsoft-fabric)
- [Power BI Desktop projects (PBIP)](https://learn.microsoft.com/power-bi/developer/projects/projects-overview)
- [Configure scheduled refresh](https://learn.microsoft.com/power-bi/connect-data/refresh-scheduled-refresh)
- [What is Fabric Activator?](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-introduction)
- [Activator ingestion from KQL Querysets](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/ingestion/ingestion-kql-querysets)
- [Detection settings in Activator](https://learn.microsoft.com/fabric/real-time-intelligence/data-activator/activator-detection-conditions)
- [Core MCP server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Learn about auditing solutions in Microsoft Purview](https://learn.microsoft.com/purview/audit-solutions-overview)
- [Create auditLogQuery (Microsoft Graph)](https://learn.microsoft.com/graph/api/security-auditcoreroot-post-auditlogqueries?view=graph-rest-1.0)
- [series_decompose_anomalies()](https://learn.microsoft.com/kusto/query/series-decompose-anomalies-function?view=microsoft-fabric)
- [Create a function in Azure from the command line](https://learn.microsoft.com/azure/azure-functions/how-to-create-function-azure-cli?pivots=programming-language-python)
- [Use Key Vault references as app settings](https://learn.microsoft.com/azure/app-service/app-service-key-vault-references)
- [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries)
- [Creating webhooks](https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks)
- [Reviewing deployments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
- [Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
