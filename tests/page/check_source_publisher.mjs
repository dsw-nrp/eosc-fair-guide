// Source refresh publication: one bot-owned pull request per source, a branch replaced only while it still points at
// the inspected head, no default-branch writes, no automatic merge, human edits kept, rejected content not proposed
// again, and commands only from accounts with write access.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { SOURCES, parseCommand, select, publish, reply, summarize, hashOf, markerOf } = createRequire(import.meta.url)("../../.github/scripts/source-publisher.cjs");
const commands = createRequire(import.meta.url)("../../.github/scripts/commands.cjs");

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const bot = "fair-guide-refresh[bot]";
const files = { "content/glossary.toml": "[glossary]\n", "content/snapshots/re3data.toml": "[snapshot]\n" };
const report = (outcomes) => JSON.stringify({ formatVersion: 1, outcomes });
const read = (outcomes) => (path) => (path.endsWith("report.json") ? report(outcomes) : files[path]);
const exists = (path) => Object.hasOwn(files, path);
const core = { info() {} };

function fakeGithub({ open = [], closed = [], commits = [], branches = [], permission = "write", raced = null, events = [], labelled = true } = {}) {
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
        create: async (options) => {
          writes.push(["createPull", options]);
          const created = { number: 7, labels: [], head: `${repo.owner}:${options.head}`, body: options.body };
          open.push(created);
          return { data: created };
        },
        update: async (options) => writes.push(["updatePull", options]),
      },
      issues: {
        createComment: async (options) => writes.push(["comment", options]),
        listEvents: () => events,
        addLabels: async (options) => writes.push(["labels", options]),
        getLabel: async () => {
          if (!labelled) throw Object.assign(Error("Not Found"), { status: 404 });
          return { data: {} };
        },
      },
      repos: { getCollaboratorPermissionLevel: async () => ({ data: { permission, role_name: permission } }) },
      actions: { listWorkflowRuns: async () => ({ data: { workflow_runs: [] } }) },
      reactions: { createForIssueComment: async (options) => writes.push(["reaction", options]) },
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
// Before the declared label exists, the PR is still published and the label waits instead of being invented.
({ github, writes } = fakeGithub({ labelled: false }));
assert.deepEqual(await publish({ github, context, core }, read(changed), exists, bot), { heslar: "proposed" });
assert(writes.some(([kind]) => kind === "createPull") && !writes.some(([kind]) => kind === "labels"), "no label is created by adding it");
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

// Commands: exactly "/refresh <reviewed key>", from a current writer, on an issue or pull request.
assert.equal(parseCommand("/refresh heslar"), "heslar");
for (const body of ["/refresh heslar now", "/refresh heslar; rm -rf /", "/refresh https://evil.example/", "/refresh ../main", "/refresh other", "refresh heslar", "/refresh  heslar"]) {
  assert.equal(parseCommand(body), null, body);
}
const comment = (permission, body = "/refresh fip-dashboard") => select({ github: fakeGithub({ permission }).github, core,
  context: { repo, eventName: "issue_comment", payload: { issue: { number: 12, pull_request: {} }, comment: { body, user: { login: "someone" } } } } });
assert.equal(await comment("write"), "fip-dashboard");
assert.equal(await comment("maintain"), "fip-dashboard");
assert.equal(await comment("read"), "", "an account without current write access cannot start a refresh");
assert.equal(await comment("none", "/refresh heslar"), "");
assert.equal(await select({ github, core, context: { repo, eventName: "issue_comment", payload: { issue: { number: 12 }, comment: { body: "/refresh heslar", user: { login: "x" } } } } }), "heslar", "an ordinary issue can start refresh");
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

// The real command parser/gate, selector, publisher and reply cooperate before a refresh PR exists.
for (const fromPull of [false, true]) {
  const event = { ...context, eventName: "issue_comment", serverUrl: "https://github.com", runId: 88,
    payload: { ...context.payload, issue: { number: 99, ...(fromPull ? { pull_request: {} } : {}) },
      comment: { id: 41, body: "/refresh heslar", user: { login: "maintainer" } } } };
  ({ github, writes } = fakeGithub());
  assert.equal(commands.parse(event.payload.comment.body).command, "refresh");
  assert.equal(await commands.acknowledge({ github, context: event, core }, true), true);
  assert.equal(await select({ github, context: event, core }), "heslar");
  const results = await publish({ github, context: event, core }, read(changed), exists, bot);
  const body = await reply({ github, context: event }, JSON.stringify(results), "0", "success");
  assert.match(body, /Proposal #7\]\(https:\/\/github.com\/dsw-nrp\/eosc-fair-guide\/pull\/7\)/);
  const answer = writes.find(([kind]) => kind === "comment")[1];
  assert.equal(answer.issue_number, 99, "reply stays in the initiating thread");
  assert.match(answer.body, /actions\/runs\/88/);
  assert.deepEqual(refMoves(writes), ["refs/heads/refresh/heslar"]);

  for (const [permission, text] of [["read", "/refresh heslar"], ["write", "/refresh unknown"]]) {
    const denied = { ...event, payload: { ...event.payload, comment: { ...event.payload.comment, body: text } } };
    ({ github, writes } = fakeGithub({ permission }));
    assert.equal(await commands.acknowledge({ github, context: denied, core }, true), false);
    assert.equal(await select({ github, context: denied, core }), "");
    assert(!writes.some(([kind]) => ["commit", "tree", "refUpdate", "createPull"].includes(kind)));
  }
}
for (const invalid of ["null", "[]", "true"]) {
  assert.match(await reply({ github, context: commanded }, invalid, "0"), /did not reach publication/);
}

// Every run's summary names each source's outcome, reason and who acts. Only a source that needs a maintainer fails
// the run; one the next scheduled refresh retries is a warning (26 October 2026: heslar and nkr timed out, and the run
// ended red with its reasons only in an artifact).
{
  const run = async (options) => {
    const state = { failed: "", warned: "", text: "" };
    const runCore = { summary: { addRaw(text) { state.text += text; return this; }, async write() {} },
      setFailed: (message) => { state.failed = message; }, warning: (message) => { state.warned = message; } };
    const text = await summarize({ core: runCore }, options);
    assert.equal(state.text, text + "\n", "the summary is written to the run");
    return { ...state, text };
  };
  const retried = await run({ results: JSON.stringify({ heslar: "failed", nkr: "failed", re3data: "proposed" }), publication: "success",
    report: { outcomes: [{ source: "heslar", status: "failed", reason: "timed out" }, { source: "nkr", status: "failed", reason: "HTTP 503" },
      { source: "re3data", status: "changed" }] } });
  assert.equal(retried.failed, "", "a source that was not retrieved does not fail the run");
  assert.match(retried.warned, /next scheduled refresh retries them/);
  assert.match(retried.text, /\| `heslar` \| not retrieved[^|]*\| Retry \| timed out \|/);
  assert.match(retried.text, /\| `re3data` \| proposed as a new refresh pull request[^|]*\| — \|/);
  assert.match(retried.text, /\*\*Next:\*\* nothing now/);
  assert.doesNotMatch(retried.text, /artifact gives|artifact names/, "the reason is in the summary itself");
  const rejected = await run({ results: JSON.stringify({ heslar: "rejected" }), publication: "success",
    report: { outcomes: [{ source: "heslar", status: "rejected", reason: "3 terms lack an identifier" }] } });
  assert.match(rejected.failed, /needs a maintainer/);
  assert.match(rejected.text, /\*\*Act\*\* \| 3 terms lack an identifier \|/);
  assert.match(rejected.text, /\*\*Done when:\*\* a rerun marks no source \*\*Act\*\*/);
  const unpublished = await run({ results: "", publication: "failure", report: { outcomes: [{ source: "re3data", status: "changed" }] } });
  assert.match(unpublished.failed, /needs a maintainer/);
  assert.match(unpublished.text, /Publication did not complete/);
  assert.match(unpublished.text, /changed, but publication did not complete \| \*\*Act\*\*/);
  const proposed = await run({ results: JSON.stringify({ re3data: "proposed" }), publication: "success",
    report: { outcomes: [{ source: "re3data", status: "changed" }] } });
  assert.deepEqual([proposed.failed, proposed.warned], ["", ""]);
  assert.match(proposed.text, /reviews each proposed or updated refresh pull request as content/);
}
console.log("check_source_publisher: one bot-owned PR per source, an atomically guarded branch head, current-main refresh, no default-branch write or merge, kept human edits, suppressed rejected content, a label a person's removal keeps off, authorized exact commands and run summaries that fail only when a maintainer acts pass");
