// Trusted default-branch code for the release workflow: finds the approved deployment run of the tagged commit and
// drafts the release with that run's artifact after checking digest, commit and version. It builds nothing.
const { readFileSync } = require("node:fs");
const { mkdirSync, writeFileSync } = require("node:fs");
const { createHash } = require("node:crypto");

const { validVersion } = require('./release-version.cjs');
const DIR = ".cache/release";
// What one publication deployed, written by the publish workflow and read by release drafting.
const PUBLISHED = ".cache/published/identity.json";
// The automation's verification record in a release body; scripts/release_body.py keeps exactly this block.
const VERIFICATION = { start: "<!-- guide-release:verification -->", end: "<!-- /guide-release:verification -->" };

function tagOf(context) {
  const tag = String(context.ref || "").replace(/^refs\/tags\//, "");
  if (!tag.startsWith('v') || !validVersion(tag.slice(1))) throw Error(`Not a release tag: ${tag}`);
  if (!/^[0-9a-f]{40}$/.test(context.sha)) throw Error("The tagged commit is not a full SHA");
  return { tag, version: tag.slice(1) };
}

/** Another tag/commit of the same run. @actions/github exposes `repo` as a getter, which object spread drops. */
function refContext(context, ref, sha) {
  const repo = context.repo;
  if (!repo?.owner || !repo?.repo) throw Error("The release context carries no repository");
  return { repo, payload: context.payload, ref, sha };
}

/** A deployment of this release tag whose production bytes are approved: a successful run, or one whose
    `production` and `approve-production` jobs succeeded while it is still publishing. Its `guide-site-<sha>`
    artifact holds those bytes. */
async function approvedRun({ github, context }) {
  const { tag } = tagOf(context);
  const runs = (await github.paginate(github.rest.actions.listWorkflowRuns, { ...context.repo, workflow_id: "deploy.yml",
    branch: tag, event: "push", head_sha: context.sha, per_page: 100 }))
    .filter((entry) => entry.head_sha === context.sha && entry.head_branch === tag && entry.event === "push");
  for (const run of runs) {
    if (run.conclusion === "success") return run.id;
    if (run.conclusion) continue;
    const jobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun, { ...context.repo, run_id: run.id,
      filter: "latest", per_page: 100 });
    const passed = (name) => jobs.some((job) => job.name === name && job.conclusion === "success");
    if (passed("production") && passed("approve-production")) return run.id;
  }
  throw Object.assign(Error(`No approved production bytes of ${context.sha}`), { code: "not-verified" });
}

/** Numeric core and SemVer prerelease precedence, independent of API tag-list ordering. */
function compareTags(a, b) {
  const parts = (tag) => { const [core, ...rest] = tag.slice(1).split("-"); return [core.split(".").map(BigInt), rest.join("-")]; };
  const [ac, ap] = parts(a), [bc, bp] = parts(b);
  for (let i = 0; i < 3; i++) if (ac[i] !== bc[i]) return ac[i] < bc[i] ? -1 : 1;
  if (!ap || !bp) return ap === bp ? 0 : ap ? -1 : 1;
  const ax = ap.split("."), bx = bp.split(".");
  for (let i = 0; i < Math.max(ax.length, bx.length); i++) {
    if (ax[i] === bx[i]) continue;
    if (ax[i] === undefined || bx[i] === undefined) return ax[i] === undefined ? -1 : 1;
    const an = /^\d+$/.test(ax[i]), bn = /^\d+$/.test(bx[i]);
    if (an && bn) return BigInt(ax[i]) < BigInt(bx[i]) ? -1 : 1;
    if (an !== bn) return an ? -1 : 1;
    return ax[i] < bx[i] ? -1 : 1;
  }
  return 0;
}

async function sources({ github, context }) {
  const branch = context.payload.repository.default_branch;
  const isTag = context.ref.startsWith("refs/tags/");
  if (!isTag && context.ref !== "refs/heads/" + branch) throw Error("Deploy only the default branch or a release tag");
  // Approval, publication and release drafting follow a tag's push run only; a failed one is retried by its rerun.
  if (isTag && context.eventName === "workflow_dispatch") {
    throw Error("A release tag deploys from its push; rerun that deployment run instead of dispatching one");
  }
  if (!/^[0-9a-f]{40}$/.test(context.sha)) throw Error("Deployment requires a full source SHA");
  const tags = (await github.paginate(github.rest.repos.listTags, { ...context.repo, per_page: 100 }))
    .filter((entry) => { try { tagOf({ ref: "refs/tags/" + entry.name, sha: entry.commit.sha }); return true; } catch { return false; } })
    .sort((a, b) => compareTags(b.name, a.name));
  const latest = tags[0];
  if (isTag && (!latest || tagOf(context).tag !== latest.name || context.sha !== latest.commit.sha)) throw Error("Only the newest release tag can replace production");
  let production = null;
  for (const entry of isTag ? tags.slice(0, 1) : tags) {
    const selected = refContext(context, "refs/tags/" + entry.name, entry.commit.sha);
    if (await available({ github, context: selected })) { production = entry; break; }
  }
  const stage = isTag ? (await github.rest.repos.getBranch({ ...context.repo, branch })).data.commit.sha : context.sha;
  if (!/^[0-9a-f]{40}$/.test(stage) || (latest && !/^[0-9a-f]{40}$/.test(latest.commit.sha))) throw Error("Invalid source commit");
  const selected = isTag ? latest : production;
  return { kind: isTag ? "tag" : "branch", staging: stage, tag: selected?.name || "", production: selected?.commit.sha || "",
    build: isTag && !production ? "true" : "false" };
}

function expectedAssets(context) {
  const { version } = tagOf(context);
  const name = `eosc-fair-guide-site-${version}-${context.sha.slice(0, 12)}.tar.gz`;
  return ["manifest.json", name, name + ".sha256"];
}

async function releaseOf(github, context) {
  try { return (await github.rest.repos.getReleaseByTag({ ...context.repo, tag: tagOf(context).tag })).data; }
  catch (error) { if (error.status !== 404) throw error; return null; }
}

async function available({ github, context }) {
  const release = await releaseOf(github, context);
  if (release && expectedAssets(context).every((name) => release.assets.some((asset) => asset.name === name))) return true;
  try { await approvedRun({ github, context }); return true; }
  catch (error) {
    if (error.code !== "not-verified") throw error;
    if (release && !release.draft) throw Error(`Published release ${tagOf(context).tag} has incomplete assets and no verified fallback`);
    return false;
  }
}

/** Serialized image publishers recheck the newest verified production source immediately before moving aliases. */
async function assertPromotion({ github, context }) {
  const { tag } = tagOf(context);
  const selected = await sources({ github, context: refContext(context, 'refs/heads/' + context.payload.repository.default_branch, context.sha) });
  if (selected.tag !== tag || selected.production !== context.sha) throw Error('A newer verified production release superseded this image');
}

async function assetBytes(github, repo, asset) {
  if (!Number.isSafeInteger(asset.size) || asset.size < 0 || asset.size > 512 * 1024 * 1024) throw Error("Release asset size is invalid");
  const response = await github.rest.repos.getReleaseAsset({ ...repo, asset_id: asset.id, headers: { accept: "application/octet-stream" } });
  const data = Buffer.from(response.data);
  if (data.length > 512 * 1024 * 1024) throw Error("Release asset exceeds the download bound");
  return data;
}

/** Where a release's approved bytes are, without fetching them: its complete release assets (no run), or the
    approved Actions artifact of the run that checked them, which a just-created tag uses until the draft exists. */
async function productionSource({ github, context }) {
  const release = await releaseOf(github, context);
  if (release && expectedAssets(context).every((name) => release.assets.some((asset) => asset.name === name))) {
    return { run: "", release };
  }
  return { run: await approvedRun({ github, context }) };
}

/** Reuse durable release assets, written to .cache/release, or name the run whose artifact holds the bytes. */
async function reuse({ github, context }, write = writeFileSync) {
  const { run, release } = await productionSource({ github, context });
  if (run) return { run };
  const names = expectedAssets(context);
  mkdirSync(DIR, { recursive: true });
  for (const filename of names) {
    const asset = release.assets.find((entry) => entry.name === filename);
    const data = await assetBytes(github, context.repo, asset);
    write(`${DIR}/${filename}`, data);
  }
  // The assembler verifies manifest identity, digest, archive members and the health revision before publication.
  return { run: "" };
}

const NO_RELEASE = { tag: "", sha: "", run: "" };

/** The release a completed publication deployed, bound to its still-current tag and the run holding its approved
    artifact; no tag when that publication deployed nothing or no release, or the release already has its assets.
    workflow_run runs only trusted default-branch code; the record must come from this repository's successful
    publish workflow, which keeps it as the `pages-identity` artifact only after a Pages deployment. */
async function publishedRelease({ github, context }, read = readFileSync) {
  const run = (await github.rest.actions.getWorkflowRun({ ...context.repo, run_id: context.payload.workflow_run.id })).data;
  if (run.conclusion !== "success" || run.event !== "workflow_run" || run.head_repository?.full_name !== `${context.repo.owner}/${context.repo.repo}` ||
      String(run.path).split("@")[0] !== ".github/workflows/publish.yml") throw Error("Not a successful repository publication");
  const { data: kept } = await github.rest.actions.listWorkflowRunArtifacts({ ...context.repo, run_id: run.id,
    name: "pages-identity", per_page: 10 });
  if (!kept.artifacts.some((artifact) => artifact.name === "pages-identity")) return NO_RELEASE;
  const record = JSON.parse(read(PUBLISHED, "utf8"));
  if (record.formatVersion !== 1 || typeof record.tag !== "string") throw Error("Invalid publication record");
  if (!record.tag) return NO_RELEASE;
  const selected = refContext(context, "refs/tags/" + record.tag, record.production);
  const { tag } = tagOf(selected);
  if ((await github.rest.repos.getCommit({ ...context.repo, ref: tag })).data.sha !== selected.sha) {
    throw Error("Release tag moved after publication");
  }
  const { run: approved } = await productionSource({ github, context: selected });
  return approved ? { tag, sha: selected.sha, run: String(approved) } : NO_RELEASE;
}

/** Draft the release with the downloaded artifact once its digest, commit, version and health run agree. */
async function draftRelease({ github, context, core }, read = readFileSync) {
  const { tag, version } = tagOf(context);
  const manifest = JSON.parse(read(`${DIR}/manifest.json`, "utf8"));
  if (manifest.commit !== context.sha) throw Error("The artifact names another commit");
  if (manifest.version !== version) throw Error(`The artifact is version ${manifest.version}, the tag says ${version}`);
  if (manifest.archive !== expectedAssets(context)[1]) throw Error("The artifact archive name does not match the tag and commit");
  if (manifest.health?.run !== "passed" || !manifest.health?.generated_at) throw Error("The artifact's check run did not pass");
  if (!['testing', 'production'].includes(manifest.build?.status)) throw Error('The artifact carries no valid release status');
  const archive = read(`${DIR}/${manifest.archive}`);
  const digest = createHash("sha256").update(archive).digest("hex");
  const declared = String(read(`${DIR}/${manifest.archive}.sha256`, "utf8")).split(/\s+/)[0];
  if (digest !== manifest.sha256 || digest !== declared) throw Error("The archive does not match its digest");
  // Reviewed notes replace the first paragraph through scripts/release_body.py; the marked verification record
  // stays byte for byte.
  const body = [
    `The merged pull requests and direct commits of ${tag} are listed in ` +
      `[CHANGELOG.md](https://github.com/${context.repo.owner}/${context.repo.repo}/blob/${tag}/CHANGELOG.md).`, "",
    VERIFICATION.start,
    `Site of commit \`${context.sha}\`, version ${version}, checked on ${manifest.health.generated_at}.`, "",
    `The attached \`${manifest.archive}\` is the site that passed the checks and was deployed (SHA-256 \`${digest}\`).`,
    ...(process.env.RELEASE_IMAGE
      ? ["", `Container image: \`${process.env.RELEASE_IMAGE}\`, signed and attested against its digest.`]
      : []),
    "", `Release status: ${manifest.build.status} (recorded by Tag release).`,
    VERIFICATION.end,
  ].join("\n");
  let release = await releaseOf(github, context);
  const documents = [manifest.archive, `${manifest.archive}.sha256`, "manifest.json"].map((name) => [name, Buffer.from(read(`${DIR}/${name}`))]);
  const missing = [];
  for (const [name, data] of documents) {
    const asset = release?.assets.find((entry) => entry.name === name);
    if (asset) {
      if (!data.equals(await assetBytes(github, context.repo, asset))) throw Error("Existing release asset differs: " + name);
    } else missing.push([name, data]);
  }
  if (release && !release.draft && missing.length) throw Error("A published release is missing required assets");
  if (!release) release = (await github.rest.repos.createRelease({ ...context.repo, tag_name: tag, name: tag, body,
    draft: true, prerelease: version.includes("-") })).data;
  for (const [name, data] of missing) {
    await github.rest.repos.uploadReleaseAsset({ ...context.repo, release_id: release.id, name, data });
  }
  core.info(`Release ${tag} carries ${manifest.archive}`);
  return release.id;
}

module.exports = { approvedRun, draftRelease, tagOf, refContext, compareTags, sources, productionSource, reuse,
  publishedRelease, assertPromotion, PUBLISHED, VERIFICATION };
