// Area labels on pull requests: read from the API's file list with the reviewed rules, only ever added, never
// re-added after a removal, and only for the pull request whose head the checks ran on.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
const { addLabels, areaLabels, label } = createRequire(import.meta.url)("../../.github/scripts/labels.cjs");

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const head = "a".repeat(40);
const python = process.platform === "win32" ? "python" : "python3";
const rules = (paths) => areaLabels(paths, (_command, args, options) => execFileSync(python, args, options));

// The reviewed rules themselves, through the standard-library helper the publisher runs.
assert.deepEqual(rules(["content/stations/repository.toml", ".github/workflows/checks.yml"]), ["area:content", "area:delivery"]);
assert.deepEqual(rules(["content/snapshots/re3data.json"]), ["area:sources"], "a refresh PR's snapshot is a source change");
assert.deepEqual(rules(["package-lock.json"]), ["area:delivery"], "a dependency update is delivery");
assert.deepEqual(rules([".agents/reports/usage/usage-2026-10-25-x.md", "openspec/changes/x/tasks.md", "README.md"]), [], "usage logs and planning label nothing");
assert.throws(() => areaLabels([], () => '["bug"]'), /Unexpected output/, "the helper can only add area labels");

const KNOWN = ["area:content", "area:delivery", "area:sources", "source-refresh"];
function fakeGithub({ files, labels = [], events = [], sha = head, known = KNOWN }) {
  const writes = [];
  const pr = { number: 12, state: "open", labels, head: { sha, repo: { full_name: "contributor/guide" } } };
  const github = {
    paginate: async (method, options) => method(options),
    rest: {
      pulls: { get: async () => ({ data: pr }), listFiles: () => files, list: () => [{ number: 12 }] },
      issues: {
        listEvents: () => events,
        addLabels: async (options) => writes.push(options),
        getLabel: async ({ name }) => {
          if (!known.includes(name)) throw Object.assign(Error("Not Found"), { status: 404 });
          return { data: { name } };
        },
      },
    },
  };
  return { github, writes };
}
const context = (event = "pull_request", pullRequests = [{ number: 12 }]) => ({
  repo, payload: { workflow_run: { id: 5, event, status: "completed", head_sha: head, head_repository: { full_name: "contributor/guide" }, pull_requests: pullRequests } },
});
const logged = [];
const core = { info: (line) => logged.push(line) };
const touched = [{ filename: "content/stations/repository.toml" }, { filename: ".github/workflows/new.yml", previous_filename: ".github/workflows/old.yml" }];

// A human PR changing content and workflows receives both area labels.
let { github, writes } = fakeGithub({ files: touched });
await label({ github, context: context(), core }, rules);
assert.deepEqual(writes, [{ ...repo, issue_number: 12, labels: ["area:content", "area:delivery"] }]);

// A fork PR is matched by its head, not by the event's (empty) pull-request list.
({ github, writes } = fakeGithub({ files: touched }));
await label({ github, context: context("pull_request", []), core }, rules);
assert.equal(writes.length, 1, "a fork's PR is found among the open PRs");

// A label a maintainer removed stays removed; present labels are not added again.
({ github, writes } = fakeGithub({ files: touched, events: [{ event: "labeled", label: { name: "area:delivery" } }, { event: "unlabeled", label: { name: "area:delivery" }, actor: { login: "maintainer" } }] }));
await label({ github, context: context(), core }, rules);
assert.deepEqual(writes[0].labels, ["area:content"], "the removed label is not re-added");
({ github, writes } = fakeGithub({ files: touched, labels: [{ name: "area:content" }, { name: "area:delivery" }] }));
await label({ github, context: context(), core }, rules);
assert.deepEqual(writes, [], "nothing to add");

// Only the checked head is labelled, and only after pull-request runs.
({ github, writes } = fakeGithub({ files: touched, sha: "b".repeat(40) }));
await label({ github, context: context(), core }, rules);
assert.deepEqual(writes, [], "a PR that moved on since the checks is left for its own run");
for (const event of ["merge_group", "push"]) {
  ({ github, writes } = fakeGithub({ files: touched }));
  await label({ github, context: context(event), core }, rules);
  assert.deepEqual(writes, [], `${event} runs label nothing`);
}

// A label the repository does not have yet is skipped and named, never created with GitHub's defaults.
({ github, writes } = fakeGithub({ files: touched, known: ["area:content"] }));
await label({ github, context: context(), core }, rules);
assert.deepEqual(writes[0].labels, ["area:content"], "only labels that exist are added");
assert(logged.some((line) => line.includes("area:delivery not in the repository yet")), "the skipped label is named");
({ github, writes } = fakeGithub({ files: touched, known: [] }));
await label({ github, context: context(), core }, rules);
assert.deepEqual(writes, [], "nothing is added before the declared labels exist");

// The shared adder used by the refresh publisher behaves the same.
({ github, writes } = fakeGithub({ files: [] }));
assert.deepEqual(await addLabels(github, repo, 3, ["source-refresh", "source-refresh"], []), { added: ["source-refresh"], absent: [] });
assert.deepEqual(writes, [{ ...repo, issue_number: 3, labels: ["source-refresh"] }]);
console.log("check_labels: reviewed path rules, API file lists, add-only labels for existing labels, sticky removals and checked-head admission pass");
