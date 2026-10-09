/* Start-up and rendering of the FAIR Data Guide. The page makes no request to an external service on load. */
(function () {
  "use strict";

  const FG = window.FairGuide;

  FG.navigate = function (hash) {
    if (window.location.hash === hash) FG.render();
    else window.location.hash = hash;
  };

  /** Navigate without moving focus or scrolling, as when switching the lens to compare roles on the same view.
      `focus` is a selector for the control that takes focus in the new view, such as the chosen lens. */
  FG.navigateInPlace = function (hash, focus) {
    FG.keepScroll = window.scrollY;
    FG.focusSelector = focus || null;
    FG.focusAfterRender = false;
    FG.navigate(hash);
  };

  /** Like navigateInPlace, but replace the current history entry, as when refining a filtered list: the address
      follows every change, and Back leaves the list instead of undoing one filter at a time. */
  FG.replaceInPlace = function (hash, focus) {
    FG.keepScroll = window.scrollY;
    FG.focusSelector = focus || null;
    FG.focusAfterRender = false;
    window.history.replaceState(null, "", hash);
    FG.render();
  };

  /* The parts of the knowledge base a view needs beyond the start: requirement guidance and the FIP profiles for
     the catalogue and the checks, the pages' text for a page. */
  const VIEW_PARTS = { catalogue: ["guidance", "fips"], check: ["guidance", "fips"], selfcheck: ["guidance", "fips"], page: ["pages"] };

  FG.render = function () {
    const route = FG.parseHash(window.location.hash);
    /* A view whose parts have not arrived yet renders once they have; the previous view stays until then. */
    const missing = (VIEW_PARTS[route.view] || []).filter((name) => !FG.partsLoaded.has(name));
    if (missing.length) {
      Promise.allSettled(missing.map(FG.loadPart)).then((results) => {
        for (const result of results) if (result.status === "rejected") console.error(result.reason.message);
        FG.render();
      });
      return;
    }
    FG.state.lang = route.lang;
    FG.state.lens = route.lens;
    FG.saveState();
    document.documentElement.lang = route.lang;
    document.title = FG.t("app.title") + " | EOSC CZ";

    const isCheck = (route.view === "check" || route.view === "selfcheck") && FG.views.selfcheck;
    const view = isCheck ? FG.views.selfcheck : FG.views[route.view] || FG.views.path;
    const app = document.getElementById("app");
    FG.exports = [];
    const main = FG.h("main", { id: "main", tabindex: "-1" }, view(route));
    /* A single check saves its result in its own export area; every other view gets the shared one. */
    if (!(isCheck && route.arg)) main.append(FG.exportBar());
    const parts = [
      FG.h("a", { class: "skip-link", href: "#main", onclick: skipToMain }, FG.t("app.skip")),
      FG.views.header(route),
      FG.views.notice(),
      FG.views.nav(route),
      FG.views.lensBand(route),
      main,
      FG.views.footer(),
    ];
    app.replaceChildren(...parts.filter(Boolean));
    if (typeof FG.keepScroll === "number") {
      window.scrollTo(0, FG.keepScroll);
      FG.keepScroll = null;
      const control = FG.focusSelector ? document.querySelector(FG.focusSelector) : null;
      if (control) control.focus({ preventScroll: true });
      /* A text field rendered again keeps its caret: where it was, or at the end of the text. */
      if (control && typeof control.setSelectionRange === "function" && /^(search|text)$/.test(control.type)) {
        const [start, end] = (control.dataset.caret || "").split(",").map(Number);
        const length = control.value.length;
        control.setSelectionRange(Number.isFinite(start) ? Math.min(start, length) : length, Number.isFinite(end) ? Math.min(end, length) : length);
      }
      FG.focusSelector = null;
    } else {
      const entry = route.extra ? main.querySelector("#item-" + CSS.escape(route.extra)) : null;
      const anchor = route.extra ? main.querySelector("#" + CSS.escape(route.extra)) || entry : null;
      if (entry && anchor === entry && (FG.focusAfterRender || FG.firstRender)) {
        /* A link to one entry of a list, followed or opened directly: bring it to the middle of the view and mark it
           briefly. */
        entry.scrollIntoView({ block: "center" });
        entry.focus({ preventScroll: true });
        entry.classList.add("jumped");
        setTimeout(() => entry.classList.remove("jumped"), 1600);
      } else if (FG.focusAfterRender) (anchor || main.querySelector("h1") || main).focus({ preventScroll: false });
    }
    FG.firstRender = false;
    FG.focusAfterRender = true;
  };

  /** Render again without moving focus to the heading, then return focus to the control that caused it. */
  FG.rerender = function (focusId) {
    FG.focusAfterRender = false;
    FG.render();
    const target = focusId ? document.getElementById(focusId) : null;
    if (target) target.focus({ preventScroll: true });
  };

  /* Closed disclosures do not print, so every one opens for printing and closes again afterwards. */
  let closedForPrint = [];
  window.addEventListener("beforeprint", () => {
    closedForPrint = [...document.querySelectorAll("details:not([open])")];
    for (const element of closedForPrint) element.open = true;
  });
  window.addEventListener("afterprint", () => {
    for (const element of closedForPrint) element.open = false;
    closedForPrint = [];
  });

  function skipToMain(event) {
    event.preventDefault();
    const main = document.getElementById("main");
    if (main) main.focus();
  }

  function start() {
    try {
      FG.load();
    } catch (error) {
      const app = document.getElementById("app");
      if (app) app.textContent = "Průvodce se nepodařilo načíst. / The guide could not be loaded.";
      return;
    }
    const saved = FG.storage.read();
    Object.assign(FG.state, {
      lang: saved.lang === "en" ? "en" : "cs",
      lens: typeof saved.lens === "string" ? saved.lens : "V",
      answers: saved.answers && typeof saved.answers === "object" ? saved.answers : {},
      started: Boolean(saved.started),
      entryStation: typeof saved.entryStation === "string" ? saved.entryStation : null,
      lastStation: typeof saved.lastStation === "string" ? saved.lastStation : null,
      lastVisit: typeof saved.lastVisit === "string" && /^\d{4}-\d{2}-\d{2}$/.test(saved.lastVisit) ? saved.lastVisit : null,
      checkGrouping: saved.checkGrouping === "steps" ? "steps" : "principles",
      resultCollapsed: saved.resultCollapsed === true,
    });
    const known = (id) => FG.stations().some((station) => station.identifier === id);
    if (!known(FG.state.entryStation)) FG.state.entryStation = null;
    if (!known(FG.state.lastStation)) FG.state.lastStation = null;
    FG.focusAfterRender = false;
    FG.firstRender = true;
    window.addEventListener("hashchange", FG.render);
    /* Printing shows the closed sections too, and closes them again afterwards. */
    let opened = [];
    window.addEventListener("beforeprint", () => {
      opened = [...document.querySelectorAll("#main details:not([open])")];
      for (const section of opened) section.open = true;
    });
    window.addEventListener("afterprint", () => {
      for (const section of opened) section.open = false;
      opened = [];
    });
    FG.render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
