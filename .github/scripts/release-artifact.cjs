// Trusted default-branch code for the release workflow: finds the verified deployment run of the tagged commit and
// drafts the release with that run's artifact after checking digest, commit and version. It builds nothing.
const { readFileSync } = require("node:fs");
const { mkdirSync, writeFileSync } = require("node:fs");
const { createHash } = require("node:crypto");

const TAG = /^v((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)$/;
const DIR = ".cache/release";

function tagOf(context) {
  const tag = String(context.ref || "").replace(/^refs\/tags\//, "");
  const match = TAG.exec(tag);
  if (!match || tag.split("-").slice(1).join("-").split(".").some((part) => /^0\d+$/.test(part))) throw Error(`Not a release tag: ${tag}`);
  if (!/^[0-9a-f]{40}$/.test(context.sha)) throw Error("The tagged commit is not a full SHA");
  return { tag, version: match[1] };
}

/** The successful deployment triggered by this exact release tag and commit. */
async function verifiedRun({ github, context }) {
  tagOf(context);
  const runs = await github.paginate(github.rest.actions.listWorkflowRuns, { ...context.repo, workflow_id: "deploy.yml",
    branch: tagOf(context).tag, event: "push", status: "success", head_sha: context.sha, per_page: 100 });
  const run = runs.find((entry) => entry.head_sha === context.sha && entry.head_branch === tagOf(context).tag && entry.event === "push" && entry.conclusion === "success");
  if (!run) throw Object.assign(Error(`No successful verified deployment of ${context.sha}; release only a deployed commit`), { code: "not-verified" });
  return run.id;
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
  if (!/^[0-9a-f]{40}$/.test(context.sha)) throw Error("Deployment requires a full source SHA");
  const tags = (await github.paginate(github.rest.repos.listTags, { ...context.repo, per_page: 100 }))
    .filter((entry) => { try { tagOf({ ref: "refs/tags/" + entry.name, sha: entry.commit.sha }); return true; } catch { return false; } })
    .sort((a, b) => compareTags(b.name, a.name));
  const latest = tags[0];
  if (isTag && (!latest || tagOf(context).tag !== latest.name || context.sha !== latest.commit.sha)) throw Error("Only the newest release tag can replace production");
  let production = null;
  for (const entry of isTag ? tags.slice(0, 1) : tags) {
    const selected = { ...context, ref: "refs/tags/" + entry.name, sha: entry.commit.sha };
    if (await available({ github, context: selected })) { production = entry; break; }
  }
  const stage = isTag ? (await github.rest.repos.getBranch({ ...context.repo, branch })).data.commit.sha : context.sha;
  if (!/^[0-9a-f]{40}$/.test(stage) || (latest && !/^[0-9a-f]{40}$/.test(latest.commit.sha))) throw Error("Invalid source commit");
  const selected = isTag ? latest : production;
  return { staging: stage, tag: selected?.name || "", production: selected?.commit.sha || "", build: isTag && !production ? "true" : "false" };
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
  try { await verifiedRun({ github, context }); return true; }
  catch (error) { if (error.code !== "not-verified") throw error; return false; }
}

async function assetBytes(github, repo, asset) {
  if (!Number.isSafeInteger(asset.size) || asset.size < 0 || asset.size > 512 * 1024 * 1024) throw Error("Release asset size is invalid");
  const response = await github.rest.repos.getReleaseAsset({ ...repo, asset_id: asset.id, headers: { accept: "application/octet-stream" } });
  const data = Buffer.from(response.data);
  if (data.length > 512 * 1024 * 1024) throw Error("Release asset exceeds the download bound");
  return data;
}

/** Reuse durable release assets; a just-created tag can use its successful Actions artifact until the draft exists. */
async function reuse({ github, context }, write = writeFileSync) {
  const release = await releaseOf(github, context);
  const names = expectedAssets(context);
  if (!release || !names.every((name) => release.assets.some((asset) => asset.name === name))) return { run: await verifiedRun({ github, context }) };
  mkdirSync(DIR, { recursive: true });
  for (const filename of names) {
    const asset = release.assets.find((entry) => entry.name === filename);
    const data = await assetBytes(github, context.repo, asset);
    write(`${DIR}/${filename}`, data);
  }
  // The assembler verifies manifest identity, digest, archive members and the health revision before publication.
  return { run: "" };
}

/** workflow_run runs only trusted default-branch code; bind the completed run to the still-current tag. */
async function completedTag({ github, context }) {
  const run = (await github.rest.actions.getWorkflowRun({ ...context.repo, run_id: context.payload.workflow_run.id })).data;
  if (run.conclusion !== "success" || run.event !== "push" || run.head_repository?.full_name !== `${context.repo.owner}/${context.repo.repo}` ||
      String(run.path).split("@")[0] !== ".github/workflows/deploy.yml") throw Error("Not a successful repository deployment");
  const result = { ...context, ref: "refs/tags/" + run.head_branch, sha: run.head_sha };
  const { tag } = tagOf(result);
  const commit = (await github.rest.repos.getCommit({ ...context.repo, ref: tag })).data.sha;
  if (commit !== result.sha) throw Error("Release tag moved after verification");
  return { tag, sha: result.sha, run: run.id };
}

/** Draft the release with the downloaded artifact once its digest, commit, version and health run agree. */
async function draftRelease({ github, context, core }, read = readFileSync) {
  const { tag, version } = tagOf(context);
  const manifest = JSON.parse(read(`${DIR}/manifest.json`, "utf8"));
  if (manifest.commit !== context.sha) throw Error("The artifact names another commit");
  if (manifest.version !== version) throw Error(`The artifact is version ${manifest.version}, the tag says ${version}`);
  if (manifest.archive !== expectedAssets(context)[1]) throw Error("The artifact archive name does not match the tag and commit");
  if (manifest.health?.run !== "passed" || !manifest.health?.generated_at) throw Error("The artifact's check run did not pass");
  const archive = read(`${DIR}/${manifest.archive}`);
  const digest = createHash("sha256").update(archive).digest("hex");
  const declared = String(read(`${DIR}/${manifest.archive}.sha256`, "utf8")).split(/\s+/)[0];
  if (digest !== manifest.sha256 || digest !== declared) throw Error("The archive does not match its digest");
  const body = [
    `Site of commit \`${context.sha}\`, version ${version}, checked on ${manifest.health.generated_at}.`, "",
    `The attached \`${manifest.archive}\` is the site that passed the checks and was deployed (SHA-256 \`${digest}\`).`,
    "The guide remains in testing until EOSC CZ agrees it.",
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

module.exports = { verifiedRun, draftRelease, tagOf, compareTags, sources, reuse, completedTag };
