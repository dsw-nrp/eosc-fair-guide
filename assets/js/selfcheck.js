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
  const FIRST_TIERS = ["#tier-required", "#tier-standard", "#tier-basic", "#tier-minimum"];
  const TIER_ORDER = ["#tier-required", "#tier-standard", "#tier-basic", "#tier-minimum", "#tier-recommended", "#tier-advanced"];
  const ANSWER_STATE = { yes: "met", partly: "partly", no: "gap", unknown: "unknown" };
  const STATE_ICON = FG.STATE_ICON;
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
  /* Revision 3 adds attached evaluator assessments; files without them are still written as revision 2. */
  const FORMAT_VERSION = 3;
  const OBSERVATION_MAX = 8;
  const VALUE_MAX = 65536;
  const EVIDENCE_MAX = 131072;
  const LOG_MAX = 65536;
  /* A saved result file: answers and evidence, and in a complete evidence download up to a few original evaluator
     reports, each within the providers' import limit. */
  const MAX_FILE = 8 * 1024 * 1024;
  const SOURCES = ["datacite", "resolver", "nkr", "re3data", "fip-dashboard", "fip-dashboard-snapshot", "nanopub", "champion", "shared", "landing", "pid-record", "github", "gitlab", "fair-checker", "f-uji"];
  const NOTE_KEYS = ["partlyOnly", "notInSource", "noDeclaration", "resolves", "notResolved", "lookupFailed", "stewardFound", "stewardMissing", "stewardRole", "stewardOrcid", "partialCoverage", "sourceConflict", "representation", "repositoryScope", "profileDeclaration", "unsupportedPid", "sampleCoverage", "titleMeaning", "rightsCoverage", "classificationScheme", "descriptionCoverage", "creatorIdentifiers", "keywordScheme", "pidProfile", "commitVersion", "copyrightCoverage", "bundledLicences", "testsNotRun", "dependenciesCoverage", "testUnavailable", "providerUnavailable", "providerVersion", "providerFail", "providerUnknown", "providerBlank", "providerMapping", "providerHarvest"];
  const LENS_ACTOR = { V: "#actor-researcher", DS: "#actor-data-steward", SR: "#actor-repository-admin", K: "#actor-community" };
  /* The last thing a run reported, and the part it was reported on: the answers part shows only what was reported
     there, so a note left by the evidence does not stay pinned above the questions. */
  const status = { check: null, part: null, text: "", busy: false };

  /* ---------------------------------------------------------------- knowledge base */

  SC.checks = () => FG.ofType("Quiz");
  const itemsOf = (check) => FG.refs(check, "hasPart").sort(FG.byPosition);
  /* A question's ID is its check's ID and its number (dataset.04): inside its check it shows by its number, and the
     page's elements are keyed by the ID with a hyphen for the dot, so selectors need no escaping. */
  const numberOf = (item) => String(item.identifier).split(".").pop();
  const keyOf = (item) => String(item.identifier).replace(/\./g, "-");

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
    /* A check with a default profile, such as no funding programme, starts with it. */
    if (!entry.profile && check.defaultProfile) entry.profile = (FG.get(check.defaultProfile) || {}).termCode;
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
  const answerable = (check, st) => applicable(check, st).filter((item) => !providedByNrp(item, st) && !item.assessmentContext);
  /** The items a result covers: those the first view shows, every item once the check is extended, and any item
      the user has answered, so an answer to an extended item counts after the view returns to the basic items. */
  /** The questions the check covers now: the first tier, or every tier once the extended check is on. The list, the
      running result, the report, the counts of what is missing and the path's marks all follow it; answers to the
      other questions stay saved and are counted aside (`hiddenAnswers`). */
  function resultItems(check, st) {
    const items = answerable(check, st);
    if (st.extended || !items.some(isFirstTier)) return items;
    return items.filter(isFirstTier);
  }

  /** Saved answers to questions the short check leaves out, with the way to bring them back; none when there are
      none. */
  function hiddenAnswers(check, st) {
    const shown = new Set(resultItems(check, st));
    const n = answerable(check, st).filter((item) => !shown.has(item) && answerOf(st, item)).length;
    if (!n) return null;
    return h(
      "p",
      { class: "small hidden-answers" },
      FG.t("selfcheck.hidden.answers", { n }),
      " ",
      h("button", { type: "button", class: "button-link", onclick: () => { st.extended = true; save(); FG.rerender(); } }, FG.t("selfcheck.hidden.show"))
    );
  }

  const byTier = (a, b) => TIER_ORDER.indexOf(FG.id(a.tier)) - TIER_ORDER.indexOf(FG.id(b.tier)) || FG.byPosition(a, b);

  /** Gaps (no, partly) and tasks (don't know), ordered by tier. */
  function outcomes(check, st) {
    const gaps = [];
    const tasks = [];
    for (const item of resultItems(check, st)) {
      const value = answerOf(st, item);
      if (value === "no" || value === "partly") gaps.push(item);
      else if (value === "unknown") tasks.push(item);
    }
    return { gaps: gaps.sort(byTier), tasks: tasks.sort(byTier) };
  }

  /** Open self-check answers whose questions are put right at a station, by state (No, Partly, Don't know), across
      the checks of the current lens; the path's rail marks them with the self-check's own icons. */
  FG.openAt = function (stationId) {
    const counts = { gap: 0, partly: 0, unknown: 0 };
    for (const check of SC.checks()) {
      if (!FG.hasRef(check, "audience", "#lens-" + FG.state.lens) || !hasState(check)) continue;
      const st = stateOf(check);
      for (const item of resultItems(check, st)) {
        const state = ANSWER_STATE[answerOf(st, item)];
        if (state in counts && FG.id(item.fixAt) === "#station-" + stationId) counts[state] += 1;
      }
    }
    return counts;
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
    return FG.saveState();
  }

  function setAnswer(check, item, value) {
    const st = stateOf(check);
    st.items[item.identifier] = Object.assign({}, record(st, item) || {}, { value, origin: "user" });
    save();
    FG.renderList("origin-" + keyOf(item), () => fragment(originLine(st, item), withdrawControl(check, st, item)));
    const card = document.getElementById("item-" + keyOf(item));
    if (card) {
      card.dataset.state = itemState(st, item);
      card.dataset.origin = "user";
    }
    FG.renderList("results", () => fragment(results(check, st)));
    FG.renderList("summary-body", () => fragment(summary(check, st)));
    const note = document.getElementById("parts-answers-note");
    if (note) note.textContent = answersNote(check, st);
    refreshPreview(check, st);
    FG.renderList("share-output", () => fragment());
    if (exportGate && exportGate.isConnected) exportGate.refresh();
  }

  function setStatus(check, text) {
    status.check = check.identifier;
    status.part = partOf(FG.parseHash(window.location.hash));
    status.text = text;
    const element = document.getElementById("prefill-status");
    if (element) element.textContent = text;
  }

  /* Evidence that covers only part of its question carries the partial-coverage note (D-168); its suggestion is a
     lower bound, which evidence about the whole question outranks. */
  const partialOnly = (observation) => FG.list(observation.notes).some((note) => note && note.key === "selfcheck.note.partialCoverage");

  /** Record the evidence of one source for every item it can answer. A pre-filled value never replaces an answer
      the user gave, and evidence without a value never hides an earlier source's suggestion. Evidence about the whole
      question outranks partial evidence whatever their order; Yes against No, or No about the whole question against
      a part found met, is a disagreement the reader settles. */
  function applyEvidence(check, source, evidence, date, recordUrl, direct) {
    const st = stateOf(check);
    let filled = 0;
    for (const item of answerable(check, st)) {
      const entry = prefillOf(item, source);
      if (!entry && !direct) continue;
      const result = evidence(item, FG.list(entry && entry.value));
      if (!result) continue;
      let value = result.value || null;
      const notes = (result.notes || []).slice();
      if (value === "yes" && item.prefillLevel === "partly") {
        value = "partly";
        notes.push({ key: "selfcheck.note.partlyOnly" });
      }
      const current = record(st, item) || {};
      const observation = readPrefill({ source: result.source || source, date: result.date || date, value, notes, list: result.list || [], fields: result.fields || [], record: result.record || recordUrl || null, subject: result.subject || stateOf(check).target || null, representation: result.representation || null, commit: result.commit || null, coverage: result.coverage || null, testId: result.testId || null, assessment: result.assessment || null });
      if (!observation) continue;
      const previous = observationsOf(current);
      /* One observation per source, record, subject, representation and assessment: a newer report from the same
         provider is another observation, so historical assessments stay distinguishable. */
      const identity = (seen) => [seen.source, seen.record, seen.subject, seen.representation, seen.assessment || ""].join("|");
      const observations = previous.filter((seen) => identity(seen) !== identity(observation)).concat(observation).slice(-OBSERVATION_MAX);
      const supported = observations.filter((seen) => seen.value);
      const whole = supported.filter((seen) => !partialOnly(seen));
      const conflict =
        (supported.some((seen) => seen.value === "yes") && supported.some((seen) => seen.value === "no")) ||
        (whole.some((seen) => seen.value === "no") && supported.some((seen) => partialOnly(seen) && seen.value === "partly"));
      const chosen = conflict ? observation : whole[whole.length - 1] || supported[supported.length - 1] || observation;
      const prefill = Object.assign({}, chosen, conflict ? { value: null, notes: chosen.notes.concat({ key: "selfcheck.note.sourceConflict" }) } : {});
      const next = Object.assign({}, current, { prefill, observations });
      value = prefill.value;
      if (current.origin !== "user" && value) Object.assign(next, { value, origin: "prefill" });
      else if (current.origin !== "user") delete next.value;
      else if (!current.origin) next.origin = "prefill";
      st.items[item.identifier] = next;
      if (value) filled += 1;
    }
    save();
    return filled;
  }

  /** Older saved answers have one pre-fill record; treat it as an observation without fabricating history. */
  function observationsOf(entry) {
    if (!entry) return [];
    return Array.isArray(entry.observations) ? entry.observations.slice(-OBSERVATION_MAX) : entry.prefill ? [entry.prefill] : [];
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
      return key ? summarise(value[key]) : JSON.stringify(value).slice(0, VALUE_MAX);
    }
    const text = String(value).replace(/\s+/g, " ").trim();
    return text.slice(0, VALUE_MAX);
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
        return values.length ? { path, values: values.slice(0, 8), more: Math.max(0, values.length - 8) } : null;
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
      else {
        delete entry.prefill;
        delete entry.observations;
      }
    }
  }

  /** Evidence describes one dataset, repository or profile; choosing another discards what the previous one gave. */
  function retarget(check, target) {
    const st = stateOf(check);
    if (st.target !== target) {
      delete st.targetInfo;
      /* A run or report preview prepared for another target, or before there was one, no longer applies. */
      if (providers) providers.forget(check);
    }
    if (st.target && st.target !== target) {
      dropEvidence(st);
      delete st.champion;
      delete st.verdicts;
      dropAssessments(check, st);
    }
    st.target = target;
    save();
  }

  /** Optional evaluator assessments describe one object too: another target ends a running assessment, whose late
      results are then ignored, and discards the attached ones with their retained reports. */
  function dropAssessments(check, st) {
    delete st.assessments;
    if (providers) providers.forget(check);
    if (FG.providers) FG.providers.pruneSources();
  }

  /** Clear an identifier together with the answers it pre-filled; answers the user gave stay. */
  function clearTarget(check, key, focusId) {
    const st = stateOf(check);
    delete st[key];
    dropEvidence(st);
    delete st.champion;
    delete st.verdicts;
    delete st.target;
    delete st.targetInfo;
    delete st.inspection;
    dropAssessments(check, st);
    if (key === "software") delete st.softwareRef;
    save();
    setStatus(check, FG.t("selfcheck.prefill.cleared"));
    FG.rerender(focusId);
  }

  /** An identifier field with a visible control that clears it with the answers it pre-filled. */
  function clearableField(check, input, key, focusId) {
    const clear = h(
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
    );
    const field = h("span", { class: "field-clearable" }, input, clear);
    field.clear = clear;
    return field;
  }

  /** Whether a check holds anything an identifier pre-filled or retained, which clearing it removes. */
  function hasPrefill(st) {
    return Boolean(st.target || st.inspection || st.champion || st.verdicts || FG.list(st.assessments).length ||
      Object.values(st.items || {}).some((entry) => entry && typeof entry === "object" && (entry.origin === "prefill" || entry.prefill || entry.observations)));
  }

  /** An identifier field with its run button: the button waits for an identifier, and the field's clear control waits
      for an identifier or for what one pre-filled; one visible reason explains both while they wait. */
  function identifierRow(check, input, key, focusId, run) {
    const st = stateOf(check);
    const field = clearableField(check, input, key, focusId);
    const typed = () => input.value.trim() !== "";
    const reason = FG.gate(run, FG.t("selfcheck.prefill.needsIdentifier"), typed, input);
    /* Whenever the clear control has nothing to clear, the button is waiting for an identifier too, so the one
       visible reason serves both. */
    const refreshClear = () => {
      const can = typed() || hasPrefill(st);
      field.clear.disabled = !can;
      if (can) field.clear.removeAttribute("aria-describedby");
      else field.clear.setAttribute("aria-describedby", reason.id);
    };
    input.addEventListener("input", refreshClear);
    refreshClear();
    return [h("div", { class: "inline" }, field, run), reason];
  }

  async function runPrefill(check, source, focusId, work) {
    if (status.busy) return;
    status.busy = true;
    /* The run reports in the evidence card whose control started it, so its status and progress are seen there. */
    const started = document.getElementById(focusId);
    const card = started && started.closest(".evidence-card");
    status.card = card ? card.dataset.source : null;
    const body = card && card.querySelector(".evidence-body");
    for (const id of ["prefill-status", "prefill-progress"]) {
      const node = document.getElementById(id);
      if (body && node && node.closest(".evidence-card") !== card) body.append(node);
    }
    setStatus(check, FG.t("selfcheck.prefill.working", { source: label(source) }));
    const messages = [];
    let count = 0;
    try {
      count = await work(messages);
    } catch (error) {
      messages.push(FG.t("selfcheck.prefill.failed", { source: label(source) }));
    } finally {
      status.busy = false;
    }
    const done = count || !messages.length ? [FG.t("selfcheck.prefill.done", { source: label(source), n: count })] : [];
    setStatus(check, done.concat(messages).join(" "));
    FG.rerender(focusId);
  }

  const prefillFromPid = (...args) => loadInspection().then(() => inspection.prefillFromPid(...args));

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
    st.fip = FG.sourceIdentifier(fip, "fip-dashboard");
    retarget(check, FG.id(fip.sameAs) || fip.url || null);
    describeTarget(check, { name: [fip.alternateName, FG.text(fip.name)].filter(Boolean).join(": "), kind: "FIP" });
    const source = FG.live.available("fip-dashboard") ? "fip-dashboard" : "fip-dashboard-snapshot";
    return runPrefill(check, source, "prefill-fip-run", async (messages) => {
      let evidenceSource = "fip-dashboard-snapshot";
      let declarations = snapshotDeclarations(fip);
      let date = (FG.get("#snapshot-fip-dashboard") || {}).dateCreated;
      if (source === "fip-dashboard") {
        try {
          const data = await FG.live.dashboard();
          const current = data.fips.find((item) => item && item.id === FG.sourceIdentifier(fip, "fip-dashboard"));
          const names = new Map(data.resources.map((item) => [item && item.id, item]));
          if (current) {
            evidenceSource = "fip-dashboard";
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
      return applyEvidence(check, "fip", (item, questions) => Object.assign(fipEvidence(questions, declarations, "principle"), { source: evidenceSource }), date, st.target);
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
    return runPrefill(check, "re3data", "prefill-re3data-run", async () => {
      /* Being in the re3data snapshot is being registered in re3data; FAIRsharing's record comes from its snapshot,
         which names the record of every repository the guide lists. Without that snapshot the question stays open
         rather than being answered from re3data alone. */
      const snapshot = FG.get("#snapshot-fairsharing");
      const failed = !snapshot;
      const fairsharing = FG.fairsharingRecord(id);
      const known = Object.assign({}, facts, { registries: ["re3data"].concat(fairsharing ? ["FAIRsharing"] : []) });
      return applyEvidence(
        check,
        "re3data",
        (item, fields) => {
          const asksFairsharing = fields.some((field) => /=FAIRsharing$/i.test(field));
          if (asksFairsharing && failed) return { value: null, notes: [{ key: "selfcheck.note.lookupFailed", params: { source: "FAIRsharing" } }] };
          const evidence = Object.assign(fieldEvidence(fields.map((field) => pathState(known, field))), { fields: fieldsOf(known, fields) });
          if (asksFairsharing) Object.assign(evidence, { date: snapshot.dateCreated, record: fairsharing || undefined });
          return evidence;
        },
        facts.date,
        st.target
      );
    });
  }

  /** Open a check from the landing's search, prepare its state, and run the lookup the user chose once the check is
      shown. */
  function startAt(checkId, prepare, run) {
    const check = FG.get("#check-" + checkId);
    if (!check) return;
    prepare(stateOf(check), check);
    const hash = FG.href("check", checkId);
    if (window.location.hash === hash) {
      FG.render();
      run(check);
    } else {
      window.addEventListener("hashchange", () => run(check), { once: true });
      FG.navigate(hash);
    }
  }

  /** The dataset check for a DOI or Handle. */
  SC.startWithPid = function (input) {
    const pid = FG.live.parsePid(input);
    if (!pid) return;
    startAt(
      "dataset",
      (st, check) => {
        st.mode = "after";
        st.pid = pid.value;
        retarget(check, FG.live.pidUrl(pid));
      },
      (check) => prefillFromPid(check, pid)
    );
  };

  /** The repository maturity check for a re3data record: an r3d identifier or address directly, a re3data DOI
      through doi.org. Resolves to whether the record was placed. */
  SC.startWithRe3data = async function (input) {
    const r3d = await FG.live.re3dataRecord(input);
    if (!r3d) return false;
    startAt(
      "maturity",
      (st) => {
        st.re3data = r3d;
        st.extended = true;
      },
      (check) => prefillFromRe3data(check, r3d)
    );
    return true;
  };

  /** The FIP completeness check for a published FIP nanopublication. */
  SC.startWithNanopub = function (code) {
    startAt(
      "fip",
      (st) => {
        st.extended = true;
      },
      (check) => prefillFromNanopub(check, code)
    );
  };

  /** The FIP completeness check for a profile of the FIP Dashboard snapshot; false when the snapshot has no such
      profile. */
  SC.startWithFip = function (id) {
    const fip = FG.refs(FG.get("#fips"), "hasPart").find((entry) => entry.identifier === id);
    if (!fip) return false;
    startAt(
      "fip",
      (st) => {
        st.extended = true;
      },
      (check) => prefillFromDashboard(check, fip)
    );
    return true;
  };

  /* ---------------------------------------------------------------- pieces */

  function stateLabel(state) {
    return h("span", { class: "state", "data-state": state }, h("span", { "aria-hidden": "true" }, STATE_ICON[state] + " "), FG.t("selfcheck.state." + state));
  }

  function noteText(note) {
    if (note.text) return localized(note.text);
    /* A reviewed provider mapping states its coverage in the crate, in the language shown. */
    if (note.key === "selfcheck.note.providerMapping" && FG.providers) return FG.providers.mappingNote(note.params);
    /* Tests are kept by identifier and named in the language shown. */
    const tests = FG.list(note.tests).map((id) => FG.text((FG.sourceEntity("fair-champion", id) || {}).name) || String(id));
    return FG.t(note.key, Object.assign({}, note.params || {}, tests.length ? { tests: tests.join(", ") } : {}));
  }

  /** The fields and values an answer was taken from, as "field = value" pairs. */
  const foundFields = (pre) => FG.list(pre.fields).filter((field) => field && FG.list(field.values).length);

  const FIELD_LABELS = {
    "rightsList[].rightsUri": "licence", "rightsList[].rights": "licence", "license": "licence", "licence": "licence",
    "titles[].title": "title", "title": "title", "name": "title", "description": "description", "descriptions[].description": "description",
    "creators[].name": "creators", "contributors[].name": "contributors", "identifier": "identifier", "doi": "identifier",
    "publicationYear": "publication", "datePublished": "publication", "dateModified": "modified", "version": "version",
    "subjects[].subject": "keywords", "keywords": "keywords", "files": "files", "dependencies": "dependencies", "type": "type", "profile": "profile"
  };
  const brief = (value, max = 150) => String(value).length > max ? String(value).slice(0, max - 1) + "…" : String(value);
  function licenceName(value) {
    try {
      const uri = new URL(value);
      if (uri.hostname !== "creativecommons.org") return null;
      const match = uri.pathname.match(/^\/licenses\/(by(?:-sa|-nc|-nd|-nc-sa|-nc-nd)?)\/(\d\.\d)(?:\/|$)/);
      if (match) return "CC " + match[1].toUpperCase() + " " + match[2];
      return /^\/publicdomain\/zero\/1\.0(?:\/|$)/.test(uri.pathname) ? "CC0 1.0" : null;
    } catch (error) { return null; }
  }
  const readableField = (field) => (FIELD_LABELS[field.path] ? FG.t("selfcheck.field." + FIELD_LABELS[field.path]) : field.path);
  const readableValue = (value) => licenceName(value) || String(value);
  const valueNode = (value, shorten) => webUrl(value) ? FG.external(value, shorten ? licenceName(value) || brief(value) : value) : shorten ? brief(value) : value;

  const observationBody = (...args) => inspection.observationBody(...args);
  const evidenceDetails = (...args) => inspection.evidenceDetails(...args);
  const originLine = (...args) => inspection.originLine(...args);
  const originRest = (...args) => inspection.originRest(...args);

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

  /** Whether the profile changes anything in the chosen mode: some item that names profiles applies to the mode. */
  function profilesMatter(check, st) {
    if (!check.defaultProfile) return true;
    return itemsOf(check).some((item) => {
      const refs = FG.refIds(item, "appliesTo");
      const modes = refs.filter((id) => id.startsWith("#mode-"));
      return refs.some((id) => id.startsWith("#profile-")) && (!modes.length || modes.includes("#mode-" + st.mode));
    });
  }

  /** Whether the data steward named for a funded output appears among the creators or contributors of a DataCite
      record: by their ORCID iD when given, otherwise only as a data curator or manager, which still needs checking. */
  function stewardEvidence(attributes, orcid) {
    const people = FG.list(attributes.creators).concat(FG.list(attributes.contributors));
    const idOf = (identifier) => FG.live.parseOrcid(identifier && identifier.nameIdentifier);
    const names = (list) => list.map((person) => person.name || [person.givenName, person.familyName].filter(Boolean).join(" ")).join(", ");
    if (orcid) {
      const found = people.filter((person) => FG.list(person.nameIdentifiers).some((identifier) => idOf(identifier) === orcid));
      return found.length
        ? { value: "yes", notes: [{ key: "selfcheck.note.stewardFound", params: { name: names(found) } }] }
        : { value: "no", notes: [{ key: "selfcheck.note.stewardMissing", params: { orcid } }] };
    }
    const curators = FG.list(attributes.contributors).filter((person) => ["DataCurator", "DataManager"].includes(person.contributorType));
    if (curators.length) return { value: "partly", notes: [{ key: "selfcheck.note.stewardRole", params: { names: names(curators) } }] };
    return { value: null, notes: [{ key: "selfcheck.note.stewardOrcid" }] };
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
      profiles.length && profilesMatter(check, st)
        ? radios("profile", FG.t("selfcheck.profileQuestion." + check.identifier), profiles.map((term) => [term.termCode, FG.text(term.name)]), st.profile, change("profile"))
        : null,
    ];
  }

  function sourcesOf(check, st) {
    const sources = new Set();
    for (const item of answerable(check, st)) for (const entry of FG.refs(item, "additionalProperty")) sources.add(String(entry.propertyID).replace("prefill:", ""));
    return sources;
  }

  /** Whether a question the check shows is answered by looking for the output's data steward. */
  const needsSteward = (check, st) =>
    answerable(check, st).some((item) => FG.refs(item, "additionalProperty").some((entry) => entry.propertyID === "prefill:datacite" && FG.list(entry.value).includes("@steward")));

  /** The data steward of a funded output, by ORCID iD, for the DataCite lookup to find among creators and contributors. */
  function stewardControl(check, st) {
    const input = h("input", { id: "prefill-steward", type: "text", autocomplete: "off", spellcheck: "false", value: st.steward || "", placeholder: "0000-0000-0000-0000" });
    input.addEventListener("change", () => {
      const orcid = FG.live.parseOrcid(input.value);
      st.steward = orcid || "";
      save();
      setStatus(check, orcid || !input.value.trim() ? "" : FG.t("selfcheck.prefill.stewardInvalid"));
    });
    return h(
      "div",
      { class: "prefill-row" },
      h("label", { for: "prefill-steward" }, FG.t("selfcheck.prefill.steward")),
      input,
      h("p", { class: "small muted" }, FG.t("selfcheck.prefill.stewardHint"))
    );
  }

  function pidControl(check, st) { return inspection.pidControl(check, st); }

  /* FAIR Champion runs the curated tests the check's questions name: on the dataset a check is about, once its
     identifier is looked up, or on a sample of a repository's records. A sample holds a few records of different
     types, since the platform's configuration rather than the record mostly decides the result. Each test shows at
     the questions it answers, where it can be run alone; the pre-fill panel runs them all. */
  const SAMPLE_MAX = 5;
  const VERDICTS = ["pass", "fail", "indeterminate"];
  const VERDICT_ICON = { pass: "✓", fail: "✗", indeterminate: "?", none: "–", partly: "◐", running: "…" };
  const sampleOf = (text) => [...new Set(String(text || "").split(/[\s,;]+/).map((value) => value.trim()).filter(Boolean))];
  const healthOf = (test) => (test ? FG.id(test.healthStatus) || test.healthStatus : null);
  const verdictKey = (test, record) => test + " " + record;
  /* Tests running now, by identifier, so each question's line can say so. */
  const running = new Set();

  /** Run tasks, at most `limit` at a time. */
  async function inBatches(tasks, limit) {
    const queue = tasks.slice();
    await Promise.all(Array.from({ length: Math.min(limit, queue.length) }, async () => { while (queue.length) await queue.shift()(); }));
  }

  /** A question's FAIR Champion tests; a test known to be unavailable is left out. */
  const testsOf = (item) =>
    FG.list((prefillOf(item, "champion") || {}).value)
      .map(String)
      .filter((id) => healthOf(FG.sourceEntity("fair-champion", id)) !== "unavailable");

  /** The FAIR Champion tests the check's questions name, each with the questions it answers, in the questions'
      order. */
  function championTests(check, st) {
    const pairs = new Map();
    for (const item of answerable(check, st)) {
      for (const id of testsOf(item)) {
        if (!pairs.has(id)) pairs.set(id, { id, test: FG.sourceEntity("fair-champion", id), items: [] });
        pairs.get(id).items.push(item);
      }
    }
    return [...pairs.values()];
  }

  /** Whether the check tests the one dataset it is about, rather than a sample of a repository's records. */
  const onDataset = (check, st) => {
    const sources = sourcesOf(check, st);
    return sources.has("datacite") || sources.has("resolver");
  };
  /** The identifiers the tests are given, as entered: the dataset looked up, or the sample. */
  const championInput = (check, st) => (onDataset(check, st) ? st.pid || "" : st.sample || "");
  /** The records a run of the tests would use: the dataset looked up above, or the repository's sample. */
  const championEntries = (check, st) => {
    const input = championInput(check, st);
    return onDataset(check, st) ? (FG.live.parsePid(input) ? [input] : []) : sampleOf(input);
  };
  /** Whether the tests can run: a dataset looked up, or a sample within its size. */
  const championReady = (check, st) => {
    const count = championEntries(check, st).length;
    return count > 0 && count <= (onDataset(check, st) ? 1 : SAMPLE_MAX);
  };
  /** The verdicts on the identifiers entered now; other identifiers start afresh. */
  const currentRun = (check, st) => (st.champion && st.champion.input === championInput(check, st) ? st.champion : null);
  const wasRun = (run, test) => Boolean(run) && run.records.some((record) => verdictKey(test, record) in run.verdicts);
  /** Of these tests, the runs still to do on the current records: never run, or without a result. */
  const pendingOf = (run, tests) =>
    tests.flatMap((test) => run.records.map((record) => [test, record])).filter(([test, record]) => !VERDICTS.includes((run.verdicts[verdictKey(test, record)] || {}).value));

  /** How far a long pre-fill has got, as a bar beside the status; the status itself announces only the start and
      the end, so a screen reader is not interrupted by every test. */
  function setProgress(done, total) {
    status.progress = total ? { done, total } : null;
    const box = document.getElementById("prefill-progress");
    if (!box) return;
    box.hidden = !total;
    const bar = box.querySelector("progress");
    bar.max = total || 1;
    bar.value = done;
    box.querySelector(".progress-count").textContent = total ? FG.t("selfcheck.prefill.progress", { done, total }) : "";
  }

  function progressBox() {
    const progress = status.busy && status.progress;
    return h(
      "div",
      { id: "prefill-progress", class: "prefill-progress", hidden: !progress },
      h("progress", { max: progress ? progress.total : 1, value: progress ? progress.done : 0, "aria-labelledby": "prefill-progress-count" }),
      h("span", { id: "prefill-progress-count", class: "progress-count small" }, progress ? FG.t("selfcheck.prefill.progress", progress) : "")
    );
  }

  function testState(run, test) { return inspection.testState(run, test); }

  /** Bring the lines of these tests up to date while a run goes on, without drawing the view again. */
  function showTests(check, st, tests) {
    const run = currentRun(check, st);
    for (const test of tests) for (const row of document.querySelectorAll(`.test-row[data-test="${CSS.escape(test)}"]`)) row.querySelector(".test-state").replaceWith(testState(run, test));
  }

  /** Run these tests on the identifiers entered, a few at a time, keeping every verdict; identifiers are resolved
      first, and one that does not resolve is not tested. Every question whose tests have results is then answered:
      Yes when every record with a pass or fail passed, Partly when some did, No when none did. A test without a
      result never counts as a failure, and the coverage is always stated. */
  async function runChampion(check, tests, focusId) {
    if (status.busy) return;
    const st = stateOf(check);
    const dataset = onDataset(check, st);
    const input = championInput(check, st);
    const entries = championEntries(check, st);
    if (!entries.length || entries.length > (dataset ? 1 : SAMPLE_MAX)) {
      setStatus(check, FG.t(dataset ? "selfcheck.prefill.championNeedsPid" : "selfcheck.prefill.championInvalid", { n: SAMPLE_MAX }));
      return;
    }
    const notices = [];
    let run = currentRun(check, st);
    if (!run) {
      const { records, unresolved } = await resolvedTargets(check, entries);
      if (unresolved.length) notices.push(dataset ? FG.t("selfcheck.prefill.championNotResolved") : FG.t("selfcheck.prefill.championUnresolved", { records: unresolved.join(", ") }));
      if (!records.length) {
        setStatus(check, notices.join(" "));
        return;
      }
      run = st.champion = { input, records, verdicts: {}, date: today() };
    }
    const single = run.records.length === 1;
    return runPrefill(check, "champion", focusId, async (messages) => {
      messages.push(...notices);
      const pending = pendingOf(run, tests);
      const left = new Map();
      for (const [test] of pending) left.set(test, (left.get(test) || 0) + 1);
      for (const test of left.keys()) running.add(test);
      for (const button of document.querySelectorAll(".test-run")) button.disabled = true;
      showTests(check, st, [...left.keys()]);
      let done = 0;
      const tasks = pending.map(([test, record]) => async () => {
        try {
          const verdict = await FG.live.championTest(test, record);
          run.verdicts[verdictKey(test, record)] = { value: verdict.value, log: String(verdict.log || "").slice(0, LOG_MAX), truncated: String(verdict.log || "").length > LOG_MAX, invocation: FG.live.championInvocation(test, record) };
        } catch (error) {
          run.verdicts[verdictKey(test, record)] = { value: null, error: String(error.message || error).slice(0, 1000), invocation: FG.live.championInvocation(test, record) };
        }
        setProgress((done += 1), tasks.length);
        left.set(test, left.get(test) - 1);
        if (!left.get(test)) {
          running.delete(test);
          showTests(check, st, [test]);
        }
      });
      setProgress(0, tasks.length);
      try {
        await inBatches(tasks, (FG.config.champion && FG.config.champion.maxParallel) || 4);
      } finally {
        for (const test of left.keys()) running.delete(test);
        setProgress(0, 0);
      }
      run.date = today();
      const ran = championTests(check, st).map((pair) => pair.id).filter((test) => wasRun(run, test));
      const total = ran.length * run.records.length;
      messages.push(FG.t("selfcheck.prefill.championCoverage", { n: total - pendingOf(run, ran).length, total }));
      /* A dataset's test results join its exported result set. */
      if (single) st.verdicts = ran.map((test) => Object.assign({ test }, run.verdicts[verdictKey(test, run.records[0])] || { value: null }));
      return applyChampion(check, st, run);
    });
  }

  /** Answer every question whose FAIR Champion tests have results on this run: Yes when every record passed them,
      Partly when some did or when the tests cover only part of the question, No when none did (D-168). A test
      without a result never counts as a failure, and the coverage is always stated. */
  function applyChampion(check, st, run) {
    const single = run.records.length === 1;
    const valueOf = (test, record) => (run.verdicts[verdictKey(test, record)] || {}).value || null;
    const ran = championTests(check, st).map((pair) => pair.id).filter((test) => wasRun(run, test));
    return applyEvidence(
      check,
      "champion",
      (item, named) => {
        const own = named;
        if (!own.some((test) => ran.includes(test))) return null;
        const states = run.records.map((record) => {
          const values = own.map((test) => valueOf(test, record));
          if (values.includes("fail")) return "fail";
          if (values.every((value) => value === "pass")) return "pass";
          return values.includes("indeterminate") ? "indeterminate" : "none";
        });
        const known = states.filter((state) => state === "pass" || state === "fail").length;
        const passed = states.filter((state) => state === "pass").length;
        /* No verdict at all verified nothing, so it is not described as partial support; a narrower test or a sample
           with records without a result supports only part of the question, and answers Partly when that part is
           met and No when it fails (D-168). */
        const partial = item.championEvidenceOnly || states.some((state) => ["none", "indeterminate"].includes(state));
        const notes = !known ? [{ key: "selfcheck.note.testUnavailable" }] : partial ? [{ key: "selfcheck.note.partialCoverage" }] : [];
        return {
          value: !known ? null : !passed ? "no" : passed === run.records.length && !partial ? "yes" : "partly",
          notes,
          coverage: `${known}/${run.records.length} · ${own.length}`,
          /* The question's test line shows the verdicts; the evidence keeps them for the result and its export. */
          fields: single
            ? own.map((test) => ({ path: test, values: [FG.t("selfcheck.champion." + (valueOf(test, run.records[0]) || "none"))] }))
            : run.records.map((record, index) => ({ path: record, values: [FG.t("selfcheck.champion." + states[index])] })),
        };
      },
      run.date,
      single ? st.target || null : null
    );
  }

  /* Saved evidence follows the current rules: once per visit, and again after answers are adopted, a saved FAIR
     Champion run is applied again, as attached assessments are (`providers.refresh`). That replaces only its own
     observations, so the reader's answers stay theirs. */
  const reapplied = new Set();
  function reapplyEvidence(check) {
    if (!reapplied.has(check.identifier)) {
      reapplied.add(check.identifier);
      const st = stateOf(check);
      const run = currentRun(check, st);
      if (run && Object.keys(run.verdicts || {}).length) applyChampion(check, st, run);
    }
    if (providers) providers.refresh(check);
  }

  /** The identifier FAIR Champion is given: a DOI or Handle as its resolver address, which the tests accept where
      they refuse a bare DOI, and an address as it is. */
  function championTarget(entry) {
    const pid = FG.live.parsePid(entry);
    return pid ? { pid, record: FG.live.pidUrl(pid) } : { pid: null, record: String(entry).trim() };
  }

  /** Resolve each persistent identifier before any test runs: a test on an identifier that does not resolve would
      only fail, so such a record is left out and reported. */
  async function resolvedTargets(check, entries) {
    setStatus(check, FG.t("selfcheck.prefill.working", { source: label("resolver") }));
    const records = [];
    const unresolved = [];
    for (const entry of entries) {
      const target = championTarget(entry);
      let found = !target.pid;
      if (target.pid) {
        try {
          found = (await FG.live.resolvePid(target.pid)).found;
        } catch (error) {
          found = false;
        }
      }
      if (found) records.push(target.record);
      else unresolved.push(entry);
    }
    return { records, unresolved };
  }

  /** The run of these tests a button offers: run what was never run, else retry what gave no result, else none. */
  function runLabel(check, st, tests, keys) {
    const run = currentRun(check, st);
    if (!run || tests.some((test) => !wasRun(run, test))) return FG.t(keys.run, { n: tests.length });
    const missing = pendingOf(run, tests).length;
    return missing ? FG.t(keys.retry, { n: missing }) : null;
  }

  /** The FAIR Champion tests that can answer a question, where it is asked: each test leading to its catalogue
      entry, its state on the identifiers entered, and a run of this question's tests alone. */
  function testLine(check, st, item) {
    const tests = testsOf(item);
    if (!tests.length) return inspection.localTestLine(item);
    const ready = championReady(check, st);
    const action = ready ? runLabel(check, st, tests, { run: "selfcheck.champion.run", retry: "selfcheck.champion.retry" }) : null;
    return h(
      "div",
      { class: "test-line", id: "tests-" + keyOf(item), tabindex: "-1" },
      h(
        "p",
        { class: "test-head" },
        /* The tests are FAIR Champion's: its badge and name lead the line, as wherever an evaluator's work appears. */
        h("span", { class: "test-label evaluator-name" }, inspection.sourceBadge("champion"),
          h("span", null, FG.text((FG.get("#resource-fair-champion") || {}).name || "FAIR Champion") + " · " + FG.t("selfcheck.champion.label", { n: tests.length }))),
        action
          ? h("button", { type: "button", class: "button-small test-run", id: "test-run-" + keyOf(item), disabled: status.busy || null, onclick: () => runChampion(check, tests, "tests-" + keyOf(item)) }, action)
          : ready
            ? null
            : h("span", { class: "muted" }, FG.t(onDataset(check, st) ? "selfcheck.champion.needPid" : "selfcheck.champion.needSample"))
      ),
      h(
        "ul",
        { class: "test-list" },
        tests.map((id) => {
          const test = FG.sourceEntity("fair-champion", id);
          return h(
            "li",
            { class: "test-row", "data-test": id },
            test ? h("a", { href: FG.entryHref(test) }, FG.text(test.name)) : h("code", null, id),
            healthOf(test) === "degraded" ? [" ", h("span", { class: "badge", "data-health": "degraded" }, FG.t("catalogue.health.degraded"))] : null,
            test && test.url ? h("p", { class: "small test-invocation" }, h("code", null, "POST"), " ", FG.external(test.url, FG.t("selfcheck.evidence.endpoint")),
              FG.list(test.subjectOf).map((reference, index) => [" · ", FG.external(typeof reference === "string" ? reference : reference["@id"], FG.t(index ? "selfcheck.evidence.serviceDocumentation" : "selfcheck.evidence.documentation"))])) : null,
            " ",
            testState(currentRun(check, st), id)
          );
        })
      )
    );
  }

  /** Every test of the check at once: how many questions they can answer, and the run of all of them; `sync` takes
      what was typed before the run reads it. */
  function championAll(check, st, sync, sampleReasonId) {
    const pairs = championTests(check, st);
    if (!pairs.length) return null;
    const questions = new Set(pairs.flatMap((pair) => pair.items.map((item) => item.identifier))).size;
    const action = runLabel(
      check,
      st,
      pairs.map((pair) => pair.id),
      { run: "selfcheck.champion.all", retry: "selfcheck.prefill.championRetry" }
    );
    const run = action
      ? h(
          "button",
          {
            type: "button",
            id: "prefill-champion-run",
            onclick: () => {
              if (sync) sync();
              runChampion(check, pairs.map((pair) => pair.id), "prefill-champion-run");
            },
          },
          action
        )
      : null;
    /* The run waits for the records it would test: the dataset looked up above, or a sample within its size, whose
       field already says what it waits for (`sampleReasonId`). The control is drawn again when either changes. */
    const shared = Boolean(run && sampleReasonId && !onDataset(check, st));
    const waiting = run && !shared ? FG.gate(run, FG.t("selfcheck.prefill.championNeedsPid"), () => championReady(check, st)) : null;
    if (shared && !championReady(check, st)) {
      run.disabled = true;
      run.setAttribute("aria-describedby", sampleReasonId);
    }
    return h(
      "div",
      { class: "champion-all" },
      h(
        "p",
        { class: "inline" },
        h("span", null, FG.t("selfcheck.champion.intro", { n: questions })),
        run || h("span", { class: "muted" }, FG.t("selfcheck.champion.allDone"))
      ),
      waiting,
      h("p", { class: "small muted" }, FG.t(onDataset(check, st) ? "selfcheck.prefill.championDeepHint" : "selfcheck.prefill.championHint"))
    );
  }

  /** Where DataCite finds the repository a check is about: the DataCite ID the guide reviewed for the repository of
      the check's re3data record, or that record's DOI from the re3data snapshot. */
  function dataciteRouteOf(st) {
    if (!st.re3data) return null;
    const record = FG.config.links.re3dataRecord + st.re3data;
    const listed = FG.repositoryEntries().find((repository) => FG.refIds(repository, "sameAs").includes(record));
    return FG.live.dataciteRoute(listed) || FG.live.dataciteRoute((FG.config.re3data || {})[st.re3data]);
  }

  /** A sample drawn at random from the repository's records in DataCite, listed with their titles before any test
      runs. Each record can be replaced by another drawn the same way, and the sample field stays editable by hand. */
  function dataciteSampleRow(check, st, field, sync) {
    const route = dataciteRouteOf(st);
    const t = (key, params) => FG.t("selfcheck.prefill.datacite" + key, params);
    const status = h("p", { class: "small", role: "status", id: "datacite-sample-status" });
    const say = (text) => { status.textContent = text; };
    /* The drawn records still in the sample field, in the field's order. */
    const listed = () => {
      const drawn = st.dataciteSample ? FG.list(st.dataciteSample.records) : [];
      return sampleOf(st.sample).map((value) => drawn.find((record) => record.doi === value.toLowerCase())).filter(Boolean);
    };
    const setField = (values) => {
      field.value = values.join("\n");
      sync();
      FG.renderList("datacite-sample", list);
    };
    const replace = async (record, button) => {
      button.disabled = true;
      try {
        const sample = st.dataciteSample;
        const taken = new Set(sampleOf(st.sample).map((value) => value.toLowerCase()));
        const fresh = (await FG.live.dataciteSample(sample.repository.id, SAMPLE_MAX)).find((item) => !taken.has(item.doi));
        if (!fresh) { say(t("NoMore")); button.disabled = false; return; }
        sample.records = sample.records.filter((item) => item.doi !== record.doi).concat(fresh);
        setField(sampleOf(st.sample).map((value) => (value.toLowerCase() === record.doi ? fresh.doi : value)));
        say(t("Replaced", { doi: record.doi, fresh: fresh.doi }));
        const next = document.getElementById("datacite-replace-" + fresh.doi.replace(/[^a-z0-9]+/g, "-"));
        if (next) next.focus();
      } catch (error) {
        say(t("Failed"));
        button.disabled = false;
      }
    };
    function list() {
      const records = listed();
      if (!records.length) return fragment();
      const sample = st.dataciteSample;
      return fragment(
        h("p", { class: "small" }, t("Drawn", { date: FG.formatDate(sample.date), n: records.length, name: sample.repository.name })),
        h("ol", { class: "datacite-sample" }, records.map((record) => {
          const replaceButton = h("button", { type: "button", class: "button-small", id: "datacite-replace-" + record.doi.replace(/[^a-z0-9]+/g, "-"),
            "aria-label": t("ReplaceOne", { doi: record.doi }) }, t("Replace"));
          replaceButton.addEventListener("click", () => replace(record, replaceButton));
          return h("li", null, h("span", { class: "datacite-sample-title" }, record.title || t("Untitled")), " ",
            record.type ? [h("span", { class: "small muted" }, record.type), " "] : null,
            FG.external(FG.live.pidUrl({ type: "doi", value: record.doi }), record.doi), " ", replaceButton);
        }))
      );
    }
    const draw = async () => {
      drawButton.disabled = true;
      say(t("Drawing"));
      try {
        const repository = await FG.live.dataciteRepository(route);
        if (!repository) { say(t("Absent")); return; }
        const records = await FG.live.dataciteSample(repository.id, SAMPLE_MAX);
        if (!records.length) { say(t("Empty")); return; }
        st.dataciteSample = { repository, date: FG.today(), records };
        setField(records.map((record) => record.doi));
        say("");
      } catch (error) {
        say(t("Failed"));
      } finally {
        drawButton.disabled = !route;
      }
    };
    const drawButton = h("button", { type: "button", id: "prefill-datacite-sample", onclick: draw }, t("Sample"));
    const reason = FG.gate(drawButton, t("NeedsRepository"), () => Boolean(route));
    return h("div", { class: "datacite-sample-row" }, drawButton, reason, status, h("div", { id: "datacite-sample" }, list()));
  }

  /** A sample of a repository's records to test; a new sample starts afresh. */
  function championSampleControl(check, st) {
    const field = h("textarea", { id: "prefill-champion", rows: "3", spellcheck: "false", autocomplete: "off" }, st.sample || "");
    /* The sample's inspection and the run of all tests wait for the same sample, so they share one reason. */
    let sampleReason = null;
    /* What is typed is the sample at once: the questions' lines and the run of all tests follow it, without the
       field being drawn again. */
    const sync = () => {
      st.sample = field.value;
      save();
      /* A sample drawn from DataCite fills the field without typing, so the controls that wait for it follow here. */
      if (sampleReason) sampleReason.refresh();
      for (const item of answerable(check, st)) {
        const line = document.getElementById("tests-" + keyOf(item));
        if (line) line.replaceWith(testLine(check, st, item));
      }
      const all = document.querySelector(".champion-all");
      if (all) all.replaceWith(championAll(check, st, sync, sampleReason && sampleReason.id));
    };
    field.addEventListener("input", sync);
    const inspect = () => {
      sync();
      const entries = sampleOf(st.sample);
      if (!entries.length || entries.length > SAMPLE_MAX) { setStatus(check, FG.t("selfcheck.prefill.championInvalid", { n: SAMPLE_MAX })); return; }
      inspection.inspectSample(check, entries);
    };
    const inspectButton = h("button", { type: "button", id: "prefill-sample-run", onclick: inspect }, FG.t("selfcheck.discovery.sampleButton"));
    const sampleSized = () => { const count = sampleOf(field.value).length; return count > 0 && count <= SAMPLE_MAX; };
    sampleReason = FG.gate(inspectButton, FG.t("selfcheck.prefill.championNeedsSample", { n: SAMPLE_MAX }), sampleSized, field);
    return h("div", { class: "prefill-row" }, h("label", { for: "prefill-champion" }, FG.t("selfcheck.prefill.champion", { n: SAMPLE_MAX })), field,
      dataciteSampleRow(check, st, field, sync), inspectButton, sampleReason,
      h("p", { class: "small muted" }, FG.t("selfcheck.discovery.sampleHint")), championAll(check, st, sync, sampleReason.id));
  }

  const re3dataControl = (...args) => inspection.re3dataControl(...args);
  const nkrControl = (...args) => inspection.nkrControl(...args);
  const fipControl = (...args) => inspection.fipControl(...args);
  const softwareControl = (...args) => inspection.softwareControl(...args);
  const inspectionDetails = (...args) => inspection.inspectionDetails(...args);

  /** The ways to start a check without answering everything by hand: public records that the check's questions
      can be filled in from, and a result saved earlier. Before the mode or profile is chosen, only the saved result,
      which brings its own. */
  /* The resource each evidence source is, for its badge: the service's own favicon wherever the Guide has one. */
  const SOURCE_RESOURCES = { pid: "datacite", nkr: "nkr", re3data: "re3data", sample: "fair-champion", fip: "fip-dashboard" };
  const SOURCE_ICONS = { software: "code", evaluators: "check", file: "upload" };

  /** One evidence source as a card: its badge and name, what it sends to which service, how long it takes and how
      many of the shown questions it can suggest an answer to, then its controls. */
  function evidenceCard(check, st, key, prefills, ...content) {
    const resource = FG.get("#resource-" + SOURCE_RESOURCES[key]);
    const localQuestions = new Set(FG.graph.filter((test) => String(test["@id"]).startsWith("#test-guide-") &&
      ((key === "software" && test.url === "assets/js/tests/software.js") || (key === "pid" && test.url === "assets/js/tests/object.js")))
      .flatMap((test) => FG.refIds(test, "isImplementationOf")));
    const count = resultItems(check, st).filter((item) => localQuestions.has(FG.id(item)) || prefills.some((source) => prefillOf(item, source))).length;
    const t = (field, params) => FG.t("selfcheck.evidenceCard." + key + "." + field, params);
    const facts = [
      [FG.t("selfcheck.evidenceCard.sends"), t("sends")],
      [FG.t("selfcheck.evidenceCard.takes"), t("takes")],
      prefills.length ? [FG.t("selfcheck.evidenceCard.answers"), FG.t("selfcheck.evidenceCard.answersCount", { n: count })] : null,
    ].filter(Boolean);
    return h(
      "section",
      { class: "evidence-card", "data-source": key, "aria-labelledby": "source-" + key },
      h(
        "h3",
        { id: key === "evaluators" ? "evaluators-title" : "source-" + key, class: "evidence-title" },
        resource ? FG.serviceBadge(resource.identifier, resource.url) : h("span", { class: "evidence-icon", "aria-hidden": "true" }, FG.icon(SOURCE_ICONS[key])),
        h("span", null, t("title"))
      ),
      h("dl", { class: "evidence-facts small" }, facts.map(([term, value]) => [h("dt", null, term), h("dd", null, value)])),
      h("div", { class: "evidence-body" }, content)
    );
  }

  /** Put these nodes at the end of the named card's body and return nothing, or return them when no card has that
      name, so the caller shows them after the cards. */
  function placed(cards, key, nodes) {
    const card = key && cards.find((node) => node.dataset.source === key);
    const body = card && card.querySelector(".evidence-body");
    if (!body) return nodes;
    body.append(...nodes.filter(Boolean));
    return null;
  }

  /** The card whose lookup found the record a check is about: the re3data, NKR or FIP card for theirs, else the
      identifier's card. */
  const targetKeyOf = (st) => ({ re3data: "re3data", NKR: "nkr", FIP: "fip" })[(st.targetInfo || {}).kind] || "pid";

  function startPanel(check, st, ready) {
    const sources = ready ? sourcesOf(check, st) : new Set();
    /* A check about a repository tests a sample of its records; a check about one object tests that object, offered
       on the record its lookup found. */
    const dataset = sources.has("datacite") || sources.has("resolver");
    const object = dataset || (ready && ["cdif", "fdo"].includes(check.identifier));
    const evaluatorPanel = providers && object ? providers.panel(check, st, resultItems(check, st)) : null;
    const cards = [
      object
        ? evidenceCard(check, st, "pid", ["datacite", "resolver"], pidControl(check, st), needsSteward(check, st) ? stewardControl(check, st) : null,
          sources.has("champion") && dataset && st.target && championReady(check, st) ? championAll(check, st) : null)
        : null,
      ready && check.identifier === "software" ? evidenceCard(check, st, "software", ["data"], softwareControl(check, st)) : null,
      sources.has("nkr") ? evidenceCard(check, st, "nkr", ["nkr"], nkrControl(check, st, sources.has("re3data"))) : null,
      sources.has("re3data") ? evidenceCard(check, st, "re3data", ["re3data"], re3dataControl(check, st)) : null,
      sources.has("champion") && !dataset ? evidenceCard(check, st, "sample", ["champion"], championSampleControl(check, st)) : null,
      sources.has("fip") ? evidenceCard(check, st, "fip", ["fip"], fipControl(check, st)) : null,
      /* External evaluators assess the object a check is about, through the identifier looked up in its card. */
      evaluatorPanel ? evidenceCard(check, st, "evaluators", [], evaluatorPanel) : null,
    ].filter(Boolean);
    const file = evidenceCard(check, st, "file", [], h("p", { class: "small" }, FG.t("selfcheck.prefill.fromFileText")), loadControl("load-file"));
    /* A run's status and progress stand in the card that started it, and the record a lookup found in the card that
       looked it up; without such a card they follow the cards. */
    const statusKey = status.check === check.identifier ? status.card : null;
    const statusLine = h("p", { id: "prefill-status", role: "status", class: "small evidence-status" }, status.check === check.identifier ? status.text : "");
    return h(
      "section",
      { class: "prefill no-print", "aria-labelledby": "prefill-title" },
      h("h2", { id: "prefill-title" }, FG.t(cards.length ? "selfcheck.prefill.title" : "selfcheck.savedTitle")),
      h("p", { class: "small" }, FG.t(cards.length ? "selfcheck.prefill.privacy" : "selfcheck.savedText")),
      h("div", { class: "evidence-cards" }, cards, file),
      placed(cards, statusKey, [statusLine, progressBox()]),
      placed(cards, targetKeyOf(st), [targetCard(st)]),
      inspectionDetails(st)
    );
  }

  function itemField(check, st, item) {
    const id = keyOf(item);
    /* The item's tier and principles; a first-tier item with no principle has none, and no empty row. */
    const principles = FG.principlesOf(item);
    const meta =
      isFirstTier(item) && !principles.length
        ? null
        : h(
            "div",
            { class: "badges" },
            isFirstTier(item) ? null : h("span", { class: "badge" }, FG.termName(FG.id(item.tier))),
            principles.map((principle) => FG.principleTile(principle))
          );
    const statement = [h("span", { class: "item-id" }, numberOf(item)), " ", FG.linkedSpan(item)];
    const clauses = FG.refs(item, "citation");
    const basedOn = clauses.length
      ? h(
          "details",
          { class: "item-basis" },
          h("summary", null, FG.t("catalogue.relation.basedOn") + " (" + clauses.length + ")"),
          h("ul", { class: "content clauses", role: "list" }, clauses.map(FG.clauseEntry))
        )
      : null;
    if (providedByNrp(item, st) || item.assessmentContext) {
      return h(
        "div",
        { class: "item " + (item.assessmentContext ? "item-context" : "item-provided"), id: "item-" + id },
        h("p", { class: "item-statement" }, statement),
        meta,
        item.description ? h("p", { class: "question-help" }, FG.linkedSpan(item, "description")) : null,
        item.note ? h("p", { class: "small" }, FG.linkedSpan(item, "note")) : null,
        item.assessmentContext ? [h("p", { class: "source-chip" }, FG.t("selfcheck.question.context")), h("p", { class: "small muted" }, FG.t("selfcheck.question.contextHint"))] : h("p", null, stateLabel("provided"), " ", FG.t("selfcheck.providedByNrpText")),
        item.assessmentContext && answerOf(st, item) ? h("details", { class: "historical-answer" }, h("summary", null, FG.t("selfcheck.question.previousAnswer")), h("div", { class: "content" }, FG.t("selfcheck.answer." + answerOf(st, item)))) : null,
        fixAtLine(item),
        basedOn
      );
    }
    const current = answerOf(st, item);
    const options = ANSWERS.filter((value) => value !== "na" || item.allowsNotApplicable);
    const entry = record(st, item);
    /* A compact card: the criterion and its principles, the answers, one evidence line and the way to withdraw an
       answer; the explanation, the other evidence, the tests, who fixes it, the path step and the sources wait in one
       disclosure, which stays open across re-renders while the page is open. */
    const detailsKey = "question-" + id;
    return h(
      "fieldset",
      { class: "item question-card", id: "item-" + id, "data-state": itemState(st, item), "data-origin": entry && entry.origin === "user" ? "user" : current ? "suggestion" : null },
      h("legend", null, statement),
      meta,
      h(
        "div",
        { class: "options" },
        options.map((value) => {
          const inputId = "answer-" + id + "-" + value;
          return h(
            "label",
            { class: "option", for: inputId, "data-value": value },
            h("input", { type: "radio", id: inputId, name: "answer-" + id, value, checked: current === value, onchange: () => setAnswer(check, item, value) }),
            ANSWER_ICON[value] ? FG.icon(ANSWER_ICON[value]) : null,
            h("span", null, FG.t("selfcheck.answer." + value))
          );
        })
      ),
      h("div", { id: "origin-" + id, class: "origin" }, originLine(st, item), withdrawControl(check, st, item)),
      h(
        "details",
        { class: "question-details", "data-key": detailsKey, open: FG.openLevels.has(detailsKey), ontoggle: (event) => (event.target.open ? FG.openLevels.add(detailsKey) : FG.openLevels.delete(detailsKey)) },
        h("summary", null, FG.t("selfcheck.question.details")),
        h(
          "div",
          { class: "content" },
          item.description ? h("p", { class: "question-help" }, FG.linkedSpan(item, "description")) : null,
          item.note ? h("p", { class: "small" }, FG.linkedSpan(item, "note")) : null,
          originRest(st, item),
          testLine(check, st, item),
          fixAtLine(item),
          basedOn
        )
      )
    );
  }

  /* The icon of each answer, as the answer states show it everywhere. */
  const ANSWER_ICON = { yes: "met", partly: "partly", no: "gap", unknown: "unknown" };

  /** The way to withdraw an answer the reader gave: back to the current suggestion where there is one, otherwise to
      no answer. Other questions keep their answers. */
  function withdrawControl(check, st, item) {
    const entry = record(st, item);
    if (!entry || entry.origin !== "user" || !answerOf(st, item)) return null;
    const pre = entry.prefill && typeof entry.prefill === "object" && entry.prefill.value ? entry.prefill : null;
    return h(
      "button",
      {
        type: "button",
        class: "button-link withdraw",
        id: "withdraw-" + keyOf(item),
        onclick: () => {
          const next = Object.assign({}, entry);
          if (pre) Object.assign(next, { value: pre.value, origin: "prefill" });
          else {
            delete next.value;
            delete next.origin;
          }
          st.items[item.identifier] = next;
          save();
          FG.rerender("answer-" + keyOf(item) + "-" + (pre ? pre.value : "yes"));
        },
      },
      FG.icon("resume"),
      h("span", null, FG.t(pre ? "selfcheck.question.withdrawToSuggestion" : "selfcheck.question.withdraw"))
    );
  }

  /** The path step where an item is addressed, as a link to it, on every item. */
  function fixAtLine(item) {
    const station = FG.get(item.fixAt);
    const actors = FG.refs(item, "fixedBy").map((actor) => FG.text(actor.name));
    return h("dl", { class: "relations question-relations fix-at small" },
      actors.length ? [h("dt", null, FG.t("selfcheck.question.responsible")), h("dd", null, actors.join(", "))] : null,
      station ? [h("dt", null, FG.t("selfcheck.result.whereFix")), h("dd", null, stepLink(station))] : null,
      FG.modelRows(item));
  }

  const letterOf = (item) => String((FG.principlesOf(item)[0] || {}).termCode || "").charAt(0);

  /** The same per-check presentation is used by Answers, Report and shared previews. */
  function groupingOptions(check) {
    const items = itemsOf(check);
    return [blocksOf(items).length && "blocks", items.some((item) => FG.principlesOf(item).length) && "principles",
      items.some((item) => FG.get(item.fixAt)) && "steps"].filter(Boolean);
  }

  function groupingOf(check) {
    const options = groupingOptions(check);
    const saved = FG.state.checkGroupings[check.identifier];
    // Retain older dataset path preferences without overriding native-block defaults in other checks.
    return options.includes(saved) ? saved : !options.includes("blocks") && FG.state.checkGrouping === "steps" && options.includes("steps") ? "steps" : options[0] || "principles";
  }

  function groupingControl(check, compact) {
    const current = groupingOf(check);
    return h(
      "fieldset",
      { class: "grouping no-print" + (compact ? " segmented" : "") },
      h("legend", null, FG.t("selfcheck.grouping")),
      groupingOptions(check).map((value) =>
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
              FG.state.checkGroupings[check.identifier] = value;
              FG.saveState();
              FG.rerender("grouping-" + value);
            },
          }),
          h("span", null, FG.t((compact ? "selfcheck.groupByShort." : "selfcheck.groupBy.") + value))
        )
      )
    );
  }

  /** A check's blocks in their order, when it has any. */
  const blocksOf = (items) => {
    const block = items.map((item) => FG.get(item.block)).find(Boolean);
    return block ? FG.refs(FG.get(block.inDefinedTermSet), "hasDefinedTerm") : [];
  };

  /** Lists contain each question once; missing mappings remain in Other. FAIR report bars may overlap. */
  function groupsOf(check, items) {
    let groups;
    const selected = groupingOf(check);
    const blocks = blocksOf(itemsOf(check));
    if (selected === "blocks") {
      groups = blocks.map((block, index) => ({ block, position: index + 1, items: items.filter((item) => FG.id(item.block) === block["@id"]) }));
    } else if (selected === "steps") {
      groups = FG.stations().map((station) => ({ station, items: items.filter((item) => FG.id(item.fixAt) === station["@id"]) }));
    } else {
      groups = ["F", "A", "I", "R"].map((letter) => ({ letter, items: items.filter((item) => letterOf(item) === letter) }));
    }
    const assigned = new Set(groups.flatMap((group) => group.items));
    const loose = items.filter((item) => !assigned.has(item));
    groups = groups.filter((group) => group.items.length);
    return loose.length ? groups.concat({ items: loose }) : groups;
  }

  /** A group's mark: the principle letter in its colour, or the path step's icon as on the path. */
  function groupMark(group) {
    if (group.block) {
      const icon = FG.config.icons && FG.config.icons.block && FG.config.icons.block[group.block.termCode];
      return FG.icon(icon, { class: "group-icon" }) || h("span", { class: "group-block" }, String(group.position));
    }
    if (group.letter) return h("span", { class: "principle-letter", "data-letter": group.letter }, group.letter);
    if (group.station) {
      const icon = FG.config.icons && FG.config.icons.station && FG.config.icons.station[group.station.identifier];
      return FG.icon(icon, { class: "group-icon" }) || h("span", null, String(group.station.position));
    }
    return h("span", { class: "group-other", "aria-hidden": "true" }, "…");
  }

  const groupName = (group) =>
    group.block ? FG.text(group.block.name) : group.letter ? FG.t("explorer.group." + group.letter) : group.station ? FG.text(group.station.name) : FG.t("selfcheck.groupOther");
  const groupTitle = (group) => [groupMark(group), " ", groupName(group)];

  /* On a wide screen with the summary open, the check's controls sit in the summary, at hand while scrolling; on a
     narrow screen or with the summary collapsed they sit above the questions. Crossing the width (turning a tablet,
     zooming) re-renders, keeping the focus on the control that had it. */
  const WIDE = window.matchMedia ? window.matchMedia("(min-width: 60rem)") : null;
  const controlsInSummary = () => Boolean(WIDE && WIDE.matches) && !FG.state.resultCollapsed;
  if (WIDE && WIDE.addEventListener) WIDE.addEventListener("change", () => document.querySelector(".check-view") && FG.rerender(document.activeElement && document.activeElement.id));

  /** The extended switch (when the check has further items) and the grouping. */
  function checkControls(check, st, compact) {
    const all = applicable(check, st);
    const first = all.filter(isFirstTier);
    const more = first.length ? all.length - first.length : 0;
    return [more ? extendedSwitch(st, more, compact) : null, groupingControl(check, true)];
  }

  /** One sentence on what the first view's tier means and how many further items exist, with the control to add them. */
  function tierInfo(check, st, first, more) {
    if (!first.length || !more) return null;
    const tier = FG.get(first[0].tier) || {};
    return h(
      "p",
      { class: "tier-info" },
      h("strong", null, FG.t("selfcheck.tierCount", { tier: FG.text(tier.name), n: first.length }) + " "),
      check.identifier === "institution" ? FG.t("selfcheck.institutionMinimum") : tier.description ? FG.span(tier.description) : null,
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
      h("span", { title: compact ? FG.t("selfcheck.extendedSwitch", { n: more }) : null }, FG.t(compact ? "selfcheck.extendedShort" : "selfcheck.extendedSwitch", { n: more }))
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
      groupsOf(check, shown).map((group) =>
        h(
          "section",
          { class: "item-group" },
          groupTitle(group) ? h("h2", null, groupTitle(group)) : null,
          group.block && group.block.description ? h("p", { class: "group-description small muted" }, FG.linkedSpan(group.block, "description")) : null,
          group.items.map((item) => itemField(check, st, item))
        )
      )
    );
  }

  /* ---------------------------------------------------------------- results */

  function whom(item) {
    const own = LENS_ACTOR[FG.state.lens];
    const actors = FG.refs(item, "fixedBy").filter((actor) => actor["@id"] !== "#actor-researcher" && actor["@id"] !== own);
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
        h("span", { class: "item-id" }, numberOf(item)),
        " ",
        FG.span(item.text),
        isFirstTier(item) ? null : [" ", h("span", { class: "badge" }, FG.termName(FG.id(item.tier)))]
      ),
      h(
        "p",
        { class: "action-meta" },
        station ? [h("span", { class: "action-label" }, FG.t("selfcheck.result.whereFix") + ": "), stepLink(station)] : null,
        who.length ? [station ? h("span", { class: "action-sep" }, " · ") : null, h("span", { class: "action-label" }, FG.t("selfcheck.result.whoFix") + ": "), who.join(", ")] : null
      ),
      programmeLine(st, item),
      basisLine(item),
      handover(st, item)
    );
  }

  /** For a funded output: that the dataset would not meet the picked programme's output requirement. */
  function programmeLine(st, item) {
    const programmes = FG.refIds(item, "appliesTo").filter((id) => id.startsWith("#profile-"));
    const picked = st && st.profile ? "#profile-" + st.profile : null;
    if (!picked || !programmes.includes(picked)) return null;
    return h("p", { class: "action-programme small" }, FG.t("selfcheck.result.programmeGap", { programme: FG.text(FG.get(picked).name) }));
  }

  /** What a gap rests on: the requirements its question cites, as identifiers leading to the catalogue, and their
      sources. */
  function basisLine(item) {
    /* By identifier, so that a gap shown where a standard's requirements have not loaded (a station) still names them. */
    const ids = FG.refIds(item, "citation").filter((id) => id.startsWith("#clause-"));
    if (!ids.length) return null;
    const clauses = ids.map(FG.get).filter(Boolean);
    const sources = [...new Set(clauses.map((clause) => FG.get(clause.isPartOf)).filter(Boolean))];
    return h(
      "p",
      { class: "action-basis small" },
      h("span", { class: "action-label" }, FG.t("selfcheck.result.basedOn") + ": "),
      ids.map((id, index) => [index ? " " : "", FG.idChip(FG.get(id))]),
      sources.length ? [" · ", sources.map((source, index) => [index ? ", " : "", FG.sourceLink(source)])] : null
    );
  }

  function taskItem(item, st) {
    const ask = whom(item);
    const lookup = FG.id(item.lookup);
    return h(
      "li",
      { class: "action-card", "data-state": "unknown" },
      h("p", { class: "action-title" }, stateLabel("unknown"), " ", h("span", { class: "item-id" }, numberOf(item)), " ", FG.span(item.text)),
      h(
        "p",
        { class: "action-meta" },
        ask.names.length ? [h("span", { class: "action-label" }, FG.t("selfcheck.result.askLabel") + ": "), ask.names.join(", ")] : null,
        lookup ? [ask.names.length ? h("span", { class: "action-sep" }, " · ") : null, FG.external(lookup, FG.t("selfcheck.result.lookup"))] : null,
        ask.helps.map((help) => [h("span", { class: "action-sep" }, " · "), helpLink(help)])
      ),
      st ? handover(st, item) : null
    );
  }

  /** Reuse retained observations for a hand-over; unavailable evidence remains unavailable. */
  function handover(st, item) {
    if (!FG.refIds(item, "implementationSeams").length) return null;
    const ask = whom(item);
    const check = FG.get(item.isPartOf) || SC.checks().find((candidate) => FG.hasRef(candidate, "hasPart", item["@id"]));
    const pid = st.target && FG.live.parsePid(st.target);
    const targetUrl = webUrl(st.target) || (pid ? FG.live.pidUrl(pid) : null);
    const targetName = st.targetInfo && (st.targetInfo.name || st.targetInfo.publisher);
    return h("details", { class: "result-handover" }, h("summary", null, FG.t("model.handover")), h("div", { class: "content" },
      h("dl", { class: "relations small" }, FG.modelRows(item),
        h("dt", null, FG.t("model.criterion")), h("dd", null, FG.idChip(item), " ", FG.span(item.text)),
        ask.names.length ? [h("dt", null, FG.t("selfcheck.result.askLabel")), h("dd", null, ask.names.join(", "))] : null,
        st.target ? [h("dt", null, FG.t("selfcheck.targetLabel")), h("dd", null, targetName && targetUrl ? [FG.external(targetUrl, targetName), " "] : null, FG.targetChip(st.target))] : null),
      h("p", { class: "small" }, FG.t("model.handoverHint")),
      check ? testLine(check, st, item) : null,
      observationsOf(record(st, item)).length ? observationsOf(record(st, item)).map(observationBody) : h("p", { class: "small muted" }, FG.t("model.noObservation")),
      basisLine(item)));
  }

  function answerText(st, item) {
    const value = answerOf(st, item);
    return value ? FG.t("selfcheck.answer." + value) : FG.t("selfcheck.result.unanswered");
  }

  /** Who the answer comes from. A source is named only while the answer still is its suggestion; the reader's own
      answer is theirs even when sources observed something, and those observations are listed apart. */
  function sourceText(st, item) {
    const entry = record(st, item);
    if (!entry || !answerOf(st, item)) return "";
    if (entry.origin === "user") return FG.t("selfcheck.origin.yours");
    if (entry.origin === "shared") return label("shared");
    if (entry.prefill && entry.prefill.source && entry.prefill.value === answerOf(st, item)) return FG.t("selfcheck.origin.suggestedBy", { source: label(entry.prefill.source), date: FG.formatDate(entry.prefill.date) });
    return "";
  }

  /** Each source's newest observation of an item, those with a readable fact first. */
  function observedFacts(entry) {
    const bySource = new Map();
    for (const seen of observationsOf(entry)) bySource.set(seen.source + "|" + (seen.assessment || ""), seen);
    const facts = (seen) => foundFields(seen).filter((field) => FIELD_LABELS[field.path] && seen.source !== "champion");
    return [...bySource.values()].reverse().sort((a, b) => facts(b).length - facts(a).length).map((seen) => ({ seen, fields: facts(seen) }));
  }

  /** The evidence of an answer in one line, for the summary and the exported result set. */
  function evidenceText(st, item) {
    const entry = record(st, item);
    return observationsOf(entry).map((pre) => {
      const fers = FG.list(pre.list).filter((fer) => fer && fer.name).map((fer) => String(fer.name));
      return [label(pre.source), FG.formatDate(pre.date), FG.t("selfcheck.evidence.suggestion") + ": " + (pre.value ? FG.t("selfcheck.answer." + pre.value) : FG.t("selfcheck.result.unanswered"))]
        .concat(foundFields(pre).map((field) => readableField(field) + ": " + field.values.map(readableValue).join(", ") + (field.more ? ` (+${field.more})` : "")))
        .concat(fers.length ? [FG.t("selfcheck.note.declared") + ": " + fers.join(", ")] : [])
        .concat(FG.list(pre.notes).map(noteText)).concat([pre.subject, pre.representation, pre.commit, pre.coverage, pre.record].filter(Boolean))
        .concat(pre.truncated ? [FG.t("selfcheck.evidence.bounded")] : []).join("; ");
    }).join("\n");
  }

  /** One answer: the question and the answer on one line, then where it came from and what supports it. */
  function answerRow(st, item) {
    const entry = record(st, item);
    const pre = entry && entry.prefill && typeof entry.prefill === "object" ? entry.prefill : null;
    const value = answerOf(st, item);
    const meta = [];
    const owner = sourceText(st, item);
    if (owner) meta.push(h("span", { class: "answer-owner" }, owner));
    for (const { seen, fields } of observedFacts(entry).slice(0, 3)) {
      meta.push(h("span", { class: "answer-observation" }, FG.t("selfcheck.evidence.observedBy", { source: label(seen.source), date: FG.formatDate(seen.date) }),
        fields.slice(0, 2).map((field) => [" ", h("span", { class: "evidence-readable" }, readableField(field), ": ", field.values.slice(0, 3).map((found, index) => [index ? ", " : "", valueNode(found, true)]))])));
    }
    return h(
      "li",
      { class: "answer-row", id: "report-answer-" + item.identifier, tabindex: "-1" },
      h(
        "p",
        { class: "answer-line" },
        h(
          "span",
          { class: "answer-pill", "data-state": itemState(st, item) },
          h("span", { "aria-hidden": "true" }, STATE_ICON[itemState(st, item)] + " "),
          providedByNrp(item, st) ? FG.t("selfcheck.state.provided") : value ? FG.t("selfcheck.answer." + value) : FG.t("selfcheck.result.unanswered")
        ),
        h("span", { class: "answer-question" }, h("span", { class: "item-id" }, numberOf(item)), " ", FG.span(item.text))
      ),
      meta.length ? h("p", { class: "answer-meta" }, meta.map((part, index) => [index ? " · " : "", part])) : null,
      pre ? evidenceDetails(entry) : null
    );
  }

  /** The result's first sentence leads with what remains to do: a gap, then a question to find out, then an
      unanswered question. Answered is not satisfied, and Don't know stays an answer with a follow-up. */
  function resultLead(items, answered, gaps, tasks, counts) {
    if (gaps.length) return FG.t("selfcheck.result.leadGaps", { n: gaps.length });
    if (tasks.length) return FG.t("selfcheck.result.leadTasks", { n: tasks.length });
    if (answered < items.length) return FG.t("selfcheck.result.leadOpen", { n: items.length - answered });
    return FG.t("selfcheck.result.leadMet", { n: (counts.met || 0) + (counts.provided || 0) });
  }

  /** What a result rests on, stated for this check: NRP admission is named only where the check is about it. */
  const advisory = (check) => FG.t("selfcheck.result.advisory") + (check.identifier === "gate" ? " " + FG.t("selfcheck.result.advisoryGate") : "");

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
        h("p", { class: "result-lead", "data-kind": gaps.length ? "gaps" : tasks.length ? "tasks" : answered < items.length ? "open" : "met" }, resultLead(items, answered, gaps, tasks, counts)),
        h("p", { class: "result-progress" }, FG.t("selfcheck.progress", { n: answered, total: items.length })),
        hiddenAnswers(check, st),
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
              st.targetInfo && (st.targetInfo.name || st.targetInfo.publisher) ? [FG.external(st.target, st.targetInfo.name || st.targetInfo.publisher), " "] : null,
              FG.targetChip(st.target)
            )
          : null,
        h("p", { class: "small muted" }, advisory(check))
      ),
      stateSections(check, st, items),
      h("h3", { id: "results-gaps", tabindex: "-1" }, FG.t("selfcheck.report.gaps")),
      gaps.length ? gapsByWhom(st, gaps) : h("p", { class: "muted" }, FG.t(tasks.length ? "selfcheck.result.noGapsTasks" : "selfcheck.result.noGaps")),
      tasks.length ? [h("h3", { id: "results-tasks", tabindex: "-1" }, FG.t("selfcheck.result.tasks")), h("ul", { class: "gaps" }, tasks.map((item) => taskItem(item, st)))] : null,
      agreement(check, st, items),
      providers ? providers.overview(check, st) : null,
      h(
        "details",
        { class: "result-all-details" },
        h("summary", null, FG.t("selfcheck.result.answers")),
        h("div", { class: "content" }, h("p", { class: "small muted result-scope" }, FG.t("selfcheck.result.scope")), resultGroups(check, st, items))
      ),
    ];
  }

  /* ---------------------------------------------------------------- the report's views of the answers */

  const DISTRIBUTION_STATES = ["met", "partly", "gap", "unknown", "open"];

  /** How a set of questions is answered: a bar of solid segments in the states' colours, and the same counts named
      in text, which is what assistive technology reads. */
  function distribution(st, items, compact) {
    const counts = {};
    for (const item of items) counts[itemState(st, item)] = (counts[itemState(st, item)] || 0) + 1;
    const present = DISTRIBUTION_STATES.filter((state) => counts[state]);
    const segments = present.map((state) => {
      const segment = h("span", { "data-state": state }, compact ? null : String(counts[state]));
      /* The page allows no style attributes, so each segment's share is set on the element itself. */
      segment.style.flexGrow = String(counts[state]);
      return segment;
    });
    /* In the running result the chips beside the bar name each question's state; the report names the counts. */
    return h(
      "div",
      { class: "distribution" + (compact ? " distribution-compact" : "") },
      h("div", { class: "distribution-bar", "aria-hidden": "true" }, segments),
      compact ? null : h("p", { class: "distribution-text small" }, present.map((state) => FG.t("selfcheck.count." + state, { n: counts[state] })).join(" · "))
    );
  }

  /** The answers per FAIR principle, one bar each, with a legend and the same numbers as a table. */
  /** The FAIR areas (F, A, I, R) a question's principles belong to; a question can address several. */
  const lettersOf = (item) => [...new Set(FG.principlesOf(item).map((principle) => String(principle.termCode || "").charAt(0)).filter(Boolean))];

  /** The state by FAIR area: a question counts under every area its principles belong to, so the rows may overlap;
      questions without a FAIR principle are left out and counted in the note. */
  function principleDistributions(st, items) {
    const rows = ["F", "A", "I", "R"]
      .map((letter) => ({
        mark: h("span", { class: "principle-letter", "data-letter": letter, title: FG.t("explorer.group." + letter) }, letter),
        name: FG.t("explorer.group." + letter),
        items: items.filter((item) => lettersOf(item).includes(letter)),
      }))
      .filter((row) => row.items.length);
    if (!rows.length) return null;
    const outside = items.filter((item) => !lettersOf(item).length).length;
    return [
      distributions(st, rows, "principle-distribution", FG.t("selfcheck.report.principle")),
      h("p", { class: "small muted" }, FG.t("selfcheck.report.principleOverlap"), outside ? " " + FG.t("selfcheck.report.principleOutside", { n: outside }) : null),
    ];
  }

  /** Native blocks and path steps partition the questions, retaining those without mappings. */
  function groupedDistributions(check, st, items) {
    const rows = groupsOf(check, items).map((group) => ({
      mark: h("span", { class: "block-mark" }, groupTitle(group)), name: groupName(group), items: group.items,
    }));
    const path = groupingOf(check) === "steps";
    return distributions(st, rows, path ? "path-distribution" : "block-distribution", FG.t(path ? "selfcheck.report.step" : "selfcheck.report.block"));
  }

  function stateSections(check, st, items) {
    const selected = groupingOf(check);
    return [
      groupingControl(check, true),
      h("h3", { id: "results-" + selected }, FG.t("selfcheck.report." + selected)),
      selected === "principles" ? principleDistributions(st, items) : groupedDistributions(check, st, items),
      h("p", { class: "small muted" }, FG.icon("info"), " ", FG.t("selfcheck.report.noScore")),
    ];
  }

  /** Rows of solid distributions, each after its mark, with one legend and the counts as a table. */
  function distributions(st, rows, rowClass, header) {
    const count = (row, state) => row.items.filter((item) => itemState(st, item) === state).length;
    return h(
      "div",
      { class: "principle-distributions" },
      rows.map((row) => h("div", { class: rowClass }, row.mark, distribution(st, row.items))),
      h("ul", { class: "distribution-legend small" }, DISTRIBUTION_STATES.map((state) => h("li", { "data-state": state }, h("span", { class: "legend-swatch", "aria-hidden": "true" }), FG.t("selfcheck.state." + state)))),
      h(
        "details",
        { class: "distribution-table" },
        h("summary", null, FG.t("selfcheck.report.table")),
        h(
          "div",
          { class: "content" },
          h(
            "table",
            { class: "data-table" },
            h("thead", null, h("tr", null, h("th", { scope: "col" }, header), DISTRIBUTION_STATES.map((state) => h("th", { scope: "col" }, FG.t("selfcheck.state." + state))))),
            h("tbody", null, rows.map((row) => h("tr", null, h("th", { scope: "row" }, row.name), DISTRIBUTION_STATES.map((state) => h("td", null, String(count(row, state)))))))
          )
        )
      )
    );
  }

  /** The gaps, grouped by who fixes them: one card per actor, each gap with where on the path it is addressed. */
  /* The owners a role stands for: the chosen role sees the gaps it puts right first. Every owner is named by its
     role, so a gap reads the same on screen, in a saved report and to whoever reads it; the researcher's group is the
     Researcher lens's own. */
  const ROLE_OWNERS = { V: ["#actor-researcher"], DS: ["#actor-data-steward"], SR: ["#actor-repository-admin", "#actor-curator"], K: ["#actor-community"] };

  /** The gaps grouped by who puts them right, as each question states it (its owners in the content); the rule is
      said above the groups, and the chosen role changes only which group comes first. */
  function gapsByWhom(st, gaps) {
    const groups = new Map();
    for (const item of gaps) {
      const actors = FG.refs(item, "fixedBy");
      const key = actors.map((actor) => actor["@id"]).join(" ") || "-";
      if (!groups.has(key)) groups.set(key, { actors, items: [] });
      groups.get(key).items.push(item);
    }
    const mine = ROLE_OWNERS[FG.state.lens] || [];
    const isMine = (group) => group.actors.some((actor) => mine.includes(actor["@id"]));
    const ordered = [...groups.values()].sort((a, b) => Number(isMine(b)) - Number(isMine(a)));
    const names = (actors) => new Intl.ListFormat(FG.state.lang === "cs" ? "cs" : "en", { type: "conjunction" }).format(actors.map((actor) => FG.text(actor.name)));
    return [
      h("p", { class: "small muted gap-rule" }, FG.t("selfcheck.report.gapsRule")),
      h(
        "div",
        { class: "gap-groups" },
        ordered.map((group) =>
          h(
            "section",
            { class: "gap-group" + (isMine(group) ? " gap-group-mine" : "") },
            h(
              "h4",
              null,
              group.actors.length ? FG.t("selfcheck.report.fixedBy", { who: names(group.actors) }) : FG.t("selfcheck.report.anyone"),
              h("span", { class: "muted" }, " · " + group.items.length),
              isMine(group) ? [" ", h("span", { class: "badge" }, FG.t("selfcheck.report.yourRole"))] : null
            ),
            h("ul", { class: "gaps" }, group.items.map((item) => gapItem(st, item)))
          )
        )
      ),
    ];
  }

  /** The evaluators that may observe a check's questions: FAIR Champion where its tests are named, and the external
      evaluators of a check about one object. */
  function evaluatorsOf(check, st) {
    const list = [];
    if (sourcesOf(check, st).has("champion")) list.push({ id: "champion", resource: "fair-champion", covers: (item) => Boolean(prefillOf(item, "champion")) });
    const object = sourcesOf(check, st).has("datacite") || sourcesOf(check, st).has("resolver") || ["cdif", "fdo"].includes(check.identifier);
    if (providers && object && FG.providers) {
      for (const provider of FG.list(FG.providers.settings().list)) {
        const mapped = new Set(FG.providers.mappings(provider).map((mapping) => mapping.question));
        list.push({ id: provider.id, resource: provider.id, covers: (item) => mapped.has(item.identifier) });
      }
    }
    return list;
  }

  /** The reader's answers beside what the evaluators observed, question by question, and whether they agree. Each
      response leads to its question's row in the list of all answers below, where the evidence stands. */
  function agreement(check, st, items) {
    const evaluators = evaluatorsOf(check, st);
    if (!evaluators.length) return null;
    const latest = (item, source) => observationsOf(record(st, item)).filter((observation) => observation.source === source).pop();
    const rows = items.filter((item) => answerOf(st, item) || evaluators.some((evaluator) => latest(item, evaluator.id)));
    /* The list of all answers below opens at the question's row, which then takes focus. */
    const toRow = (item) => () => {
      const list = document.querySelector(".result-all-details");
      if (list) list.open = true;
      const row = document.getElementById("report-answer-" + item.identifier);
      if (!row) return;
      row.scrollIntoView({ block: "center" });
      row.focus({ preventScroll: true });
      row.classList.add("jumped");
      setTimeout(() => row.classList.remove("jumped"), 1600);
    };
    const link = (item, content) => h("button", { type: "button", class: "button-link agreement-link", onclick: toRow(item) }, content);
    const cell = (item, evaluator) => {
      const observation = latest(item, evaluator.id);
      if (!observation) return h("td", { class: "muted" }, FG.t(evaluator.covers(item) ? "selfcheck.report.noResult" : "selfcheck.report.unmapped"));
      const verdict = observation.value ? stateLabel(ANSWER_STATE[observation.value] || "open") : FG.t("selfcheck.report.noVerdict");
      return h("td", null, link(item, verdict));
    };
    /* Partial evidence is a lower bound (D-168): its Partly agrees with Yes or Partly, and its No with No or Partly. */
    const consistent = (own, observation) => (partialOnly(observation) ? (observation.value === "partly" ? own !== "no" : own !== "yes") : observation.value === own);
    const verdictOf = (item) => {
      const own = answerOf(st, item);
      const seen = evaluators.map((evaluator) => latest(item, evaluator.id)).filter((observation) => observation && observation.value);
      if (!own || own === "unknown" || own === "na" || !seen.length) return "none";
      return seen.every((observation) => consistent(own, observation)) ? "agree" : "differ";
    };
    return [
      h("h3", { id: "results-agreement" }, FG.t("selfcheck.report.agreementTitle")),
      h("p", { class: "small" }, FG.t("selfcheck.report.agreementIntro")),
      rows.length
        ? h(
            "div",
            { class: "table-scroll", tabindex: "0", role: "region", "aria-labelledby": "results-agreement" },
            h(
              "table",
              { class: "data-table agreement" },
              h(
                "thead",
                null,
                h(
                  "tr",
                  null,
                  h("th", { scope: "col" }, FG.t("selfcheck.report.question")),
                  h("th", { scope: "col" }, FG.t("selfcheck.report.yours")),
                  evaluators.map((evaluator) => {
                    const resource = FG.get("#resource-" + evaluator.resource) || { name: evaluator.id };
                    return h("th", { scope: "col" }, h("span", { class: "evaluator-name" }, FG.serviceBadge(evaluator.id, resource.url), h("span", null, FG.text(resource.name))));
                  }),
                  h("th", { scope: "col" }, FG.t("selfcheck.report.agree"))
                )
              ),
              h(
                "tbody",
                null,
                rows.map((item) =>
                  h(
                    "tr",
                    { "data-agreement": verdictOf(item) },
                    /* Each row names its question, so the table reads without the question list beside it. */
                    h("th", { scope: "row", class: "agreement-question" }, h("button", { type: "button", class: "button-link", onclick: () => jumpToItem(check, item) }, h("span", { class: "item-id" }, numberOf(item)), " ", FG.span(item.text))),
                    h("td", null, link(item, answerOf(st, item) ? stateLabel(itemState(st, item)) : h("span", { class: "muted" }, FG.t("selfcheck.state.open")))),
                    evaluators.map((evaluator) => cell(item, evaluator)),
                    h("td", { class: "agreement-verdict" }, FG.t("selfcheck.report.agreement." + verdictOf(item)))
                  )
                )
              )
            )
          )
        : h("p", { class: "muted" }, FG.t("selfcheck.report.agreementNone")),
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
      groupsOf(check, shown).map((group) => {
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

  const escapeMarkdown = (value) => String(value).replace(/([\\|[\]<>*_`#])/g, "\\$1");

  function markdown(check, st) {
    st = Object.assign({}, st, SC.portableState(check, st));
    const items = resultItems(check, st);
    const { gaps, tasks } = outcomes(check, st);
    const lines = ["# " + escapeMarkdown(FG.text(check.name)) + " (" + FG.formatDate(today()) + ")", ""];
    if (st.target) {
      const named = st.targetInfo && (st.targetInfo.name || st.targetInfo.publisher);
      lines.push(escapeMarkdown(FG.t("selfcheck.targetLabel") + ": " + (named ? named + " (" + st.target + ")" : st.target)), "");
    }
    const answered = items.filter((item) => answerOf(st, item)).length;
    const counts = {};
    for (const item of items) counts[itemState(st, item)] = (counts[itemState(st, item)] || 0) + 1;
    lines.push(escapeMarkdown(resultLead(items, answered, gaps, tasks, counts)), "", escapeMarkdown(advisory(check)), "");
    const row = (cells) => "| " + cells.map((cell) => escapeMarkdown(cell).replace(/\n/g, " ")).join(" | ") + " |";
    if (profilesOf(check).length) {
      lines.push("## " + FG.t("selfcheck.result.gate"), "", row([FG.t("selfcheck.result.condition"), FG.t("selfcheck.result.state")]), "| --- | --- |");
      for (const item of applicable(check, st)) lines.push(row([item.identifier + " " + FG.text(item.text), FG.t("selfcheck.state." + itemState(st, item))]));
    } else {
      lines.push("## " + FG.t("selfcheck.result.principles"), "", row([FG.t("selfcheck.result.principle"), FG.t("selfcheck.result.state"), FG.t("selfcheck.result.answered")]), "| --- | --- | --- |");
      for (const entry of principleRows(check, st)) lines.push(row([entry.principle.termCode, FG.t("selfcheck.state." + entry.state), FG.t("selfcheck.result.ofTotal", { n: entry.answered, total: entry.total })]));
      lines.push("", escapeMarkdown(FG.t("selfcheck.result.scope")));
    }
    lines.push("", "## " + FG.t("selfcheck.result.gaps"), "");
    if (!gaps.length) lines.push(escapeMarkdown(FG.t(tasks.length ? "selfcheck.result.noGapsTasks" : "selfcheck.result.noGaps")));
    for (const item of gaps) {
      const station = FG.get(item.fixAt);
      const where = station ? `${FG.t("selfcheck.result.whereFix")}: [${escapeMarkdown(FG.text(station.name))}](${FG.pageAddress()}${FG.href("path", station.identifier)})` : "";
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
      lines.push(`- **${item.identifier}** ${escapeMarkdown(FG.text(item.text))}: **${escapeMarkdown(answerText(st, item))}**`, "");
      for (const property of ["implementationLayers", "implementationSeams"]) {
        const terms = FG.refs(item, property);
        if (terms.length) lines.push(FG.t("catalogue.relation." + property) + ": " + terms.map((term) => `[${escapeMarkdown(FG.text(term.name))}](${FG.pageAddress()}${FG.entryHref(term)})`).join(", "), "");
      }
      if (details) lines.push(...details.split("\n").map((line) => "> " + escapeMarkdown(line)), "");
    }
    const context = applicable(check, st).filter((item) => item.assessmentContext);
    if (context.length) {
      lines.push("", "## " + FG.t("selfcheck.question.context"), "");
      for (const item of context) lines.push(`- **${item.identifier}** ${escapeMarkdown(FG.text(item.text))}${answerOf(st, item) ? " · " + escapeMarkdown(FG.t("selfcheck.question.previousAnswer") + ": " + answerText(st, item)) : ""}`);
    }
    if (providers) lines.push(...providers.markdownLines(check, st, escapeMarkdown));
    const run = currentRun(check, st);
    if (run && Object.keys(run.verdicts).length) {
      lines.push("", "## " + FG.t("selfcheck.evidence.log"), "");
      for (const [key, result] of Object.entries(run.verdicts)) {
        lines.push("### " + escapeMarkdown(key), "", escapeMarkdown(FG.t("selfcheck.champion." + (result.value || "none"))), "");
        if (result.error) lines.push(escapeMarkdown(FG.t("selfcheck.evidence.requestError") + " " + result.error), "");
        if (result.log) lines.push(escapeMarkdown(FG.t("selfcheck.evidence.originalLog")), "", ...result.log.split(/\r?\n/).map((line) => "> " + escapeMarkdown(line)), "");
        if (result.truncated) lines.push(escapeMarkdown(FG.t("selfcheck.evidence.bounded")), "");
      }
    }
    lines.push("", `${FG.t("selfcheck.export.generatedBy")}, ${FG.config.version}: ${FG.pageAddress()}`, "");
    /* Hidden from readers: the answers as in a shared link, with the format and guide versions, and the whole state
       the JSON-LD carries (identifiers, what they are, evidence), so the summary loads back completely. */
    lines.push(`<!-- fair-guide-result v${FG.list(st.assessments).length ? FORMAT_VERSION : 2} guide=${FG.config.version}: ${check.identifier} ${SC.sharePayload(check, st)} -->`);
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
    st = Object.assign({}, st, SC.portableState(check, st));
    const vocab = FG.config.vocab;
    const guideCrate = FG.siteAddress() + "ro-crate-metadata.json";
    const now = new Date().toISOString();
    const target = st.target ? { "@id": st.target } : undefined;
    const members = [];
    const tests = [];
    for (const item of answerable(check, st)) {
      const value = answerOf(st, item);
      if (!value || value === "na") continue;
      /* The manual test of the question in the guide's API, which an exported result can be followed to. */
      const testId = FG.siteAddress() + FG.config.api.files.test.replace("{id}", item.identifier);
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
        implementationLayers: FG.refIds(item, "implementationLayers").map((id) => ({ "@id": guideCrate + id })),
        implementationSeams: FG.refIds(item, "implementationSeams").map((id) => ({ "@id": guideCrate + id })),
      });
      tests.push({ "@id": testId, "@type": "CreativeWork", additionalType: { "@id": vocab.ftr + "Test" }, name: item.identifier + ": " + FG.text(item.text) });
    }
    const run = currentRun(check, st);
    const probeVerdicts = run ? run.records.flatMap((record, index) => championTests(check, st).map((test) => Object.assign({ test: test.id, target: record, index }, run.verdicts[verdictKey(test.id, record)]))) : FG.list(st.verdicts);
    for (const verdict of probeVerdicts) {
      if (!verdict || !["pass", "fail", "indeterminate"].includes(verdict.value) || !verdict.test) continue;
      const test = FG.sourceEntity("fair-champion", verdict.test);
      if (!test) continue;
      members.push({
        "@id": "#result-" + verdict.test + (run && run.records.length > 1 ? "-" + verdict.index : ""),
        "@type": ["CreativeWork", "TestResult"],
        name: FG.text(test.name),
        "prov:value": verdict.value,
        "ftr:completion": verdict.value === "pass" ? 1 : verdict.value === "fail" ? 0 : undefined,
        "ftr:outputFromTest": { "@id": test.url },
        "ftr:assessmentTarget": verdict.target ? { "@id": verdict.target } : target,
        "ftr:log": verdict.log ? String(verdict.log) : undefined,
        "prov:wasGeneratedBy": { "@id": "#run" },
        implementationLayers: FG.refIds(test, "implementationLayers").map((id) => ({ "@id": guideCrate + id })),
        implementationSeams: FG.refIds(test, "implementationSeams").map((id) => ({ "@id": guideCrate + id })),
      });
      tests.push({ "@id": test.url, "@type": "CreativeWork", additionalType: { "@id": vocab.ftr + "Test" }, name: FG.text(test.name) });
    }
    /* Optional evaluators' native results, each generated by its own assessment activity. */
    const provided = providers ? providers.crateMembers(check, st, target) : { members: [], activities: [], tests: [] };
    members.push(...provided.members);
    tests.push(...provided.tests);
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
        url: FG.pageAddress(),
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
      ...provided.activities,
      ...tests.filter((test, index, all) => all.findIndex((other) => other["@id"] === test["@id"]) === index),
    ];
    const records = new Set(members.map((member) => member["prov:used"] && member["prov:used"]["@id"]).filter(Boolean));
    for (const member of members) if (member["ftr:assessmentTarget"]) records.add(member["ftr:assessmentTarget"]["@id"]);
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
          guideState: vocab.guideTerms.guideState,
          implementationLayers: { "@id": vocab.guideTerms.implementationLayers, "@type": "@id" },
          implementationSeams: { "@id": vocab.guideTerms.implementationSeams, "@type": "@id" },
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
      items[item.identifier] = { value: answerOf(st, item), origin: entry.origin || null, prefill: entry.prefill || null, observations: observationsOf(entry) };
    }
    /* Attached evaluator assessments need format revision 3; a result without them stays readable by earlier
       versions of the guide. Original reports travel only in the complete evidence download. */
    const assessments = FG.providers ? FG.providers.portable(st) : [];
    return boundedPortable({
      format: FORMAT,
      v: assessments.length ? FORMAT_VERSION : 2,
      guideVersion: FG.config.version,
      check: check.identifier,
      mode: st.mode || null,
      profile: st.profile || null,
      target: st.target || null,
      targetInfo: st.targetInfo || null,
      pid: st.pid || null,
      nkr: st.nkr || null,
      steward: st.steward || null,
      re3data: st.re3data || null,
      fip: st.fip || null,
      software: st.software || null,
      softwareRef: st.softwareRef || null,
      sample: st.sample || null,
      dataciteSample: st.dataciteSample || null,
      champion: st.champion || null,
      inspection: st.inspection || null,
      assessments: assessments.length ? assessments : undefined,
      items,
    });
  };

  function boundedPortable(data) { return inspection ? inspection.boundedPortable(data) : data; }

  /** Notes for a loaded result: questions this version does not know, and a file from another guide version. */
  function loadNotices(skipped, version) {
    const notices = [];
    if (skipped) notices.push(FG.t("selfcheck.load.skipped", { n: skipped }));
    if (version && version !== FG.config.version) notices.push(FG.t("selfcheck.load.otherVersion", { version, current: FG.config.version }));
    return notices;
  }

  const isText = (value, max) => typeof value === "string" && value.length <= max;
  const webUrl = (value) => {
    if (!isText(value, 2000) || /\s/.test(value)) return null;
    try { const url = new URL(value); return /^https?:$/.test(url.protocol) && !url.username && !url.password && url.href.length <= 2000 ? url.href : null; } catch (error) { return null; }
  };
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
          for (const [key, value] of Object.entries(note.params || {}).slice(0, 4)) if (!FG.unsafeKey(key) && isText(key, 50) && isText(value, 300)) params[key] = value;
          return { key: "selfcheck.note." + note.key.replace("selfcheck.note.", ""), params };
        }
        const text = textValue(note.text);
        return text ? { text } : null;
      })
      .filter(Boolean);
    const list = (Array.isArray(pre.list) ? pre.list.slice(0, 20) : [])
      .filter((fer) => fer && isText(fer.name, 300))
      .map((fer) => ({ name: fer.name, url: webUrl(fer.url), status: FIP_RANK.includes(fer.status) ? fer.status : undefined }));
    let remaining = EVIDENCE_MAX;
    let truncated = Boolean(pre.truncated) || (Array.isArray(pre.fields) && pre.fields.length > 12);
    const fields = (Array.isArray(pre.fields) ? pre.fields.slice(0, 12) : [])
      .filter((field) => field && isText(field.path, 300) && Array.isArray(field.values))
      .map((field) => {
        const raw = field.values.filter((value) => typeof value === "string");
        const values = raw.slice(0, 8).map((value) => {
          const kept = value.slice(0, Math.min(VALUE_MAX, Math.max(0, remaining)));
          remaining -= kept.length;
          if (kept.length < value.length) truncated = true;
          return kept;
        }).filter(Boolean);
        return { path: field.path, values, more: (Number.isInteger(field.more) && field.more > 0 ? field.more : 0) + raw.length - values.length };
      });
    const testId = isText(pre.testId, 100) && /^guide-[a-z]+-\d{2}$/.test(pre.testId) && FG.get("#test-" + pre.testId) ? pre.testId : null;
    const assessment = FG.providers && FG.providers.isAssessmentId(pre.assessment) ? pre.assessment : null;
    return { source: pre.source, date: pre.date, value: ANSWERS.includes(pre.value) ? pre.value : null, notes, list, fields, record: webUrl(pre.record), subject: isText(pre.subject, 2000) ? pre.subject : null, representation: isText(pre.representation, 2000) ? pre.representation : null, commit: isText(pre.commit, 100) ? pre.commit : null, coverage: isText(pre.coverage, 300) ? pre.coverage : null, testId, assessment, truncated };
  }

  /** A check state from a file the guide wrote, or the reason it cannot be read: not a guide file, a newer format,
      a check this version does not know, or a damaged file. Questions this version does not know are skipped. */
  function readChampion(data, check, st) {
    if (!data || !isText(data.input, 6000) || !Array.isArray(data.records) || !data.records.length || data.records.length > SAMPLE_MAX ||
        !data.records.every((url) => webUrl(url)) || !/^\d{4}-\d{2}-\d{2}$/.test(String(data.date)) ||
        !data.verdicts || typeof data.verdicts !== "object" || Array.isArray(data.verdicts)) return null;
    const allowed = new Set(championTests(check, st).flatMap((test) => data.records.map((record) => verdictKey(test.id, record))));
    const verdicts = {};
    for (const [key, result] of Object.entries(data.verdicts)) {
      if (!allowed.has(key)) continue;
      if (!result || (result.value !== null && !VERDICTS.includes(result.value))) return null;
      verdicts[key] = { value: result.value, log: isText(result.log, LOG_MAX) ? result.log : typeof result.log === "string" ? result.log.slice(0, LOG_MAX) : "",
        error: typeof result.error === "string" ? result.error.slice(0, 1000) : undefined,
        truncated: Boolean(result.truncated) || (typeof result.log === "string" && result.log.length > LOG_MAX),
        invocation: result.invocation && result.invocation.method === "POST" && webUrl(result.invocation.url) && result.invocation.body && webUrl(result.invocation.body.resource_identifier) ?
          { url: webUrl(result.invocation.url), method: "POST", body: { resource_identifier: webUrl(result.invocation.body.resource_identifier) } } : null };
    }
    return { input: data.input, records: data.records, date: data.date, verdicts };
  }

  SC.readPortable = function (data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) return { error: "damaged" };
    if (data.format !== undefined && data.format !== FORMAT) return { error: "notGuide" };
    if (Number.isInteger(data.v) && data.v > FORMAT_VERSION) return { error: "newer", params: { version: isText(data.guideVersion, 40) ? data.guideVersion : "?" } };
    if (![1, 2, FORMAT_VERSION].includes(data.v) || !isText(data.check, 50)) return { error: "damaged" };
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
      const observations = Array.isArray(entry.observations) ? entry.observations.slice(-OBSERVATION_MAX).map(readPrefill) : prefill ? [prefill] : [];
      if (observations.some((seen) => !seen)) return { error: "damaged" };
      const manual = entry.origin === "user" || (entry.value && (!prefill || entry.value !== prefill.value));
      items[id] = Object.assign({ origin: manual ? "user" : "shared", imported: true, observations }, entry.value ? { value: entry.value } : {}, prefill ? { prefill } : {});
    }
    const state = { mode: data.mode, profile: data.profile, extended: true, target: webUrl(data.target), items };
    if (isText(data.pid, 300)) state.pid = data.pid;
    if (isText(data.nkr, 100) && /^[\w.:-]+$/.test(data.nkr)) state.nkr = data.nkr;
    if (isText(data.steward, 40) && FG.live.parseOrcid(data.steward)) state.steward = FG.live.parseOrcid(data.steward);
    if (isText(data.re3data, 20) && FG.live.parseRe3data(data.re3data) === data.re3data) state.re3data = data.re3data;
    if (isText(data.fip, 100) && /^[\w.-]+$/.test(data.fip)) state.fip = data.fip;
    if (isText(data.software, 1000)) state.software = data.software;
    if (isText(data.softwareRef, 200)) state.softwareRef = data.softwareRef;
    if (isText(data.sample, 6000)) state.sample = data.sample;
    const drawn = data.dataciteSample;
    /* A sample saved before samples spanned every record type still loads; its type is no longer kept. */
    if (drawn && typeof drawn === "object" && drawn.repository && FG.live.dataciteRoute({ datacite: drawn.repository.id }) &&
        /^\d{4}-\d{2}-\d{2}$/.test(String(drawn.date))) {
      state.dataciteSample = {
        repository: { id: drawn.repository.id, name: isText(drawn.repository.name, 300) ? drawn.repository.name : drawn.repository.id },
        date: drawn.date,
        records: FG.list(drawn.records).slice(0, SAMPLE_MAX)
          .filter((record) => record && isText(record.doi, 300) && (FG.live.parsePid(record.doi) || {}).type === "doi" && isText(record.title || "", 300))
          .map((record) => ({ doi: record.doi.toLowerCase(), title: record.title || "", type: isText(record.type || "", 60) ? record.type || "" : "" })),
      };
    }
    if (data.inspection && typeof data.inspection === "object" && /^\d{4}-\d{2}-\d{2}$/.test(String(data.inspection.date))) {
      state.inspection = { date: data.inspection.date, coverage: {}, representations: FG.list(data.inspection.representations).slice(0, 8)
        .filter((entry) => entry && webUrl(entry.url) && isText(entry.format, 100) && isText(entry.source, 80))
        .map((entry) => ({ url: webUrl(entry.url), format: entry.format, source: entry.source })), diagnostics: FG.list(data.inspection.diagnostics).slice(0, 20)
        .filter((entry) => entry && isText(entry.code, 80) && isText(entry.message, 500))
        .map((entry) => ({ code: entry.code, source: isText(entry.source, 80) ? entry.source : "landing", url: webUrl(entry.url), message: entry.message })) };
    }
    if (data.champion != null) {
      const restored = readChampion(data.champion, check, state);
      if (!restored) return { error: "damaged" };
      state.champion = restored;
      if (restored.records.length === 1) state.verdicts = Object.entries(restored.verdicts).map(([key, result]) => Object.assign({ test: key.split(" ")[0] }, result));
    }
    if (data.targetInfo && typeof data.targetInfo === "object") {
      const info = {};
      for (const key of ["name", "creators", "publisher", "year", "kind", "url", "commit", "ref"]) if (isText(String(data.targetInfo[key] || ""), 300) && data.targetInfo[key]) info[key] = String(data.targetInfo[key]);
      if (info.url && !webUrl(info.url)) delete info.url;
      if (info.name || info.publisher) state.targetInfo = info;
    }
    if (data.assessments != null) {
      if (data.v < 3 || !Array.isArray(data.assessments) || !FG.providers) return { error: "damaged" };
      const assessments = data.assessments.slice(0, 8).map(FG.providers.readAssessment);
      if (assessments.some((assessment) => !assessment)) return { error: "damaged" };
      if (assessments.length) state.assessments = assessments;
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
      let found;
      try {
        found = SC.readPortable(JSON.parse(holder.guideState));
      } catch (error) {
        return { error: "damaged" };
      }
      /* A complete evidence download also carries the original evaluator reports its assessments name. */
      if (!found.error && typeof holder.guideSources === "string") {
        try {
          found.sources = JSON.parse(holder.guideSources);
        } catch (error) {
          return { error: "damaged" };
        }
      }
      return found;
    }
    /* The guide's own markers start a line; text in the summary always escapes "<", so a value can never start one. */
    const match = String(text).match(/^<!--\s*fair-guide-result(?:\s+v(\d+))?(?:\s+guide=(\S+?))?:\s*([a-z-]+)\s+(a\d+\.[A-Za-z0-9._]+)\s*-->/m);
    if (!match) return { error: "notGuide" };
    if (Number(match[1] || FORMAT_VERSION) > FORMAT_VERSION) return { error: "newer", params: { version: match[2] || "?" } };
    const check = FG.get("#check-" + match[3]);
    if (!check) return { error: "unknownCheck" };
    const carried = String(text).match(/^<!--\s*fair-guide-state\b([\s\S]*?)^-->/m);
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
    SC.pendingFile = { check: found.check.identifier, state: found.state, notices: found.notices || [], sources: found.sources || null };
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
        /* The browser refused to save the answers; say so instead of letting work vanish on the next visit. */
        FG.storageFull ? h("p", { class: "notice small", role: "alert", id: "local-data-full" }, FG.t("localData.notSaved")) : null,
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

  /* The About page shows the same note in its privacy section. */
  SC.localDataNote = localDataNote;

  const fileName = (check, extension) => "fair-self-check-" + check.identifier + "-" + today() + "." + extension;

  SC.sharePayload = function (check, st) {
    /* Version a2: a question by its number, since the link names its check. */
    const parts = ["a2", st.mode || "_", st.profile || "_"];
    for (const item of itemsOf(check)) {
      const value = answerOf(st, item);
      if (value) parts.push(numberOf(item) + SHARE_CODE[value]);
    }
    return parts.join(".");
  };

  /** Read the answers in a shared link; questions this version does not know are skipped and counted, anything
      else unexpected makes the whole link invalid. */
  SC.parseShare = function (check, payload) {
    const parts = String(payload || "").split(".");
    if (parts[0] !== "a2" || parts.length < 3) return null;
    const codes = Object.fromEntries(Object.entries(SHARE_CODE).map(([value, letter]) => [letter, value]));
    const byNumber = new Map(itemsOf(check).map((item) => [numberOf(item), item.identifier]));
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
      const match = part.match(/^(\d{2})([a-z])$/);
      if (!match || !codes[match[2]]) return null;
      if (!byNumber.has(match[1])) {
        shared.skipped += 1;
        continue;
      }
      shared.items[byNumber.get(match[1])] = { value: codes[match[2]], origin: "shared" };
    }
    return shared;
  };

  function shareUrl(check, st) {
    const base = FG.pageAddress();
    return base + FG.href("check", check.identifier) + "/" + SC.sharePayload(check, st);
  }

  function showShare(check, st) {
    const url = shareUrl(check, st);
    FG.renderList("share-output", () =>
      fragment(
        h("label", { for: "share-url" }, FG.t("selfcheck.export.shareLabel")),
        h("div", { class: "inline" }, h("input", { id: "share-url", type: "text", readonly: true, value: url }), h("button", { type: "button", onclick: (event) => FG.copyText(event, url, "share-url") }, FG.t("common.copy"))),
        h("p", { class: "small" }, FG.t("selfcheck.export.shareNote"))
      )
    );
    const field = document.getElementById("share-url");
    if (field) field.focus();
  }

  /** The result set with every retained original evaluator report, lossless and loadable like any saved result. */
  function completeEvidence(check, st) {
    const crate = SC.ftrCrate(check, st);
    const root = crate["@graph"].find((entity) => entity["@id"] === "./");
    root.guideSources = JSON.stringify(providers ? providers.sources(st) : {});
    root.description = root.description + " " + FG.t("selfcheck.export.evidenceScope");
    crate["@context"][1].guideSources = FG.config.vocab.guideTerms.guideSources;
    return JSON.stringify(crate, null, 2) + "\n";
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
    if (providers) providers.forget(check);
    if (FG.providers) FG.providers.pruneSources();
    save();
    FG.rerender("export-title");
  }

  /** Whether a check has an answer, given or pre-filled, for the exports, the share link and clearing to act on. */
  const hasAnswers = (st) => Object.values(st.items || {}).some((entry) => entry && typeof entry === "object" && entry.value);
  /* The reason the export controls give while the check has no answer; answering refreshes it in place. */
  let exportGate = null;

  function exportSection(check, st) {
    const download = h(
      "button",
      {
        type: "button",
        class: "button-small button-primary",
        id: "export-download",
        onclick: () => FG.download(fileName(check, exportFormat === "jsonld" ? "jsonld" : "md"), exportText(check, st), exportFormat === "jsonld" ? "application/ld+json" : "text/markdown"),
      },
      FG.icon("download"),
      FG.t("selfcheck.export.download")
    );
    const copy = h("button", { type: "button", class: "button-small", id: "export-copy", onclick: (event) => FG.copyText(event, exportText(check, st), "export-preview-text") }, FG.icon("copy"), h("span", { class: "copy-label" }, FG.t("common.copy")));
    const share = h("button", { type: "button", class: "button-small", id: "share-create", onclick: () => showShare(check, st) }, FG.icon("link"), FG.t("selfcheck.export.share"));
    const clear = h("button", { type: "button", class: "button-link", id: "answers-clear", onclick: () => clearAnswers(check) }, FG.t("selfcheck.reset"));
    exportGate = FG.gate([download, copy, share, clear], FG.t("selfcheck.export.needsAnswer"), () => hasAnswers(st));
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
      h("div", { class: "export-actions" }, download, copy),
      exportGate,
      h(
        "details",
        { class: "export-preview", ontoggle: (event) => event.target.open && refreshPreview(check, st) },
        h("summary", null, FG.t("selfcheck.export.preview")),
        h("textarea", { id: "export-preview-text", readonly: true, rows: "14", "aria-label": FG.t("selfcheck.export.preview") })
      ),
      h("p", { class: "small muted" }, FG.t("selfcheck.export.formats")),
      /* The summary and the result set carry assessments compactly; the complete download adds every retained
         original report, so nothing accepted is lost to the summary's size budget. */
      providers && FG.list(st.assessments).length
        ? h("p", { class: "export-evidence small" },
          h("button", { type: "button", class: "button-small", id: "export-evidence", onclick: () => FG.download(fileName(check, "evidence.jsonld"), completeEvidence(check, st), "application/ld+json") }, FG.icon("download"), FG.t("selfcheck.export.evidence")),
          " ", FG.t("selfcheck.export.evidenceHint"))
        : null,
      h(
        "div",
        { class: "export-more" },
        share,
        h("button", { type: "button", class: "button-small", onclick: () => window.print() }, FG.icon("print"), FG.t("selfcheck.export.print")),
        /* The check itself as data: its benchmark in the guide's API, with each question as a metric and its test. */
        FG.recordHref(check) ? h("a", { class: "button button-small", id: "export-data", href: FG.recordHref(check), type: "application/json" }, FG.icon("code"), FG.t("selfcheck.export.data")) : null
      ),
      h("div", { id: "share-output", class: "share-output" }),
      h("p", null, clear)
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
    /* The answers are saved before any original report is kept; reports are kept only when their digest verifies,
       and their records are then rebuilt from them. */
    const use = async () => {
      const sources = fromFile && SC.pendingFile ? SC.pendingFile.sources : null;
      FG.state.answers[check.identifier] = shared;
      reapplied.delete(check.identifier);
      if (providers) providers.forget(check);
      if (FG.providers) FG.providers.pruneSources();
      SC.pendingFile = null;
      save();
      if (providers && FG.list(shared.assessments).length) {
        await providers.restoreSources(shared, sources);
        save();
      }
      /* The adopted answers are what the reader came for. */
      FG.navigate(partHref(check, "answers"));
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
    const go = () => {
      if (!document.getElementById("item-" + keyOf(item)) && !st.extended) {
        st.extended = true;
        save();
        FG.rerender();
      }
      jumpTo(document.getElementById("item-" + keyOf(item)));
    };
    /* The questions are in the answers part; from the evidence or the report, it opens first. */
    if (partOf(FG.parseHash(window.location.hash)) !== "answers") {
      window.addEventListener("hashchange", () => requestAnimationFrame(go), { once: true });
      FG.navigate(partHref(check, "answers"));
      return;
    }
    go();
  }

  /** The questions in the same groups as the list, with a short label for each group. */
  function summaryGroups(check, items) {
    return groupsOf(check, items).map((group) => ({ label: groupMark(group), name: groupName(group), items: group.items }));
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
    const groups = summaryGroups(check, shown);
    /* The gaps and the things to find out are listed in the report. */
    const count = (key, n) =>
      n
        ? h("a", { class: "summary-count", "data-kind": key, href: partHref(check, "report") }, FG.t("selfcheck.summary." + key, { n }))
        : h("span", { class: "summary-count summary-count-none", "data-kind": key }, FG.t("selfcheck.summary." + key, { n }));
    return [
      h("p", { class: "summary-progress" }, FG.t("selfcheck.progress", { n: answered, total: items.length })),
      hiddenAnswers(check, st),
      groups.map((group) =>
        h(
          "div",
          { class: "summary-group" },
          h("span", { class: "summary-group-label", title: group.name }, group.label),
          distribution(st, group.items, true),
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
                  numberOf(item),
                  h("span", { class: "visually-hidden" }, " " + name + ": " + FG.t("selfcheck.state." + state))
                )
              );
            })
          )
        )
      ),
      h("p", { class: "summary-counts" }, count("gaps", gaps.length), count("tasks", tasks.length)),
      h("p", { class: "summary-full" }, h("a", { class: "button button-small button-primary", href: partHref(check, "report") }, FG.t("selfcheck.parts.report") + " →")),
    ];
  }

  /** The result so far beside the questions; a small icon collapses it, and the choice is remembered. */
  function summaryPanel(check, st) {
    const collapsed = Boolean(FG.state.resultCollapsed);
    const toggle = () => {
      FG.state.resultCollapsed = !collapsed;
      FG.saveState();
      FG.keepScroll = window.scrollY;
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
    const part = partOf(route);
    const head = [
      h("p", { class: "muted" }, h("a", { href: FG.href("selfcheck") }, FG.t("selfcheck.title"))),
      FG.heading(1, null, FG.span(check.name)),
      FG.linkedParagraphs(check, "description"),
      minutes ? h("p", { class: "muted" }, FG.t("station.minutes", { n: minutes })) : null,
      /* The note on local data heads the evidence; the other parts carry only its alert when the browser refused to
         save, so work never vanishes unannounced. */
      part === "evidence" ? localDataNote() : part && FG.storageFull ? h("p", { class: "notice small", role: "alert", id: "local-data-full" }, FG.t("localData.notSaved")) : null,
    ];
    if (!part) return h("div", { class: "layout wrap selfcheck" }, h("article", null, head, sharedView(check, route.extra)));
    reapplyEvidence(check);
    const st = stateOf(check);
    const choose = [h("div", { class: "no-print" }, settings(check, st)), h("p", { class: "notice" }, FG.t("selfcheck.chooseFirst"))];
    if (!ready(check, st) || part === "evidence") {
      /* Evidence: what the check is about and the sources answers can be suggested from. */
      return h(
        "div",
        { class: "wrap selfcheck check-view check-evidence" },
        h("header", { class: "check-head" }, head, partsNav(check, st, part)),
        h(
          "article",
          { class: "check-main" },
          ready(check, st) ? h("div", { class: "no-print" }, settings(check, st)) : choose,
          startPanel(check, st, ready(check, st)),
          ready(check, st) ? partNext(check, "answers") : null
        )
      );
    }
    if (part === "report") {
      return h(
        "div",
        { class: "wrap selfcheck check-view check-report" },
        h("header", { class: "check-head" }, head, partsNav(check, st, part)),
        h(
          "article",
          { class: "check-main" },
          h(
            "section",
            { class: "results", "aria-labelledby": "results-title" },
            h("h2", { id: "results-title", tabindex: "-1" }, FG.t("selfcheck.result.title")),
            h("div", { id: "results" }, results(check, st))
          ),
          exportSection(check, st)
        )
      );
    }
    return h(
      "div",
      { class: "wrap selfcheck check-view check-answers" },
      h("header", { class: "check-head" }, head, partsNav(check, st, part)),
      h(
        "div",
        { class: "check-split" + (FG.state.resultCollapsed ? " result-collapsed" : "") },
        h(
          "article",
          { class: "check-main" },
          /* What a test run from a question card reports, kept in view while the reader works down the questions. */
          h("p", { id: "prefill-status", role: "status", class: "small part-status" }, status.check === check.identifier && status.part === "answers" ? status.text : ""),
          itemsSection(check, st),
          partNext(check, "report")
        ),
        summaryPanel(check, st)
      )
    );
  }

  /* ---------------------------------------------------------------- the check's parts */

  /* A check reads as three parts, each with its own address: the evidence answers can come from, the answers, and
     the report. The check's own address opens the evidence. */
  const PARTS = ["evidence", "answers", "report"];
  const partOf = (route) => (PARTS.includes(route.extra) ? route.extra : route.extra ? null : "evidence");
  const partHref = (check, part) => FG.href("check", check.identifier) + "/" + part;

  /** How far the answers are, as the answers step says it; answering updates it in place. */
  function answersNote(check, st) {
    if (!ready(check, st)) return FG.t("selfcheck.parts.answersWaiting");
    const items = resultItems(check, st);
    return FG.t("selfcheck.parts.answersNote", { n: items.filter((item) => answerOf(st, item)).length, total: items.length });
  }

  /** The three parts as numbered steps, the current one marked; each step says what it holds or how far it is. */
  function partsNav(check, st, part) {
    const notes = {
      evidence: FG.t("selfcheck.parts.evidenceNote"),
      answers: answersNote(check, st),
      report: FG.t("selfcheck.parts.reportNote"),
    };
    return h(
      "nav",
      { class: "check-parts no-print", "aria-label": FG.t("selfcheck.parts.label") },
      h(
        "ol",
        null,
        PARTS.map((key, index) =>
          h(
            "li",
            null,
            h(
              "a",
              { class: "check-part", href: partHref(check, key), "aria-current": key === part ? "step" : null },
              h("span", { class: "check-part-number", "aria-hidden": "true" }, h("span", null, String(index + 1))),
              h("span", { class: "check-part-text" }, h("strong", null, FG.t("selfcheck.parts." + key)), h("span", { class: "small", id: "parts-" + key + "-note" }, notes[key]))
            )
          )
        )
      )
    );
  }

  /** The way on to the next part, at the end of a part. */
  const partNext = (check, part) =>
    h("p", { class: "part-next no-print" }, h("a", { class: "button button-primary", href: partHref(check, part) }, FG.t("selfcheck.parts.to." + part) + " →"));

  /** How many questions a check asks: a range when its mode or profile decides, one number otherwise. */
  function questionCount(check) {
    const modes = modesOf(check).map((term) => term.termCode);
    const profiles = profilesOf(check).map((term) => term.termCode);
    const choices = (modes.length ? modes : [null]).flatMap((mode) => (profiles.length ? profiles : [null]).map((profile) => ({ mode, profile })));
    const counts = choices.map((choice) => itemsOf(check).filter((item) => applies(item, choice)).length);
    const low = Math.min(...counts);
    const high = Math.max(...counts);
    return low === high ? FG.t("selfcheck.items", { n: low }) : FG.t("selfcheck.itemsRange", { low, high });
  }

  /** A check as a card: its icon and name, what it is for, how long it takes and for whom, progress once started. */
  function checkCard(check) {
    const st = hasState(check) ? stateOf(check) : null;
    const items = st ? resultItems(check, st) : [];
    const total = items.length;
    const answered = items.filter((item) => answerOf(st, item)).length;
    /* A check already filled in shows its result as the report's chips do, one per answer state. */
    const counts = {};
    for (const item of answered ? items : []) counts[itemState(st, item)] = (counts[itemState(st, item)] || 0) + 1;
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
      /* What the check is for comes first, so NRP conditions, FAIR maturity and certification are told apart. */
      FG.ui.selfcheck.purpose && FG.ui.selfcheck.purpose[check.identifier]
        ? h("p", { class: "check-card-purpose", "data-check": check.identifier }, h("span", { class: "check-card-purpose-label" }, FG.t("selfcheck.purpose.label") + ": "), FG.t("selfcheck.purpose." + check.identifier))
        : null,
      FG.linkedParagraphs(check, "description"),
      h("p", { class: "check-card-meta" }, meta.join(" · ")),
      answered
        ? h(
            "div",
            { class: "check-progress" },
            h("progress", { max: String(total), value: String(answered), "aria-label": FG.t("selfcheck.progress", { n: answered, total }) }),
            h("span", null, FG.t("selfcheck.progress", { n: answered, total })),
            h(
              "ul",
              { class: "result-counts check-card-counts" },
              ["met", "partly", "gap", "unknown", "open"]
                .filter((state) => counts[state])
                .map((state) => h("li", { "data-state": state }, h("span", { "aria-hidden": "true" }, STATE_ICON[state] + " "), FG.t("selfcheck.count." + state, { n: counts[state] })))
            )
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
    FG.offerExport({ id: "data", icon: "code", label: FG.t("export.data"), href: FG.config.api.files.record.replace("{record}", "checks") });
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
        h("details", { class: "flow-details" }, h("summary", null, FG.t("visual.evidence.title")), h("div", { class: "content" }, FG.flow("evidence"))),
        h("h2", null, FG.t("selfcheck.forLens")),
        h("ul", { class: "check-cards" }, mine.map(checkCard)),
        others.length ? [h("h2", null, FG.t("selfcheck.others")), h("ul", { class: "check-cards" }, others.map(checkCard))] : null,
        h(
          "section",
          { class: "saved-results", "aria-labelledby": "saved-title" },
          h("h2", { id: "saved-title" }, FG.t("selfcheck.savedTitle")),
          h("p", null, FG.t("selfcheck.savedText")),
          loadControl("load-file-overview"),
          h("p", { class: "small" }, h("a", { href: FG.href("page", "about") + "/privacy" }, FG.t("localData.aboutLink")))
        )
      )
    );
  }

  let inspection = null;
  let providers = null;
  let inspectionLoading = null;
  let inspectionFailed = false;
  const loadScript = (path) => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = path;
    script.onload = resolve;
    script.onerror = () => { script.remove(); reject(new Error("check module unavailable: " + path)); };
    document.head.appendChild(script);
  });
  /* The check controls and the optional evaluators load together when a check first opens; neither contacts a
     service until the reader asks. */
  function loadInspection() {
    if (!inspectionLoading) inspectionLoading = (async () => {
      await loadScript(FG.config.discovery.controlsScript);
      if (FG.config.providers && FG.config.providers.script) await loadScript(FG.config.providers.script);
      if (!SC.inspectionFactory) throw new Error("inspection module unavailable");
      inspection = SC.inspectionFactory({ FG, SC, h, stateOf, runPrefill, applyEvidence, today, webUrl, save,
        describeTarget, dataciteInfo, stewardEvidence, fieldEvidence, pathState, fieldsOf, retarget, clearableField, identifierRow, brief,
        setStatus, prefillFromRe3data, prefillFromNkr, prefillFromDashboard, prefillFromNanopub, label,
        record, answerOf, foundFields, FIELD_LABELS, readableField, valueNode, SHOWN_VALUES, noteText, observationsOf, FIP_RANK, VERDICT_ICON, running, wasRun, verdictKey });
      if (SC.providersFactory) providers = SC.providersFactory({ h, stateOf, applyEvidence, save, setStatus, record, observationsOf, keyOf, jumpToItem, inBatches, retarget });
    })().catch((error) => { inspectionLoading = null; throw error; });
    return inspectionLoading;
  }

  FG.views.selfcheck = function (route) {
    if (!inspection) {
      if (!inspectionFailed) loadInspection().then(() => FG.rerender()).catch(() => { inspectionFailed = true; FG.rerender(); });
      return h("div", { class: "wrap", role: "status" }, FG.t(inspectionFailed ? "app.error" : "app.loading"));
    }
    return route.view === "check" && FG.get("#check-" + route.arg) ? checkView(route) : overview(route);
  };
})();
