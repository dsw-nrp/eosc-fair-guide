// Trusted default-branch code: treats the PR artifact as bounded, escaped data and never executes it.
const { readFileSync, statSync } = require("node:fs");
const marker = "<!-- fair-guide-review-summary -->";
const escape = (value) => String(value).replace(/\s+/g, " ").slice(0, 400)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/([\\`*_{}\[\]()#!|])/g, "\\$1").replace(/@/g, "@\u200b");
const clean = (value, limit = 200) => String(value).replace(/[`\r\n]/g, " ").trim().slice(0, limit);
// Independent trusted validator; the Python/Node parity test covers this exact domain.
const placements = {
  resource: { re3data: ["content/resources.toml", "resource.repository"], fipDashboard: ["content/resources.toml", ""], knav: ["content/resources.toml", ""] },
  repository: { re3data: ["content/repositories.toml", ""], fipDashboard: ["content/repositories.toml", ""], knav: ["content/repositories.toml", ""] },
  source: { knav: ["content/sources.toml", ""] },
};
function validPlacement(item) {
  if (![item.entry, item.file, item.table, item.field].every((value) => typeof value === "string")) return false;
  const split = item.entry.indexOf(":");
  if (split <= 0 || split === item.entry.length - 1) return false;
  const kind = item.entry.slice(0, split);
  const fields = Object.hasOwn(placements, kind) ? placements[kind] : null;
  const target = fields && Object.hasOwn(fields, item.field) ? fields[item.field] : null;
  return Boolean(target && target[0] === item.file && target[1] === item.table);
}
const codeText = (value) => escape(clean(value, 400));
const COMMENT_LIMIT = 60000;
const SUGGESTION_COMMENT_LIMIT = 12;

function validSuggestion(item) {
  return item && typeof item === "object" &&
    typeof item.entry === "string" && item.entry.length <= 200 &&
    typeof item.record === "string" && item.record.length <= 200 &&
    item.resolution === "link" && item.safe === true &&
    validPlacement(item) &&
    typeof item.value === "string" && item.value.length > 0 && item.value.length <= 128 &&
    typeof item.reason === "string" && item.reason.length <= 400;
}

function suggestionLines(run, suggestions, repository) {
  if (!suggestions || suggestions.formatVersion !== 1 || suggestions.head !== run.head_sha ||
      (suggestions.repository && suggestions.repository !== repository) ||
      !Array.isArray(suggestions.suggestions) || suggestions.suggestions.length > 20) return [];
  const valid = suggestions.suggestions.filter(validSuggestion);
  const items = valid.slice(0, SUGGESTION_COMMENT_LIMIT);
  const dropped = suggestions.suggestions.length - valid.length;
  const omitted = valid.length - items.length;
  if (!items.length) return dropped ? ["", "### Suggested fixes", "", `${dropped} malformed suggestion(s) were omitted.`] : [];
  const lines = ["", "### Suggested fixes", ""];
  for (const item of items) {
    lines.push(`- \`${codeText(item.entry)}\` ← \`${codeText(item.record)}\`: \`${codeText(item.reason)}\``);
    const table = item.table || "entry";
    lines.push("  ```diff", `  --- ${item.file}`, `  +++ ${item.file}`,
      `  @@ ${table} (${clean(item.entry)})`, `  +${item.field} = "${clean(item.value)}"`, "  ```");
  }
  if (dropped) lines.push("", `${dropped} malformed suggestion(s) were omitted.`);
  if (omitted) lines.push("", `${omitted} additional suggestion(s) are in the suggestions artifact.`);
  return lines;
}

function matches(pr, run) {
  const source = run.head_repository?.full_name;
  return typeof source === "string" && /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(source) &&
    pr.state === "open" && pr.head?.sha === run.head_sha && pr.head.repo?.full_name === source;
}

function body(run, report, repository, suggestions = null) {
  if (!/^[0-9a-f]{40}$/.test(run.head_sha) || report.formatVersion !== 1 || report.head !== run.head_sha || !Array.isArray(report.items) || report.items.length > 200 ||
      !Number.isSafeInteger(report.total) || report.total < report.items.length || !Number.isSafeInteger(run.id) ||
      !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) throw Error("Invalid review artifact identity or bounds");
  const candidates = report.items.slice(0, 40);
  const suggestionText = suggestionLines(run, suggestions, repository).join("\n");
  const reserved = suggestionText.length + 500;
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
      if (lines.join("\n").length + row.length + reserved > COMMENT_LIMIT) break;
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
  if (suggestionText) lines.push(suggestionText);
  const text = lines.join("\n");
  return text.length > COMMENT_LIMIT ? text.slice(0, COMMENT_LIMIT - 40) + "\n\n… comment truncated." : text;
}

function readReport(file) {
  if (statSync(file).size > 524288) throw Error("Review artifact exceeds 512 KiB");
  return JSON.parse(readFileSync(file, "utf8"));
}

function readOptional(file, read) {
  try {
    return read(file);
  } catch {
    return null;
  }
}

async function comment({ github, context, core }, read = readReport) {
  const run = context.payload.workflow_run;
  if (run.event !== "pull_request" || run.status !== "completed") return;
  const repository = context.repo.owner + "/" + context.repo.repo;
  const file = ".cache/pr-review-incoming/summary.json";
  const suggestions = readOptional(".cache/pr-review-incoming/suggestions.json", read);
  const text = body(run, read(file), repository, suggestions);
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

module.exports = { body, matches, comment, validSuggestion };
