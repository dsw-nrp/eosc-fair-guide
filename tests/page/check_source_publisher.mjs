// Source refresh publication: one bot-owned pull request per source, no default-branch writes, no automatic merge,
// human edits kept, rejected content not proposed again, and commands only from accounts with write access.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { SOURCES, parseCommand, select, publish, hashOf, markerOf } = createRequire(import.meta.url)("../../.github/scripts/source-publisher.cjs");

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const bot = "fair-guide-refresh[bot]";
const files = { "content/glossary.toml": "[glossary]\n", "content/snapshots/re3data.toml": "[snapshot]\n" };
const report = (outcomes) => JSON.stringify({ formatVersion: 1, outcomes });
const read = (outcomes) => (path) => (path.endsWith("report.json") ? report(outcomes) : files[path]);
const exists = (path) => Object.hasOwn(files, path);
const core = { info() {} };

function fakeGithub({ open = [], closed = [], commits = [], branches = [], permission = "write" } = {}) {
  const writes = [];
  const github = {
    paginate: async (method, options) => method(options),
    rest: {
      pulls: {
        list: ({ state, head }) => (state === "open" ? open : closed).filter((pr) => pr.head === head),
        listCommits: () => commits,
        create: async (options) => writes.push(["createPull", options]),
        update: async (options) => writes.push(["updatePull", options]),
      },
      issues: { createComment: async (options) => writes.push(["comment", options]) },
      repos: { getCollaboratorPermissionLevel: async () => ({ data: { permission, role_name: permission } }) },
      git: {
        getRef: async ({ ref }) => {
          if (ref === "heads/main") return { data: { object: { sha: "m".repeat(40) } } };
          if (branches.includes(ref)) return { data: { object: { sha: "b".repeat(40) } } };
          throw Object.assign(Error("Not Found"), { status: 404 });
        },
        getCommit: async () => ({ data: { tree: { sha: "t".repeat(40) } } }),
        createTree: async (options) => { writes.push(["tree", options]); return { data: { sha: "n".repeat(40) } }; },
        createCommit: async (options) => { writes.push(["commit", options]); return { data: { sha: "c".repeat(40) } }; },
        createRef: async (options) => writes.push(["createRef", options]),
        updateRef: async (options) => writes.push(["updateRef", options]),
      },
    },
  };
  return { github, writes };
}
const context = { repo, payload: { repository: { default_branch: "main" } } };
const changed = [{ source: "heslar", status: "changed" }];
const marker = markerOf("heslar", hashOf([["content/glossary.toml", files["content/glossary.toml"]]]));
const refs = (writes) => writes.filter(([kind]) => kind === "createRef" || kind === "updateRef").map(([, options]) => options.ref);

// A new change: a commit on the default branch's head, a reserved branch and one pull request; nothing merges.
let { github, writes } = fakeGithub();
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "proposed" });
assert.deepEqual(refs(writes), ["refs/heads/refresh/heslar"]);
assert.deepEqual(writes.find(([kind]) => kind === "commit")[1].parents, ["m".repeat(40)], "refreshed from current main");
const created = writes.find(([kind]) => kind === "createPull")[1];
assert.equal(created.base, "main");
assert(created.body.includes(marker));
assert(!writes.some(([, options]) => String(options.ref || "").includes("heads/main")), "the default branch is never written");

// The same content already proposed, unchanged or rejected outcomes: nothing is written.
({ github, writes } = fakeGithub({ open: [{ number: 5, head: "dsw-nrp:refresh/heslar", body: marker }] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "already-proposed" });
assert.deepEqual(writes, []);
({ github, writes } = fakeGithub());
assert.deepEqual(await publish({ github, context, core }, read([{ source: "heslar", status: "unchanged" }, { source: "re3data", status: "rejected" }]), exists, bot), { heslar: "unchanged", re3data: "rejected" });
assert.deepEqual(writes, []);

// Content closed without merging is not proposed again; different content is.
({ github, writes } = fakeGithub({ closed: [{ number: 4, head: "dsw-nrp:refresh/heslar", body: marker, merged_at: null }] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "rejected-before" });
assert.deepEqual(writes, []);
({ github, writes } = fakeGithub({ closed: [{ number: 4, head: "dsw-nrp:refresh/heslar", body: markerOf("heslar", "0".repeat(64)), merged_at: null }] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "proposed" });

// An open bot proposal is updated from current main; one with a person's commit is left alone and explained.
const older = { number: 6, head: "dsw-nrp:refresh/heslar", body: markerOf("heslar", "1".repeat(64)) };
({ github, writes } = fakeGithub({ open: [older], commits: [{ author: { login: bot } }], branches: ["heads/refresh/heslar"] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "updated" });
assert.deepEqual(writes.filter(([kind]) => kind === "updateRef").map(([, options]) => [options.ref, options.force]), [["heads/refresh/heslar", true]]);
({ github, writes } = fakeGithub({ open: [older], commits: [{ author: { login: bot } }, { author: { login: "maintainer" } }], branches: ["heads/refresh/heslar"] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "human-edits" });
assert.deepEqual(writes.map(([kind]) => kind), ["comment"], "human edits are kept: no ref update, one explanation");
({ github, writes } = fakeGithub({ open: [older], commits: [{ author: { login: bot } }], branches: ["heads/refresh/heslar"] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, undefined), { heslar: "human-edits" }, "an unknown bot identity cannot claim a branch");

// Commands: exactly "/refresh <reviewed key>", from a current writer, on a pull request.
assert.equal(parseCommand("/refresh heslar"), "heslar");
for (const body of ["/refresh heslar now", "/refresh heslar; rm -rf /", "/refresh https://evil.example/", "/refresh ../main", "/refresh other", "refresh heslar", "/refresh  heslar"]) {
  assert.equal(parseCommand(body), null, body);
}
const comment = (permission, body = "/refresh fip-dashboard") => select({ github: fakeGithub({ permission }).github, core,
  context: { repo, eventName: "issue_comment", payload: { issue: { pull_request: {} }, comment: { body, user: { login: "someone" } } } } });
assert.equal(await comment("write"), "fip-dashboard");
assert.equal(await comment("maintain"), "fip-dashboard");
assert.equal(await comment("read"), "", "an account without current write access cannot start a refresh");
assert.equal(await comment("none", "/refresh heslar"), "");
assert.equal(await select({ github, core, context: { repo, eventName: "issue_comment", payload: { issue: {}, comment: { body: "/refresh heslar", user: { login: "x" } } } } }), "", "issue comments are not refresh commands");
assert.equal(await select({ github, core, context: { repo, eventName: "workflow_dispatch", payload: { inputs: { source: "re3data" } } } }), "re3data");
assert.equal(await select({ github, core, context: { repo, eventName: "workflow_dispatch", payload: { inputs: { source: "x; y" } } } }), "");
assert.equal(await select({ github, core, context: { repo, eventName: "schedule", payload: {} } }), Object.keys(SOURCES).join(" "));
console.log("check_source_publisher: one bot-owned PR per source, current-main refresh, no default-branch write or merge, kept human edits, suppressed rejected content and authorized exact commands pass");
