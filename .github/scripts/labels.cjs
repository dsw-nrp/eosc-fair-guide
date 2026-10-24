// Trusted default-branch code that only adds labels. A label that was ever removed from the issue or pull request
// is not added again, so a person's removal sticks; the event history is the record of it.
const { execFileSync } = require("node:child_process");
const { matches } = require("./comment-summary.cjs");

const AREA = /^area:[a-z]+$/;

async function removedBefore(github, repo, number) {
  const events = await github.paginate(github.rest.issues.listEvents, { ...repo, issue_number: number, per_page: 100 });
  return new Set(events.filter((event) => event.event === "unlabeled" && event.label?.name).map((event) => event.label.name));
}

/** Add the wanted labels that are neither present nor removed before; returns the ones added. */
async function addLabels(github, repo, number, wanted, current = []) {
  const present = new Set(current.map((label) => (typeof label === "string" ? label : label?.name)));
  const missing = [...new Set(wanted)].filter((name) => !present.has(name));
  if (!missing.length) return [];
  const removed = await removedBefore(github, repo, number);
  const added = missing.filter((name) => !removed.has(name));
  if (added.length) await github.rest.issues.addLabels({ ...repo, issue_number: number, labels: added });
  return added;
}

/** The area labels for changed paths, from the reviewed rules through `scripts/area_labels.py`. */
function areaLabels(paths, run = execFileSync) {
  const labels = JSON.parse(run("python3", ["scripts/area_labels.py"], { input: JSON.stringify(paths), encoding: "utf8" }));
  if (!Array.isArray(labels) || !labels.every((name) => typeof name === "string" && AREA.test(name))) {
    throw Error("Unexpected output from scripts/area_labels.py");
  }
  return labels;
}

/** After a pull request's checks: add the area labels its changed files call for, read from the API, never the
    artifact, so a fork cannot choose its labels. */
async function label({ github, context, core }, compute = areaLabels) {
  const run = context.payload.workflow_run;
  if (run.event !== "pull_request" || run.status !== "completed") return;
  const listed = run.pull_requests?.length ? run.pull_requests : await github.paginate(github.rest.pulls.list, { ...context.repo, state: "open", per_page: 100 });
  for (const candidate of listed) {
    if (!Number.isSafeInteger(candidate.number)) continue;
    const { data: pr } = await github.rest.pulls.get({ ...context.repo, pull_number: candidate.number });
    if (!matches(pr, run)) continue;
    const files = await github.paginate(github.rest.pulls.listFiles, { ...context.repo, pull_number: pr.number, per_page: 100 });
    const paths = files.flatMap((file) => [file.filename, file.previous_filename].filter((path) => typeof path === "string"));
    const added = await addLabels(github, context.repo, pr.number, compute(paths), pr.labels || []);
    core.info(`PR ${pr.number}: ${added.length ? "added " + added.join(", ") : "no area label to add"}`);
  }
}

module.exports = { addLabels, areaLabels, label };
