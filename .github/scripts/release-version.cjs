// One release/prerelease predicate and one precedence for dispatch, artifact binding and image promotion.
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
/** Numeric core and SemVer prerelease precedence of two release tags, independent of API tag-list ordering. */
function compareTags(a, b) {
  const parts = (tag) => { const [core, ...rest] = tag.slice(1).split("-"); return [core.split(".").map(BigInt), rest.join("-")]; };
  const [ac, ap] = parts(a), [bc, bp] = parts(b);
  for (let i = 0; i < 3; i++) if (ac[i] !== bc[i]) return ac[i] < bc[i] ? -1 : 1;
  if (!ap || !bp) return ap === bp ? 0 : ap ? -1 : 1;
  const ax = ap.split("."), bx = bp.split(".");
  for (let i = 0; i < Math.max(ax.length, bx.length); i++) {
    if (ax[i] === bx[i]) continue;
    if (ax[i] === undefined || bx[i] === undefined) return ax[i] === undefined ? -1 : 1;
    const an = /^\d+$/.test(ax[i]), bn = /^\d+$/.test(bx[i]);
    if (an && bn) return BigInt(ax[i]) < BigInt(bx[i]) ? -1 : 1;
    if (an !== bn) return an ? -1 : 1;
    return ax[i] < bx[i] ? -1 : 1;
  }
  return 0;
}
module.exports = { validVersion, releaseInput, compareTags, ACCEPTED_FORM };
