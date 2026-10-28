<!-- type: landing -->
# Contributing

Help improve the FAIR Data Guide through a focused pull request into `main`. Choose the task below; each guide
gives its prerequisites and checks. People review the advice and tone; automation checks consistency and delivery.

| I want to… | Start here |
| --- | --- |
| Change advice, a question, a source or a resource | [Edit content](docs/how-to/edit-content.md) |
| Set up a checkout, preview the site or run checks | [Build and check](docs/how-to/build-and-check.md) |
| Change behaviour, a format, CI or governance | [Plan a change](docs/how-to/plan-a-change.md) before implementation |
| Repair a duplicate locally or on a pull request | [Fix a duplicate](docs/runbooks/fix-a-duplicate.md) |
| Understand review, credit, branch names or commit messages | [Contribution reference](docs/contribution-reference.md) |
| Use an AI assistant | [Agent tooling](docs/agent-tooling.md); the assistant starts at [AGENTS.md](AGENTS.md) |
| Merge, release or maintain the repository | [Maintainer tasks](docs/ci.md) |

New advice, questions and resources using existing fields are content work. Changed assessment meaning, new fields
or changed runtime behaviour need an approved OpenSpec change. The [content model](docs/content-model.md) defines
the existing contract; [design](docs/design.md) explains its reasons.

Commit messages preserve the change and its reason for release notes; mention AI assistance when used. Only a
breaking change, a required step or a security fix also needs a line under `[Unreleased]` in
`CHANGELOG.md` ([policy](docs/changelog.md)).

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md). Report security concerns through
[SECURITY.md](SECURITY.md).
