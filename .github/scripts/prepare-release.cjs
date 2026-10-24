// Trusted default-branch dispatch code. Metadata, changelog writing and the prepared-file set belong to
// scripts/release_versions.py; this module consumes that manifest and owns only GitHub reads and delivery.
const {readFileSync, mkdirSync, writeFileSync, realpathSync} = require('node:fs');
const {createHash} = require('node:crypto');
const {resolve, relative, isAbsolute} = require('node:path');
const policy = require('../release-prepared-files.json');
const MANIFEST = '.cache/release/prepared.json';
const HISTORY = '.cache/release/history.json';
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
async function collect({github, context, core}, write = writeFileSync, read = readFileSync) {
  const {base, version} = dispatch(context);
  await current(github, context, base);
  try {
    await github.rest.git.getRef({...context.repo, ref: `tags/v${version}`});
    throw Error('The requested release is already tagged');
  } catch (error) { if (error.status !== 404) throw error; }
  const history = JSON.parse(read(HISTORY, 'utf8'));
  if (history.formatVersion !== 1 || history.source !== context.sha ||
      !(history.previousTag === null || (typeof history.previousTag === 'string' &&
        history.previousTag.startsWith('v') && validVersion(history.previousTag.slice(1)))) ||
      !Array.isArray(history.commits) || history.commits.some(sha => !/^[0-9a-f]{40}$/.test(sha)) ||
      new Set(history.commits).size !== history.commits.length || !Array.isArray(history.firstParent))
    throw Error('Invalid or stale release history export');
  const seen = new Set();
  for (const commit of history.firstParent) {
    if (!commit || !history.commits.includes(commit.sha) || seen.has(commit.sha) ||
        typeof commit.subject !== 'string' || !commit.subject.trim()) throw Error('Invalid release history export');
    seen.add(commit.sha);
  }
  if (!history.commits.length || !history.firstParent.length) throw Error('No commits since the previous tag');
  // Pagination must complete; no search-result cap, timestamp cutoff or single
  // page. The Python script filters merged commits by actual local ancestry.
  const prs = await github.paginate(github.rest.pulls.list,
    {...context.repo, state: 'closed', base, per_page: 100});
  const associations = {};
  // Bound simultaneous API calls; paginate every candidate, including rebased PR commits.
  for (let start = 0; start < history.firstParent.length; start += 4) {
    await Promise.all(history.firstParent.slice(start, start + 4).map(async commit => {
      const linked = await github.paginate(github.rest.repos.listPullRequestsAssociatedWithCommit,
        {...context.repo, commit_sha: commit.sha, per_page: 100});
      if (linked.some(pr => !Number.isSafeInteger(pr.number) || pr.number < 1)) throw Error('Malformed commit-to-PR association');
      associations[commit.sha] = [...new Set(linked.map(pr => pr.number))].sort((a, b) => a - b);
    }));
  }
  const {data: run} = await github.rest.actions.getWorkflowRun({...context.repo, run_id: context.runId});
  mkdirSync('.cache/release', {recursive: true});
  write('.cache/release/prs.json', JSON.stringify(prs));
  write('.cache/release/associations.json', JSON.stringify({formatVersion: 1, source: context.sha,
    previousTag: history.previousTag, repository: `${context.repo.owner}/${context.repo.repo}`, base,
    associations: Object.fromEntries(history.firstParent.map(commit => [commit.sha, associations[commit.sha]]))}));
  core.setOutput('timestamp', run.created_at);
  core.setOutput('date', run.created_at.slice(0, 10));
}
function preparedFiles(manifest, version, root = resolve(__dirname, '../..')) {
  if (policy.formatVersion !== 1 || !Array.isArray(policy.metadata) || !Array.isArray(policy.additional))
    throw Error('Invalid release path policy');
  const expected = [...policy.metadata, ...policy.additional];
  if (!expected.length || new Set(expected).size !== expected.length ||
      manifest.formatVersion !== 1 || manifest.version !== version || !Array.isArray(manifest.files) ||
      manifest.files.length !== expected.length) throw Error('Invalid prepared-file manifest');
  const seen = new Set();
  const canonicalRoot = realpathSync(root);
  for (const item of manifest.files) {
    const name = item?.path;
    if (typeof name !== 'string' || !expected.includes(name) || /[\\:]/.test(name) ||
        name.split('/').some(part => ['', '.', '..'].includes(part)) ||
        isAbsolute(name) || typeof item?.sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(item.sha256) ||
        seen.has(name)) throw Error('Invalid prepared-file manifest');
    const candidate = resolve(canonicalRoot, name);
    const actual = realpathSync(candidate);
    const local = relative(canonicalRoot, actual);
    if (actual !== candidate || isAbsolute(local) || local === '..' || local.startsWith('../') || local.startsWith('..\\'))
      throw Error(`Prepared path escapes or aliases another file: ${name}`);
    seen.add(name);
  }
  return manifest.files;
}
async function propose({github, context, core}, read = readFileSync, root) {
  const {base, version, branch} = dispatch(context);
  const parent = await current(github, context, base);
  const manifest = JSON.parse(read(MANIFEST, 'utf8'));
  const files = preparedFiles(manifest, version, root).map(item => {
    const content = read(item.path);
    if (createHash('sha256').update(content).digest('hex') !== item.sha256)
      throw Error(`Prepared file changed after preparation: ${item.path}`);
    return {path: item.path, content};
  });
  const tree = [];
  for (const {path, content} of files) {
    const {data} = await github.rest.git.createBlob({...context.repo, content: content.toString('base64'), encoding: 'base64'});
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
    body: 'Prepares the version, release dates, citation/Zenodo metadata and the complete PR/direct-commit changelog.\n\nReview the metadata and required checks, then merge. Creating the tag requires the separate Tag release dispatch.\n\nPrepared by the repository release automation; no AI content generation.',
    maintainer_can_modify: true});
  core.info(pr.html_url);
}
/** The tag ruleset requires a successful `github-pages` deployment of the tagged commit. Before tagging, require one
    for the current default-branch commit, or name the deployment or publish run to wait for. */
async function deployed({github, context, core}) {
  const {base} = dispatch(context);
  await current(github, context, base);
  const deployments = await github.paginate(github.rest.repos.listDeployments, {...context.repo, environment: 'github-pages',
    sha: context.sha, per_page: 100});
  for (const deployment of deployments.filter(entry => entry.sha === context.sha)) {
    const statuses = await github.paginate(github.rest.repos.listDeploymentStatuses, {...context.repo,
      deployment_id: deployment.id, per_page: 100});
    if (statuses.some(status => status.state === 'success')) {
      core.info(`Commit ${context.sha} was published by deployment ${deployment.id}`);
      return deployment.id;
    }
  }
  const runs = [];
  for (const workflow of ['deploy.yml', 'publish.yml']) {
    runs.push(...(await github.paginate(github.rest.actions.listWorkflowRuns, {...context.repo, workflow_id: workflow,
      branch: base, head_sha: context.sha, per_page: 100})).filter(run => run.head_sha === context.sha && run.head_branch === base));
  }
  const waiting = runs.find(run => !run.conclusion);
  throw Error(waiting
    ? `The current default-branch commit is still being deployed; wait for ${waiting.html_url} to finish, then run Tag release again`
    : `The current default-branch commit has no successful deployment${runs.length ? ` (latest run: ${runs[0].html_url})` : ''}; ` +
      'run Deploy the verified site on the default branch, then run Tag release again');
}
async function tag({github, context, core}, read = readFileSync) {
  const {base, version} = dispatch(context);
  const status = context.payload.inputs.release_status;
  if (!['testing', 'production'].includes(status)) throw Error('Choose release_status testing or production');
  await current(github, context, base);
  if (JSON.parse(read('package.json', 'utf8')).version !== version) throw Error('The committed metadata has another version');
  // No updateRef: an existing tag is never moved, even on a dispatch retry.
  try {
    await github.rest.git.getRef({...context.repo, ref: `tags/v${version}`});
    throw Error('The release tag already exists; its status cannot be changed');
  } catch (error) { if (error.status !== 404) throw error; }
  await current(github, context, base);
  const {data: annotated} = await github.rest.git.createTag({...context.repo, tag: `v${version}`,
    message: `Release v${version}\n\nFair-Guide-Release-Status: ${status}\n`, object: context.sha, type: 'commit'});
  const {data} = await github.rest.git.createRef({...context.repo, ref: `refs/tags/v${version}`, sha: annotated.sha});
  core.info(`Created ${data.ref} at ${context.sha} with status ${status}`);
}
module.exports = {validVersion, dispatch, collect, propose, deployed, tag, preparedFiles};
