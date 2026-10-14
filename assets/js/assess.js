/* Conservative mappings of observed facts to guide questions. Deferred; no network or code execution. */
(function () {
  "use strict";
  const FG = window.FairGuide;
  const SC = FG.selfcheck;
  const list = FG.list;
  const present = (value) => value !== undefined && value !== null && value !== "" && (!Array.isArray(value) || value.length > 0);
  const text = (value) => typeof value === "string" ? value : value && typeof value === "object" ? value.name || value["@id"] || value.url || value.value || JSON.stringify(value) : String(value);
  const url = (value, base) => {
    if (!present(value) || typeof value === "object" && !value["@id"] && !value.url) return null;
    try { const parsed = new URL(typeof value === "object" ? value["@id"] || value.url : text(value), base); return /^https?:$/.test(parsed.protocol) && !parsed.username && !parsed.password ? parsed.href : null; } catch (error) { return null; }
  };
  const isoDate = (value) => typeof value === "string" && /^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))?$/.test(value) && Number.isFinite(Date.parse(value));
  const field = (path, value) => ({ path, values: list(value).filter(present).map(text) });
  const SCHEMA = FG.config.discovery.schemaVocabulary;
  const CODEMETA = FG.config.discovery.codeMetaVocabulary;
  const codeMetaContexts = FG.config.discovery.codeMetaContexts;
  /* One bounded reading of compact JSON-LD, shared by object discovery (identity) and every local assessment
     (object and software metadata). Only Schema.org and the published CodeMeta context are known; a remote context
     is never fetched, so an unknown one leaves its compact terms unmapped. Long context lists and term chains are cut
     off rather than followed, and keys that would reach a prototype are ignored. */
  const MAX_CONTEXTS = 16;
  const MAX_CHAIN = 8;
  const UNKNOWN = Object.freeze({ vocab: null, terms: Object.freeze(Object.create(null)), unknown: true });
  const emptyContext = () => ({ vocab: null, terms: Object.create(null), unknown: false });
  const withTerms = (result, entries) => {
    const terms = Object.assign(Object.create(null), result.terms);
    for (const [key, value] of entries) if (!FG.unsafeKey(key)) terms[key] = value;
    return terms;
  };
  const schemaIri = (iri) => String(iri).replace(/^http:\/\/schema\.org\//, SCHEMA);
  function activeContext(value, inherited) {
    const contexts = list(value);
    if (contexts.length > MAX_CONTEXTS) return UNKNOWN;
    let result = inherited || emptyContext();
    for (const context of contexts) {
      if (context === null) result = emptyContext();
      else if (typeof context === "string") {
        if (/^https?:\/\/schema\.org\/?$/.test(context)) result = Object.assign({}, result, { vocab: SCHEMA });
        else if (codeMetaContexts.includes(context)) result = Object.assign({}, result, { vocab: SCHEMA, terms: withTerms(result,
          ["developmentStatus", "issueTracker", "softwareRequirements"].map((name) => [name, name === "softwareRequirements" ? SCHEMA + name : CODEMETA + name])) });
        else result = UNKNOWN;
      } else if (context && typeof context === "object" && !Array.isArray(context)) {
        result = { vocab: Object.hasOwn(context, "@vocab") ? context["@vocab"] : result.vocab, terms: withTerms(result, Object.entries(context)), unknown: result.unknown };
      }
    }
    return result;
  }
  const contextOf = (data, parent) => Object.hasOwn(data, "@context") ?
    data["@context"] === null ? activeContext([null]) : activeContext(data["@context"], parent) : parent || emptyContext();
  /** The absolute IRI a key of a node means under its active context, or null when it cannot be known. */
  function expandKey(context, key, depth = 0) {
    if (depth > MAX_CHAIN) return null;
    if (/^https?:\/\//.test(key)) return schemaIri(key);
    if (Object.hasOwn(context.terms, key)) {
      const term = context.terms[key];
      if (term === null || (term && typeof term === "object" && (Object.hasOwn(term, "@context") || term["@reverse"]))) return null;
      const mapped = typeof term === "string" ? term : term && term["@id"];
      return typeof mapped === "string" && mapped !== key ? expandKey(context, mapped, depth + 1) : null;
    }
    const parts = key.split(":");
    if (parts.length === 2 && Object.hasOwn(context.terms, parts[0])) {
      const prefix = context.terms[parts[0]];
      const uri = typeof prefix === "string" ? prefix : prefix && prefix["@id"];
      return uri && /^https?:\/\//.test(uri) ? schemaIri(uri + parts[1]) : null;
    }
    return !context.unknown && context.vocab ? schemaIri(context.vocab) + key : null;
  }
  const keysFor = (data, name, namespace, parent) => {
    const context = contextOf(data, parent);
    return Object.keys(data).filter((key) => !FG.unsafeKey(key) && expandKey(context, key) === namespace + name);
  };
  /** The first present value of a property, as an assessment reads it. */
  function property(data, name, namespace = SCHEMA, parent) {
    const found = keysFor(data, name, namespace, parent).find((key) => present(data[key]));
    return found ? data[found] : undefined;
  }
  /** Every value stated for a property under any key that means it, as identity matching reads it. */
  const propertyValues = (data, name, namespace = SCHEMA, parent) => keysFor(data, name, namespace, parent).flatMap((key) => list(data[key]));
  const schemaProperty = (data, name, parent) => property(data, name, SCHEMA, parent);
  const schemaType = (data, name) => {
    const context = contextOf(data);
    return list(data["@type"]).some((type) => typeof type === "string" &&
      (schemaIri(type) === SCHEMA + name ||
        (!context.unknown && context.vocab === SCHEMA && type === name && !Object.hasOwn(context.terms, name))));
  };
  FG.jsonLd = { activeContext, expandKey, property, propertyValues, schemaType };
  const profileOf = (representation) => list(representation.profiles).concat(list(representation.data[FG.config.discovery.conformsTo])).filter((value) => url(value));

  SC.assessmentHelpers = { list, present, text, url, isoDate, field, SCHEMA, CODEMETA, activeContext, property, schemaProperty, schemaType, profileOf };
  SC.localTests = {};
  SC.registerLocalTests = function (questions) {
    for (const question of questions) {
      const id = "guide-" + question.replace(".", "-");
      SC.localTests[id] = function (observations) {
        return observations.filter((entry) => entry.id === question).map((entry) => Object.assign({}, entry, { testId: id }));
      };
    }
  };
  SC.runLocalTests = function (check, observations) {
    return Object.entries(SC.localTests).filter(([id]) => id.startsWith("guide-" + check.identifier + "-"))
      .flatMap(([, evaluate]) => evaluate(observations));
  };
})();
