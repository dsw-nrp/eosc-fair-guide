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

  FG.render = function () {
    const route = FG.parseHash(window.location.hash);
    FG.state.lang = route.lang;
    FG.state.lens = route.lens;
    FG.saveState();
    document.documentElement.lang = route.lang;
    document.title = FG.t("app.title") + " | EOSC CZ";

    const view = (route.view === "check" || route.view === "selfcheck") && FG.views.selfcheck ? FG.views.selfcheck : FG.views[route.view] || FG.views.path;
    const app = document.getElementById("app");
    const main = FG.h("main", { id: "main", tabindex: "-1" }, view(route));
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
      FG.focusSelector = null;
    } else if (FG.focusAfterRender) {
      const anchor = route.extra ? main.querySelector("#" + CSS.escape(route.extra)) : null;
      const target = anchor || main.querySelector("h1") || main;
      target.focus({ preventScroll: false });
    }
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
    window.addEventListener("hashchange", FG.render);
    FG.render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
