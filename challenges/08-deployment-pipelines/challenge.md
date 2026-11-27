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

  A Fabric administrator finds them in OneLake catalog > Govern >
  Configurations > Tenant settings; where Govern isn't available, use
  Settings > Admin portal > Tenant settings
  ([Learn](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)).
- The same administrator enables these settings for the people who connect,
  update and branch out from dev
  ([Learn](https://learn.microsoft.com/fabric/admin/git-integration-admin-settings)):
  - Users can create Fabric items
  - Users can synchronize workspace items with their Git repositories
  - Users can sync workspace items with GitHub repositories
  - Users can export workspace items with applied sensitivity labels to Git repositories
  - Create workspaces, which branching out to a new workspace needs
- The SPN isn't a Fabric administrator or a capacity admin, has no
  admin-consent Power BI permissions and isn't in any label publishing policy.
  It has Contributor permissions on both capacities and is Admin of
  `dev-fin-revenue`, `stg-fin-revenue` and `prd-fin-revenue`. It becomes an
  admin of the pipeline by creating it.
- The stage admin groups, `grp_fabric_stg_fin_admin` and
  `grp_fabric_prd_fin_admin`, are security groups. Microsoft 365 groups can't
  be pipeline admins.
- From 2027-02-28, when items in a workspace carry sensitivity labels with
  protection policies, only people and SPNs with read and write access to all
  its items can use Git integration on it, deploy to it or assign it to a
  pipeline stage. In each such policy, turn on Allow users to retain full
  control and add `sg-fabric-workspace-provisioner` and the stage admin groups
  under Add users and groups. An SPN can only be added through a security group
  ([Learn](https://learn.microsoft.com/fabric/governance/protection-policies-overview)).
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
   parameter. Edit `sm_gold_revenue` live in Power BI Desktop, open TMDL view,
   drag Expressions from the Model tab into the editor and add this parameter
   at the same indentation as the existing expression:

   ```tmdl
   expression OneLakeSourceUrl = "https://onelake.dfs.fabric.microsoft.com/<workspace-id>/<item-id>" meta [IsParameterQuery = true, IsParameterQueryRequired = true, Type = "Text"]
   ```

   Use dev's workspace ID and the lakehouse's item ID, not the ID of its SQL
   analytics endpoint. In the existing Direct Lake expression, replace the
   quoted URL with the parameter, so the source reads
   `AzureStorage.DataLake(OneLakeSourceUrl, [HierarchicalNavigation = true])`.
   Keep the expression's name and annotations. Apply the change, then commit it
   from dev's Source control pane.
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

1. Create the labels, the `staging` environment and its federated credential:

   ```bash
   gh label create promote/stg --color 1D76DB --description "Deploy this merged PR from dev to stg"
   gh label create promote/prd --color B60205 --description "Deploy this merged PR from stg to prd after approval"
   repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
   app_id=$(gh variable get AZURE_CLIENT_ID)
   gh api --method PUT "repos/$repo/environments/staging"
   az ad app federated-credential create --id "$app_id" --parameters '{"name":"gh-staging","issuer":"https://token.actions.githubusercontent.com","subject":"repo:'"$repo"':environment:staging","audiences":["api://AzureADTokenExchange"]}'
   ```

   The `production` environment, with its required reviewers and federated
   credential, comes from challenge 00.
2. Create `.github/workflows/promote.yml`:

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
     group: promote-finance-revenue
     cancel-in-progress: false

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
time. GitHub keeps only the newest pending run and cancels older ones, so if
yours was canceled, add its label again.

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
           items: list[dict], note: str) -> dict:
    """Deploy the items and wait for the operation to finish."""
    r = fab._request("POST", f"{fab.FABRIC_BASE}/deploymentPipelines/{pipeline_id}/deploy",
                     json={"sourceStageId": source_id, "targetStageId": target_id,
                           "items": items, "note": note}, expect=(202,))
    operation = r.headers["x-ms-operation-id"]
    while True:
        time.sleep(int(r.headers.get("Retry-After", 20)))
        r = fab._request("GET", f"{fab.FABRIC_BASE}/operations/{operation}")
        state = r.json()
        if state["status"] in ("Succeeded", "Failed"):
            return state


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
        state = deploy(pipeline_id, stages[source], stages[target], items,
                       f"PR #{pr} merge {sha}")
        lines.append(f"Deployed {len(items)} items from {source} to {target}: "
                     f"{state['status']}.")
        if state["status"] != "Succeeded":
            lines.append(f"Error: {state.get('error')}")
            return 1
        if target == "stg":
            op = newest_deploy(pipeline_id, stages["stg"])
            lines += ["", f"<!-- promote target=stg result=Succeeded sha={sha} "
                          f"operation={op['id']} -->"]
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
   stage if it isn't assigned yet. Right after a pipeline is created, calls can
   fail with `Alm_InvalidRequest_WorkloadUnavailable`: wait 60 to 120 seconds
   and retry.
2. Complete `ensure_admins()`. Add each group in `admins` as a pipeline Admin
   with Add Deployment Pipeline Role Assignment if it isn't one already.

The deploy note goes to the pipeline's history in the portal, but the gate
doesn't read it back. The PR comment holds the evidence: after a successful stg
deploy, it records the merge and the ID of stg's newest deploy, and a prd run
passes only if that deploy is still stg's newest.

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
4. A member of `grp_fabric_stg_fin_admin` takes over `sm_gold_revenue` in
   `stg-fin-revenue`, because only an item's owner can create rules for it.
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
  deploy stay as they are, so reload them from their source.
- If the original PR deleted an item, updating dev from the revert re-creates
  it with a new item ID and without its data or sensitivity label. Reload the
  data and set the label again.
- Deploying backward, from a later stage to an earlier one, works only into an
  empty stage, so you can't copy prd back over stg.
- Undo in a workspace's Source control pane discards only changes that aren't
  committed yet. An item it brings back after a deletion loses its sensitivity
  label, and its owner becomes the person who undid the change.
- List Deployment Pipeline Operations returns at most the 20 most recent
  deploys. The promotion comments on each PR keep the longer record.
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
2. Check the pipeline with the Skill:

   ```text
   /deployment-pipelines-authoring-cli Show the stages of the finance-revenue pipeline, the items in each stage and the last five deploy operations.
   ```

3. Without the Skill, a pipeline admin can read the same operations with the
   REST API:

   ```bash
   PIPELINE_ID=$(az rest --method get --resource https://api.fabric.microsoft.com --url https://api.fabric.microsoft.com/v1/deploymentPipelines --query "value[?displayName=='finance-revenue'].id | [0]" --output tsv)
   az rest --method get --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$PIPELINE_ID/operations" --query "value[].{type:type,status:status,target:targetStageId,start:executionStartTime,end:executionEndTime}" --output table
   ```

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

## Stretch goals

- **Git status gate.** Before a stg promotion, call Get Status on dev and stop
  when dev has incoming or uncommitted changes, so stg gets exactly what `main`
  holds. Check first that the SPN can call Git status in your tenant.
- **Pipeline drift.** Extend `drift.py` to list each stage's items and report
  any that `pipelines/finance-revenue.yaml` doesn't declare, apart from each
  lakehouse's SQL analytics endpoint. Add them to its report and exit 2, as
  for other drift, so `drift.yml` opens its usual issue labeled `drift` and
  `governance`.
- **Selective promotion.** Deploy only the items a PR changed, by mapping its
  changed files under `fabric/finance-revenue/` to items through their
  `.platform` files. A deploy fails when an item's dependency is missing from
  the target, so add new dependencies too.

## MCP tips

- The Core MCP server has no tools for Git integration or deployment pipelines.
  The scripts and Skills call REST for those, and the scripts would call REST
  anyway, because they run unattended as the SPN.
- `list_items`, `get_item` and `list_workspace_roles` check a stage from chat.
- `get_item_definition` exports an item's definition, the first step of the GA
  route for `sm_gold_revenue`. Don't call `update_item_definition` on stg or
  prd: only the pipeline changes them.
- The remote Core MCP server has no operation tools. To check a long-running
  operation from chat, add the local Fabric MCP server with `/mcp add`, running
  `npx -y @microsoft/fabric-mcp@latest server start --mode all`. It has
  `core_get-operation-state` and `core_get-operation-result`.

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
  `.github/workflows/promote.yml` and `fabric/finance-revenue/`.

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
- [Take over item ownership](https://learn.microsoft.com/fabric/fundamentals/item-ownership-take-over)
- [Protection policies](https://learn.microsoft.com/fabric/governance/protection-policies-overview)
- [Deploy Stage Content](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/deploy-stage-content)
- [List Deployment Pipeline Operations](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/list-deployment-pipeline-operations)
- [List Deployment Pipeline Stage Items](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/list-deployment-pipeline-stage-items)
- [List Deployment Pipelines](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/list-deployment-pipelines)
- [Create Deployment Pipeline](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/create-deployment-pipeline)
- [Assign Workspace To Stage](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/assign-workspace-to-stage)
- [Add Deployment Pipeline Role Assignment](https://learn.microsoft.com/rest/api/fabric/core/deployment-pipelines/add-deployment-pipeline-role-assignment)
- [Git - Get Status](https://learn.microsoft.com/rest/api/fabric/core/git/get-status)
- [Git - Update From Git](https://learn.microsoft.com/rest/api/fabric/core/git/update-from-git)
- [Enable service principal access to admin APIs](https://learn.microsoft.com/fabric/admin/enable-service-principal-admin-apis)
- [Connect GitHub Actions to Azure with OpenID Connect](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect)
- [az ad app federated-credential](https://learn.microsoft.com/cli/azure/ad/app/federated-credential)
- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Core MCP server tools](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/tools-core-mcp-server)
- [Core MCP server](https://learn.microsoft.com/rest/api/fabric/articles/mcp-servers/core-remote/overview-core-mcp-server)
- [Skills for Fabric](https://github.com/microsoft/skills-for-fabric)
