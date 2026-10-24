// The release attaches the verified deployment's artifact: the tagged commit's successful run, matching digest,
// commit, version and a passed check run, drafted for the maintainer to publish. Nothing is built.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
const { verifiedRun, draftRelease, tagOf, refContext, compareTags, sources, reuse, completedTag, assertPromotion, VERIFICATION } = createRequire(import.meta.url)("../../.github/scripts/release-artifact.cjs");
const { validVersion } = createRequire(import.meta.url)("../../.github/scripts/release-version.cjs");
const cases = JSON.parse(readFileSync(new URL("../fixtures/normalization.json", import.meta.url), "utf8"));
for (const value of cases.versions.valid) assert(validVersion(value), value);
for (const value of cases.versions.invalid) assert(!validVersion(value), JSON.stringify(value));

const repo = { owner: "dsw-nrp", repo: "eosc-fair-guide" };
const sha = "a".repeat(40);
class FakeContext {
  constructor(ref = "refs/tags/v1.0.0-alpha.1", commit = sha) {
    this.ref = ref;
    this.sha = commit;
    this.payload = { repository: { default_branch: "main" } };
  }
  get repo() { return repo; }
}
const context = (ref, commit) => new FakeContext(ref, commit);
assert.equal({ ...context() }.repo, undefined, "@actions/github keeps repo on the context prototype");
assert.deepEqual(refContext(context(), "refs/tags/v1.0.0-alpha.1", sha).repo, repo, "the carrier carries the repository");
assert.throws(() => refContext({ payload: {} }, "refs/tags/v1.0.0-alpha.1", sha), /carries no repository/);
const core = { info() {} };
const archive = Buffer.from("site bytes");
const digest = createHash("sha256").update(archive).digest("hex");
const name = "eosc-fair-guide-site-1.0.0-alpha.1-aaaaaaaaaaaa";
const manifest = { name, version: "1.0.0-alpha.1", commit: sha, archive: `${name}.tar.gz`, sha256: digest,
  build: {status: 'testing'},
  health: { generated_at: "2026-10-12T00:00:00Z", run: "passed" } };
const files = (overrides = {}, archiveBytes = archive) => (path) => {
  if (path.endsWith("manifest.json")) return JSON.stringify({ ...manifest, ...overrides });
  if (path.endsWith(".sha256")) return `${digest}  ${name}.tar.gz\n`;
  return archiveBytes;
};
function fake(runs = [], tags = []) {
  const calls = [];
  return { calls, github: { paginate: async (method, options) => method(options), rest: {
    actions: { listWorkflowRuns: (options) => { calls.push(["runs", options]); return runs; },
      getWorkflowRun: async (options) => { calls.push(["completed", options]); return { data: runs[0] }; } },
    repos: {
      createRelease: async (options) => { calls.push(["release", options]); return { data: { id: 77 } }; },
      uploadReleaseAsset: async (options) => calls.push(["asset", options.name]),
      listTags: async (options) => { calls.push(["tags", options]); return tags; },
      getBranch: async () => ({ data: { commit: { sha: "b".repeat(40) } } }),
      getCommit: async () => ({ data: { sha } }),
      getReleaseByTag: async () => { throw Object.assign(Error("absent"), { status: 404 }); },
    },
  } } };
}

assert.deepEqual(tagOf(context()), { tag: "v1.0.0-alpha.1", version: "1.0.0-alpha.1" });
for (const ref of ["refs/tags/latest", "refs/heads/main", "refs/tags/v1.0", "refs/tags/v1.0.0;rm"]) assert.throws(() => tagOf(context(ref)), Error, ref);

const goodRun = { id: 5, head_sha: sha, head_branch: "v1.0.0-alpha.1", event: "push", conclusion: "success" };
let { github, calls } = fake([goodRun]);
assert.equal(await verifiedRun({ github, context: context() }), 5);
assert.equal(calls[0][1].workflow_id, "deploy.yml");
assert.equal(calls[0][1].head_sha, sha);
assert.equal(calls[0][1].branch, "v1.0.0-alpha.1", "a default-branch run cannot supply production");
({ github } = fake([{ id: 6, head_sha: "b".repeat(40), conclusion: "success" }]));
await assert.rejects(verifiedRun({ github, context: context() }), /No successful verified deployment/);

({ github, calls } = fake());
assert.equal(await draftRelease({ github, context: context(), core }, files()), 77);
const release = calls.find(([kind]) => kind === "release")[1];
assert.equal(release.draft, true, "publication stays the maintainer's act");
assert.equal(release.prerelease, true);
assert(release.body.includes(sha) && release.body.includes(digest));
assert(release.body.includes('Release status: testing'));
assert(release.body.startsWith("The merged pull requests and direct commits of v1.0.0-alpha.1 are listed in " +
  "[CHANGELOG.md](https://github.com/dsw-nrp/eosc-fair-guide/blob/v1.0.0-alpha.1/CHANGELOG.md)."), "a durable default for the notes");
{
  // The verification record is one marked block at the end, so reviewed notes can replace everything before it.
  const start = release.body.indexOf(VERIFICATION.start);
  assert.equal(release.body.indexOf(VERIFICATION.start, start + 1), -1);
  assert(release.body.endsWith(VERIFICATION.end));
  const block = release.body.slice(start);
  assert(block.includes(sha) && block.includes(digest) && block.includes("\n\nRelease status: testing"));
}
{
  const {github, calls} = fake();
  await draftRelease({github, context: context(), core}, files({build: {status: 'production'}}));
  const body = calls.find(([kind]) => kind === 'release')[1].body;
  assert(body.includes('Release status: production'));
  assert(!body.includes('remains in testing'));
}
assert.deepEqual(calls.filter(([kind]) => kind === "asset").map(([, value]) => value), [`${name}.tar.gz`, `${name}.tar.gz.sha256`, "manifest.json"]);
for (const [overrides, bytes, reason] of [
  [{ commit: "c".repeat(40) }, archive, /another commit/],
  [{ version: "1.0.0" }, archive, /the tag says/],
  [{ health: { generated_at: null, run: "passed" } }, archive, /did not pass/],
  [{ health: { generated_at: "x", run: "partial" } }, archive, /did not pass/],
  [{ build: {} }, archive, /valid release status/],
  [{ build: {status: 'released'} }, archive, /valid release status/],
  [{}, Buffer.from("tampered"), /does not match its digest/],
]) {
  ({ github, calls } = fake());
  await assert.rejects(draftRelease({ github, context: context(), core }, files(overrides, bytes)), reason);
  assert(!calls.some(([kind]) => kind === "release"), "nothing is drafted from a mismatched artifact");
}
console.log("check_release: tagged commit's verified run, matching digest/commit/version/check run and a draft release pass");

for (const ref of ["v01.0.0", "v1.0.0-alpha..1", "v1.0.0-01"]) assert.throws(() => tagOf(context("refs/tags/" + ref)));
for (const [a, b] of [["v1.0.0-alpha.10", "v1.0.0-alpha.2"], ["v1.0.0", "v1.0.0-alpha.10"], ["v2.0.0-alpha.1", "v1.9.9"], ["v1.0.0-alpha.1", "v1.0.0-alpha"], ["v1.0.0-a", "v1.0.0-1"]]) {
  assert(compareTags(a, b) > 0, `${a} follows ${b}`);
  assert(compareTags(b, a) < 0);
  assert.equal(compareTags(a, a), 0);
}
const tag = (name, commit = sha) => ({ name, commit: { sha: commit } });
({ github, calls } = fake([{ ...goodRun, head_branch: "v1.0.0-alpha.10", head_sha: "c".repeat(40) }], [tag("v1.0.0-alpha.2"), tag("invalid"), tag("v1.0.0-alpha.10", "c".repeat(40)), tag("v01.0.0")]));
assert.deepEqual(await sources({ github, context: context("refs/heads/main") }), { staging: sha, production: "c".repeat(40), tag: "v1.0.0-alpha.10", build: "false" });
({ github } = fake([], [tag("v1.0.0-alpha.1")]));
assert.deepEqual(await sources({ github, context: context() }), { staging: "b".repeat(40), production: sha, tag: "v1.0.0-alpha.1", build: "true" });
await assert.rejects(sources({ github, context: context("refs/heads/feature") }), /default branch/);
await assert.rejects(sources({ github, context: context("refs/tags/v0.9.0") }), /newest release tag/);
({ github } = fake());
assert.deepEqual(await sources({ github, context: context("refs/heads/main") }), { staging: sha, production: "", tag: "", build: "false" });
({ github } = fake([goodRun], [tag("v1.1.0", "c".repeat(40)), tag("v1.0.0-alpha.1")]));
assert.deepEqual(await sources({ github, context: context("refs/heads/main") }), { staging: sha, production: sha, tag: "v1.0.0-alpha.1", build: "false" }, "a failed newer tag does not block previews or supersede production");
({ github } = fake([], [tag("v1.1.0", "c".repeat(40)), tag("v1.0.0-alpha.1")]));
github.rest.repos.getReleaseByTag = async () => ({ data: { draft: false, assets: [] } });
await assert.rejects(sources({ github, context: context("refs/heads/main") }), /Published release.*incomplete assets/,
  "a lost established release cannot select an older tag or the no-release placeholder");
github.rest.repos.getReleaseByTag = async () => { throw Object.assign(Error("service unavailable"), { status: 503 }); };
await assert.rejects(sources({ github, context: context("refs/heads/main") }), /service unavailable/);
({ github } = fake([goodRun], [tag("v1.0.0-alpha.1")]));
assert.equal((await sources({ github, context: context() })).build, "false", "an already verified tag reuses its original bytes on retry");

({ github } = fake([goodRun]));
assert.deepEqual(await reuse({ github, context: context() }), { run: 5 }, "the pre-release fallback requires a verified tag deployment");
const bytes = new Map([[1, Buffer.from(JSON.stringify(manifest))], [2, archive], [3, Buffer.from(digest)]]);
github.rest.repos.getReleaseByTag = async () => ({ data: { assets: [
  { id: 1, name: "manifest.json", size: bytes.get(1).length }, { id: 2, name: manifest.archive, size: archive.length },
  { id: 3, name: manifest.archive + ".sha256", size: digest.length },
] } });
github.rest.repos.getReleaseAsset = async ({ asset_id }) => ({ data: bytes.get(asset_id) });
const written = [];
assert.deepEqual(await reuse({ github, context: context() }, (path, data) => written.push([path, data])), { run: "" });
assert.deepEqual(written.map(([path]) => path), ["manifest.json", manifest.archive, manifest.archive + ".sha256"].map((file) => ".cache/release/" + file));
assert(written[1][1].equals(archive), "durable release bytes are reused unchanged");
github.rest.repos.getReleaseByTag = async () => ({ data: { assets: [{ id: 2, name: manifest.archive, size: archive.length }] } });
assert.deepEqual(await reuse({ github, context: context() }), { run: 5 }, "a partial draft falls back to the checked artifact");

const completed = { ...goodRun, path: ".github/workflows/deploy.yml", head_repository: { full_name: "dsw-nrp/eosc-fair-guide" } };
const eventContext = context();
eventContext.payload = { workflow_run: { id: 5 } };
({ github } = fake([completed]));
assert.deepEqual(await completedTag({ github, context: eventContext }), { tag: "v1.0.0-alpha.1", sha, run: 5 });
for (const changed of [{ event: "pull_request" }, { conclusion: "failure" }, { head_branch: "main" }, { path: ".github/workflows/checks.yml" }, { head_repository: { full_name: "foreign/fork" } }]) {
  ({ github } = fake([{ ...completed, ...changed }]));
  await assert.rejects(completedTag({ github, context: eventContext }));
}
({ github } = fake([completed]));
github.rest.repos.getCommit = async () => ({ data: { sha: "b".repeat(40) } });
await assert.rejects(completedTag({ github, context: eventContext }), /tag moved/);
console.log("check_release: source selection, durable byte reuse, exact tag-run lineage and moved/foreign-tag rejection pass");

({ github, calls } = fake());
let draft = null;
let interrupt = true;
const uploaded = new Map();
github.rest.repos.getReleaseByTag = async () => {
  if (!draft) throw Object.assign(Error("absent"), { status: 404 });
  return { data: draft };
};
github.rest.repos.createRelease = async (options) => {
  calls.push(["release", options]);
  draft = { id: 77, draft: true, assets: [] };
  return { data: draft };
};
github.rest.repos.uploadReleaseAsset = async (options) => {
  if (interrupt && draft.assets.length === 1) throw Error("interrupted upload");
  calls.push(["asset", options.name]);
  const id = draft.assets.length + 1;
  uploaded.set(id, Buffer.from(options.data));
  draft.assets.push({ id, name: options.name, size: options.data.length });
};
github.rest.repos.getReleaseAsset = async ({ asset_id }) => ({ data: uploaded.get(asset_id) });
await assert.rejects(draftRelease({ github, context: context(), core }, files()), /interrupted upload/);
assert.equal(draft.assets.length, 1);
interrupt = false;
assert.equal(await draftRelease({ github, context: context(), core }, files()), 77);
assert.equal(calls.filter(([kind]) => kind === "release").length, 1, "retry reuses the existing draft");
assert.equal(draft.assets.length, 3, "retry uploads only the missing files");
const writes = calls.length;
draft.draft = false;
assert.equal(await draftRelease({ github, context: context(), core }, files()), 77);
assert.equal(calls.length, writes, "a complete published release is untouched");
uploaded.set(1, Buffer.from("tampered existing asset"));
await assert.rejects(draftRelease({ github, context: context(), core }, files()), /Existing release asset differs/);
assert.equal(calls.length, writes, "conflicting assets are never overwritten or deleted");
await assert.rejects(draftRelease({ github, context: context(), core }, files({ archive: "../private" })), /archive name/);
console.log("check_release: partial drafts recover, verified tags reuse bytes, complete releases are idempotent and conflicts are refused");

({ github } = fake([goodRun], [tag("v1.0.0-alpha.1")]));
await assertPromotion({ github, context: context() });
github.rest.repos.listTags = async () => [tag("v2.0.0", "c".repeat(40)), tag("v1.0.0-alpha.1")];
github.rest.actions.listWorkflowRuns = async ({ head_sha }) => head_sha === "c".repeat(40)
  ? [{ ...goodRun, head_sha, head_branch: "v2.0.0" }] : [goodRun];
await assert.rejects(assertPromotion({ github, context: context() }), /superseded/,
  "a delayed older release cannot move aliases after a newer production release is verified");
