// Source refresh publication: one bot-owned pull request per source, a branch replaced only while it still points at
// the inspected head, no default-branch writes, no automatic merge, human edits kept, rejected content not proposed
// again, and commands only from accounts with write access.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { SOURCES, parseCommand, select, publish, reply, hashOf, markerOf } = createRequire(import.meta.url)("../../.github/scripts/source-publisher.cjs");

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const bot = "fair-guide-refresh[bot]";
const files = { "content/glossary.toml": "[glossary]\n", "content/snapshots/re3data.toml": "[snapshot]\n" };
const report = (outcomes) => JSON.stringify({ formatVersion: 1, outcomes });
const read = (outcomes) => (path) => (path.endsWith("report.json") ? report(outcomes) : files[path]);
const exists = (path) => Object.hasOwn(files, path);
const core = { info() {} };

function fakeGithub({ open = [], closed = [], commits = [], branches = [], permission = "write", raced = null, events = [] } = {}) {
  const writes = [];
  const heads = new Map(branches.map((ref) => ["refs/" + ref, "b".repeat(40)]));
  const github = {
    paginate: async (method, options) => method(options),
    // The atomic ref update GitHub applies: compare the expected head, then move the ref in one operation.
    graphql: async (_query, { input }) => {
      const [update] = input.refUpdates;
      writes.push(["refUpdate", { ...update, repositoryId: input.repositoryId }]);
      if (raced) heads.set(update.name, raced);
      if ((heads.get(update.name) || "0".repeat(40)) !== (update.beforeOid || "0".repeat(40))) {
        throw Error("UpdateRefs rejected: the ref does not match beforeOid");
      }
      heads.set(update.name, update.afterOid);
      return { updateRefs: { clientMutationId: null } };
    },
    rest: {
      pulls: {
        list: ({ state, head }) => (state === "open" ? open : closed).filter((pr) => pr.head === head),
        listCommits: () => commits,
        create: async (options) => { writes.push(["createPull", options]); return { data: { number: 7, labels: [] } }; },
        update: async (options) => writes.push(["updatePull", options]),
      },
      issues: {
        createComment: async (options) => writes.push(["comment", options]),
        listEvents: () => events,
        addLabels: async (options) => writes.push(["labels", options]),
      },
      repos: { getCollaboratorPermissionLevel: async () => ({ data: { permission, role_name: permission } }) },
      git: {
        getRef: async ({ ref }) => {
          if (ref === "heads/main") return { data: { object: { sha: "m".repeat(40) } } };
          if (heads.has("refs/" + ref)) return { data: { object: { sha: heads.get("refs/" + ref) } } };
          throw Object.assign(Error("Not Found"), { status: 404 });
        },
        getCommit: async () => ({ data: { tree: { sha: "t".repeat(40) } } }),
        createTree: async (options) => { writes.push(["tree", options]); return { data: { sha: "n".repeat(40) } }; },
        createCommit: async (options) => { writes.push(["commit", options]); return { data: { sha: "c".repeat(40) } }; },
      },
    },
  };
  return { github, writes };
}
const context = { repo, payload: { repository: { default_branch: "main", node_id: "R_eosc-fair-guide" } } };
const changed = [{ source: "heslar", status: "changed" }];
const marker = markerOf("heslar", hashOf([["content/glossary.toml", files["content/glossary.toml"]]]));
const refMoves = (writes) => writes.filter(([kind]) => kind === "refUpdate").map(([, update]) => update.name);

// A new change: a commit on the default branch's head, a reserved branch and one pull request; nothing merges.
let { github, writes } = fakeGithub();
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "proposed" });
assert.deepEqual(refMoves(writes), ["refs/heads/refresh/heslar"]);
const created = writes.find(([kind]) => kind === "refUpdate")[1];
assert.equal(created.beforeOid, "0".repeat(40), "an absent branch is created only while it stays absent");
assert.equal(created.afterOid, "c".repeat(40));
assert.equal(created.force, true);
assert.equal(created.repositoryId, "R_eosc-fair-guide");
assert.deepEqual(writes.find(([kind]) => kind === "commit")[1].parents, ["m".repeat(40)], "refreshed from current main");
const pull = writes.find(([kind]) => kind === "createPull")[1];
assert.equal(pull.base, "main");
assert(pull.body.includes(marker));
assert(!writes.some(([, value]) => String(value?.name || value?.ref || "").includes("main")), "the default branch is never written");
assert.deepEqual(writes.find(([kind]) => kind === "labels")[1], { ...repo, issue_number: 7, labels: ["source-refresh"] }, "a new refresh PR is labelled");

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
const refreshCommit = { author: { login: bot }, commit: { message: "Refresh the heslar snapshot" } };
({ github, writes } = fakeGithub({ open: [older], commits: [refreshCommit], branches: ["heads/refresh/heslar"] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "updated" });
assert.deepEqual(
  writes.filter(([kind]) => kind === "refUpdate").map(([, update]) => [update.name, update.beforeOid, update.afterOid]),
  [["refs/heads/refresh/heslar", "b".repeat(40), "c".repeat(40)]],
  "the inspected head is the one the update replaces",
);
assert.deepEqual(writes.find(([kind]) => kind === "labels")[1].labels, ["source-refresh"], "an updated refresh PR keeps its label");
// The label is added once; a person's removal sticks across later refreshes.
({ github, writes } = fakeGithub({ open: [{ ...older, labels: [{ name: "source-refresh" }] }], commits: [refreshCommit], branches: ["heads/refresh/heslar"] }));
await publish({ github, context, core }, read(changed), exists, bot);
assert(!writes.some(([kind]) => kind === "labels"), "a present label is not added again");
({ github, writes } = fakeGithub({ open: [older], commits: [refreshCommit], branches: ["heads/refresh/heslar"],
  events: [{ event: "unlabeled", label: { name: "source-refresh" }, actor: { login: "maintainer" } }] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "updated" });
assert(!writes.some(([kind]) => kind === "labels"), "a removed label is not re-added");
// A branch another writer advanced after inspection keeps its newer head: the comparison refuses the replacement.
({ github, writes } = fakeGithub({ open: [older], commits: [refreshCommit], branches: ["heads/refresh/heslar"], raced: "d".repeat(40) }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "moved" });
assert.deepEqual(writes.map(([kind]) => kind), ["tree", "commit", "refUpdate"], "a moved branch gets no pull update or comment");
assert.equal((await github.rest.git.getRef({ ref: "heads/refresh/heslar" })).data.object.sha, "d".repeat(40));
await assert.rejects(
  publish({ github: fakeGithub().github, core, context: { repo, payload: { repository: { default_branch: "main" } } } },
    read(changed), exists, bot),
  /repository identity/,
  "the atomic mutation needs the repository it targets",
);

({ github, writes } = fakeGithub({ open: [older], commits: [{ author: { login: bot } }, { author: { login: "maintainer" } }], branches: ["heads/refresh/heslar"] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "human-edits" });
assert.deepEqual(writes.map(([kind]) => kind), ["comment"], "human edits are kept: no ref update, one explanation");
({ github, writes } = fakeGithub({ open: [older], commits: [{ author: { login: bot } }], branches: ["heads/refresh/heslar"] }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, undefined), { heslar: "human-edits" }, "an unknown bot identity cannot claim a branch");

for (const commits of [
  [refreshCommit, { author: { login: bot }, commit: { message: "Apply safe duplicate link from /fix-duplicates (PR #82)" } }],
  [{ author: { login: bot }, commit: { message: "Refresh the re3data snapshot" } }],
  [{ author: { login: bot } }], [{ author: null }], [],
  [{ author: { login: "another[bot]" }, commit: refreshCommit.commit }],
]) {
  ({ github, writes } = fakeGithub({ open: [older], commits, branches: ["heads/refresh/heslar"] }));
  await publish({ github, context, core }, read(changed), exists, bot);
  assert.deepEqual(writes.map(([kind]) => kind), ["comment"], "repairs and unknown branch ownership are preserved");
  assert(writes[0][1].body.includes("reconcile"), "protected branches explain manual reconciliation");
}
({ github, writes } = fakeGithub({ open: [older], commits: [refreshCommit] }));
github.rest.pulls.listCommits = () => { throw Error("inventory unavailable"); };
await publish({ github, context, core }, read(changed), exists, bot);
assert.deepEqual(writes.map(([kind]) => kind), ["comment"], "failed inventory cannot replace a branch");

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

// A commanded refresh ends with one reply naming each source's result and the run, also when publication never ran.
const commanded = { repo, serverUrl: "https://github.com", runId: 77, payload: { issue: { number: 9 } } };
({ github, writes } = fakeGithub());
const replied = await reply({ github, context: commanded }, JSON.stringify({ re3data: "proposed", heslar: "human-edits", other: "x" }), "0");
assert.match(replied, /`re3data`: proposed as a new refresh pull request/);
assert.match(replied, /`heslar`: kept on its branch.*reconcile it by hand/);
assert(!replied.includes("`other`"), "only reviewed source keys are reported");
assert.match(replied, /actions\/runs\/77/);
assert.equal(writes.length, 1);
({ github, writes } = fakeGithub());
assert.match(await reply({ github, context: commanded }, "", "1"), /did not reach publication because a source was rejected or failed.*\*\*Next:\*\*/s);
assert.match(await reply({ github, context: commanded }, "{not json", "0"), /did not reach publication; no pull request was changed/);
const stopped = await reply({ github, context: commanded }, "", "0", "failure");
assert.match(stopped, /stopped during publication, so its refresh branch or pull request may already have changed/);
assert(!stopped.includes("no pull request was changed"), "a publication that failed part-way is never reported as no change");
console.log("check_source_publisher: one bot-owned PR per source, an atomically guarded branch head, current-main refresh, no default-branch write or merge, kept human edits, suppressed rejected content, a label a person's removal keeps off and authorized exact commands pass");
