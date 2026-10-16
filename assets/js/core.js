/* Core of the FAIR Data Guide: the knowledge-base index, interface strings, safe DOM building, browser storage and
   routing. Every value from the crate or from a live service reaches the page as text; nothing is parsed as HTML. */
(function () {
  "use strict";

  const FG = (window.FairGuide = window.FairGuide || {});
  const STORAGE_KEY = "eosc-fair-guide";
  const SOURCE_KEY = STORAGE_KEY + ":source:";
  const LANGS = ["cs", "en"];

  /* ---------------------------------------------------------------- knowledge base */

  /* The crate and the interface data arrive as generated classic scripts (assets/data/), which load from a local
     file as well as from a web host. */
  FG.load = function () {
    const crate = window.FairGuideData.kb;
    const page = window.FairGuideData.ui;
    FG.graph = crate["@graph"];
    FG.byId = new Map(FG.graph.map((entity) => [entity["@id"], entity]));
    FG.ui = page.ui;
    FG.config = page.config;
    FG.root = FG.byId.get("./");
    FG.DASHBOARD = FG.config.links.fipDashboard;
  };

  /** A genuine upstream identifier, kept separate from the Guide-owned primary. */
  FG.sourceIdentifier = (entity, scheme) => FG.refs(entity, "alternateIdentifier")
    .find((item) => item && item.propertyID === scheme)?.value || null;
  FG.sourceEntity = (scheme, value, prefix = "") => {
    const matches = FG.graph.filter((entity) => entity["@id"].startsWith(prefix) && FG.sourceIdentifier(entity, scheme) === value);
    return matches.length === 1 ? matches[0] : null;
  };

  /* Keys that write through to an object's prototype instead of the object. Every merge of data read from a file or a
     service skips them (language patches here, discovered metadata in discovery.js, imported results). */
  const UNSAFE_KEYS = new Set(["__proto__", "constructor", "prototype"]);
  FG.unsafeKey = (name) => UNSAFE_KEYS.has(name);

  /* Language patches follow the generated tree. Null array positions leave structural or original values alone;
     objects are updated in place, so the graph index and references keep the same identity on language switching. */
  function mergeData(target, patch) {
    for (const [key, value] of Object.entries(patch || {})) {
      if (value === null || UNSAFE_KEYS.has(key)) continue;
      if (value && typeof value === "object") {
        if (!target[key] || typeof target[key] !== "object") target[key] = Array.isArray(value) ? [] : {};
        mergeData(target[key], value);
      } else target[key] = value;
    }
  }
  FG.mergeData = mergeData;

  const searchTerms = new WeakMap();
  function bindSearch(value, entries) {
    for (const entry of entries || []) {
      const array = entry.path.reduce((node, key) => node && node[key], value);
      if (array && typeof array === "object") searchTerms.set(array, entry.words);
    }
  }

  const scriptLoads = new Map();
  function loadScript(path) {
    if (!scriptLoads.has(path)) {
      scriptLoads.set(path, new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = path;
        script.onload = resolve;
        script.onerror = () => {
          scriptLoads.delete(path);
          script.remove();
          reject(new Error("The Guide could not load its local data file: " + path));
        };
        document.head.append(script);
      }));
    }
    return scriptLoads.get(path);
  }

  FG.loadHelpers = () => loadScript(FG.config.helpers.script);
  /** A view whose code loads when it first opens (the catalogue). */
  FG.loadView = (name) => loadScript(FG.config.views[name]);

  FG.languagesLoaded = new Set();
  FG.loadLanguage = async function (lang) {
    if (FG.languagesLoaded.has(lang)) return;
    await loadScript(FG.config.languages[lang]);
    const values = (window.FairGuideData.languages || {})[lang];
    if (!values) throw new Error("The Guide's language data is missing: " + lang);
    mergeData(window.FairGuideData.kb, values.kb);
    mergeData(window.FairGuideData.ui, values.ui);
    bindSearch(window.FairGuideData.kb, values.search);
    FG.languagesLoaded.add(lang);
  };

  /* Views load their neutral part and selected language only. Switching language fills translations of the parts
     already needed without changing answers or refetching neutral entities. All files are local classic scripts. */
  FG.partsLoaded = new Set();
  const partLoads = {};
  const partLanguagesLoaded = new Set();
  FG.partHasLanguage = (name, lang) => partLanguagesLoaded.has(name + "/" + lang);
  FG.loadPart = async function (name, lang) {
    if (!partLoads[name]) {
      partLoads[name] = loadScript(FG.config.parts[name]).then(() => {
        const part = (window.FairGuideData.parts || {})[name];
        if (!part) throw new Error("The Guide's data part is missing: " + name);
        for (const entity of part.entities || []) {
          FG.graph.push(entity);
          FG.byId.set(entity["@id"], entity);
        }
        FG.partsLoaded.add(name);
        return part;
      }).catch((error) => {
        delete partLoads[name];
        throw error;
      });
    }
    const part = await partLoads[name];
    const language = lang || FG.state.lang;
    if (!FG.partHasLanguage(name, language)) {
      await loadScript(FG.config.partLanguages[name][language]);
      const values = ((window.FairGuideData.partLanguages || {})[name] || {})[language];
      if (!values) throw new Error("The Guide's part translation is missing: " + name + "/" + language);
      mergeData(part, values.values);
      bindSearch(part, values.search);
      partLanguagesLoaded.add(name + "/" + language);
    }
    for (const [id, properties] of Object.entries(part.properties || {})) Object.assign(FG.byId.get(id) || {}, properties);
    if (part.ui) mergeData(FG.ui, part.ui);
    if (part.config) mergeData(FG.config, part.config);
  };

  /** Explicit data exports keep bilingual API-style records. Reading a view does not require this load. */
  FG.completeLanguages = () => Promise.all(LANGS.flatMap((lang) => [FG.loadLanguage(lang),
    ...[...FG.partsLoaded].map((name) => FG.loadPart(name, lang))]));

  FG.list = (value) => (value == null ? [] : Array.isArray(value) ? value : [value]);
  FG.id = (value) => (typeof value === "string" ? value : value && value["@id"]);
  FG.get = (value) => FG.byId.get(FG.id(value));
  FG.refs = (entity, prop) => FG.list(entity && entity[prop]).map(FG.get).filter(Boolean);
  FG.refIds = (entity, prop) => FG.list(entity && entity[prop]).map(FG.id).filter(Boolean);
  FG.hasRef = (entity, prop, id) => FG.refIds(entity, prop).includes(id);
  FG.ofType = (type) => FG.graph.filter((entity) => FG.list(entity["@type"]).includes(type));
  FG.byPosition = (a, b) => (a.position || 0) - (b.position || 0);

  /** The implementation model is an independent organising vocabulary, with explicit editorial associations. */
  FG.modelTerms = (kind) => FG.refs(FG.get("#implementation-model"), "hasDefinedTerm").filter((term) => !kind || term.modelKind === kind).sort(FG.byPosition);
  FG.modelLink = (term) => FG.h("a", { class: "model-tag", href: FG.entryHref(term) }, FG.span(term.name));
  FG.modelRows = function (entity) {
    return ["implementationLayers", "implementationSeams"].flatMap((property) => {
      const terms = FG.refs(entity, property);
      return terms.length ? [FG.relationTerm(property), FG.h("dd", { class: "model-tags" }, terms.map(FG.modelLink))] : [];
    });
  };
  /** A labelled row's label with the row's icon, the same wherever the row appears; a row of a model term's own
      details names its label. */
  FG.relationTerm = (key, label) =>
    FG.h("dt", null, FG.icon(((FG.config && FG.config.icons && FG.config.icons.relation) || {})[key]), label || FG.t("catalogue.relation." + key));

  /** The icon of each answer state, the same in the self-check, its report and the path's rail. */
  FG.STATE_ICON = { met: "✓", partly: "◐", gap: "✗", unknown: "?", open: "–", provided: "↗" };

  /** The favicon that stands for an address: its host's, normalised and kept with the page, unless the host serves
      many tools and the address is not its home page. */
  FG.faviconOf = function (url) {
    const favicons = (FG.config && FG.config.favicons) || { hosts: [], homeOnly: [] };
    let parts;
    try {
      parts = new URL(String(url || ""));
    } catch (error) {
      return null;
    }
    const host = parts.hostname.toLowerCase().replace(/^www\./, "");
    if (parts.protocol !== "https:" || !favicons.hosts.includes(host)) return null;
    if (favicons.homeOnly.includes(host) && parts.pathname.replace(/\/+$/, "") !== "") return null;
    return "assets/favicons/" + host + ".png";
  };

  /** One badge for an external tool or service wherever the Guide shows it, beside its name: in the catalogue, among
      a step's resources and in the self-check's evidence. It is the service's own favicon wherever one could be
      obtained (D-183); otherwise the icon of its catalogue kind on the kind's colour, as the kind facet shows it, so
      one service looks the same everywhere (D-185). */
  FG.serviceBadge = function (key, url, kind = "resources") {
    const mark = FG.config.favicons?.marks?.[key];
    const favicon = mark ? "assets/favicons/" + mark : FG.faviconOf(url);
    if (favicon) {
      return FG.h("span", { class: "service-badge service-favicon", "data-service": String(key), "aria-hidden": "true" },
        FG.h("img", { src: favicon, alt: "", width: "48", height: "48", loading: "lazy", decoding: "async" }));
    }
    return FG.kindBadge(kind, key);
  };

  /** An entry's icon where it has no favicon of its own: its catalogue kind's icon on the kind's colour. */
  FG.kindBadge = function (kind, key) {
    const icon = ((FG.config && FG.config.icons && FG.config.icons.kind) || {})[kind];
    return FG.h("span", { class: "service-badge service-placeholder kind-" + kind, "data-service": key ? String(key) : null, "aria-hidden": "true" }, FG.icon(icon));
  };
  FG.modelContexts = (station, lens) => FG.graph.filter((entity) => String(entity["@id"]).startsWith("#model-context-") && FG.hasRef(entity, "isPartOf", station["@id"]) && FG.hasRef(entity, "audience", "#lens-" + lens));

  /** Pick the value in the requested language; fall back to another language and report it. */
  FG.textOf = function (value, lang) {
    let fallback = null;
    for (const item of FG.list(value)) {
      if (typeof item === "string" || typeof item === "number") return { text: String(item), lang: null };
      if (item && item["@language"] === lang) return { text: item["@value"], lang: null };
      if (item && !fallback) fallback = item;
    }
    return fallback ? { text: fallback["@value"], lang: fallback["@language"] } : { text: "", lang: null };
  };

  FG.text = (value, lang) => FG.textOf(value, lang || FG.state.lang).text;

  /** A span carrying the value, with a lang attribute when it fell back to another language. */
  FG.span = function (value, attrs) {
    const { text, lang } = FG.textOf(value, FG.state.lang);
    return FG.h("span", Object.assign({ lang: lang || null }, attrs || {}), text);
  };

  /** A repository's or an infrastructure's name in one language with that language's abbreviation, where it has one
      the name does not already contain: "Český sociálněvědní datový archiv (ČSDA)" (D-173). */
  FG.abbreviatedName = function (entity, lang) {
    const name = FG.text(entity.name, lang);
    const abbreviation = entity.abbreviation ? FG.text(entity.abbreviation, lang) : "";
    return abbreviation && !name.includes(abbreviation) ? name + " (" + abbreviation + ")" : name;
  };

  /** The same name in the other language, where it differs, so an entry keeps both forms. */
  FG.otherLanguageName = function (entity) {
    const other = FG.state.lang === "cs" ? "en" : "cs";
    const theirs = FG.abbreviatedName(entity, other);
    return theirs !== FG.abbreviatedName(entity, FG.state.lang) ? { lang: other, text: theirs } : null;
  };

  /** Every form of a name, in both languages with the abbreviations, for search to match. */
  FG.nameForms = (entity) => [FG.bothLanguages(entity.name), FG.bothLanguages(entity.abbreviation)].join(" ");

  /** The name of the agent a property references (an operating, hosting or developing organisation), or null. */
  FG.partyName = (entity, key) => {
    const target = FG.get(FG.id(entity[key]));
    return target ? FG.text(target.name) : null;
  };

  /** An entity's name as nodes in the reader's language, marked with its language. A resource shows the guide's
      name for it; a work the guide only cites, written in another language and carrying a translated title, shows
      its original title followed by the translation in brackets, as a citation would. */
  FG.nameNodes = function (entity) {
    const values = FG.list(entity && entity.name);
    const own = typeof entity.inLanguage === "string" ? entity.inLanguage : null;
    const tagged = (lang) => values.find((value) => value && value["@language"] === lang);
    const original = own && own !== FG.state.lang && !entity.resourceType ? tagged(own) : null;
    const translated = tagged(FG.state.lang);
    if (original && translated) return [FG.h("span", { lang: own }, original["@value"]), " [" + translated["@value"] + "]"];
    if (typeof entity.name === "string") return [FG.h("span", { lang: own }, entity.name)];
    return [FG.span(entity.name)];
  };

  /** An entity's name as plain text, in the same form FG.nameNodes shows. */
  FG.nameText = (entity) => FG.nameNodes(entity).map((node) => (typeof node === "string" ? node : node.textContent)).join("");

  /* ---------------------------------------------------------------- exports */

  /** Save text the page made as a file. */
  FG.download = function (name, text, type) {
    const blob = new Blob([text], { type: type + ";charset=utf-8" });
    /* A blob link made here from content the page produced; FG.h would refuse its scheme, so the element is built
       directly. */
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  };

  /** Copy text from a button and say so on its label (`.copy-label`, or the whole button). When the clipboard is
      refused, select the element that shows the text, so the reader can copy it themselves. */
  FG.copyText = async function (event, text, fallbackId) {
    const button = event.currentTarget;
    try {
      await navigator.clipboard.writeText(text);
      (button.querySelector(".copy-label") || button).textContent = FG.t("common.copied");
    } catch (error) {
      const field = document.getElementById(fallbackId);
      if (!field) return;
      field.focus();
      if (typeof field.select === "function") field.select();
      else window.getSelection().selectAllChildren(field);
    }
  };

  /** A file name for an export: the guide, what it holds, and today's date. */
  FG.exportName = (parts, extension) => ["fair-guide"].concat(parts).concat(FG.today()).join("-") + "." + extension;

  /** Rows as CSV with a header of column labels; a byte order mark lets spreadsheets read the Czech letters. */
  FG.csv = function (columns, rows) {
    const cell = (value) => {
      const text = Array.isArray(value) ? value.join("; ") : String(value == null ? "" : value);
      return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
    };
    const lines = [columns.map((column) => cell(column.label))].concat(rows.map((row) => columns.map((column) => cell(row[column.key]))));
    return "\ufeff" + lines.map((line) => line.join(",")).join("\r\n") + "\r\n";
  };

  /** What the view being rendered offers to save, besides printing; views add to it. */
  FG.exports = [];
  FG.offerExport = (entry) => FG.exports.push(entry);

  /** An entity's record in the guide's API, as a path under the page; null where it has none. */
  FG.recordHref = function (entity) {
    const api = FG.config.api;
    const record = api && api.records[FG.id(entity)];
    return record ? api.files.record.replace("{record}", record) : null;
  };

  /** A link to an entity's record, the same small link in the corner of every card that has one. */
  FG.apiLink = function (entity) {
    const href = FG.recordHref(entity);
    return href ? FG.h("a", { class: "json-link", href, type: "application/json", title: FG.t("api.recordTitle") }, FG.t("api.record")) : null;
  };

  /** The view as data: the record of the entity it shows, offered under the view. */
  FG.offerRecord = function (entity) {
    const href = FG.recordHref(entity);
    if (href) FG.offerExport({ id: "data", icon: "code", label: FG.t("export.data"), href });
  };

  /** Language-tagged values as a language map, as the API writes them: one text per language. */
  FG.languageMap = (value) =>
    FG.list(value).some((item) => item && item["@language"])
      ? Object.fromEntries(FG.list(value).filter((item) => item && item["@language"]).map((item) => [item["@language"], item["@value"]]))
      : FG.text(value);

  /** The view's exports and printing, under the view; the whole knowledge base is on the page for machines. An export
      that cannot act now (`unavailable`, its reason) is inactive, and the bar states each such reason once. */
  FG.exportBar = function () {
    const reasons = [...new Set(FG.exports.map((entry) => entry.unavailable).filter(Boolean))];
    const reasonId = (text) => "export-reason-" + reasons.indexOf(text);
    const button = (entry) =>
      entry.href
        ? FG.h("a", { class: "button button-small", id: "export-" + entry.id, href: entry.href, type: "application/json" }, FG.icon(entry.icon || "download"), FG.h("span", null, entry.label))
        : FG.h("button", { type: "button", class: "button-small", id: "export-" + entry.id, onclick: entry.run, disabled: Boolean(entry.unavailable),
          "aria-describedby": entry.unavailable ? reasonId(entry.unavailable) : null }, FG.icon(entry.icon || "download"), FG.h("span", null, entry.label));
    return FG.h(
      "section",
      { class: "export-bar wrap no-print", "aria-labelledby": "export-bar-title" },
      FG.h(
        "div",
        { class: "export-bar-inner" },
        FG.h("h2", { id: "export-bar-title", class: "export-bar-title" }, FG.t("export.title")),
        FG.h(
          "div",
          { class: "export-actions" },
          FG.exports.map(button),
          button({ id: "print", icon: "print", label: FG.t("export.print"), run: () => window.print() })
        ),
        reasons.map((text) => FG.h("p", { class: "control-reason small", id: reasonId(text) }, text))
      )
    );
  };

  /* ---------------------------------------------------------------- references in text */

  /** Where a reference in text leads: its catalogue entry, page or lifecycle station. */
  FG.referenceHref = function (id) {
    if (id === "#infrastructures") return FG.catalogueHref("infrastructures");
    if (String(id).startsWith("#page-")) return FG.href("page", String(id).slice(6));
    const address = FG.config.api?.records[id];
    if (address) {
      const [kind, ...parts] = address.split("/");
      if (FG.catalogueKind(kind) === "stations") return FG.href("path", parts.join("/"));
      if (kind === "check") return FG.href("check", parts.join("/"));
      return FG.catalogueHref(kind, parts.join("/"));
    }
    const base = FG.config.pageUrl || "";
    return base && String(id).startsWith(base) ? String(id).slice(base.length).replace(/\/?$/, "/") : null;
  };

  /** A text as nodes, with the first occurrence of each phrase its entity names by reference linked; a link already
      made in an earlier paragraph of the same text is not repeated. */
  function linkedNodes(entity, text, lang, used) {
    const links = ((FG.config && FG.config.textLinks) || {})[entity && entity["@id"]] || [];
    const matches = [];
    for (const link of links) {
      const phrase = link[lang] || link.und;
      const at = phrase && !used.has(link.ref) ? text.indexOf(phrase) : -1;
      if (at >= 0) matches.push({ at, end: at + phrase.length, link });
    }
    matches.sort((a, b) => a.at - b.at);
    const nodes = [];
    let from = 0;
    for (const match of matches) {
      const href = FG.referenceHref(match.link.ref);
      if (match.at < from || !href) continue;
      nodes.push(text.slice(from, match.at), FG.h("a", { class: "text-ref", href }, text.slice(match.at, match.end)));
      used.add(match.link.ref);
      from = match.end;
    }
    nodes.push(text.slice(from));
    return nodes.filter((node) => node !== "");
  }

  /** An entity's text with the entries it names linked, as FG.span shows it otherwise. */
  FG.linkedSpan = function (entity, prop) {
    const { text, lang } = FG.textOf(entity[prop || "text"], FG.state.lang);
    return FG.h("span", { lang: lang || null }, ...linkedNodes(entity, text, lang || FG.state.lang, new Set()));
  };

  /* A list item that opens with a short lead and a colon, "Git: commit each verified step", shows the lead in bold. */
  const LEAD_LENGTH = 40;
  function listItem(line, nodesOf) {
    const at = line.indexOf(": ");
    if (at > 0 && at <= LEAD_LENGTH && !/[.;!?]/.test(line.slice(0, at))) {
      return FG.h("li", null, FG.h("strong", null, ...nodesOf(line.slice(0, at))), ...nodesOf(line.slice(at)));
    }
    return FG.h("li", null, ...nodesOf(line));
  }

  /* A block of text: a list when every line starts with "- ", a paragraph otherwise. */
  function textBlock(block, lang, nodesOf) {
    const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
    // A flat pipe table keeps its column and row headers at phone width inside its own scroll region.
    const cells = (line) => line.slice(1, -1).split("|").map((cell) => cell.trim());
    if (lines.length >= 3 && lines.every((line) => line.startsWith("|") && line.endsWith("|"))) {
      const rows = lines.map(cells);
      if (rows[1].every((cell) => /^:?-{3,}:?$/.test(cell)) && rows.every((row) => row.length === rows[0].length)) {
        return FG.h("div", { class: "text-table-scroll", role: "region", tabindex: "0", "aria-label": rows[0][0], lang: lang || null },
          FG.h("table", { class: "text-table" },
            FG.h("thead", null, FG.h("tr", null, rows[0].map((cell) => FG.h("th", { scope: "col" }, ...nodesOf(cell))))),
            FG.h("tbody", null, rows.slice(2).map((row) => FG.h("tr", null, row.map((cell, i) => FG.h(i ? "td" : "th", i ? null : { scope: "row" }, ...nodesOf(cell))))))));
      }
    }
    if (lines.length && lines.every((line) => line.startsWith("- "))) {
      return FG.h("ul", { class: "text-list", lang: lang || null }, ...lines.map((line) => listItem(line.slice(2), nodesOf)));
    }
    return FG.h("p", { lang: lang || null }, ...nodesOf(block));
  }

  /** An entity's text as paragraphs with the entries it names linked, as FG.paragraphs shows it otherwise. */
  FG.linkedParagraphs = function (entity, prop) {
    const { text, lang } = FG.textOf(entity[prop || "text"], FG.state.lang);
    const used = new Set();
    return text
      .split(/\n\s*\n/)
      .filter(Boolean)
      .map((block) => textBlock(block, lang, (part) => linkedNodes(entity, part, lang || FG.state.lang, used)));
  };

  /** Paragraphs of a text whose paragraphs are separated by a blank line; a block of "- " lines is a list. */
  FG.paragraphs = function (value) {
    const { text, lang } = FG.textOf(value, FG.state.lang);
    return text
      .split(/\n\s*\n/)
      .filter(Boolean)
      .map((block) => textBlock(block, lang, (part) => [part]));
  };

  /* ---------------------------------------------------------------- interface strings */

  FG.t = function (key, params) {
    const entry = key.split(".").reduce((node, part) => (node ? node[part] : undefined), FG.ui);
    let value = entry && (entry[FG.state.lang] || entry.cs) ? entry[FG.state.lang] || entry.cs : key;
    /* Plural forms are separated by "|": Czech one|few|many (1, 2 to 4, other), English one|other, chosen by n. */
    if (value.includes("|") && params && typeof params.n === "number") {
      const forms = value.split("|");
      const n = Math.abs(params.n);
      const index = FG.state.lang === "cs" ? (n === 1 ? 0 : n >= 2 && n <= 4 ? 1 : 2) : n === 1 ? 0 : 1;
      value = forms[Math.min(index, forms.length - 1)];
    }
    for (const [name, replacement] of Object.entries(params || {})) {
      value = value.split("{" + name + "}").join(String(replacement));
    }
    return value;
  };

  FG.formatDate = function (iso) {
    if (!iso) return "";
    const parts = String(iso).slice(0, 10).split("-");
    if (parts.length !== 3) return String(iso);
    return FG.state.lang === "cs" ? `${Number(parts[2])}. ${Number(parts[1])}. ${parts[0]}` : parts.join("-");
  };

  /** A number as the page's language writes it: a decimal comma and grouped thousands in Czech. */
  FG.formatNumber = (value) => Number(value).toLocaleString(FG.state.lang === "cs" ? "cs-CZ" : "en-GB");

  /** Today's date in the visitor's time zone, as YYYY-MM-DD. */
  FG.today = function () {
    const now = new Date();
    return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
  };

  /* ---------------------------------------------------------------- safe DOM */

  const SAFE_SCHEME = /^(https:|mailto:)/i;
  const ANY_SCHEME = /^[a-z][a-z0-9+.-]*:/i;

  /** Only HTTPS, mailto, in-page and relative links are allowed; anything else becomes inert. */
  /* Identifier resolvers that also answer over HTTPS: an identifier minted on plain HTTP, such as a nanopublication
     IRI, is shown as it is and linked over HTTPS. */
  const HTTPS_RESOLVER = /^http:\/\/((www\.)?purl\.org|w3id\.org|(dx\.)?doi\.org|hdl\.handle\.net|identifiers\.org|n2t\.net)\//i;

  /* A browser drops leading and trailing control characters and spaces and every tab and newline before it reads an
     address's scheme (WHATWG URL), so "java\tscript:" is a script link; the check reads the address as the browser
     will. A backslash counts as a slash, so "/\host" leaves the guide like "//host". */
  const URL_EDGES = /^[\u0000-\u0020]+|[\u0000-\u0020]+$/g;
  const URL_TABS_AND_NEWLINES = /[\t\n\r]/g;
  const URL_CONTROL = /[\u0000-\u001f\u007f]/;
  const NETWORK_PATH = /^[\\/]{2}/;

  /** A link's address if it is safe to follow; null when it is not, so the element is not a link at all rather than
      one that leads back to the start. */
  FG.safeHref = function (href) {
    const value = String(href || "").replace(URL_EDGES, "").replace(URL_TABS_AND_NEWLINES, "");
    if (URL_CONTROL.test(value)) return null;
    if (value.startsWith("#") || SAFE_SCHEME.test(value)) return value;
    if (HTTPS_RESOLVER.test(value)) return "https://" + value.slice("http://".length);
    if (ANY_SCHEME.test(value) || NETWORK_PATH.test(value)) return null;
    return value;
  };

  /* Attributes that name an address pass FG.safeHref; event handlers are only ever functions, never inline code; an
     inline document is never set. */
  const URL_ATTRIBUTES = new Set(["href", "src", "action", "formaction", "poster", "xlink:href"]);
  const REFUSED_ATTRIBUTES = new Set(["srcdoc"]);

  FG.h = function (tag, attrs, ...children) {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attrs || {})) {
      if (value == null || value === false) continue;
      const lower = name.toLowerCase();
      if (name === "class") element.className = value;
      else if (lower.startsWith("on")) {
        if (typeof value === "function") element.addEventListener(name.slice(2), value);
      }
      else if (URL_ATTRIBUTES.has(lower)) {
        const safe = FG.safeHref(value);
        if (safe !== null) element.setAttribute(name, safe);
      }
      else if (!REFUSED_ATTRIBUTES.has(lower)) element.setAttribute(name, value === true ? "" : String(value));
    }
    for (const child of children.flat(Infinity)) {
      if (child == null || child === false || child === "") continue;
      element.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return element;
  };

  /* Controls that can act only once something exists (an identifier, records, an answer) stay inactive until then,
     with the reason as visible text: an inactive control cannot take focus, so the reason cannot live in a tooltip.
     The reason shows only while the controls are inactive; it is rechecked whenever a watched field changes, and its
     refresh() serves other triggers, such as an answer. */
  let reasonCount = 0;
  FG.gate = function (controls, reasonText, ready, fields) {
    const list = [].concat(controls).filter(Boolean);
    const id = "reason-" + (reasonCount += 1);
    const reason = FG.h("p", { class: "control-reason small", id }, reasonText);
    const refresh = () => {
      const can = Boolean(ready());
      for (const control of list) {
        control.disabled = !can;
        if (can) control.removeAttribute("aria-describedby");
        else control.setAttribute("aria-describedby", id);
      }
      reason.hidden = can;
    };
    for (const field of [].concat(fields || []).filter(Boolean)) field.addEventListener("input", refresh);
    reason.refresh = refresh;
    refresh();
    return reason;
  };

  /** A small reader visual from one maintained definition: the labelled steps of `visual.<name>` in content/ui.toml,
      in their order, as a figure with an ordered list. It reads in order with a screen reader, reflows on a phone,
      prints, and needs no drawing runtime; the arrows between steps are decoration. */
  FG.flow = function (name, extra) {
    const definition = FG.ui.visual && FG.ui.visual[name];
    if (!definition) return null;
    const steps = Object.keys(definition).filter((key) => definition[key] && definition[key].label);
    return FG.h(
      "figure",
      { class: "flow", "data-flow": name },
      FG.h("figcaption", { class: "flow-title" }, FG.t("visual." + name + ".title")),
      FG.h(
        "ol",
        { class: "flow-steps" },
        steps.map((key) => FG.h("li", { class: "flow-step", "data-step": key }, FG.h("strong", { class: "flow-label" }, FG.t("visual." + name + "." + key + ".label")), " ",
          FG.h("span", { class: "flow-text" }, FG.t("visual." + name + "." + key + ".text"))))
      ),
      definition.note ? FG.h("p", { class: "flow-note small" }, FG.t("visual." + name + ".note")) : null,
      extra || null
    );
  };

  /** An icon from the inlined sprite: an interface key from content/icons.toml or a Font Awesome name. Icons are
      decorative; the text next to them carries the meaning. */
  FG.icon = function (name, attrs) {
    const sprite = document.querySelector("svg.sprite");
    const id = (FG.config && FG.config.icons && FG.config.icons.ui && FG.config.icons.ui[name]) || name;
    if (!sprite || !id || !sprite.querySelector("#i-" + id)) return null;
    const svg = document.createElementNS(sprite.namespaceURI, "svg");
    svg.setAttribute("class", "icon" + (attrs && attrs.class ? " " + attrs.class : ""));
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    const use = document.createElementNS(sprite.namespaceURI, "use");
    use.setAttribute("href", "#i-" + id);
    svg.append(use);
    return svg;
  };

  /** An external link that opens in a new tab and says so to screen readers. */
  FG.external = function (href, label, attrs) {
    return FG.h(
      "a",
      Object.assign({ href, target: "_blank", rel: "noopener noreferrer" }, attrs || {}),
      label,
      FG.h("span", { class: "visually-hidden" }, " (" + FG.t("common.newWindow") + ")")
    );
  };

  /** A local test's documentation has a heading in each language; external documentation keeps its own URL. */
  FG.testDocumentationHref = (url, test) => FG.state.lang === "en" && String(test.identifier).startsWith("guide-") && String(url).endsWith("#" + test.identifier) ? url + "-en" : url;

  /* ---------------------------------------------------------------- storage */

  FG.storage = {
    read() {
      try {
        return JSON.parse(window.localStorage.getItem(STORAGE_KEY)) || {};
      } catch (error) {
        return {};
      }
    },
    write(value) {
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
        return true;
      } catch (error) {
        /* Storage can be unavailable (private windows, blocked site data) or full; the guide works without it and
           says so where answers are kept. */
        return false;
      }
    },
    remove() {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
        for (const key of Object.keys(window.localStorage)) if (key.startsWith(SOURCE_KEY)) window.localStorage.removeItem(key);
      } catch (error) {
        /* Nothing to remove when storage is unavailable. */
      }
    },
    /* Original evaluator reports, one key per content digest, apart from the answers: a report the browser refuses
       to keep never stops the answers from being saved. Writing reports whether the report was kept. */
    readSource(digest) {
      try {
        return window.localStorage.getItem(SOURCE_KEY + digest);
      } catch (error) {
        return null;
      }
    },
    writeSource(digest, text) {
      try {
        window.localStorage.setItem(SOURCE_KEY + digest, text);
        return true;
      } catch (error) {
        return false;
      }
    },
    pruneSources(used) {
      try {
        for (const key of Object.keys(window.localStorage)) if (key.startsWith(SOURCE_KEY) && !used.has(key.slice(SOURCE_KEY.length))) window.localStorage.removeItem(key);
      } catch (error) {
        /* Nothing to remove when storage is unavailable. */
      }
    },
    /** The characters of every retained report, for the shared budget. */
    sourceSize() {
      try {
        return Object.keys(window.localStorage).filter((key) => key.startsWith(SOURCE_KEY)).reduce((sum, key) => sum + (window.localStorage.getItem(key) || "").length, 0);
      } catch (error) {
        return 0;
      }
    },
  };

  FG.state = { lang: "cs", lens: "V", answers: {}, lastStation: null, lastVisit: null, readStations: [], checkGrouping: "principles", resultCollapsed: false, hideCheckBadges: false };

  /** Disclosure levels the user opened (L1, L2, L3, ai); kept while the page is open, so switching lens keeps them. */
  FG.openLevels = new Set();

  /** Whether the state holds nothing worth keeping: language and lens come from the address anyway. */
  const isEmptyState = (state) =>
    !Object.keys(state.answers || {}).length &&
    !state.lastStation &&
    !state.lastVisit &&
    !FG.list(state.readStations).length &&
    state.checkGrouping !== "steps" &&
    !state.resultCollapsed &&
    !state.hideCheckBadges;

  /** Remove everything the guide stores in this browser and start from an empty state. */
  FG.clearStoredData = function () {
    Object.assign(FG.state, { answers: {}, lastStation: null, lastVisit: null, readStations: [], checkGrouping: "principles", resultCollapsed: false, hideCheckBadges: false });
    FG.openLevels.clear();
    FG.storage.remove();
    /* Reports held for this visit go too. */
    if (FG.providers && FG.providers.forgetAll) FG.providers.forgetAll();
  };

  /** The reader's own read mark on a step: set it or take it off. Every visible control for the step follows without a
      re-render, so the control the reader used keeps the focus (D-190). */
  FG.toggleReadStation = function (stationId) {
    const reads = FG.list(FG.state.readStations);
    FG.state.readStations = reads.includes(stationId) ? reads.filter((id) => id !== stationId) : reads.concat(stationId);
    const read = FG.state.readStations.includes(stationId);
    FG.saveState();
    for (const control of document.querySelectorAll('.read-toggle[data-read="' + CSS.escape(stationId) + '"]')) {
      control.dataset.state = read ? "read" : "unread";
      control.setAttribute("aria-pressed", read ? "true" : "false");
      control.setAttribute("title", FG.t(read ? "journey.readOff" : "journey.readOn"));
      const glyph = control.querySelector(".read-toggle-glyph");
      if (glyph) glyph.textContent = read ? "✓" : "○";
    }
  };

  /** Save the state; whether it was saved is returned and kept in `FG.storageFull`. When the browser refuses it,
      retained evaluator reports give way first: they are dropped from storage (the page keeps them for the visit)
      and the answers are saved again, so a report never costs the reader their answers. */
  FG.saveState = function () {
    if (isEmptyState(FG.state)) {
      FG.storage.remove();
      FG.storageFull = false;
      return true;
    }
    const value = {
      lang: FG.state.lang,
      lens: FG.state.lens,
      answers: FG.state.answers,
      lastStation: FG.state.lastStation,
      lastVisit: FG.state.lastVisit,
      readStations: FG.state.readStations,
      checkGrouping: FG.state.checkGrouping,
      resultCollapsed: FG.state.resultCollapsed,
      hideCheckBadges: FG.state.hideCheckBadges,
    };
    let saved = FG.storage.write(value);
    if (!saved && FG.storage.pruneSources) {
      if (FG.keepSourcesForVisit) FG.keepSourcesForVisit();
      FG.storage.pruneSources(new Set());
      saved = FG.storage.write(value);
    }
    FG.storageFull = !saved;
    return saved;
  };

  /* ---------------------------------------------------------------- routing */

  const VIEWS = ["path", "check", "explorer", "catalogue", "tools", "page", "selfcheck"];

  /** In-page targets that name crate entities, as used by advice actions. */
  FG.entityRoute = function (hash) {
    const id = hash.replace(/^#/, "");
    let match;
    if ((match = id.match(/^station-(.+)$/))) return { view: "path", arg: match[1] };
    if ((match = id.match(/^check-(.+)$/))) return { view: "check", arg: match[1] };
    if ((match = id.match(/^page-(.+)$/))) return { view: "page", arg: match[1] };
    if ((match = id.match(/^resource-(.+)$/))) {
      const address = FG.config.api.records["#resource-" + match[1]];
      return address ? { view: "catalogue", arg: address.split("/")[0], extra: address.split("/").slice(1).join("/") } : null;
    }
    /* A topic (`#resources?type=standard,vocabulary`) opens the kind narrowed to it, for the reader's lens. */
    if ((match = id.match(/^(resources|repositories)\?(.+)$/)) && FG.catalogueTopic) return { view: "catalogue", arg: FG.catalogueTopic(match[1], match[2]) };
    if (id === "repositories") return FG.repositoryFinderHref ? FG.parseHash(FG.repositoryFinderHref()) : { view: "catalogue", arg: "repositories" };
    if (id === "resources") return { view: "catalogue", arg: "resources" };
    if (id === "tests") return { view: "catalogue", arg: "tests" };
    if (id === "ledger") return { view: "explorer" };
    if (id === "path") return { view: "path" };
    return null;
  };

  FG.parseHash = function (hash) {
    const route = { lang: FG.state.lang, lens: FG.state.lens, view: "path", arg: null, extra: null };
    if (!hash || hash === "#") {
      // The page is also the crate's HTML preview; opened as the preview it shows the machine-readable data
      // rather than the path landing, so a reader following the crate's preview link sees the crate, not a view
      // unrelated to it.
      if (/ro-crate-preview\.html$/.test(window.location.pathname)) {
        return Object.assign(route, FG.parseHash(FG.href("page", "machines")));
      }
      return route;
    }
    if (!hash.startsWith("#/")) {
      const target = FG.entityRoute(hash);
      return target ? Object.assign(route, target) : route;
    }
    const parts = hash
      .slice(2)
      .split("/")
      .map((part) => {
        try {
          return decodeURIComponent(part);
        } catch (error) {
          return "";
        }
      });
    if (LANGS.includes(parts[0])) route.lang = parts[0];
    if (FG.lenses().some((lens) => lens.audienceType === parts[1])) route.lens = parts[1];
    if (VIEWS.includes(parts[2])) route.view = parts[2];
    route.arg = parts[3] || null;
    route.extra = parts.slice(4).join("/") || null;
    return route;
  };

  /** Text for matching: without diacritics and in lower case. */
  FG.fold = (value) =>
    String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();

  /** A language map's Czech and English text together, for matching in either language. */
  FG.bothLanguages = (value) => FG.list(value).map((item) => typeof item === "string" || typeof item === "number"
    ? String(item) : item && item["@value"]).concat(value && typeof value === "object" ? searchTerms.get(value) : "").filter(Boolean).join(" ");

  /** Where the guide is, for links that leave the page (exports, shared links): the address the page is served from,
      or the configured address when it is opened as a local file. Nothing else names the site's address, so the
      guide can move. */
  FG.pageAddress = function () {
    return /^https?:$/.test(window.location.protocol) ? window.location.href.split("#")[0] : FG.config.pageUrl || "";
  };

  /** The directory of the page's files (the crate, the API) at that address. */
  FG.siteAddress = function () {
    const page = FG.pageAddress();
    return page ? new URL(".", page).href : "";
  };

  FG.href = function (view, arg, overrides) {
    const lang = (overrides && overrides.lang) || FG.state.lang;
    const lens = (overrides && overrides.lens) || FG.state.lens;
    return "#/" + [lang, lens, view].concat(arg ? [arg] : []).map(encodeURIComponent).join("/");
  };

  /** The current address with its language or lens changed, keeping the entry or part it names. */
  FG.routeHref = (route, overrides, arg = route.arg) => FG.href(route.view, arg, overrides) + (route.extra ? "/" + encodeURIComponent(route.extra) : "");

  /** Turn an advice action target into a link: in-page entity targets become routes, keeping the entry they name. */
  FG.actionHref = function (target) {
    if (target.startsWith("#")) {
      const route = FG.entityRoute(target);
      return route ? FG.routeHref(route) : "#";
    }
    return target;
  };

  /* ---------------------------------------------------------------- shared lookups */

  FG.lenses = () => FG.ofType("Audience").filter((entity) => entity["@id"].startsWith("#lens-"));
  FG.stations = () => FG.refs(FG.get("#path"), "step").sort(FG.byPosition);
  /** FAIR principles in a fixed order: F, A, I, R, then by number (A1 before A1.1 before A2). */
  FG.principleOrder = function (a, b) {
    const key = (principle) => {
      const code = String(principle.termCode || "");
      return ["FAIR".indexOf(code.charAt(0))].concat(code.slice(1).split(".").map(Number));
    };
    const left = key(a);
    const right = key(b);
    for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
      const x = index < left.length ? left[index] : -1;
      const y = index < right.length ? right[index] : -1;
      if (x !== y) return x - y;
    }
    return 0;
  };

  /** The principles an entity is about, in the fixed order. */
  FG.principlesOf = (entity) => FG.refs(entity, "about").filter((ref) => ref.termCode).sort(FG.principleOrder);
  FG.principles = () => FG.principlesOf(FG.root);
  FG.termName = (id) => FG.text(FG.get(id) && FG.get(id).name);
})();
