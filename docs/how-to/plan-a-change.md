<!-- type: how-to -->
# Plan a change with OpenSpec

A change of behaviour, of a data or API contract, of a stored format, of CI or of a governance rule is planned
before it is built. Typos, wording, formatting, behaviour-neutral dependency updates and routine source refreshes
need no plan; a change of meaning is never only wording.

New advice, a question or a resource using existing fields and assessment meaning is ordinary
[content work](edit-content.md). A new field or changed assessment meaning changes the contract and needs this plan.

1. **Read the contracts.** The current requirements are in `openspec/specs/`; find the capability your change
   touches.
2. **Create the change.** Use the repository's pinned command-line tool:

   ```bash
   npm ci
   npm run openspec:cli -- list --json
   npm run openspec:cli -- new change <slug>
   npm run openspec:cli -- instructions proposal --change <slug>
   ```

3. **Write the artifacts.** Complete the proposal, design, specs and tasks under `openspec/changes/<slug>/`, as the
   instructions for each say, then run `npm run openspec:validate`.
4. **Get approval.** Open a pull request with the change and wait for a maintainer's explicit approval before
   implementing it.
5. **Implement and archive.** Work through the tasks, then archive the change once it is delivered, again with
   approval.

With an AI assistant, the same steps run through the OpenSpec skills; the [agent tooling guide](../agent-tooling.md)
names them.
