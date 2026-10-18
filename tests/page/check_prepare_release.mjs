// No GitHub mutations: exact-source, delivery and recovery fixtures.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const {dispatch, validVersion, collect, propose, tag} = createRequire(import.meta.url)('../../.github/scripts/prepare-release.cjs');
const sha = 'a'.repeat(40);
const PREPARED = '.cache/release/prepared.json';
const PREPARED_PATHS = ['content/guide.toml', 'CITATION.cff', 'package.json', 'package-lock.json',
  'pyproject.toml', 'CHANGELOG.md', 'content/provenance.toml', 'content/identifiers.toml'];
const context = {eventName: 'workflow_dispatch', ref: 'refs/heads/main', sha, runId: 12,
  repo: {owner: 'example', repo: 'guide'}, payload: {repository: {default_branch: 'main'}, inputs: {version: '1.2.3-alpha.1', release_status: 'testing'}}};
for (const value of ['1.2.3', '0.0.0', '1.2.3-alpha.1', '1.2.3-rc-2']) assert(validVersion(value));
for (const value of ['v1.2.3', '01.2.3', '1.2.3-alpha.01', '1.2.3-a..b', '1.2.3+build', '$(id)']) assert(!validVersion(value));
assert.throws(() => dispatch({...context, ref: 'refs/heads/feature'}), /default branch/);
assert.throws(() => dispatch({...context, eventName: 'push'}), /dispatch/);
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
function fixture() {
  const state = {refs: new Map([['heads/main', sha]]), commits: new Map([[sha, {tree: {sha: 'base'}}]]), prs: [],
    creates: [], tags: new Map(), failPR: false, reads: [], outputs: {}};
  const github = {rest: {git: {
    getRef: async ({ref}) => {if (!state.refs.has(ref)) throw Object.assign(Error('missing'), {status: 404}); return {data: {object: {sha: state.refs.get(ref)}}};},
    getCommit: async ({commit_sha}) => ({data: state.commits.get(commit_sha)}),
    createBlob: async args => ({data: {sha: hash(args)}}),
    createTree: async args => ({data: {sha: hash(args)}}),
    createCommit: async args => {const id = hash(args); state.commits.set(id, {message: args.message, tree: {sha: args.tree}, parents: args.parents.map(sha => ({sha}))}); return {data: {sha: id}};},
    createTag: async args => {const id = hash(args); state.tags.set(id, args); return {data: {sha: id}};},
    createRef: async ({ref, sha}) => {const key = ref.slice(5); if (state.refs.has(key)) throw Error('already exists'); state.refs.set(key, sha); state.creates.push(ref); return {data: {ref}};},
  }, pulls: {list: 'pulls.list', create: async args => {
    if (state.failPR) {state.failPR = false; throw Error('interrupted');}
    const pr = {...args, html_url: 'https://github.com/example/guide/pull/3', state: 'open'}; state.prs.push(pr); return {data: pr};
  }}, actions: {getWorkflowRun: async () => ({data: {created_at: '2026-10-14T10:00:00Z'}})}},
  paginate: async (_method, args) => {state.reads.push(args); return state.prs;}};
  const core = {info() {}, setOutput: (key, value) => {state.outputs[key] = value;}};
  const manifest = {formatVersion: 1, version: context.payload.inputs.version,
    files: PREPARED_PATHS.map(path => ({path, sha256: createHash('sha256').update(Buffer.from(path)).digest('hex')}))};
  const read = (path, encoding) => path === PREPARED ? JSON.stringify(manifest)
    : path === 'package.json' && encoding ? JSON.stringify({version: context.payload.inputs.version})
    : Buffer.from(path);
  return {state, github, core, read, manifest};
}
{
  const {state, github, core} = fixture();
  state.prs = Array.from({length: 205}, (_, number) => ({number}));
  let written;
  await collect({github, core, context}, (_path, bytes) => {written = JSON.parse(bytes);});
  assert.equal(written.length, 205);
  assert.equal(state.reads[0].state, 'closed');
  assert.equal(state.reads[0].base, 'main');
  assert.equal(state.outputs.date, '2026-10-14');
  state.refs.set('tags/v1.2.3-alpha.1', sha);
  await assert.rejects(collect({github, core, context}), /already tagged/);
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
  assert.equal(manifest.files.length, 8);
  assert(!state.creates.some(ref => ref.includes('/tags/')));
  const branch = state.refs.get('heads/release/1.2.3-alpha.1');
  state.commits.get(branch).tree.sha = 'human edit';
  await assert.rejects(propose({github, core, context}, read), /different content/);
}
{
  const {state, github, core, read, manifest} = fixture();
  const corrupted = {...manifest, files: manifest.files.map((item, index) =>
    index ? item : {...item, sha256: '0'.repeat(64)})};
  const changed = (path, encoding) => path === PREPARED ? JSON.stringify(corrupted) : read(path, encoding);
  await assert.rejects(propose({github, core, context}, changed), /changed after preparation/);
  assert.equal(state.creates.length, 0);
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
  await assert.rejects(tag({github, core, context}, read), /merged this release/);
  state.prs = [{merged_at: '2026-10-14', merge_commit_sha: sha, head: {repo: {full_name: 'example/guide'}}}];
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
console.log('Release dispatch fixtures: complete collection, exact source, PR recovery, protected edits and separate immutable tag pass.');
