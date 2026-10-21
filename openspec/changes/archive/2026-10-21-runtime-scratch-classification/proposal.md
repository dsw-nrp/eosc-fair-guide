# Proposal

## Why

The delivered tooling now declares `.agents/local_scratch/` as the repository's run-scratch area: transient hand-offs
stay visible in `git status`, a tracked `README.md` describes the layout, and `local_scratch_paths.py` and
`runtime_env.py` implement it. Two guide checks predate that convention. The ownership map classifies only a fixed
list of local runtime files, so anything the area holds is reported as an unclassified managed file. The
public-content hygiene rule refuses the literal path wherever it appears, which includes the delivered library and
skills that document the convention and cannot be edited here. After the default branch was integrated at
`a38f70f`, every pull request fails `agent-ownership`, `sibling-delivery` and `public-content` before its own change
is reviewed, and `agent-generation` reports an inventory that predates the two delivered modules.

## What Changes

- Classify `.agents/local_scratch/**` as runtime in `.agents/guide/surfaces.toml`, so files there are neither
  unowned findings nor targets for native generation.
- Narrow the scratch hygiene rule to machine-specific places: an absolute, drive-qualified or rooted path that names
  the scratch layout is refused, while the repository-relative layout the delivered tooling documents is not.
- Regenerate `docs/agent-tooling.md` from the delivery manifest, which now lists `local_scratch_paths.py` and
  `runtime_env.py`.
- Keep every other hygiene rule, the declared runtime file list and all delivered files unchanged; delivered assets
  stay read-only and are corrected upstream only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-delivery`: the ownership map names the runtime scratch area, and the hygiene check refuses
  machine-specific scratch locations instead of the repository's own relative convention.

## Impact

Implementation affects `.agents/guide/surfaces.toml`, the generated `docs/agent-tooling.md`,
`scripts/check_public_content.py` and `tests/test_check_public_content.py`; `content/provenance.toml` records the
accompanying review action. No delivered file is edited, no page, API, stored-format or runtime dependency changes,
and no commit message or document gains a machine-specific path.

Validate with strict OpenSpec validation, the ownership, sibling-delivery, generation and public-content checks,
including a planted runtime file and a planted absolute path, Ruff, and the full `python scripts/check_all.py`
close-out.
