// Trusted default-branch dispatch code. Metadata and changelog writing belongs to
// scripts/release_versions.py; this module owns only GitHub reads and delivery.
const {readFileSync, mkdirSync, writeFileSync} = require('node:fs');
const FILES = ['content/guide.toml', 'CITATION.cff', 'package.json', 'package-lock.json',
  'pyproject.toml', 'CHANGELOG.md', 'content/provenance.toml', 'content/identifiers.toml'];
const { validVersion } = require('./release-version.cjs');
function dispatch(context) {
  const base = context.payload.repository.default_branch;
  const version = context.payload.inputs.version;
  if (context.eventName !== 'workflow_dispatch' || context.ref !== `refs/heads/${base}` || !validVersion(version))
    throw Error('Run this dispatch on the default branch with a SemVer version');
  return {base, version, branch: `release/${version}`};
}
async function current(github, context, base) {
  const {data} = await github.rest.git.getRef({...context.repo, ref: `heads/${base}`});
  if (data.object.sha !== context.sha) throw Error('The default branch moved; rerun the dispatch on its current commit');
  return (await github.rest.git.getCommit({...context.repo, commit_sha: context.sha})).data;
}
async function collect({github, context, core}, write = writeFileSync) {
  const {base, version} = dispatch(context);
  await current(github, context, base);
  try {
    await github.rest.git.getRef({...context.repo, ref: `tags/v${version}`});
    throw Error('The requested release is already tagged');
  } catch (error) { if (error.status !== 404) throw error; }
  // Pagination must complete; no search-result cap, timestamp cutoff or single
  // page. The Python script filters merged commits by actual local ancestry.
  const prs = await github.paginate(github.rest.pulls.list,
    {...context.repo, state: 'closed', base, per_page: 100});
  mkdirSync('.cache/release', {recursive: true});
  write('.cache/release/prs.json', JSON.stringify(prs));
  const {data: run} = await github.rest.actions.getWorkflowRun({...context.repo, run_id: context.runId});
  core.setOutput('timestamp', run.created_at);
  core.setOutput('date', run.created_at.slice(0, 10));
}
async function propose({github, context, core}, read = readFileSync) {
  const {base, version, branch} = dispatch(context);
  const parent = await current(github, context, base);
  const tree = [];
  for (const path of FILES) {
    const content = read(path).toString('base64');
    const {data} = await github.rest.git.createBlob({...context.repo, content, encoding: 'base64'});
    tree.push({path, mode: '100644', type: 'blob', sha: data.sha});
  }
  const {data: built} = await github.rest.git.createTree({...context.repo, base_tree: parent.tree.sha, tree});
  const message = `Prepare release ${version}`;
  let ref;
  try { ref = (await github.rest.git.getRef({...context.repo, ref: `heads/${branch}`})).data; }
  catch (error) { if (error.status !== 404) throw error; }
  if (ref) {
    // Recover a failed PR creation; never overwrite human changes or rebase an
    // old proposal. A reviewed, closed proposal is not silently reopened.
    const {data: commit} = await github.rest.git.getCommit({...context.repo, commit_sha: ref.object.sha});
    if (commit.parents.length !== 1 || commit.parents[0].sha !== context.sha || commit.tree.sha !== built.sha || commit.message !== message)
      throw Error('The release branch exists with different content; review it manually');
  } else {
    const {data: commit} = await github.rest.git.createCommit({...context.repo, message, tree: built.sha, parents: [context.sha]});
    await github.rest.git.createRef({...context.repo, ref: `refs/heads/${branch}`, sha: commit.sha});
  }
  const previous = await github.paginate(github.rest.pulls.list,
    {...context.repo, state: 'all', base, head: `${context.repo.owner}:${branch}`, per_page: 100});
  if (previous.some(pr => pr.state === 'closed')) throw Error('This release proposal was closed; review it manually');
  if (previous.length) { core.info(previous[0].html_url); return; }
  const {data: pr} = await github.rest.pulls.create({...context.repo, base, head: branch, title: message,
    body: 'Prepares the version, release dates and the complete merged-pull-request changelog.\n\nReview the metadata and required checks, then merge. Creating the tag requires the separate Tag release dispatch.\n\nPrepared by the repository release automation; no AI content generation.',
    maintainer_can_modify: true});
  core.info(pr.html_url);
}
async function tag({github, context, core}, read = readFileSync) {
  const {base, version, branch} = dispatch(context);
  const status = context.payload.inputs.release_status;
  if (!['testing', 'production'].includes(status)) throw Error('Choose release_status testing or production');
  await current(github, context, base);
  if (JSON.parse(read('package.json', 'utf8')).version !== version) throw Error('The merged metadata has another version');
  const prs = await github.paginate(github.rest.pulls.list,
    {...context.repo, state: 'closed', base, head: `${context.repo.owner}:${branch}`, per_page: 100});
  if (!prs.some(pr => pr.merged_at && pr.merge_commit_sha === context.sha && pr.head?.repo?.full_name === `${context.repo.owner}/${context.repo.repo}`))
    throw Error('Tag only the current default-branch commit that merged this release pull request');
  // No updateRef: an existing tag is never moved, even on a dispatch retry.
  try {
    await github.rest.git.getRef({...context.repo, ref: `tags/v${version}`});
    throw Error('The release tag already exists; its status cannot be changed');
  } catch (error) { if (error.status !== 404) throw error; }
  const {data: annotated} = await github.rest.git.createTag({...context.repo, tag: `v${version}`,
    message: `Release v${version}\n\nFair-Guide-Release-Status: ${status}\n`, object: context.sha, type: 'commit'});
  const {data} = await github.rest.git.createRef({...context.repo, ref: `refs/tags/v${version}`, sha: annotated.sha});
  core.info(`Created ${data.ref} at ${context.sha} with status ${status}`);
}
module.exports = {FILES, validVersion, dispatch, collect, propose, tag};
