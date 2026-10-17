// One inventory of every printed check, mode and scope, shared with the CI collector.
export function printMatrix(graph) {
  const nodes = new Map(graph.map((entity) => [entity['@id'], entity]));
  const basic = ['cs', 'en'].flatMap((lang) => graph.filter((entity) => entity['@type'] === 'Quiz').flatMap((check) => {
    const modes = [].concat(nodes.get('#modes-' + check.identifier)?.hasDefinedTerm || []).map((ref) => nodes.get(ref['@id']).termCode);
    return (modes.length ? modes : [null]).flatMap((mode) => [false, true].map((extended) => ({
      lang, check: check.identifier, mode, extended,
      key: `${lang}/${check.identifier}/${mode || 'default'}/${extended ? 'extended' : 'basic'}`,
    })));
  }));
  const paths = basic.filter((item) => item.extended && ['dataset', 'fip', 'gate', 'maturity'].includes(item.check) &&
    (item.check !== 'dataset' || item.mode === 'after')).map((item) => ({ ...item, grouping: 'steps', key: item.key + '/steps' }));
  return basic.concat(paths);
}
