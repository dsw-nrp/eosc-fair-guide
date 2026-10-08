/* Start-up and rendering of the FAIR data guide. The page makes no request to an external service on load. */
(function () {
  "use strict";

  const FG = window.FairGuide;

  FG.navigate = function (hash) {
    if (window.location.hash === hash) FG.render();
    else window.location.hash = hash;
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
    app.replaceChildren(
      FG.h("a", { class: "skip-link", href: "#main", onclick: skipToMain }, FG.t("app.skip")),
      FG.views.header(route),
      FG.views.notice(),
      FG.views.nav(route),
      main,
      FG.views.footer()
    );
    if (FG.focusAfterRender) {
      const target = main.querySelector("h1") || main;
      target.focus({ preventScroll: false });
    }
    FG.focusAfterRender = true;
  };

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
    });
    FG.focusAfterRender = false;
    window.addEventListener("hashchange", FG.render);
    FG.render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
