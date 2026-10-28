// Trusted default-branch code: publishes the live watch's maintenance digest (scripts/watch_sources.py renders it).
// One open digest issue, created by this workflow's identity, carries an automation-owned body rebuilt every run; a
// comment is posted only for meaningful change and found again on a retry. Closing the digest is how a maintainer
// rotates it: the next run opens a successor that links its predecessor, posts the forward link and moves open tasks,
// each step repeatable until done. Maintainers' tasks (issues with a finding key, from people with write access) are
// attached as sub-issues. Two open digests stop publication. It also finds the run whose saved watch state the next
// observation continues, and the latest scheduled Source refresh whose report the digest lists. This module writes
// only issues of this repository.
const { readFileSync, writeFileSync, mkdirSync } = require("node:fs");
const { handoff } = require("./handoff.cjs");

const LABEL = "guide-health";
const TASK_LABEL = "area:maintenance";
const BOT = "github-actions[bot]";
const TITLE = "Maintenance digest";
const DIGEST = "<!-- fair-guide-digest -->";
const FINDING = /<!-- fair-guide-finding key=(\S+) outcome=(\S+) -->/;
const CONTINUES = /^Continues #(\d+)\.$/m;
const forwardOf = (number) => `<!-- fair-guide-digest-successor #${number} -->`;
const runOf = (id) => `<!-- fair-guide-digest-run id=${id} -->`;
const BODY = ".cache/digest/body.md";
const COMMENT = ".cache/digest/comment.md";
const TASKS = ".cache/digest/tasks.json";

/** Digest issues this workflow created, open and closed, newest first. Pull requests and other issues are ignored. */
async function digests(github, repo) {
  const issues = await github.paginate(github.rest.issues.listForRepo, { ...repo, state: "all", labels: LABEL,
    sort: "created", direction: "desc", per_page: 100 });
  return issues.filter((issue) => !issue.pull_request && issue.user?.login === BOT && String(issue.body || "").startsWith(DIGEST));
}

/** Before rendering: the predecessor a new digest would continue, and the maintainers' keyed tasks. */
async function prepare({ github, context, core }, write = writeFileSync) {
  const repo = context.repo;
  const found = await digests(github, repo);
  const open = found.filter((issue) => issue.state === "open");
  // A successor keeps naming its predecessor, so every rebuild re-checks the rotation until it is complete.
  const predecessor = open.length
    ? CONTINUES.exec(String(open[0].body || ""))?.[1] || ""
    : String(found.find((issue) => issue.state === "closed")?.number || "");
  const tasks = await keyedTasks(github, repo, new Set(found.map((issue) => issue.number)));
  mkdirSync(".cache/digest", { recursive: true });
  write(TASKS, JSON.stringify(tasks, null, 2) + "\n");
  core.setOutput("predecessor", predecessor);
  return { predecessor, tasks };
}

/** Issues carrying a finding key whose author has write access; anyone else's issue is never adopted. */
async function keyedTasks(github, repo, skip) {
  const issues = await github.paginate(github.rest.issues.listForRepo, { ...repo, state: "all", labels: TASK_LABEL, per_page: 100 });
  const access = new Map();
  const tasks = [];
  for (const issue of issues) {
    const match = FINDING.exec(String(issue.body || ""));
    if (!match || issue.pull_request || skip.has(issue.number)) continue;
    const login = issue.user?.login;
    if (!access.has(login)) {
      try {
        const { data } = await github.rest.repos.getCollaboratorPermissionLevel({ ...repo, username: login });
        access.set(login, ["admin", "write"].includes(data.permission));
      } catch { access.set(login, false); }
    }
    if (!access.get(login)) continue;
    tasks.push({ key: decodeURIComponent(match[1]), outcome: decodeURIComponent(match[2]), number: issue.number, id: issue.id,
      state: issue.state, reason: issue.state_reason || "", closed: issue.closed_at || "", url: issue.html_url });
  }
  return tasks;
}

/** Publish the rendered digest. Returns what happened, for the run summary and the tests. */
async function publish({ github, context, core }, read = readFileSync) {
  const repo = context.repo;
  const body = read(BODY, "utf8");
  const comment = read(COMMENT, "utf8").trim();
  const tasks = JSON.parse(read(TASKS, "utf8"));
  // Both inputs are checked before anything is written, so a malformed render never publishes half.
  if (!body.startsWith(DIGEST)) throw Error("The rendered digest lacks its marker");
  const run = comment ? /<!-- fair-guide-digest-run id=(\S+) -->/.exec(comment)?.[1] : "";
  if (comment && !run) throw Error("The rendered comment lacks its run marker");
  const open = (await digests(github, repo)).filter((issue) => issue.state === "open");
  if (open.length > 1) {
    const numbers = open.map((issue) => `#${issue.number}`).join(" and ");
    const text = `Two maintenance digests are open (${numbers}); nothing was written.`;
    core.warning(text);
    await core.summary.addRaw(text + "\n\n" + handoff({ next: "a maintainer closes the digest no longer needed.",
      blocked: "this run's observations artifact keeps what it found, and the next run reports it again.",
      done: "the next run rebuilds the one open digest." }) + "\n").write();
    core.setOutput("published", "false");
    return { refused: open.map((issue) => issue.number) };
  }
  const result = { created: false, updated: false, commented: false, adopted: [], moved: [], pinned: null };
  let digest = open[0];
  if (!digest) {
    // Both declared labels: `guide-health` finds the digest again, `area:maintenance` puts it in the Maintenance view.
    digest = (await github.rest.issues.create({ ...repo, title: TITLE, body, labels: [LABEL, TASK_LABEL] })).data;
    result.created = true;
    result.pinned = await pin(github, digest, core);
  } else if (digest.body !== body) {
    await github.rest.issues.update({ ...repo, issue_number: digest.number, body });
    result.updated = true;
  }
  const predecessor = Number(CONTINUES.exec(body)?.[1] || 0);
  if (predecessor) Object.assign(result, await rotate(github, repo, predecessor, digest.number));
  if (comment) {
    const existing = await github.paginate(github.rest.issues.listComments, { ...repo, issue_number: digest.number, per_page: 100 });
    if (!existing.some((entry) => String(entry.body || "").includes(runOf(run)))) {
      await github.rest.issues.createComment({ ...repo, issue_number: digest.number, body: comment });
      result.commented = true;
    }
  }
  const attached = new Set((await subIssues(github, repo, digest.number)).map((issue) => issue.number));
  // Closed tasks stay where they are, also after a rotation; the render still shows their disposition.
  for (const task of tasks) {
    if (attached.has(task.number) || task.state !== "open") continue;
    await github.request("POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues",
      { ...repo, issue_number: digest.number, sub_issue_id: task.id, replace_parent: true });
    result.adopted.push(task.number);
  }
  result.digest = digest.number;
  const parts = [`Maintenance digest #${digest.number}: ${result.created ? "opened" : result.updated ? "rebuilt" : "unchanged"}`];
  if (result.commented) parts.push("commented on the change");
  if (result.adopted.length) parts.push(`attached tasks ${result.adopted.map((n) => "#" + n).join(", ")}`);
  if (result.moved.length) parts.push(`moved tasks ${result.moved.map((n) => "#" + n).join(", ")} from #${predecessor}`);
  if (result.pinned === false) parts.push("could not pin it; pin it by hand");
  await core.summary.addRaw(parts.join("; ") + ".\n\n" + handoff({
    next: `a maintainer triages the digest's Needs triage section in #${digest.number}.`,
    blocked: "discuss a finding in a comment on the digest; a task created with **Track as task** is attached on the next run.",
    done: "a run's digest lists nothing under Needs triage." }) + "\n").write();
  // Only a published digest advances what the next run counts as already reported.
  core.setOutput("published", "true");
  return result;
}

async function subIssues(github, repo, number) {
  return github.paginate("GET /repos/{owner}/{repo}/issues/{issue_number}/sub_issues", { ...repo, issue_number: number, per_page: 100 });
}

/** Finish a rotation; each step is checked first, so an interrupted run completes it without repeating anything. */
async function rotate(github, repo, predecessor, successor) {
  const moved = [];
  const comments = await github.paginate(github.rest.issues.listComments, { ...repo, issue_number: predecessor, per_page: 100 });
  if (!comments.some((entry) => String(entry.body || "").includes(forwardOf(successor)))) {
    await github.rest.issues.createComment({ ...repo, issue_number: predecessor,
      body: `Continued in #${successor}, which carries every unresolved finding and open task.\n\n${forwardOf(successor)}` });
  }
  for (const task of await subIssues(github, repo, predecessor)) {
    if (task.state !== "open") continue;
    await github.request("POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues",
      { ...repo, issue_number: successor, sub_issue_id: task.id, replace_parent: true });
    moved.push(task.number);
  }
  return { moved };
}

const STATE = "health-watch-state";
const WORKFLOW = ".github/workflows/health-watch.yml";
const REFRESH_WORKFLOW = "source-refresh.yml";

/** The run whose durable watch state the next observation continues: the newest unexpired state artifact saved by
    this workflow on the default branch of this repository. A branch or fork run cannot supply state. */
async function previousState({ github, context, core }) {
  const repo = context.repo;
  const base = context.payload.repository?.default_branch || "main";
  const { data } = await github.rest.actions.listArtifactsForRepo({ ...repo, name: STATE, per_page: 30 });
  for (const artifact of data.artifacts || []) {
    const run = artifact.workflow_run || {};
    if (artifact.name !== STATE || artifact.expired || run.head_branch !== base || run.head_repository_id !== run.repository_id) continue;
    const { data: details } = await github.rest.actions.getWorkflowRun({ ...repo, run_id: run.id });
    if (String(details.path).split("@")[0] !== WORKFLOW || !["schedule", "workflow_dispatch"].includes(details.event)) continue;
    core.setOutput("run", String(run.id));
    return String(run.id);
  }
  core.setOutput("run", "");
  return "";
}

/** The latest completed scheduled Source refresh of the default branch and its report artifact, so the digest lists
    the sources it did not refresh (decision 29). A run without a readable report is still named, for an "unknown"
    entry; a failed lookup names nothing and says so as a warning. */
async function latestRefresh({ github, context, core }) {
  const repo = context.repo;
  const base = context.payload.repository?.default_branch || "main";
  const found = { run: "", url: "", date: "", artifact: "" };
  try {
    const { data } = await github.rest.actions.listWorkflowRuns({ ...repo, workflow_id: REFRESH_WORKFLOW, branch: base,
      event: "schedule", status: "completed", per_page: 10 });
    const run = (data.workflow_runs || []).find((entry) => entry.head_repository?.full_name === `${repo.owner}/${repo.repo}`);
    if (run && Number.isSafeInteger(run.id)) {
      const name = `source-refresh-${run.id}-${run.run_attempt || 1}`;
      const { data: listed } = await github.rest.actions.listWorkflowRunArtifacts({ ...repo, run_id: run.id, name, per_page: 10 });
      Object.assign(found, { run: String(run.id), url: run.html_url, date: String(run.run_started_at || run.created_at || "").slice(0, 10),
        artifact: (listed.artifacts || []).some((artifact) => artifact.name === name && !artifact.expired) ? name : "" });
    }
  } catch (error) {
    core.warning(`Could not find the latest scheduled Source refresh: ${error.message}`);
  }
  for (const [key, value] of Object.entries(found)) core.setOutput(key, value);
  return found;
}

/** Pinning is a convenience: a failure is reported, never fatal. */
async function pin(github, issue, core) {
  try {
    await github.graphql("mutation($id: ID!) { pinIssue(input: { issueId: $id }) { issue { id } } }", { id: issue.node_id });
    return true;
  } catch (error) {
    core.warning(`Could not pin maintenance digest #${issue.number}: ${error.message}`);
    return false;
  }
}

module.exports = { prepare, publish, keyedTasks, rotate, previousState, latestRefresh, LABEL, TASK_LABEL, BOT, DIGEST,
  TITLE, STATE, forwardOf, runOf };
