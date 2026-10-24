// Trusted default-branch code for comment commands. A comment is read only as data, never as shell text. This file
// decides which command a comment names before any job with write access runs, and computes who may use a command
// where; `/help` and the command gate share that eligibility, so they cannot disagree.
const { SOURCES, parseCommand: parseRefresh, authorized } = require("./source-publisher.cjs");
const { marker: REVIEW_MARKER, SUGGESTED_FIXES } = require("./comment-summary.cjs");

const HELP_MARKER = "<!-- fair-guide-command-help -->";
const BOT = "github-actions[bot]";
const SOURCE_KEYS = Object.keys(SOURCES);
const COMMANDS = {
  "/fix-duplicates": "Commits the safe duplicate links listed in the Guide review comment to this pull request, with a provenance action naming you and its registered identifier.",
  "/refresh": `Refreshes one snapshot source from the default branch into its own refresh pull request: \`/refresh <source>\` with ${SOURCE_KEYS.map((key) => `\`${key}\``).join(", ")}.`,
  "/help": "Lists the commands that apply here and whether you may use them.",
};
const CONTRIBUTING = "CONTRIBUTING.md#fixing-a-duplicate-from-a-pull-request";

/** Edit distance, for "did you mean" on a mistyped command. */
function distance(a, b) {
  const row = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i++) {
    let previous = row[0];
    row[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const kept = row[j];
      row[j] = Math.min(row[j] + 1, row[j - 1] + 1, previous + (a[i - 1] === b[j - 1] ? 0 : 1));
      previous = kept;
    }
  }
  return row[b.length];
}

/** The command a comment names. Only a first word shaped like a slash command is addressed to this workflow;
    a known command with wrong arguments, or a near miss of one, gets help instead of silence. */
function parse(body) {
  const text = String(body || "").trim();
  const word = /^\/[a-z][a-z-]{0,39}(?=\s|$)/.exec(text)?.[0];
  if (!word) return { command: "" };
  if (word === "/help") return { command: "help" };
  if (word === "/fix-duplicates") {
    return text === word ? { command: "fix-duplicates" } : { command: "unknown", notice: "`/fix-duplicates` takes no arguments." };
  }
  if (word === "/refresh") {
    const source = parseRefresh(text);
    return source ? { command: "refresh", source } : { command: "unknown", notice: "`/refresh` needs exactly one source key from the list below." };
  }
  const [near, gap] = Object.keys(COMMANDS).map((name) => [name, distance(word, name)]).sort((a, b) => a[1] - b[1])[0];
  return gap <= 3 ? { command: "unknown", notice: `\`${word}\` is not a command; did you mean \`${near}\`?` } : { command: "" };
}

/** Whether `command` may run for the commenter here, with every reason it may not. The handler repeats the write
    access and pull-request part in `fix_duplicates.py` (`can_write`, `admitted`); a parity test runs both on one table. */
async function eligibility({ github, context }, command, appConfigured) {
  const repo = context.repo;
  const reasons = [];
  const pull = context.payload.issue?.pull_request ? context.payload.issue.number : null;
  if (!(await authorized(github, repo, context.payload.comment?.user?.login))) reasons.push("it needs current write access to this repository");
  if (!appConfigured) reasons.push("the repository's GitHub App is not configured");
  if (pull === null) {
    reasons.push("it runs only from a pull-request comment");
  } else if (command === "fix-duplicates") {
    const { data } = await github.rest.pulls.get({ ...repo, pull_number: pull });
    const main = data.base?.repo?.default_branch;
    if (data.state !== "open") reasons.push("the pull request is not open");
    if (data.head?.repo?.full_name !== `${repo.owner}/${repo.repo}`) reasons.push("it does not run on pull requests from forks");
    if (data.base?.ref !== main || data.head?.ref === main) reasons.push("the pull request must target the default branch from another branch");
  }
  return { available: !reasons.length, reasons };
}

const runUrl = (context) => `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
const docsUrl = (context) => `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/blob/HEAD/${CONTRIBUTING}`;

async function react({ github, context }, content) {
  const comment = context.payload.comment?.id;
  if (Number.isSafeInteger(comment)) await github.rest.reactions.createForIssueComment({ ...context.repo, comment_id: comment, content });
}

/** The safe links the latest trusted review comment offers, as the command would read them from the same checks. */
async function suggestionsListed({ github, context }) {
  const comments = await github.paginate(github.rest.issues.listComments, { ...context.repo, issue_number: context.payload.issue.number, per_page: 100 });
  const review = comments.find((entry) => entry.user?.login === BOT && String(entry.body || "").startsWith(REVIEW_MARKER));
  return review ? String(review.body).includes(SUGGESTED_FIXES) : null;
}

function helpBody({ login, notice, pull, fix, refresh, suggestions, context }) {
  const cell = (result) => (result.available ? "Available" : "Not available: " + result.reasons.join("; "));
  const lines = [HELP_MARKER, "### Commands", ""];
  if (notice) lines.push(notice, "");
  lines.push(`Answered for \`${login}\` on this ${pull ? "pull request" : "issue"}. Post a command as the whole comment.`, "",
    "| Command | For you here | What it does |", "| --- | --- | --- |",
    `| \`/fix-duplicates\` | ${cell(fix)} | ${COMMANDS["/fix-duplicates"]} |`,
    `| \`/refresh <source>\` | ${cell(refresh)} | ${COMMANDS["/refresh"]} |`,
    `| \`/help\` | Available | ${COMMANDS["/help"]} |`, "");
  if (pull && suggestions === true) lines.push("The latest Guide review comment lists safe duplicate links, so `/fix-duplicates` has a repair to apply.", "");
  if (pull && suggestions === false) lines.push("The latest Guide review comment lists no safe duplicate link, so `/fix-duplicates` would change nothing.", "");
  lines.push("`/fix-duplicates` also needs a reviewed `[[person]]` whose `github` is your login and the `duplicate-fix` instrument on the branch; it refuses and explains when either is missing.", "",
    `**Next:** use an available command, or ask a maintainer to run it. Without a command, run \`python scripts/check_duplicates.py --fix\` locally; see [the contributing guide](${docsUrl(context)}).`);
  return lines.join("\n");
}

/** Answer `/help` or a near miss in one bot-maintained comment per thread, so asking again never adds comments. */
async function help({ github, context, core }, appConfigured = process.env.APP_CONFIGURED === "true") {
  const parsed = parse(context.payload.comment?.body);
  const pull = Boolean(context.payload.issue?.pull_request);
  const fix = await eligibility({ github, context }, "fix-duplicates", appConfigured);
  const refresh = await eligibility({ github, context }, "refresh", appConfigured);
  const suggestions = pull ? await suggestionsListed({ github, context }) : null;
  const text = helpBody({ login: context.payload.comment?.user?.login || "unknown", notice: parsed.notice, pull, fix, refresh, suggestions, context });
  const issue = context.payload.issue.number;
  const comments = await github.paginate(github.rest.issues.listComments, { ...context.repo, issue_number: issue, per_page: 100 });
  const own = comments.find((entry) => entry.user?.login === BOT && String(entry.body || "").startsWith(HELP_MARKER));
  if (own) await github.rest.issues.updateComment({ ...context.repo, comment_id: own.id, body: text });
  else await github.rest.issues.createComment({ ...context.repo, issue_number: issue, body: text });
  await react({ github, context }, "+1");
  core?.info(`Help answered on #${issue}`);
  return text;
}

const ACTIVE = ["queued", "in_progress", "waiting", "pending", "requested"];
const runTitle = (number) => `Comment on #${number}`;

/** An earlier run that holds or awaits the resource this command changes, so the requester knows why it waits:
    the same pull request for a repair, any refresh for a refresh, since refreshes share one queue. */
async function waitingBehind({ github, context }, command) {
  const prefix = (command === "refresh" ? "refresh" : "fix-duplicates") + " / ";
  const candidates = [];
  for (const status of ACTIVE) {
    const { data } = await github.rest.actions.listWorkflowRuns({ ...context.repo, workflow_id: "commands.yml", status, per_page: 20 });
    candidates.push(...data.workflow_runs.filter((run) => run.id < context.runId &&
      (command === "refresh" || run.display_title === runTitle(context.payload.issue.number))));
    if (command === "refresh") {
      const { data: scheduled } = await github.rest.actions.listWorkflowRuns({ ...context.repo, workflow_id: "source-refresh.yml", status, per_page: 20 });
      const earlier = scheduled.workflow_runs.find((run) => run.id < context.runId);
      if (earlier) return earlier;
    }
  }
  for (const run of candidates.sort((a, b) => a.id - b.id)) {
    const { data } = await github.rest.actions.listJobsForWorkflowRun({ ...context.repo, run_id: run.id, per_page: 50 });
    if (data.jobs.some((job) => job.name.startsWith(prefix) && ACTIVE.includes(job.status))) return run;
  }
  return null;
}

/** Accept a privileged command with an immediate reaction, or refuse it with the reasons and what to do instead. */
async function acknowledge({ github, context, core }, appConfigured = process.env.APP_CONFIGURED === "true") {
  const parsed = parse(context.payload.comment?.body);
  if (!["fix-duplicates", "refresh"].includes(parsed.command)) return false;
  const result = await eligibility({ github, context }, parsed.command, appConfigured);
  const name = parsed.command === "refresh" ? `\`/refresh ${parsed.source}\`` : "`/fix-duplicates`";
  if (!result.available) {
    await react({ github, context }, "confused");
    await github.rest.issues.createComment({ ...context.repo, issue_number: context.payload.issue.number,
      body: `${name} did not run because ${result.reasons.join("; ")}. Nothing was changed.\n\n**Next:** ask a maintainer to run it, or post \`/help\` to see what applies here. A local alternative is described in [the contributing guide](${docsUrl(context)}).` });
    core?.info(`${name} refused: ${result.reasons.join("; ")}`);
    return false;
  }
  await react({ github, context }, "eyes");
  const earlier = await waitingBehind({ github, context }, parsed.command);
  if (earlier) {
    await github.rest.issues.createComment({ ...context.repo, issue_number: context.payload.issue.number,
      body: `${name} is queued behind [an earlier run](${earlier.html_url}) that changes the same ${parsed.command === "refresh" ? "snapshots" : "pull request"}. It starts when that run finishes; nothing more is needed.` });
  }
  return true;
}

/** Close an accepted command: a reaction on success, and a reply whenever nothing else will explain the result. */
async function outcome({ github, context }, command, result) {
  if (result === "success") {
    await react({ github, context }, "rocket");
    return "success";
  }
  if (result !== "failure" && result !== "cancelled") return result;
  await react({ github, context }, "confused");
  const name = command === "refresh" ? "`/refresh`" : "`/fix-duplicates`";
  let body;
  if (result === "cancelled") {
    body = `${name} was cancelled before it finished, for example because too many commands were waiting for the same pull request or source, or because the run was cancelled. [Run](${runUrl(context)}).\n\n**Next:** check the branch, then post ${name} again to retry.`;
  } else if (command === "fix-duplicates") {
    body = `\`/fix-duplicates\` encountered an unexpected failure. Check the pull-request branch: a commit may already exist even though no success comment was posted. [Run](${runUrl(context)}).\n\n**Next:** if the branch has no repair commit, post \`/fix-duplicates\` again; otherwise review that commit and its checks.`;
  } else {
    return result; // The refresh run itself replies with each source's result, including failures.
  }
  await github.rest.issues.createComment({ ...context.repo, issue_number: context.payload.issue.number, body });
  return result;
}

module.exports = { parse, distance, eligibility, helpBody, help, acknowledge, waitingBehind, outcome, runTitle, HELP_MARKER, COMMANDS };
