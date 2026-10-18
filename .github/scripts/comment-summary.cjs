// Trusted default-branch code: treats the PR artifact as bounded, escaped data and never executes it.
const { readFileSync, statSync } = require("node:fs");
const marker = "<!-- fair-guide-review-summary -->";
const escape = (value) => String(value).replace(/\s+/g, " ").slice(0, 400)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/([\\`*_{}\[\]()#!|])/g, "\\$1").replace(/@/g, "@\u200b");

function matches(pr, run) {
  const source = run.head_repository?.full_name;
  return typeof source === "string" && /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(source) &&
    pr.state === "open" && pr.head?.sha === run.head_sha && pr.head.repo?.full_name === source;
}

function body(run, report, repository) {
  if (!/^[0-9a-f]{40}$/.test(run.head_sha) || report.formatVersion !== 1 || report.head !== run.head_sha || !Array.isArray(report.items) || report.items.length > 200 ||
      !Number.isSafeInteger(report.total) || report.total < report.items.length || !Number.isSafeInteger(run.id) ||
      !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) throw Error("Invalid review artifact identity or bounds");
  const candidates = report.items.slice(0, 40);
  let shown = 0;
  const lines = [marker, "## Guide review", "", `Commit: \`${run.head_sha}\`. Run conclusion: **${escape(run.conclusion)}**.`, "",
    `[Checks, health report and desktop/mobile preview artifacts](https://github.com/${repository}/actions/runs/${run.id})`, "",
    `Changed authored items: **${report.total}**.`, ""];
  if (candidates.length) {
    lines.push("| Item | Change | Česky | English |", "| --- | --- | --- | --- |");
    for (const item of candidates) {
      if (typeof item.id !== "string" || !["added", "updated", "removed"].includes(item.change) ||
          typeof item.name?.cs !== "string" || typeof item.name?.en !== "string") throw Error("Invalid changed item");
      const row = `| ${escape(item.kind)}: ${escape(item.id)} | ${item.change} | ${escape(item.name.cs)} | ${escape(item.name.en)} |`;
      if (lines.join("\n").length + row.length > 59000) break;
      lines.push(row);
      shown++;
    }
  }
  if (report.total > shown) {
    // Claim a complete list only when the artifact says it carries one beside the bounded rows.
    const complete = report.complete === "changes.json"
      ? " Every changed item is listed in `changes.json` in the review artifact."
      : ` Only the first ${report.items.length} changed items are in the review artifact.`;
    lines.push("", `The table shows ${shown} of ${report.total} changed items within the comment size limit.${complete}`);
  }
  return lines.join("\n");
}

function readReport(file) {
  if (statSync(file).size > 524288) throw Error("Review artifact exceeds 512 KiB");
  return JSON.parse(readFileSync(file, "utf8"));
}

async function comment({ github, context, core }, read = readReport) {
  const run = context.payload.workflow_run;
  if (run.event !== "pull_request" || run.status !== "completed") return;
  const repository = context.repo.owner + "/" + context.repo.repo;
  const file = ".cache/pr-review-incoming/summary.json";
  const text = body(run, read(file), repository);
  const listed = run.pull_requests?.length ? run.pull_requests : await github.paginate(github.rest.pulls.list, { ...context.repo, state: "open", per_page: 100 });
  for (const candidate of listed) {
    if (!Number.isSafeInteger(candidate.number)) continue;
    const { data: pr } = await github.rest.pulls.get({ ...context.repo, pull_number: candidate.number });
    if (!matches(pr, run)) continue;
    const comments = await github.paginate(github.rest.issues.listComments, { ...context.repo, issue_number: pr.number, per_page: 100 });
    const own = comments.find((entry) => entry.user?.login === "github-actions[bot]" && entry.body?.startsWith(marker));
    if (own) await github.rest.issues.updateComment({ ...context.repo, comment_id: own.id, body: text });
    else await github.rest.issues.createComment({ ...context.repo, issue_number: pr.number, body: text });
    core.info("Review summary posted for PR " + pr.number);
  }
}

module.exports = { body, matches, comment };
