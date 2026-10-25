// One release/prerelease predicate for dispatch, artifact binding and image promotion.
const VERSION = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;
function validVersion(value) {
  if (typeof value !== "string") return false;
  const match = VERSION.exec(value);
  return Boolean(match && match[0] === value && !(match[4] || "").split(".").some((part) => /^0\d+$/.test(part)));
}
const ACCEPTED_FORM = "a SemVer release or prerelease such as 1.0.0-alpha.4 or v1.0.0-alpha.4";
// A maintainer's dispatch input: surrounding whitespace and one leading v are dropped, then the strict predicate
// decides. Returns the bare version, or null. Tags, artifacts and images keep the strict predicate alone.
function releaseInput(value) {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  const bare = trimmed.startsWith("v") ? trimmed.slice(1) : trimmed;
  return validVersion(bare) ? bare : null;
}
module.exports = { validVersion, releaseInput, ACCEPTED_FORM };
