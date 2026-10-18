/* Local advisory test definitions. Inputs are already retrieved; these functions make no requests. */
(function () {
  "use strict";
  const FG = window.FairGuide;
  const SC = FG.selfcheck;
  const { list, present, text, url, isoDate, field, SCHEMA, CODEMETA, activeContext, property, schemaProperty, schemaType, profileOf } = SC.assessmentHelpers;
  SC.softwareObservations = function (check, repository) {
    if (!repository.supported || !/^[a-f0-9]{40,64}$/i.test(repository.commit || "")) return [];
    const observations = [];
    const metadata = repository.metadata || {};
    const base = { source: repository.provider, date: repository.date.slice(0, 10), record: repository.url, subject: repository.url,
      commit: repository.commit, coverage: `${repository.coverage.readFiles}/${repository.coverage.selectedFiles}`,
      notes: [{ key: "selfcheck.note.repositoryScope" }] };
    const emit = (number, value, path, fields, extra) => observations.push(Object.assign({}, base, { id: `software.${String(number).padStart(2, "0")}`, value,
      representation: path, fields }, extra || {}));
    emit(3, "partly", "commit", [field("commit", repository.commit)], { notes: base.notes.concat([{ key: "selfcheck.note.commitVersion" }]) });
    if (metadata.visibility === "public") emit(9, "yes", "repository", [field("repository", repository.url), field("visibility", "public")]);
    if (metadata.name || metadata.description) emit(4, "partly", "repository", [field("name", metadata.name), field("description", metadata.description)]);
    if (metadata.license) emit(16, "partly", "repository", [field("license", metadata.license)], { notes: base.notes.concat([{ key: "selfcheck.note.copyrightCoverage" }]) });
    for (const file of repository.files || []) {
      if (file.truncated || !file.text) continue;
      const details = [field("file", file.path)];
      const extra = { record: file.url || repository.url };
      if (file.kind === "licence") emit(15, "partly", file.path, details.concat(field("licence", file.text)), Object.assign({}, extra, { notes: base.notes.concat([{ key: "selfcheck.note.bundledLicences" }]) }));
      if (file.kind === "test-definition" && /(?:\b(?:assert\w*|describe|it|test)\s*\(|\bdef\s+test_\w+|\bfunc\s+Test\w+|@Test\b|#\[test\])/.test(file.text.replace(/\/\*[\s\S]*?\*\/|^\s*(?:\/\/|#(?!\[)).*$/gm, "")))
        emit(14, "partly", file.path, details, Object.assign({}, extra, { notes: base.notes.concat([{ key: "selfcheck.note.testsNotRun" }]) }));
      if (file.kind === "software-metadata" && /(?:^|\/)codemeta\.json$/i.test(file.path)) {
        let data;
        try { data = JSON.parse(file.text); } catch (error) { continue; }
        const nodes = list(data && (data["@graph"] || data));
        for (const node of nodes) {
          if (!node || typeof node !== "object") continue;
          const merged = Object.assign({ "@context": data["@context"] }, node);
          const get = (name) => schemaProperty(merged, name);
          // CodeMeta's published context extends Schema.org. Read only its known properties; no remote context fetch.
          const prop = (name) => get(name) || property(merged, name, CODEMETA);
          const location = prop("codeRepository");
          if (!schemaType(merged, "SoftwareSourceCode") || !url(location) || url(location).replace(/\.git\/?$/, "").replace(/\/$/, "") !== repository.url.replace(/\/$/, "")) continue;
          if (list(prop("identifier")).some((value) => url(value))) emit(7, "partly", file.path, details.concat(field("identifier", prop("identifier"))), extra);
          if (present(prop("name")) || present(prop("description"))) emit(4, "partly", file.path, details.concat(field("name", prop("name")), field("description", prop("description"))), extra);
          if (present(prop("developmentStatus")) || present(prop("issueTracker"))) emit(5, "partly", file.path, details.concat(field("developmentStatus", prop("developmentStatus")), field("issueTracker", prop("issueTracker"))), extra);
          if (present(prop("author")) || present(prop("contributor"))) emit(6, "partly", file.path, details.concat(field("creators", prop("author")), field("contributors", prop("contributor"))), extra);
          if (present(prop("license"))) emit(16, "partly", file.path, details.concat(field("license", prop("license"))), Object.assign({}, extra, { notes: base.notes.concat([{ key: "selfcheck.note.copyrightCoverage" }]) }));
          if (present(prop("softwareRequirements"))) emit(13, "partly", file.path, details.concat(field("dependencies", prop("softwareRequirements"))), extra);
        }
      }
      if (file.kind === "dependency-build") {
        // A selected manifest is evidence of a declaration, not of installability or complete dependencies.
        let content = null;
        if (/(?:^|\/)package\.json$/i.test(file.path)) {
          try { const manifest = JSON.parse(file.text); const declared = Object.assign({}, manifest.dependencies, manifest.devDependencies, manifest.peerDependencies, manifest.optionalDependencies); if (Object.keys(declared).length) content = JSON.stringify(declared); } catch (error) { /* No supported declaration. */ }
        } else if (/(?:^|\/)requirements[^/]*\.txt$/i.test(file.path)) {
          const entries = file.text.split(/\r?\n/).map((line) => line.trim()).filter((line) => /^[a-z0-9][a-z0-9._-]*(?:\[|\s*(?:[<>=!~]|@)|\s*$)/i.test(line));
          if (entries.length) content = entries.join("\n");
        } else if (/(?:^|\/)pyproject\.toml$/i.test(file.path) && /^\s*(?:dependencies|requires)\s*=\s*\[[\s\S]*?["'][^"']+["']/m.test(file.text)) content = file.text;
        if (content) emit(13, "partly", file.path, details.concat(field("dependencies", content)), Object.assign({}, extra, { notes: base.notes.concat([{ key: "selfcheck.note.dependenciesCoverage" }]) }));
      }
      if (file.kind === "citation") {
        // Citation targets may describe a paper; no DOI or licence is attributed to the software from CFF alone.
        const authors = (file.text.match(/^authors:\s*\n((?:[ \t]+[^\n]*(?:\n|$))+)/m) || [])[1] || "";
        const names = [...authors.matchAll(/^\s{2,4}(?:-\s*)?(?:family-names|given-names):\s*(.+)$/gm)].map((match) => match[1]);
        if (names.length) emit(6, "partly", file.path, details.concat(field("citation.authors", names)), extra);
      }
    }
    return observations;
  };
  SC.registerLocalTests(["software.03", "software.04", "software.05", "software.06", "software.07", "software.09", "software.13", "software.14", "software.15", "software.16"]);
  SC.assessSoftware = function (check, result) { return SC.runLocalTests(check, SC.softwareObservations(check, result)); };
})();
