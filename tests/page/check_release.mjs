// The release attaches the verified deployment's artifact: the tagged commit's successful run, matching digest,
// commit, version and a passed check run, drafted for the maintainer to publish. Nothing is built.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
const { verifiedRun, draftRelease, tagOf } = createRequire(import.meta.url)("../../.github/scripts/release-artifact.cjs");

const repo = { owner: "motyc", repo: "eosc-fair-guide" };
const sha = "a".repeat(40);
const context = (ref = "refs/tags/v1.0.0-alpha.1", commit = sha) => ({ repo, ref, sha: commit, payload: { repository: { default_branch: "main" } } });
const core = { info() {} };
const archive = Buffer.from("site bytes");
const digest = createHash("sha256").update(archive).digest("hex");
const name = "eosc-fair-guide-site-1.0.0-alpha.1-aaaaaaaaaaaa";
const manifest = { name, version: "1.0.0-alpha.1", commit: sha, archive: `${name}.tar.gz`, sha256: digest,
  health: { generated_at: "2026-10-12T00:00:00Z", run: "passed" } };
const files = (overrides = {}, archiveBytes = archive) => (path) => {
  if (path.endsWith("manifest.json")) return JSON.stringify({ ...manifest, ...overrides });
  if (path.endsWith(".sha256")) return `${digest}  ${name}.tar.gz\n`;
  return archiveBytes;
};
function fake(runs = []) {
  const calls = [];
  return { calls, github: { paginate: async (method, options) => method(options), rest: {
    actions: { listWorkflowRuns: (options) => { calls.push(["runs", options]); return runs; } },
    repos: {
      createRelease: async (options) => { calls.push(["release", options]); return { data: { id: 77 } }; },
      uploadReleaseAsset: async (options) => calls.push(["asset", options.name]),
    },
  } } };
}

assert.deepEqual(tagOf(context()), { tag: "v1.0.0-alpha.1", version: "1.0.0-alpha.1" });
for (const ref of ["refs/tags/latest", "refs/heads/main", "refs/tags/v1.0", "refs/tags/v1.0.0;rm"]) assert.throws(() => tagOf(context(ref)), Error, ref);

let { github, calls } = fake([{ id: 5, head_sha: sha, conclusion: "success" }]);
assert.equal(await verifiedRun({ github, context: context() }), 5);
assert.equal(calls[0][1].workflow_id, "deploy.yml");
assert.equal(calls[0][1].head_sha, sha);
({ github } = fake([{ id: 6, head_sha: "b".repeat(40), conclusion: "success" }]));
await assert.rejects(verifiedRun({ github, context: context() }), /No successful verified deployment/);

({ github, calls } = fake());
assert.equal(await draftRelease({ github, context: context(), core }, files()), 77);
const release = calls.find(([kind]) => kind === "release")[1];
assert.equal(release.draft, true, "publication stays the maintainer's act");
assert.equal(release.prerelease, true);
assert(release.body.includes(sha) && release.body.includes(digest));
assert.deepEqual(calls.filter(([kind]) => kind === "asset").map(([, value]) => value), [`${name}.tar.gz`, `${name}.tar.gz.sha256`, "manifest.json"]);
for (const [overrides, bytes, reason] of [
  [{ commit: "c".repeat(40) }, archive, /another commit/],
  [{ version: "1.0.0" }, archive, /the tag says/],
  [{ health: { generated_at: null, run: "passed" } }, archive, /did not pass/],
  [{ health: { generated_at: "x", run: "partial" } }, archive, /did not pass/],
  [{}, Buffer.from("tampered"), /does not match its digest/],
]) {
  ({ github, calls } = fake());
  await assert.rejects(draftRelease({ github, context: context(), core }, files(overrides, bytes)), reason);
  assert(!calls.some(([kind]) => kind === "release"), "nothing is drafted from a mismatched artifact");
}
console.log("check_release: tagged commit's verified run, matching digest/commit/version/check run and a draft release pass");
