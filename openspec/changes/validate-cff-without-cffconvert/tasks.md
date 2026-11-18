# Tasks

## 1. Vendored schema

- [x] 1.1 Fetch `schema.json` from `citation-file-format/citation-file-format` at tag `1.2.0`, store it unchanged as
  `scripts/schemas/cff-1.2.0.json` and record its SHA-256; verify the digest matches a second fetch and the file
  parses as JSON.
- [x] 1.2 Declare the file in `REUSE.toml` with "The Citation File Format authors" and `CC-BY-4.0`; verify
  `reuse lint` passes.

## 2. Validation without cffconvert

- [x] 2.1 In `scripts/check_citation_metadata.py`, load `CITATION.cff` with a date-preserving `SafeLoader`, refuse a
  `cff-version` other than `1.2.0`, and validate with `Draft7Validator` and `FormatChecker` against the vendored
  schema, reporting `CITATION.cff <path>: <message>`; verify `python scripts/check_citation_metadata.py` passes on
  the current files.
- [x] 2.2 Extend `tests/test_citation_metadata.py`: an invalid `date-released`, a missing required field and
  `cff-version: 1.3.0` each fail with the file and path named; verify the tests fail against a schema stub that
  accepts everything and pass against the vendored schema.
- [x] 2.3 Replace `cffconvert --validate` in `docs/how-to/build-and-check.md` with the check's command; verify
  `python scripts/check_docs.py` passes.

## 3. Dependencies

- [x] 3.1 Remove `cffconvert` from `requirements-dev.txt` and set `jsonschema==4.26.0`; verify a fresh install
  resolves and `python -c "import cffconvert"` fails in it.
- [x] 3.2 Run the citation tests and `python scripts/check_citation_metadata.py` under `jsonschema` 4.26.0; verify
  both pass and the negative cases still fail.

## 4. Integration

- [x] 4.1 Run `npm run openspec:validate` and `python scripts/check_all.py`; verify all checks pass.
- [ ] 4.2 **Hand-off (maintainer):** review the pull request; after merge, close
  [dsw-nrp/eosc-fair-guide#70](https://github.com/dsw-nrp/eosc-fair-guide/pull/70) as superseded, linking the merged
  pull request.

## Workflow follow-up

- Archive the change after the pull request merges and its checks pass on `main`.
