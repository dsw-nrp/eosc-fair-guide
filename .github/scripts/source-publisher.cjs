// Trusted default-branch code for source refresh: selects reviewed source keys and publishes validated snapshot
// changes as one bot-owned pull request per source. It never writes the default branch, never merges, never runs
// pull-request code and never interpolates comment text into a command.
const { readFileSync, existsSync } = require("node:fs");
const { createHash } = require("node:crypto");
const { addLabels } = require("./labels.cjs");
const { handoff } = require("./handoff.cjs");

// The reviewed source keys and the files each refresh may change are authored once in
// `.github/source-registry.json` and read by `scripts/refresh_snapshots.py` too. The FIP Dashboard's interdependent
// collections are one file, so one commit replaces them together; FAIRsharing and DataCite read the repositories
// the catalogue lists, the re3data snapshot included, so they run after it.
const { sources: SOURCE_REGISTRY } = require("../source-registry.json");
if (!Array.isArray(SOURCE_REGISTRY) || SOURCE_REGISTRY.some((entry) =>
  !entry || typeof entry.key !== "string" || !Array.isArray(entry.files) || !entry.files.length)) {
  throw Error("Invalid source registry");
}
const SOURCES = Object.freeze(Object.fromEntries(SOURCE_REGISTRY.map(({ key, files }) => [key, files])));
const PREFIX = "refresh/";
const REFRESH_LABEL = "source-refresh";
const MARKER = "<!-- fair-guide-source-refresh ";
const WRITERS = ["admin", "maintain", "write"];
const REPORT = ".cache/refresh/report.json";
// A refresh branch may only move when it still points at the head whose commits were inspected. The `updateRefs`
// mutation compares `beforeOid` and applies its updates atomically, so an update cannot replace a head it never
// saw; the all-zero value confirms that a branch was absent when an absent one is created.
const ABSENT = "0".repeat(40);
const REF_UPDATE = "mutation($input: UpdateRefsInput!) { updateRefs(input: $input) { clientMutationId } }";

const branchOf = (source) => PREFIX + source;
const markerOf = (source, hash) => `${MARKER}source=${source} sha256=${hash} -->`;
const hashOf = (files) => createHash("sha256").update(files.map(([path, text]) => path + "\0" + text + "\0").join("")).digest("hex");

/** A refresh command is exactly "/refresh <source key>"; anything else, including extra words, is not one. */
function parseCommand(body) {
  const match = /^\/refresh ([a-z0-9-]{1,40})$/.exec(String(body || "").trim());
  return match && Object.hasOwn(SOURCES, match[1]) ? match[1] : null;
}

/** Whether the account currently has write access; checked at the time of the command, never assumed. */
async function authorized(github, repo, login) {
  if (typeof login !== "string" || !login) return false;
  try {
    const { data } = await github.rest.repos.getCollaboratorPermissionLevel({ ...repo, username: login });
    return WRITERS.includes(data.role_name) || ["admin", "write"].includes(data.permission);
  } catch (error) {
    return false;
  }
}

/** The source keys this run refreshes, space-separated: every key on a schedule, the chosen one on manual dispatch,
    and the commanded one for an authorized issue or pull-request comment. Nothing for anything else. */
async function select({ github, context, core }) {
  const repo = context.repo;
  if (context.eventName === "schedule") return Object.keys(SOURCES).join(" ");
  if (context.eventName === "workflow_dispatch") {
    const chosen = context.payload.inputs?.source;
    if (chosen === "all") return Object.keys(SOURCES).join(" ");
    return Object.hasOwn(SOURCES, chosen) ? chosen : "";
  }
  if (context.eventName === "issue_comment" && Number.isSafeInteger(context.payload.issue?.number) && context.payload.issue.number > 0) {
    const source = parseCommand(context.payload.comment?.body);
    if (!source) return "";
    if (!(await authorized(github, repo, context.payload.comment?.user?.login))) {
      core.info("Refresh command ignored: the commenter has no current write access.");
      return "";
    }
    return source;
  }
  return "";
}

function readReport(read) {
  const report = JSON.parse(read(REPORT, "utf8"));
  if (report.formatVersion !== 1 || !Array.isArray(report.outcomes)) throw Error("Invalid refresh report");
  return report;
}

async function mainHead(github, repo, base) {
  const { data } = await github.rest.git.getRef({ ...repo, ref: "heads/" + base });
  const { data: commit } = await github.rest.git.getCommit({ ...repo, commit_sha: data.object.sha });
  return { sha: data.object.sha, tree: commit.tree.sha };
}

/** The commit a branch points at, or null when it does not exist. */
async function branchHead(github, repo, ref) {
  try {
    return (await github.rest.git.getRef({ ...repo, ref })).data.object.sha;
  } catch (error) {
    if (error?.status === 404) return null;
    throw error;
  }
}

/** Move a refresh branch to the new snapshot commit only while it still points at the inspected commit. */
async function replaceBranch(github, repositoryId, name, before, after) {
  await github.graphql(REF_UPDATE, {
    input: { repositoryId, refUpdates: [{ name, beforeOid: before, afterOid: after, force: true }] },
  });
}

const refreshMessage = (source) => `Refresh the ${source} snapshot`;

/** Publish each changed source. Returns what happened per source, for the run log and the tests. The App's bot
    login (`<app-slug>[bot]`) tells its own commits from people's; without it every existing branch counts as edited. */
async function publish({ github, context, core }, read = readFileSync, exists = existsSync, bot = process.env.SOURCE_BOT_LOGIN) {
  const repo = context.repo;
  const base = context.payload.repository?.default_branch || "main";
  const repositoryId = context.payload.repository?.node_id;
  if (typeof repositoryId !== "string" || !repositoryId) throw Error("Missing repository identity");
  const results = {};
  for (const outcome of readReport(read).outcomes) {
    const source = outcome.source;
    if (!Object.hasOwn(SOURCES, source)) continue;
    if (outcome.status !== "changed") { results[source] = outcome.status; continue; }
    const files = SOURCES[source].filter((path) => exists(path)).map((path) => [path, read(path, "utf8")]);
    if (!files.length) { results[source] = "missing"; continue; }
    const hash = hashOf(files);
    const marker = markerOf(source, hash);
    const branch = branchOf(source);
    if (!branch.startsWith(PREFIX) || branch === base) throw Error("Refusing to write outside the reserved refresh branches");
    const head = `${repo.owner}:${branch}`;
    const open = (await github.paginate(github.rest.pulls.list, { ...repo, state: "open", head, base, per_page: 100 }))[0];
    const closed = await github.paginate(github.rest.pulls.list, { ...repo, state: "closed", head, base, per_page: 100 });
    if (closed.some((pr) => !pr.merged_at && String(pr.body || "").includes(marker))) {
      results[source] = "rejected-before";
      core.info(`${source}: this exact content was proposed and closed without merging; it is not proposed again.`);
      continue;
    }
    if (open && String(open.body || "").includes(marker)) { results[source] = "already-proposed"; continue; }
    const ref = "heads/" + branch;
    // The head is read before the inventory so an update is only allowed while the branch still points at the
    // commits this run inspected; a branch that moves afterwards keeps its newer head.
    const inspected = await branchHead(github, repo, ref);
    if (open) {
      let commits;
      try {
        commits = await github.paginate(github.rest.pulls.listCommits, { ...repo, pull_number: open.number, per_page: 100 });
      } catch {
        core.info(`${source}: unable to verify the branch commit inventory; preserving it.`);
      }
      if (!bot || !Array.isArray(commits) || !commits.length || commits.some((commit) =>
        commit?.author?.login !== bot || typeof commit.commit?.message !== "string" ||
        commit.commit.message.replace(/\n$/, "") !== refreshMessage(source))) {
        results[source] = "human-edits";
        await github.rest.issues.createComment({ ...repo, issue_number: open.number,
          body: `A newer ${source} refresh is available, but this branch cannot be verified as containing only the refresh App's expected snapshot commits. Its repairs and other changes are kept; reconcile the refresh by hand or close this pull request so the next refresh can start from the default branch.` });
        continue;
      }
    }
    const current = await mainHead(github, repo, base);
    const tree = await github.rest.git.createTree({ ...repo, base_tree: current.tree,
      tree: files.map(([path, text]) => ({ path, mode: "100644", type: "blob", content: text })) });
    const commit = await github.rest.git.createCommit({ ...repo, message: refreshMessage(source),
      tree: tree.data.sha, parents: [current.sha] });
    try {
      await replaceBranch(github, repositoryId, "refs/" + ref, inspected ?? ABSENT, commit.data.sha);
    } catch (error) {
      if ((await branchHead(github, repo, ref)) !== inspected) {
        results[source] = "moved";
        core.info(`${source}: the refresh branch moved after its commits were inspected; its current head is kept and the next run inspects it again.`);
        continue;
      }
      throw error;
    }
    const body = [`Validated refresh of the **${source}** snapshot from the default branch at \`${current.sha}\`.`, "",
      "The response passed the shape, completeness, size and removal checks of `scripts/refresh_snapshots.py`.", "",
      handoff({ next: "a maintainer reviews the snapshot change as content and merges it through the queue; nothing merges automatically.",
        blocked: "close this pull request if the change is wrong; identical content is not proposed again.",
        done: "this pull request is merged or closed." }), "", marker].join("\n");
    if (open) await github.rest.pulls.update({ ...repo, pull_number: open.number, body });
    const pr = open || (await github.rest.pulls.create({ ...repo, title: `Refresh the ${source} snapshot`, head: branch, base, body, maintainer_can_modify: true })).data;
    // The review publisher adds the area label from the changed paths once the checks have run.
    const { absent } = await addLabels(github, repo, pr.number, [REFRESH_LABEL], pr.labels || []);
    if (absent.length) core.info(`${source}: the ${REFRESH_LABEL} label does not exist yet; the next refresh adds it.`);
    results[source] = open ? "updated" : "proposed";
  }
  core.info(JSON.stringify(results));
  return results;
}

// What each publication result means for the person who commanded the refresh, and what they can do next.
const OUTCOMES = {
  proposed: "proposed as a new refresh pull request; review it as content",
  updated: "updated in its open refresh pull request; review the new commit",
  "already-proposed": "already proposed with the same content; review the open refresh pull request",
  unchanged: "unchanged; there is nothing to propose",
  empty: "empty at the source, so the snapshot was kept; check the source before refreshing again",
  rejected: "rejected by validation, so the snapshot was kept; the run summary names the reason",
  failed: "not retrieved, so the snapshot was kept; a later refresh retries it, and the run summary names the reason",
  "rejected-before": "identical to a proposal that was closed without merging, so it was not proposed again",
  "human-edits": "kept on its branch, which has commits other than the refresh App's; reconcile it by hand or close that pull request",
  moved: "kept on its branch, which moved during the run; post the command again to retry",
  missing: "not written, because the refresh produced no snapshot file",
};

/** Reply to a `/refresh` command with each source's result and the run, after the run, however it ended. A publication
    step that failed part-way may already have moved a branch or pull request, so it is never reported as no change. */
async function reply({ github, context }, results, code, publication = "") {
  let parsed = {};
  try {
    parsed = JSON.parse(results || "{}");
  } catch {
    parsed = {};
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) parsed = {};
  const run = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const rows = [];
  for (const [source, status] of Object.entries(parsed).filter(([key]) => Object.hasOwn(SOURCES, key))) {
    let proposal = "";
    if (["proposed", "updated", "already-proposed", "human-edits", "moved"].includes(status)) {
      try {
        const pulls = await github.paginate(github.rest.pulls.list, {
          ...context.repo, state: "open", head: `${context.repo.owner}:${branchOf(source)}`, per_page: 100,
        });
        const pull = pulls.find((entry) => Number.isSafeInteger(entry.number) && entry.number > 0);
        if (pull) proposal = ` [Proposal #${pull.number}](${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/pull/${pull.number}).`;
      } catch { /* Publication may have succeeded even if its proposal can no longer be read. */ }
      if (!proposal) proposal = " Proposal link unavailable; check the run and open refresh pull requests.";
    }
    rows.push(`- \`${source}\`: ${OUTCOMES[status] || "finished with an unrecognized result; see the run"}.${proposal}`);
  }
  let body;
  const retry = { blocked: "ask a maintainer, who can run Source refresh from its Actions page.",
    done: "`/refresh` replies with each source's result." };
  if (rows.length) {
    body = [`\`/refresh\` finished ([run](${run})):`, "", ...rows, "", handoff({
      next: "review each proposed or updated refresh pull request, and act on any other result listed above.",
      blocked: "the run summary gives each source's outcome and reason.",
      done: "each refresh pull request is merged or closed." })].join("\n");
  } else if (publication === "failure") {
    body = `\`/refresh\` stopped during publication, so its refresh branch or pull request may already have changed. [Run](${run}).\n\n` +
      handoff({ next: "check the open refresh pull request and the run log, then post the command again.", ...retry });
  } else {
    body = `\`/refresh\` did not reach publication${code && code !== "0" ? " because a source was rejected or failed" : ""}; no pull request was changed. [Run](${run}).\n\n` +
      handoff({ next: "read the run summary, which names the reason, then post the command again.", ...retry });
  }
  await github.rest.issues.createComment({ ...context.repo, issue_number: context.payload.issue.number, body });
  return body;
}

// A run fails only when a maintainer must act (decision 29); a source the next scheduled run retries is a warning.
const ACT = new Set(["rejected", "human-edits", "missing"]);
const RETRY = new Set(["failed", "empty", "moved"]);

/** The run summary of every refresh, scheduled or commanded: each source's outcome and reason, who acts next, and the
    run's own result. `publication` is the publish step's outcome; a publication that did not succeed may have left a
    refresh branch half-moved, so it always needs a maintainer. Returns the summary text. */
async function summarize({ core }, { results = "", publication = "", report = { outcomes: [] } } = {}) {
  let parsed = {};
  try {
    parsed = JSON.parse(results || "{}");
  } catch {
    parsed = {};
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) parsed = {};
  const refreshed = Object.fromEntries((report.outcomes || []).map((outcome) => [outcome.source, outcome]));
  const statuses = { ...Object.fromEntries(Object.entries(refreshed).map(([source, outcome]) => [source, outcome.status])), ...parsed };
  const published = publication === "success";
  const rows = Object.entries(statuses).filter(([source]) => Object.hasOwn(SOURCES, source)).map(([source, status]) => {
    const role = ACT.has(status) || (!published && status === "changed") ? "act" : RETRY.has(status) ? "retry" : "none";
    const reason = String(refreshed[source]?.reason || "").replace(/[|\r\n]+/g, " ").slice(0, 300);
    const text = status === "changed" && !published ? "changed, but publication did not complete" : OUTCOMES[status] || status;
    return { source, role, line: `| \`${source}\` | ${text} | ${role === "act" ? "**Act**" : role === "retry" ? "Retry" : "—"} | ${reason} |` };
  });
  const act = !published || rows.some((row) => row.role === "act");
  const retry = rows.some((row) => row.role === "retry");
  const next = act
    ? "a maintainer acts on each source marked **Act**: read its reason, then fix the source data or its parser in a pull request, or reconcile its refresh branch by hand; then run **Source refresh** for it again."
    : retry
      ? "nothing now: the next scheduled refresh retries each source marked Retry; run **Source refresh** for one to retry sooner."
      : "a maintainer reviews each proposed or updated refresh pull request as content and merges it through the queue.";
  const lines = ["## Source refresh", ""];
  if (!published) lines.push("Publication did not complete; a refresh branch or pull request may already have changed.", "");
  lines.push("| Source | Outcome | Who acts | Reason |", "| --- | --- | --- | --- |", ...rows.map((row) => row.line), "",
    handoff({ next, blocked: "the refresh report artifact keeps each source's raw outcome, and the maintenance digest lists the sources not refreshed.",
      done: act ? "a rerun marks no source **Act**." : "each refresh pull request is merged or closed." }));
  const text = lines.join("\n");
  await core.summary.addRaw(text + "\n").write();
  if (act) core.setFailed("At least one source needs a maintainer; the run summary names it and the next step.");
  else if (retry) core.warning("Some sources were not retrieved; the next scheduled refresh retries them. See the run summary.");
  return text;
}

module.exports = { SOURCES, parseCommand, authorized, select, publish, reply, summarize, hashOf, markerOf, branchOf, OUTCOMES,
  ACT, RETRY };
