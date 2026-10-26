# Documentation review receipt

Date: 2026-10-25. Starting revision: `3b3267544b40c2c11bfe68600d9ddeb11de5f337`.
The [section map](section-map.md) accounts for 148 former sections. The structure, links, named-file and README
agreement checks pass for 37 current human documents. Agent instructions and delivered surfaces retain their owners.

## Independent audience readers

Three fresh `default` agents were started without the writing conversation. They read only human documentation,
its linked documentation and the section map; moved facts were sampled with `git show` against the starting revision.
They edited no files and performed no operational actions. Each reviewed the corrected documents again.

| Audience | Agent | Final result |
| --- | --- | --- |
| Guide readers | `docs_reader_review` | `NO_FINDINGS` |
| Contributors | `docs_contributor_review` | `NO_FINDINGS` |
| Maintainers | `docs_maintainer_review` | `NO_FINDINGS` |

## Findings and repairs

| Finding | Disposition |
| --- | --- |
| Reader explanation had no inbound route | Both READMEs link the FIP section of `docs/about.md`; repository layout is also reachable |
| Embedding required source inspection to find its configuration | Both Guide-side and host-side markup, `data-parent-origins` syntax, maintainer responsibility and the build route are documented |
| Advisory wording was lost from contributor guidance | The content reference states the named-NRP-only rule and suitable identifier alternatives; the content how-to links and states them |
| Advertised local duplicate repair lacked identity and recovery details | A linked local how-to restores `github`/`commitNames`, `--person`, complete checks, nonzero no-ops and rollback; the PR runbook covers a missing reply after a successful commit |
| Catalogue and deployment reference disagreed about retrying staging | The catalogue's authored TOML now distinguishes dispatching current staging from retrying a failed tag deployment, then was regenerated |
| Recorded acceptance could not meet the review step's completion condition | The runbook names both eligible-review and conditional explicit-acceptance completion, while preserving enforced GitHub requirements |
| Assembly procedure remained in reference | The procedure moved to `docs/how-to/verify-assembly.md`, linked from the deployment reference |
| Historical tag recovery remained in reference without operational steps | A linked runbook gives prerequisites, exact approval, commands, completion evidence and failure handling; the release runbook exposes the route |

No documentation finding is deferred.

The first integrated run additionally caught the standing introductory tooling-link contract and the complete
source-name inventory in both READMEs. Both were restored without weakening those tests; the reader reviewer
rechecked the final landing pages.

## Moved-fact samples

- Readers: life-cycle stages, role lenses and progressive detail; evaluator scope and retained reader answers;
  Dashboard ownership, browser restriction and prefill fallback; protocol fields, validation and size limits.
- Contributors: bilingual values, the five dated statuses, ORCID opt-out and reviewed identity, conditional
  independent review and explicit release acceptance.
- Maintainers: the timing receipt and artifact caveats, release-body byte preservation and refusals, local repair
  identity/no-op/reply recovery, and the review exception's original conditions.

This is local documentation acceptance. It does not establish that the new default-branch workflows have run,
that the digest has been published, that legacy issues have migrated, or that a release rehearsal has occurred.
