// Trusted default-branch code for deployment: finds a merge-queue result that a staging deployment can reuse, and
// resolves what the serialized Pages publication publishes. It builds and publishes nothing itself.
const { writeFileSync } = require("node:fs");
const { tagOf, refContext, sources, reuse } = require("./release-artifact.cjs");

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

const NOTHING = { staging: "", staging_run: "", tag: "", production: "", production_run: "" };

/** What this run publishes, resolved inside the serialized section so that neither channel moves back.
    Production is the newest approved release, from its release assets (written to .cache/release) or the run that
    approved it. A branch run publishes its own checked staging site while its commit is the default-branch head; a
    tag run publishes the newest checked staging site of any default-branch run. */
async function publication({ github, context }, write = writeFileSync) {
  const branch = context.payload.repository.default_branch;
  const isTag = context.ref.startsWith("refs/tags/");
  if (!isTag && context.ref !== "refs/heads/" + branch) throw Error("Publish only the default branch or a release tag");
  if (!SHA.test(context.sha)) throw Error("Publication requires a full source SHA");
  const head = (await github.rest.repos.getBranch({ ...context.repo, branch })).data.commit.sha;
  if (!SHA.test(head)) throw Error("Invalid default-branch commit");
  let staging;
  if (isTag) {
    staging = await newestStaging(github, context, branch);
    if (!staging) throw Error("No default-branch deployment kept a checked staging site; deploy the default branch, then rerun this run");
  } else if (context.sha !== head) {
    const successor = await newerRun(github, context, branch);
    return { publish: "false", reason: `the default branch moved on to ${head}`, successor: successor?.html_url || "", ...NOTHING };
  } else {
    staging = { commit: head, run: String(context.runId) };
  }
  const selected = await sources({ github, context: refContext(context, "refs/heads/" + branch, head) });
  if (isTag && selected.tag !== tagOf(context).tag) {
    const successor = selected.tag ? await newerRun(github, context, selected.tag) : null;
    return { publish: "false", reason: `${selected.tag || "another release"} is the newest approved release`,
      successor: successor?.html_url || "", ...NOTHING };
  }
  let production = { tag: "", commit: "", run: "" };
  if (selected.tag) {
    const { run } = await reuse({ github, context: refContext(context, "refs/tags/" + selected.tag, selected.production) }, write);
    production = { tag: selected.tag, commit: selected.production, run: run ? String(run) : "" };
  }
  return { publish: "true", reason: "", successor: "", staging: staging.commit, staging_run: staging.run,
    tag: production.tag, production: production.commit, production_run: production.run };
}

/** The summary of a cancelled run, naming the run that supersedes it. A cancelled Pages deployment changes nothing. */
async function superseded({ github, context }) {
  const ref = context.ref.replace(/^refs\/(heads|tags)\//, "");
  const run = await newerRun(github, context, ref);
  return run
    ? `This run was cancelled; [run ${run.id}](${run.html_url}) supersedes it and publishes the newest checked site.`
    : "This run was cancelled; the next deployment of this ref publishes the newest checked site.";
}

module.exports = { queueResult, newestStaging, publication, superseded };
