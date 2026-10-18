// Trusted default-branch code for source refresh: selects reviewed source keys and publishes validated snapshot
// changes as one bot-owned pull request per source. It never writes the default branch, never merges, never runs
// pull-request code and never interpolates comment text into a command.
const { readFileSync, existsSync } = require("node:fs");
const { createHash } = require("node:crypto");

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
const MARKER = "<!-- fair-guide-source-refresh ";
const WRITERS = ["admin", "maintain", "write"];
const REPORT = ".cache/refresh/report.json";

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

/** Publish each changed source. Returns what happened per source, for the run log and the tests. The App's bot
    login (`<app-slug>[bot]`) tells its own commits from people's; without it every existing branch counts as edited. */
async function publish({ github, context, core }, read = readFileSync, exists = existsSync, bot = process.env.SOURCE_BOT_LOGIN) {
  const repo = context.repo;
  const base = context.payload.repository?.default_branch || "main";
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
    if (open) {
      const commits = await github.paginate(github.rest.pulls.listCommits, { ...repo, pull_number: open.number, per_page: 100 });
      if (!bot || commits.some((commit) => commit.author?.login !== bot)) {
        results[source] = "human-edits";
        await github.rest.issues.createComment({ ...repo, issue_number: open.number,
          body: `A newer ${source} refresh is available, but this branch has commits from people. They are kept; reconcile the refresh by hand or close this pull request so the next refresh can start from the default branch.` });
        continue;
      }
    }
    const current = await mainHead(github, repo, base);
    const tree = await github.rest.git.createTree({ ...repo, base_tree: current.tree,
      tree: files.map(([path, text]) => ({ path, mode: "100644", type: "blob", content: text })) });
    const commit = await github.rest.git.createCommit({ ...repo, message: `Refresh the ${source} snapshot`,
      tree: tree.data.sha, parents: [current.sha] });
    const ref = "heads/" + branch;
    const known = await github.rest.git.getRef({ ...repo, ref }).then(() => true, () => false);
    if (known) await github.rest.git.updateRef({ ...repo, ref, sha: commit.data.sha, force: true });
    else await github.rest.git.createRef({ ...repo, ref: "refs/" + ref, sha: commit.data.sha });
    const body = [`Validated refresh of the **${source}** snapshot from the default branch at \`${current.sha}\`.`, "",
      "The response passed the shape, completeness, size and removal checks of `scripts/refresh_snapshots.py`.",
      "Review the change as content; nothing merges automatically.", "", marker].join("\n");
    if (open) await github.rest.pulls.update({ ...repo, pull_number: open.number, body });
    else await github.rest.pulls.create({ ...repo, title: `Refresh the ${source} snapshot`, head: branch, base, body, maintainer_can_modify: true });
    results[source] = open ? "updated" : "proposed";
  }
  core.info(JSON.stringify(results));
  return results;
}

module.exports = { SOURCES, parseCommand, authorized, select, publish, hashOf, markerOf, branchOf };
