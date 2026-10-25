// No GitHub mutations: exact-source, delivery and recovery fixtures.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {copyFileSync, mkdirSync, mkdtempSync, rmSync, symlinkSync} from 'node:fs';
import {resolve, dirname} from 'node:path';
const {dispatch, validVersion, collect, propose, deployed, tag, preparedFiles} = createRequire(import.meta.url)('../../.github/scripts/prepare-release.cjs');
const sha = 'a'.repeat(40);
const PREPARED = '.cache/release/prepared.json';
const PREPARED_PATHS = ['content/guide.toml', 'CITATION.cff', 'package.json', 'package-lock.json',
  'pyproject.toml', '.zenodo.json', 'CHANGELOG.md', 'content/provenance.toml', 'content/identifiers.toml'];
const context = {eventName: 'workflow_dispatch', ref: 'refs/heads/main', sha, runId: 12,
  repo: {owner: 'example', repo: 'guide'}, payload: {repository: {default_branch: 'main'}, inputs: {version: '1.2.3-alpha.1', release_status: 'testing'}}};
for (const value of ['1.2.3', '0.0.0', '1.2.3-alpha.1', '1.2.3-rc-2']) assert(validVersion(value));
for (const value of ['v1.2.3', '01.2.3', '1.2.3-alpha.01', '1.2.3-a..b', '1.2.3+build', '$(id)']) assert(!validVersion(value));
assert.throws(() => dispatch({...context, ref: 'refs/heads/feature'}), /default branch/);
assert.throws(() => dispatch({...context, eventName: 'push'}), /dispatch/);
const typed = value => ({...context, payload: {...context.payload, inputs: {...context.payload.inputs, version: value}}});
for (const value of ['v1.2.3-alpha.1', ' 1.2.3-alpha.1\n'])
  assert.deepEqual(dispatch(typed(value)), {base: 'main', version: '1.2.3-alpha.1', branch: 'release/1.2.3-alpha.1'}, value);
for (const value of ['vv1.2.3', '1.2', '', undefined])
  assert.throws(() => dispatch(typed(value)), /1\.0\.0-alpha\.4 or v1\.0\.0-alpha\.4/, String(value));
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
function fixture() {
  const state = {refs: new Map([['heads/main', sha]]), commits: new Map([[sha, {tree: {sha: 'base'}}]]), prs: [],
    creates: [], updates: [], blobs: [], tags: new Map(), failPR: false, reads: [], outputs: {}, associations: [],
    failAssociations: false, prCommits: []};
  const github = {rest: {git: {
    getRef: async ({ref}) => {if (!state.refs.has(ref)) throw Object.assign(Error('missing'), {status: 404}); return {data: {object: {sha: state.refs.get(ref)}}};},
    getCommit: async ({commit_sha}) => ({data: state.commits.get(commit_sha)}),
    createBlob: async args => {state.blobs.push(args); return {data: {sha: hash(args)}};},
    createTree: async args => ({data: {sha: hash(args)}}),
    createCommit: async args => {const id = hash(args); state.commits.set(id, {message: args.message, tree: {sha: args.tree}, parents: args.parents.map(sha => ({sha}))}); return {data: {sha: id}};},
    createTag: async args => {const id = hash(args); state.tags.set(id, args); return {data: {sha: id}};},
    createRef: async ({ref, sha}) => {const key = ref.slice(5); if (state.refs.has(key)) throw Error('already exists'); state.refs.set(key, sha); state.creates.push(ref); return {data: {ref}};},
    updateRef: async ({ref, sha, force}) => {state.updates.push({ref, sha, force}); state.refs.set(ref, sha); return {data: {ref}};},
  }, pulls: {list: 'pulls.list', listCommits: 'pulls.commits', create: async args => {
    if (state.failPR) {state.failPR = false; throw Error('interrupted');}
    const pr = {...args, html_url: 'https://github.com/example/guide/pull/3', state: 'open'}; state.prs.push(pr); return {data: pr};
  }}, repos: {listPullRequestsAssociatedWithCommit: 'commit.pulls', listDeployments: 'deployments',
    listDeploymentStatuses: 'deployment.statuses'},
  actions: {getWorkflowRun: async () => ({data: {created_at: '2026-10-14T10:00:00Z'}}), listWorkflowRuns: 'workflow.runs'}},
  paginate: async (method, args) => {
    state.reads.push(args);
    if (method === 'deployments') return state.deployments || [];
    if (method === 'deployment.statuses') return (state.statuses || {})[args.deployment_id] || [];
    if (method === 'workflow.runs') return (state.runs || {})[args.workflow_id] || [];
    if (method === 'pulls.commits') return state.prCommits;
    if (method === 'commit.pulls') {
      if (state.failAssociations) throw Error('Association page failed');
      return state.associations;
    }
    return state.prs;
  }};
  const core = {info() {}, setOutput: (key, value) => {state.outputs[key] = value;}};
  const manifest = {formatVersion: 1, version: context.payload.inputs.version,
    files: PREPARED_PATHS.map(path => ({path, sha256: createHash('sha256').update(Buffer.from(path)).digest('hex')}))};
  const history = {formatVersion: 1, source: sha, previousTag: 'v1.0.0', commits: [sha], firstParent: [{sha, subject: 'A direct commit'}]};
  const read = (path, encoding) => path === PREPARED ? JSON.stringify(manifest)
    : path === '.cache/release/history.json' ? JSON.stringify(history)
    : path === 'package.json' && encoding ? JSON.stringify({version: context.payload.inputs.version})
    : Buffer.from(path);
  return {state, github, core, read, manifest, history};
}
{
  const {state, github, core, read} = fixture();
  state.prs = Array.from({length: 205}, (_, number) => ({number}));
  state.associations = Array.from({length: 205}, (_, index) => ({number: index + 1}));
  const written = new Map();
  await collect({github, core, context}, (path, bytes) => {written.set(path, JSON.parse(bytes));}, read);
  assert.equal(written.get('.cache/release/prs.json').length, 205);
  assert.equal(written.get('.cache/release/associations.json').associations[sha].length, 205);
  assert.equal(state.reads[0].state, 'closed');
  assert.equal(state.reads[0].base, 'main');
  assert.equal(state.outputs.date, '2026-10-14');
  assert.equal(state.reads[1].commit_sha, sha);
  assert.equal(state.creates.length, 0);
  state.refs.set('tags/v1.2.3-alpha.1', sha);
  await assert.rejects(collect({github, core, context}), /already tagged/);
}
{
  const {state, github, core, read, history} = fixture();
  for (const value of [{...history, source: 'b'.repeat(40)}, {...history, firstParent: [...history.firstParent, ...history.firstParent]},
    {...history, commits: [], firstParent: []}]) {
    await assert.rejects(collect({github, core, context}, () => assert.fail('Must not write partial collection'), () => JSON.stringify(value)), /history|No commits/);
  }
  state.failAssociations = true;
  await assert.rejects(collect({github, core, context}, () => assert.fail('Must not write partial collection'), read), /Association page failed/);
  assert.equal(state.creates.length, 0);
  assert.equal(state.tags.size, 0);
}
{
  const {state, github, core, read, manifest} = fixture();
  state.failPR = true;
  await assert.rejects(propose({github, core, context}, read), /interrupted/);
  assert.equal(state.creates.length, 1);
  await propose({github, core, context}, read);
  assert.equal(state.creates.length, 1, 'retry reuses the exact prepared branch');
  assert.equal(state.prs.length, 1);
  await propose({github, core, context}, read);
  assert.equal(state.prs.length, 1);
  assert.equal(manifest.files.length, PREPARED_PATHS.length);
  assert(!state.creates.some(ref => ref.includes('/tags/')));
  assert.equal(state.outputs.url, 'https://github.com/example/guide/pull/3', 'the proposal address is a step output');
  const branch = state.refs.get('heads/release/1.2.3-alpha.1');
  state.commits.get(branch).tree.sha = 'human edit';
  await assert.rejects(propose({github, core, context}, read), /changes the preparation did not make/);
}
const BOT = 'fair-guide-actions[bot]';
const ours = message => ({author: {login: BOT}, commit: {message}});
const moved = 'c'.repeat(40);
const later = {...context, sha: moved};
function movedOn(state) {
  state.refs.set('heads/main', moved);
  state.commits.set(moved, {tree: {sha: 'later'}});
}
{
  // An outdated proposal that only the automation touched is prepared again from the moved default branch.
  const {state, github, core, read} = fixture();
  await propose({github, core, context}, read, undefined, BOT);
  movedOn(state);
  state.prCommits = [ours('Prepare release 1.2.3-alpha.1\n')];
  await propose({github, core, context: later}, read, undefined, BOT);
  assert.equal(state.prs.length, 1, 'the pull request keeps its number');
  assert.deepEqual(state.updates.map(update => [update.ref, update.force]), [['heads/release/1.2.3-alpha.1', true]]);
  assert.deepEqual(state.commits.get(state.refs.get('heads/release/1.2.3-alpha.1')).parents, [{sha: moved}]);
}
for (const [name, commits, bot] of [
  ['a person committed', [ours('Prepare release 1.2.3-alpha.1'), {author: {login: 'motyc'}, commit: {message: 'Fix'}}], BOT],
  ['another message', [ours('Merge main')], BOT],
  ['no bot identity', [ours('Prepare release 1.2.3-alpha.1')], undefined],
  ['no commits listed', [], BOT],
]) {
  const {state, github, core, read} = fixture();
  await propose({github, core, context}, read, undefined, BOT);
  movedOn(state);
  state.prCommits = commits;
  await assert.rejects(propose({github, core, context: later}, read, undefined, bot), /did not make/, name);
  assert.deepEqual(state.updates, [], `${name}: human changes are never overwritten`);
}
{
  const {state, github, core, read} = fixture();
  state.prs = [{state: 'closed', merged_at: null, html_url: 'https://github.com/example/guide/pull/2'}];
  await assert.rejects(propose({github, core, context}, read, undefined, BOT), /closed without merging/);
  assert.deepEqual([state.creates, state.updates], [[], []]);
}
{
  // Completing a merged release: a new pull request from the release branch, which the merge deleted.
  const {state, github, core, read, manifest} = fixture();
  const completion = (path, encoding) => path === PREPARED ? JSON.stringify({...manifest, mode: 'complete'}) : read(path, encoding);
  state.prs = [{state: 'closed', merged_at: '2026-10-25T02:10:54Z', html_url: 'https://github.com/example/guide/pull/2'}];
  await propose({github, core, context}, completion, undefined, BOT);
  const created = state.prs.at(-1);
  assert.equal(created.title, 'Complete release 1.2.3-alpha.1');
  assert.match(created.body, /^Completes the untagged release/);
  assert.equal(state.commits.get(state.refs.get('heads/release/1.2.3-alpha.1')).message, 'Complete release 1.2.3-alpha.1');
  // A branch the merge left behind is stale and reused for the next completion.
  movedOn(state);
  state.prs = [{state: 'closed', merged_at: '2026-10-25T02:10:54Z', html_url: 'https://github.com/example/guide/pull/2'}];
  await propose({github, core, context: later}, completion, undefined, BOT);
  assert.equal(state.updates.length, 1);
  assert.equal(state.prs.at(-1).title, 'Complete release 1.2.3-alpha.1');
}
{
  const {state, github, core, read, manifest} = fixture();
  const corrupted = {...manifest, files: manifest.files.map((item, index) =>
    index ? item : {...item, sha256: '0'.repeat(64)})};
  const changed = (path, encoding) => path === PREPARED ? JSON.stringify(corrupted) : read(path, encoding);
  await assert.rejects(propose({github, core, context}, changed), /changed after preparation/);
  assert.equal(state.creates.length, 0);
  assert.equal(state.blobs.length, 0);
}
for (const mutate of [
  files => files.slice(1),
  files => [...files, {path: 'SECURITY.md', sha256: '0'.repeat(64)}],
  files => files.map((item, i) => i === files.length - 1 ? {...item, path: '../outside'} : item),
  files => files.map((item, i) => i === files.length - 1 ? {...item, path: '/absolute'} : item),
  files => files.map((item, i) => i === files.length - 1 ? {...item, path: 'C:\\outside'} : item),
  files => files.map((item, i) => i === files.length - 1 ? {...item, path: 'content/../content/identifiers.toml'} : item),
  files => files.map((item, i) => i === files.length - 1 ? {...item, path: 'content\\identifiers.toml'} : item),
]) {
  const {state, github, core, read, manifest} = fixture();
  const malformed = {...manifest, files: mutate(manifest.files)};
  const fileReads = [];
  const changed = (path, encoding) => {
    if (path === PREPARED) return JSON.stringify(malformed);
    fileReads.push(path); return read(path, encoding);
  };
  await assert.rejects(propose({github, core, context}, changed), /Invalid prepared-file manifest/);
  assert.deepEqual(fileReads, [], 'validate every selected path before any prepared file read');
  assert.equal(state.blobs.length, 0, 'invalid selections cause no GitHub writes');
}
{
  mkdirSync('.cache', {recursive: true});
  const temporary = mkdtempSync(resolve('.cache/release-paths-'));
  const root = resolve(temporary, 'repo'), outside = resolve(temporary, 'outside');
  try {
    const {manifest} = fixture();
    for (const name of PREPARED_PATHS) {
      mkdirSync(dirname(resolve(root, name)), {recursive: true});
      copyFileSync(name, resolve(root, name));
    }
    assert.equal(preparedFiles(manifest, context.payload.inputs.version, root).length, PREPARED_PATHS.length);
    rmSync(resolve(root, 'content'), {recursive: true});
    mkdirSync(outside);
    for (const name of PREPARED_PATHS.filter(name => name.startsWith('content/')))
      copyFileSync(name, resolve(outside, name.slice('content/'.length)));
    symlinkSync(outside, resolve(root, 'content'), 'junction');
    assert.throws(() => preparedFiles(manifest, context.payload.inputs.version, root), /escapes or aliases/);
  } finally {
    rmSync(temporary, {recursive: true, force: true});
  }
}
{
  const {state, github, core, read, manifest} = fixture();
  const duplicated = {...manifest, files: [...manifest.files, manifest.files[0]]};
  const duplicate = (path, encoding) => path === PREPARED ? JSON.stringify(duplicated) : read(path, encoding);
  await assert.rejects(propose({github, core, context}, duplicate), /Invalid prepared-file manifest/);
  assert.equal(state.creates.length, 0);
}
{
  const {state, github, core, read, manifest} = fixture();
  const missing = manifest.files[0].path;
  const absent = (path, encoding) => {
    if (path === missing) throw Object.assign(Error(`missing ${path}`), {code: 'ENOENT'});
    return read(path, encoding);
  };
  await assert.rejects(propose({github, core, context}, absent), /ENOENT|missing/);
  assert.equal(state.creates.length, 0);
}
{
  const {state, github, core, read} = fixture();
  assert.deepEqual(state.prs, [], 'Direct metadata commits need no merged release PR');
  await tag({github, core, context}, read);
  assert.deepEqual(state.creates, ['refs/tags/v1.2.3-alpha.1']);
  const annotated = state.tags.get(state.refs.get('tags/v1.2.3-alpha.1'));
  assert.equal(annotated.object, sha);
  assert.equal(annotated.type, 'commit');
  assert.equal(annotated.message, 'Release v1.2.3-alpha.1\n\nFair-Guide-Release-Status: testing\n');
  await assert.rejects(tag({github, core, context}, read), /already exists/);
  const production = {...context, payload: {...context.payload, inputs: {...context.payload.inputs, release_status: 'production'}}};
  await assert.rejects(tag({github, core, context: production}, read), /already exists/);
  assert.equal(state.tags.size, 1, 'retry cannot change the tag decision or create another annotation');
}
{
  const {state, github, core, read} = fixture();
  const wrongVersion = (path, encoding) => path === 'package.json' ? JSON.stringify({version: '9.9.9'}) : read(path, encoding);
  await assert.rejects(tag({github, core, context}, wrongVersion), /another version/);
  assert.equal(state.tags.size, 0);
  const original = github.rest.git.getRef;
  let headReads = 0;
  github.rest.git.getRef = async args => {
    if (args.ref === 'heads/main' && ++headReads === 2) state.refs.set('heads/main', 'b'.repeat(40));
    return original(args);
  };
  await assert.rejects(tag({github, core, context}, read), /moved/);
  assert.equal(state.tags.size, 0, 'final head recheck precedes even the annotation write');
}
{
  const {state, github, core, read} = fixture();
  state.prs = [{merged_at: '2026-10-14', merge_commit_sha: sha, head: {repo: {full_name: 'example/guide'}}}];
  for (const status of [undefined, '', 'released', 'Production', 'production\nextra']) {
    const invalid = {...context, payload: {...context.payload, inputs: {...context.payload.inputs, release_status: status}}};
    await assert.rejects(tag({github, core, context: invalid}, read), /Choose release_status/);
    assert.equal(state.tags.size, 0); assert.equal(state.creates.length, 0);
  }
  const production = {...context, payload: {...context.payload, inputs: {...context.payload.inputs, release_status: 'production'}}};
  await tag({github, core, context: production}, read);
  assert([...state.tags.values()][0].message.endsWith('Fair-Guide-Release-Status: production\n'));
}
{
  const {state, github, core, read} = fixture();
  state.refs.set('heads/main', 'b'.repeat(40));
  await assert.rejects(propose({github, core, context}, read), /moved/);
  await assert.rejects(tag({github, core, context}, read), /moved/);
  assert.deepEqual(state.creates, []);
}
{
  // Tagging needs a successful github-pages deployment of the current commit, as the tag ruleset does; otherwise the
  // refusal names the deployment or publish run to wait for.
  const {state, github, core} = fixture();
  const run = (id, conclusion, extra = {}) => ({id, conclusion, head_sha: sha, head_branch: 'main',
    html_url: `https://github.com/example/guide/actions/runs/${id}`, ...extra});
  state.deployments = [{id: 41, sha}];
  state.statuses = {41: [{state: 'inactive'}, {state: 'success'}, {state: 'in_progress'}]};
  assert.equal(await deployed({github, core, context}), 41, 'a later deployment marking it inactive keeps it deployed');
  const query = state.reads.find(args => args.environment);
  assert.deepEqual([query.environment, query.sha], ['github-pages', sha]);
  state.statuses = {41: [{state: 'failure'}, {state: 'in_progress'}]};
  state.runs = {'deploy.yml': [run(8, 'success')], 'publish.yml': [run(9, null)]};
  await assert.rejects(deployed({github, core, context}), /still being deployed; wait for https:\/\/github\.com\/example\/guide\/actions\/runs\/9 to finish/);
  state.runs = {'deploy.yml': [run(8, 'failure')]};
  await assert.rejects(deployed({github, core, context}), /no successful deployment \(latest run: .*runs\/8\); run Deploy the verified site/);
  state.runs = {};
  state.deployments = [{id: 42, sha: 'b'.repeat(40)}];
  state.statuses = {42: [{state: 'success'}]};
  await assert.rejects(deployed({github, core, context}), /no successful deployment; run Deploy the verified site/,
    'a deployment of another commit does not count');
  state.runs = {'deploy.yml': [run(7, null, {head_branch: 'v1.0.0'})]};
  await assert.rejects(deployed({github, core, context}), /no successful deployment;/, 'a tag run is not the default branch');
  state.refs.set('heads/main', 'b'.repeat(40));
  await assert.rejects(deployed({github, core, context}), /moved/);
  assert.deepEqual(state.creates, [], 'the check never tags');
}
console.log('Release dispatch fixtures: complete collection, exact source, PR recovery, protected edits and separate immutable tag pass.');
