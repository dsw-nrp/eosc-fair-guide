# Agent tooling

Start here when choosing an AI-assisted workflow for the Guide. The task table below gives the appropriate
entry and its prerequisites; the vendor table explains how to invoke it in your client.

[AGENTS.md](../AGENTS.md) is the runtime entry. `CLAUDE.md`, the Copilot entry and `CODEX.md` point to it.
The authored rules and routing skill are under `.agents/guide/`; `surfaces.toml` owns their mirrors and the
protection map. The generated inventory below describes the current receipt, including command, dispatch and
script paths. Tool-generated OpenSpec wrappers are separate from that delivered set.

## Planning and execution

The native `fair-guide-editor` skill MUST delegate every behaviour, data/API contract, stored-format, CI or
governance change to the OpenSpec lifecycle through delivered `aiscr-planning-core` and `openspec-*` surfaces
**before implementation**. Read relevant installed specs, complete proposal/design/specs/tasks and obtain
the required approval. Return to native content, build and release execution through approved apply only.
Never implement first and maintain specs later. Routine wording/formatting corrections, behaviour-neutral
dependency updates and source refreshes may use ordinary checks while preserving the existing contract.

Install pinned Node dependencies with `npm ci` before `npm run openspec:cli -- <command>`; validate with
`npm run openspec:validate`. The delivered planning rule owns lifecycle and approval semantics. Native
content constraints live in `.agents/guide/rules/fair-guide-content.md`; execution, usage logging and ownership
live in `.agents/guide/rules/fair-guide-surfaces.md`. Release procedures remain in
[CONTRIBUTING.md](../CONTRIBUTING.md) and [deployment.md](deployment.md).

## Task to tool

| Task | Entry | Preconditions and limits |
| --- | --- | --- |
| Any Guide edit | `fair-guide-editor` | Read AGENTS and both native rules; classify before editing |
| Propose or implement changed behaviour/contracts/CI/governance | `openspec-*` lifecycle | Installed pinned CLI, planning artifacts and approval before apply; fresh archive approval |
| Shape a GitHub issue | `aiscr-plan-issue` | Read the workflow; authenticated GitHub access for authorized writes |
| Plan from a shaped issue | `aiscr-plan-from-issue` | Ready issue; planning stops at its implementation boundary |
| Review a PR or local Git scope | `aiscr-review-pr` | Git baseline and guide review facts; authenticated GitHub for remote scope; posting requires approval |
| Draft release notes | `aiscr-write-release-notes` | Reviewed release scope and GitHub lineage; Python with PyYAML; prepare the release configuration and reports before validation; publication is opt-in |
| Draft, investigate or verify within a workflow | Enrolled `aiscr-*` agents and dispatch | Follow the calling workflow's delegation stance; the drafter is `aiscr-draft` |
| Validate the Guide | `python scripts/check_all.py` | Python dev requirements, pinned Node dependencies and Chromium; `--live` additionally needs network |

## Compatibility decisions

The delivered rule `aiscr-quality-first-execution` maps close-out to `python scripts/check_all.py` here.
Its `--only` mode is partial and does not establish complete close-out. Planning baseline discovery maps to
`git status --short`, `git symbolic-ref --short HEAD` and `git log`/`git diff` against the reviewed base; a
detached HEAD must be handled explicitly. The hub-specific `--sibling` mode is unavailable in this repository.

Use this Guide's browser/API checks for local acceptance; they do not imply hosted acceptance or a translation-review
workflow. The current bundle retains the issue-planning, plan-from-issue, PR-review and release-notes workflows and their shared dependencies.
Read `.agents/config/review_config.toml` before review: no database; deployment pipeline, public API and
first-party frontend are present. The usage and review configuration paths are guide-owned.

## Vendor invocation and loading

Native mirrors are generated from the same authored rules. Their existence does not prove a client has loaded
them; check the client's active context and enabled instruction/skill support. Manual reading through AGENTS
is the fallback for every client. No personal or machine-local configuration is provisioned by this generator.

| Client | Entry and rules | Skills, workflows and agents |
| --- | --- | --- |
| Codex | Read `AGENTS.md` and explicitly read mixed `CODEX.md`; do not assume CODEX is automatically loaded | Invoke installed skills by name (for example `$fair-guide-editor`); `.agents/skills/` and `.codex/agents/` require the client's corresponding support |
| Claude Code | `CLAUDE.md` points to AGENTS; project rules are `.claude/rules/` | `/fair-guide-editor` and the enrolled skills use `.claude/skills/`; subagents use `.claude/agents/` |
| Cursor | Read AGENTS; `.cursor/rules/*.mdc` native rules declare `alwaysApply: true` | Read `.agents/skills/<name>/SKILL.md` when no matching discovery is available; use registered agent definitions only when supported |
| Kilo | Read AGENTS and `.kilo/rules/` | Read the selected `.agents/skills/` workflow; `.kilo/agents/` definitions require compatible client support |
| Gemini CLI | Read AGENTS and explicitly include `.gemini/context/` rules, unless context configuration already loads them | Enrolled commands live in `.gemini/commands/`; OpenSpec uses `opsx`; read the native skill directly |
| GitHub Copilot | `.github/copilot-instructions.md` points to AGENTS; delivered and native rules use `.github/instructions/` | Enrolled workflows use the shared `.agents/skills/` tree; discovery depends on client support, so read the selected skill when needed. `.github/prompts/opsx-*` and `.github/agents/openspec.agent.md` are tool-generated OpenSpec surfaces; no enrolled `aiscr-*` prompts or agents are delivered there |

GitHub workflows that use local scripts require their documented interpreter and `gh` authentication where
applicable. A command or agent being installed does not authorize remote writes, staging, commits, merges,
publication or changes to permissions. Workflow approval gates and repository contribution rules still apply.

The bundled release-notes validator is `.agents/scripts/validate_release_yml.py`. It checks the prepared
`.github/release.yml` and report files; absent inputs are reported as failures. The Guide's committed config
can be checked with `python .agents/scripts/validate_release_yml.py --root . --skip-reports`.
For report-only validation, select the recommended config using
`--release-config .agents/reports/release-notes/eosc-fair-guide_release.yml`.
Prepare the reports and recommended copy first, then run that option with `--root .` and without
`--skip-reports`; a config-only pass does not establish report validity.

## Ownership, integrity and regeneration

`.agents/delivery-manifest.json` defines delivered membership by exact path and SHA-256, plus individual
`CODEX.md` sections. Prefixes and brand names do not establish ownership. Delivered rules, skills, agents,
dispatch, commands, scripts and templates are read-only; propose changes upstream. Native sources may refer
to them in one direction. Add local behaviour under `.agents/guide/` and generate the mirrors.

The ownership map distinguishes owned, generated, delivered, tool-generated and mixed files. Runtime caches
and documented local settings have a separate classification. Every file within the managed roots must have
an owner. OpenSpec wrappers are maintained by the pinned OpenSpec tool; unrelated files cannot hide behind
the `aiscr-*` prefix. The receipt is an integrity baseline, not a cryptographic signature or an authorization
to replace it. Review a new receipt as part of an explicitly approved delivery.

```bash
python scripts/generate_agent_surfaces.py
python scripts/generate_agent_surfaces.py --check
python scripts/check_agent_surfaces.py
python scripts/check_sibling_delivery.py
python scripts/check_all.py
```

Generation writes the native rule mirrors and identical skill copies, replaces only `guide:native` in
`CODEX.md`, and refreshes this inventory. It preserves every delivered section and the entry preamble verbatim.
Redelivery preserves the complete native region. The integrity check detects missing/modified delivered files
and sections, extra sections, unmarked mixed-reader text and unclassified managed files; it ignores declared
owned, generated, runtime and tool-generated content. The three tooling checks run in `check_all` and its CI
partition. A check failure is reported, never automatically repaired by the checker.

The guide owns `.agents/reports/usage/`; the delivered `aiscr-usage-logging` and `aiscr-model-logging` rules
own notability and exact fields. Follow those owners through the native surfaces rule. A content change also
records its own content paradata.

## Generated inventory

<!-- begin:guide:inventory -->

| Ownership | Asset | Paths |
| --- | --- | --- |
| Delivered | `aiscr-analyse-correctness` | `.claude/agents/aiscr-analyse-correctness.md`, `.codex/agents/aiscr-analyse-correctness.toml`, `.cursor/agents/aiscr-analyse-correctness.md`, `.gemini/agents/aiscr-analyse-correctness.md`, `.kilo/agents/aiscr-analyse-correctness.md` |
| Delivered | `aiscr-analyse-dead-code` | `.claude/agents/aiscr-analyse-dead-code.md`, `.codex/agents/aiscr-analyse-dead-code.toml`, `.cursor/agents/aiscr-analyse-dead-code.md`, `.gemini/agents/aiscr-analyse-dead-code.md`, `.kilo/agents/aiscr-analyse-dead-code.md` |
| Delivered | `aiscr-analyse-deploy-safety` | `.claude/agents/aiscr-analyse-deploy-safety.md`, `.codex/agents/aiscr-analyse-deploy-safety.toml`, `.cursor/agents/aiscr-analyse-deploy-safety.md`, `.gemini/agents/aiscr-analyse-deploy-safety.md`, `.kilo/agents/aiscr-analyse-deploy-safety.md` |
| Delivered | `aiscr-analyse-duplication` | `.claude/agents/aiscr-analyse-duplication.md`, `.codex/agents/aiscr-analyse-duplication.toml`, `.cursor/agents/aiscr-analyse-duplication.md`, `.gemini/agents/aiscr-analyse-duplication.md`, `.kilo/agents/aiscr-analyse-duplication.md` |
| Delivered | `aiscr-analyse-integration` | `.claude/agents/aiscr-analyse-integration.md`, `.codex/agents/aiscr-analyse-integration.toml`, `.cursor/agents/aiscr-analyse-integration.md`, `.gemini/agents/aiscr-analyse-integration.md`, `.kilo/agents/aiscr-analyse-integration.md` |
| Delivered | `aiscr-analyse-performance` | `.claude/agents/aiscr-analyse-performance.md`, `.codex/agents/aiscr-analyse-performance.toml`, `.cursor/agents/aiscr-analyse-performance.md`, `.gemini/agents/aiscr-analyse-performance.md`, `.kilo/agents/aiscr-analyse-performance.md` |
| Delivered | `aiscr-analyse-security` | `.claude/agents/aiscr-analyse-security.md`, `.codex/agents/aiscr-analyse-security.toml`, `.cursor/agents/aiscr-analyse-security.md`, `.gemini/agents/aiscr-analyse-security.md`, `.kilo/agents/aiscr-analyse-security.md` |
| Delivered | `aiscr-dispatch-library` | `.agents/skills/_dispatch/common.md`, `.agents/skills/_dispatch/contract-drafting.md`, `.agents/skills/_dispatch/contract-findings.md`, `.agents/skills/_dispatch/contract-investigation.md`, `.agents/skills/_dispatch/contract-survey.md`, `.agents/skills/_dispatch/contract-verification.md`, `.agents/skills/_dispatch/lens-correctness.md`, `.agents/skills/_dispatch/lens-dead-code.md`, `.agents/skills/_dispatch/lens-deploy-safety.md`, `.agents/skills/_dispatch/lens-draft.md`, `.agents/skills/_dispatch/lens-duplication.md`, `.agents/skills/_dispatch/lens-integration.md`, `.agents/skills/_dispatch/lens-investigate.md`, `.agents/skills/_dispatch/lens-language.md`, `.agents/skills/_dispatch/lens-performance.md`, `.agents/skills/_dispatch/lens-security.md`, `.agents/skills/_dispatch/lens-survey.md`, `.agents/skills/_dispatch/lens-verify.md` |
| Delivered | `aiscr-draft` | `.claude/agents/aiscr-draft.md`, `.codex/agents/aiscr-draft.toml`, `.cursor/agents/aiscr-draft.md`, `.gemini/agents/aiscr-draft.md`, `.kilo/agents/aiscr-draft.md` |
| Delivered | `aiscr-investigate` | `.claude/agents/aiscr-investigate.md`, `.codex/agents/aiscr-investigate.toml`, `.cursor/agents/aiscr-investigate.md`, `.gemini/agents/aiscr-investigate.md`, `.kilo/agents/aiscr-investigate.md` |
| Delivered | `aiscr-plan-from-issue` | `.agents/scripts/github/github_issues.py`, `.agents/scripts/github/github_utils.py`, `.agents/scripts/lib/local_scratch_paths.py`, `.agents/scripts/lib/log_utils.py`, `.agents/scripts/lib/proc_utils.py`, `.agents/scripts/lib/runtime_env.py`, `.agents/skills/aiscr-plan-from-issue/SKILL.md`, `.claude/skills/aiscr-plan-from-issue/SKILL.md`, `.gemini/commands/aiscr/aiscr-plan-from-issue.toml` |
| Delivered | `aiscr-plan-issue` | `.agents/skills/aiscr-plan-issue/SKILL.md`, `.claude/skills/aiscr-plan-issue/SKILL.md`, `.gemini/commands/aiscr/aiscr-plan-issue.toml` |
| Delivered | `aiscr-review-pr` | `.agents/scripts/github/github_pr_review.py`, `.agents/skills/aiscr-review-pr/SKILL.md`, `.agents/skills/aiscr-review-pr/review-formats.md`, `.agents/skills/aiscr-review-pr/review-tracks.md`, `.claude/skills/aiscr-review-pr/SKILL.md`, `.claude/skills/aiscr-review-pr/review-formats.md`, `.claude/skills/aiscr-review-pr/review-tracks.md`, `.gemini/commands/aiscr/aiscr-review-pr.toml` |
| Delivered | `aiscr-survey` | `.claude/agents/aiscr-survey.md`, `.codex/agents/aiscr-survey.toml`, `.cursor/agents/aiscr-survey.md`, `.gemini/agents/aiscr-survey.md`, `.kilo/agents/aiscr-survey.md` |
| Delivered | `aiscr-verify` | `.claude/agents/aiscr-verify.md`, `.codex/agents/aiscr-verify.toml`, `.cursor/agents/aiscr-verify.md`, `.gemini/agents/aiscr-verify.md`, `.kilo/agents/aiscr-verify.md` |
| Delivered | `aiscr-write-release-notes` | `.agents/scripts/validate_release_yml.py`, `.agents/skills/aiscr-write-release-notes/SKILL.md`, `.claude/skills/aiscr-write-release-notes/SKILL.md`, `.gemini/commands/aiscr/aiscr-write-release-notes.toml` |
| Delivered | `step-sibling-rules` | `.claude/rules/aiscr-delivered-assets.md`, `.claude/rules/aiscr-model-logging.md`, `.claude/rules/aiscr-openspec-posture.md`, `.claude/rules/aiscr-planning-core.md`, `.claude/rules/aiscr-quality-first-execution.md`, `.claude/rules/aiscr-review-conduct.md`, `.claude/rules/aiscr-usage-logging.md`, `.cursor/rules/aiscr-delivered-assets.mdc`, `.cursor/rules/aiscr-model-logging.mdc`, `.cursor/rules/aiscr-openspec-posture.mdc`, `.cursor/rules/aiscr-planning-core.mdc`, `.cursor/rules/aiscr-quality-first-execution.mdc`, `.cursor/rules/aiscr-review-conduct.mdc`, `.cursor/rules/aiscr-usage-logging.mdc`, `.gemini/context/aiscr-delivered-assets.md`, `.gemini/context/aiscr-model-logging.md`, `.gemini/context/aiscr-openspec-posture.md`, `.gemini/context/aiscr-planning-core.md`, `.gemini/context/aiscr-quality-first-execution.md`, `.gemini/context/aiscr-review-conduct.md`, `.gemini/context/aiscr-usage-logging.md`, `.github/instructions/aiscr-delivered-assets.instructions.md`, `.github/instructions/aiscr-model-logging.instructions.md`, `.github/instructions/aiscr-openspec-posture.instructions.md`, `.github/instructions/aiscr-planning-core.instructions.md`, `.github/instructions/aiscr-quality-first-execution.instructions.md`, `.github/instructions/aiscr-review-conduct.instructions.md`, `.github/instructions/aiscr-usage-logging.instructions.md`, `.kilo/rules/aiscr-delivered-assets.md`, `.kilo/rules/aiscr-model-logging.md`, `.kilo/rules/aiscr-openspec-posture.md`, `.kilo/rules/aiscr-planning-core.md`, `.kilo/rules/aiscr-quality-first-execution.md`, `.kilo/rules/aiscr-review-conduct.md`, `.kilo/rules/aiscr-usage-logging.md` |
| Delivered section | `step-sibling-rules` | `CODEX.md:aiscr-delivered-assets`, `CODEX.md:aiscr-entry`, `CODEX.md:aiscr-model-logging`, `CODEX.md:aiscr-openspec-posture`, `CODEX.md:aiscr-planning-core`, `CODEX.md:aiscr-quality-first-execution`, `CODEX.md:aiscr-review-conduct`, `CODEX.md:aiscr-usage-logging` |
| Native generated | `fair-guide-content` | `.claude/rules/fair-guide-content.md`, `.cursor/rules/fair-guide-content.mdc`, `.gemini/context/fair-guide-content.md`, `.github/instructions/fair-guide-content.instructions.md`, `.kilo/rules/fair-guide-content.md` |
| Native generated | `fair-guide-editor` | `.agents/skills/fair-guide-editor/SKILL.md`, `.claude/skills/fair-guide-editor/SKILL.md` |
| Native generated | `fair-guide-surfaces` | `.claude/rules/fair-guide-surfaces.md`, `.cursor/rules/fair-guide-surfaces.mdc`, `.gemini/context/fair-guide-surfaces.md`, `.github/instructions/fair-guide-surfaces.instructions.md`, `.kilo/rules/fair-guide-surfaces.md` |

Templates are listed only when present in the delivery receipt.

<!-- end:guide:inventory -->
