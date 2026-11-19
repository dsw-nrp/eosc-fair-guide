# Design

## Context

See proposal.md, Why. `check()` in `scripts/check_citation_metadata.py` calls `Citation(raw).validate()` and then
loads the same text with `yaml.safe_load` for its own consistency checks. `cffconvert` 2.0.0 selects the schema for
the file's `cff-version` from the copies it bundles and validates with `jsonschema` Draft 7. The Guide's
`CITATION.cff` declares `cff-version: 1.2.0`, and its dates are quoted strings. The check runs offline, in the
close-out, in release preparation and in tag validation.

## Goals / Non-Goals

**Goals:**

- Keep CFF schema validation offline, deterministic and as strict as it is now, with the failing path named.
- Remove the only dependency that pins `jsonschema` below 4.

**Non-Goals:**

- Supporting CFF versions the Guide does not declare.
- Converting CFF to other formats, which the Guide does not use `cffconvert` for.

## Decisions

**Vendor the upstream schema, not `cffconvert`'s copy.** The file is `schema.json` from
`citation-file-format/citation-file-format` at tag `1.2.0`, stored unchanged as `scripts/schemas/cff-1.2.0.json`
with its source, tag and digest recorded in a header comment of the check and in `REUSE.toml` (CC BY 4.0, "The
Citation File Format authors"). The tag is the published specification; `cffconvert`'s bundled copy is an
implementation detail of an unmaintained package. Alternative considered: installing `cffconvert` from its main
branch, rejected as an unreleased alpha from a git reference.

**Validate with the existing validator class.** `Draft7Validator` with `FormatChecker`, as the check already uses
for `.zenodo.json`; the schema declares draft-07. A probe on 18 November 2026 with `jsonschema` 3.2.0 found no
errors for the current file and rejected a non-ISO `date-released`. Errors are reported as
`CITATION.cff <path>: <message>`, one per error, which names the field where `cffconvert` reported one exception.

**Read YAML without timestamp conversion.** A `SafeLoader` subclass without the timestamp resolver keeps unquoted
dates as strings, so the schema's `date` format sees what the file says. The same loaded mapping feeds the later
consistency checks, which already compare strings.

**Refuse other CFF versions.** A file whose `cff-version` is not `1.2.0` fails with the supported version named.
Adopting a newer CFF version is a deliberate change that vendors its schema.

## Risks / Trade-offs

- [Format checking differs between `jsonschema` 3 and 4] → the tests run the current file and the negative cases
  under 4.26.0 before the pin moves.
- [`rpds-py` needs a binary wheel for the runner's Python] → CI uses Python 3.12; the close-out runs on the local
  interpreter too, and a missing wheel stops the apply phase before merge.
- [The vendored schema drifts from upstream fixes] → the 1.2.0 tag is fixed; later fixes arrive with a deliberate
  CFF version change.

## Migration Plan

One pull request replaces the call, vendors the schema, updates the pins and the how-to, and closes
[dsw-nrp/eosc-fair-guide#70](https://github.com/dsw-nrp/eosc-fair-guide/pull/70) as superseded. Rollback is a revert
of that pull request, which restores `cffconvert` and the 3.2.0 pin together.
