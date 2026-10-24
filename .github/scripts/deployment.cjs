// Trusted default-branch code for deployment: finds a merge-queue result that a staging deployment can reuse, and
// resolves what the separate, serialized publish workflow publishes. It builds and publishes nothing itself.
const { tagOf, refContext, sources, productionSource } = require("./release-artifact.cjs");

const SHA = /^[0-9a-f]{40}$/;
const sameRepository = (context, run) => run.head_repository?.full_name === `${context.repo.owner}/${context.repo.repo}`;

/** The successful merge-group checks run of exactly this commit, whose health snapshot staging may import, or why
    there is none. A pull-request run never qualifies. */
async function queueResult({ github, context }) {
  if (!SHA.test(context.sha)) throw Error("Deployment requires a full source SHA");
  const runs = (await github.paginate(github.rest.actions.listWorkflowRuns, { ...context.repo, workflow_id: "checks.yml",
    event: "merge_group", head_sha: context.sha, per_page: 100 }))
    .filter((run) => run.head_sha === context.sha && run.event === "merge_group" && sameRepository(context, run));
  const passed = runs.find((run) => run.conclusion === "success");
  if (passed) return { run: String(passed.id), attempt: String(passed.run_attempt), url: passed.html_url, reason: "" };
  const latest = runs[0];
  const reason = latest
    ? `the merge-queue run of this commit ${latest.conclusion ? `ended with ${latest.conclusion}` : "has not finished"} (${latest.html_url})`
    : "no merge-queue run checked this commit, as after a direct or administrator merge";
  return { run: "", attempt: "", url: "", reason };
}

/** The newest deployment run of `branch` started after this one, or null. */
async function newerRun(github, context, branch) {
  const { data } = await github.rest.actions.listWorkflowRuns({ ...context.repo, workflow_id: "deploy.yml", branch, per_page: 20 });
  return data.workflow_runs.find((run) => run.head_branch === branch && run.id > context.runId && sameRepository(context, run)) || null;
}

/** The newest deployment run of `branch` at `sha`: the one whose publication publishes that commit, or null. */
async function runFor(github, context, branch, sha) {
  const { data } = await github.rest.actions.listWorkflowRuns({ ...context.repo, workflow_id: "deploy.yml", branch,
    head_sha: sha, per_page: 10 });
  return data.workflow_runs.find((run) => run.head_branch === branch && run.head_sha === sha && sameRepository(context, run)) || null;
}

/** The newest default-branch commit whose staging site a deployment run checked and kept, with that run. */
async function newestStaging(github, context, branch) {
  const { data: commits } = await github.rest.repos.listCommits({ ...context.repo, sha: branch, per_page: 100 });
  const order = new Map(commits.map((commit, index) => [commit.sha, index]));
  const { data } = await github.rest.actions.listWorkflowRuns({ ...context.repo, workflow_id: "deploy.yml", branch, per_page: 30 });
  let newest = null;
  for (const run of data.workflow_runs) {
    if (run.head_branch !== branch || !order.has(run.head_sha) || !sameRepository(context, run)) continue;
    if (newest && order.get(run.head_sha) >= order.get(newest.commit)) continue;
    const { data: kept } = await github.rest.actions.listWorkflowRunArtifacts({ ...context.repo, run_id: run.id,
      name: "staging-site", per_page: 10 });
    if (kept.artifacts.some((artifact) => artifact.name === "staging-site" && !artifact.expired)) {
      newest = { commit: run.head_sha, run: String(run.id) };
    }
  }
  return newest;
}

/** The deployment run whose completion started this publication, as the context `publication` reads: its ref, commit
    and run id. Only a successful run of this repository's deploy.yml from a push or a manual run qualifies, and a
    release tag must still name the commit that run prepared. */
async function completedDeployment({ github, context }) {
  const run = (await github.rest.actions.getWorkflowRun({ ...context.repo, run_id: context.payload.workflow_run.id })).data;
  if (run.conclusion !== "success" || !["push", "workflow_dispatch"].includes(run.event) || !sameRepository(context, run) ||
      String(run.path).split("@")[0] !== ".github/workflows/deploy.yml") throw Error("Not a successful repository deployment");
  const branch = context.payload.repository.default_branch;
  const ref = run.head_branch === branch ? `refs/heads/${branch}` : `refs/tags/${run.head_branch}`;
  const deployed = Object.assign(refContext(context, ref, run.head_sha), { runId: run.id });
  if (ref.startsWith("refs/tags/")) {
    tagOf(deployed);
    if ((await github.rest.repos.getCommit({ ...context.repo, ref: run.head_branch })).data.sha !== run.head_sha) {
      throw Error("Release tag moved after its deployment");
    }
  }
  return deployed;
}

const nothing = (reason, successor) => ({ publish: "false", reason, successor: successor?.html_url || "", staging: "",
  staging_run: "", tag: "", production: "", production_run: "" });

/** What one publication publishes, resolved inside the serialized section so that neither channel moves back. Its
    Pages deployment is recorded against `recorded`, the default-branch head when it started, so it publishes only
    that commit's staging site. Production is the newest approved release, from its release assets or the run that
    approved it (`production_run`), whichever deployment started the publication; nothing is fetched here. After a
    default-branch deployment, publication takes that run's own checked staging site while its commit is the head.
    After a release-tag deployment, it takes the newest checked staging site once that is the head's; until then the
    head's own deployment publishes the release. */
async function publication({ github, context, recorded }) {
  const branch = context.payload.repository.default_branch;
  const isTag = context.ref.startsWith("refs/tags/");
  if (!isTag && context.ref !== "refs/heads/" + branch) throw Error("Publish only the default branch or a release tag");
  if (!SHA.test(context.sha) || !SHA.test(recorded || "")) throw Error("Publication requires full source SHAs");
  const head = (await github.rest.repos.getBranch({ ...context.repo, branch })).data.commit.sha;
  if (!SHA.test(head)) throw Error("Invalid default-branch commit");
  if (head !== recorded) {
    return nothing(`the default branch moved on to ${head} after this publication started`, await runFor(github, context, branch, head));
  }
  let staging = { commit: context.sha, run: String(context.runId) };
  if (isTag) {
    staging = await newestStaging(github, context, branch);
    if (staging?.commit !== head) {
      return nothing(`the default-branch head ${head} has no checked staging site yet; its deployment publishes this release with it`,
        await runFor(github, context, branch, head));
    }
  } else if (context.sha !== head) {
    return nothing(`the default branch moved on to ${head}`, await runFor(github, context, branch, head));
  }
  // The newest approved release, even after another tag's deployment: a publication waiting for this one may have
  // been replaced by it, so it publishes everything that one would have.
  const selected = await sources({ github, context: refContext(context, "refs/heads/" + branch, head) });
  let production = { tag: "", commit: "", run: "" };
  if (selected.tag) {
    const { run } = await productionSource({ github, context: refContext(context, "refs/tags/" + selected.tag, selected.production) });
    production = { tag: selected.tag, commit: selected.production, run: run ? String(run) : "" };
  }
  return { publish: "true", reason: "", successor: "", staging: staging.commit, staging_run: staging.run,
    tag: production.tag, production: production.commit, production_run: production.run };
}

/** The summary of a cancelled deployment run, naming the run that supersedes it. Publication runs in its own workflow,
    so cancelling preparation never interrupts a Pages deployment. */
async function superseded({ github, context }) {
  const ref = context.ref.replace(/^refs\/(heads|tags)\//, "");
  const run = await newerRun(github, context, ref);
  return run
    ? `This run was cancelled; [run ${run.id}](${run.html_url}) supersedes it and publishes the newest checked site.`
    : "This run was cancelled; the next deployment of this ref publishes the newest checked site.";
}

module.exports = { queueResult, newestStaging, completedDeployment, publication, superseded };
