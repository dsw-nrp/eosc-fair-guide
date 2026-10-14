/* Identifier and citation helpers. Only an explicit lookup calls a connector.
   Checksum algorithms follow ORCID's identifier documentation and ROR's documented Crockford/MOD 97-10 pattern. */
(function () {
  "use strict";
  const FG = window.FairGuide;
  const H = (FG.helpers = FG.helpers || {});
  const h = (...args) => FG.h(...args);
  const NAMES = { doi: "DOI", handle: "Handle", orcid: "ORCID iD", ror: "ROR ID" };
  const BASE32 = "0123456789abcdefghjkmnpqrstvwxyz";
  const CANDIDATE = /(?<![\w./:@-])(?:(?:https?:\/\/)?(?:(?:www\.)?orcid\.org|(?:www\.)?ror\.org|(?:dx\.)?doi\.org|hdl\.handle\.net)\/[^\s<>"']+|\d{4}-\d{4}-\d{4}-\d{3}[\dX]|0[a-z0-9]{6}\d{2}|(?:doi|hdl):\s*\d[\w.-]*\/[^\s<>"']+|10\.\d{4,9}\/[^\s<>"']+)/gi;

  H.validOrcid = function (value) {
    if (!/^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/.test(value)) return false;
    const digits = value.replace(/-/g, "");
    let total = 0;
    for (const digit of digits.slice(0, 15)) total = (total + Number(digit)) * 2;
    const check = (12 - total % 11) % 11;
    return digits[15] === (check === 10 ? "X" : String(check));
  };

  H.validRor = function (value) {
    if (!/^0[a-hj-km-np-tv-z0-9]{6}\d{2}$/.test(value)) return false;
    let number = 0;
    for (const letter of value.slice(0, 7)) number = number * 32 + BASE32.indexOf(letter);
    return Number(value.slice(7)) === 98 - (number * 100) % 97;
  };

  // Remove sentence punctuation and unmatched closing brackets, keeping balanced DOI suffixes such as a(b).
  function unquote(value) {
    value = value.replace(/[.,;:!?]+$/, "");
    for (const [open, close] of [["(", ")"], ["[", "]"], ["{", "}"]]) {
      while (value.endsWith(close) && value.split(close).length > value.split(open).length) value = value.slice(0, -1);
    }
    return value;
  }

  /* Forms are recognised by the shared owner in live.js, exactly as search and the checks recognise them; this
     helper adds only the checksums. */
  function parsed(input) {
    const value = unquote(input);
    const orcid = FG.live.parseOrcid(value);
    if (orcid) return { type: "orcid", value: orcid };
    const ror = FG.live.parseRor(value);
    if (ror) return { type: "ror", value: ror };
    if (/^(?:https?:\/\/)?(?:www\.)?(?:orcid\.org|ror\.org)\//i.test(value)) return null;
    if (/^(?:https?:\/\/)?(?:(?:dx\.)?doi\.org|hdl\.handle\.net)\//i.test(value)) {
      const url = new URL(/^https?:\/\//i.test(value) ? value : "https://" + value);
      return FG.live.parsePid(url.origin + url.pathname);
    }
    return FG.live.parsePid(value);
  }

  H.identifierUrl = (item) => item.type === "orcid" ? FG.config.helpers.orcidUrl + item.value
    : item.type === "ror" ? FG.config.helpers.rorUrl + item.value : FG.live.pidUrl(item);

  H.extract = function (input) {
    const config = FG.config.helpers;
    const text = String(input || "");
    if (text.length > config.maxCharacters) return { items: [], textLimit: true, itemLimit: false };
    const items = [], seen = new Set();
    for (const match of text.matchAll(CANDIDATE)) {
      const next = text[match.index + match[0].length];
      if (next && /[\w/-]/.test(next)) continue;
      const item = parsed(match[0]);
      if (!item) continue;
      // DOI names are case insensitive; Handle suffixes can distinguish case.
      const key = item.type + ":" + (item.type === "doi" ? item.value.toLowerCase() : item.value);
      if (seen.has(key)) continue;
      seen.add(key);
      if (items.length === config.maxItems) return { items, textLimit: false, itemLimit: true };
      item.checksum = item.type === "orcid" ? H.validOrcid(item.value) : item.type === "ror" ? H.validRor(item.value) : null;
      items.push(item);
    }
    return { items, textLimit: false, itemLimit: false };
  };

  H.resolveIdentifier = async function (item) {
    if (item.checksum === false) return { status: "invalid" };
    try {
      if (item.type === "orcid" || item.type === "ror") {
        const name = await FG.live[item.type === "orcid" ? "orcidName" : "rorName"](item.value);
        return name === null ? { status: "notFound" } : { status: "found", title: name === item.value ? null : name, url: H.identifierUrl(item) };
      }
      const record = await FG.live.resolvePid(item);
      if (!record.found) return { status: "notFound" };
      let title = record.title, metadataUnavailable = false;
      if (!title && item.type === "doi") {
        const matches = (value) => typeof value === "string" && value.toLowerCase() === item.value.toLowerCase();
        try {
          const metadata = await FG.live.datacite(item.value);
          if (metadata && matches(metadata.doi)) title = FG.list(metadata.titles).map((entry) => entry && entry.title).find((name) => typeof name === "string" && name.trim());
        } catch (error) { metadataUnavailable = true; }
        if (!title) {
          try {
            const metadata = await FG.live.crossref(item.value);
            if (metadata && matches(metadata.DOI)) title = FG.list(metadata.title).find((name) => typeof name === "string" && name.trim());
          } catch (error) { metadataUnavailable = true; }
        }
        if (title) metadataUnavailable = false;
      }
      return { status: "found", title: title || null, url: record.url, metadataUnavailable };
    } catch (error) {
      return { status: "unavailable" };
    }
  };

  let draft = "", seed = null;
  H.identifiers = function (route) {
    if (route.extra && route.extra !== seed) { draft = route.extra; seed = route.extra; }
    const config = FG.config.helpers;
    const text = h("textarea", { id: "identifier-text", rows: 6, "aria-describedby": "identifier-privacy", oninput: () => { draft = text.value; } }, draft);
    const clear = h("button", { type: "button", class: "field-clear", "aria-label": FG.t("helper.identifiers.clear"), title: FG.t("helper.identifiers.clear"), onclick: () => {
      text.value = ""; draft = ""; seed = null;
      rows = []; queue.length = 0;
      list.replaceChildren(); summary.textContent = "";
      window.history.replaceState(null, "", FG.href("page", "identifiers"));
      waiting.refresh(); controls(); text.focus();
    } }, FG.icon("clear"));
    const summary = h("p", { id: "identifier-summary", role: "status" });
    const list = h("ul", { class: "identifier-list" });
    const find = h("button", { type: "submit", class: "button button-primary" }, FG.t("helper.identifiers.find"));
    /* Finding waits for text, and clearing for text or results; one reason serves both, since clearing has nothing
       to do only when there is no text either. */
    const typed = () => text.value.trim() !== "";
    const waiting = FG.gate(find, FG.t("helper.identifiers.needsText"), typed, text);
    const refreshClear = () => {
      const can = typed() || rows.length > 0;
      clear.disabled = !can;
      if (can) clear.removeAttribute("aria-describedby");
      else clear.setAttribute("aria-describedby", waiting.id);
    };
    text.addEventListener("input", refreshClear);
    /* Shown only while some found identifier is still to be looked up. */
    const all = h("button", { type: "button", class: "button", hidden: true, onclick: () => {
      rows.filter((row) => row.status === "unresolved").forEach(enqueue);
    } }, FG.t("helper.identifiers.resolveAll"));
    const form = h("form", { onsubmit: (event) => { event.preventDefault(); if (typed()) scan(); } },
      h("label", { for: "identifier-text" }, FG.t("helper.identifiers.label")), h("div", { class: "field-clearable" }, text, clear),
      h("p", { id: "identifier-privacy", class: "small muted" }, FG.t("helper.identifiers.privacy")),
      h("div", { class: "buttons" }, find, all), waiting);
    const box = h("section", { class: "identifier-helper", "aria-label": FG.t("helper.identifiers.label") }, form, summary, list);
    let rows = [], active = 0, itemLimit = false;
    const queue = [];
    refreshClear();

    function controls() {
      const running = active > 0 || queue.length > 0;
      all.hidden = !rows.some((row) => row.status === "unresolved");
      all.disabled = running;
      refreshClear();
      if (rows.some((row) => !["unresolved", "invalid"].includes(row.status))) {
        summary.textContent = FG.t("helper.identifiers.coverage", {
          done: rows.filter((row) => ["found", "notFound", "unavailable"].includes(row.status)).length,
          total: rows.filter((row) => row.status !== "invalid").length,
        }) + (itemLimit ? " " + FG.t("helper.identifiers.itemLimit", { n: config.maxItems }) : "");
      }
    }

    function show(row) {
      row.element.dataset.status = row.status;
      row.message.replaceChildren();
      const result = row.result;
      if (row.status === "found") {
        row.message.append(h("p", null, h("strong", null, FG.t("helper.identifiers.found")), " ", result.title || FG.t("helper.identifiers.titleMissing")));
        if (result.metadataUnavailable) row.message.append(h("p", { class: "small muted" }, FG.t("helper.identifiers.metadataUnavailable")));
        if (result.url && result.url !== H.identifierUrl(row.item)) row.message.append(h("p", null, FG.external(result.url, FG.t("helper.identifiers.openRecord"))));
      } else row.message.append(h("p", null, FG.t("helper.identifiers." + row.status)));
      row.button.disabled = ["invalid", "queued", "running", "found", "notFound"].includes(row.status);
      row.button.hidden = ["invalid", "found", "notFound"].includes(row.status);
      row.button.textContent = FG.t("helper.identifiers." + (row.status === "unavailable" ? "retry" : "resolve"));
    }

    function enqueue(row) {
      if (!["unresolved", "unavailable"].includes(row.status)) return;
      row.status = "queued";
      queue.push(row);
      show(row);
      drain();
    }

    function drain() {
      while (active < config.maxConcurrent && queue.length) {
        const row = queue.shift();
        active++;
        row.status = "running";
        show(row);
        H.resolveIdentifier(row.item).then((result) => {
          row.result = result;
          row.status = result.status;
          show(row);
        }).finally(() => { active--; drain(); controls(); });
      }
      controls();
    }

    function scan() {
      const found = H.extract(text.value);
      itemLimit = found.itemLimit;
      list.replaceChildren();
      rows = [];
      if (found.textLimit) summary.textContent = FG.t("helper.identifiers.textLimit", { n: config.maxCharacters });
      else summary.textContent = FG.t(found.items.length ? "helper.identifiers.count" : "helper.identifiers.empty", { n: found.items.length })
        + (found.itemLimit ? " " + FG.t("helper.identifiers.itemLimit", { n: config.maxItems }) : "");
      for (const item of found.items) {
        const row = { item, status: item.checksum === false ? "invalid" : "unresolved" };
        row.message = h("div", { role: "status" });
        row.button = h("button", { type: "button", class: "button button-small", onclick: () => enqueue(row) });
        rows.push(row);
        row.element = h("li", null,
          h("p", null, h("strong", null, NAMES[item.type]), " ", FG.external(H.identifierUrl(item), H.identifierUrl(item))),
          item.checksum !== null ? h("p", { class: "small muted" }, FG.t("helper.identifiers." + (item.checksum ? "checksumValid" : "checksumInvalid"))) : null,
          row.message, row.button);
        list.append(row.element);
        show(row);
      }
      controls();
    }
    if (draft) scan();
    return box;
  };
  const CITATION_FORMATS = [
    { id: "apa", style: "apaStyle", locale: "apaLocale", mime: "text/plain", extension: "txt" },
    { id: "iso690", style: "isoStyle", locale: "isoLocale", mime: "text/plain", extension: "txt" },
    { id: "bibtex", mime: "application/x-bibtex", extension: "bib" },
    { id: "ris", mime: "application/x-research-info-systems", extension: "ris" },
  ];
  const sameDoi = (a, b) => typeof a === "string" && a.trim().toLowerCase() === b.toLowerCase();
  const citationError = (code) => Object.assign(new Error(code), { code });

  /** Public DOI representations. A failed format remains unavailable; it never becomes another style. */
  H.generateCitations = async function (doi) {
    const config = FG.config.helpers.citation, live = FG.live;
    const options = { maxBytes: config.maxBytes, timeoutSeconds: config.timeoutSeconds };
    const agency = await live.doiAgency(doi, options);
    if (!agency) throw citationError("notFound");
    if (!["DataCite", "Crossref"].includes(agency)) throw citationError("unsupported");
    const encoded = encodeURIComponent(doi);
    const data = await live.fetchJson(agency === "DataCite" ? "datacite" : "crossref",
      (agency === "DataCite" ? "dois/" : "works/") + encoded, { ...options, allowNotFound: true });
    const record = data && (agency === "DataCite" ? data.data && data.data.attributes : data.message);
    if (!record) throw citationError("notFound");
    if (!sameDoi(agency === "DataCite" ? record.doi : record.DOI, doi)) throw citationError("mismatch");
    const title = FG.list(agency === "DataCite" ? record.titles : record.title)
      .map((entry) => typeof entry === "string" ? entry : entry && entry.title).find((entry) => typeof entry === "string" && entry.trim()) || doi;
    // The published list prevents unknown-style fallback from being labelled as Czech ISO 690.
    const styles = live.fetchJson(config.formatter, config.stylesPath, { ...options, maxBytes: config.maxStylesBytes })
      .then((value) => ({ values: Array.isArray(value) ? value : [] }), () => ({ error: "unavailable" }));
    const formats = await Promise.all(CITATION_FORMATS.map(async (format) => {
      const item = { ...format };
      let connector, path;
      if (format.style) {
        connector = config.formatter;
        path = config.formatPath + "?" + new URLSearchParams({ doi, style: config[format.style], lang: config[format.locale] });
      } else {
        connector = agency === "DataCite" ? config.dataciteConnector : "crossref";
        path = (agency === "DataCite" ? config.datacitePath : config.crossrefPath)
          .replace("{mime}", format.mime).replace("{doi}", encoded);
      }
      item.url = new URL(path, live.origin(connector) + "/").href;
      try {
        if (format.style) {
          const available = await styles;
          if (available.error) throw citationError(available.error);
          if (!available.values.includes(config[format.style])) throw citationError("styleMissing");
        }
        const result = await live.fetchText(connector, path, { ...options, accept: format.mime });
        const text = result.text.trim();
        if (!text || /^(?:<!doctype|<html)/i.test(text)) throw citationError("invalidResponse");
        if ((result.format && result.format !== format.mime) || (format.style && !result.format)) throw citationError("invalidResponse");
        if (format.id === "bibtex") {
          const found = text.match(/\bdoi\s*=\s*(?:\{([^}]+)\}|"([^"]+)")/i);
          if (!/^@\w+\s*\{/.test(text) || !found || !sameDoi(found[1] || found[2], doi)) throw citationError("invalidResponse");
        } else if (format.id === "ris") {
          const found = text.match(/^DO\s+-\s*(.+)$/m);
          if (!/^TY\s+-\s*\S+/m.test(text) || !/^ER\s+-\s*$/m.test(text) || !found || !sameDoi(found[1], doi)) throw citationError("invalidResponse");
        }
        item.text = text;
      } catch (error) { item.error = ["styleMissing", "invalidResponse", "rate-limit"].includes(error.code) ? error.code : "unavailable"; }
      return item;
    }));
    return { doi, title, agency, formats, checkedAt: new Date().toISOString() };
  };

  let citationDraft = "", citationSeed = null, citationResult = null, citationStatus = "", citationGeneration = 0, refreshCitation;
  H.citation = function (route) {
    if (route.extra && (route.extra !== citationSeed || !document.querySelector(".citation-helper"))) {
      citationDraft = route.extra; citationSeed = route.extra; citationResult = null; citationStatus = ""; citationGeneration++;
    }
    const t = (key, values) => FG.t("helper.citation." + key, values);
    const output = h("div", { class: "citation-results" });
    const status = h("p", { role: "status", id: "citation-status" });
    const input = h("input", { id: "citation-doi", type: "text", maxlength: 1024, autocomplete: "off", spellcheck: "false",
      "aria-describedby": "citation-privacy citation-status", value: citationDraft, oninput: () => {
        citationDraft = input.value; citationResult = null; citationStatus = ""; citationGeneration++; refresh();
      } });
    const clear = h("button", { type: "button", class: "field-clear", "aria-label": t("clear"), title: t("clear"), onclick: () => {
      input.value = ""; citationDraft = ""; citationSeed = null; citationResult = null; citationStatus = ""; citationGeneration++;
      window.history.replaceState(null, "", FG.href("page", "citation")); refresh(); input.focus();
    } }, FG.icon("clear"));
    const submit = h("button", { type: "submit", class: "button button-primary" }, t("generate"));
    /* Preparing waits for a DOI, and clearing for a DOI or a result; one reason serves both. */
    const typed = () => input.value.trim() !== "";
    const waiting = FG.gate(submit, t("needsDoi"), typed);
    const form = h("form", { onsubmit: async (event) => {
      event.preventDefault();
      if (!typed()) return;
      const pid = FG.live.parsePid(input.value);
      if (!pid || pid.type !== "doi" || /[<>"\x00-\x1f]/.test(pid.value)) { citationStatus = "invalid"; refresh(); return; }
      const generation = ++citationGeneration;
      citationResult = null; citationStatus = "running"; refresh();
      try {
        const result = await H.generateCitations(pid.value);
        if (generation !== citationGeneration) return;
        citationResult = result; citationStatus = "done";
      } catch (error) {
        if (generation !== citationGeneration) return;
        citationStatus = ["notFound", "unsupported", "mismatch"].includes(error.code) ? error.code : "unavailable";
      }
      if (refreshCitation) refreshCitation();
    } }, h("label", { for: "citation-doi" }, t("label")), h("div", { class: "field-clearable" }, input, clear),
    h("p", { id: "citation-privacy", class: "small muted" }, t("privacy")), submit, waiting);
    const box = h("section", { class: "citation-helper", "aria-label": t("label") }, form, status, output);

    function refresh() {
      status.textContent = citationStatus ? t(citationStatus) : "";
      waiting.refresh();
      if (citationStatus === "running") submit.disabled = true;
      const clearable = typed() || Boolean(citationResult) || Boolean(citationStatus);
      clear.disabled = !clearable;
      if (clearable) clear.removeAttribute("aria-describedby");
      else clear.setAttribute("aria-describedby", waiting.id);
      output.replaceChildren();
      if (!citationResult) {
        const pid = FG.live.parsePid(citationDraft);
        if (citationStatus && !["running", "invalid"].includes(citationStatus) && pid && pid.type === "doi") {
          output.append(h("p", null, FG.external(FG.live.pidUrl(pid), pid.value)));
        }
        return;
      }
      const result = citationResult;
      output.append(h("p", null, h("strong", null, result.title)), h("p", { class: "small muted" },
        FG.external(FG.live.pidUrl({ type: "doi", value: result.doi }), result.doi), " · " + result.agency + " · ",
        h("time", { datetime: result.checkedAt }, new Date(result.checkedAt).toLocaleString(FG.state.lang))), h("p", { class: "small" }, t("review")));
      for (const format of result.formats) {
        const id = "citation-" + format.id;
        const block = h("section", { class: "citation-format", "aria-labelledby": id + "-heading" },
          h("h3", { id: id + "-heading" }, t(format.id)), h("p", { class: "small muted" }, FG.external(format.url, t("source"))));
        if (format.error) block.append(h("p", { role: "status" }, t(format.error)));
        else block.append(h("pre", { id, tabindex: "0", class: ["apa", "iso690"].includes(format.id) ? "citation-text" : null }, format.text), h("div", { class: "buttons" },
          h("button", { type: "button", class: "button button-small", onclick: (event) => FG.copyText(event, format.text, id) }, FG.t("common.copy")),
          h("button", { type: "button", class: "button button-small", onclick: () => FG.download(FG.exportName(["citation", format.id], format.extension), format.text, format.mime) }, t("download"))));
        output.append(block);
      }
    }
    refreshCitation = refresh;
    refresh();
    return box;
  };
})();
