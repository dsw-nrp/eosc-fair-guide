// The live watch's issue publisher: one issue per stable key, updated rather than duplicated, closed on recovery,
// bounded writes, and pull requests or unrelated issues left alone.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { apply, markerOf, LABEL, MAX_WRITES } = createRequire(import.meta.url)("../../.github/scripts/health-issues.cjs");

const repo = { owner: "motyc", repo: "eosc-fair-guide" };
const core = { info() {} };
const plan = (actions) => () => JSON.stringify({ format_version: 1, actions });
function fake(open) {
  const writes = [];
  const github = {
    paginate: async (method, options) => method(options),
    rest: { issues: {
      listForRepo: (options) => { assert.equal(options.labels, LABEL); return open; },
      create: async (options) => writes.push(["create", options]),
      update: async (options) => writes.push(["update", options]),
      createComment: async (options) => writes.push(["comment", options]),
    } },
  };
  return { github, writes };
}
const existing = { number: 3, title: "Link is broken: https://b.example/gone", body: "Old text\n\n" + markerOf("link:https://b.example/gone") };
const open = { key: "link:https://b.example/gone", action: "open", title: existing.title, body: "New text" };

let { github, writes } = fake([]);
assert.deepEqual(await apply({ github, context: { repo }, core }, plan([open])), { opened: 1, updated: 0, closed: 0, unchanged: 0, deferred: 0 });
assert.equal(writes[0][0], "create");
assert.deepEqual(writes[0][1].labels, [LABEL]);
assert(writes[0][1].body.endsWith(markerOf(open.key)), "the key travels in the issue");

({ github, writes } = fake([existing, { number: 9, body: markerOf(open.key), pull_request: {} }, { number: 10, body: "unrelated" }]));
assert.equal((await apply({ github, context: { repo }, core }, plan([open]))).updated, 1);
assert.deepEqual(writes.map(([kind, options]) => [kind, options.issue_number]), [["update", 3]], "the keyed issue is updated, not duplicated");

({ github, writes } = fake([{ ...existing, body: "New text\n\n" + markerOf(open.key) }]));
assert.equal((await apply({ github, context: { repo }, core }, plan([open]))).unchanged, 1);
assert.deepEqual(writes, []);

({ github, writes } = fake([existing]));
const closing = [{ key: open.key, action: "close", comment: "Recovered." }, { key: "link:https://never.example", action: "close" }];
assert.equal((await apply({ github, context: { repo }, core }, plan(closing))).closed, 1);
assert.deepEqual(writes.map(([kind, options]) => [kind, options.issue_number, options.state]), [["comment", 3, undefined], ["update", 3, "closed"]]);

({ github, writes } = fake([]));
const flood = Array.from({ length: MAX_WRITES + 5 }, (_, n) => ({ key: "link:" + n, action: "open", title: "t" + n, body: "b" }));
const counts = await apply({ github, context: { repo }, core }, plan(flood));
assert.deepEqual([counts.opened, counts.deferred], [MAX_WRITES, 5], "writes per run are bounded");

for (const broken of [{ format_version: 2, actions: [] }, { format_version: 1, actions: [{ key: "", action: "open" }] }, { format_version: 1, actions: [{ key: "x", action: "delete" }] }]) {
  await assert.rejects(apply({ github, context: { repo }, core }, () => JSON.stringify(broken)));
}
console.log("check_health_issues: keyed deduplicated issues, recovery closing, bounded writes and refused malformed plans pass");
