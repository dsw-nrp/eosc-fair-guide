/* Core of the FAIR Data Guide: the knowledge-base index, interface strings, safe DOM building, browser storage and
   routing. Every value from the crate or from a live service reaches the page as text; nothing is parsed as HTML. */
(function () {
  "use strict";

  const FG = (window.FairGuide = window.FairGuide || {});
  const STORAGE_KEY = "eosc-fair-guide";
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

  /** Today's date in the visitor's time zone, as YYYY-MM-DD. */
  FG.today = function () {
    const now = new Date();
    return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
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
    remove() {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch (error) {
        /* Nothing to remove when storage is unavailable. */
      }
    },
  };

  FG.state = { lang: "cs", lens: "V", answers: {}, started: false, entryStation: null, lastStation: null, lastVisit: null, checkGrouping: "principles", resultCollapsed: false };

  /** Disclosure levels the user opened (L1, L2, L3, ai); kept while the page is open, so switching lens keeps them. */
  FG.openLevels = new Set();

  /** Whether the state holds nothing worth keeping: language and lens come from the address anyway. */
  const isEmptyState = (state) =>
    !Object.keys(state.answers || {}).length &&
    !state.started &&
    !state.entryStation &&
    !state.lastStation &&
    !state.lastVisit &&
    state.checkGrouping !== "steps" &&
    !state.resultCollapsed;

  /** Remove everything the guide stores in this browser and start from an empty state. */
  FG.clearStoredData = function () {
    Object.assign(FG.state, { answers: {}, started: false, entryStation: null, lastStation: null, lastVisit: null, checkGrouping: "principles", resultCollapsed: false });
    FG.openLevels.clear();
    FG.storage.remove();
  };

  FG.saveState = function () {
    if (isEmptyState(FG.state)) {
      FG.storage.remove();
      return;
    }
    FG.storage.write({
      lang: FG.state.lang,
      lens: FG.state.lens,
      answers: FG.state.answers,
      started: FG.state.started,
      entryStation: FG.state.entryStation,
      lastStation: FG.state.lastStation,
      lastVisit: FG.state.lastVisit,
      checkGrouping: FG.state.checkGrouping,
      resultCollapsed: FG.state.resultCollapsed,
    });
  };

  /* ---------------------------------------------------------------- routing */

  const VIEWS = ["path", "check", "explorer", "catalogue", "resources", "repositories", "tools", "page", "selfcheck"];
  /* The resource and repository finders are tabs of the catalogue; their own addresses still lead there. */
  const CATALOGUE_TABS = ["resources", "repositories"];

  /** In-page targets that name crate entities, as used by advice actions. */
  FG.entityRoute = function (hash) {
    const id = hash.replace(/^#/, "");
    let match;
    if ((match = id.match(/^station-(.+)$/))) return { view: "path", arg: match[1] };
    if ((match = id.match(/^check-(.+)$/))) return { view: "check", arg: match[1] };
    if ((match = id.match(/^page-(.+)$/))) return { view: "page", arg: match[1] };
    if ((match = id.match(/^resource-(.+)$/))) return { view: "catalogue", arg: "resources", extra: match[1] };
    if (id === "repositories") return { view: "catalogue", arg: "repositories" };
    if (id === "resources") return { view: "catalogue", arg: "resources" };
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
    if (CATALOGUE_TABS.includes(route.view)) Object.assign(route, { view: "catalogue", arg: route.view, extra: route.arg });
    return route;
  };

  /** Text for matching: without diacritics and in lower case. */
  FG.fold = (value) =>
    String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();

  /** A language map's Czech and English text together, for matching in either language. */
  FG.bothLanguages = (value) => FG.textOf(value, "cs").text + " " + FG.textOf(value, "en").text;

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
