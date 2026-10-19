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

## Ownership and regeneration

Delivered membership comes from `.agents/delivery-manifest.json`, including the generated sections of `CODEX.md`.
Delivered rules, skills, agents, dispatch, commands, scripts and templates are read-only. Propose corrections
upstream. An `aiscr-*` name alone does not establish membership. Native surfaces may refer to delivered tools;
delivered tools do not acquire dependencies on native rules or scripts.

Edit native sources under `.agents/guide/`, then run `python scripts/generate_agent_surfaces.py`. Never edit their
vendor mirrors or the generated inventory by hand. The generator replaces only the `guide:native` region of
`CODEX.md`; delivered sections and its preamble remain byte-identical. OpenSpec owns its generated wrappers.
`python scripts/check_agent_surfaces.py` reports any managed file that has no declared owner, and
`python scripts/check_sibling_delivery.py` verifies the receipt without rewriting delivered content.

## Build, review and release

Install `requirements-dev.txt`, run `npm ci` and `npm run browsers`, then use `python scripts/check_all.py` for
close-out. A selected `--only` subset is partial; live checks additionally need `--live` and network access.
Build with `python scripts/build_site.py` and inspect the changed view in both languages, at phone width and in
print. `CONTRIBUTING.md` owns branch, pull-request and human review procedures; `docs/deployment.md` owns release
preparation, tagging, immutable artifact identity and recovery. Release preparation opens a PR by default and
collects merged PRs and direct default-branch commits since the previous reachable release tag without duplication.
Keep CFF and Zenodo metadata consistent and validated; both release routes require the same checks. Publication
remains separately authorized. Add the real concept-DOI badge to both READMEs only after successful Zenodo archiving.

Scheduled source refreshes propose validated snapshots as pull requests; health watch reports issues. Neither
merges or writes the default branch. Connectors and their origins are reviewed in `content/live.toml`, which
generates the Content Security Policy. Follow the content rule for identifiers, sources, evidence and paradata.

## Usage and review facts

The guide owns its rolling usage entry under `.agents/reports/usage/`. The delivered `aiscr-usage-logging`
rule owns notability, entry lifecycle and exact field labels; `aiscr-model-logging` owns runtime/backend
metadata. Read those delivered rules in your client or their sections in `CODEX.md` and use their field
labels verbatim. Keep content paradata in its own content-owned source. Never include secrets or private paths.

`.agents/config/review_config.toml` is guide-owned. Its `review_facts` describe this static application:
no database; a deployment pipeline, public API and first-party frontend are present. Read those facts before
reviewing. The delivered tooling does not replace them or make the unavailable sibling mode available.
