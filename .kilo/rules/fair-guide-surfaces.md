<!-- Generated from .agents/guide/rules/fair-guide-surfaces.md; run scripts/generate_agent_surfaces.py. -->

# FAIR guide agent surfaces

`AGENTS.md` is the runtime entry. The authored rules and routing skill live under `.agents/guide/`;
`surfaces.toml` owns their output paths and the ownership map. Read `docs/agent-tooling.md` for tool selection,
vendor loading, compatibility and checks.

## Plan before implementing

The `fair-guide-editor` skill MUST delegate every behaviour, data/API contract, stored-format, CI or governance
change to the OpenSpec lifecycle through the delivered `aiscr-planning-core` and `openspec-*` surfaces before
implementation. Read the relevant `openspec/specs/` contracts, complete proposal/design/specs/tasks and obtain
the required approval. Resume native execution only through the approved apply phase. Never implement first
and maintain specs later. The delivered planning rule owns mode-transfer gates. A typo, formatting correction,
behaviour-neutral dependency update or routine source refresh may use ordinary checks while preserving the
existing contract; a semantic change is not wording.

Adding advice, a question or a resource under existing fields and assessment semantics is content work, with
sources, paradata and ordinary checks. Adding a field, changing what an answer means, or changing a connector's
behaviour changes the contract and needs OpenSpec planning and approval.

## Ownership and regeneration

Delivered membership comes from `.agents/delivery-manifest.json`, including the generated sections of `CODEX.md`.
Delivered rules, skills, agents, dispatch, commands, scripts and templates are read-only. Propose corrections
upstream. An `aiscr-*` name alone does not establish membership. Native surfaces may refer to delivered tools;
delivered tools do not acquire dependencies on native rules or scripts.

Edit native sources under `.agents/guide/`, then run `python scripts/generate_agent_surfaces.py`. Never edit their
vendor mirrors or the generated inventory by hand. The generator replaces only the `guide:native` region of
`CODEX.md`; delivered sections and its preamble remain byte-identical. OpenSpec owns its generated wrappers.
`python scripts/check_agent_surfaces.py` reports any managed file that has no declared owner, and
`python scripts/check_sibling_delivery.py` verifies the receipt without rewriting delivered content. The
repository's runtime scratch area is a declared runtime path: hand-offs there are neither owned nor delivered, and
native generation never writes into it.

## Build, review and release

Install `requirements-dev.txt`, run `npm ci` and `npm run browsers`, then use `python scripts/check_all.py` for
close-out. A selected `--only` subset is partial; live checks additionally need `--live` and network access.
Build with `python scripts/build_site.py` and inspect the changed view in both languages, at phone width and in
print. `CONTRIBUTING.md` owns branch, pull-request and human review procedures; `docs/deployment.md` owns release
preparation, tagging, immutable artifact identity and recovery. Release preparation opens a PR by default and
collects merged PRs and direct default-branch commits since the previous reachable release tag without duplication.
Keep CFF and Zenodo metadata consistent and validated; both release routes require the same checks. READMEs carry
a Zenodo concept DOI badge.

Scheduled source refreshes propose validated snapshots as pull requests; health watch reports issues. Neither
merges or writes the default branch. Connectors and their origins are reviewed in `content/live.toml`, which
generates the Content Security Policy. Follow the content rule for identifiers, sources, evidence and paradata.

## Human documentation and change notes

Guide readers start at the bilingual READMEs, contributors at `CONTRIBUTING.md`, and maintainers at `docs/ci.md`.
Keep each human document to one type, declared on its first line as `<!-- type: TYPE -->`: landing, how-to,
reference, explanation or tutorial. A landing page routes tasks; reference records contracts and explanation
gives reasons. Procedures have one home in a how-to and are linked from reference and explanation.

Recurring maintainer tasks have a runbook under `docs/runbooks/`. One-time issue migrations and other
change-specific procedures stay with their OpenSpec change, retaining complete evidence and approval gates; a
hand-off still needs an independently reviewed procedure. A runbook opens with who acts, how long and why in at
most two sentences; numbered steps give **Where**, **Do**, **Done when** and **If it fails**.
Keep each step within 130 words and all steps within 1300 words; link the reference for detail. A branching flow
uses Mermaid with `accTitle`, `accDescr` and equivalent adjacent prose.

Run `python scripts/check_docs.py` for declarations, runbook structure, links, named files, npm scripts and README
agreement. Moved text also needs a section map kept with the OpenSpec change and checked with `--map <path>`:
every former section names its audience, type and new home or removal reason. Have a fresh independent agent per
affected audience read only the documents and their links, check whether the steps can be followed and sample
moved facts against the map. Fix its findings before the dependent hand-off is complete. Exclude `AGENTS.md` and
delivered or generated surfaces from this reshape; their owners still govern them.

Commit messages preserve the change and reason for release notes. `[Unreleased]` in `CHANGELOG.md` needs one line
only for a breaking change, a required step or a security fix; other changes use the generated release lineage.
The release runbook owns publication steps; `docs/changelog.md` owns the changelog policy.

## Usage and review facts

The guide owns its rolling usage entry under `.agents/reports/usage/`. The delivered `aiscr-usage-logging`
rule owns notability, entry lifecycle and exact field labels; `aiscr-model-logging` owns runtime/backend
metadata. Read those delivered rules in your client or their sections in `CODEX.md` and use their field
labels verbatim. Keep content paradata in its own content-owned source. Never include secrets or private paths.

`.agents/config/review_config.toml` is guide-owned. Its `review_facts` describe this static application:
no database; a deployment pipeline, public API and first-party frontend are present. Read those facts before
reviewing. The delivered tooling does not replace them or make the unavailable sibling mode available.
