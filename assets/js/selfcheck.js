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
    const items = answerable(check, st).filter((item) => answerOf(st, item) !== "na");
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
  function applyEvidence(check, source, evidence, date) {
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
      const next = Object.assign({}, current, { prefill: { source: result.source || source, date, value, notes, list: result.list || [] } });
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

  /** Evidence describes one dataset, repository or profile; choosing another discards what the previous one gave. */
  function retarget(check, target) {
    const st = stateOf(check);
    if (st.target && st.target !== target) {
      for (const [id, entry] of Object.entries(st.items)) {
        if (!entry || typeof entry !== "object") continue;
        if (entry.origin === "prefill") delete st.items[id];
        else delete entry.prefill;
      }
    }
    st.target = target;
    save();
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
        count += applyEvidence(check, "resolver", () =>
          resolved.found
            ? { value: "yes", notes: resolved.url ? [{ key: "selfcheck.note.resolves", params: { url: resolved.url } }] : [] }
            : { value: null, notes: [{ key: "selfcheck.note.notResolved" }] },
          date
        );
      } catch (error) {
        messages.push(FG.t("selfcheck.prefill.failed", { source: label("resolver") }));
      }
      if (pid.type !== "doi") return count;
      try {
        const attributes = await FG.live.datacite(pid.value);
        if (attributes) count += applyEvidence(check, "datacite", (item, fields) => fieldEvidence(fields.map((field) => pathState(attributes, field))), date);
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
    return runPrefill(check, "nkr", "prefill-nkr-run", async () =>
      applyEvidence(check, "nkr", (item, fields) => fieldEvidence(fields.map((field) => (field === "@record" ? "present" : pathState(nkrRecord.content, field)))), today())
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
      return applyEvidence(check, "fip", (item, questions) => Object.assign(fipEvidence(questions, declarations, "principle"), { source }), date);
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
      return applyEvidence(check, "fip", (item, questions) => Object.assign(fipEvidence(questions, declarations, "question"), { source: "nanopub" }), today());
    });
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

  /** Where an answer came from: a pre-fill with its source and date, a change by the user, or a shared link. */
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
      parts.push(
        h(
          "p",
          { class: "source-chip", "data-origin": kind },
          FG.t("selfcheck.origin." + kind, Object.assign(params, { value: pre.value ? FG.t("selfcheck.answer." + pre.value) : "" }))
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
      h("div", { class: "inline" }, input, h("button", { type: "button", id: "prefill-pid-run", onclick: run }, FG.t("selfcheck.prefill.pidButton")))
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
        h("div", { class: "inline" }, nanopub, h("button", { type: "button", id: "prefill-nanopub-run", onclick: runNanopub }, FG.t("selfcheck.prefill.nanopubButton")))
      ),
    ];
  }

  function prefillPanel(check, st) {
    const sources = sourcesOf(check, st);
    const controls = [];
    if (sources.has("datacite") || sources.has("resolver")) controls.push(pidControl(check, st));
    if (sources.has("nkr")) controls.push(nkrControl(check, st));
    if (sources.has("fip")) controls.push(fipControl(check, st));
    if (!controls.length) return null;
    return h(
      "section",
      { class: "prefill no-print", "aria-labelledby": "prefill-title" },
      h("h2", { id: "prefill-title" }, FG.t("selfcheck.prefill.title")),
      h("p", { class: "small" }, FG.t("selfcheck.prefill.privacy")),
      controls,
      h("p", { id: "prefill-status", role: "status", class: "small" }, status.check === check.identifier ? status.text : "")
    );
  }

  function itemField(check, st, item) {
    const id = item.identifier;
    const meta = h(
      "div",
      { class: "badges" },
      h("span", { class: "badge" }, FG.termName(FG.id(item.tier))),
      FG.refs(item, "about").map((principle) => FG.principleTile(principle))
    );
    const statement = [h("span", { class: "item-id" }, id), " ", FG.span(item.text)];
    const clauses = FG.refs(item, "citation");
    const basedOn = clauses.length
      ? h(
          "details",
          { class: "small" },
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
      basedOn
    );
  }

  function itemsSection(check, st) {
    const all = applicable(check, st);
    const first = all.filter(isFirstTier);
    /* A check without Minimum or Required items has no short first view and shows every item. */
    const shown = st.extended || !first.length ? all : first;
    const more = first.length ? all.length - first.length : 0;
    const groups = FG.stations()
      .map((station) => ({ station, items: shown.filter((item) => FG.id(item.fixAt) === station["@id"]) }))
      .filter((group) => group.items.length);
    const loose = shown.filter((item) => !FG.get(item.fixAt));
    return h(
      "div",
      { class: "items no-print" },
      groups.map((group) =>
        h("section", { class: "item-group" }, h("h2", null, FG.t("selfcheck.fixAt", { station: FG.text(group.station.name) })), group.items.map((item) => itemField(check, st, item)))
      ),
      loose.map((item) => itemField(check, st, item)),
      more
        ? h(
            "p",
            { class: "extended" },
            h(
              "button",
              {
                type: "button",
                id: "extended-toggle",
                "aria-expanded": st.extended ? "true" : "false",
                onclick: () => {
                  st.extended = !st.extended;
                  save();
                  FG.rerender("extended-toggle");
                },
              },
              st.extended ? FG.t("selfcheck.extendedHide") : FG.t("selfcheck.extendedShow", { n: more })
            ),
            " ",
            h("span", { class: "small muted" }, FG.t("selfcheck.extendedNote"))
          )
        : null
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

  function gapItem(st, item) {
    const station = FG.get(item.fixAt);
    const who = FG.refs(item, "fixedBy").map((actor) => FG.text(actor.name));
    return h(
      "li",
      null,
      h("p", null, h("strong", null, item.identifier), " ", FG.span(item.text), " ", h("span", { class: "badge" }, FG.termName(FG.id(item.tier))), " ", stateLabel(itemState(st, item))),
      h(
        "p",
        { class: "small" },
        station ? [h("strong", null, FG.t("selfcheck.result.whereFix") + ": "), h("a", { href: FG.href("path", station.identifier) }, FG.span(station.name))] : null,
        who.length ? [station ? " · " : null, h("strong", null, FG.t("selfcheck.result.whoFix") + ": "), who.join(", ")] : null
      )
    );
  }

  function taskItem(item) {
    const ask = whom(item);
    const lookup = FG.id(item.lookup);
    return h(
      "li",
      null,
      h("p", null, h("strong", null, item.identifier), " ", FG.span(item.text)),
      h(
        "p",
        { class: "small" },
        ask.names.length ? FG.t("selfcheck.result.ask", { whom: ask.names.join(", ") }) : null,
        lookup ? [ask.names.length ? " · " : null, FG.external(lookup, FG.t("selfcheck.result.lookup"))] : null
      ),
      ask.helps.length ? h("ul", { class: "small" }, ask.helps.map((help) => h("li", null, helpLink(help)))) : null
    );
  }

  function table(caption, headers, rows) {
    return h(
      "div",
      { class: "table-wrap" },
      h(
        "table",
        { class: "result-table" },
        h("caption", null, caption),
        h("thead", null, h("tr", null, headers.map((header) => h("th", { scope: "col" }, header)))),
        h("tbody", null, rows.map((cells) => h("tr", null, cells.map((cell, index) => (index === 0 ? h("th", { scope: "row" }, cell) : h("td", null, cell))))))
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

  function stateTable(check, st) {
    if (profilesOf(check).length) {
      return table(
        FG.t("selfcheck.result.gate"),
        [FG.t("selfcheck.result.condition"), FG.t("selfcheck.result.state")],
        applicable(check, st).map((item) => [[item.identifier, " ", FG.span(item.text), " ", h("span", { class: "badge" }, FG.termName(FG.id(item.tier)))], stateLabel(itemState(st, item))])
      );
    }
    return table(
      FG.t("selfcheck.result.principles"),
      [FG.t("selfcheck.result.principle"), FG.t("selfcheck.result.state"), FG.t("selfcheck.result.answered")],
      principleRows(check, st).map((row) => [
        h("a", { href: FG.href("explorer", row.principle.termCode) }, row.principle.termCode + " ", FG.span(row.principle.name)),
        stateLabel(row.state),
        FG.t("selfcheck.result.ofTotal", { n: row.answered, total: row.total }),
      ])
    );
  }

  function results(check, st) {
    const items = answerable(check, st);
    const answered = items.filter((item) => answerOf(st, item)).length;
    const { gaps, tasks } = outcomes(check, st);
    return [
      h("h2", { id: "results-title" }, FG.t("selfcheck.result.title")),
      h("p", null, FG.t("selfcheck.progress", { n: answered, total: items.length })),
      st.target ? h("p", { class: "small" }, FG.t("selfcheck.target", { target: st.target })) : null,
      h("p", { class: "small" }, FG.t("selfcheck.result.advisory")),
      stateTable(check, st),
      h("h3", null, FG.t("selfcheck.result.gaps")),
      gaps.length ? h("ul", { class: "gaps" }, gaps.map((item) => gapItem(st, item))) : h("p", null, FG.t("selfcheck.result.noGaps")),
      tasks.length ? [h("h3", null, FG.t("selfcheck.result.tasks")), h("ul", { class: "gaps" }, tasks.map(taskItem))] : null,
      h(
        "details",
        { class: "answers" },
        h("summary", null, FG.t("selfcheck.result.answers")),
        h(
          "div",
          { class: "content" },
          table(
            FG.t("selfcheck.result.answers"),
            [FG.t("selfcheck.result.item"), FG.t("selfcheck.result.answer"), FG.t("selfcheck.result.source")],
            items.map((item) => [[item.identifier, " ", FG.span(item.text)], answerText(st, item), sourceText(st, item)])
          )
        )
      ),
    ];
  }

  /* ---------------------------------------------------------------- exports */

  const pageBase = () => FG.config.pageUrl;
  const escapeMarkdown = (value) => String(value).replace(/([\\|[\]<>*_`#])/g, "\\$1");

  function markdown(check, st) {
    const items = answerable(check, st);
    const { gaps, tasks } = outcomes(check, st);
    const lines = ["# " + escapeMarkdown(FG.text(check.name)) + " (" + FG.formatDate(today()) + ")", ""];
    if (st.target) lines.push(escapeMarkdown(FG.t("selfcheck.target", { target: st.target })), "");
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
    lines.push("", "## " + FG.t("selfcheck.result.answers"), "", row([FG.t("selfcheck.result.item"), FG.t("selfcheck.result.answer"), FG.t("selfcheck.result.source")]), "| --- | --- | --- |");
    for (const item of items) lines.push(row([item.identifier + " " + FG.text(item.text), answerText(st, item), sourceText(st, item)]));
    lines.push("", `${FG.t("selfcheck.export.generatedBy")}, ${FG.config.version}: ${pageBase()}`, "");
    return lines.join("\n");
  }

  function logLine(st, item) {
    const parts = [FG.t("selfcheck.result.answer") + ": " + answerText(st, item)];
    const source = sourceText(st, item);
    if (source) parts.push(source);
    return parts.join("; ");
  }

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
        mentions: { "@id": "#result-set" },
      },
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
    if (target) graph.push({ "@id": st.target, "@type": "CreativeWork", name: st.target });
    return {
      "@context": [
        vocab.roCrate + "/context",
        {
          ftr: vocab.ftr,
          prov: vocab.prov,
          TestResultSet: vocab.ftr + "TestResultSet",
          TestResult: vocab.ftr + "TestResult",
          TestExecutionActivity: vocab.ftr + "TestExecutionActivity",
        },
      ],
      "@graph": graph,
    };
  };

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

  /** Read the answers in a shared link; anything unexpected makes the whole link invalid. */
  SC.parseShare = function (check, payload) {
    const parts = String(payload || "").split(".");
    if (parts[0] !== "a1" || parts.length < 3) return null;
    const codes = Object.fromEntries(Object.entries(SHARE_CODE).map(([value, letter]) => [letter, value]));
    const ids = new Set(itemsOf(check).map((item) => item.identifier));
    const shared = { mode: null, profile: null, extended: true, items: {} };
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
      if (!match || !ids.has(match[1]) || !codes[match[2]]) return null;
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

  function showMarkdown(check, st) {
    const text = markdown(check, st);
    FG.renderList("share-output", () =>
      fragment(
        h("label", { for: "markdown-text" }, FG.t("selfcheck.export.markdown")),
        h("textarea", { id: "markdown-text", readonly: true, rows: "12" }, text),
        h("div", { class: "buttons" }, h("button", { type: "button", onclick: (event) => copyWithFeedback(event, text, "markdown-text") }, FG.t("common.copy")))
      )
    );
    const field = document.getElementById("markdown-text");
    if (field) field.focus();
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
        "div",
        { class: "buttons" },
        h("button", { type: "button", onclick: () => showMarkdown(check, st) }, FG.t("selfcheck.export.markdown")),
        h("button", { type: "button", onclick: () => download(fileName(check, "md"), markdown(check, st), "text/markdown") }, FG.t("selfcheck.export.downloadMd")),
        h("button", { type: "button", onclick: () => download(fileName(check, "jsonld"), JSON.stringify(SC.ftrCrate(check, st), null, 2) + "\n", "application/ld+json") }, FG.t("selfcheck.export.jsonld")),
        h("button", { type: "button", onclick: () => window.print() }, FG.t("selfcheck.export.print")),
        h("button", { type: "button", id: "share-create", onclick: () => showShare(check, st) }, FG.t("selfcheck.export.share"))
      ),
      h("div", { id: "share-output", class: "share-output" }),
      h("p", null, h("button", { type: "button", class: "button-link", onclick: () => clearAnswers(check) }, FG.t("selfcheck.reset")))
    );
  }

  /* ---------------------------------------------------------------- views */

  function sharedView(check, payload) {
    const shared = SC.parseShare(check, payload);
    if (!shared) return [h("p", { class: "notice", role: "status" }, FG.t("selfcheck.export.sharedInvalid")), h("p", null, h("a", { class: "button", href: FG.href("check", check.identifier) }, FG.t("selfcheck.export.keepOwn")))];
    const use = () => {
      FG.state.answers[check.identifier] = shared;
      save();
      FG.navigate(FG.href("check", check.identifier));
    };
    return [
      h(
        "div",
        { class: "notice shared" },
        h("p", null, FG.t("selfcheck.export.sharedBanner")),
        h(
          "div",
          { class: "buttons" },
          h("button", { type: "button", class: "button-primary", onclick: use }, FG.t("selfcheck.export.useShared")),
          h("a", { class: "button", href: FG.href("check", check.identifier) }, FG.t("selfcheck.export.keepOwn"))
        )
      ),
      h("section", { class: "results", "aria-labelledby": "results-title" }, results(check, shared)),
    ];
  }

  function checkView(route) {
    const check = FG.get("#check-" + route.arg);
    const minutes = String(check.timeRequired || "").replace(/\D/g, "");
    const head = [
      h("p", { class: "muted" }, h("a", { href: FG.href("selfcheck") }, FG.t("selfcheck.title"))),
      FG.heading(1, null, FG.span(check.name)),
      FG.paragraphs(check.description),
      minutes ? h("p", { class: "muted" }, FG.t("station.minutes", { n: minutes })) : null,
    ];
    if (route.extra) return h("div", { class: "layout wrap selfcheck" }, h("article", null, head, sharedView(check, route.extra)));
    const st = stateOf(check);
    const isReady = ready(check, st);
    return h(
      "div",
      { class: "layout wrap selfcheck" },
      h(
        "article",
        null,
        head,
        h("div", { class: "no-print" }, settings(check, st)),
        isReady ? prefillPanel(check, st) : h("p", { class: "notice" }, FG.t("selfcheck.chooseFirst")),
        isReady ? itemsSection(check, st) : null,
        isReady ? h("section", { id: "results", class: "results", "aria-labelledby": "results-title" }, results(check, st)) : null,
        isReady ? exportSection(check, st) : null
      )
    );
  }

  function checkCard(check) {
    const st = hasState(check) ? stateOf(check) : null;
    const answered = st ? answerable(check, st).filter((item) => answerOf(st, item)).length : 0;
    const minutes = String(check.timeRequired || "").replace(/\D/g, "");
    const name = FG.text(check.name);
    return h(
      "li",
      { class: "card" },
      h("h3", null, FG.span(check.name)),
      FG.paragraphs(check.description),
      h(
        "div",
        { class: "badges" },
        minutes ? h("span", { class: "badge" }, FG.t("station.minutes", { n: minutes })) : null,
        h("span", { class: "badge" }, FG.t("selfcheck.items", { n: itemsOf(check).length })),
        FG.refs(check, "audience").map((lens) => h("span", { class: "badge" }, FG.text(lens.name)))
      ),
      answered ? h("p", { class: "small" }, FG.t("selfcheck.progress", { n: answered, total: answerable(check, st).length })) : null,
      h("p", null, h("a", { class: "button button-primary", href: FG.href("check", check.identifier) }, FG.t(answered ? "selfcheck.continue" : "selfcheck.start", { name })))
    );
  }

  function overview(route) {
    const checks = SC.checks();
    const mine = checks.filter((check) => FG.hasRef(check, "audience", "#lens-" + route.lens));
    const others = checks.filter((check) => !mine.includes(check));
    return h(
      "div",
      { class: "layout wrap" },
      h(
        "article",
        null,
        FG.heading(1, null, FG.t("selfcheck.title")),
        h("p", null, FG.t("selfcheck.intro")),
        h("h2", null, FG.t("selfcheck.forLens")),
        h("ul", { class: "cards" }, mine.map(checkCard)),
        others.length ? [h("h2", null, FG.t("selfcheck.others")), h("ul", { class: "cards" }, others.map(checkCard))] : null
      )
    );
  }

  FG.views.selfcheck = function (route) {
    return route.view === "check" && FG.get("#check-" + route.arg) ? checkView(route) : overview(route);
  };
})();
