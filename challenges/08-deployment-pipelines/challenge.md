# Challenge 08 — Deployment pipelines & cross-environment promotion

> **Outcome:** a merged PR reaches `stg-fin-revenue`, then `prd-fin-revenue`,
> only through the `finance-revenue` deployment pipeline. A label on the merged
> PR starts each promotion, and prd also needs an approval and proof that stg
> holds the same merge. A rollback is a revert of the merge, promoted the same
> way.

## Why this challenge exists

Copying items between workspaces by hand leaves no review, no audit trail and
no way back. This challenge gives the finance revenue gold layer one route to
production. Only `dev-fin-revenue` connects to Git, and it changes only through
PRs to `main`. Feature work happens in a branched workspace,
`sbx-fin-revenue-feature`, which is never promoted. `stg-fin-revenue` and
`prd-fin-revenue` get content only from the deployment pipeline. dev and stg
run on `contosononprodf2`, and prd runs on `contosoprodf4`.

Fabric has no workspace snapshot to restore. A deploy copies item definitions,
not data, so Git is the history, and a rollback is a revert that you promote
like any other change.

## Learning objectives

1. Connect only `dev-fin-revenue` to Git, change it only through PRs, and do
   feature work in a branched sandbox that's never promoted.
2. Declare the pipeline in `pipelines/finance-revenue.yaml` and validate it
   before merge, with production rules keyed on the manifests' `environment`
   field.
3. Promote a merged PR with a label, signing in with OIDC through a `staging`
   and a `production` environment, and prove that stg holds the same merge
   before prd gets it.
4. Point the semantic model in each stage at its own lakehouse with a
   parameter rule that a stage admin owns.
5. Roll back by reverting the merge, and state what a revert can't undo.
6. Check each stage from chat with the Fabric Core MCP, and run Git and
   pipeline operations with the `git-integration-operations-cli` and
   `deployment-pipelines-authoring-cli` Skills.
7. Tell what Git and a deploy carry from what each stage keeps, set the
   active value set of each stage's variable library with the
   `variable-library-cli` Skill, and give each stage one deploy route.

## Prerequisites

- Challenges [00](../00-setup/challenge.md),
  [01](../01-workspace-as-code/challenge.md) and
  [05](../05-medallion-bootstrap/challenge.md) complete. The SPN's group,
  `sg-fabric-workspace-provisioner`, is enabled in the four tenant settings
  from challenge 00:
  - Service principals can create workspaces, connections, and deployment pipelines
  - Service principals can call Fabric public APIs
  - Service principals can access read-only admin APIs
  - Service principals can access admin APIs used for updates

  For new customers, the first setting is off by default
  ([Learn](https://learn.microsoft.com/fabric/admin/service-admin-portal-developer#service-principals-can-create-workspaces-connections-and-deployment-pipelines))
  and the second is on
  ([Learn](https://learn.microsoft.com/fabric/admin/service-admin-portal-developer#service-principals-can-call-fabric-public-apis)).
  A Fabric administrator finds them in OneLake catalog > Govern >
  Configurations > Tenant settings
  ([Learn](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis#enable-service-principal-authentication)).
  Where Govern hasn't rolled out yet, use Settings > Admin portal > Tenant
  settings
  ([Learn](https://learn.microsoft.com/fabric/admin/about-tenant-settings#how-to-get-to-the-tenant-settings)).
- The same administrator enables these settings for the people who connect,
  update and branch out from dev
  ([Learn](https://learn.microsoft.com/fabric/admin/git-integration-admin-settings)):
  - Users can create Fabric items
  - Users can synchronize workspace items with their Git repositories
  - Users can sync workspace items with GitHub repositories
  - Users can export workspace items with applied sensitivity labels to Git repositories
  - Create workspaces, which branching out to a new workspace needs
    ([Learn](https://learn.microsoft.com/fabric/cicd/git-integration/git-get-started#fabric-prerequisites))
- The SPN isn't a Fabric administrator or a capacity admin, has no
  admin-consent required permissions for Fabric or Power BI
  ([Learn](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis#how-to-check-if-your-app-has-admin-consent-required-permissions))
  and isn't in any label publishing policy.
  It has Contributor permissions on both capacities and is Admin of
  `dev-fin-revenue`, `stg-fin-revenue` and `prd-fin-revenue`. It becomes an
  admin of the pipeline by creating it.
- The stage admin groups, `grp_fabric_stg_fin_admin` and
  `grp_fabric_prd_fin_admin`, are security groups. Microsoft 365 groups can't
  be pipeline admins.
- From 2027-02-28, users without read and write permission on a workspace's
  items can't use Git integration on it
  ([Learn](https://learn.microsoft.com/fabric/cicd/git-integration/git-integration-process#permissions)).
  From the same date, in a workspace whose items carry sensitivity labels with
  protection policies, users also need read and write permission on all its
  items to deploy to it or assign it to certain pipeline stages
  ([Learn](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/understand-the-deployment-process#permissions)).
  Today, protection policies don't integrate with Fabric CI/CD: deployment
  pipelines and Git integration use only workspace permissions
  ([Learn](https://learn.microsoft.com/fabric/governance/protection-policies-overview#considerations-and-limitations)).
  If a protection policy covers these workspaces, see the protection policy
  stretch goal before 2027-02-28.
- Challenge 00's GitHub Enterprise Cloud organization supports branch limits
  and required reviewers on environments in private repositories
  ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments#deployment-branches-and-tags)).
- A manifest for each stage from challenge 01.
  `workspaces/prd-fin-revenue.yaml`:

  ```yaml
  name: prd-fin-revenue
  environment: prd
  team: fin
  domain: dom-fin-corp
  subDomain: sdm-fin-rev
  description: "Production gold layer for finance revenue reporting, promoted from stg."
  capacity: contosoprodf4
  region: northeurope
  sensitivityLabel: Confidential
  costCenter: CC-2042
  owners:
    - principalType: Group
      identifier: 77777777-7777-7777-7777-777777777777
      role: Admin
      groupName: grp_fabric_prd_fin_admin
    - principalType: Group
      identifier: 99999999-9999-9999-9999-999999999999
      role: Member
      groupName: grp_fabric_prd_fin_member
  ```

  `dev-fin-revenue.yaml` and `stg-fin-revenue.yaml` have the same fields, with
  `environment: dev` or `stg`, `capacity: contosononprodf2`, and their own
  description and owner groups. stg's Admin owner is
  `grp_fabric_stg_fin_admin` (`88888888-8888-8888-8888-888888888888`).
- `dev-fin-revenue` holds the gold layer: `lh_gold_revenue`, `sm_gold_revenue`
  and `rpt_gold_revenue`. `sm_gold_revenue` is a Direct Lake on OneLake model
  over the lakehouse, and `rpt_gold_revenue` is a report on the model. Create
  any of them that challenge 05 didn't.
- If the tenant setting Block republish and disable package refresh is on,
  only a model's owner can update it. That can block the SPN's deploys after a
  stage admin takes over `sm_gold_revenue` in Task 6, so check the setting
  with your Fabric administrator first.
- For Task 9, three ADLS Gen2 storage accounts, one per stage, such as
  `stcontosofindev`, `stcontosofinstg` and `stcontosofinprd`, each with a
  `reference` container holding FX rate files under `fx-rates/`. Create a
  Fabric cloud connection to each in Settings > Manage connections and
  gateways, and note their IDs. Give the SPN the User role on all three:
  binding a shortcut to a connection needs permission on it, and the SPN
  deploys the shortcut to every stage.
- The Fabric Core MCP server and Skills for Fabric, installed as shown below.

To install the Core MCP server and the Skills, run from a terminal:

```bash
copilot mcp add --transport http fabric https://api.fabric.microsoft.com/v1/mcp/core
copilot plugin marketplace add microsoft/skills-for-fabric
copilot plugin install fabric-skills@fabric-collection
```

In a Copilot CLI session, `/mcp add` adds the server too.

## Tasks

### Task 1 — Connect dev to Git

Fabric commits straight to the branch a workspace is connected to, so connect
dev to a seed branch first. Branch protection on `main` would block those
commits.

1. Create the seed branch from a clone of this repository:

   ```bash
   git fetch origin
   git switch -c init/fin-revenue origin/main
   git push -u origin init/fin-revenue
   ```

2. Create a fine-grained personal access token for this repository with read
   and write access to Contents. Fabric uses it to commit and update.

   > **Preview** (checked 2026-11-27): Semantic models in Git integration — [Learn](https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration#supported-items). GA route: export `sm_gold_revenue` with Get Item Definition, commit it, and publish it and its reports to each stage with fabric-cicd.

3. In `dev-fin-revenue`, open Workspace settings > Git integration, select
   GitHub and add the token. Choose this repository, branch `init/fin-revenue`
   and Git folder `fabric/finance-revenue`, then select Connect and sync. The
   folder is empty, so the initial sync copies dev's items into it. Each item
   gets a `<display name>.<type>` folder with a `.platform` file that records
   its type and display name.
4. Let each stage point the model at its own lakehouse. Deployment pipelines
   have no data source rules for Direct Lake on OneLake models, so use a
   parameter
   ([Learn](https://learn.microsoft.com/fabric/fundamentals/direct-lake-develop#use-m-parameters-with-deployment-pipelines)).
   Live edit `sm_gold_revenue` in Power BI Desktop: open the OneLake catalog,
   select the model, and choose Connect > Edit
   ([Learn](https://learn.microsoft.com/fabric/fundamentals/direct-lake-power-bi-desktop#live-edit-a-semantic-model-with-direct-lake)).
   Open TMDL view and drag Expressions from the Model tab into the editor to
   script the shared expression that holds the `AzureStorage.DataLake`
   connection
   ([TMDL view](https://learn.microsoft.com/power-bi/transform-model/desktop-tmdl-view),
   [Direct Lake in Power BI Desktop](https://learn.microsoft.com/fabric/fundamentals/direct-lake-power-bi-desktop#tmdl-view)).
   Add this parameter at the same indentation as that expression:

   ```tmdl
   expression OneLakeSourceUrl = "https://onelake.dfs.fabric.microsoft.com/<workspace-id>/<item-id>" meta [IsParameterQuery = true, IsParameterQueryRequired = true, Type = "Text"]
   ```

   Use dev's workspace ID and the lakehouse's item ID, not the ID of its SQL
   analytics endpoint. In the existing Direct Lake expression, replace the
   quoted URL with the parameter, for example
   `AzureStorage.DataLake(OneLakeSourceUrl, [HierarchicalNavigation = true])`
   ([Learn](https://learn.microsoft.com/fabric/fundamentals/direct-lake-develop#power-query-connectors)).
   Keep the expression's name, annotations and any other connection options
   unchanged. Apply the change, then commit it from dev's Source control pane.

   Live editing needs Power BI Desktop on Windows, the XMLA endpoint enabled
   for the tenant, XMLA read-write on the capacity, Write on the model, Viewer
   on the lakehouse and a paid license
   ([Direct Lake in Power BI Desktop](https://learn.microsoft.com/fabric/fundamentals/direct-lake-power-bi-desktop#requirements-and-permissions),
   [Get Power BI Desktop](https://learn.microsoft.com/power-bi/fundamentals/desktop-get-the-desktop#minimum-requirements),
   [Edit data models in the Power BI service](https://learn.microsoft.com/power-bi/transform-model/service-edit-data-models#limitations)).
   Capacities default to read-only, so a capacity admin sets the capacity's
   XMLA Endpoint workload setting to Read Write
   ([Learn](https://learn.microsoft.com/fabric/enterprise/powerbi/service-premium-connect-tools#enable-xmla-read-write)).

   > **Preview** (checked 2026-11-27): TMDL view on the web — [Learn](https://learn.microsoft.com/power-bi/transform-model/desktop-tmdl-view#tmdl-view-in-power-bi-service-preview). GA route: live edit in Power BI Desktop, as in this step.

   Without Windows, make the same change in TMDL view on the web: open the
   model from the workspace and select TMDL View (Preview). It needs semantic
   model editing turned on in the admin portal and Write on the model
   ([Learn](https://learn.microsoft.com/power-bi/transform-model/service-edit-data-models#enabling-semantic-model-editing-in-the-admin-portal),
   [Permissions](https://learn.microsoft.com/power-bi/transform-model/service-edit-data-models#permissions)).
5. Open the PR, review it and merge it:

   ```bash
   gh pr create --base main --head init/fin-revenue --fill
   ```

   Then a workspace Admin uses Switch branch in dev's Source control pane to
   move dev to `main`. From now on, dev changes only when someone updates it
   from `main`.
6. For feature work, a developer selects Branch out in dev's Source control
   pane and creates a new workspace, `sbx-fin-revenue-feature`, on a new
   branch, `feature/fin-revenue-margin`. They commit there and open a PR to
   `main`. The sandbox has no manifest, so `drift.py` reports it as unmanaged.
   Delete it once its PR merges.

### Task 2 — Declare the pipeline

Create `pipelines/finance-revenue.yaml`. It names the stages, the groups that
administer the pipeline and the items a promotion deploys:

```yaml
name: finance-revenue
description: "Promotes the finance revenue gold layer from dev to stg to prd."
gitFolder: fabric/finance-revenue
admins:
  - principalType: Group
    identifier: 88888888-8888-8888-8888-888888888888
    groupName: grp_fabric_stg_fin_admin
  - principalType: Group
    identifier: 77777777-7777-7777-7777-777777777777
    groupName: grp_fabric_prd_fin_admin
stages:
  - name: dev
    workspace: dev-fin-revenue
  - name: stg
    workspace: stg-fin-revenue
    promotionLabel: promote/stg
    githubEnvironment: staging
  - name: prd
    workspace: prd-fin-revenue
    promotionLabel: promote/prd
    githubEnvironment: production
items:
  - type: Lakehouse
    pattern: "^lh_gold_revenue$"
  - type: SemanticModel
    pattern: "^sm_gold_revenue$"
  - type: Report
    pattern: "^rpt_gold_revenue[a-z0-9_]*$"
```

`promote.py` adds both groups as pipeline admins, and each is Admin of its
stage's workspace through its manifest. `githubEnvironment` names the GitHub
environment that gates the stage.

Add `schemas/pipeline.schema.json` (JSON Schema draft 2020-12). It requires the
fields above, rejects any others and enforces:

- three stages, named dev, stg and prd in that order, with workspaces that
  start with `dev-`, `stg-` or `prd-`
- admins with `principalType: Group` and a GUID `identifier`
- a `promotionLabel` that matches `^promote/(stg|prd)$` and a
  `githubEnvironment` of `staging` or `production`
- an item `type` of `Lakehouse`, `SemanticModel` or `Report`

The `*` rule in `.github/CODEOWNERS` already sends `pipelines/` to the
maintainers. If a security team approves production changes, add it too:

```text
/pipelines/  @your-org/fabric-governance-maintainers @your-org/fabric-security
```

### Task 3 — Validate the pipeline before merge

Add `check_pipelines(manifests)` to `scripts/validate.py`. It reads every
`pipelines/*.yaml` file and returns a `FileResult` for each, with a blocking
finding for each rule it breaks:

| Rule | Blocks when |
|---|---|
| `pipeline-schema` | the file doesn't match `schemas/pipeline.schema.json` |
| `pipeline-stage-order` | the stages aren't dev, stg and prd in that order, or a workspace's prefix differs from its stage |
| `pipeline-stage-manifest` | a stage's workspace has no manifest, or the manifest's `environment` differs from the stage name |
| `pipeline-prd-gate` | the stage whose manifest has `environment: prd` doesn't use `promote/prd` and `production` |
| `pipeline-item-pattern` | a pattern matches no item under `gitFolder`, by the `.platform` file's `metadata.type` and `metadata.displayName` or by the `<name>.<Type>` folder |

Call it in `main()`, just before `render_markdown`:

```python
results.extend(check_pipelines(all_workspace_files()))
```

Then add `'pipelines/**'` and `'fabric/**'` to the `paths` in
`.github/workflows/validate.yml`, so renaming an item in dev also runs the
check.

### Task 4 — Labels, environments and `promote.yml`

1. Anyone with write access to the repository creates the labels:

   ```bash
   gh label create promote/stg --color 1D76DB --description "Deploy this merged PR from dev to stg"
   gh label create promote/prd --color B60205 --description "Deploy this merged PR from stg to prd after approval"
   ```

2. A repository admin, or the owner of a personal repository, creates the
   `staging` environment and limits its deployments to `main`
   ([Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments#creating-an-environment)):

   ```bash
   repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
   gh api --method PUT "repos/$repo/environments/staging" -F 'deployment_branch_policy[protected_branches]=false' -F 'deployment_branch_policy[custom_branch_policies]=true'
   gh api --method POST "repos/$repo/environments/staging/deployment-branch-policies" -f name=main -f type=branch
   ```

   Without a branch limit, a workflow on any branch could use `staging` and
   sign in with its federated credential. `promote.yml` still runs, because a
   `pull_request_target` run's `GITHUB_REF` is the default branch, and branch
   rules match `GITHUB_REF`
   ([Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments#deployment-branches-and-tags),
   [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target)).
3. An owner of the `gh-fabric-workspace-provisioner` app registration, or an
   Application Administrator or Cloud Application Administrator, adds the
   `staging` federated credential from a clone of the repository
   ([Learn](https://learn.microsoft.com/graph/api/federatedidentitycredential-post?view=graph-rest-1.0#permissions)).
   It reuses the subject prefix of challenge 00's `production` credential:

   ```bash
   app_id=$(gh variable get AZURE_CLIENT_ID)
   prefix=$(az ad app federated-credential list --id "$app_id" --query "[?ends_with(subject, ':environment:production')].subject | [0]" -o tsv)
   prefix=${prefix%:environment:production}
   echo "$prefix"
   ```

   Check that the echoed prefix names your repository.

   ```bash
   az ad app federated-credential create --id "$app_id" --parameters '{"name":"github-staging","issuer":"https://token.actions.githubusercontent.com","subject":"'"${prefix:?Run challenge 00 first}"':environment:staging","audiences":["api://AzureADTokenExchange"]}'
   ```

   GitHub issues immutable subjects,
   `repo:<owner>@<owner-id>/<repo>@<repo-id>:…`, for repositories created,
   renamed or transferred after 2026-07-15, and challenge 00 creates a new
   repository. A subject built from the repository's name alone drops the
   IDs, so the stg sign-in would fail with `AADSTS700213`. Reusing
   production's prefix keeps whichever format challenge 00 used
   ([OpenID Connect](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims)).
   An app registration holds at most 20 federated credentials
   ([Learn](https://learn.microsoft.com/entra/workload-id/workload-identity-federation-considerations#general-federated-identity-credential-considerations)).

   The `production` environment, with its required reviewers, `main` limit
   and federated credential, comes from challenge 00.
4. Create `.github/workflows/promote.yml`:

   ```yaml
   name: promote

   on:
     pull_request_target:
       types: [labeled]

   permissions:
     contents: read
     id-token: write
     pull-requests: write

   concurrency:
     group: ${{ (github.event.label.name == 'promote/stg' || github.event.label.name == 'promote/prd') && 'promote-finance-revenue' || format('promote-skip-{0}', github.run_id) }}
     cancel-in-progress: false
     queue: max

   jobs:
     promote:
       if: >-
         github.event.pull_request.merged == true &&
         (github.event.label.name == 'promote/stg' || github.event.label.name == 'promote/prd')
       runs-on: [self-hosted, fabric-gov]
       environment: ${{ github.event.label.name == 'promote/prd' && 'production' || 'staging' }}
       timeout-minutes: 60
       env:
         TARGET: ${{ github.event.label.name == 'promote/prd' && 'prd' || 'stg' }}
         MERGE_SHA: ${{ github.event.pull_request.merge_commit_sha }}
         PR_NUMBER: ${{ github.event.pull_request.number }}
         GITHUB_TOKEN: ${{ github.token }}
       steps:
         - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
           with:
             persist-credentials: false

         - name: Setup Python venv
           run: |
             python3 -m venv .venv
             .venv/bin/pip install --quiet --upgrade pip
             .venv/bin/pip install --quiet -r scripts/requirements.txt
             echo "$GITHUB_WORKSPACE/.venv/bin" >> $GITHUB_PATH

         - name: Azure login (OIDC)
           uses: azure/login@7ddb5af1ef8758cf1353cf3b42f940aee27ba21c # v3.0.2
           with:
             client-id: ${{ vars.AZURE_CLIENT_ID }}
             tenant-id: ${{ vars.AZURE_TENANT_ID }}
             allow-no-subscriptions: true

         - name: Promote
           run: python scripts/promote.py

         - name: Comment on the PR
           if: always() && hashFiles('promotion-report.md') != ''
           uses: marocchino/sticky-pull-request-comment@5770ad5eb8f42dd2c4f34da00c94c5381e49af88 # v3.0.5
           with:
             header: promotion-${{ env.TARGET }}
             path: promotion-report.md
   ```

`pull_request_target` runs the workflow and scripts from `main`, with OIDC and
a write token, so never check out the PR's head. The merged change is already
on `main`.

Anyone with triage access can add a label, so the `production` environment's
required reviewers are the gate for prd. To run a promotion again, remove the
label and add it back. Promotions share one concurrency group and run one at a
time. With `queue: max`, up to 100 promotions wait their turn instead of being
canceled. Runs started by other labels get their own group, so they can't take
a promotion's place. A prd run that waits for approval can hold the group, so
approve or reject it promptly. Waiting runs usually start in the order they
began waiting, but GitHub doesn't guarantee that order
([Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)).

### Task 5 — Write `promote.py`

Create `scripts/promote.py`. It deploys only the items the pipeline file
declares, refuses prd unless stg holds the same merge, and writes
`promotion-report.md` for the PR comment. It uses `_request`, `_paged` and
`AuthError` from `scripts/_fabric.py`, and exits with code 3 on a 401 or 403,
like `provision.py`.

```python
"""Promote a merged PR through the finance-revenue deployment pipeline."""
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import _fabric as fab  # noqa: E402

PIPELINE_FILE = Path("pipelines/finance-revenue.yaml")
REPORT = Path("promotion-report.md")
MAX_ITEMS = 300
SOURCE = {"stg": "dev", "prd": "stg"}
MARKER = re.compile(
    r"<!-- promote target=stg result=Succeeded sha=(\w+) operation=([\w-]+) -->")


class GateError(RuntimeError):
    """The promotion is blocked."""


def bind_stages(spec: dict) -> tuple[str, dict[str, str]]:
    """Find or create the pipeline and assign each stage's workspace.

    Returns the pipeline ID and a map from stage name to stage ID."""
    raise NotImplementedError("Task 5, step 1")


def ensure_admins(pipeline_id: str, admins: list[dict]) -> None:
    """Add each admin group as a pipeline Admin if it isn't one."""
    raise NotImplementedError("Task 5, step 2")


def select_items(pipeline_id: str, stage_id: str, patterns: list[dict]) -> list[dict]:
    """The source stage's items that the pipeline file declares."""
    url = f"{fab.FABRIC_BASE}/deploymentPipelines/{pipeline_id}/stages/{stage_id}/items"
    chosen = [{"sourceItemId": i["itemId"], "itemType": i["itemType"]}
              for i in fab._paged(url)
              if any(p["type"] == i["itemType"]
                     and re.fullmatch(p["pattern"], i["itemDisplayName"])
                     for p in patterns)]
    if not 0 < len(chosen) <= MAX_ITEMS:
        raise GateError(f"{len(chosen)} items match; a deploy takes 1 to {MAX_ITEMS}")
    return chosen


def newest_deploy(pipeline_id: str, stage_id: str) -> dict | None:
    """The latest deploy into a stage, from the 20 most recent operations."""
    url = f"{fab.FABRIC_BASE}/deploymentPipelines/{pipeline_id}/operations"
    deploys = [o for o in fab._paged(url)
               if o.get("type") == "Deploy" and o.get("targetStageId") == stage_id]
    return max(deploys, key=lambda o: o.get("executionStartTime", ""), default=None)


def require_stg_evidence(pr: str, sha: str, pipeline_id: str, stg_id: str) -> None:
    """Pass only if stg's newest deploy is this merge's successful stg promotion."""
    repo = os.environ["GITHUB_REPOSITORY"]
    r = requests.get(f"https://api.github.com/repos/{repo}/issues/{pr}/comments",
                     headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                              "Accept": "application/vnd.github+json"},
                     params={"per_page": 100}, timeout=30)
    r.raise_for_status()
    operations = [m.group(2) for c in r.json()
                  if c["user"]["login"] == "github-actions[bot]"
                  for m in MARKER.finditer(c["body"]) if m.group(1) == sha]
    if not operations:
        raise GateError("this merge hasn't reached stg; add promote/stg first")
    newest = newest_deploy(pipeline_id, stg_id)
    if not newest or newest["id"] != operations[-1] or newest.get("status") != "Succeeded":
        raise GateError("stg changed since this PR was promoted; promote/stg again")


def deploy(pipeline_id: str, source_id: str, target_id: str,
           items: list[dict], note: str) -> tuple[str, dict]:
    """Deploy the items, wait for the operation, and return the deploy's ID and final state."""
    r = fab._request("POST", f"{fab.FABRIC_BASE}/deploymentPipelines/{pipeline_id}/deploy",
                     json={"sourceStageId": source_id, "targetStageId": target_id,
                           "items": items, "note": note}, expect=(200, 202))
    if r.status_code == 200:
        state = r.json()
        return state["id"], state
    deployment_id = r.headers["deployment-id"]
    operation = r.headers["x-ms-operation-id"]
    while True:
        time.sleep(int(r.headers.get("Retry-After", 20)))
        r = fab._request("GET", f"{fab.FABRIC_BASE}/operations/{operation}")
        state = r.json()
        if state["status"] not in ("NotStarted", "Running"):
            return deployment_id, state


def main() -> int:
    target, sha, pr = os.environ["TARGET"], os.environ["MERGE_SHA"], os.environ["PR_NUMBER"]
    lines = [f"## Promotion to {target}", ""]
    try:
        spec = yaml.safe_load(PIPELINE_FILE.read_text())
        pipeline_id, stages = bind_stages(spec)
        ensure_admins(pipeline_id, spec["admins"])
        if target == "prd":
            require_stg_evidence(pr, sha, pipeline_id, stages["stg"])
        source = SOURCE[target]
        items = select_items(pipeline_id, stages[source], spec["items"])
        deployment_id, state = deploy(pipeline_id, stages[source], stages[target],
                                      items, f"PR #{pr} merge {sha}")
        lines.append(f"Deployed {len(items)} items from {source} to {target}: "
                     f"{state['status']}.")
        if state["status"] != "Succeeded":
            lines.append(f"Error: {state.get('error')}")
            return 1
        if target == "stg":
            lines += ["", f"<!-- promote target=stg result=Succeeded sha={sha} "
                          f"operation={deployment_id} -->"]
        return 0
    except fab.AuthError as e:
        lines.append(f"Stopped on a permission error: {e}")
        return 3
    except GateError as e:
        lines.append(f"Blocked: {e}")
        return 1
    finally:
        REPORT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
```

1. Complete `bind_stages()`. Find the pipeline by display name with List
   Deployment Pipelines, or create it with stages `dev`, `stg` and `prd`. Look
   up each workspace with `fab.get_workspace_by_name` and assign it to its
   stage if it isn't assigned yet.
2. Complete `ensure_admins()`. Add each group in `admins` as a pipeline Admin
   with Add Deployment Pipeline Role Assignment if it isn't one already.

The deploy note goes to the pipeline's history in the portal, but the gate
doesn't read it back. The PR comment holds the evidence: after a successful stg
deploy, it records the merge and the ID of this run's deploy (the
`deployment-id` header, or `id` when the deploy answers 200). A prd run passes
only if that deploy is still stg's newest. After your first stg promotion,
check once that the recorded ID matches that deploy's `id` in List Deployment
Pipeline Operations, which Task 8 step 3 lists.

### Task 6 — Promote a change

1. In `sbx-fin-revenue-feature`, add a measure to `sm_gold_revenue`, commit it
   to `feature/fin-revenue-margin` from the Source control pane, and open a PR
   to `main`. Merge it after review.
2. Update dev from `main`. In a Copilot CLI session:

   ```text
   /git-integration-operations-cli Update dev-fin-revenue from Git and show me the Git status before and after.
   ```

   If the update fails with `WorkspaceHeadMismatch`, dev changed after the
   status call. Ask the Skill to read the status again and retry.

   > **Preview** (checked 2026-11-27): Semantic models in deployment pipelines — [Learn](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines#supported-items). GA route: promote the lakehouse with the pipeline, and publish `sm_gold_revenue` and its reports to each stage from Git with fabric-cicd.

3. Add the stg label to the merged PR:

   ```bash
   PR=42
   gh pr edit "$PR" --add-label promote/stg
   ```

   The first deploy creates the three items in stg. Until a rule is set, the
   new model still points at dev's lakehouse.

   This run also assigns the workspaces to their stages. The first deploy
   after a workspace is assigned can fail with
   `Alm_InvalidRequest_WorkloadUnavailable`. Wait 60 to 120 seconds, then
   remove the label and add it back.
4. A member of `grp_fabric_stg_fin_admin` takes over `sm_gold_revenue` in
   `stg-fin-revenue`, because only an item's owner can create rules for it:
   they open the model's settings and select Take over
   ([Semantic model permissions](https://learn.microsoft.com/power-bi/connect-data/service-datasets-permissions#what-are-the-semantic-model-permissions)).
   In the pipeline, they open stg's deployment rules and add a parameter rule
   for `OneLakeSourceUrl` with stg's IDs:

   ```text
   https://onelake.dfs.fabric.microsoft.com/<stg-workspace-id>/<stg-lakehouse-id>
   ```

5. Remove `promote/stg` and add it again, so the rule applies. Load data into
   stg's `lh_gold_revenue`, refresh the model, and check in lineage view that
   it reads stg's lakehouse.
6. Add `promote/prd`. The run waits for a production reviewer, then deploys
   from stg to prd if stg's newest deploy is this PR's. If another PR reached
   stg since, promote that PR instead: its content includes this one. A member
   of `grp_fabric_prd_fin_admin` takes over the model in prd, sets the same
   rule with prd's IDs, then removes `promote/prd` and adds it again.

The first stage can't have rules, and a deploy copies item definitions, not
data.

### Task 7 — Roll back

Fabric has no snapshot to restore. To undo a promoted change, revert its merge
on `main` and promote the revert:

```bash
PR=42
SHA=$(gh pr view "$PR" --json mergeCommit --jq .mergeCommit.oid)
git fetch origin
git switch -c "revert/pr-$PR" origin/main
git revert -m 1 "$SHA"
git push -u origin "revert/pr-$PR"
gh pr create --base main --head "revert/pr-$PR" --title "Revert PR $PR" --body "Rolls back PR $PR."
```

Drop `-m 1` if the PR was squash merged. If it was rebase merged, revert each
of its commits instead. Merge the revert PR and update dev from Git as in
Task 6. Then add `promote/stg` to the revert PR and, once stg looks right,
`promote/prd`. Use a reset only on a branch nobody else uses, such as a
feature branch before its PR merges. On `main`, always revert.

List what the revert can't undo in the revert PR:

- Data doesn't roll back. Rows loaded or tables changed since the original
  deploy stay as they are, so reload them from their source. Reverting a data
  item (one that stores data, such as a lakehouse) to an older version can
  break its data, need you to drop the data, or make the update fail
  ([Learn](https://learn.microsoft.com/fabric/cicd/best-practices-cicd#rolling-back-changes)).
  Check this before you merge the revert.
- If the original PR deleted an item, the revert re-creates it in dev with a
  new item ID, no data and no sensitivity label, and whoever updated dev
  becomes its owner
  ([Git integration process](https://learn.microsoft.com/fabric/cicd/git-integration/git-integration-process#differences-between-git-integration-and-recycle-bin-item-recovery-behavior),
  [Commit changes](https://learn.microsoft.com/fabric/cicd/git-integration/git-get-started#commit-changes-to-git)).
  The pipeline doesn't pair the new item with an old copy still in stg or
  prd. A deploy would add a second item with the same name, or fail for a
  Power BI item such as a report or semantic model
  ([Item pairing](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines#item-pairing),
  [Deployment limitations](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/understand-the-deployment-process#general-considerations-and-limitations)).
  Before you promote the revert, copy out any data you need from the old
  copies, then delete them in stg and prd. Set the item's sensitivity label
  again in dev, because a deploy copies the label to a new item. After the
  deploys, reload the item's data. If the item is `sm_gold_revenue`, each
  stage admin takes it over again and re-creates its deployment rule,
  because deleting an item deletes its rules
  ([Learn](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/create-rules#considerations-and-limitations)).
- Deploying backward, from a later stage to an earlier one, works only into an
  empty stage, so you can't copy prd back over stg.
- Undo in a workspace's Source control pane discards only changes that aren't
  committed yet. An item it brings back after a deletion loses its sensitivity
  label, and its owner becomes the person who undid the change.
- List Deployment Pipeline Operations returns at most the 20 most recent
  deploys. Each PR keeps one promotion comment for stg and one for prd, each
  with only its latest result.
- If the revert removes an item, check stg and prd for it after the deploys,
  and delete it there if it's still present.

### Task 8 — Verify each stage

1. Check the stages from chat with the Core MCP. In a Copilot CLI session:

   ```text
   List the items in stg-fin-revenue and prd-fin-revenue with their types.
   List the role assignments on prd-fin-revenue.
   ```

   stg and prd hold the three items and the lakehouse's SQL analytics
   endpoint, and nothing else. prd's roles are its manifest's owners and the
   SPN.
2. Check the pipeline with the Skill. In a Copilot CLI session:

   ```text
   /deployment-pipelines-authoring-cli Show the stages of the finance-revenue pipeline, the items in each stage and the last five deploy operations.
   ```

3. Without the Skill, a pipeline admin can read the same operations with the
   REST API:

   ```bash
   PIPELINE_ID=$(az rest --method get --resource https://api.fabric.microsoft.com --url https://api.fabric.microsoft.com/v1/deploymentPipelines --query "value[?displayName=='finance-revenue'].id | [0]" --output tsv)
   az rest --method get --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$PIPELINE_ID/operations" --query "value[].{id:id,type:type,status:status,target:targetStageId,start:executionStartTime,end:executionEndTime}" --output table
   ```

### Task 9 — Set up what a deploy doesn't carry

Git and a deploy carry item definitions. Data, permissions, labels and most
settings stay with each stage:

| What | Git | Deploy | Set it up in each stage |
|---|---|---|---|
| Item definitions: lakehouse metadata, model and report definitions, a variable library's variables and value sets | Yes | Yes, overwriting the paired item in the target | Nothing: change them through PRs |
| Data in tables and files | No, and never overwritten | No, and never overwritten | Load it, as in Task 6 |
| Lakehouse shortcuts | Yes, in `shortcuts.metadata.json` | Yes, replacing every shortcut in the target lakehouse. Targets in the same workspace are remapped but must exist there; external targets stay the same unless variables set them | Variables in `vl_gold_revenue` (steps 2 to 5) |
| Active value set | No: it's workspace state | No: a new library starts on the default value set | A stage admin sets it once (step 5) |
| Workspace roles and settings, and item permissions | No | No: the target keeps its own | Roles from the manifests and `provision.py` in [challenge 01](../01-workspace-as-code/challenge.md); a stage admin for the rest |
| OneLake security roles | Preview: definitions in `data-access-roles.json`, without members | Same as Git | Step 7 |
| Sensitivity labels | No: Git doesn't store them | Only to a new item or an empty stage, or when the source's label has protection and the target's doesn't | A stage admin checks the label after each deploy |
| Model refresh schedule, data source credentials, query caching and endorsement | No | No | A stage admin; certification needs an approved certifier |
| The model's lakehouse | dev's `OneLakeSourceUrl` | Replaced by a parameter rule | The rule from Task 6 |

If the model has row-level security roles, a deploy doesn't copy their
members either: a stage admin assigns them in each stage.

1. Branch out from dev again, as in Task 1, to a new workspace,
   `sbx-fin-revenue-feature`, on a new branch, `feature/fin-revenue-config`.
2. In the sandbox, create `vl_gold_revenue` with two String variables:

   - `reference_location`, defaulting to
     `https://stcontosofindev.dfs.core.windows.net`
   - `reference_connection_id`, defaulting to dev's connection ID

   Learn also lists a Connection reference type for connection IDs
   ([Learn](https://learn.microsoft.com/fabric/cicd/variable-library/variable-types#supported-types-in-variable-libraries)).
   Check which type the Manage shortcut pane accepts for the connection
   before you create the library.

   Add value sets `stg` and `prd`, each overriding both variables with that
   stage's values. dev uses the default value set, so don't add a `dev` value
   set: its overrides would repeat the defaults and keep the old values when
   the defaults change.

   Step 4's commit writes the library to Git. Its files look like this,
   without their `$schema` lines. `variables.json`:

   ```json
   {
     "variables": [
       {
         "name": "reference_location",
         "type": "String",
         "value": "https://stcontosofindev.dfs.core.windows.net"
       },
       {
         "name": "reference_connection_id",
         "type": "String",
         "value": "<dev-connection-id>"
       }
     ]
   }
   ```

   `valueSets/stg.json`:

   ```json
   {
     "name": "stg",
     "variableOverrides": [
       {
         "name": "reference_location",
         "value": "https://stcontosofinstg.dfs.core.windows.net"
       },
       {
         "name": "reference_connection_id",
         "value": "<stg-connection-id>"
       }
     ]
   }
   ```

   `valueSets/prd.json` has prd's values, and `settings.json` lists the value
   sets in order: `{"valueSetsOrder": ["stg", "prd"]}`. Git doesn't hold the
   active value set.
3. In the sandbox's `lh_gold_revenue`, create the ADLS Gen2 shortcut
   `Files/fx_rates` to `/reference/fx-rates` on dev's account, with dev's
   connection. Right-click it, select Manage shortcut > Edit target, and
   assign `reference_location` to the location and `reference_connection_id`
   to the connection. Only this pane assigns variables to a shortcut; the
   REST API can't.
4. Commit both items from the sandbox's Source control pane. Pull the branch
   and add the library to the items in `pipelines/finance-revenue.yaml`:

   ```yaml
   items:
     - type: Lakehouse
       pattern: "^lh_gold_revenue$"
     - type: VariableLibrary
       pattern: "^vl_gold_revenue$"
     - type: SemanticModel
       pattern: "^sm_gold_revenue$"
     - type: Report
       pattern: "^rpt_gold_revenue[a-z0-9_]*$"
   ```

   Add `VariableLibrary` to the item types in `schemas/pipeline.schema.json`.
   Push and open a PR to `main`. `pipeline-item-pattern` passes because the
   PR also adds `vl_gold_revenue.VariableLibrary/`. Delete the sandbox once
   the PR merges.
5. Merge, update dev from Git as in Task 6, and add `promote/stg`. The deploy
   creates the library in stg with the default value set active, so stg's
   shortcut still reads dev's account. Set stg's value set right after this
   first deploy, before anything reads `fx_rates`. Learn pages disagree on
   whether a deployment plan sets the active value set, so don't count on
   one. Read the active value set back after each first deploy.

   A member of `grp_fabric_stg_fin_admin` sets it. In a Copilot CLI session:

   ```text
   /variable-library-cli Set the active value set of vl_gold_revenue in stg-fin-revenue to stg, then read it back.
   ```

   Without the Skill:

   ```bash
   WS_ID=$(az rest --method get --resource https://api.fabric.microsoft.com --url https://api.fabric.microsoft.com/v1/workspaces --query "value[?displayName=='stg-fin-revenue'].id | [0]" --output tsv)
   VL_ID=$(az rest --method get --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/variableLibraries" --query "value[?displayName=='vl_gold_revenue'].id | [0]" --output tsv)
   az rest --method patch --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/variableLibraries/$VL_ID" --headers "Content-Type=application/json" --body '{"properties":{"activeValueSetName":"stg"}}'
   az rest --method get --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/variableLibraries/$VL_ID" --query properties.activeValueSetName --output tsv
   ```

   Check stg's `Files/fx_rates`. If it still lists dev's files, remove
   `promote/stg` and add it again. Then add `promote/prd`, and a member of
   `grp_fabric_prd_fin_admin` sets `prd` right after, the same way. Later
   deploys from `promote.py` don't change the active value set, so each stage
   keeps its own.
6. Check both stages with the Core MCP. In a Copilot CLI session:

   ```text
   List the items in stg-fin-revenue and prd-fin-revenue with their types.
   Get the definition of vl_gold_revenue in prd-fin-revenue.
   ```

   Both stages now also hold `vl_gold_revenue`. The definition shows the
   value sets but not the active one; read that with the Skill or the GET in
   step 5.

   > **Preview** (checked 2026-11-27): OneLake security data access roles in Git and deployment pipelines — [Learn](https://learn.microsoft.com/fabric/data-engineering/lakehouse-git-deployment-pipelines). GA route: define the roles in each stage from code, as in challenge 10.

7. If `lh_gold_revenue` has OneLake security roles, Git and deploys carry
   their definitions in `data-access-roles.json` only after the lakehouse is
   opted in to tracking them. Preview object types are off by default, and
   only a workspace Admin or Member can sync roles. If a deploy fails with
   `LakehouseImportUserActionNeededForObjectOverwrite`, the target lakehouse
   uses OneLake security but isn't opted in, so the deploy won't overwrite its
   roles: turn on tracking and opt-in there, reconcile its roles and deploy
   again. Entra members aren't carried; they survive only on roles whose names
   match exactly. Keep role names identical across stages, or define the roles
   from code, as in
   [challenge 10](../10-onelake-security-as-code/challenge.md).

### Task 10 — Choose one deploy route per stage

Other tools can deploy the same Git content. Give stg and prd one route each,
and never point a second tool at them. Two tools overwrite each other's
changes and split the history. The pipeline also doesn't pair an item that
another tool created. Its next deploy adds a second item with the same name.
For a Power BI item, such as a report or semantic model, the deploy fails
instead
([Item pairing](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines#item-pairing),
[Deployment limitations](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/understand-the-deployment-process#general-considerations-and-limitations)).
Branched workspaces are never stages.

| Route | What it does | What to weigh |
|---|---|---|
| Pipeline with `promote.py` (this challenge) | Deploys stage to stage, up to 300 items per deploy | Rules per stage; history is the last 20 operations and each PR's latest result per stage |
| fabric-cicd v1.4.0 | Publishes the Git folder to a workspace on every run | `environment` picks the `parameter.yml` values and activates the value set with that name; without it, the active value set stays. `parameter.yml` offers `find_replace`, `key_value_replace`, `spark_pool` and `semantic_model_binding`. Shortcuts publish only with the `enable_shortcut_publish` feature flag. No deployment plans |
| Fabric CLI v1.9.0 | `fab deploy` publishes from a config file through fabric-cicd; `fab import` and `fab export` move single items | By default, `fab deploy` also removes target items that aren't in the source; skip unpublish in the config file to stop it |
| Terraform `microsoft/fabric` v1.15.1 | `fabric_deployment_pipeline`, `fabric_deployment_pipeline_role_assignment`, `fabric_workspace_git` and `fabric_variable_library` declare the pipeline, its roles, a Git connection and a library | It doesn't deploy content; `fabric_workspace_git` supports an SPN only with a configured connection |
| Deployment plans (Preview) | Add item order, and actions before or after an item deploys, such as running a notebook, to a deploy through a pipeline, Git or the REST API | One plan per operation and one target workspace per run; no workspace configuration such as connections or workspace identities; stops at the first failure and doesn't roll back; Learn pages disagree on whether a plan sets a library's active value set |

Workspace Private Link doesn't support deployment pipelines or semantic models:
a workspace in a pipeline can't block public access, and a workspace that
holds a semantic model can't turn on workspace-level private links. A stage
that needs Private Link, as in
[challenge 11](../11-network-exfiltration-guardrails/challenge.md), can't be
in this pipeline or hold `sm_gold_revenue`. Decide which matters more for
each workspace before you turn it on.

1. Check from chat that only the pipeline can change stg and prd. In a
   Copilot CLI session:

   ```text
   List the role assignments on stg-fin-revenue and prd-fin-revenue.
   ```

   Expect only each manifest's owners and the SPN. Anyone else with
   Contributor or above could publish to the stage with another tool.
2. Check that neither stage is connected to Git. In a Copilot CLI session:

   ```text
   /git-integration-operations-cli Show whether stg-fin-revenue and prd-fin-revenue are connected to Git.
   ```

   If either is, a workspace Admin disconnects it in Workspace settings > Git
   integration > Disconnect workspace.

## Success criteria

- [ ] Only `dev-fin-revenue` is connected to Git, on `main` with folder
      `fabric/finance-revenue`, and the sandbox is deleted after its PR merges.
- [ ] `validate.py` blocks a pipeline file whose stages are out of order,
      whose prd stage doesn't use `promote/prd` and `production`, or whose
      item pattern matches nothing in `fabric/finance-revenue`.
- [ ] `promote/stg` on a merged PR deploys only the declared items from dev to
      stg, and the PR comment holds the stg marker.
- [ ] `promote/prd` waits for a production reviewer, and stops without
      deploying when stg has had a newer deploy than the PR's.
- [ ] In each stage, `sm_gold_revenue` reads that stage's `lh_gold_revenue`.
- [ ] After a revert PR is promoted, stg and prd hold the earlier definitions,
      and the revert PR lists what didn't roll back.
- [ ] The SPN isn't a Fabric administrator or a capacity admin, and the
      pipeline's other admins are security groups.
- [ ] In stg and prd, `vl_gold_revenue` has that stage's value set active,
      and `Files/fx_rates` lists that stage's files.
- [ ] stg and prd aren't connected to Git, and their roles match their
      manifests' owners and the SPN.

## Stretch goals

- **Git status gate.** Before a stg promotion, call Get Status on dev and stop
  when dev has incoming or uncommitted changes, so stg gets exactly what `main`
  holds. The SPN needs its own Git credentials for this call. Set them with
  [Update My Git Credentials](https://learn.microsoft.com/rest/api/fabric/core/git/update-my-git-credentials),
  using a configured connection the SPN has permission on, because an SPN
  can't use the Automatic source. Check them with
  [Get My Git Credentials](https://learn.microsoft.com/rest/api/fabric/core/git/get-my-git-credentials).
  These calls need Contributor or higher on dev
  ([Learn](https://learn.microsoft.com/rest/api/fabric/core/git/get-status#permissions)).
- **Breaking-change gate.** Before a prd promotion, get `sm_gold_revenue`'s
  definition from stg and from prd with
  [Get Semantic Model Definition](https://learn.microsoft.com/rest/api/fabric/semanticmodel/items/get-semantic-model-definition),
  which returns TMDL by default. When it answers 202, poll the operation as
  `deploy()` does, then read the definition from `/operations/{id}/result`.
  Compare the tables, columns and measures in the `definition/tables/` parts,
  and raise `GateError` when prd has one that stg doesn't: the deploy would
  remove it, and reports or queries outside the pipeline may use it. If the
  model has an encrypted sensitivity label, the SPN needs usage rights that
  let it remove the label.
- **Pipeline drift.** Extend `drift.py` to list each stage's items and report
  any that `pipelines/finance-revenue.yaml` doesn't declare, apart from each
  lakehouse's SQL analytics endpoint. Add them to its report and exit 2, as
  for other drift, so `drift.yml` opens its usual issue labeled `drift` and
  `governance`.
- **Selective promotion.** Deploy only the items a PR changed, by mapping its
  changed files under `fabric/finance-revenue/` to items through their
  `.platform` files. A deploy fails when an item's dependency is missing from
  the target, so add new dependencies too.
- **fabric-cicd for one stage.** Create an empty `sbx-fin-revenue-cicd` on
  `contosononprodf2`. Publish `fabric/finance-revenue/` to it with
  fabric-cicd v1.4.0, `environment="stg"`, and the `enable_shortcut_publish`
  feature flag on for `fx_rates`. In `parameter.yml`, add two `find_replace`
  entries for `OneLakeSourceUrl`: dev's workspace ID becomes `$workspace.$id`
  and dev's lakehouse ID becomes `$items.Lakehouse.lh_gold_revenue.$id`.
  Compare with stg, then delete the sandbox.

> **Preview** (checked 2026-11-27): Deployment plans — [Learn](https://learn.microsoft.com/fabric/cicd/deployment-plan/deployment-plan-overview). GA route: deploy with `promote.py`, then set each stage's value set as in Task 9.

- **Deployment plan.** Create a plan that deploys `vl_gold_revenue` before
  `lh_gold_revenue`, names `stg` as the library's active value set, and runs
  a notebook after `sm_gold_revenue` deploys. Attach it to a deploy to stg.
  After the deploy, read the library's active value set in stg. If it isn't
  `stg`, set it as in Task 9.
  To attach it from `promote.py`, add `?beta=true` to the deploy URL and an
  `options.deploymentPlan` object with the plan's `itemId` and
  `"referenceType": "ByItemId"`; plan support in that API is Beta.
  Make the notebook fail once, and record what the failed run left in stg:
  nothing rolls back.

> **Preview** (checked 2026-11-27): Protection policies — [Learn](https://learn.microsoft.com/fabric/governance/protection-policies-create#create-a-protection-policy-for-fabric). GA route: none; stretch task.

- **Protection policies.** In each protection policy that covers items in
  `dev-fin-revenue`, `stg-fin-revenue` or `prd-fin-revenue`, turn on Allow
  users to retain full control. Under Add users and groups, add
  `sg-fabric-workspace-provisioner`, the stage admin groups and the people
  who update dev from Git. An SPN can be added only through a security group
  ([Learn](https://learn.microsoft.com/fabric/governance/protection-policies-create#prerequisites)).
  Do this before 2027-02-28, when deploys and Git integration start to need
  read and write permission on every item.

## MCP tips

- The Core MCP server has no tools for Git integration or deployment pipelines.
  The scripts and Skills call REST for those, and the scripts would call REST
  anyway, because they run unattended as the SPN.
- `list_items`, `get_item` and `list_workspace_roles` check a stage from chat.
- `get_item_definition` exports an item's definition, the first step of the GA
  route for `sm_gold_revenue`. Don't call `update_item_definition` on stg or
  prd: only the pipeline changes them.
- `get_item_definition` on `vl_gold_revenue` returns its variables and value
  sets, but not the active value set, which is workspace state. Read that
  with `/variable-library-cli` or Get Variable Library.
- The remote Core MCP server has no operation tools. To check a long-running
  operation from chat, add the local Fabric MCP server with `/mcp add`, running
  `npx -y @microsoft/fabric-mcp@latest server start --mode all`. It has
  `core_get-operation-state` and `core_get-operation-result`, and needs
  Node.js 22 or later, with `npx` on your `PATH`.

## Skills tips

- `/git-integration-operations-cli` connects workspaces, commits, updates and
  reads Git status. It's experimental, and it leaves out branch switching,
  `fab deploy`, fabric-cicd and rebinding items across workspaces. Task 1
  switches branches in the portal, and Task 6 rebinds the model with a
  deployment rule.
- `/deployment-pipelines-authoring-cli` creates pipelines, assigns workspaces,
  deploys forward or backward, polls the operation and manages pipeline roles.
  An SPN can use it only if its group is in the tenant setting for creating
  deployment pipelines. In this challenge, use it to inspect; `promote.yml`
  does the deploys.
- `/variable-library-cli` creates variable libraries, edits their variables
  and value sets, and sets the active value set. It keeps the definition, in
  Git, apart from the active value set, which each workspace keeps, and won't
  write an override equal to the default. To assign variables to a shortcut,
  it sends you to the Manage shortcut pane: the REST API can't.

## Repository files

- [`.github/workflows/validate.yml`](../../.github/workflows/validate.yml) and
  [`scripts/validate.py`](../../scripts/validate.py): Task 3 adds
  `check_pipelines()` and the `pipelines/**` and `fabric/**` paths.
- [`.github/workflows/provision.yml`](../../.github/workflows/provision.yml):
  `promote.yml` copies its venv step and OIDC sign-in.
- [`scripts/_fabric.py`](../../scripts/_fabric.py): `promote.py` uses its
  `_request`, `_paged` and `AuthError`.
- [`scripts/drift.py`](../../scripts/drift.py): reports the sandbox as
  unmanaged, and the pipeline drift stretch goal extends it.
- [`.github/CODEOWNERS`](../../.github/CODEOWNERS): Task 2.
- New in this challenge: `pipelines/finance-revenue.yaml`,
  `schemas/pipeline.schema.json`, `scripts/promote.py`,
  `.github/workflows/promote.yml` and `fabric/finance-revenue/`, which holds
  `vl_gold_revenue.VariableLibrary/` after Task 9.

## References

- [Git integration](https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration)
- [Get started with Git integration](https://learn.microsoft.com/fabric/cicd/git-integration/git-get-started)
- [Git integration process](https://learn.microsoft.com/fabric/cicd/git-integration/git-integration-process)
- [Branched workspaces](https://learn.microsoft.com/fabric/cicd/git-integration/branched-workspace)
- [Source code format](https://learn.microsoft.com/fabric/cicd/git-integration/source-code-format)
- [Git integration tenant settings](https://learn.microsoft.com/fabric/admin/git-integration-admin-settings)
- [Deployment pipelines](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines)
- [The deployment process](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/understand-the-deployment-process)
- [Deploy content](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/deploy-content)
- [Create deployment rules](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/create-rules)
- [Automate deployment pipelines](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/pipeline-automation-fabric)
- [CI/CD best practices: rolling back changes](https://learn.microsoft.com/fabric/cicd/best-practices-cicd#rolling-back-changes)
- [Troubleshoot CI/CD](https://learn.microsoft.com/fabric/cicd/troubleshoot-cicd)
- [Develop Direct Lake semantic models](https://learn.microsoft.com/fabric/fundamentals/direct-lake-develop)
- [Direct Lake in Power BI Desktop](https://learn.microsoft.com/fabric/fundamentals/direct-lake-power-bi-desktop)
- [TMDL view](https://learn.microsoft.com/power-bi/transform-model/desktop-tmdl-view)
- [Semantic model ownership](https://learn.microsoft.com/power-bi/connect-data/service-datasets-understand#semantic-model-ownership)
- [Take Over In Group](https://learn.microsoft.com/rest/api/power-bi/datasets/take-over-in-group)
- [Protection policies](https://learn.microsoft.com/fabric/governance/protection-policies-overview)
- [Create protection policies](https://learn.microsoft.com/fabric/governance/protection-policies-create)
- [Lakehouse Git integration and deployment pipelines](https://learn.microsoft.com/fabric/data-engineering/lakehouse-git-deployment-pipelines)
- [Variable libraries](https://learn.microsoft.com/fabric/cicd/variable-library/variable-library-overview)
- [Variable library CI/CD](https://learn.microsoft.com/fabric/cicd/variable-library/variable-library-cicd)
- [Variable library permissions](https://learn.microsoft.com/fabric/cicd/variable-library/variable-library-permissions)
- [Variable types](https://learn.microsoft.com/fabric/cicd/variable-library/variable-types)
- [Assign variables to shortcuts](https://learn.microsoft.com/fabric/onelake/assign-variables-to-shortcuts)
- [OneLake shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcuts)
- [Assign a workspace to a deployment pipeline](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/assign-pipeline)
- [Deployment plans](https://learn.microsoft.com/fabric/cicd/deployment-plan/deployment-plan-overview)
- [Workspace Private Link supported scenarios](https://learn.microsoft.com/fabric/security/security-workspace-level-private-links-support)
- [Deploy Stage Content](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/deploy-stage-content)
- [List Deployment Pipeline Operations](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/list-deployment-pipeline-operations)
- [List Deployment Pipeline Stage Items](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/list-deployment-pipeline-stage-items)
- [List Deployment Pipelines](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/list-deployment-pipelines)
- [Create Deployment Pipeline](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/create-deployment-pipeline)
- [Assign Workspace To Stage](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/assign-workspace-to-stage)
- [Add Deployment Pipeline Role Assignment](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/add-deployment-pipeline-role-assignment)
- [Get Operation State](https://learn.microsoft.com/rest/api/fabric/core/long-running-operations/get-operation-state)
- [Git - Get Status](https://learn.microsoft.com/rest/api/fabric/core/git/get-status)
- [Git - Update My Git Credentials](https://learn.microsoft.com/rest/api/fabric/core/git/update-my-git-credentials)
- [Git - Get My Git Credentials](https://learn.microsoft.com/rest/api/fabric/core/git/get-my-git-credentials)
- [Git - Update From Git](https://learn.microsoft.com/rest/api/fabric/core/git/update-from-git)
- [Variable library definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/variable-library-definition)
- [Get Variable Library](https://learn.microsoft.com/rest/api/fabric/variablelibrary/items/get-variable-library)
- [Update Variable Library](https://learn.microsoft.com/rest/api/fabric/variablelibrary/items/update-variable-library)
- [Enable service principal access to admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)
- [Connect GitHub Actions to Azure with OpenID Connect](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect)
- [az ad app federated-credential](https://learn.microsoft.com/cli/azure/ad/app/federated-credential)
- [fabric-cicd](https://microsoft.github.io/fabric-cicd/latest/)
- [fabric-cicd parameterization](https://microsoft.github.io/fabric-cicd/latest/how_to/parameterization/)
- [Fabric CLI deploy](https://microsoft.github.io/fabric-cli/commands/fs/deploy/)
- [Terraform provider for Fabric](https://registry.terraform.io/providers/microsoft/fabric/latest/docs)
- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Control workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [OpenID Connect immutable subject claims](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims)
- [Core MCP server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Core MCP server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server)
- [Fabric MCP server](https://github.com/microsoft/mcp/blob/main/servers/Fabric.Mcp.Server/README.md)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
