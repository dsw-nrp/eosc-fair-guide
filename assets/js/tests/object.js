/* Local advisory test definitions. Inputs are already retrieved; these functions make no requests. */
(function () {
  "use strict";
  const FG = window.FairGuide;
  const SC = FG.selfcheck;
  const { list, present, text, url, isoDate, field, SCHEMA, CODEMETA, activeContext, property, schemaProperty, schemaType, profileOf } = SC.assessmentHelpers;
  /** One representation stays one observation: fragments from different subjects or sources never complete
      a compound criterion together. An omitted field means unobserved, never a negative answer. */
  SC.objectObservations = function (check, result, sample) {
    const observations = [];
    const target = result.pid ? FG.live.pidUrl(result.pid) : result.input;
    const resolved = result.resolved && result.resolved.found;
    const emit = (number, value, representation, fields, notes) => {
      const id = check.identifier + "." + String(number).padStart(2, "0");
      observations.push({ id, source: representation.source || "landing", date: result.date.slice(0, 10), record: representation.url || representation.record,
        subject: target, representation: representation.url, coverage: sample ? "sample" : "representation", value: sample && value === "yes" ? "partly" : value,
        fields: fields.filter((entry) => entry.values.length), notes: (notes || []).concat(sample ? [{ key: "selfcheck.note.sampleCoverage" }] : []) });
    };
    const resolver = { source: "resolver", url: result.resolved && result.resolved.url || target };
    if (resolved) {
      if (check.identifier === "dataset" && result.pid) { emit(1, "yes", resolver, [field("identifier", target)]); emit(2, "yes", resolver, [field("landingPage", result.resolved.url)]); }
      if (check.identifier === "fdo" && result.pid) emit(1, "partly", resolver, [field("identifier", target)], [{ key: "selfcheck.note.partialCoverage" }]);
      if (check.identifier === "fdo" && result.pid && list(result.resolved.values).length) emit(2, "partly", { source: "pid-record", url: target },
        [field("PID.record", result.resolved.values)], [{ key: "selfcheck.note.pidProfile" }]);
      if (check.identifier === "maturity") emit(2, "partly", resolver, [field("landingPage", result.resolved.url)], [{ key: "selfcheck.note.partialCoverage" }]);
    }
    for (const representation of result.representations || []) {
      if (representation.identity !== "matched") continue;
      const data = representation.data || {};
      if (representation.format === "text/html") continue;
      const registry = representation.source === "datacite";
      const get = (name) => schemaProperty(data, name);
      const title = registry ? list(data.titles).map((entry) => entry.title).filter(Boolean) : get("name");
      const description = registry ? list(data.descriptions).map((entry) => entry.description).filter(Boolean) : get("description");
      const licences = registry ? list(data.rightsList).map((entry) => entry.rightsUri).filter(Boolean) : list(get("license")).map((value) => url(value, representation.url)).filter(Boolean);
      const keywords = registry ? list(data.subjects).map((entry) => entry.subject).filter(Boolean) : get("keywords");
      const distributions = get("distribution");
      const parent = activeContext(data["@context"] === null ? [null] : data["@context"]);
      const access = list(distributions).flatMap((entry) => entry && typeof entry === "object" ? [schemaProperty(entry, "contentUrl", parent), schemaProperty(entry, "url", parent)].flatMap(list).map((value) => url(value, representation.url)).filter(Boolean) : []);
      const creators = registry ? data.creators : get("creator") || get("author");
      const published = registry ? list(data.dates).filter((entry) => entry.dateType === "Issued").map((entry) => entry.date) : get("datePublished");
      const modified = registry ? list(data.dates).filter((entry) => entry.dateType === "Updated").map((entry) => entry.date) : get("dateModified");
      const profiles = profileOf(representation);
      const identifier = registry ? data.doi : get("identifier") || data["@id"];
      if (check.identifier === "cdif") {
        if (present(identifier) && resolved) emit(1, "yes", representation, [field("identifier", identifier)]);
        if (present(title)) emit(2, "partly", representation, [field("name", title)], [{ key: "selfcheck.note.titleMeaning" }]);
        if (access.length) emit(3, "yes", representation, [field("distribution.contentUrl", access)]);
        if (licences.length) emit(4, "partly", representation, [field("license", licences)], [{ key: "selfcheck.note.rightsCoverage" }]);
        if (profiles.length) emit(5, "yes", representation, [field("profile", profiles)], [{ key: "selfcheck.note.profileDeclaration" }]);
        const type = registry ? data.types : data["@type"];
        if (present(type)) emit(6, "partly", representation, [field("type", type)], [{ key: "selfcheck.note.classificationScheme" }]);
        if (present(get("variableMeasured"))) emit(7, "partly", representation, [field("variableMeasured", get("variableMeasured"))]);
        if (present(get("temporalCoverage"))) emit(8, "partly", representation, [field("temporalCoverage", get("temporalCoverage"))]);
        if (present(get("spatialCoverage"))) emit(9, "partly", representation, [field("spatialCoverage", get("spatialCoverage"))]);
        if (present(description)) emit(10, "partly", representation, [field("description", description)], [{ key: "selfcheck.note.descriptionCoverage" }]);
        if (present(creators)) emit(11, "partly", representation, [field("creators", creators)], [{ key: "selfcheck.note.creatorIdentifiers" }]);
        if (list(modified).some(isoDate)) emit(12, "yes", representation, [field("dateModified", list(modified).filter(isoDate))]);
        if (present(get("contactPoint"))) emit(13, "partly", representation, [field("contactPoint", get("contactPoint"))]);
        const funding = registry ? data.fundingReferences : get("funding");
        if (present(funding)) emit(15, "partly", representation, [field("funding", funding)]);
        if (present(keywords)) emit(16, "partly", representation, [field("keywords", keywords)], [{ key: "selfcheck.note.keywordScheme" }]);
        if (list(published).some(isoDate)) emit(18, "yes", representation, [field("datePublished", list(published).filter(isoDate))]);
        const contributors = registry ? data.contributors : get("contributor");
        if (present(contributors)) emit(19, "partly", representation, [field("contributors", contributors)]);
        if (registry && present(data.relatedIdentifiers)) emit(20, "partly", representation, [field("relatedIdentifiers", data.relatedIdentifiers)]);
        const version = registry ? data.version : get("version");
        if (present(version)) emit(21, "partly", representation, [field("version", version)]);
        if (registry && isoDate(data.updated)) emit(24, "yes", representation, [field("metadata.dateModified", data.updated)]);
        // Profiles, FDO types, preservation, authenticity and permissions require their own evidence.
      }
      if (check.identifier === "fdo") {
        if (representation.source === "pid-record") emit(2, "partly", representation, [field("PID.record", representation.data)], [{ key: "selfcheck.note.pidProfile" }]);
        if (profiles.length && representation.source === "pid-record") emit(4, "partly", representation, [field("profile", profiles)], [{ key: "selfcheck.note.profileDeclaration" }]);
      }
      if (check.identifier === "dataset") {
        if (access.length) emit(3, "yes", representation, [field("distribution.contentUrl", access)]);
        if (licences.length) emit(4, "yes", representation, [field("license", licences)]);
        if (present(title) || present(description) || present(keywords)) emit(6, "partly", representation, [field("name", title), field("description", description), field("keywords", keywords)], [{ key: "selfcheck.note.keywordScheme" }]);
      }
      if (check.identifier === "maturity") {
        if (!registry && present(identifier)) emit(3, "partly", representation, [field("identifier", identifier), field("distribution.contentUrl", access)]);
        if (licences.length) emit(6, "partly", representation, [field("license", licences)], [{ key: "selfcheck.note.rightsCoverage" }]);
        if (!registry && /(?:ld\+json|rdf)/.test(representation.format)) emit(12, "partly", representation, [field("metadata.format", representation.format)]);
      }
    }
    return observations;
  };

  SC.registerLocalTests(["dataset.01", "dataset.02", "dataset.03", "dataset.04", "dataset.06", "maturity.02", "maturity.03", "maturity.06", "maturity.12", "cdif.01", "cdif.02", "cdif.03", "cdif.04", "cdif.05", "cdif.06", "cdif.07", "cdif.08", "cdif.09", "cdif.10", "cdif.11", "cdif.12", "cdif.13", "cdif.15", "cdif.16", "cdif.18", "cdif.19", "cdif.20", "cdif.21", "cdif.24", "fdo.01", "fdo.02", "fdo.04"]);
  SC.assessObject = function (check, result, sample) { return SC.runLocalTests(check, SC.objectObservations(check, result, sample)); };
})();
