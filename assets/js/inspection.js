/* Local inspection controls, loaded when a check opens. External reads still require a user action. */
(function () {
  "use strict";
  window.FairGuide.selfcheck.inspectionFactory = function (dependencies) {
    const { FG, SC, h, stateOf, runPrefill, applyEvidence, today, webUrl, save, describeTarget,
      dataciteInfo, stewardEvidence, fieldEvidence, pathState, fieldsOf, retarget, identifierRow, brief,
      setStatus, prefillFromRe3data, prefillFromNkr, prefillFromDashboard, prefillFromNanopub, label,
      record, answerOf, foundFields, FIELD_LABELS, readableField, valueNode, SHOWN_VALUES, noteText, observationsOf, FIP_RANK, VERDICT_ICON, running, wasRun, verdictKey } = dependencies;
  /** Keep the complete portable payload small enough for both its base64 Markdown copy and FTR logs.
      Ordinary observations are unchanged. Large exports disclose omitted older observations or shortened
      retained values; this never changes an answer or mutates the browser's working state. */
  function boundedPortable(data) {
    const size = (value) => new TextEncoder().encode(JSON.stringify(value)).length;
    const limit = 384 * 1024;
    if (size(data) <= limit) return data;
    data = JSON.parse(JSON.stringify(data));
    while (size(data) > limit) {
      let changed = false;
      const shorten = (holder, key) => {
        if (typeof holder[key] === "string" && holder[key].length > 200) {
          holder[key] = holder[key].slice(0, Math.ceil(holder[key].length / 2));
          changed = true;
          return true;
        }
        return false;
      };
      for (const entry of Object.values(data.items)) {
        if (entry.observations && entry.observations.length > 1) {
          entry.observations.shift();
          entry.observations.forEach((seen) => { seen.truncated = true; });
          if (entry.prefill) entry.prefill.truncated = true;
          changed = true;
          continue;
        }
        if (entry.observations && entry.prefill && entry.observations.length === 1) {
          delete entry.observations;
          entry.prefill.truncated = true;
          changed = true;
        }
        for (const seen of [...(entry.observations || []), ...(entry.prefill ? [entry.prefill] : [])]) {
          for (const field of seen.fields || []) for (let index = 0; index < field.values.length; index++) {
            if (shorten(field.values, index)) seen.truncated = true;
          }
          if (seen.list && seen.list.length > 5) { seen.list.length = Math.ceil(seen.list.length / 2); seen.truncated = true; changed = true; }
          for (const note of seen.notes || []) {
            if (shorten(note, "text")) seen.truncated = true;
            for (const key of Object.keys(note.params || {})) if (shorten(note.params, key)) seen.truncated = true;
          }
        }
      }
      for (const verdict of Object.values(data.champion && data.champion.verdicts || {})) if (shorten(verdict, "log")) verdict.truncated = true;
      if (!changed) break;
    }
    return data;
  }


  /** One test's state on the current records: running, not run, its verdict on a dataset, or for a sample how many
      records with a result passed, with each record's verdict behind a disclosure. */
  function testState(run, test) {
    const mark = (state, text, more) =>
      h("div", { class: "test-state", "data-state": state }, h("span", { "aria-hidden": "true" }, VERDICT_ICON[state] + " "), text, run && run.date && state !== "running" ? h("span", { class: "muted" }, " · " + FG.formatDate(run.date)) : null, more);
    if (running.has(test)) return mark("running", FG.t("selfcheck.champion.running"));
    if (!wasRun(run, test)) return h("div", { class: "test-state" });
    const values = run.records.map((record) => (run.verdicts[verdictKey(test, record)] || {}).value || "none");
    const details = h("details", { class: "test-records" }, h("summary", null, FG.t(values.length === 1 ? "selfcheck.evidence.log" : "selfcheck.champion.byRecord")),
      h("div", { class: "content" }, run.records.map((record, index) => {
        const result = run.verdicts[verdictKey(test, record)] || {};
        return h("section", { class: "probe-record" }, h("p", null, FG.external(record, brief(record, 90)), " · ", FG.t("selfcheck.champion." + values[index])),
          result.error ? h("p", { class: "probe-error" }, FG.t("selfcheck.evidence.requestError"), ": ", result.error) : null,
          result.invocation ? h("p", { class: "small test-invocation" }, h("code", null, result.invocation.method), " ", FG.external(result.invocation.url, FG.t("selfcheck.evidence.invocation")), h("code", null, JSON.stringify(result.invocation.body))) : null,
          result.log ? h("details", { class: "probe-log" }, h("summary", null, FG.t("selfcheck.evidence.originalLog")), h("div", { class: "content" }, h("pre", { tabindex: "0", role: "region", "aria-label": FG.t("selfcheck.evidence.originalLog") }, result.log))) : null,
          result.truncated ? h("p", { class: "small muted" }, FG.t("selfcheck.evidence.boundedLog")) : null);
      })));
    if (values.length === 1) return mark(values[0], FG.t("selfcheck.champion." + values[0]), details);
    const passed = values.filter((value) => value === "pass").length;
    const known = passed + values.filter((value) => value === "fail").length;
    const state = !known ? (values.includes("indeterminate") ? "indeterminate" : "none") : passed === values.length ? "pass" : passed ? "partly" : "fail";
    return mark(
      state,
      FG.t("selfcheck.champion.sample", { passed, n: known, total: values.length }),
      details
    );
  }


  function pidControl(check, st) {
    const input = h("input", { id: "prefill-pid", type: "text", autocomplete: "off", spellcheck: "false", value: st.pid || "" });
    const run = () => {
      const pid = FG.live.parsePid(input.value);
      const inputText = input.value.trim();
      if (!inputText || inputText.length > 300) {
        setStatus(check, FG.t("selfcheck.prefill.pidInvalid"));
        return;
      }
      st.pid = pid ? pid.value : inputText;
      retarget(check, pid ? FG.live.pidUrl(pid) : webUrl(inputText));
      prefillFromPid(check, st.pid);
    };
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") run();
    });
    return h(
      "div",
      { class: "prefill-row" },
      h("label", { for: "prefill-pid" }, FG.t("selfcheck.discovery.pid")),
      identifierRow(check, input, "pid", "prefill-pid", h("button", { type: "button", id: "prefill-pid-run", onclick: run }, FG.t("selfcheck.prefill.pidButton"))),
      h("p", { class: "small muted" }, FG.t("selfcheck.discovery.hint"))
    );
  }


  let assessorsLoading = null;
  function loadAssessors() {
    if (SC.assessObject && SC.assessSoftware) return Promise.resolve();
    if (!assessorsLoading) assessorsLoading = (async () => {
      const paths = (FG.config.discovery.assessmentScripts || [FG.config.discovery.assessmentScript])
        .filter((path) => !(FG.jsonLd && path === FG.config.discovery.assessmentScript)); // already loaded by discovery
      for (const path of paths) await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = path;
        script.onload = resolve;
        script.onerror = () => { script.remove(); reject(new Error("assessment module unavailable")); };
        document.head.appendChild(script);
      });
      if (!SC.assessObject || !SC.assessSoftware) throw new Error("assessment module unavailable");
    })().catch((error) => { assessorsLoading = null; throw error; });
    return assessorsLoading;
  }

  function applyObservations(check, observations) {
    let count = 0;
    for (const observation of observations) count += applyEvidence(check, observation.source,
      (item) => item.identifier === observation.id ? observation : null, observation.date, observation.record, true);
    return count;
  }

  function rememberInspection(check, result) {
    const st = stateOf(check);
    st.inspection = { date: String(result.date || today()).slice(0, 10), coverage: result.coverage || {},
      representations: (result.representations || []).slice(0, 8).map((entry) => ({ url: webUrl(entry.url), format: String(entry.format || "").slice(0, 100), source: String(entry.source || "landing").slice(0, 80) })),
      diagnostics: (result.diagnostics || []).slice(0, 20).map((entry) => ({ code: String(entry.code || "unavailable").slice(0, 80),
        source: String(entry.source || "landing").slice(0, 80), url: webUrl(entry.url), message: String(entry.message || "").slice(0, 500) })) };
    save();
  }

  function prefillFromPid(check, input) {
    return runPrefill(check, "landing", "prefill-pid-run", async (messages) => {
      await loadAssessors();
      const result = await FG.live.discoverObject(input);
      const st = stateOf(check);
      rememberInspection(check, result);
      if (!result.supported) { messages.push(FG.t("selfcheck.note.unsupportedPid")); return 0; }
      if (result.resolved && result.resolved.found) describeTarget(check, { name: result.resolved.title, url: result.resolved.url });
      let count = 0;
      if (result.datacite) {
        describeTarget(check, dataciteInfo(result.datacite));
        count += applyEvidence(check, "datacite", (item, fields) => fields.includes("@steward") ? stewardEvidence(result.datacite, st.steward) :
          Object.assign(fieldEvidence(fields.map((field) => pathState(result.datacite, field))), { fields: fieldsOf(result.datacite, fields) }),
        result.date.slice(0, 10), FG.config.links.dataciteRecord + result.pid.value);
      }
      count += applyObservations(check, SC.assessObject(check, result));
      if (result.diagnostics.length) messages.push(FG.t("selfcheck.discovery.limited"));
      return count;
    });
  }

  function softwareControl(check, st) {
    const input = h("input", { id: "prefill-software", type: "url", spellcheck: "false", autocomplete: "off", value: st.software || "" });
    const ref = h("input", { id: "prefill-software-ref", type: "text", spellcheck: "false", autocomplete: "off", value: st.softwareRef || "", maxlength: "200" });
    const run = () => runPrefill(check, "landing", "prefill-software-run", async (messages) => {
      /* What the reader typed stays in the field after a failed attempt, as the PID does, so it can be retried. */
      st.software = input.value.trim().slice(0, 1000);
      st.softwareRef = ref.value.trim().slice(0, 200);
      await loadAssessors();
      const repository = await FG.live.softwareRepository(st.software, { ref: st.softwareRef });
      rememberInspection(check, repository);
      if (!repository.supported || !repository.commit) { messages.push(FG.t("selfcheck.software.unavailable")); return 0; }
      // Switching the assessed commit invalidates automatic evidence; authored answers survive.
      retarget(check, repository.url + "#" + repository.commit);
      describeTarget(check, { name: repository.metadata.name || repository.repository, kind: repository.provider, url: repository.url, commit: repository.commit, ref: repository.ref });
      const count = applyObservations(check, SC.assessSoftware(check, repository));
      if (repository.diagnostics.length) messages.push(FG.t("selfcheck.discovery.limited"));
      return count;
    });
    input.addEventListener("keydown", (event) => { if (event.key === "Enter") run(); });
    return h("div", { class: "prefill-row" }, h("label", { for: input.id }, FG.t("selfcheck.software.repository")),
      identifierRow(check, input, "software", input.id, h("button", { type: "button", id: "prefill-software-run", onclick: run }, FG.t("selfcheck.software.button"))),
      h("label", { for: ref.id }, FG.t("selfcheck.software.ref")), ref,
      h("p", { class: "small muted" }, FG.t("selfcheck.software.hint")));
  }

  function inspectionDetails(st) {
    if (!st.inspection) return null;
    const reason = (code) => {
      if (code === "unsupported-origin") return "origin";
      if (code === "unavailable" || code === "unreadable-response") return "browser";
      if (code.startsWith("identity-")) return "identity";
      if (code === "unsupported-format") return "format";
      if (code === "timeout") return "timeout";
      if (code === "rate-limit") return "rate";
      if (code.includes("limit") || code === "pagination") return "limit";
      return "service";
    };
    return h("details", { class: "inspection-details" }, h("summary", null, FG.t("selfcheck.discovery.details")),
      h("div", { class: "content" }, h("p", { class: "small muted" }, FG.formatDate(st.inspection.date)),
        FG.list(st.inspection.representations).length ? [h("p", null, FG.t("selfcheck.discovery.readable")),
          h("ul", null, st.inspection.representations.map((entry) => h("li", null, entry.url ? FG.external(entry.url, brief(entry.url)) : label(entry.source), " · ", h("code", null, entry.format))))] : null,
        st.inspection.diagnostics.map((diagnostic) => h("section", { class: "probe-record" },
          h("p", null, FG.t("selfcheck.discovery.reason." + reason(diagnostic.code)), diagnostic.url ? [" · ", FG.external(diagnostic.url, FG.t("selfcheck.evidence.openSource"))] : null),
          h("details", { class: "probe-log" }, h("summary", null, FG.t("selfcheck.evidence.originalLog")),
            h("div", { class: "content" }, h("code", null, diagnostic.code), h("p", null, diagnostic.message)))))));
  }

  /** The re3data field: a re3data DOI (resolved through doi.org), an r3d identifier or the record's address. */
  function re3dataControl(check, st) {
    const input = h("input", { id: "prefill-re3data", type: "text", autocomplete: "off", spellcheck: "false", value: st.re3data || "" });
    const run = async () => {
      const id = await FG.live.re3dataRecord(input.value);
      if (!id) {
        setStatus(check, FG.t("selfcheck.prefill.re3dataInvalid"));
        return;
      }
      prefillFromRe3data(check, id);
    };
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") run();
    });
    return h(
      "div",
      { class: "prefill-row" },
      h("label", { for: "prefill-re3data" }, FG.t("selfcheck.prefill.re3data")),
      identifierRow(check, input, "re3data", "prefill-re3data", h("button", { type: "button", id: "prefill-re3data-run", onclick: run }, FG.t("selfcheck.prefill.re3dataButton"))),
      h("p", { class: "small muted" }, FG.t("selfcheck.prefill.re3dataHint"))
    );
  }

  /** NKR's repositories to fill the check from; while NKR lists none, the status says how to go on instead. */
  function nkrControl(check, st, re3data) {
    const records = FG.live.nkrRecords();
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
    return h("div", { class: "prefill-row" }, FG.live.nkrNote({ empty: FG.t(re3data ? "selfcheck.prefill.nkrEmptyRe3data" : "selfcheck.prefill.nkrEmptyByHand") }), picker);
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
        identifierRow(check, nanopub, "nanopub", "prefill-nanopub", h("button", { type: "button", id: "prefill-nanopub-run", onclick: runNanopub }, FG.t("selfcheck.prefill.nanopubButton"))),
        h("p", { class: "small muted" }, FG.t("selfcheck.prefill.clearHint"))
      ),
    ];
  }

  function inspectSample(check, entries) {
      runPrefill(check, "landing", "prefill-sample-run", async (messages) => {
        await loadAssessors();
        let count = 0;
        const diagnostics = [];
        for (const entry of entries) {
          const result = await FG.live.discoverObject(entry);
          count += applyObservations(check, SC.assessObject(check, result, true));
          diagnostics.push(...result.diagnostics);
        }
        rememberInspection(check, { date: today(), diagnostics, coverage: { records: entries.length } });
        messages.push(FG.t("selfcheck.note.sampleCoverage"));
        if (diagnostics.length) messages.push(FG.t("selfcheck.discovery.limited"));
        return count;
      });
  }
  function observationBody(pre) {
    const rows = [];
    for (const key of ["subject", "representation", "commit", "coverage"]) if (pre[key]) rows.push(h("dt", null, FG.t("selfcheck.evidence." + key)), h("dd", null, key === "coverage" && ["sample", "representation"].includes(pre[key]) ? FG.t("selfcheck.coverage." + pre[key]) : valueNode(pre[key], false)));
    return h("div", { class: "content" },
      h("p", { class: "source-chip" }, label(pre.source) + " · " + FG.formatDate(pre.date), pre.record ? [" · ", FG.external(pre.record, FG.t("selfcheck.evidence.record"))] : null),
      rows.length ? h("dl", { class: "relations evidence-relations" }, rows) : null,
      pre.testId ? localTestLinks(FG.get("#test-" + pre.testId)) : null,
      /* A provider observation refers to its one retained assessment, whose native results are in the overview. */
      pre.assessment ? h("p", { class: "small" }, h("button", { type: "button", class: "button-link", onclick: () => {
        const overview = document.getElementById("results-assessments");
        if (overview) { overview.scrollIntoView({ block: "start" }); overview.focus({ preventScroll: true }); }
      } }, FG.t("selfcheck.providers.openOverview"))) : null,
      foundFields(pre).map((field) => h("div", { class: "evidence-field" }, h("p", null, h("strong", null, readableField(field)), " · ", h("code", null, field.path)),
        h("div", { class: "evidence-value", tabindex: "0", role: "region", "aria-label": readableField(field) }, field.values.map((value) => h("p", null, valueNode(value, false)))), field.more ? h("p", { class: "small muted" }, FG.t("selfcheck.evidence.more", { n: field.more })) : null)),
      FG.list(pre.notes).map((note) => h("p", null, noteText(note))),
      pre.truncated ? h("p", { class: "small muted" }, FG.t("selfcheck.evidence.bounded"), pre.record ? [" ", FG.external(pre.record, FG.t("selfcheck.evidence.openSource"))] : null) : null);
  }

  function localTestLinks(test) {
    if (!test) return null;
    return h("p", { class: "small test-invocation" }, h("a", { href: FG.catalogueHref("tests", test.identifier) }, FG.text(test.name)),
      test.url ? [" · ", h("a", { href: test.url, target: "_blank", rel: "noopener" }, FG.t("selfcheck.evidence.code"))] : null,
      FG.refs(test, "subjectOf").map((doc) => [" · ", h("a", { href: FG.testDocumentationHref(doc.url || doc["@id"], test), target: "_blank", rel: "noopener" }, FG.t("selfcheck.evidence.documentation"))]));
  }

  function localTestLine(item) {
    const id = "guide-" + item.identifier.replace(".", "-");
    const test = FG.get("#test-" + id);
    const entryPoint = test && FG.refs(test, "additionalProperty").find((property) => property.propertyID === "entryPoint");
    return test ? h("div", { class: "test-line", "data-local-test": id }, localTestLinks(test),
      h("p", { class: "small muted" }, FG.t("selfcheck.evidence.local")),
      entryPoint ? h("details", { class: "probe-log" }, h("summary", null, FG.t("selfcheck.evidence.call")),
        h("div", { class: "content test-invocation" }, h("code", null, entryPoint.value))) : null) : null;
  }

  /** Who gave the answer: the reader, a pre-fill they kept, changed or confirmed, or a shared result. A source is
      named as the answer's origin only when the answer still is that source's suggestion. */
  function ownership(entry, value, pre) {
    const params = pre ? { source: label(pre.source), date: FG.formatDate(pre.date), value: pre.value ? FG.t("selfcheck.answer." + pre.value) : "" } : {};
    let kind = null;
    /* An answer taken from someone else's result was not confirmed or changed by this reader. */
    if (entry.origin === "shared" || entry.imported) kind = pre && pre.value && value && value !== pre.value ? "differs" : pre && pre.value && value === pre.value ? "sharedMatch" : "shared";
    else if (entry.origin === "user") kind = value ? (!pre || !pre.value ? "user" : value === pre.value ? "confirmed" : "changed") : null;
    else if (pre) kind = pre.value && value === pre.value ? "prefilled" : "suggestion";
    return kind ? { kind, text: FG.t("selfcheck.origin." + kind, params) } : null;
  }

  /** The observations worth reading first: one per source, newest first, those with a readable fact or suggestion
      ahead of those without, so a later source never hides an earlier useful fact. */
  function readable(entry) {
    const seen = new Set();
    const list = [];
    for (const observation of observationsOf(entry).slice().reverse()) {
      const key = observation.source + "|" + (observation.assessment || "");
      if (seen.has(key)) continue;
      seen.add(key);
      list.push(observation);
    }
    const useful = (observation) => (observation.value ? 2 : 0) + (foundFields(observation).some((field) => FIELD_LABELS[field.path]) ? 1 : 0);
    return list.sort((a, b) => useful(b) - useful(a));
  }

  /** One observation as a line: source and date, its suggestion or none, up to three readable values, and its first
      notes (one in a question's evidence line, up to three in its details). */
  function observationLine(observation, notes = 3) {
    /* A FAIR Champion observation's verdicts show on the question's test line. */
    const fields = observation.source === "champion" ? [] : foundFields(observation).filter((field) => FIELD_LABELS[field.path] || observation.assessment).slice(0, 3);
    return h(
      "div",
      { class: "evidence-observation", "data-source": observation.source },
      h(
        "p",
        { class: "evidence-head" },
        h("span", { class: "evidence-source" }, label(observation.source) + " · " + FG.formatDate(observation.date) + ": "),
        h("span", { class: "verdict", "data-kind": observation.value ? "suggestion" : "none" }, observation.value ? FG.t("selfcheck.evidence.suggests", { value: FG.t("selfcheck.answer." + observation.value) }) : FG.t("selfcheck.evidence.noSuggestion")),
        observation.record ? [" · ", FG.external(observation.record, FG.t("selfcheck.evidence.record"))] : null,
        fields.map((field) => [h("span", { class: "evidence-readable" }, h("strong", null, readableField(field) + ": "), field.values.slice(0, SHOWN_VALUES).map((value, index) => [index ? ", " : "", valueNode(value, true)]))])
      ),
      FG.list(observation.notes).filter((note) => note && typeof note === "object").slice(0, notes).map((note) => h("p", { class: "small evidence-note" }, noteText(note)))
    );
  }

  /* The resource each evidence source is, so it carries its badge wherever its evidence appears. */
  const SOURCE_RESOURCE = { champion: "fair-champion", re3data: "re3data", nkr: "nkr", datacite: "datacite", "fip-dashboard": "fip-dashboard",
    "fip-dashboard-snapshot": "fip-dashboard", "f-uji": "f-uji", "fair-checker": "fair-checker" };
  const sourceBadge = (source) => {
    const resource = FG.get("#resource-" + (SOURCE_RESOURCE[source] || source));
    return resource ? FG.serviceBadge(resource.identifier, resource.url) : null;
  };

  /** A question's one consolidated evidence line, always in view: who owns the answer, with the most useful
      observation and its source's badge; before any evidence, where a suggestion could come from, or that none can. */
  function originLine(st, item) {
    const entry = record(st, item);
    const value = answerOf(st, item);
    const pre = entry && entry.prefill && typeof entry.prefill === "object" ? entry.prefill : null;
    const owner = entry ? ownership(entry, value, pre) : null;
    const first = entry && pre ? readable(entry)[0] : null;
    if (!owner && !first) {
      const sources = [...new Set(FG.refs(item, "additionalProperty").map((property) => String(property.propertyID).replace("prefill:", "")))].map(label);
      /* A test the Guide runs in the browser is a source too. */
      if (FG.get("#test-guide-" + item.identifier.replace(".", "-"))) sources.push(FG.t("selfcheck.question.localTest"));
      return h("p", { class: "evidence-line evidence-none small" },
        sources.length ? FG.t("selfcheck.question.evidenceFrom", { sources: sources.join(", ") }) : FG.t("selfcheck.question.noEvidence"));
    }
    return h("div", { class: "evidence-line" },
      owner ? h("p", { class: "source-chip", "data-origin": owner.kind }, owner.text) : null,
      first ? h("div", { class: "evidence-first" }, sourceBadge(first.source), observationLine(first, 1)) : null);
  }

  /** The rest of a question's evidence, for its details: the other observations, the declared resources and the
      complete technical record. */
  function originRest(st, item) {
    const entry = record(st, item);
    const pre = entry && entry.prefill && typeof entry.prefill === "object" ? entry.prefill : null;
    if (!pre) return null;
    const list = FG.list(pre.list).filter((entryItem) => entryItem && entryItem.name);
    return [
      readable(entry).slice(0, 4).map((observation) => h("div", { class: "evidence-first" }, sourceBadge(observation.source), observationLine(observation))),
      list.length
        ? [h("p", { class: "small" }, FG.t("selfcheck.note.declared") + ":"),
          h("ul", { class: "small" }, list.map((fer) => h("li", null, fer.url ? FG.external(fer.url, String(fer.name)) : String(fer.name),
            FIP_RANK.includes(fer.status) ? " (" + FG.t("selfcheck.fipStatus." + fer.status) + ")" : null)))]
        : null,
      h("details", { class: "evidence-details" }, h("summary", null, FG.t("selfcheck.evidence.details")), observationsOf(entry).map(observationBody)),
    ];
  }

  /** The evidence beside an item, in reading order: who owns the answer; the useful facts each source observed,
      with its date and what it suggests; what remains uncertain; then the complete technical details. */
  function origin(st, item) {
    const entry = record(st, item);
    if (!entry) return null;
    const value = answerOf(st, item);
    const parts = [];
    const pre = entry.prefill && typeof entry.prefill === "object" ? entry.prefill : null;
    const owner = ownership(entry, value, pre);
    if (owner) parts.push(h("p", { class: "source-chip", "data-origin": owner.kind }, owner.text));
    if (pre) {
      parts.push(readable(entry).slice(0, 4).map(observationLine));
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
      parts.push(h("details", { class: "evidence-details" }, h("summary", null, FG.t("selfcheck.evidence.details")), observationsOf(entry).map(observationBody)));
    }
    return parts;
  }

    return { pidControl, testState, boundedPortable, prefillFromPid, softwareControl, inspectionDetails, inspectSample, re3dataControl, nkrControl, fipControl, observationBody, origin, originLine, originRest, sourceBadge, localTestLine };
  };
})();
