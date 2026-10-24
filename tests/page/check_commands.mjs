// Comment commands: exact parsing, help for near misses, one shared eligibility for /help and the command gate, one
// bot help comment per thread, refusals that change nothing, and an outcome for every accepted command.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const { parse, distance, eligibility, help, acknowledge, outcome, HELP_MARKER } = createRequire(import.meta.url)("../../.github/scripts/commands.cjs");

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const core = { info() {} };
const reviewMarker = "<!-- fair-guide-review-summary -->";

function fakeGithub({ permission = "write", pull = {}, comments = [], runs = {}, jobs = {} } = {}) {
  const writes = [];
  const thread = [...comments];
  const github = {
    paginate: async (method, options) => method(options),
    rest: {
      actions: {
        listWorkflowRuns: async ({ workflow_id: workflow, status }) => ({ data: { workflow_runs: (runs[workflow] || []).filter((run) => run.status === status) } }),
        listJobsForWorkflowRun: async ({ run_id: id }) => ({ data: { jobs: jobs[id] || [] } }),
      },
      repos: { getCollaboratorPermissionLevel: async () => ({ data: { permission, role_name: permission } }) },
      pulls: {
        get: async () => ({ data: { state: "open", head: { ref: "feature", repo: { full_name: "dsw-nrp/eosc-fair-guide" } },
          base: { ref: "main", repo: { default_branch: "main" } }, ...pull } }),
      },
      issues: {
        listComments: () => thread,
        createComment: async (options) => { writes.push(["create", options]); thread.push({ id: 900 + writes.length, user: { login: "github-actions[bot]" }, body: options.body }); },
        updateComment: async (options) => writes.push(["update", options]),
      },
      reactions: { createForIssueComment: async (options) => writes.push(["react", options.content]) },
    },
  };
  return { github, writes };
}

const context = (body, { pull = true, login = "maintainer" } = {}) => ({
  repo, serverUrl: "https://github.com", runId: 42,
  payload: { comment: { id: 7, body, user: { login } }, issue: { number: 12, ...(pull ? { pull_request: {} } : {}) } },
});

// Parsing: commands are whole comments; arguments are exact; ordinary text and paths are not addressed to us.
assert.deepEqual(parse("/fix-duplicates"), { command: "fix-duplicates" });
assert.deepEqual(parse("  /fix-duplicates\n"), { command: "fix-duplicates" });
assert.deepEqual(parse("/refresh re3data"), { command: "refresh", source: "re3data" });
assert.deepEqual(parse("/help"), { command: "help" });
for (const body of ["Looks good", "/content/resources.toml has a typo", "please /fix-duplicates", "", null, "/ refresh", "/zzzzzzzzzzzz"]) {
  assert.equal(parse(body).command, "", String(body));
}
assert.equal(parse("/fixduplicates").command, "unknown");
assert.match(parse("/fixduplicates").notice, /did you mean `\/fix-duplicates`/);
assert.match(parse("/refesh").notice, /did you mean `\/refresh`/);
assert.match(parse("/refresh nowhere").notice, /exactly one source/);
assert.match(parse("/fix-duplicates now").notice, /no arguments/);
assert.equal(parse("/refresh re3data; rm -rf /").command, "unknown", "extra words never reach a command");
assert.equal(distance("kitten", "sitting"), 3);

// One eligibility decides both /help and the gate.
const appConfigured = true;
const allowed = await eligibility({ github: fakeGithub().github, context: context("/fix-duplicates") }, "fix-duplicates", appConfigured);
assert.deepEqual(allowed, { available: true, reasons: [] });
const cases = [
  [{ permission: "read" }, {}, /write access/],
  [{ pull: { head: { ref: "feature", repo: { full_name: "someone/fork" } } } }, {}, /forks/],
  [{ pull: { state: "closed" } }, {}, /not open/],
  [{ pull: { base: { ref: "release", repo: { default_branch: "main" } } } }, {}, /default branch/],
  [{}, { pull: false }, /pull-request comment/],
];
for (const [options, place, reason] of cases) {
  const result = await eligibility({ github: fakeGithub(options).github, context: context("/fix-duplicates", place) }, "fix-duplicates", appConfigured);
  assert.equal(result.available, false);
  assert.match(result.reasons.join("; "), reason);
}
assert.match((await eligibility({ github: fakeGithub().github, context: context("/refresh heslar") }, "refresh", false)).reasons.join(), /App is not configured/);

// Help: one bot comment per thread, updated when asked again, with reasons and the local alternative.
let { github, writes } = fakeGithub({ comments: [{ id: 3, user: { login: "github-actions[bot]" }, body: reviewMarker + "\n### Suggested fixes\n" }] });
const text = await help({ github, context: context("/help"), core }, appConfigured);
assert(text.startsWith(HELP_MARKER));
assert.match(text, /\| `\/fix-duplicates` \| Available \|/);
assert.match(text, /lists safe duplicate links/);
assert.match(text, /scripts\/check_duplicates\.py --fix/);
assert(!text.includes("@maintainer"), "help never mentions people");
await help({ github, context: context("/help"), core }, appConfigured);
assert.deepEqual(writes.map(([kind]) => kind), ["create", "react", "update", "react"], "asking again edits the same comment");
({ github, writes } = fakeGithub({ permission: "read", pull: { head: { ref: "x", repo: { full_name: "someone/fork" } } } }));
const refused = await help({ github, context: context("/fixduplicates", { login: "visitor" }), core }, appConfigured);
assert.match(refused, /did you mean `\/fix-duplicates`/);
assert.match(refused, /Not available: it needs current write access to this repository; it does not run on pull requests from forks/);
assert.equal(writes.filter(([kind]) => kind === "create").length, 1, "a near miss is answered, nothing else is written");

({ github } = fakeGithub({ comments: [{ id: 3, user: { login: "github-actions[bot]" }, body: reviewMarker + "\nNo suggestions.\n" }] }));
assert.match(await help({ github, context: context("/help"), core }, appConfigured), /lists no safe duplicate link, so `\/fix-duplicates` would change nothing/);

// Help and the gate agree for a maintainer, a non-maintainer and a fork.
for (const options of [{}, { permission: "read" }, { pull: { head: { ref: "x", repo: { full_name: "someone/fork" } } } }]) {
  const shown = await help({ github: fakeGithub(options).github, context: context("/help"), core }, appConfigured);
  const accepted = await acknowledge({ github: fakeGithub(options).github, context: context("/fix-duplicates"), core }, appConfigured);
  assert.equal(/\| `\/fix-duplicates` \| Available \|/.test(shown), accepted, JSON.stringify(options));
}

// The gate: an eligible command is acknowledged; an ineligible one is refused with its reasons and runs nothing.
({ github, writes } = fakeGithub());
assert.equal(await acknowledge({ github, context: context("/refresh re3data"), core }, appConfigured), true);
assert.deepEqual(writes, [["react", "eyes"]]);
({ github, writes } = fakeGithub({ permission: "read" }));
assert.equal(await acknowledge({ github, context: context("/fix-duplicates"), core }, appConfigured), false);
assert.deepEqual(writes.map(([kind]) => kind), ["react", "create"]);
assert.match(writes[1][1].body, /did not run because it needs current write access.*Nothing was changed/);
assert.match(writes[1][1].body, /\*\*Next:\*\*/);
assert.equal(await acknowledge({ github, context: context("/help"), core }, appConfigured), false, "help needs no gate");

// A command that must wait says which earlier run holds its resource; unrelated or later runs are not blamed.
const holder = { id: 30, status: "in_progress", display_title: "Comment on #12", html_url: "https://github.com/run/30" };
const otherThread = { id: 31, status: "in_progress", display_title: "Comment on #99", html_url: "https://github.com/run/31" };
const later = { id: 50, status: "queued", display_title: "Comment on #12", html_url: "https://github.com/run/50" };
const busy = { 30: [{ name: "fix-duplicates / fix", status: "in_progress" }], 31: [{ name: "fix-duplicates / fix", status: "in_progress" }] };
({ github, writes } = fakeGithub({ runs: { "commands.yml": [holder, otherThread, later] }, jobs: busy }));
assert.equal(await acknowledge({ github, context: context("/fix-duplicates"), core }, appConfigured), true);
assert.deepEqual(writes.map(([kind]) => kind), ["react", "create"]);
assert.match(writes[1][1].body, /queued behind \[an earlier run\]\(https:\/\/github\.com\/run\/30\)/);
({ github, writes } = fakeGithub({ runs: { "commands.yml": [otherThread, later] }, jobs: busy }));
await acknowledge({ github, context: context("/fix-duplicates"), core }, appConfigured);
assert.deepEqual(writes, [["react", "eyes"]], "another pull request's repair does not hold this one");
({ github, writes } = fakeGithub({ runs: { "commands.yml": [otherThread], "source-refresh.yml": [] }, jobs: { 31: [{ name: "refresh / refresh", status: "queued" }] } }));
await acknowledge({ github, context: context("/refresh re3data"), core }, appConfigured);
assert.match(writes[1][1].body, /queued behind .*run\/31.*same snapshots/, "refreshes share one queue across pull requests");
({ github, writes } = fakeGithub({ runs: { "source-refresh.yml": [{ id: 20, status: "in_progress", html_url: "https://github.com/run/20" }] } }));
await acknowledge({ github, context: context("/refresh heslar"), core }, appConfigured);
assert.match(writes[1][1].body, /run\/20/, "a scheduled refresh in progress also holds the queue");

// Every accepted command ends visibly: a reaction on success, a reply when nothing else explains the result.
({ github, writes } = fakeGithub());
assert.equal(await outcome({ github, context: context("/fix-duplicates") }, "fix-duplicates", "success"), "success");
assert.deepEqual(writes, [["react", "rocket"]]);
for (const command of ["fix-duplicates", "refresh"]) {
  ({ github, writes } = fakeGithub());
  await outcome({ github, context: context("/x") }, command, "cancelled");
  assert.deepEqual(writes.map(([kind]) => kind), ["react", "create"]);
  assert.match(writes[1][1].body, /cancelled before it finished.*actions\/runs\/42/s);
  assert.match(writes[1][1].body, /post `\/(fix-duplicates|refresh)` again/);
}
({ github, writes } = fakeGithub());
await outcome({ github, context: context("/fix-duplicates") }, "fix-duplicates", "failure");
assert.match(writes[1][1].body, /a commit may already exist/);
({ github, writes } = fakeGithub());
await outcome({ github, context: context("/refresh heslar") }, "refresh", "failure");
assert.deepEqual(writes, [["react", "confused"]], "the refresh run replies with its own per-source result");
console.log("check_commands: exact parsing, near-miss help, shared eligibility, one help comment, visible refusals and outcomes pass");
