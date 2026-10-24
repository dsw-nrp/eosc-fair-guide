// Deployment identities: a staging deployment reuses only the merge-queue result of the same commit; the separate,
// serialized publication follows only a successful deployment run and resolves the newest checked staging site and
// the newest approved release, so a late approval still promotes its tag, no run moves a channel back and the Pages
// record names the staging commit published.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { queueResult, newestStaging, completedDeployment, publication, superseded } = createRequire(import.meta.url)("../../.github/scripts/deployment.cjs");

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const own = { full_name: "dsw-nrp/eosc-fair-guide" };
const commit = (letter) => letter.repeat(40);
const [c0, c1, c2, c3] = ["0", "1", "2", "3"].map(commit);
const tagged = commit("a");

class FakeContext {
  constructor(ref, sha, runId) {
    Object.assign(this, { ref, sha, runId, payload: { repository: { default_branch: "main" } } });
  }
  get repo() { return repo; }
}

const run = (id, workflow, fields = {}) => ({ id, workflow, event: "push", head_branch: "main", head_sha: c0,
  conclusion: "success", run_attempt: 1, html_url: `https://github.com/dsw-nrp/eosc-fair-guide/actions/runs/${id}`,
  head_repository: own, ...fields });
const job = (name, conclusion = "success") => ({ name, conclusion });

/** GitHub as the deployment code reads it; the newest run comes first, as in the API. */
function fake({ runs = [], jobs = {}, artifacts = {}, head = c3, commits = [c3, c2, c1, c0], tags = [], releases = {} } = {}) {
  const filtered = ({ workflow_id, branch, event, head_sha }) => runs
    .filter((entry) => entry.workflow === workflow_id && (!branch || entry.head_branch === branch) &&
      (!event || entry.event === event) && (!head_sha || entry.head_sha === head_sha))
    .sort((a, b) => b.id - a.id);
  return {
    paginate: async (method, options) => {
      const { data } = await method(options);
      return data.workflow_runs ?? data.jobs ?? data;
    },
    rest: {
      actions: {
        getWorkflowRun: async ({ run_id }) => ({ data: runs.find((entry) => entry.id === run_id) }),
        listWorkflowRuns: async (options) => ({ data: { workflow_runs: filtered(options) } }),
        listJobsForWorkflowRun: async ({ run_id }) => ({ data: { jobs: jobs[run_id] || [] } }),
        listWorkflowRunArtifacts: async ({ run_id, name }) => ({
          data: { artifacts: (artifacts[run_id] || []).filter((entry) => entry.name === name) } }),
      },
      repos: {
        getBranch: async () => ({ data: { commit: { sha: head } } }),
        getCommit: async ({ ref }) => ({ data: { sha: Object.fromEntries(tags)[ref] } }),
        listCommits: async () => ({ data: commits.map((sha) => ({ sha })) }),
        listTags: async () => ({ data: tags.map(([name, sha]) => ({ name, commit: { sha } })) }),
        getReleaseByTag: async ({ tag }) => {
          if (releases[tag]) return { data: releases[tag] };
          throw Object.assign(Error("absent"), { status: 404 });
        },
      },
    },
  };
}
const kept = (expired = false) => [{ name: "staging-site", expired }];

// A staging deployment reuses only the passing merge-queue run of exactly this commit in this repository.
{
  const branch = new FakeContext("refs/heads/main", c3, 50);
  const queue = run(40, "checks.yml", { event: "merge_group", head_branch: "gh-readonly-queue/main/pr-7-x", head_sha: c3, run_attempt: 2 });
  let github = fake({ runs: [queue, run(41, "checks.yml", { event: "pull_request", head_sha: c3 })] });
  assert.deepEqual(await queueResult({ github, context: branch }),
    { run: "40", attempt: "2", url: queue.html_url, reason: "" });
  for (const [runs, reason] of [
    [[run(41, "checks.yml", { event: "pull_request", head_sha: c3 })], /no merge-queue run checked this commit/],
    [[{ ...queue, conclusion: "failure" }], /ended with failure/],
    [[{ ...queue, conclusion: null }], /has not finished/],
    [[{ ...queue, head_repository: { full_name: "someone/fork" } }], /no merge-queue run checked this commit/],
    [[{ ...queue, head_sha: c2 }], /no merge-queue run checked this commit/],
  ]) {
    github = fake({ runs });
    const result = await queueResult({ github, context: branch });
    assert.equal(result.run, "", String(reason));
    assert.match(result.reason, reason);
  }
  // Even if the API returned a pull-request run of the same commit, it never stands in for the queue.
  github = fake();
  github.rest.actions.listWorkflowRuns = async () => ({ data: { workflow_runs: [run(41, "checks.yml", { event: "pull_request", head_sha: c3 })] } });
  assert.equal((await queueResult({ github, context: branch })).run, "");
  await assert.rejects(queueResult({ github, context: new FakeContext("refs/heads/main", "HEAD", 50) }), /full source SHA/);
}

// The newest checked staging site is the newest default-branch commit whose run kept one, never a rerun of an old run.
{
  const runs = [run(10, "deploy.yml", { head_sha: c1 }), run(11, "deploy.yml", { head_sha: c2 }),
    run(12, "deploy.yml", { head_sha: c3, conclusion: null }), run(13, "deploy.yml", { head_sha: c0 }),
    run(14, "deploy.yml", { head_branch: "v1.0.0", head_sha: tagged })];
  const github = fake({ runs, artifacts: { 10: kept(), 11: kept(true), 13: kept(), 14: kept() } });
  assert.deepEqual(await newestStaging(github, new FakeContext("refs/tags/v1.0.0", tagged, 14), "main"), { commit: c1, run: "10" });
  assert.equal(await newestStaging(fake({ runs }), new FakeContext("refs/tags/v1.0.0", tagged, 14), "main"), null);
}

// Publication follows only a successful deployment run of this repository, from a push or a manual run.
{
  const deployRun = (fields) => run(80, "deploy.yml", { head_sha: c3, path: ".github/workflows/deploy.yml", ...fields });
  const following = (runs, tags = []) => {
    const context = new FakeContext("refs/heads/main", c3, 99);
    context.payload.workflow_run = { id: 80 };
    return completedDeployment({ github: fake({ runs, tags }), context });
  };
  const branch = await following([deployRun()]);
  assert.deepEqual([branch.ref, branch.sha, branch.runId, branch.repo], ["refs/heads/main", c3, 80, repo]);
  assert.equal((await following([deployRun({ event: "workflow_dispatch" })])).ref, "refs/heads/main");
  const tag = await following([deployRun({ head_branch: "v1.0.0", head_sha: tagged })], [["v1.0.0", tagged]]);
  assert.deepEqual([tag.ref, tag.sha], ["refs/tags/v1.0.0", tagged]);
  for (const [fields, reason] of [
    [{ conclusion: "failure" }, /Not a successful repository deployment/],
    [{ conclusion: "cancelled" }, /Not a successful repository deployment/],
    [{ event: "pull_request" }, /Not a successful repository deployment/],
    [{ path: ".github/workflows/checks.yml" }, /Not a successful repository deployment/],
    [{ head_repository: { full_name: "someone/fork" } }, /Not a successful repository deployment/],
    [{ head_branch: "feature" }, /Not a release tag/],
  ]) {
    await assert.rejects(following([deployRun(fields)]), reason, JSON.stringify(fields));
  }
  await assert.rejects(following([deployRun({ head_branch: "v1.0.0", head_sha: tagged })], [["v1.0.0", c2]]), /tag moved/);
}

// After a default-branch deployment: its own staging site while it is the head, beside the newest approved release.
const approvedTag = { runs: [run(30, "deploy.yml", { head_branch: "v1.0.0", head_sha: tagged, conclusion: null })],
  jobs: { 30: [job("production"), job("approve-production")] } };
const publish = (github, context, recorded = c3) => publication({ github, context, recorded });
{
  const github = fake({ runs: [run(60, "deploy.yml", { head_sha: c3 }), ...approvedTag.runs],
    jobs: approvedTag.jobs, tags: [["v1.0.0", tagged]] });
  assert.deepEqual(await publish(github, new FakeContext("refs/heads/main", c3, 60)),
    { publish: "true", reason: "", successor: "", staging: c3, staging_run: "60", tag: "v1.0.0", production: tagged,
      production_run: "30" }, "a release approved while this run prepared is included");
  assert.deepEqual(await publish(fake(), new FakeContext("refs/heads/main", c3, 60)),
    { publish: "true", reason: "", successor: "", staging: c3, staging_run: "60", tag: "", production: "", production_run: "" },
    "a first preview needs no release");
}

// An older deployment, or a retry of one, publishes nothing and names the run for the head.
{
  const github = fake({ runs: [run(60, "deploy.yml", { head_sha: c2 }), run(61, "deploy.yml", { head_sha: c3, conclusion: null })] });
  const result = await publish(github, new FakeContext("refs/heads/main", c2, 60));
  assert.equal(result.publish, "false");
  assert.match(result.reason, new RegExp(`moved on to ${c3}`));
  assert.equal(result.successor, run(61, "deploy.yml").html_url);
  assert.equal(result.staging, "", "nothing is downloaded or assembled");
}

// The Pages record names the head when this publication started; after a later push, that push's run publishes.
{
  const github = fake({ runs: [run(60, "deploy.yml", { head_sha: c2 }), run(61, "deploy.yml", { head_sha: c3, conclusion: null })] });
  const result = await publish(github, new FakeContext("refs/heads/main", c2, 60), c2);
  assert.equal(result.publish, "false");
  assert.match(result.reason, /after this publication started/);
  assert.equal(result.successor, run(61, "deploy.yml").html_url);
  await assert.rejects(publish(github, new FakeContext("refs/heads/main", c3, 61), ""), /full source SHAs/);
}

// The default branch advances while a tag waits: the branch keeps the last approved production.
{
  const waiting = { ...approvedTag.runs[0], head_branch: "v1.1.0", head_sha: commit("b"), id: 31 };
  const github = fake({ runs: [run(62, "deploy.yml", { head_sha: c3 }), approvedTag.runs[0], waiting],
    jobs: { ...approvedTag.jobs, 31: [job("production"), job("approve-production", null)] },
    tags: [["v1.1.0", commit("b")], ["v1.0.0", tagged]] });
  const result = await publish(github, new FakeContext("refs/heads/main", c3, 62));
  assert.deepEqual([result.publish, result.tag, result.production_run], ["true", "v1.0.0", "30"]);
}

// A tag approved after the branch moved on publishes with the head's checked staging site.
{
  const runs = [run(20, "deploy.yml", { head_sha: c2 }), run(21, "deploy.yml", { head_sha: c3 }),
    { ...approvedTag.runs[0], id: 22, conclusion: "success" }];
  const github = fake({ runs, artifacts: { 20: kept(), 21: kept() }, tags: [["v1.0.0", tagged]] });
  assert.deepEqual(await publish(github, new FakeContext("refs/tags/v1.0.0", tagged, 22)),
    { publish: "true", reason: "", successor: "", staging: c3, staging_run: "21", tag: "v1.0.0", production: tagged,
      production_run: "22" });
}

// While the head's own deployment still prepares, a tag publishes nothing; that deployment publishes it with the head.
{
  const runs = [run(20, "deploy.yml", { head_sha: c2 }), run(21, "deploy.yml", { head_sha: c3, conclusion: null }),
    { ...approvedTag.runs[0], id: 22, conclusion: "success" }];
  for (const artifacts of [{ 20: kept() }, {}]) {
    const github = fake({ runs, artifacts, tags: [["v1.0.0", tagged]] });
    const result = await publish(github, new FakeContext("refs/tags/v1.0.0", tagged, 22));
    assert.equal(result.publish, "false", "an older staging site would make the Pages record name the wrong commit");
    assert.match(result.reason, /has no checked staging site yet; its deployment publishes this release/);
    assert.equal(result.successor, run(21, "deploy.yml").html_url);
  }
  // That deployment's publication then includes the release its now successful run approved.
  const github = fake({ runs: [{ ...runs[1], conclusion: "success" }, runs[2]], tags: [["v1.0.0", tagged]] });
  const result = await publish(github, new FakeContext("refs/heads/main", c3, 21));
  assert.deepEqual([result.publish, result.staging, result.tag, result.production_run], ["true", c3, "v1.0.0", "22"]);
}

// A tag approved after a newer one publishes the newest approved release, everything the newer tag's waiting
// publication, which it may have replaced, would have published.
{
  const newer = { ...approvedTag.runs[0], id: 23, head_branch: "v1.1.0", head_sha: commit("b"), conclusion: "success" };
  const runs = [run(21, "deploy.yml", { head_sha: c3 }), { ...approvedTag.runs[0], id: 22, conclusion: "success" }, newer];
  const github = fake({ runs, artifacts: { 21: kept() }, tags: [["v1.1.0", commit("b")], ["v1.0.0", tagged]] });
  assert.deepEqual(await publish(github, new FakeContext("refs/tags/v1.0.0", tagged, 22)),
    { publish: "true", reason: "", successor: "", staging: c3, staging_run: "21", tag: "v1.1.0", production: commit("b"),
      production_run: "23" });
}

// Release assets supply production bytes without any run; deciding fetches none of them.
{
  const name = "eosc-fair-guide-site-1.0.0-aaaaaaaaaaaa.tar.gz";
  const assets = ["manifest.json", name, `${name}.sha256`].map((file, index) => ({ id: index + 1, name: file, size: 1 }));
  const github = fake({ tags: [["v1.0.0", tagged]], releases: { "v1.0.0": { draft: false, assets } } });
  github.rest.repos.getReleaseAsset = async () => assert.fail("the decision downloads no release asset");
  const result = await publish(github, new FakeContext("refs/heads/main", c3, 63));
  assert.deepEqual([result.publish, result.tag, result.production, result.production_run], ["true", "v1.0.0", tagged, ""]);
}
await assert.rejects(publish(fake(), new FakeContext("refs/heads/feature", c3, 64)), /default branch or a release tag/);

// A cancelled run names the run that supersedes it.
{
  const github = fake({ runs: [run(70, "deploy.yml", { head_sha: c2 }), run(71, "deploy.yml", { head_sha: c3, conclusion: null })] });
  assert.match(await superseded({ github, context: new FakeContext("refs/heads/main", c2, 70) }), /\[run 71\]\(.*\/runs\/71\) supersedes it/);
  assert.match(await superseded({ github, context: new FakeContext("refs/heads/main", c3, 71) }), /next deployment of this ref/);
}
console.log("check_publication: same-commit queue reuse, trusted publication trigger, newest checked staging, approved production, late approvals, exact Pages records and superseded runs pass");
