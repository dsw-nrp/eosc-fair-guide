// The maintenance digest publisher: one bot-owned digest rebuilt in place, a comment only for change and never twice
// for one run, two open digests refused, rotation by closing that completes after an interruption, tasks adopted
// only from people with write access, and pinning that never blocks publication.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { prepare, publish, keyedTasks, previousState, LABEL, TASK_LABEL, BOT, DIGEST, TITLE, STATE, forwardOf, runOf } =
  createRequire(import.meta.url)("../../.github/scripts/health-digest.cjs");

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const body = (extra = "") => `${DIGEST}\nRebuilt.${extra}\n`;
const marker = (key, outcome) => `<!-- fair-guide-finding key=${encodeURIComponent(key)} outcome=${outcome} -->`;

/** GitHub as the publisher reads and writes it; every write is recorded. */
function fake({ issues = [], comments = {}, subs = {}, access = { motyc: "admin" }, pinFails = false } = {}) {
  const writes = [];
  let next = 500;
  const github = {
    paginate: async (method, options) => {
      if (typeof method === "string") return (subs[options.issue_number] || []).map((number) => issues.find((issue) => issue.number === number));
      return method(options);
    },
    request: async (route, options) => {
      writes.push(["sub-issue", options.issue_number, options.sub_issue_id]);
      const task = issues.find((issue) => issue.id === options.sub_issue_id);
      for (const list of Object.values(subs)) { const at = list.indexOf(task.number); if (at >= 0) list.splice(at, 1); }
      (subs[options.issue_number] ||= []).push(task.number);
    },
    graphql: async () => { if (pinFails) throw Error("pinning is not allowed"); writes.push(["pin"]); },
    rest: {
      issues: {
        listForRepo: (options) => issues.filter((issue) => (issue.labels || []).includes(options.labels)),
        listComments: ({ issue_number }) => comments[issue_number] || [],
        create: async (options) => {
          const issue = { ...options, number: next++, id: 9000 + next, node_id: "N", state: "open", user: { login: BOT },
            labels: options.labels };
          issues.push(issue); writes.push(["create", options]);
          return { data: issue };
        },
        update: async (options) => {
          Object.assign(issues.find((issue) => issue.number === options.issue_number), options);
          writes.push(["update", options.issue_number]);
        },
        createComment: async (options) => {
          (comments[options.issue_number] ||= []).push({ body: options.body });
          writes.push(["comment", options.issue_number]);
        },
      },
      repos: {
        getCollaboratorPermissionLevel: async ({ username }) => {
          if (!(username in access)) throw Object.assign(Error("Not Found"), { status: 404 });
          return { data: { permission: access[username] } };
        },
      },
    },
  };
  return { github, writes, issues, comments, subs };
}
const summary = { text: "", addRaw(value) { this.text += value; return this; }, async write() {} };
const core = { info() {}, warning(text) { core.warned.push(text); }, warned: [], setOutput(key, value) { core.outputs[key] = value; },
  outputs: {}, summary };
const files = (rendered, comment = "", tasks = []) => (path) => ({ ".cache/digest/body.md": rendered,
  ".cache/digest/comment.md": comment, ".cache/digest/tasks.json": JSON.stringify(tasks) })[path];
const digestIssue = (number, state = "open", text = body()) => ({ number, id: 9000 + number, node_id: "D" + number, state,
  body: text, user: { login: BOT }, labels: [LABEL] });
const task = (number, login, extra = {}) => ({ number, id: 100 + number, state: "open", labels: [TASK_LABEL], user: { login },
  body: "Task.\n" + marker("link:https://b.example/gone", "broken"), html_url: `https://github.com/x/${number}`, ...extra });
const context = { repo };

// The first run opens and pins the digest, comments on the change and attaches a maintainer's task.
{
  const { github, writes, issues } = fake({ issues: [task(7, "motyc")] });
  const comment = `${runOf("41")}\n\n**New** (1)`;
  const result = await publish({ github, context, core }, files(body(), comment, [{ number: 7, id: 107 }]));
  assert.deepEqual([result.created, result.commented, result.pinned, result.adopted], [true, true, true, [7]]);
  assert.equal(core.outputs.published, "true");
  const created = writes.find(([kind]) => kind === "create")[1];
  assert.deepEqual([created.title, created.labels], [TITLE, [LABEL]]);
  // A retry of the same run finds its comment; an unchanged body is not rewritten.
  writes.length = 0;
  const again = await publish({ github, context, core }, files(body(), comment, [{ number: 7, id: 107 }]));
  assert.deepEqual([again.created, again.updated, again.commented, again.adopted], [false, false, false, []]);
  assert.deepEqual(writes, [], "a retry writes nothing");
  await publish({ github, context, core }, files(body(" Newer."), "", []));
  assert.equal(issues.find((issue) => issue.number === result.digest).body, body(" Newer."), "the body is rebuilt in place");
}
// Two open digests: nothing is written and the summary names both.
{
  const { github, writes } = fake({ issues: [digestIssue(3), digestIssue(4)] });
  summary.text = "";
  const result = await publish({ github, context, core }, files(body(), `${runOf("41")}\nNew`));
  assert.deepEqual(result.refused, [3, 4]);
  assert.deepEqual(writes, []);
  assert.equal(core.outputs.published, "false", "the next run still reports what this one could not");
  assert.match(summary.text, /Two maintenance digests are open \(#3 and #4\); nothing was written/);
}
// Only digests this workflow created count; a person's issue with the label is left alone.
{
  const { github, writes } = fake({ issues: [{ ...digestIssue(3), user: { login: "someone" } }] });
  const result = await publish({ github, context, core }, files(body()));
  assert.equal(result.created, true, "another author's issue is not the digest");
  assert.equal(writes.filter(([kind]) => kind === "update").length, 0);
}
// Rotation: after a maintainer closes #3, the successor links it, posts the forward link and takes its open tasks.
{
  const state = fake({ issues: [digestIssue(3, "closed"), task(7, "motyc"), task(8, "motyc", { state: "closed" })], subs: { 3: [7, 8] } });
  await prepare({ github: state.github, context, core }, () => {});
  assert.equal(core.outputs.predecessor, "3");
  const continued = body("\n\nContinues #3.");
  const result = await publish({ github: state.github, context, core }, files(continued));
  assert.deepEqual(result.moved, [7], "open tasks move; closed ones keep their place");
  assert.equal(state.comments[3].length, 1);
  assert(state.comments[3][0].body.includes(forwardOf(result.digest)));
  // A run interrupted after creating the successor completes the rotation without a second successor or comment.
  state.writes.length = 0;
  await prepare({ github: state.github, context, core }, () => {});
  assert.equal(core.outputs.predecessor, "3", "the successor keeps naming its predecessor");
  await publish({ github: state.github, context, core }, files(continued));
  assert.deepEqual(state.writes, [], "every rotation step is already done");
}
{
  // Interrupted before the forward link and the move: the next run finishes both.
  const state = fake({ issues: [digestIssue(3, "closed"), digestIssue(5, "open", body("\n\nContinues #3.")), task(7, "motyc")],
    subs: { 3: [7] } });
  const result = await publish({ github: state.github, context, core }, files(body("\n\nContinues #3.")));
  assert.deepEqual([result.created, result.moved], [false, [7]]);
  assert(state.comments[3][0].body.includes(forwardOf(5)));
}
{
  // Interrupted after the forward link: only the move remains, and the link is not posted twice.
  const state = fake({ issues: [digestIssue(3, "closed"), digestIssue(5, "open", body("\n\nContinues #3.")), task(7, "motyc")],
    subs: { 3: [7] }, comments: { 3: [{ body: forwardOf(5) }] } });
  const result = await publish({ github: state.github, context, core }, files(body("\n\nContinues #3.")));
  assert.deepEqual([result.moved, state.comments[3].length, state.subs[5]], [[7], 1, [7]]);
}
// Tasks: only issues with a finding key from people with write access; closed ones keep their disposition.
{
  const { github } = fake({ issues: [task(7, "motyc"), task(8, "visitor"), task(9, "reader"),
    task(10, "motyc", { state: "closed", state_reason: "not_planned", closed_at: "2026-11-01T10:00:00Z" }),
    task(11, "motyc", { body: "No marker." }), { ...task(12, "motyc"), pull_request: {} }], access: { motyc: "write", reader: "read" } });
  const tasks = await keyedTasks(github, repo, new Set());
  assert.deepEqual(tasks.map((entry) => entry.number), [7, 10]);
  assert.deepEqual([tasks[0].key, tasks[0].outcome], ["link:https://b.example/gone", "broken"]);
  assert.deepEqual([tasks[1].state, tasks[1].reason, tasks[1].closed], ["closed", "not_planned", "2026-11-01T10:00:00Z"]);
}
// Pinning is best effort; malformed renders are refused before any write.
{
  const { github, writes } = fake({ pinFails: true });
  core.warned.length = 0;
  const result = await publish({ github, context, core }, files(body()));
  assert.deepEqual([result.created, result.pinned], [true, false]);
  assert.match(core.warned[0], /Could not pin maintenance digest/);
  const fresh = fake();
  await assert.rejects(publish({ github: fresh.github, context, core }, files("No marker.\n")), /lacks its marker/);
  await assert.rejects(publish({ github: fresh.github, context, core }, files(body(), "New, without a run marker")), /lacks its run marker/);
  assert.deepEqual(fresh.writes, []);
  assert(writes.length >= 1);
}
// The previous state comes only from this workflow's own runs on the default branch, newest first.
{
  const artifact = (id, extra = {}) => ({ name: STATE, expired: false,
    workflow_run: { id, head_branch: "main", repository_id: 1, head_repository_id: 1 }, ...extra });
  const runs = { 61: { path: ".github/workflows/health-watch.yml", event: "schedule" },
    62: { path: ".github/workflows/health-watch.yml@refs/heads/main", event: "workflow_dispatch" },
    63: { path: ".github/workflows/checks.yml", event: "pull_request" },
    // Health-watch runs in every other respect, so only the branch and fork rules exclude them.
    68: { path: ".github/workflows/health-watch.yml", event: "workflow_dispatch" },
    69: { path: ".github/workflows/health-watch.yml", event: "workflow_dispatch" } };
  const listed = [
    artifact(70, { expired: true }),
    artifact(69, { workflow_run: { id: 69, head_branch: "topic", repository_id: 1, head_repository_id: 1 } }),
    artifact(68, { workflow_run: { id: 68, head_branch: "main", repository_id: 1, head_repository_id: 2 } }),
    artifact(63), artifact(62), artifact(61),
  ];
  const github = { rest: { actions: {
    listArtifactsForRepo: async (options) => { assert.equal(options.name, STATE); return { data: { artifacts: listed } }; },
    getWorkflowRun: async ({ run_id }) => ({ data: runs[run_id] }),
  } } };
  const scoped = { repo, payload: { repository: { default_branch: "main" } } };
  assert.equal(await previousState({ github, context: scoped, core }), "62", "expired, branch, fork and other workflows are skipped");
  listed.splice(4);
  assert.equal(await previousState({ github, context: scoped, core }), "");
  assert.equal(core.outputs.run, "", "no trusted state: the watch shows a reset");
}
console.log("check_health_digest: one rebuilt digest, comments once per change, two digests refused, resumable rotation, write-access tasks, best-effort pinning and trusted previous state pass");
