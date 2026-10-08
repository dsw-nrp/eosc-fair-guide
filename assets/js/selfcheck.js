/* Self-check of the FAIR Data Guide: a check per lens, answers that admit uncertainty, pre-fill from open sources
   with its source and date, results that lead back to the path, and exports. No score is computed anywhere.
   Answers stay in the browser: a lookup sends only the identifier the user enters or chooses, and a link with
   answers exists only when the user creates one. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const SC = (FG.selfcheck = FG.selfcheck || {});
  const ANSWERS = ["yes", "partly", "no", "unknown", "na"];
  const SHARE_CODE = { yes: "y", partly: "p", no: "n", unknown: "k", na: "x" };
  const FIRST_TIERS = ["#tier-required", "#tier-minimum"];
  const TIER_ORDER = ["#tier-required", "#tier-minimum", "#tier-recommended", "#tier-advanced"];
  const ANSWER_STATE = { yes: "met", partly: "partly", no: "gap", unknown: "unknown" };
  const STATE_ICON = { met: "✓", partly: "◐", gap: "✗", unknown: "?", open: "–", provided: "↗" };
  const FTR_VALUE = { yes: "pass", partly: "indeterminate", no: "fail", unknown: "indeterminate" };
  const FIP_RANK = ["in-use", "to-be-replaced", "planned", "under-consideration"];
  const NANOPUB_STATUS = {
    "declares-current-use-of": "in-use",
    "declares-planned-use-of": "planned",
    "declares-planned-replacement-of": "to-be-replaced",
  };
  /* The result format: its name and version are written into every JSON-LD and Markdown export, with the guide's
     version, so a file can be read by the version that understands it. */
  const FORMAT = "eosc-fair-guide-result";
  const FORMAT_VERSION = 1;
  const MAX_FILE = 2 * 1024 * 1024;
  const SOURCES = ["datacite", "resolver", "nkr", "re3data", "fip-dashboard", "fip-dashboard-snapshot", "nanopub", "champion", "shared"];
  const R3D = /r3d\d{9}/i;
  const NOTE_KEYS = ["partlyOnly", "notInSource", "noDeclaration", "resolves", "notResolved"];
  const LENS_ACTOR = { V: "#actor-user", DS: "#actor-data-steward", SR: "#actor-repository-admin", K: "#actor-community" };
  const status = { check: null, text: "", busy: false };

  /* ---------------------------------------------------------------- knowledge base */

  SC.checks = () => FG.ofType("Quiz");
  const itemsOf = (check) => FG.refs(check, "hasPart").sort(FG.byPosition);
  const modesOf = (check) => FG.refs(FG.get("#modes-" + check.identifier), "hasDefinedTerm");
  const profilesOf = (check) => FG.refs(FG.get("#profiles-" + check.identifier), "hasDefinedTerm");
  const today = () => new Date().toISOString().slice(0, 10);
  const label = (source) => FG.t("selfcheck.source." + source);
  const prefillOf = (item, source) => FG.refs(item, "additionalProperty").find((entry) => entry.propertyID === "prefill:" + source);

  function fragment(...children) {
    const node = document.createDocumentFragment();
    for (const child of children.flat(Infinity)) if (child != null && child !== false) node.append(child);
    return node;
  }

  /** A localised value: crate text, a {cs, en} object from a live service, or a plain string. */
  function localized(value) {
    if (Array.isArray(value)) return FG.text(value);
    if (value && typeof value === "object") return String(value[FG.state.lang] || value.cs || value.en || "");
    return value == null ? "" : String(value);
  }

  /* ---------------------------------------------------------------- state */

  /** The stored state of a check, repaired where browser storage or a link holds something unexpected. */
  function stateOf(check) {
    let entry = FG.state.answers[check.identifier];
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) entry = FG.state.answers[check.identifier] = {};
    if (!entry.items || typeof entry.items !== "object" || Array.isArray(entry.items)) entry.items = {};
    if (entry.mode && !modesOf(check).some((term) => term.termCode === entry.mode)) delete entry.mode;
    if (entry.profile && !profilesOf(check).some((term) => term.termCode === entry.profile)) delete entry.profile;
    return entry;
  }

  const hasState = (check) => {
    const entry = FG.state.answers[check.identifier];
    return Boolean(entry && typeof entry === "object" && !Array.isArray(entry));
  };

  function record(st, item) {
    const entry = st.items[item.identifier];
    return entry && typeof entry === "object" && !Array.isArray(entry) ? entry : null;
  }

  function answerOf(st, item) {
    const entry = record(st, item);
    if (!entry || !ANSWERS.includes(entry.value)) return null;
    return entry.value !== "na" || item.allowsNotApplicable ? entry.value : null;
  }

  function applies(item, st) {
    const refs = FG.refIds(item, "appliesTo");
    const modes = refs.filter((id) => id.startsWith("#mode-"));
    const profiles = refs.filter((id) => id.startsWith("#profile-"));
    if (modes.length && !modes.includes("#mode-" + st.mode)) return false;
    if (profiles.length && !profiles.includes("#profile-" + st.profile)) return false;
    return true;
  }

  const ready = (check, st) => (!modesOf(check).length || Boolean(st.mode)) && (!profilesOf(check).length || Boolean(st.profile));
  const providedByNrp = (item, st) => Boolean(st.profile) && FG.hasRef(item, "providedByNrpFor", "#profile-" + st.profile);
  const isFirstTier = (item) => FIRST_TIERS.includes(FG.id(item.tier));
  const applicable = (check, st) => (ready(check, st) ? itemsOf(check).filter((item) => applies(item, st)) : []);
  const answerable = (check, st) => applicable(check, st).filter((item) => !providedByNrp(item, st));
  /** The items a result covers: those the first view shows, every item once the check is extended, and any item
      the user has answered, so an answer to an extended item counts after the view returns to the basic items. */
  function resultItems(check, st) {
    const items = answerable(check, st);
    if (st.extended || !items.some(isFirstTier)) return items;
    return items.filter((item) => isFirstTier(item) || answerOf(st, item));
  }

  const byTier = (a, b) => TIER_ORDER.indexOf(FG.id(a.tier)) - TIER_ORDER.indexOf(FG.id(b.tier)) || FG.byPosition(a, b);

  /** Gaps (no, partly) and tasks (don't know), ordered by tier. */
  function outcomes(check, st) {
    const gaps = [];
    const tasks = [];
    for (const item of answerable(check, st)) {
      const value = answerOf(st, item);
      if (value === "no" || value === "partly") gaps.push(item);
      else if (value === "unknown") tasks.push(item);
    }
    return { gaps: gaps.sort(byTier), tasks: tasks.sort(byTier) };
  }

  /** Open self-check items addressed at a station, across the checks of the current lens; the path rail marks them. */
  FG.gapsAt = function (stationId) {
    let count = 0;
    for (const check of SC.checks()) {
      if (!FG.hasRef(check, "audience", "#lens-" + FG.state.lens) || !hasState(check)) continue;
      const { gaps, tasks } = outcomes(check, stateOf(check));
      count += gaps.concat(tasks).filter((item) => FG.id(item.fixAt) === "#station-" + stationId).length;
    }
    return count;
  };

  function itemState(st, item) {
    if (providedByNrp(item, st)) return "provided";
    return ANSWER_STATE[answerOf(st, item)] || "open";
  }

  /** The state of each principle the check covers: a gap wins, then partly, then unknown; met needs every item. */
  function principleRows(check, st) {
    const items = resultItems(check, st).filter((item) => answerOf(st, item) !== "na");
    return FG.principles()
      .map((principle) => {
        const mine = items.filter((item) => FG.hasRef(item, "about", principle["@id"]));
        if (!mine.length) return null;
        const values = mine.map((item) => answerOf(st, item)).filter(Boolean);
        let state = "open";
        if (values.includes("no")) state = "gap";
        else if (values.includes("partly")) state = "partly";
        else if (values.includes("unknown")) state = "unknown";
        else if (values.length === mine.length) state = "met";
        return { principle, state, answered: values.length, total: mine.length };
      })
      .filter(Boolean);
  }

  /* ---------------------------------------------------------------- answering */

  function save() {
    FG.saveState();
  }

  function setAnswer(check, item, value) {
    const st = stateOf(check);
    st.items[item.identifier] = Object.assign({}, record(st, item) || {}, { value, origin: "user" });
    save();
    FG.renderList("origin-" + item.identifier, () => fragment(origin(st, item)));
    FG.renderList("results", () => fragment(results(check, st)));
    FG.renderList("summary-body", () => fragment(summary(check, st)));
    refreshPreview(check, st);
    FG.renderList("share-output", () => fragment());
  }

  function setStatus(check, text) {
    status.check = check.identifier;
    status.text = text;
    const element = document.getElementById("prefill-status");
    if (element) element.textContent = text;
  }

  /** Record the evidence of one source for every item it can answer. A pre-filled value never replaces an answer
      the user gave, and evidence without a value never hides an earlier source's suggestion. */
  function applyEvidence(check, source, evidence, date, recordUrl) {
    const st = stateOf(check);
    let filled = 0;
    for (const item of answerable(check, st)) {
      const entry = prefillOf(item, source);
      if (!entry) continue;
      const result = evidence(item, FG.list(entry.value));
      if (!result) continue;
      let value = result.value || null;
      const notes = (result.notes || []).slice();
      if (value === "yes" && item.prefillLevel === "partly") {
        value = "partly";
        notes.push({ key: "selfcheck.note.partlyOnly" });
      }
      const current = record(st, item) || {};
      if (!value && current.prefill && current.prefill.value) continue;
      const prefill = { source: result.source || source, date, value, notes, list: result.list || [], fields: result.fields || [], record: result.record || recordUrl || null };
      const next = Object.assign({}, current, { prefill });
      if (current.origin !== "user" && value) Object.assign(next, { value, origin: "prefill" });
      else if (!current.origin) next.origin = "prefill";
      st.items[item.identifier] = next;
      if (value) filled += 1;
    }
    save();
    return filled;
  }

  function filled(value) {
    if (value == null) return false;
    if (Array.isArray(value)) return value.some(filled);
    if (typeof value === "object") return Object.values(value).some(filled);
    if (typeof value === "boolean") return value;
    return String(value).trim() !== "";
  }

  /** Whether a record field is present: `field`, `list[].field`, `list[key=value]` and `list[key=value].field`. */
  function pathState(record, path) {
    const contains = String(path).match(/^(\w+)=(.+)$/);
    if (contains) return FG.list(record[contains[1]]).some((value) => String(value).toLowerCase() === contains[2].toLowerCase()) ? "present" : "absent";
    const match = String(path).match(/^@?(\w+)(?:\[(?:(\w+)=(\w+))?\])?(?:\.(\w+))?$/);
    if (!match) return "absent";
    const [, field, key, wanted, sub] = match;
    let value = record[field];
    if (key) value = FG.list(value).filter((entry) => entry && String(entry[key]) === wanted);
    if (!sub) return filled(value) ? "present" : "absent";
    const list = FG.list(value);
    const withSub = list.filter((entry) => entry && filled(entry[sub]));
    if (!list.length || !withSub.length) return "absent";
    return withSub.length === list.length ? "present" : "partial";
  }

  /** A found value in a few words: the meaningful field of an object, or the text itself. */
  function summarise(value) {
    if (value && typeof value === "object") {
      const key = ["rightsUri", "rights", "relatedIdentifier", "nameIdentifier", "affiliationIdentifier", "name", "title", "description", "subject", "identifier", "url", "value"].find((name) =>
        filled(value[name])
      );
      return key ? summarise(value[key]) : JSON.stringify(value).slice(0, 80);
    }
    const text = String(value).replace(/\s+/g, " ").trim();
    return text.length > 120 ? text.slice(0, 117) + "…" : text;
  }

  /** The values a record holds at a path, for the evidence shown beside an item. */
  function pathValues(record, path) {
    const contains = String(path).match(/^(\w+)=(.+)$/);
    if (contains) return pathState(record, path) === "present" ? [contains[2]] : [];
    const match = String(path).match(/^@?(\w+)(?:\[(?:(\w+)=(\w+))?\])?(?:\.(\w+))?$/);
    if (!match || path === "@record") return [];
    const [, field, key, wanted, sub] = match;
    let value = record[field];
    if (key) value = FG.list(value).filter((entry) => entry && String(entry[key]) === wanted);
    const values = (sub ? FG.list(value).map((entry) => entry && entry[sub]) : FG.list(value))
      .flatMap((entry) => (Array.isArray(entry) ? entry : [entry]))
      .filter(filled)
      .map(summarise);
    return [...new Set(values)];
  }

  const SHOWN_VALUES = 3;

  /** The fields an item was answered from, each with the values found there. */
  function fieldsOf(record, paths) {
    return paths
      .map((path) => {
        const values = pathValues(record, path);
        return values.length ? { path, values: values.slice(0, SHOWN_VALUES), more: Math.max(0, values.length - SHOWN_VALUES) } : null;
      })
      .filter(Boolean);
  }

  function fieldEvidence(states) {
    if (states.length && states.every((state) => state === "present")) return { value: "yes" };
    if (states.some((state) => state !== "absent")) return { value: "partly", notes: [{ key: "selfcheck.note.partlyOnly" }] };
    return { value: null, notes: [{ key: "selfcheck.note.notInSource" }] };
  }

  /** Map FIP declarations onto an item: in use or to be replaced gives yes, planned or under consideration partly. */
  function fipEvidence(questions, declarations, matchBy) {
    const principles = questions.map((question) => question.replace(/-(MD|D)$/, ""));
    const mine = declarations.filter((declaration) =>
      matchBy === "question" ? questions.includes(declaration.question) : principles.includes(declaration.principle)
    );
    if (!mine.length) return { value: null, notes: [{ key: "selfcheck.note.noDeclaration" }] };
    const best = FIP_RANK.find((rank) => mine.some((declaration) => declaration.status === rank));
    const value = best === "in-use" || best === "to-be-replaced" ? "yes" : best ? "partly" : null;
    const notes = mine.filter((declaration) => declaration.note).map((declaration) => ({ text: declaration.note }));
    const seen = new Set();
    const list = [];
    for (const declaration of mine) {
      const key = (declaration.fer.url || declaration.fer.name) + " " + declaration.status;
      if (!declaration.fer.name || seen.has(key)) continue;
      seen.add(key);
      list.push(Object.assign({ status: declaration.status }, declaration.fer));
    }
    return { value, notes, list };
  }

  /** What an identifier turned out to be, kept with the check so the page and the exports can say it. */
  function describeTarget(check, info) {
    const st = stateOf(check);
    const merged = Object.assign({}, st.targetInfo || {});
    for (const [key, value] of Object.entries(info || {})) if (value) merged[key] = String(value).slice(0, 300);
    if (merged.name || merged.publisher) st.targetInfo = merged;
    save();
  }

  /** Title, first author, publisher, year and type from a DataCite record. */
  function dataciteInfo(attributes) {
    const titles = FG.list(attributes.titles).map((entry) => entry && entry.title).filter(Boolean);
    const creators = FG.list(attributes.creators).map((entry) => entry && entry.name).filter(Boolean);
    const publisher = attributes.publisher && typeof attributes.publisher === "object" ? attributes.publisher.name : attributes.publisher;
    const types = attributes.types || {};
    return {
      name: titles[0],
      creators: creators.length > 1 ? FG.t("selfcheck.etAl", { name: creators[0] }) : creators[0],
      publisher,
      year: attributes.publicationYear,
      kind: types.resourceType || types.resourceTypeGeneral,
      url: attributes.url,
    };
  }

  /** The assessed identifier described in one line: what it is and a link to it. */
  function targetCard(st) {
    const info = st.targetInfo;
    if (!info || !(info.name || info.publisher)) return null;
    const details = [info.creators, info.publisher, info.year, info.kind].filter(Boolean);
    return h(
      "p",
      { class: "target-card" },
      FG.icon("identifier"),
      h(
        "span",
        null,
        h("span", { class: "muted" }, FG.t("selfcheck.found") + ": "),
        h("strong", null, info.name || info.publisher),
        details.length ? h("span", { class: "muted" }, " · " + details.join(" · ")) : null,
        st.target ? [" · ", FG.external(st.target, FG.t("selfcheck.evidence.record"))] : null
      )
    );
  }

  /** Discard what an identifier gave: answers it pre-filled, including those taken unchanged from a loaded result,
      go; answers someone gave or changed stay, without the evidence. */
  function dropEvidence(st) {
    for (const [id, entry] of Object.entries(st.items)) {
      if (!entry || typeof entry !== "object") continue;
      const unchanged = entry.origin === "shared" && entry.prefill && (entry.value || null) === (entry.prefill.value || null);
      if (entry.origin === "prefill" || unchanged) delete st.items[id];
      else delete entry.prefill;
    }
  }

  /** Evidence describes one dataset, repository or profile; choosing another discards what the previous one gave. */
  function retarget(check, target) {
    const st = stateOf(check);
    if (st.target !== target) delete st.targetInfo;
    if (st.target && st.target !== target) dropEvidence(st);
    st.target = target;
    save();
  }

  /** Clear an identifier together with the answers it pre-filled; answers the user gave stay. */
  function clearTarget(check, key, focusId) {
    const st = stateOf(check);
    delete st[key];
    dropEvidence(st);
    delete st.target;
    delete st.targetInfo;
    save();
    status.check = check.identifier;
    status.text = FG.t("selfcheck.prefill.cleared");
    FG.rerender(focusId);
  }

  /** An identifier field with a visible control that clears it with the answers it pre-filled. */
  function clearableField(check, input, key, focusId) {
    return h(
      "span",
      { class: "field-clearable" },
      input,
      h(
        "button",
        {
          type: "button",
          class: "field-clear",
          id: input.id + "-clear",
          "aria-label": FG.t("selfcheck.prefill.clearLabel"),
          title: FG.t("selfcheck.prefill.clearLabel"),
          onclick: () => clearTarget(check, key, focusId),
        },
        FG.icon("clear") || "×"
      )
    );
  }

  async function runPrefill(check, source, focusId, work) {
    if (status.busy) return;
    status.busy = true;
    setStatus(check, FG.t("selfcheck.prefill.working", { source: label(source) }));
    const messages = [];
    let count = 0;
    try {
      count = await work(messages);
    } finally {
      status.busy = false;
    }
    const done = count || !messages.length ? [FG.t("selfcheck.prefill.done", { source: label(source), n: count })] : [];
    status.check = check.identifier;
    status.text = done.concat(messages).join(" ");
    FG.rerender(focusId);
  }

  function prefillFromPid(check, pid) {
    return runPrefill(check, pid.type === "doi" ? "datacite" : "resolver", "prefill-pid-run", async (messages) => {
      const date = today();
      let count = 0;
      try {
        const resolved = await FG.live.resolvePid(pid);
        if (resolved.found) describeTarget(check, { name: resolved.title, url: resolved.url });
        count += applyEvidence(
          check,
          "resolver",
          () =>
            resolved.found
              ? { value: "yes", notes: resolved.url ? [{ key: "selfcheck.note.resolves", params: { url: resolved.url } }] : [] }
              : { value: null, notes: [{ key: "selfcheck.note.notResolved" }] },
          date,
          resolved.url || null
        );
      } catch (error) {
        messages.push(FG.t("selfcheck.prefill.failed", { source: label("resolver") }));
      }
      if (pid.type !== "doi") return count;
      try {
        const attributes = await FG.live.datacite(pid.value);
        const recordUrl = FG.config.links.dataciteRecord ? FG.config.links.dataciteRecord + pid.value : null;
        if (attributes) describeTarget(check, dataciteInfo(attributes));
        if (attributes)
          count += applyEvidence(
            check,
            "datacite",
            (item, fields) => Object.assign(fieldEvidence(fields.map((field) => pathState(attributes, field))), { fields: fieldsOf(attributes, fields) }),
            date,
            recordUrl
          );
        else messages.push(FG.t("selfcheck.prefill.notFound", { source: label("datacite") }));
      } catch (error) {
        messages.push(FG.t("selfcheck.prefill.failed", { source: label("datacite") }));
      }
      return count;
    });
  }

  function prefillFromNkr(check, nkrRecord) {
    const st = stateOf(check);
    st.nkr = nkrRecord.id;
    retarget(check, nkrRecord.id ? FG.config.links.nkr + "objects/" + nkrRecord.id : nkrRecord.url || null);
    describeTarget(check, { name: nkrRecord.name, kind: "NKR" });
    return runPrefill(check, "nkr", "prefill-nkr-run", async () =>
      applyEvidence(
        check,
        "nkr",
        (item, fields) =>
          Object.assign(fieldEvidence(fields.map((field) => (field === "@record" ? "present" : pathState(nkrRecord.content, field)))), {
            fields: fieldsOf(nkrRecord.content || {}, fields),
          }),
        today(),
        st.target
      )
    );
  }

  function snapshotDeclarations(fip) {
    return FG.refs(fip, "hasPart").map((declaration) => {
      const fer = FG.get(declaration.mentions) || {};
      const record = FG.refIds(fer, "sameAs").find((id) => id.startsWith(FG.DASHBOARD));
      return {
        principle: (FG.get(declaration.about) || {}).termCode,
        status: declaration.creativeWorkStatus,
        note: declaration.description,
        fer: { name: FG.text(fer.alternateName || fer.name) || FG.text(fer.name), url: record || fer.url || null },
      };
    });
  }

  function prefillFromDashboard(check, fip) {
    const st = stateOf(check);
    st.fip = fip.identifier;
    retarget(check, FG.id(fip.sameAs) || fip.url || null);
    describeTarget(check, { name: [fip.alternateName, FG.text(fip.name)].filter(Boolean).join(": "), kind: "FIP" });
    const source = FG.live.available("fip-dashboard") ? "fip-dashboard" : "fip-dashboard-snapshot";
    return runPrefill(check, source, "prefill-fip-run", async (messages) => {
      let declarations = snapshotDeclarations(fip);
      let date = (FG.get("#snapshot-fip-dashboard") || {}).dateCreated;
      if (source === "fip-dashboard") {
        try {
          const data = await FG.live.dashboard();
          const current = data.fips.find((item) => item && item.id === fip.identifier);
          const names = new Map(data.resources.map((item) => [item && item.id, item]));
          if (current) {
            declarations = FG.list(current.declarations).map((declaration) => {
              const resource = names.get(declaration.resource) || {};
              return {
                principle: declaration.principle,
                status: declaration.status,
                note: declaration.note,
                fer: { name: String(resource.acronym || resource.name || declaration.resource), url: FG.DASHBOARD + "resources/" + declaration.resource },
              };
            });
            date = today();
          }
        } catch (error) {
          messages.push(FG.t("selfcheck.prefill.failed", { source: label("fip-dashboard") }));
        }
      }
      return applyEvidence(check, "fip", (item, questions) => Object.assign(fipEvidence(questions, declarations, "principle"), { source }), date, st.target);
    });
  }

  function prefillFromNanopub(check, code) {
    retarget(check, FG.live.fipIri(code));
    return runPrefill(check, "nanopub", "prefill-nanopub-run", async (messages) => {
      let rows;
      try {
        rows = await FG.live.fipDeclarations(code);
      } catch (error) {
        messages.push(FG.t("selfcheck.prefill.failed", { source: label("nanopub") }));
        return 0;
      }
      if (!rows.length) {
        messages.push(FG.t("selfcheck.prefill.nanopubEmpty"));
        return 0;
      }
      /* The FIP is published under one of several IRI forms; the result names the one that matched. */
      if (rows[0].fip) stateOf(check).target = rows[0].fip;
      const declarations = rows.map((row) => ({
        question: row.question,
        status: NANOPUB_STATUS[row.relation],
        fer: { name: row.label || row.fer, url: FG.live.httpsIri(row.fer) },
      }));
      return applyEvidence(check, "fip", (item, questions) => Object.assign(fipEvidence(questions, declarations, "question"), { source: "nanopub" }), today(), stateOf(check).target);
    });
  }

  /** Pre-fill from the re3data snapshot the guide carries; re3data itself cannot be read from a browser. */
  function prefillFromRe3data(check, id) {
    const st = stateOf(check);
    st.re3data = id;
    retarget(check, FG.config.links.re3dataRecord + id);
    const facts = (FG.config.re3data || {})[id];
    if (!facts) {
      describeTarget(check, { name: id, kind: "re3data" });
      setStatus(check, FG.t("selfcheck.prefill.re3dataMissing", { id }));
      FG.rerender("prefill-re3data-run");
      return Promise.resolve();
    }
    describeTarget(check, { name: facts.name, kind: "re3data" });
    return runPrefill(check, "re3data", "prefill-re3data-run", async () =>
      applyEvidence(check, "re3data", (item, fields) => Object.assign(fieldEvidence(fields.map((field) => pathState(facts, field))), { fields: fieldsOf(facts, fields) }), facts.date, st.target)
    );
  }

  /** Open the dataset check for an identifier from the landing's search and run the lookup the user chose. */
  SC.startWithPid = function (input) {
    const pid = FG.live.parsePid(input);
    const check = FG.get("#check-dataset");
    if (!pid || !check) return;
    const st = stateOf(check);
    st.mode = "after";
    st.pid = pid.value;
    retarget(check, FG.live.pidUrl(pid));
    const hash = FG.href("check", "dataset");
    if (window.location.hash === hash) {
      FG.render();
      prefillFromPid(check, pid);
    } else {
      window.addEventListener("hashchange", () => prefillFromPid(check, pid), { once: true });
      FG.navigate(hash);
    }
  };

  /* ---------------------------------------------------------------- pieces */

  function stateLabel(state) {
    return h("span", { class: "state", "data-state": state }, h("span", { "aria-hidden": "true" }, STATE_ICON[state] + " "), FG.t("selfcheck.state." + state));
  }

  function noteText(note) {
    if (note.text) return localized(note.text);
    return FG.t(note.key, note.params || {});
  }

  /** The fields and values an answer was taken from, as "field = value" pairs. */
  const foundFields = (pre) => FG.list(pre.fields).filter((field) => field && FG.list(field.values).length);
  const fieldText = (field) => field.path + " = " + field.values.join(", ") + (field.more ? " (+" + field.more + ")" : "");

  /** The evidence beside an item: the verdict of a pre-fill with the values it found, its source, date and record,
      a change by the user, or a shared link. */
  function origin(st, item) {
    const entry = record(st, item);
    if (!entry) return null;
    const value = answerOf(st, item);
    const parts = [];
    if (entry.origin === "shared") parts.push(h("p", { class: "source-chip", "data-origin": "shared" }, FG.t("selfcheck.origin.shared")));
    const pre = entry.prefill && typeof entry.prefill === "object" ? entry.prefill : null;
    if (pre) {
      const params = { source: label(pre.source), date: FG.formatDate(pre.date) };
      let kind = entry.origin === "prefill" ? "prefilled" : "confirmed";
      if (!pre.value) kind = "suggestion";
      else if (entry.origin === "user" && value !== pre.value) kind = "changed";
      /* An answer taken from someone else's result was not confirmed or changed by this user. */
      else if (entry.origin === "shared") kind = value !== pre.value ? "differs" : "prefilled";
      const verdict =
        kind === "changed" || kind === "differs"
          ? h("span", { class: "verdict", "data-kind": "changed" }, FG.t("selfcheck.evidence." + kind))
          : pre.value
            ? stateLabel(ANSWER_STATE[pre.value])
            : h("span", { class: "verdict", "data-kind": "none" }, FG.t("selfcheck.evidence.none"));
      const fields = foundFields(pre);
      parts.push(
        h(
          "p",
          { class: "evidence-head" },
          verdict,
          fields.map((field) => [" · ", h("span", { class: "evidence-field" }, h("code", null, field.path), " = ", h("code", null, field.values.join(", ")), field.more ? " (+" + field.more + ")" : "")])
        ),
        h(
          "p",
          { class: "source-chip", "data-origin": kind },
          FG.t("selfcheck.origin." + kind, Object.assign(params, { value: pre.value ? FG.t("selfcheck.answer." + pre.value) : "" })),
          pre.record ? [" · ", FG.external(pre.record, FG.t("selfcheck.evidence.record"))] : null
        )
      );
      for (const note of FG.list(pre.notes)) if (note && typeof note === "object") parts.push(h("p", { class: "small" }, noteText(note)));
      const list = FG.list(pre.list).filter((entryItem) => entryItem && entryItem.name);
      if (list.length) {
        parts.push(
          h("p", { class: "small" }, FG.t("selfcheck.note.declared") + ":"),
          h(
            "ul",
            { class: "small" },
            list.map((fer) =>
              h(
                "li",
                null,
                fer.url ? FG.external(fer.url, String(fer.name)) : String(fer.name),
                FIP_RANK.includes(fer.status) ? " (" + FG.t("selfcheck.fipStatus." + fer.status) + ")" : null
              )
            )
          )
        );
      }
    }
    return parts;
  }

  function radios(name, legend, options, current, onchange) {
    return h(
      "fieldset",
      { class: "choice" },
      h("legend", null, legend),
      h(
        "div",
        { class: "options" },
        options.map(([value, text]) => {
          const id = name + "-" + value;
          return h("label", { class: "option", for: id }, h("input", { type: "radio", id, name, value, checked: current === value, onchange: () => onchange(value, id) }), text);
        })
      )
    );
  }

  function settings(check, st) {
    const modes = modesOf(check);
    const profiles = profilesOf(check);
    const change = (key) => (value, id) => {
      st[key] = value;
      save();
      FG.rerender(id);
    };
    return [
      modes.length
        ? radios("mode", FG.t("selfcheck.modeQuestion"), modes.map((term) => [term.termCode, FG.t("selfcheck.mode." + term.termCode)]), st.mode, change("mode"))
        : null,
      profiles.length ? radios("profile", FG.t("selfcheck.profileQuestion"), profiles.map((term) => [term.termCode, FG.text(term.name)]), st.profile, change("profile")) : null,
    ];
  }

  function sourcesOf(check, st) {
    const sources = new Set();
    for (const item of answerable(check, st)) for (const entry of FG.refs(item, "additionalProperty")) sources.add(String(entry.propertyID).replace("prefill:", ""));
    return sources;
  }

  function pidControl(check, st) {
    const input = h("input", { id: "prefill-pid", type: "text", autocomplete: "off", spellcheck: "false", value: st.pid || "" });
    const run = () => {
      const pid = FG.live.parsePid(input.value);
      if (!pid) {
        setStatus(check, FG.t("selfcheck.prefill.pidInvalid"));
        return;
      }
      st.pid = pid.value;
      retarget(check, FG.live.pidUrl(pid));
      prefillFromPid(check, pid);
    };
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") run();
    });
    return h(
      "div",
      { class: "prefill-row" },
      h("label", { for: "prefill-pid" }, FG.t("selfcheck.prefill.pid")),
      h("div", { class: "inline" }, clearableField(check, input, "pid", "prefill-pid"), h("button", { type: "button", id: "prefill-pid-run", onclick: run }, FG.t("selfcheck.prefill.pidButton"))),
      h("p", { class: "small muted" }, FG.t("selfcheck.prefill.clearHint"))
    );
  }

  /** The re3data field: a re3data DOI (resolved through doi.org), an r3d identifier or the record's address. */
  function re3dataControl(check, st) {
    const input = h("input", { id: "prefill-re3data", type: "text", autocomplete: "off", spellcheck: "false", value: st.re3data || "" });
    const run = async () => {
      const value = input.value.trim();
      let id = (value.match(R3D) || [])[0];
      const pid = id ? null : FG.live.parsePid(value);
      if (!id && pid && pid.type === "doi") {
        try {
          const resolved = await FG.live.resolvePid(pid);
          id = ((resolved.url || "").match(R3D) || [])[0];
        } catch (error) {
          id = null;
        }
      }
      if (!id) {
        setStatus(check, FG.t("selfcheck.prefill.re3dataInvalid"));
        return;
      }
      prefillFromRe3data(check, id.toLowerCase());
    };
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") run();
    });
    return h(
      "div",
      { class: "prefill-row" },
      h("label", { for: "prefill-re3data" }, FG.t("selfcheck.prefill.re3data")),
      h("div", { class: "inline" }, clearableField(check, input, "re3data", "prefill-re3data"), h("button", { type: "button", id: "prefill-re3data-run", onclick: run }, FG.t("selfcheck.prefill.re3dataButton"))),
      h("p", { class: "small muted" }, FG.t("selfcheck.prefill.re3dataHint"))
    );
  }

  function nkrControl(check, st) {
    const nkr = FG.live.nkr;
    const records = nkr.state === "done" ? nkr.records : [];
    let picker = null;
    if (records.length) {
      const select = h(
        "select",
        { id: "prefill-nkr" },
        records.map((item, index) => h("option", { value: String(index), selected: st.nkr && st.nkr === item.id }, item.name))
      );
      picker = [
        h("label", { for: "prefill-nkr" }, FG.t("selfcheck.prefill.nkrChoose")),
        h(
          "div",
          { class: "inline" },
          select,
          h("button", { type: "button", id: "prefill-nkr-run", onclick: () => prefillFromNkr(check, records[Number(select.value)]) }, FG.t("selfcheck.prefill.nkrButton"))
        ),
      ];
    }
    return h("div", { class: "prefill-row" }, FG.live.nkrButton(), picker);
  }

  function fipControl(check, st) {
    const fips = FG.refs(FG.get("#fips"), "hasPart");
    const snapshot = FG.get("#snapshot-fip-dashboard");
    const select = h(
      "select",
      { id: "prefill-fip" },
      fips.map((fip) => h("option", { value: fip.identifier, selected: st.fip === fip.identifier }, [fip.alternateName, FG.text(fip.name)].filter(Boolean).join(": ")))
    );
    const nanopub = h("input", { id: "prefill-nanopub", type: "text", autocomplete: "off", spellcheck: "false" });
    const runNanopub = () => {
      const code = FG.live.nanopubCode(nanopub.value);
      if (code) prefillFromNanopub(check, code);
      else setStatus(check, FG.t("selfcheck.prefill.nanopubInvalid"));
    };
    nanopub.addEventListener("keydown", (event) => {
      if (event.key === "Enter") runNanopub();
    });
    return [
      fips.length
        ? h(
            "div",
            { class: "prefill-row" },
            h("label", { for: "prefill-fip" }, FG.t("selfcheck.prefill.fipChoose")),
            h(
              "div",
              { class: "inline" },
              select,
              h("button", { type: "button", id: "prefill-fip-run", onclick: () => prefillFromDashboard(check, fips.find((fip) => fip.identifier === select.value)) }, FG.t("selfcheck.prefill.fipButton"))
            ),
            !FG.live.available("fip-dashboard") && snapshot
              ? h(
                  "p",
                  { class: "small" },
                  FG.t("finder.snapshot", { date: FG.formatDate(snapshot.dateCreated) }) + ". ",
                  snapshot.disclaimer ? [h("strong", null, FG.t("finder.disclaimer") + ": "), FG.span(snapshot.disclaimer)] : null
                )
              : null
          )
        : null,
      h(
        "div",
        { class: "prefill-row" },
        h("label", { for: "prefill-nanopub" }, FG.t("selfcheck.prefill.nanopub")),
        h("div", { class: "inline" }, clearableField(check, nanopub, "nanopub", "prefill-nanopub"), h("button", { type: "button", id: "prefill-nanopub-run", onclick: runNanopub }, FG.t("selfcheck.prefill.nanopubButton"))),
        h("p", { class: "small muted" }, FG.t("selfcheck.prefill.clearHint"))
      ),
    ];
  }

  /** The ways to start a check without answering everything by hand: public records that the check's questions
      can be filled in from, and a result saved earlier. Before the mode or profile is chosen, only the saved result,
      which brings its own. */
  function startPanel(check, st, ready) {
    const sources = ready ? sourcesOf(check, st) : new Set();
    const controls = [];
    if (sources.has("datacite") || sources.has("resolver")) controls.push(pidControl(check, st));
    if (sources.has("nkr")) controls.push(nkrControl(check, st));
    if (sources.has("re3data")) controls.push(re3dataControl(check, st));
    if (sources.has("fip")) controls.push(fipControl(check, st));
    if (!controls.length) {
      return h(
        "section",
        { class: "prefill no-print", "aria-labelledby": "prefill-title" },
        h("h2", { id: "prefill-title" }, FG.t("selfcheck.savedTitle")),
        h("p", { class: "small" }, FG.t("selfcheck.savedText")),
        loadControl("load-file")
      );
    }
    return h(
      "section",
      { class: "prefill no-print", "aria-labelledby": "prefill-title" },
      h("h2", { id: "prefill-title" }, FG.t("selfcheck.prefill.title")),
      h("h3", null, FG.t("selfcheck.prefill.fromRecords")),
      h("p", { class: "small" }, FG.t("selfcheck.prefill.privacy")),
      controls,
      targetCard(st),
      h("p", { id: "prefill-status", role: "status", class: "small" }, status.check === check.identifier ? status.text : ""),
      h("div", { class: "prefill-file" }, h("h3", null, FG.t("selfcheck.prefill.fromFile")), h("p", { class: "small" }, FG.t("selfcheck.prefill.fromFileText")), loadControl("load-file"))
    );
  }

  function itemField(check, st, item) {
    const id = item.identifier;
    const meta = h(
      "div",
      { class: "badges" },
      isFirstTier(item) ? null : h("span", { class: "badge" }, FG.termName(FG.id(item.tier))),
      FG.principlesOf(item).map((principle) => FG.principleTile(principle))
    );
    const statement = [h("span", { class: "item-id" }, id), " ", FG.span(item.text)];
    const clauses = FG.refs(item, "citation");
    const basedOn = clauses.length
      ? h(
          "details",
          { class: "item-basis" },
          h("summary", null, FG.t("selfcheck.basedOn")),
          h("ul", { class: "content" }, clauses.map((clause) => h("li", null, h("span", { class: "code" }, clause.identifier || ""), " ", FG.span(clause.text || clause.name))))
        )
      : null;
    if (providedByNrp(item, st)) {
      return h(
        "div",
        { class: "item item-provided", id: "item-" + id },
        h("p", { class: "item-statement" }, statement),
        meta,
        h("p", null, stateLabel("provided"), " ", FG.t("selfcheck.providedByNrpText"))
      );
    }
    const current = answerOf(st, item);
    const options = ANSWERS.filter((value) => value !== "na" || item.allowsNotApplicable);
    return h(
      "fieldset",
      { class: "item", id: "item-" + id },
      h("legend", null, statement),
      meta,
      item.description ? h("p", { class: "small" }, FG.span(item.description)) : null,
      item.note ? h("p", { class: "small" }, FG.span(item.note)) : null,
      h(
        "div",
        { class: "options" },
        options.map((value) => {
          const inputId = "answer-" + id + "-" + value;
          return h(
            "label",
            { class: "option", for: inputId },
            h("input", { type: "radio", id: inputId, name: "answer-" + id, value, checked: current === value, onchange: () => setAnswer(check, item, value) }),
            FG.t("selfcheck.answer." + value)
          );
        })
      ),
      h("div", { id: "origin-" + id, class: "origin" }, origin(st, item)),
      fixAtLine(item),
      basedOn
    );
  }

  /** The path step where an item is addressed, named on every item. */
  function fixAtLine(item) {
    const station = FG.get(item.fixAt);
    return station ? h("p", { class: "fix-at small muted" }, FG.t("selfcheck.fixAt", { station: FG.text(station.name) })) : null;
  }

  const letterOf = (item) => String((FG.principlesOf(item)[0] || {}).termCode || "").charAt(0);

  /** How items are grouped: by FAIR principle by default, or by the path step that addresses them. */
  function groupingControl(compact) {
    const current = FG.state.checkGrouping === "steps" ? "steps" : "principles";
    return h(
      "fieldset",
      { class: "grouping no-print" + (compact ? " segmented" : "") },
      h("legend", null, FG.t("selfcheck.grouping")),
      ["principles", "steps"].map((value) =>
        h(
          "label",
          { class: "option", for: "grouping-" + value },
          h("input", {
            type: "radio",
            id: "grouping-" + value,
            name: "grouping",
            value,
            checked: current === value,
            onchange: () => {
              FG.state.checkGrouping = value;
              FG.saveState();
              FG.rerender("grouping-" + value);
            },
          }),
          h("span", null, FG.t((compact ? "selfcheck.groupByShort." : "selfcheck.groupBy.") + value))
        )
      )
    );
  }

  /** The groups shared by the list, the summary and the result: by FAIR principle (F, A, I, R) by default, or by
      the path step that addresses each question. Questions outside every group come last, ungrouped. */
  function groupsOf(items) {
    let groups;
    let loose;
    if (FG.state.checkGrouping === "steps") {
      groups = FG.stations().map((station) => ({ station, items: items.filter((item) => FG.id(item.fixAt) === station["@id"]) }));
      loose = items.filter((item) => !FG.get(item.fixAt));
    } else {
      groups = ["F", "A", "I", "R"].map((letter) => ({ letter, items: items.filter((item) => letterOf(item) === letter) }));
      loose = items.filter((item) => !["F", "A", "I", "R"].includes(letterOf(item)));
    }
    groups = groups.filter((group) => group.items.length);
    return loose.length ? groups.concat({ items: loose }) : groups;
  }

  /** A group's mark: the principle letter in its colour, or the path step's icon as on the path. */
  function groupMark(group) {
    if (group.letter) return h("span", { class: "principle-letter", "data-letter": group.letter }, group.letter);
    if (group.station) {
      const icon = FG.config.icons && FG.config.icons.station && FG.config.icons.station[group.station.identifier];
      return FG.icon(icon, { class: "group-icon" }) || h("span", null, String(group.station.position));
    }
    return h("span", { class: "group-other", "aria-hidden": "true" }, "…");
  }

  const groupName = (group) => (group.letter ? FG.t("explorer.group." + group.letter) : group.station ? FG.text(group.station.name) : FG.t("selfcheck.groupOther"));
  const groupTitle = (group) => [groupMark(group), " ", groupName(group)];

  /* On a wide screen with the summary open, the check's controls sit in the summary, at hand while scrolling; on a
     narrow screen or with the summary collapsed they sit above the questions. Crossing the width re-renders. */
  const WIDE = window.matchMedia ? window.matchMedia("(min-width: 60rem)") : null;
  const controlsInSummary = () => Boolean(WIDE && WIDE.matches) && !FG.state.resultCollapsed;
  if (WIDE && WIDE.addEventListener) WIDE.addEventListener("change", () => document.querySelector(".check-view") && FG.rerender());

  /** The extended switch (when the check has further items) and the grouping. */
  function checkControls(check, st, compact) {
    const all = applicable(check, st);
    const first = all.filter(isFirstTier);
    const more = first.length ? all.length - first.length : 0;
    return [more ? extendedSwitch(st, more, compact) : null, groupingControl(true)];
  }

  /** One sentence on what the first view's tier means and how many further items exist, with the control to add them. */
  function tierInfo(check, st, first, more) {
    if (!first.length || !more) return null;
    const tier = FG.get(first[0].tier) || {};
    return h(
      "p",
      { class: "tier-info" },
      h("strong", null, FG.t("selfcheck.tierCount", { tier: FG.text(tier.name), n: first.length }) + " "),
      tier.description ? FG.span(tier.description) : null,
      " " + FG.t("selfcheck.extendedExplain")
    );
  }

  /** The extended check as an on/off switch: it adds the recommended and advanced items and keeps the answers. */
  function extendedSwitch(st, more, compact) {
    return h(
      "label",
      { class: "switch", for: "extended-toggle" },
      h("input", {
        type: "checkbox",
        role: "switch",
        id: "extended-toggle",
        checked: Boolean(st.extended),
        onchange: () => {
          st.extended = !st.extended;
          save();
          FG.rerender("extended-toggle");
        },
      }),
      h("span", { class: "switch-track", "aria-hidden": "true" }),
      h("span", { title: compact ? FG.t("selfcheck.extendedSwitch", { n: more }) : null }, FG.t(compact ? "selfcheck.extendedShort" : "selfcheck.extendedSwitch", { n: more })),
      h("span", { class: "switch-state", "aria-hidden": "true" }, FG.t(st.extended ? "common.on" : "common.off"))
    );
  }

  function itemsSection(check, st) {
    const all = applicable(check, st);
    const first = all.filter(isFirstTier);
    /* A check without Minimum or Required items has no short first view and shows every item. */
    const shown = st.extended || !first.length ? all : first;
    const more = first.length ? all.length - first.length : 0;
    return h(
      "div",
      { class: "items no-print" },
      tierInfo(check, st, first, more),
      controlsInSummary() ? null : h("div", { class: "check-toolbar no-print" }, checkControls(check, st)),
      groupsOf(shown).map((group) =>
        h("section", { class: "item-group" }, groupTitle(group) ? h("h2", null, groupTitle(group)) : null, group.items.map((item) => itemField(check, st, item)))
      )
    );
  }

  /* ---------------------------------------------------------------- results */

  function whom(item) {
    const own = LENS_ACTOR[FG.state.lens];
    const actors = FG.refs(item, "fixedBy").filter((actor) => actor["@id"] !== "#actor-user" && actor["@id"] !== own);
    if (FG.state.lens === "V" && !actors.some((actor) => actor["@id"] === "#actor-data-steward")) actors.push(FG.get("#actor-data-steward"));
    const helps = [];
    if (actors.some((actor) => actor && actor["@id"] === "#actor-data-steward")) helps.push(FG.get("#help-data-steward"));
    if (!actors.filter(Boolean).length) helps.push(FG.get("#help-nrp-support"));
    return { names: actors.filter(Boolean).map((actor) => FG.text(actor.name)), helps: helps.filter(Boolean) };
  }

  function helpLink(help) {
    return help.url.startsWith("mailto:") ? h("a", { href: help.url }, FG.text(help.name)) : FG.external(help.url, FG.text(help.name));
  }

  /** The path step where something is fixed, as a link with the step's icon. */
  function stepLink(station) {
    const icon = FG.config.icons && FG.config.icons.station && FG.config.icons.station[station.identifier];
    return h("a", { class: "step-link", href: FG.href("path", station.identifier) }, FG.icon(icon), FG.span(station.name));
  }

  /** Something missing, as a card: the question, then where to fix it and who does it. */
  function gapItem(st, item) {
    const station = FG.get(item.fixAt);
    const who = FG.refs(item, "fixedBy").map((actor) => FG.text(actor.name));
    const state = itemState(st, item);
    return h(
      "li",
      { class: "action-card", "data-state": state },
      h(
        "p",
        { class: "action-title" },
        stateLabel(state),
        " ",
        h("span", { class: "item-id" }, item.identifier),
        " ",
        FG.span(item.text),
        isFirstTier(item) ? null : [" ", h("span", { class: "badge" }, FG.termName(FG.id(item.tier)))]
      ),
      h(
        "p",
        { class: "action-meta" },
        station ? [h("span", { class: "action-label" }, FG.t("selfcheck.result.whereFix") + ": "), stepLink(station)] : null,
        who.length ? [station ? h("span", { class: "action-sep" }, " · ") : null, h("span", { class: "action-label" }, FG.t("selfcheck.result.whoFix") + ": "), who.join(", ")] : null
      )
    );
  }

  function taskItem(item) {
    const ask = whom(item);
    const lookup = FG.id(item.lookup);
    return h(
      "li",
      { class: "action-card", "data-state": "unknown" },
      h("p", { class: "action-title" }, stateLabel("unknown"), " ", h("span", { class: "item-id" }, item.identifier), " ", FG.span(item.text)),
      h(
        "p",
        { class: "action-meta" },
        ask.names.length ? [h("span", { class: "action-label" }, FG.t("selfcheck.result.askLabel") + ": "), ask.names.join(", ")] : null,
        lookup ? [ask.names.length ? h("span", { class: "action-sep" }, " · ") : null, FG.external(lookup, FG.t("selfcheck.result.lookup"))] : null,
        ask.helps.map((help) => [h("span", { class: "action-sep" }, " · "), helpLink(help)])
      )
    );
  }

  function answerText(st, item) {
    const value = answerOf(st, item);
    return value ? FG.t("selfcheck.answer." + value) : FG.t("selfcheck.result.unanswered");
  }

  function sourceText(st, item) {
    const entry = record(st, item);
    if (!entry) return "";
    if (entry.origin === "shared") return label("shared");
    if (entry.prefill && entry.prefill.source) return label(entry.prefill.source) + ", " + FG.formatDate(entry.prefill.date);
    return "";
  }

  /** The evidence of an answer in one line, for the summary and the exported result set. */
  function evidenceText(st, item) {
    const entry = record(st, item);
    const pre = entry && entry.prefill && typeof entry.prefill === "object" ? entry.prefill : null;
    if (!pre) return "";
    const fers = FG.list(pre.list).filter((fer) => fer && fer.name).map((fer) => String(fer.name));
    return foundFields(pre)
      .map(fieldText)
      .concat(fers.length ? [FG.t("selfcheck.note.declared") + ": " + fers.join(", ")] : [])
      .concat(pre.record ? [pre.record] : [])
      .join("; ");
  }

  /** One answer: the question and the answer on one line, then where it came from and what supports it. */
  function answerRow(st, item) {
    const entry = record(st, item);
    const pre = entry && entry.prefill && typeof entry.prefill === "object" ? entry.prefill : null;
    const value = answerOf(st, item);
    const meta = [];
    if (entry && entry.origin === "shared") meta.push(FG.t("selfcheck.origin.shared"));
    if (pre) {
      meta.push(label(pre.source) + ", " + FG.formatDate(pre.date));
      const fields = foundFields(pre);
      for (const field of fields) meta.push(h("span", { class: "evidence-field" }, h("code", null, field.path), " = ", h("code", null, field.values.join(", ")), field.more ? " (+" + field.more + ")" : ""));
      if (!fields.length && !pre.value) meta.push(FG.t("selfcheck.evidence.notStated"));
      if (pre.record) meta.push(FG.external(pre.record, FG.t("selfcheck.evidence.record")));
    }
    return h(
      "li",
      { class: "answer-row" },
      h(
        "p",
        { class: "answer-line" },
        h(
          "span",
          { class: "answer-pill", "data-state": itemState(st, item) },
          h("span", { "aria-hidden": "true" }, STATE_ICON[itemState(st, item)] + " "),
          providedByNrp(item, st) ? FG.t("selfcheck.state.provided") : value ? FG.t("selfcheck.answer." + value) : FG.t("selfcheck.result.unanswered")
        ),
        h("span", { class: "answer-question" }, h("span", { class: "item-id" }, item.identifier), " ", FG.span(item.text))
      ),
      meta.length ? h("p", { class: "answer-meta" }, meta.map((part, index) => [index ? " · " : "", part])) : null
    );
  }

  function results(check, st) {
    const items = resultItems(check, st);
    const answered = items.filter((item) => answerOf(st, item)).length;
    const { gaps, tasks } = outcomes(check, st);
    const counts = {};
    for (const item of items) counts[itemState(st, item)] = (counts[itemState(st, item)] || 0) + 1;
    return [
      h(
        "div",
        { class: "result-headline" },
        h("p", { class: "result-progress" }, FG.t("selfcheck.progress", { n: answered, total: items.length })),
        h(
          "ul",
          { class: "result-counts" },
          ["met", "partly", "gap", "unknown", "open"]
            .filter((state) => counts[state])
            .map((state) => h("li", { "data-state": state }, h("span", { "aria-hidden": "true" }, STATE_ICON[state] + " "), FG.t("selfcheck.count." + state, { n: counts[state] })))
        ),
        st.target
          ? h(
              "p",
              { class: "small" },
              FG.t("selfcheck.targetLabel") + ": ",
              FG.external(st.target, (st.targetInfo && (st.targetInfo.name || st.targetInfo.publisher)) || st.target)
            )
          : null,
        h("p", { class: "small muted" }, FG.t("selfcheck.result.advisory"))
      ),
      h("h3", { id: "results-gaps", tabindex: "-1" }, FG.t("selfcheck.result.gaps")),
      gaps.length ? h("ul", { class: "gaps" }, gaps.map((item) => gapItem(st, item))) : h("p", { class: "muted" }, FG.t("selfcheck.result.noGaps")),
      tasks.length ? [h("h3", { id: "results-tasks", tabindex: "-1" }, FG.t("selfcheck.result.tasks")), h("ul", { class: "gaps" }, tasks.map(taskItem))] : null,
      h("h3", { class: "result-all" }, FG.t("selfcheck.result.answers")),
      resultGroups(check, st, items),
    ];
  }

  /** The overview of the result in the list's groups: for a principle group the state of each principle it covers,
      then every question with its answer and the evidence behind it. */
  function resultGroups(check, st, items) {
    const shown = applicable(check, st).filter((item) => providedByNrp(item, st) || items.includes(item));
    const rows = principleRows(check, st);
    return h(
      "div",
      { class: "result-groups" },
      groupsOf(shown).map((group) => {
        const principles = group.letter ? rows.filter((row) => String(row.principle.termCode).charAt(0) === group.letter) : [];
        return h(
          "section",
          { class: "result-group" },
          groupTitle(group) ? h("h3", null, groupTitle(group)) : null,
          principles.length
            ? h(
                "ul",
                { class: "principle-states", "aria-label": FG.t("selfcheck.result.principles") },
                principles.map((row) =>
                  h(
                    "li",
                    { class: "principle-state", "data-state": row.state },
                    h(
                      "a",
                      { href: FG.href("explorer", row.principle.termCode), title: FG.t("selfcheck.state." + row.state) },
                      row.state === "open" ? null : h("span", { "aria-hidden": "true" }, STATE_ICON[row.state] + " "),
                      h("strong", null, row.principle.termCode),
                      " ",
                      FG.span(row.principle.name),
                      h("span", { class: "visually-hidden" }, ": " + FG.t("selfcheck.state." + row.state))
                    )
                  )
                )
              )
            : null,
          h("ul", { class: "answers-list" }, group.items.map((item) => answerRow(st, item)))
        );
      })
    );
  }

  /* ---------------------------------------------------------------- exports */

  const pageBase = () => FG.config.pageUrl;
  const escapeMarkdown = (value) => String(value).replace(/([\\|[\]<>*_`#])/g, "\\$1");

  function markdown(check, st) {
    const items = resultItems(check, st);
    const { gaps, tasks } = outcomes(check, st);
    const lines = ["# " + escapeMarkdown(FG.text(check.name)) + " (" + FG.formatDate(today()) + ")", ""];
    if (st.target) {
      const named = st.targetInfo && (st.targetInfo.name || st.targetInfo.publisher);
      lines.push(escapeMarkdown(FG.t("selfcheck.targetLabel") + ": " + (named ? named + " (" + st.target + ")" : st.target)), "");
    }
    lines.push(escapeMarkdown(FG.t("selfcheck.result.advisory")), "");
    const row = (cells) => "| " + cells.map((cell) => escapeMarkdown(cell).replace(/\n/g, " ")).join(" | ") + " |";
    if (profilesOf(check).length) {
      lines.push("## " + FG.t("selfcheck.result.gate"), "", row([FG.t("selfcheck.result.condition"), FG.t("selfcheck.result.state")]), "| --- | --- |");
      for (const item of applicable(check, st)) lines.push(row([item.identifier + " " + FG.text(item.text), FG.t("selfcheck.state." + itemState(st, item))]));
    } else {
      lines.push("## " + FG.t("selfcheck.result.principles"), "", row([FG.t("selfcheck.result.principle"), FG.t("selfcheck.result.state"), FG.t("selfcheck.result.answered")]), "| --- | --- | --- |");
      for (const entry of principleRows(check, st)) lines.push(row([entry.principle.termCode, FG.t("selfcheck.state." + entry.state), FG.t("selfcheck.result.ofTotal", { n: entry.answered, total: entry.total })]));
    }
    lines.push("", "## " + FG.t("selfcheck.result.gaps"), "");
    if (!gaps.length) lines.push(escapeMarkdown(FG.t("selfcheck.result.noGaps")));
    for (const item of gaps) {
      const station = FG.get(item.fixAt);
      const where = station ? `${FG.t("selfcheck.result.whereFix")}: [${escapeMarkdown(FG.text(station.name))}](${pageBase()}${FG.href("path", station.identifier)})` : "";
      const who = FG.refs(item, "fixedBy").map((actor) => FG.text(actor.name)).join(", ");
      lines.push(`- **${item.identifier}** ${escapeMarkdown(FG.text(item.text))} (${FG.termName(FG.id(item.tier))}, ${FG.t("selfcheck.answer." + answerOf(st, item))}). ${where}${who ? "; " + FG.t("selfcheck.result.whoFix") + ": " + who : ""}`);
    }
    if (tasks.length) {
      lines.push("", "## " + FG.t("selfcheck.result.tasks"), "");
      for (const item of tasks) {
        const ask = whom(item);
        const lookup = FG.id(item.lookup);
        lines.push(`- **${item.identifier}** ${escapeMarkdown(FG.text(item.text))}${ask.names.length ? ". " + FG.t("selfcheck.result.ask", { whom: ask.names.join(", ") }) : ""}${lookup ? ` ([${FG.t("selfcheck.result.lookup")}](${lookup}))` : ""}`);
      }
    }
    lines.push("", "## " + FG.t("selfcheck.result.answers"), "");
    for (const item of items) {
      const details = [sourceText(st, item), evidenceText(st, item)].filter(Boolean).join("; ");
      lines.push(`- **${item.identifier}** ${escapeMarkdown(FG.text(item.text))}: **${escapeMarkdown(answerText(st, item))}**${details ? " (" + escapeMarkdown(details) + ")" : ""}`);
    }
    lines.push("", `${FG.t("selfcheck.export.generatedBy")}, ${FG.config.version}: ${pageBase()}`, "");
    /* Hidden from readers: the answers as in a shared link, with the format and guide versions, and the whole state
       the JSON-LD carries (identifiers, what they are, evidence), so the summary loads back completely. */
    lines.push(`<!-- fair-guide-result v${FORMAT_VERSION} guide=${FG.config.version}: ${check.identifier} ${SC.sharePayload(check, st)} -->`);
    lines.push("<!-- fair-guide-state", toBase64(JSON.stringify(SC.portableState(check, st))).match(/.{1,76}/g).join("\n"), "-->", "");
    return lines.join("\n");
  }

  function logLine(st, item) {
    const parts = [FG.t("selfcheck.result.answer") + ": " + answerText(st, item)];
    const source = sourceText(st, item);
    if (source) parts.push(source);
    const found = evidenceText(st, item);
    if (found) parts.push(FG.t("selfcheck.result.evidence") + ": " + found);
    return parts.join("; ");
  }

  const recordOf = (st, item) => {
    const entry = record(st, item);
    return entry && entry.prefill && typeof entry.prefill === "object" && entry.prefill.record ? entry.prefill.record : null;
  };

  /** The result as an FTR test result set in a small RO-Crate. Self-check answers and live test verdicts share it. */
  SC.ftrCrate = function (check, st) {
    const vocab = FG.config.vocab;
    const guideCrate = pageBase() + "ro-crate-metadata.json";
    const now = new Date().toISOString();
    const target = st.target ? { "@id": st.target } : undefined;
    const members = [];
    const tests = [];
    for (const item of answerable(check, st)) {
      const value = answerOf(st, item);
      if (!value || value === "na") continue;
      const testId = guideCrate + "#item-" + item.identifier;
      members.push({
        "@id": "#result-" + item.identifier,
        "@type": ["CreativeWork", "TestResult"],
        name: item.identifier + ": " + FG.text(item.text),
        "prov:value": FTR_VALUE[value],
        "ftr:completion": value === "yes" ? 1 : value === "no" ? 0 : undefined,
        "ftr:outputFromTest": { "@id": testId },
        "ftr:assessmentTarget": target,
        "ftr:log": logLine(st, item),
        "prov:used": recordOf(st, item) ? { "@id": recordOf(st, item) } : undefined,
        "prov:wasGeneratedBy": { "@id": "#run" },
      });
      tests.push({ "@id": testId, "@type": "CreativeWork", additionalType: { "@id": vocab.ftr + "Test" }, name: item.identifier + ": " + FG.text(item.text) });
    }
    for (const verdict of FG.list(st.verdicts)) {
      if (!verdict || !["pass", "fail", "indeterminate"].includes(verdict.value) || !verdict.test) continue;
      const test = FG.get("#test-" + verdict.test);
      if (!test) continue;
      members.push({
        "@id": "#result-" + verdict.test,
        "@type": ["CreativeWork", "TestResult"],
        name: FG.text(test.name),
        "prov:value": verdict.value,
        "ftr:completion": verdict.value === "pass" ? 1 : verdict.value === "fail" ? 0 : undefined,
        "ftr:outputFromTest": { "@id": test.url },
        "ftr:assessmentTarget": target,
        "ftr:log": verdict.log ? String(verdict.log) : undefined,
        "prov:wasGeneratedBy": { "@id": "#run" },
      });
      tests.push({ "@id": test.url, "@type": "CreativeWork", additionalType: { "@id": vocab.ftr + "Test" }, name: FG.text(test.name) });
    }
    const name = FG.text(check.name) + " (" + now.slice(0, 10) + ")";
    const graph = [
      { "@id": "ro-crate-metadata.json", "@type": "CreativeWork", conformsTo: { "@id": vocab.roCrate }, about: { "@id": "./" } },
      {
        "@id": "./",
        "@type": "Dataset",
        name,
        description: FG.t("selfcheck.result.advisory"),
        datePublished: now.slice(0, 10),
        license: { "@id": "#license" },
        isBasedOn: { "@id": guideCrate },
        about: { "@id": guideCrate + "#check-" + check.identifier },
        mentions: { "@id": "#result-set" },
        guideState: JSON.stringify(SC.portableState(check, st)),
      },
      { "@id": guideCrate + "#check-" + check.identifier, "@type": "CreativeWork", name: FG.text(check.name) },
      { "@id": "#license", "@type": "CreativeWork", name: FG.t("selfcheck.export.licenseName"), description: FG.t("selfcheck.export.licenseText") },
      {
        "@id": guideCrate,
        "@type": "CreativeWork",
        name: FG.text(FG.root.name),
        version: FG.config.version,
        url: pageBase(),
      },
      {
        "@id": "#result-set",
        "@type": ["CreativeWork", "TestResultSet"],
        name,
        "ftr:assessmentTarget": target,
        "prov:hadMember": members.map((member) => ({ "@id": member["@id"] })),
        "prov:wasGeneratedBy": { "@id": "#run" },
      },
      {
        "@id": "#run",
        "@type": ["Action", "TestExecutionActivity"],
        name: FG.t("selfcheck.export.generatedBy"),
        endTime: now,
        object: target,
        instrument: { "@id": guideCrate },
        result: { "@id": "#result-set" },
      },
      ...members,
      ...tests,
    ];
    const records = new Set(members.map((member) => member["prov:used"] && member["prov:used"]["@id"]).filter(Boolean));
    if (target) records.add(st.target);
    for (const id of records) graph.push({ "@id": id, "@type": "CreativeWork", name: id });
    return {
      "@context": [
        vocab.roCrate + "/context",
        {
          ftr: vocab.ftr,
          prov: vocab.prov,
          TestResultSet: vocab.ftr + "TestResultSet",
          TestResult: vocab.ftr + "TestResult",
          TestExecutionActivity: vocab.ftr + "TestExecutionActivity",
          guideState: vocab.guide + "guideState",
        },
      ],
      "@graph": graph,
    };
  };

  /* ---------------------------------------------------------------- portable results */

  /** A check's answers, mode or profile, target and evidence, as carried by the JSON-LD export. */
  SC.portableState = function (check, st) {
    const items = {};
    for (const item of itemsOf(check)) {
      const entry = record(st, item);
      if (!entry || (!answerOf(st, item) && !entry.prefill)) continue;
      items[item.identifier] = { value: answerOf(st, item), origin: entry.origin || null, prefill: entry.prefill || null };
    }
    return {
      format: FORMAT,
      v: FORMAT_VERSION,
      guideVersion: FG.config.version,
      check: check.identifier,
      mode: st.mode || null,
      profile: st.profile || null,
      target: st.target || null,
      targetInfo: st.targetInfo || null,
      pid: st.pid || null,
      nkr: st.nkr || null,
      re3data: st.re3data || null,
      fip: st.fip || null,
      items,
    };
  };

  /** Notes for a loaded result: questions this version does not know, and a file from another guide version. */
  function loadNotices(skipped, version) {
    const notices = [];
    if (skipped) notices.push(FG.t("selfcheck.load.skipped", { n: skipped }));
    if (version && version !== FG.config.version) notices.push(FG.t("selfcheck.load.otherVersion", { version, current: FG.config.version }));
    return notices;
  }

  const isText = (value, max) => typeof value === "string" && value.length <= max;
  const webUrl = (value) => (isText(value, 2000) && /^https?:\/\/[^\s]+$/.test(value) ? value : null);
  const textValue = (value) =>
    isText(value, 2000) ? value : value && typeof value === "object" && (isText(value.cs, 2000) || isText(value.en, 2000)) ? { cs: String(value.cs || ""), en: String(value.en || "") } : null;

  /** Evidence from a file, keeping only the shapes the guide itself writes. */
  function readPrefill(pre) {
    if (!pre || typeof pre !== "object" || !SOURCES.includes(pre.source) || !/^\d{4}-\d{2}-\d{2}$/.test(String(pre.date))) return null;
    const notes = (Array.isArray(pre.notes) ? pre.notes.slice(0, 10) : [])
      .map((note) => {
        if (!note || typeof note !== "object") return null;
        if (typeof note.key === "string" && NOTE_KEYS.includes(note.key.replace("selfcheck.note.", ""))) {
          const params = {};
          for (const [key, value] of Object.entries(note.params || {})) if (isText(value, 2000)) params[key] = value;
          return { key: "selfcheck.note." + note.key.replace("selfcheck.note.", ""), params };
        }
        const text = textValue(note.text);
        return text ? { text } : null;
      })
      .filter(Boolean);
    const list = (Array.isArray(pre.list) ? pre.list.slice(0, 50) : [])
      .filter((fer) => fer && isText(fer.name, 300))
      .map((fer) => ({ name: fer.name, url: webUrl(fer.url), status: FIP_RANK.includes(fer.status) ? fer.status : undefined }));
    const fields = (Array.isArray(pre.fields) ? pre.fields.slice(0, 20) : [])
      .filter((field) => field && isText(field.path, 100) && Array.isArray(field.values))
      .map((field) => ({ path: field.path, values: field.values.filter((value) => isText(value, 300)).slice(0, SHOWN_VALUES), more: Number.isInteger(field.more) && field.more > 0 ? field.more : 0 }));
    return { source: pre.source, date: pre.date, value: ANSWERS.includes(pre.value) ? pre.value : null, notes, list, fields, record: webUrl(pre.record) };
  }

  /** A check state from a file the guide wrote, or the reason it cannot be read: not a guide file, a newer format,
      a check this version does not know, or a damaged file. Questions this version does not know are skipped. */
  SC.readPortable = function (data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) return { error: "damaged" };
    if (data.format !== undefined && data.format !== FORMAT) return { error: "notGuide" };
    if (Number.isInteger(data.v) && data.v > FORMAT_VERSION) return { error: "newer", params: { version: isText(data.guideVersion, 40) ? data.guideVersion : "?" } };
    if (data.v !== FORMAT_VERSION || !isText(data.check, 50)) return { error: "damaged" };
    const check = FG.get("#check-" + data.check);
    if (!check) return { error: "unknownCheck" };
    if (!data.items || typeof data.items !== "object" || Array.isArray(data.items)) return { error: "damaged" };
    if (data.mode !== null && !modesOf(check).some((term) => term.termCode === data.mode)) return { error: "damaged" };
    if (data.profile !== null && !profilesOf(check).some((term) => term.termCode === data.profile)) return { error: "damaged" };
    const ids = new Set(itemsOf(check).map((item) => item.identifier));
    const items = {};
    let skipped = 0;
    for (const [id, entry] of Object.entries(data.items)) {
      if (!ids.has(id)) {
        skipped += 1;
        continue;
      }
      if (!entry || typeof entry !== "object") return { error: "damaged" };
      if (entry.value !== null && !ANSWERS.includes(entry.value)) return { error: "damaged" };
      const prefill = entry.prefill ? readPrefill(entry.prefill) : null;
      if (entry.prefill && !prefill) return { error: "damaged" };
      items[id] = Object.assign({ origin: "shared" }, entry.value ? { value: entry.value } : {}, prefill ? { prefill } : {});
    }
    const state = { mode: data.mode, profile: data.profile, extended: true, target: webUrl(data.target), items };
    if (isText(data.pid, 300)) state.pid = data.pid;
    if (isText(data.nkr, 100) && /^[\w.:-]+$/.test(data.nkr)) state.nkr = data.nkr;
    if (isText(data.re3data, 20) && /^r3d\d{9}$/.test(data.re3data)) state.re3data = data.re3data;
    if (isText(data.fip, 100) && /^[\w.-]+$/.test(data.fip)) state.fip = data.fip;
    if (data.targetInfo && typeof data.targetInfo === "object") {
      const info = {};
      for (const key of ["name", "creators", "publisher", "year", "kind", "url"]) if (isText(String(data.targetInfo[key] || ""), 300) && data.targetInfo[key]) info[key] = String(data.targetInfo[key]);
      if (info.url && !webUrl(info.url)) delete info.url;
      if (info.name || info.publisher) state.targetInfo = info;
    }
    return { check, state, notices: loadNotices(skipped, isText(data.guideVersion, 40) ? data.guideVersion : null) };
  };

  /** Text as base64 of its UTF-8 bytes and back, for the state the Markdown summary carries in a comment. */
  function toBase64(text) {
    let binary = "";
    for (const byte of new TextEncoder().encode(text)) binary += String.fromCharCode(byte);
    return btoa(binary);
  }

  function fromBase64(text) {
    const binary = atob(text.replace(/\s+/g, ""));
    return new TextDecoder("utf-8", { fatal: true }).decode(Uint8Array.from(binary, (char) => char.charCodeAt(0)));
  }

  /** Read a file the guide exported, the JSON-LD result set or the Markdown summary, or say why it cannot be read. */
  function readResultFile(text) {
    let crate = null;
    try {
      crate = JSON.parse(text);
    } catch (error) {
      crate = null;
    }
    if (crate && typeof crate === "object") {
      const holder = FG.list(crate["@graph"]).find((entity) => entity && typeof entity.guideState === "string");
      if (!holder) return { error: "notGuide" };
      try {
        return SC.readPortable(JSON.parse(holder.guideState));
      } catch (error) {
        return { error: "damaged" };
      }
    }
    const match = String(text).match(/<!--\s*fair-guide-result(?:\s+v(\d+))?(?:\s+guide=(\S+?))?:\s*([a-z-]+)\s+(a\d+\.[A-Za-z0-9._]+)\s*-->/);
    if (!match) return { error: "notGuide" };
    if (Number(match[1] || FORMAT_VERSION) > FORMAT_VERSION) return { error: "newer", params: { version: match[2] || "?" } };
    const check = FG.get("#check-" + match[3]);
    if (!check) return { error: "unknownCheck" };
    const carried = String(text).match(/<!--\s*fair-guide-state\b([\s\S]*?)-->/);
    if (carried) {
      let data = null;
      try {
        data = JSON.parse(fromBase64(carried[1]));
      } catch (error) {
        return { error: "damaged" };
      }
      if (!data || data.check !== check.identifier) return { error: "damaged" };
      return SC.readPortable(data);
    }
    /* A summary without the state (an older guide) gives the answers only. */
    const state = SC.parseShare(check, match[4]);
    if (!state) return { error: "damaged" };
    return { check, state, notices: loadNotices(state.skipped, match[2] || null) };
  }

  /** A file the user loads opens as a preview of its check, like a shared link. */
  async function loadFile(file, statusId) {
    const show = (key, params) => {
      const element = document.getElementById(statusId);
      if (element) element.textContent = FG.t(key, params || {});
    };
    if (!file) return;
    if (file.size > MAX_FILE) {
      show("selfcheck.load.error.tooLarge");
      return;
    }
    const found = readResultFile(await file.text());
    if (found.error) {
      show("selfcheck.load.error." + found.error, found.params);
      return;
    }
    SC.pendingFile = { check: found.check.identifier, state: found.state, notices: found.notices || [] };
    FG.navigate(FG.href("check", found.check.identifier) + "/file");
  }

  function loadControl(id) {
    const statusId = id + "-status";
    return h(
      "div",
      { class: "load-file no-print" },
      h("input", { type: "file", id, class: "file-input", accept: ".jsonld,.json,.md,application/ld+json,application/json,text/markdown", onchange: (event) => loadFile(event.target.files[0], statusId) }),
      h("label", { for: id, class: "button button-small" }, FG.icon("upload"), FG.t("selfcheck.load.label")),
      h("span", { class: "small muted" }, FG.t("selfcheck.load.hint")),
      h("p", { id: statusId, class: "small", role: "status" })
    );
  }

  /** What the guide keeps in the browser, said in one sentence, with how it works and a control to delete it all. */
  function localDataNote() {
    const remove = () => {
      if (!window.confirm(FG.t("localData.confirm"))) return;
      FG.clearStoredData();
      SC.pendingFile = null;
      FG.rerender("local-data-delete");
      const element = document.getElementById("local-data-status");
      if (element) element.textContent = FG.t("localData.deleted");
    };
    return h(
      "div",
      { class: "local-data no-print" },
      FG.icon("info", { class: "local-data-icon" }),
      h(
        "div",
        { class: "local-data-main" },
        h("p", { class: "local-data-line" }, FG.t("localData.statement")),
        h(
          "div",
          { class: "local-data-actions" },
          h(
            "details",
            { class: "local-data-how" },
            h("summary", null, FG.t("localData.how")),
            h(
              "div",
              { class: "content" },
              h("ul", null, ["stored", "where", "sent", "move", "delete"].map((key) => h("li", null, h("strong", null, FG.t("localData." + key + "Title") + ": "), FG.t("localData." + key))))
            )
          ),
          h("button", { type: "button", id: "local-data-delete", class: "local-data-delete", onclick: remove }, FG.icon("trash"), h("span", null, FG.t("localData.deleteAll")))
        ),
        h("p", { id: "local-data-status", class: "small", role: "status" })
      )
    );
  }

  function download(name, text, type) {
    const blob = new Blob([text], { type: type + ";charset=utf-8" });
    /* A blob link made here from the user's own result; FG.h would refuse its scheme, so the element is built directly. */
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  const fileName = (check, extension) => "fair-self-check-" + check.identifier + "-" + today() + "." + extension;

  SC.sharePayload = function (check, st) {
    const parts = ["a1", st.mode || "_", st.profile || "_"];
    for (const item of itemsOf(check)) {
      const value = answerOf(st, item);
      if (value) parts.push(item.identifier + SHARE_CODE[value]);
    }
    return parts.join(".");
  };

  /** Read the answers in a shared link; questions this version does not know are skipped and counted, anything
      else unexpected makes the whole link invalid. */
  SC.parseShare = function (check, payload) {
    const parts = String(payload || "").split(".");
    if (parts[0] !== "a1" || parts.length < 3) return null;
    const codes = Object.fromEntries(Object.entries(SHARE_CODE).map(([value, letter]) => [letter, value]));
    const ids = new Set(itemsOf(check).map((item) => item.identifier));
    const shared = { mode: null, profile: null, extended: true, items: {}, skipped: 0 };
    if (parts[1] !== "_") {
      if (!modesOf(check).some((term) => term.termCode === parts[1])) return null;
      shared.mode = parts[1];
    }
    if (parts[2] !== "_") {
      if (!profilesOf(check).some((term) => term.termCode === parts[2])) return null;
      shared.profile = parts[2];
    }
    for (const part of parts.slice(3)) {
      const match = part.match(/^([A-Z]\d{2})([a-z])$/);
      if (!match || !codes[match[2]]) return null;
      if (!ids.has(match[1])) {
        shared.skipped += 1;
        continue;
      }
      shared.items[match[1]] = { value: codes[match[2]], origin: "shared" };
    }
    return shared;
  };

  function shareUrl(check, st) {
    const base = /^https?:$/.test(window.location.protocol) ? window.location.href.split("#")[0] : pageBase();
    return base + FG.href("check", check.identifier) + "/" + SC.sharePayload(check, st);
  }

  async function copy(text, fallbackId) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (error) {
      const field = document.getElementById(fallbackId);
      if (field) {
        field.focus();
        field.select();
      }
      return false;
    }
  }

  function showShare(check, st) {
    const url = shareUrl(check, st);
    FG.renderList("share-output", () =>
      fragment(
        h("label", { for: "share-url" }, FG.t("selfcheck.export.shareLabel")),
        h("div", { class: "inline" }, h("input", { id: "share-url", type: "text", readonly: true, value: url }), h("button", { type: "button", onclick: (event) => copyWithFeedback(event, url, "share-url") }, FG.t("common.copy"))),
        h("p", { class: "small" }, FG.t("selfcheck.export.shareNote"))
      )
    );
    const field = document.getElementById("share-url");
    if (field) field.focus();
  }

  async function copyWithFeedback(event, text, fallbackId) {
    const button = event.currentTarget;
    if (await copy(text, fallbackId)) button.textContent = FG.t("common.copied");
  }

  /* The format chosen for saving, kept while the page is open. */
  let exportFormat = "md";
  const exportText = (check, st) => (exportFormat === "jsonld" ? JSON.stringify(SC.ftrCrate(check, st), null, 2) + "\n" : markdown(check, st));

  function refreshPreview(check, st) {
    const area = document.getElementById("export-preview-text");
    if (area && area.closest("details").open) area.value = exportText(check, st);
  }

  function clearAnswers(check) {
    if (!window.confirm(FG.t("selfcheck.reset") + "?")) return;
    delete FG.state.answers[check.identifier];
    save();
    FG.rerender("export-title");
  }

  function exportSection(check, st) {
    return h(
      "section",
      { class: "export no-print", "aria-labelledby": "export-title" },
      h("h2", { id: "export-title", tabindex: "-1" }, FG.t("selfcheck.export.title")),
      h(
        "fieldset",
        { class: "export-format" },
        h("legend", null, FG.t("selfcheck.export.format")),
        [
          ["md", "selfcheck.export.formatMd"],
          ["jsonld", "selfcheck.export.formatJsonld"],
        ].map(([value, key]) =>
          h(
            "label",
            { class: "option", for: "export-format-" + value },
            h("input", {
              type: "radio",
              name: "export-format",
              id: "export-format-" + value,
              value,
              checked: exportFormat === value,
              onchange: () => {
                exportFormat = value;
                refreshPreview(check, st);
              },
            }),
            FG.t(key)
          )
        )
      ),
      h(
        "div",
        { class: "export-actions" },
        h(
          "button",
          {
            type: "button",
            class: "button-small button-primary",
            id: "export-download",
            onclick: () => download(fileName(check, exportFormat === "jsonld" ? "jsonld" : "md"), exportText(check, st), exportFormat === "jsonld" ? "application/ld+json" : "text/markdown"),
          },
          FG.icon("download"),
          FG.t("selfcheck.export.download")
        ),
        h("button", { type: "button", class: "button-small", id: "export-copy", onclick: (event) => copyWithFeedback(event, exportText(check, st), "export-preview-text") }, FG.icon("copy"), FG.t("common.copy"))
      ),
      h(
        "details",
        { class: "export-preview", ontoggle: (event) => event.target.open && refreshPreview(check, st) },
        h("summary", null, FG.t("selfcheck.export.preview")),
        h("textarea", { id: "export-preview-text", readonly: true, rows: "14", "aria-label": FG.t("selfcheck.export.preview") })
      ),
      h("p", { class: "small muted" }, FG.t("selfcheck.export.formats")),
      h(
        "div",
        { class: "export-more" },
        h("button", { type: "button", class: "button-small", id: "share-create", onclick: () => showShare(check, st) }, FG.icon("link"), FG.t("selfcheck.export.share")),
        h("button", { type: "button", class: "button-small", onclick: () => window.print() }, FG.icon("print"), FG.t("selfcheck.export.print"))
      ),
      h("div", { id: "share-output", class: "share-output" }),
      h("p", null, h("button", { type: "button", class: "button-link", onclick: () => clearAnswers(check) }, FG.t("selfcheck.reset")))
    );
  }

  /* ---------------------------------------------------------------- views */

  function sharedView(check, payload) {
    const fromFile = payload === "file";
    const pending = SC.pendingFile && SC.pendingFile.check === check.identifier ? SC.pendingFile.state : null;
    const shared = fromFile ? pending : SC.parseShare(check, payload);
    const notices = fromFile ? (SC.pendingFile && SC.pendingFile.notices) || [] : shared ? loadNotices(shared.skipped, null) : [];
    if (!shared) {
      return [
        h("p", { class: "notice", role: "status" }, FG.t(fromFile ? "selfcheck.load.gone" : "selfcheck.export.sharedInvalid")),
        h("p", null, h("a", { class: "button", href: FG.href("check", check.identifier) }, FG.t("selfcheck.export.keepOwn"))),
      ];
    }
    const use = () => {
      FG.state.answers[check.identifier] = shared;
      SC.pendingFile = null;
      save();
      FG.navigate(FG.href("check", check.identifier));
    };
    return [
      h(
        "div",
        { class: "notice shared" },
        h("p", null, FG.t(fromFile ? "selfcheck.load.banner" : "selfcheck.export.sharedBanner")),
        notices.map((notice) => h("p", { class: "small" }, notice)),
        h(
          "div",
          { class: "buttons" },
          h("button", { type: "button", class: "button-primary", onclick: use }, FG.t(fromFile ? "selfcheck.load.use" : "selfcheck.export.useShared")),
          h("a", { class: "button", href: FG.href("check", check.identifier) }, FG.t("selfcheck.export.keepOwn"))
        )
      ),
      h("section", { class: "results", "aria-labelledby": "results-title" }, h("h2", { id: "results-title" }, FG.t("selfcheck.result.title")), results(check, shared)),
    ];
  }

  /** Move to a place in the check and give it focus without a second scroll. */
  /** Move to a place in the check, give it focus and mark it briefly, so the jump is visible even when the place
      was already in view. */
  function jumpTo(element) {
    if (!element) return;
    element.scrollIntoView({ block: "start" });
    const target = element.matches("input, button, h2, h3") ? element : element.querySelector("input, h2, h3") || element;
    target.focus({ preventScroll: true });
    element.classList.add("jumped");
    setTimeout(() => element.classList.remove("jumped"), 1600);
  }

  /** Jump to an item; an item the short view hides opens the extended view first. */
  function jumpToItem(check, item) {
    const st = stateOf(check);
    if (!document.getElementById("item-" + item.identifier) && !st.extended) {
      st.extended = true;
      save();
      FG.rerender();
    }
    jumpTo(document.getElementById("item-" + item.identifier));
  }

  /** The questions in the same groups as the list, with a short label for each group. */
  function summaryGroups(items) {
    return groupsOf(items).map((group) => ({ label: groupMark(group), name: groupName(group), items: group.items }));
  }

  /** The result so far in a few lines: progress, one chip per question in the list's groups that jumps to it,
      and the counts of gaps and things to find out that jump to the full result below the questions. */
  function summary(check, st) {
    const items = resultItems(check, st);
    const answered = items.filter((item) => answerOf(st, item)).length;
    const { gaps, tasks } = outcomes(check, st);
    /* The summary mirrors the questions: the same groups as the list (by principle or by path step), one chip per
       question with its answer state. */
    const shown = applicable(check, st).filter((item) => providedByNrp(item, st) || items.includes(item));
    const groups = summaryGroups(shown);
    const count = (key, n, anchor) =>
      n
        ? h("button", { type: "button", class: "summary-count", "data-kind": key, onclick: () => jumpTo(document.getElementById(anchor)) }, FG.t("selfcheck.summary." + key, { n }))
        : h("span", { class: "summary-count summary-count-none", "data-kind": key }, FG.t("selfcheck.summary." + key, { n }));
    return [
      h("p", { class: "summary-progress" }, FG.t("selfcheck.progress", { n: answered, total: items.length })),
      groups.map((group) =>
        h(
          "div",
          { class: "summary-group" },
          h("span", { class: "summary-group-label" }, group.label),
          h(
            "ul",
            { class: "summary-chips", "aria-label": group.name },
            group.items.map((item) => {
              const state = itemState(st, item);
              const name = FG.text(item.text);
              return h(
                "li",
                null,
                h(
                  "button",
                  { type: "button", class: "summary-chip", "data-state": state, title: name + " (" + FG.t("selfcheck.state." + state) + ")", onclick: () => jumpToItem(check, item) },
                  state === "open" ? null : h("span", { "aria-hidden": "true" }, STATE_ICON[state] + " "),
                  item.identifier,
                  h("span", { class: "visually-hidden" }, " " + name + ": " + FG.t("selfcheck.state." + state))
                )
              );
            })
          )
        )
      ),
      h("p", { class: "summary-counts" }, count("gaps", gaps.length, "results-gaps"), count("tasks", tasks.length, "results-tasks")),
      h("p", { class: "summary-full" }, h("button", { type: "button", class: "button-link", onclick: () => jumpTo(document.getElementById("results-title")) }, FG.t("selfcheck.summary.full"))),
    ];
  }

  /** The result so far beside the questions; a small icon collapses it, and the choice is remembered. */
  function summaryPanel(check, st) {
    const collapsed = Boolean(FG.state.resultCollapsed);
    const toggle = () => {
      FG.state.resultCollapsed = !collapsed;
      FG.saveState();
      FG.rerender("result-toggle");
    };
    const label = FG.t(collapsed ? "selfcheck.result.show" : "selfcheck.result.hide");
    return h(
      "aside",
      { class: "check-summary no-print", "aria-labelledby": "summary-title" },
      h(
        "div",
        { class: "summary-head" },
        h("h2", { id: "summary-title", class: collapsed ? "visually-hidden" : null }, FG.t("selfcheck.summary.title")),
        h(
          "button",
          { type: "button", class: "icon-button", id: "result-toggle", "aria-expanded": String(!collapsed), "aria-controls": "result-body", "aria-label": label, title: label, onclick: toggle },
          FG.icon(collapsed ? "expand" : "collapse")
        )
      ),
      h(
        "div",
        { id: "result-body", hidden: collapsed },
        controlsInSummary() ? h("div", { class: "summary-controls" }, checkControls(check, st, true)) : null,
        h("div", { id: "summary-body" }, summary(check, st))
      )
    );
  }

  function checkView(route) {
    const check = FG.get("#check-" + route.arg);
    const minutes = String(check.timeRequired || "").replace(/\D/g, "");
    const head = [
      h("p", { class: "muted" }, h("a", { href: FG.href("selfcheck") }, FG.t("selfcheck.title"))),
      FG.heading(1, null, FG.span(check.name)),
      FG.paragraphs(check.description),
      minutes ? h("p", { class: "muted" }, FG.t("station.minutes", { n: minutes })) : null,
      route.extra ? null : localDataNote(),
    ];
    if (route.extra) return h("div", { class: "layout wrap selfcheck" }, h("article", null, head, sharedView(check, route.extra)));
    const st = stateOf(check);
    if (!ready(check, st)) {
      return h(
        "div",
        { class: "layout wrap selfcheck" },
        h("article", null, head, h("div", { class: "no-print" }, settings(check, st)), h("p", { class: "notice" }, FG.t("selfcheck.chooseFirst")), startPanel(check, st, false))
      );
    }
    return h(
      "div",
      { class: "wrap selfcheck check-view" },
      h("header", { class: "check-head" }, head),
      h(
        "div",
        { class: "check-split" + (FG.state.resultCollapsed ? " result-collapsed" : "") },
        h(
          "article",
          { class: "check-main" },
          h("div", { class: "no-print" }, settings(check, st)),
          startPanel(check, st, true),
          itemsSection(check, st),
          h(
            "section",
            { class: "results", "aria-labelledby": "results-title" },
            h("h2", { id: "results-title", tabindex: "-1" }, FG.t("selfcheck.result.title")),
            h("div", { id: "results" }, results(check, st))
          ),
          exportSection(check, st)
        ),
        summaryPanel(check, st)
      )
    );
  }

  /** How many questions a check asks: a range when its mode or profile decides, one number otherwise. */
  function questionCount(check) {
    const choices = modesOf(check).map((term) => ({ mode: term.termCode })).concat(profilesOf(check).map((term) => ({ profile: term.termCode })));
    const counts = (choices.length ? choices : [{}]).map((choice) => itemsOf(check).filter((item) => applies(item, Object.assign({ mode: null, profile: null }, choice))).length);
    const low = Math.min(...counts);
    const high = Math.max(...counts);
    return low === high ? FG.t("selfcheck.items", { n: low }) : FG.t("selfcheck.itemsRange", { low, high });
  }

  /** A check as a card: its icon and name, what it is for, how long it takes and for whom, progress once started. */
  function checkCard(check) {
    const st = hasState(check) ? stateOf(check) : null;
    const total = st ? answerable(check, st).length : 0;
    const answered = st ? answerable(check, st).filter((item) => answerOf(st, item)).length : 0;
    const minutes = String(check.timeRequired || "").replace(/\D/g, "");
    const icon = FG.config.icons && FG.config.icons.check && FG.config.icons.check[check.identifier];
    const name = FG.text(check.name);
    const meta = [
      minutes ? FG.t("station.minutes", { n: minutes }) : null,
      questionCount(check),
      FG.refs(check, "audience")
        .map((lens) => FG.text(lens.name))
        .join(", "),
    ].filter(Boolean);
    return h(
      "li",
      { class: "check-card" },
      h("div", { class: "check-card-head" }, FG.icon(icon, { class: "check-card-icon" }), h("h3", null, FG.span(check.name))),
      FG.paragraphs(check.description),
      h("p", { class: "check-card-meta" }, meta.join(" · ")),
      answered
        ? h(
            "div",
            { class: "check-progress" },
            h("progress", { max: String(total), value: String(answered), "aria-label": FG.t("selfcheck.progress", { n: answered, total }) }),
            h("span", null, FG.t("selfcheck.progress", { n: answered, total }))
          )
        : null,
      h(
        "p",
        { class: "check-card-action" },
        h(
          "a",
          { class: "button button-small" + (answered ? "" : " button-primary"), href: FG.href("check", check.identifier) },
          FG.t(answered ? "selfcheck.continueShort" : "selfcheck.startShort"),
          h("span", { class: "visually-hidden" }, ": " + name)
        )
      )
    );
  }

  /** The self-check overview: what it does in three steps, the checks for the current lens and the others, and a
      place to load a saved result. */
  function overview(route) {
    const checks = SC.checks();
    const mine = checks.filter((check) => FG.hasRef(check, "audience", "#lens-" + route.lens));
    const others = checks.filter((check) => !mine.includes(check));
    const steps = ["selfcheck.steps.choose", "selfcheck.steps.answer", "selfcheck.steps.result"];
    return h(
      "div",
      { class: "layout wrap selfcheck-overview" },
      h(
        "article",
        null,
        FG.heading(1, null, FG.t("selfcheck.title")),
        h("p", { class: "lead" }, FG.t("selfcheck.intro")),
        h(
          "ol",
          { class: "how-steps" },
          steps.map((key, index) => h("li", null, h("span", { class: "how-step-number" }, String(index + 1)), h("span", null, FG.t(key))))
        ),
        h("h2", null, FG.t("selfcheck.forLens")),
        h("ul", { class: "check-cards" }, mine.map(checkCard)),
        others.length ? [h("h2", null, FG.t("selfcheck.others")), h("ul", { class: "check-cards" }, others.map(checkCard))] : null,
        h(
          "section",
          { class: "saved-results", "aria-labelledby": "saved-title" },
          h("h2", { id: "saved-title" }, FG.t("selfcheck.savedTitle")),
          h("p", null, FG.t("selfcheck.savedText")),
          loadControl("load-file-overview"),
          localDataNote()
        )
      )
    );
  }

  FG.views.selfcheck = function (route) {
    return route.view === "check" && FG.get("#check-" + route.arg) ? checkView(route) : overview(route);
  };
})();
