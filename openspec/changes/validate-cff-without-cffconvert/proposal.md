# Proposal

## Why

The repository checks pin `jsonschema` at 3.2.0 (2019) only because `cffconvert` 2.0.0, its last release
(September 2021), requires `jsonschema<4`. Dependabot's update to 4.26.0
([dsw-nrp/eosc-fair-guide#70](https://github.com/dsw-nrp/eosc-fair-guide/pull/70)) fails with
`ResolutionImpossible`, and `cffconvert`'s main branch has supported `jsonschema>=4.18` since 2024 without a
release. The Guide uses `cffconvert` for one call, `Citation(raw).validate()`, so an unmaintained dependency holds
back the validator the citation check already uses for `.zenodo.json`.

## What Changes

- `scripts/check_citation_metadata.py` validates `CITATION.cff` itself: it reads the YAML without converting dates
  and validates it with `jsonschema` against the CFF 1.2.0 schema, vendored unchanged from
  `citation-file-format/citation-file-format` at tag `1.2.0`.
- The vendored schema is declared in `REUSE.toml` with its holder and CC BY 4.0 licence.
- `cffconvert` leaves `requirements-dev.txt`, and `jsonschema` moves to 4.26.0; PR 70 is then closed as superseded.
- `docs/how-to/build-and-check.md` names `python scripts/check_citation_metadata.py` instead of
  `cffconvert --validate`.
- A `CITATION.cff` that declares a `cff-version` other than 1.2.0 fails with a message naming the supported
  version, rather than being validated against a schema it does not declare.

Exclusions: the `.zenodo.json` import profile and the cross-file consistency rules are unchanged; CFF 1.3.0 and
any network fetch of schemas are out of scope.

Validation: the existing citation tests, a new test that an invalid CFF value and an unsupported `cff-version` fail
with the file and field named, and the full close-out with `jsonschema` 4.26.0 installed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement "Citation checks validate CFF and the effective Zenodo import format" in
`openspec/specs/fair-guide/guide-delivery/spec.md` already requires CFF schema validation without naming a tool;
only its mechanism changes, so the change sets `skip_specs: true`.

## Impact

- Code: `scripts/check_citation_metadata.py` and `tests/test_citation_metadata.py`.
- Files: a new vendored `scripts/schemas/cff-1.2.0.json`; `REUSE.toml`; `requirements-dev.txt`.
- Documentation: `docs/how-to/build-and-check.md`.
- Dependencies: removes `cffconvert` and its transitive `pykwalify` and `ruamel.yaml`; `jsonschema` 4 brings
  `referencing`, `jsonschema-specifications` and `rpds-py`.
- CI: the `citation-metadata` job keeps its name and command; release preparation and tag validation call the
  same check.
