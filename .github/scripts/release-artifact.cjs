// Trusted default-branch code for the release workflow: finds the verified deployment run of the tagged commit and
// drafts the release with that run's artifact after checking digest, commit and version. It builds nothing.
const { readFileSync } = require("node:fs");
const { createHash } = require("node:crypto");

const TAG = /^v(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$/;
const DIR = ".cache/release";

function tagOf(context) {
  const tag = String(context.ref || "").replace(/^refs\/tags\//, "");
  const match = TAG.exec(tag);
  if (!match) throw Error(`Not a release tag: ${tag}`);
  if (!/^[0-9a-f]{40}$/.test(context.sha)) throw Error("The tagged commit is not a full SHA");
  return { tag, version: match[1] };
}

/** The successful deployment run on the default branch for exactly the tagged commit. */
async function verifiedRun({ github, context }) {
  tagOf(context);
  const runs = await github.paginate(github.rest.actions.listWorkflowRuns, { ...context.repo, workflow_id: "deploy.yml",
    branch: context.payload.repository?.default_branch || "main", event: "push", status: "success", head_sha: context.sha, per_page: 100 });
  const run = runs.find((entry) => entry.head_sha === context.sha && entry.conclusion === "success");
  if (!run) throw Error(`No successful verified deployment of ${context.sha}; release only a deployed commit`);
  return run.id;
}

/** Draft the release with the downloaded artifact once its digest, commit, version and health run agree. */
async function draftRelease({ github, context, core }, read = readFileSync) {
  const { tag, version } = tagOf(context);
  const manifest = JSON.parse(read(`${DIR}/manifest.json`, "utf8"));
  if (manifest.commit !== context.sha) throw Error("The artifact names another commit");
  if (manifest.version !== version) throw Error(`The artifact is version ${manifest.version}, the tag says ${version}`);
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
  const { data: release } = await github.rest.repos.createRelease({ ...context.repo, tag_name: tag, name: tag, body,
    draft: true, prerelease: version.includes("-") });
  for (const name of [manifest.archive, `${manifest.archive}.sha256`, "manifest.json"]) {
    await github.rest.repos.uploadReleaseAsset({ ...context.repo, release_id: release.id, name, data: read(`${DIR}/${name}`) });
  }
  core.info(`Drafted ${tag} with ${manifest.archive}`);
  return release.id;
}

module.exports = { verifiedRun, draftRelease, tagOf };
