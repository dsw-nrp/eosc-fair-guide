// The one place the page and API tests name the Guide's records, as tests/addresses.py does
// for the Python tests. A record is named by its address, `<kind>/<id>` or `<kind>/<scope>/<id>`, and a part of it by
// the address and a fragment (`advice/plan.05#step-1`). The crate publishes each at its IRI under the namespace; the
// page's data names it by the address itself. Tests name records only through these helpers, never by the build's
// internal keys.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// The Guide's namespace, as content/guide.toml declares it; the built page carries the one it was built with.
export const GUIDE_NAMESPACE = "https://w3id.org/eosc-cz/fair-guide/";

/** The namespace a built site was published with, from its page configuration. */
export function siteNamespace(site) {
  const ui = readFileSync(resolve(site, "assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m);
  return (ui && JSON.parse(ui[1]).config.namespace) || GUIDE_NAMESPACE;
}

/** The published IRI of a record, or of a part of one. */
export const iri = (address, namespace = GUIDE_NAMESPACE) => namespace + "id/" + address;

/** The address a published IRI names, or the address itself when the page's data names it so; null otherwise. */
export function addressOf(id, namespace = GUIDE_NAMESPACE) {
  const value = String(id && typeof id === "object" ? id["@id"] : id || "");
  const base = namespace + "id/";
  if (value.startsWith(base)) return value.slice(base.length);
  return /^[a-z][a-z-]*\/[^#]/.test(value) && !value.startsWith("assets/") ? value : null;
}

/** The kind an IRI or address names (`resources`), or null. */
export const kindOf = (id, namespace = GUIDE_NAMESPACE) => (addressOf(id, namespace) || "").split("/")[0] || null;

/** Whether an entity, IRI or address is a record of a kind itself rather than a part of one. */
export function isRecord(value, kind, namespace = GUIDE_NAMESPACE) {
  const address = addressOf(value, namespace);
  return Boolean(address) && !address.includes("#") && address.split("/")[0] === kind;
}

/** A record's ID within its kind: the address without its kind (`rdmkit/plan` for a scoped stage). */
export const localId = (address) => String(address).split("#")[0].split("/").slice(1).join("/");

/** A vocabulary term's address. */
export const term = (set, code) => `vocabularies/${set}/${code}`;

/** The API file of a record. */
export const apiFile = (address) => `api/v1/${address}.json`;

/** The page route of a record's catalogue entry. */
export const route = (address, lang = "cs", lens = "V") => `#/${lang}/${lens}/catalogue/${address}`;

/** The crate's entities by IRI, with a lookup by address. */
export function crateIndex(graph, namespace = GUIDE_NAMESPACE) {
  const byId = new Map(graph.map((entity) => [entity["@id"], entity]));
  return { byId, get: (address) => byId.get(iri(address, namespace)) || byId.get(address) };
}
