/* Core of the FAIR data guide: the knowledge-base index, interface strings, safe DOM building, browser storage and
   routing. Every value from the crate or from a live service reaches the page as text; nothing is parsed as HTML. */
(function () {
  "use strict";

  const FG = (window.FairGuide = window.FairGuide || {});
  const STORAGE_KEY = "eosc-fair-guide";
  const LANGS = ["cs", "en"];

  /* ---------------------------------------------------------------- knowledge base */

  FG.load = function () {
    const crate = JSON.parse(document.getElementById("kb").textContent);
    const page = JSON.parse(document.getElementById("ui").textContent);
    FG.graph = crate["@graph"];
    FG.byId = new Map(FG.graph.map((entity) => [entity["@id"], entity]));
    FG.ui = page.ui;
    FG.config = page.config;
    FG.root = FG.byId.get("./");
    FG.DASHBOARD = FG.config.links.fipDashboard;
  };

  FG.list = (value) => (value == null ? [] : Array.isArray(value) ? value : [value]);
  FG.id = (value) => (typeof value === "string" ? value : value && value["@id"]);
  FG.get = (value) => FG.byId.get(FG.id(value));
  FG.refs = (entity, prop) => FG.list(entity && entity[prop]).map(FG.get).filter(Boolean);
  FG.refIds = (entity, prop) => FG.list(entity && entity[prop]).map(FG.id).filter(Boolean);
  FG.hasRef = (entity, prop, id) => FG.refIds(entity, prop).includes(id);
  FG.ofType = (type) => FG.graph.filter((entity) => FG.list(entity["@type"]).includes(type));
  FG.byPosition = (a, b) => (a.position || 0) - (b.position || 0);

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

  /** Paragraphs of a text whose paragraphs are separated by a blank line. */
  FG.paragraphs = function (value) {
    const { text, lang } = FG.textOf(value, FG.state.lang);
    return text
      .split(/\n\s*\n/)
      .filter(Boolean)
      .map((paragraph) => FG.h("p", { lang: lang || null }, paragraph));
  };

  /* ---------------------------------------------------------------- interface strings */

  FG.t = function (key, params) {
    const entry = key.split(".").reduce((node, part) => (node ? node[part] : undefined), FG.ui);
    let value = entry && (entry[FG.state.lang] || entry.cs) ? entry[FG.state.lang] || entry.cs : key;
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

  /* ---------------------------------------------------------------- safe DOM */

  const SAFE_SCHEME = /^(https:|mailto:)/i;
  const ANY_SCHEME = /^[a-z][a-z0-9+.-]*:/i;

  /** Only HTTPS, mailto, in-page and relative links are allowed; anything else becomes inert. */
  FG.safeHref = function (href) {
    const value = String(href || "").trim();
    if (value.startsWith("#") || SAFE_SCHEME.test(value)) return value;
    if (ANY_SCHEME.test(value) || value.startsWith("//")) return "#";
    return value;
  };

  FG.h = function (tag, attrs, ...children) {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attrs || {})) {
      if (value == null || value === false) continue;
      if (name === "class") element.className = value;
      else if (name.startsWith("on") && typeof value === "function") element.addEventListener(name.slice(2), value);
      else if (name === "href") element.setAttribute("href", FG.safeHref(value));
      else element.setAttribute(name, value === true ? "" : String(value));
    }
    for (const child of children.flat(Infinity)) {
      if (child == null || child === false || child === "") continue;
      element.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return element;
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
      } catch (error) {
        /* Storage can be unavailable (private windows, blocked site data); the guide works without it. */
      }
    },
  };

  FG.state = { lang: "cs", lens: "V", answers: {}, started: false, entryStation: null, lastStation: null };

  /** Disclosure levels the user opened (L1, L2, L3, ai); kept while the page is open, so switching lens keeps them. */
  FG.openLevels = new Set();

  FG.saveState = function () {
    FG.storage.write({
      lang: FG.state.lang,
      lens: FG.state.lens,
      answers: FG.state.answers,
      started: FG.state.started,
      entryStation: FG.state.entryStation,
      lastStation: FG.state.lastStation,
    });
  };

  /* ---------------------------------------------------------------- routing */

  const VIEWS = ["path", "check", "explorer", "resources", "repositories", "page", "selfcheck"];

  /** In-page targets that name crate entities, as used by advice actions. */
  FG.entityRoute = function (hash) {
    const id = hash.replace(/^#/, "");
    let match;
    if ((match = id.match(/^station-(.+)$/))) return { view: "path", arg: match[1] };
    if ((match = id.match(/^check-(.+)$/))) return { view: "check", arg: match[1] };
    if ((match = id.match(/^page-(.+)$/))) return { view: "page", arg: match[1] };
    if ((match = id.match(/^resource-(.+)$/))) return { view: "resources", arg: match[1] };
    if (id === "repositories") return { view: "repositories" };
    if (id === "resources") return { view: "resources" };
    if (id === "ledger") return { view: "explorer" };
    if (id === "path") return { view: "path" };
    return null;
  };

  FG.parseHash = function (hash) {
    const route = { lang: FG.state.lang, lens: FG.state.lens, view: "path", arg: null, extra: null };
    if (!hash || hash === "#") return route;
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
    route.extra = parts[4] || null;
    return route;
  };

  FG.href = function (view, arg, overrides) {
    const lang = (overrides && overrides.lang) || FG.state.lang;
    const lens = (overrides && overrides.lens) || FG.state.lens;
    return "#/" + [lang, lens, view].concat(arg ? [arg] : []).map(encodeURIComponent).join("/");
  };

  /** Turn an advice action target into a link: in-page entity targets become routes. */
  FG.actionHref = function (target) {
    if (target.startsWith("#")) {
      const route = FG.entityRoute(target);
      return route ? FG.href(route.view, route.arg) : "#";
    }
    return target;
  };

  /* ---------------------------------------------------------------- shared lookups */

  FG.lenses = () => FG.ofType("Audience").filter((entity) => entity["@id"].startsWith("#lens-"));
  FG.stations = () => FG.refs(FG.get("#path"), "step").sort(FG.byPosition);
  FG.principles = () => FG.refs(FG.root, "about");
  FG.termName = (id) => FG.text(FG.get(id) && FG.get(id).name);
})();
