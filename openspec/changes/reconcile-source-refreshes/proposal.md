# Reconcile source refreshes and catalogue presentation

## Why

Four pending source refreshes cross the Guide's identity migration: they retain obsolete routes and counter-based
IDs, introduce a registry type whose FIP classification disappears, and exceed the initial-download budget.
The maintainer also selected the related footer and favicon work for the same session, so one plan must cover
the semantic repairs, source observations and reader-visible result before implementation resumes.

## What Changes

- Reconcile the KNAV, FIP Dashboard, Heslář and NKR refreshes against the existing one-thing identity model.
  Preserve source records under their described things, genuine source IDs and exact source passages; replace
  counter allocation with kind-aware identity resolution and reviewable refusal of unresolved collisions.
- Audit the meaning of existing FIP joins and retain precise established source keys. Separate specific licences
  from their family/publisher and repository software from deployed repositories; preserve source claims without
  turning instance-specific verification into software certification. Use the new glossary terms in suitable
  existing bilingual guidance, with an explicit placement or omission decision for each term.
- Preserve the FIP classification when the Dashboard changes a record from `repository` to `registry`.
- Keep both initial languages within 300 KB gzip by deferring NKR/re3data pre-fill and repository keyword detail through
  existing data parts, retaining complete cold search, local files, iframes and Retry behavior.
- Move both complete citations from the footer to About, preserving their source/editor roles and existing credit
  metadata. Keep an accessible footer route to the full credits.
- Extend own-site favicon coverage to standards, guides and documents. Refresh obtainable marks and record dated
  acquisition outcomes in the existing manifest, distinguishing unavailable images from transient failures and
  hosts never attempted. Collect the reconciled things' own sites, including NKR-only repositories, rather than
  their catalogue-record URLs. Preserve existing icons during failed refreshes and retain shared-platform exclusions.
- Validate the complete combined result and prepare separately reviewable updates for the original PRs; remote
  publication, human acceptance, merging and issue closure remain separate actions.
- Include the remaining observations explicitly authorized by the maintainer: reserve inferred organisation
  addresses, require an explicit valid favicon set, constrain temporary filenames, enforce public-only HTTPS
  destinations and redirects, and reject incompatible initial/deferred data revisions with recoverable loading.
  Retain intentional search-focus preloading. Keep source facts, Python 3.11, local-file/iframe operation and the
  300 KB limit; defer assessment-only configuration through existing parts if needed to pay for revision checks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fair-guide/guide-knowledge-base`: address-scoped identity reservations, counter-free source reconciliation and
  preserved classification of registry records.
- `fair-guide/guide-experience`: complete deferred registry data, citations on About and consistent own-site icons
  for eligible resources, including standards, guides and documents.
- `fair-guide/guide-delivery`: dated favicon observations, explicit asset-set integrity, owned working files and
  public-only, address-pinned HTTPS acquisition with safe preservation of verified assets.

## Impact

Implementation targets the identity normalizer and snapshot reconciliation, crate generation, existing deferred
data configuration, footer/About rendering, favicon collection and badge eligibility, source/identity metadata,
native design/content documentation, provenance and regression/browser checks. The favicon manifest gains
acquisition observations; image size, normalization, licensing and the public API and saved-answer formats stay
unchanged. No dependency, backend or external request on page load is introduced.

This change supersedes the unimplemented `defer-nkr-prefill-data` plan and carries all eight of its tasks forward.
It implements the no-counter and registry-record contracts already defined by `unify-identity-model-and-api`;
it does not reopen that change's release, namespace, human-review or archive gates.

Scope references:
[dsw-nrp/eosc-fair-guide#178](https://github.com/dsw-nrp/eosc-fair-guide/pull/178),
[dsw-nrp/eosc-fair-guide#177](https://github.com/dsw-nrp/eosc-fair-guide/pull/177),
[dsw-nrp/eosc-fair-guide#176](https://github.com/dsw-nrp/eosc-fair-guide/pull/176),
[dsw-nrp/eosc-fair-guide#168](https://github.com/dsw-nrp/eosc-fair-guide/pull/168),
[dsw-nrp/eosc-fair-guide#179](https://github.com/dsw-nrp/eosc-fair-guide/issues/179), and
[dsw-nrp/eosc-fair-guide#150](https://github.com/dsw-nrp/eosc-fair-guide/issues/150).

Acceptance requires exact imported-source fidelity, explicit collision and classification regressions, both
citations only on About, observed favicon coverage and honest failure records, the unchanged 307,200-byte bound
in Czech and English, bilingual desktop/phone/print inspection, and the complete repository checks.
