# Tasks

## 1. Runtime scratch classification

- [x] 1.1 Add `.agents/local_scratch/**` to the runtime list in `.agents/guide/surfaces.toml` and regenerate `docs/agent-tooling.md`; verify the generator's `--check` mode, `check_agent_surfaces.py` and `check_sibling_delivery.py` pass with the tracked scratch README and a planted untracked hand-off.
- [x] 1.2 Verify native generation still refuses a declared output under a runtime path, so the new classification protects the area rather than only silencing a finding.

## 2. Hygiene rule boundary

- [x] 2.1 Narrow the scratch rule in `scripts/check_public_content.py` to absolute drive-qualified and rooted paths and extend `tests/test_check_public_content.py`; verify the delivered relative references pass, an absolute drive path and a rooted path fail, and the redacted finding keeps the `file:line: rule` form.
- [x] 2.2 Run the check on the repository and confirm no finding remains from the delivered library or skills while the workstation and private-reference rules still fire.

## 3. Review action and close-out

- [x] 3.1 Extend the pull request's provenance action in `content/provenance.toml` with the re-verified `datarepo` link, the merged default-branch integration and this session's instruments, and confirm the content check accepts the merged base.
- [x] 3.2 Run strict OpenSpec validation, Ruff, the focused suites and the full `python scripts/check_all.py` close-out; record the outcome in the rolling usage entry and leave the change unarchived for maintainer review.
