// Trusted default-branch code: applies the live watch's issue plan (scripts/watch_sources.py) with stable keys, so
// a persistent problem has one issue that is updated rather than duplicated and is closed when it recovers.
const { readFileSync } = require("node:fs");

const LABEL = "guide-health";
const MAX_WRITES = 25;
const PLAN = ".cache/watch/issues.json";
const markerOf = (key) => `<!-- fair-guide-health key=${encodeURIComponent(key)} -->`;

function readPlan(read) {
  const plan = JSON.parse(read(PLAN, "utf8"));
  if (plan.format_version !== 1 || !Array.isArray(plan.actions)) throw Error("Invalid watch plan");
  for (const action of plan.actions) {
    if (typeof action.key !== "string" || !action.key || action.key.length > 500 || !["open", "close"].includes(action.action)) {
      throw Error("Invalid watch action");
    }
  }
  return plan.actions;
}

/** Apply the plan; returns counts of what happened. At most MAX_WRITES issue writes per run, opens first. */
async function apply({ github, context, core }, read = readFileSync) {
  const repo = context.repo;
  const actions = readPlan(read);
  const open = await github.paginate(github.rest.issues.listForRepo, { ...repo, state: "open", labels: LABEL, per_page: 100 });
  const byKey = new Map();
  for (const issue of open) {
    const match = /<!-- fair-guide-health key=([^ ]+) -->/.exec(String(issue.body || ""));
    if (match && !issue.pull_request) byKey.set(decodeURIComponent(match[1]), issue);
  }
  const counts = { opened: 0, updated: 0, closed: 0, unchanged: 0, deferred: 0 };
  let writes = 0;
  const ordered = [...actions.filter((action) => action.action === "open"), ...actions.filter((action) => action.action === "close")];
  for (const action of ordered) {
    const existing = byKey.get(action.key);
    if (action.action === "close" && !existing) continue;
    if (writes >= MAX_WRITES) { counts.deferred++; continue; }
    if (action.action === "open") {
      const body = `${String(action.body || "").slice(0, 60000)}\n\n${markerOf(action.key)}`;
      const title = String(action.title || action.key).slice(0, 200);
      if (existing && existing.body === body && existing.title === title) { counts.unchanged++; continue; }
      if (existing) {
        await github.rest.issues.update({ ...repo, issue_number: existing.number, title, body });
        counts.updated++;
      } else {
        await github.rest.issues.create({ ...repo, title, body, labels: [LABEL] });
        counts.opened++;
      }
    } else {
      await github.rest.issues.createComment({ ...repo, issue_number: existing.number, body: String(action.comment || "Recovered.").slice(0, 2000) });
      await github.rest.issues.update({ ...repo, issue_number: existing.number, state: "closed", state_reason: "completed" });
      counts.closed++;
    }
    writes++;
  }
  core.info(JSON.stringify(counts));
  return counts;
}

module.exports = { apply, markerOf, LABEL, MAX_WRITES };
