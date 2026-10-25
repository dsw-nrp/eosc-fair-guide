// Trusted default-branch code for source refresh: selects reviewed source keys and publishes validated snapshot
// changes as one bot-owned pull request per source. It never writes the default branch, never merges, never runs
// pull-request code and never interpolates comment text into a command.
const { readFileSync, existsSync } = require("node:fs");
const { createHash } = require("node:crypto");
const { addLabels } = require("./labels.cjs");

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
    and the commanded one for an authorized pull-request comment. Nothing for anything else. */
async function select({ github, context, core }) {
  const repo = context.repo;
  if (context.eventName === "schedule") return Object.keys(SOURCES).join(" ");
  if (context.eventName === "workflow_dispatch") {
    const chosen = context.payload.inputs?.source;
    if (chosen === "all") return Object.keys(SOURCES).join(" ");
    return Object.hasOwn(SOURCES, chosen) ? chosen : "";
  }
  if (context.eventName === "issue_comment" && context.payload.issue?.pull_request) {
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
      "The response passed the shape, completeness, size and removal checks of `scripts/refresh_snapshots.py`.",
      "Review the change as content; nothing merges automatically.", "", marker].join("\n");
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
  rejected: "rejected by validation, so the snapshot was kept; the refresh report artifact names the reason",
  failed: "not retrieved, so the snapshot was kept; retry later or check the refresh report artifact",
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
  const run = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const rows = Object.entries(parsed).filter(([source]) => Object.hasOwn(SOURCES, source))
    .map(([source, status]) => `- \`${source}\`: ${OUTCOMES[status] || "finished with an unrecognized result; see the run"}.`);
  let body;
  if (rows.length) body = [`\`/refresh\` finished ([run](${run})):`, "", ...rows].join("\n");
  else if (publication === "failure") body = `\`/refresh\` stopped during publication, so its refresh branch or pull request may already have changed. [Run](${run}).\n\n**Next:** check the open refresh pull request and the run log, then post the command again or ask a maintainer.`;
  else body = `\`/refresh\` did not reach publication${code && code !== "0" ? " because a source was rejected or failed" : ""}; no pull request was changed. [Run](${run}).\n\n**Next:** read the run's refresh report, then post the command again or ask a maintainer.`;
  await github.rest.issues.createComment({ ...context.repo, issue_number: context.payload.issue.number, body });
  return body;
}

module.exports = { SOURCES, parseCommand, authorized, select, publish, reply, hashOf, markerOf, branchOf, OUTCOMES };
