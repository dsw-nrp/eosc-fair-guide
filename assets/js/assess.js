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
  function activeContext(value, inherited) {
    let result = inherited || { vocab: null, terms: {}, unknown: false };
    for (const context of list(value)) {
      if (context === null) result = { vocab: null, terms: {}, unknown: false };
      else if (typeof context === "string") {
        if (/^https?:\/\/schema\.org\/?$/.test(context)) result = Object.assign({}, result, { vocab: SCHEMA });
        else if (codeMetaContexts.includes(context)) result = Object.assign({}, result, { vocab: SCHEMA, terms: Object.assign({}, result.terms,
          Object.fromEntries(["developmentStatus", "issueTracker", "softwareRequirements"].map((name) => [name, name === "softwareRequirements" ? SCHEMA + name : CODEMETA + name]))) });
        else result = { vocab: null, terms: {}, unknown: true };
      } else if (context && typeof context === "object") {
        result = { vocab: Object.hasOwn(context, "@vocab") ? context["@vocab"] : result.vocab, terms: Object.assign({}, result.terms, context), unknown: result.unknown };
      }
    }
    return result;
  }
  function property(data, name, namespace = SCHEMA, parent) {
    const context = Object.hasOwn(data, "@context") ? data["@context"] === null ? activeContext([null]) : activeContext(data["@context"], parent) : parent || activeContext([]);
    const expand = (key, seen = new Set()) => {
      if (seen.has(key)) return null;
      seen.add(key);
      if (/^https?:\/\//.test(key)) return key.replace(/^http:\/\/schema\.org\//, SCHEMA);
      if (Object.hasOwn(context.terms, key)) {
        const term = context.terms[key];
        if (term === null || (term && typeof term === "object" && (Object.hasOwn(term, "@context") || term["@reverse"]))) return null;
        const mapped = typeof term === "string" ? term : term && term["@id"];
        return mapped ? expand(mapped, seen) : null;
      }
      const parts = key.split(":");
      if (parts.length === 2 && Object.hasOwn(context.terms, parts[0])) {
        const prefix = context.terms[parts[0]];
        const uri = typeof prefix === "string" ? prefix : prefix && prefix["@id"];
        return uri && /^https?:\/\//.test(uri) ? (uri + parts[1]).replace(/^http:\/\/schema\.org\//, SCHEMA) : null;
      }
      return !context.unknown && context.vocab ? String(context.vocab).replace(/^http:\/\/schema\.org\//, SCHEMA) + key : null;
    };
    const found = Object.keys(data).find((key) => expand(key) === namespace + name && present(data[key]));
    return found ? data[found] : undefined;
  }
  const schemaProperty = (data, name, parent) => property(data, name, SCHEMA, parent);
  const schemaType = (data, name) => {
    const context = activeContext(Object.hasOwn(data, "@context") && data["@context"] === null ? [null] : data["@context"]);
    return list(data["@type"]).some((type) => typeof type === "string" &&
      (type.replace(/^http:\/\/schema\.org\//, SCHEMA) === SCHEMA + name ||
        (!context.unknown && context.vocab === SCHEMA && type === name && !Object.hasOwn(context.terms, name))));
  };
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
