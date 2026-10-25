// Every trusted publisher's output ends with who acts next, the way round a blocker and the evidence of completion,
// and the shared helper refuses a missing element, so no renderer can drop one silently.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { handoff } = require("../../.github/scripts/handoff.cjs");
const { body } = require("../../.github/scripts/comment-summary.cjs");
const { reply } = require("../../.github/scripts/source-publisher.cjs");
const { superseded } = require("../../.github/scripts/deployment.cjs");
const { outcome } = require("../../.github/scripts/commands.cjs");

const LABELS = ["Next", "If blocked", "Done when"];
function endsWithHandoff(text, why) {
  const tail = String(text).trim().split("\n").filter((line) => line.trim()).slice(-3);
  assert.deepEqual(tail.map((line) => line.split(":**")[0]), LABELS.map((label) => `- **${label}`), why);
  for (const line of tail) assert(line.split(":** ")[1]?.trim(), `${why}: ${line} says nothing`);
  return tail;
}

for (const missing of ["next", "blocked", "done"]) {
  const values = { next: "act", blocked: "work round", done: "evidence", [missing]: " " };
  assert.throws(() => handoff(values), /needs its/, `${missing} is required`);
}

// The review comment: only a successful run reads as one.
const run = { id: 7, conclusion: "success", head_sha: "a".repeat(40) };
const report = { formatVersion: 1, head: run.head_sha, total: 0, items: [] };
const passed = endsWithHandoff(body(run, report, "dsw-nrp/eosc-fair-guide"), "a passed review comment");
assert.match(passed[0], /a reviewer reviews the change/);
const failed = endsWithHandoff(body({ ...run, conclusion: "failure" }, report, "dsw-nrp/eosc-fair-guide"), "a failed review comment");
assert.match(failed[0], /the author fixes the failed checks/);
assert.doesNotMatch(failed.join("\n"), /merged through the queue/, "a failure never claims what success would");
const huge = body(run, { ...report, total: 40, items: Array(40).fill({ id: "&".repeat(400), kind: "&".repeat(400),
  change: "updated", name: { cs: "&".repeat(400), en: "&".repeat(400) } }), complete: "changes.json" }, "dsw-nrp/eosc-fair-guide");
endsWithHandoff(huge, "a comment at its size limit keeps its handoff");

// Command and refresh replies, and a superseded deployment.
const posted = [];
const github = { rest: { issues: { createComment: async (entry) => posted.push(entry.body), createReaction: async () => {} },
  reactions: { createForIssueComment: async () => {} } } };
const context = { repo: { owner: "dsw-nrp", repo: "eosc-fair-guide" }, serverUrl: "https://github.com", runId: 9,
  payload: { issue: { number: 3 }, comment: { id: 4 } } };
await outcome({ github, context }, "fix-duplicates", "cancelled");
endsWithHandoff(posted.at(-1), "a cancelled command");
await outcome({ github, context }, "fix-duplicates", "failure");
endsWithHandoff(posted.at(-1), "a failed repair");
for (const [results, code, publication] of [[JSON.stringify({ re3data: "proposed" }), "0", ""], ["{}", "1", ""], ["{}", "0", "failure"]]) {
  endsWithHandoff(await reply({ github, context }, results, code, publication), `a refresh reply (${results}, ${publication})`);
}
const runs = { rest: { actions: { listWorkflowRuns: async () => ({ data: { workflow_runs: [] } }) } },
  paginate: async () => [] };
endsWithHandoff(await superseded({ github: runs, context: { ...context, ref: "refs/heads/main", runId: 9 } }), "a superseded deployment");
console.log("check_handoff: required elements, review comments by conclusion, command, refresh and deployment replies end with their next step");
