# Design

## Runtime classification

`surfaces.toml` already separates managed areas from declared runtime files. The scratch area is the first runtime
path that is a whole directory and that holds files a person may read and act on, rather than a local settings file.
Classifying `.agents/local_scratch/**` as runtime states that ownership by a delivery bundle is not claimed for it:
native generation may not write there, and the ownership and delivery-integrity checks do not treat its files as
unclassified or as delivered content. A tracked README describing the area is therefore allowed while remaining a
runtime file, and an untracked hand-off is equally acceptable.

The alternative — removing the tracked README or adding it to the delivery manifest — was rejected. The directory is
deliberately not gitignored so hand-offs stay visible; the README documents that decision, and the manifest records
what upstream delivers, which does not include it.

## Hygiene rule

The requirement forbids local machine paths, user-specific setup and private planning references. A
repository-relative runtime path is none of those: the delivered tooling uses it as the shared convention, and the
delivered skills must name it to be usable. The rule is therefore narrowed to an absolute form — a drive-qualified or
rooted path that reaches the scratch layout — which is what a maintainer's own checkout would contain. The existing
workstation rule is unchanged, so a Windows user directory is still refused even without a scratch component.

A repository-relative reference now passes everywhere, including future hand-offs. The check still scans delivered
files, so an absolute path or a hub-internal name in delivered tooling is reported rather than excused; only the
over-broad literal match is removed.

## Failure handling and evidence

The rule keeps producing redacted findings (`file:line: rule`), so a failure names the place without quoting the
path. Tests plant a relative layout, an absolute drive path and a rooted path to prove the boundary in both
directions. The ownership change is proven with a planted runtime file under the scratch area and with the two
existing ownership checks, and the regenerated inventory is verified by the generator's `--check` mode.
