// One release/prerelease predicate for dispatch, artifact binding and image promotion.
const VERSION = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;
function validVersion(value) {
  if (typeof value !== "string") return false;
  const match = VERSION.exec(value);
  return Boolean(match && match[0] === value && !(match[4] || "").split(".").some((part) => /^0\d+$/.test(part)));
}
module.exports = { validVersion };
