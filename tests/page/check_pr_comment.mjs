import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { body, matches, comment } = createRequire(import.meta.url)("../../.github/scripts/comment-summary.cjs");
const run = { id: 123, event: "pull_request", status: "completed", conclusion: "failure", head_sha: "a".repeat(40), head_repository: { full_name: "fork/guide" }, pull_requests: [{ number: 1 }, { number: 2 }] };
const item = { id: "dataset.01", kind: "question", change: "updated", name: { cs: "Text <script> @team | [link](evil)", en: "Changed question" } };
const report = { formatVersion: 1, head: run.head_sha, total: 1, items: [item] };
const text = body(run, report, "dsw-nrp/eosc-fair-guide");
assert(text.includes("Run conclusion: **failure**"), "run conclusion comes from the trusted event");
assert(!text.includes("<script>") && !text.includes("@team") && !text.includes("[link](evil)"), "artifact content cannot add HTML, mentions or links");
assert.throws(() => body(run, { ...report, head: "b".repeat(40) }, "dsw-nrp/eosc-fair-guide"));
assert.throws(() => body(run, { ...report, items: Array(201).fill(item), total: 201 }, "dsw-nrp/eosc-fair-guide"));
const pr = { number: 2, state: "open", head: { sha: run.head_sha, repo: { full_name: "fork/guide" } } };
assert(matches(pr, run));
assert(!matches({ ...pr, head: { ...pr.head, sha: "b".repeat(40) } }, run));
assert(!matches({ ...pr, head: { ...pr.head, repo: { full_name: "another/guide" } } }, run));
assert(!matches({ ...pr, head: { ...pr.head, repo: null } }, { ...run, head_repository: null }), "missing repository metadata cannot establish identity");
assert(!matches(pr, { ...run, head_repository: {} }));
const expanded = { id: "&".repeat(400), kind: "&".repeat(400), change: "updated", name: { cs: "&".repeat(400), en: "&".repeat(400) } };
const bounded = body(run, { ...report, total: 40, items: Array(40).fill(expanded), complete: "changes.json" }, "dsw-nrp/eosc-fair-guide");
assert(bounded.length < 60000, "escaped rows stay within the final comment size limit");
assert(bounded.includes("Every changed item is listed in `changes.json`"), "omitted rows have a discoverable complete artifact");
// More than 200 changes: the bounded summary carries 200 rows and the true total; completeness is claimed only
// when the artifact declares the complete list beside them.
const many = { ...report, total: 250, items: Array(200).fill(item) };
const declared = body(run, { ...many, complete: "changes.json" }, "dsw-nrp/eosc-fair-guide");
assert(declared.includes("Changed authored items: **250**") && declared.includes("of 250 changed items") && declared.includes("`changes.json`"));
const undeclared = body(run, many, "dsw-nrp/eosc-fair-guide");
assert(!undeclared.includes("changes.json") && undeclared.includes("Only the first 200 changed items are in the review artifact."), "no completeness claim without a complete list");
const suggestion = {
  entry: "resource:service", record: "re3data:r3d1", resolution: "link", safe: true,
  file: "content/resources.toml", table: "resource.repository", field: "re3data",
  value: "r3d1", reason: "shares <script> @team | [link](evil)",
};
const suggestions = { formatVersion: 1, head: run.head_sha, suggestions: [suggestion] };
const fixed = body(run, report, "dsw-nrp/eosc-fair-guide", suggestions);
assert(fixed.includes("### Suggested fixes"), "safe suggestions are shown");
assert(fixed.includes('re3data = "r3d1"'), "the exact field and value are shown");
assert(!fixed.includes("<script>") && !fixed.includes("@team") && !fixed.includes("[link](evil)"), "suggestion text stays escaped");
assert(!body(run, report, "dsw-nrp/eosc-fair-guide", { ...suggestions, head: "b".repeat(40) }).includes("Suggested fixes"), "stale suggestions are omitted");
assert(!body(run, report, "dsw-nrp/eosc-fair-guide", { ...suggestions, suggestions: [{ ...suggestion, file: "outside.toml" }] }).includes('re3data = "r3d1"'), "unknown files are dropped");
assert(body(run, report, "dsw-nrp/eosc-fair-guide", { ...suggestions, suggestions: [{ ...suggestion, value: "x".repeat(129) }] }).includes("malformed suggestion"), "dropped suggestions are counted");
const reasonCode = body(run, report, "dsw-nrp/eosc-fair-guide", { ...suggestions,
  suggestions: [{ ...suggestion, reason: "https://example.test @org/team `escape`\n![image](evil)" }] });
assert(reasonCode.includes(": `https://example.test"), "reason URLs are inert code text");
assert(!reasonCode.includes("`escape`"), "reason backticks cannot escape the code span");
const entryCode = body(run, report, "dsw-nrp/eosc-fair-guide", { ...suggestions,
  suggestions: [{ ...suggestion, entry: "resource:x`https://example.test" }] });
assert(entryCode.includes("- `resource:x https://example.test` ← "), "entry backticks are removed inside the code span");
assert(!entryCode.includes("x`https://example.test"), "entry text cannot close the code span");
const recordCode = body(run, report, "dsw-nrp/eosc-fair-guide", { ...suggestions,
  suggestions: [{ ...suggestion, record: "re3data:x`https://example.test" }] });
assert(recordCode.includes("`re3data:x https://example.test`: "), "record backticks are removed inside the code span");
assert(!recordCode.includes("x`https://example.test"), "record text cannot close the code span");
assert(!body(run, report, "dsw-nrp/eosc-fair-guide", { ...suggestions,
  suggestions: [{ ...suggestion, table: "" }] }).includes('re3data = "r3d1"'), "invalid placement combinations are dropped");
const manySuggestions = {
  formatVersion: 1, head: run.head_sha,
  suggestions: Array(20).fill({ ...suggestion, reason: "x".repeat(400) }),
};
const boundedWithFixes = body(
  run,
  { ...report, total: 40, items: Array(40).fill(expanded), complete: "changes.json" },
  "dsw-nrp/eosc-fair-guide",
  manySuggestions,
);
assert(boundedWithFixes.length < 60000, "changed rows and suggestions together stay within the comment limit");
assert(boundedWithFixes.includes("additional suggestion(s)"), "suggestions beyond the comment bound point to the artifact");
const changes = [], marker = "<!-- fair-guide-review-summary -->";
const existing = [{ id: 9, user: { login: "person" }, body: marker }, { id: 10, user: { login: "github-actions[bot]" }, body: marker }];
const github = { rest: { pulls: { get: async ({ pull_number }) => ({ data: pull_number === 2 ? pr : { ...pr, head: { ...pr.head, sha: "b".repeat(40) } } }) },
  issues: { listComments() {}, updateComment: async (entry) => changes.push(entry), createComment: async (entry) => changes.push(entry) } },
  paginate: async () => existing };
await comment(
  { github, context: { repo: { owner: "dsw-nrp", repo: "eosc-fair-guide" }, payload: { workflow_run: run } }, core: { info() {} } },
  (file) => (file.endsWith("suggestions.json") ? suggestions : report),
);
assert.equal(changes.length, 1, "stale PR head is skipped");
assert.equal(changes[0].comment_id, 10, "only the action bot's own marked comment is updated");
assert.equal(changes[0].body, body(run, report, "dsw-nrp/eosc-fair-guide", suggestions));
console.log("check_pr_comment: bounded escaped data, exact head/repository admission, trusted conclusion and bot-owned update pass");
