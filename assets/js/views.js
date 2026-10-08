/* Views of the FAIR Data Guide: shell, path, principle explorer, resource and repository finders, pages. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const h = (...args) => FG.h(...args);
  const STATUS_ICON = { operational: "●", pilot: "◐", "in-development": "◔", planned: "○", prospective: "◌" };
  const KIND_ORDER = ["#rkind-domain", "#rkind-institutional", "#rkind-general"];
  FG.views = {};

  /* ---------------------------------------------------------------- shared pieces */

  /** A heading that can receive focus after navigation. */
  function heading(level, attrs, ...children) {
    return h("h" + level, Object.assign({ tabindex: "-1" }, attrs || {}), ...children);
  }

  FG.heading = heading;

  function isStale(asOf) {
    if (!asOf) return false;
    const days = (Date.now() - new Date(asOf + "T00:00:00Z").getTime()) / 86400000;
    return days > (FG.config.freshnessDays || 180);
  }

  function statusBadge(entity) {
    const statusId = FG.id(entity.serviceStatus);
    if (!statusId) return null;
    const code = statusId.replace("#status-", "");
    const asOf = entity.statusAsOf;
    return h(
      "span",
      { class: "badge", "data-status": code },
      h("span", { "aria-hidden": "true" }, STATUS_ICON[code] || "•"),
      FG.termName(statusId),
      asOf ? h("span", { class: "muted" }, " · " + FG.t("status.asOf", { date: FG.formatDate(asOf) })) : null,
      isStale(asOf) ? h("span", null, " · " + FG.t("status.stale")) : null
    );
  }

  /** The FIP Dashboard record of a resource, if the guide links one, with its verifications. */
  function dashboardRecord(entity) {
    const url = FG.refIds(entity, "sameAs").find((id) => id.startsWith(FG.DASHBOARD + "resources/"));
    if (!url) return null;
    const fer = FG.get("#fer-" + url.split("/").pop());
    return { url, fer };
  }

  function verificationBadges(fer) {
    if (!fer) return [];
    const reviews = FG.refs(fer, "review");
    const byLevel = (level) => reviews.filter((review) => review.reviewAspect === level);
    const badges = [];
    const verified = byLevel("verified");
    if (verified.length) {
      const names = verified.map((review) => FG.text((FG.get(review.author) || {}).alternateName || (FG.get(review.author) || {}).name));
      badges.push(h("span", { class: "badge", "data-verification": "verified" }, h("span", { "aria-hidden": "true" }, "✓"), FG.t("resource.verified", { verifiers: names.join(", ") })));
    }
    if (byLevel("self-declared").length) badges.push(h("span", { class: "badge" }, FG.t("resource.selfDeclared")));
    if (byLevel("under-review").length) badges.push(h("span", { class: "badge" }, FG.t("resource.underReview")));
    return badges;
  }

  function resourceCard(resource) {
    const record = dashboardRecord(resource);
    const name = FG.text(resource.name);
    const languages = FG.list(resource.inLanguage);
    return h(
      "li",
      { class: "card" },
      h("h3", null, FG.external(resource.url, name)),
      resource.description ? h("p", null, FG.span(resource.description)) : null,
      h(
        "div",
        { class: "badges" },
        h("span", { class: "badge" }, FG.termName(FG.id(resource.resourceType))),
        statusBadge(resource),
        languages.length ? h("span", { class: "badge" }, FG.t("resource.languages", { languages: languages.join(", ") })) : null,
        record ? verificationBadges(record.fer) : null,
        record ? FG.external(record.url, FG.t("resource.dashboard"), { class: "small" }) : null
      )
    );
  }

  function lensOf(entity, lens) {
    return FG.hasRef(entity, "audience", "#lens-" + lens);
  }

  /* ---------------------------------------------------------------- shell */

  /** A FAIR principle as a tile: its letter in the F/A/I/R colour, then the rest of the code and the short title,
      so the tile reads "R1.1 Licence" and links to the principle in the explorer. */
  FG.principleTile = function (principle, attrs) {
    const code = String(principle.termCode);
    return h(
      "a",
      Object.assign({ class: "principle-tile", "data-letter": code.charAt(0), href: FG.href("explorer", code) }, attrs || {}),
      h("span", { class: "principle-letter" }, code.charAt(0)),
      h("span", null, code.slice(1) + " ", FG.span(principle.name))
    );
  };

  const principleTiles = (principles, label) =>
    h("ul", { class: "principle-tiles", "aria-label": label || null }, principles.map((principle) => h("li", null, FG.principleTile(principle))));

  /** The icon of a disclosure level, or of a named interface role. */
  const levelIcon = (code) => FG.icon((FG.config.icons && FG.config.icons.level && FG.config.icons.level[code]) || "");

  /** Whether a path route shows the landing (the path's start) rather than a station. */
  FG.landingShown = function (route) {
    return route.view === "path" && (route.arg === "start" || (!route.arg && !FG.state.started));
  };

  FG.views.header = function (route) {
    const otherLang = route.lang === "cs" ? "en" : "cs";
    return h(
      "header",
      { class: "site-header" },
      h(
        "div",
        { class: "wrap" },
        h(
          "div",
          { class: "brand" },
          FG.external(FG.config.links.eoscHome, h("img", { src: "assets/img/eosc-cz-logo.svg", alt: FG.t("app.home"), width: "144", height: "30" })),
          h("a", { class: "brand-title", href: FG.href("path", "start") }, FG.t("app.title"))
        ),
        h(
          "div",
          { class: "controls" },
          h("a", { class: "button", href: FG.href(route.view, route.arg, { lang: otherLang }), lang: otherLang, hreflang: otherLang }, FG.t("nav.switchTo"))
        )
      )
    );
  };

  /* Views whose content the lens changes; the lens band is shown only there. */
  const LENS_VIEWS = new Set(["path", "selfcheck", "resources"]);

  /** The lens switch: four links under the main menu, each shareable, switching in place so roles can be compared
      at the same position; focus stays on the chosen lens. */
  FG.views.lensBand = function (route) {
    if (!LENS_VIEWS.has(route.view)) return null;
    const icons = (FG.config.icons && FG.config.icons.lens) || {};
    const arg = FG.landingShown(route) ? "start" : route.arg;
    const option = (lens) => {
      const href = FG.href(route.view, arg, { lens: lens.audienceType });
      const switchInPlace = (event) => {
        if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        FG.navigateInPlace(href, `.lens-option[data-lens="${lens.audienceType}"]`);
      };
      return h(
        "li",
        null,
        h(
          "a",
          {
            class: "lens-option",
            href,
            "data-lens": lens.audienceType,
            "aria-current": lens.audienceType === route.lens ? "true" : null,
            onclick: switchInPlace,
          },
          FG.icon(icons[lens.audienceType], { class: "icon-large" }),
          h("span", null, FG.text(lens.name))
        )
      );
    };
    return h(
      "nav",
      { class: "lens-band", "aria-label": FG.t("nav.lens") },
      h("div", { class: "wrap" }, h("span", { class: "lens-band-label", "aria-hidden": "true" }, FG.t("nav.lens")), h("ul", null, FG.lenses().map(option)))
    );
  };

  FG.views.notice = function () {
    if (FG.config.releaseStatus !== "testing" || !FG.config.testingNotice) return null;
    return h(
      "div",
      { class: "testing-notice", role: "note", "aria-label": FG.t("app.testing") },
      h("div", { class: "wrap" }, h("p", null, h("strong", null, FG.t("app.testing") + ":"), FG.config.testingNotice[FG.state.lang]))
    );
  };

  FG.views.nav = function (route) {
    const first = FG.stations()[0];
    const station = FG.state.lastStation || FG.state.entryStation || (first && first.identifier);
    const landing = FG.landingShown(route);
    const items = [
      ["path", "start", "nav.home", landing],
      ["path", station, "nav.path", route.view === "path" && !landing],
      ["selfcheck", null, "nav.selfcheck", route.view === "selfcheck" || route.view === "check"],
      ["explorer", null, "nav.explorer", route.view === "explorer"],
      ["resources", null, "nav.resources", route.view === "resources"],
      ["repositories", null, "nav.repositories", route.view === "repositories"],
      ["page", "about", "nav.about", route.view === "page" && route.arg === "about"],
    ];
    return h(
      "nav",
      { class: "main-nav wrap", "aria-label": FG.t("nav.label") },
      h(
        "ul",
        null,
        items.map(([view, arg, key, current]) => h("li", null, h("a", { href: FG.href(view, arg), "aria-current": current ? "page" : null }, FG.t(key))))
      )
    );
  };

  /** "Ilona Trtíková" as "Trtíková, I." */
  function citedName(name) {
    const parts = String(name).trim().split(/\s+/);
    const family = parts.pop();
    return parts.length ? family + ", " + parts.map((part) => part.charAt(0) + ".").join(" ") : family;
  }

  const yearOf = (date) => String(date || "").slice(0, 4);

  /** A published work cited with its authors, year, title, version and link. */
  function citeWork(work) {
    const people = FG.refs(work, "author");
    const names = people.length ? people.map((person) => person.name) : String(work.creditText || "").split(";").filter(Boolean);
    return [
      names.map(citedName).join(", "),
      " (" + yearOf(work.datePublished) + "). ",
      h("em", null, FG.text(work.name)),
      work.version ? ", " + FG.t("cite.version", { v: work.version }) : "",
      ". ",
      work.url ? FG.external(work.url, work.url) : null,
    ];
  }

  /** The guide cited as software, with its compiler as editor. */
  function citeGuide(root) {
    const editors = FG.refs(root, "editor").map((person) => citedName(person.name));
    const publisher = FG.get(root.publisher);
    return [
      editors.join(", ") + (editors.length ? " (" + FG.t("cite.editor") + ")" : ""),
      " (" + yearOf(root.datePublished) + "). ",
      h("em", null, FG.text(root.name)),
      ", " + FG.t("cite.version", { v: root.version }) + " [" + FG.t("cite.software") + "]. ",
      publisher ? FG.text(publisher.name) + ". " : "",
      FG.external(root.url, root.url),
    ];
  }

  FG.views.footer = function () {
    const root = FG.root;
    const analysis = FG.refs(root, "isBasedOn")[0];
    return h(
      "footer",
      { class: "site-footer" },
      h(
        "div",
        { class: "wrap" },
        h("p", null, FG.t("footer.version", { version: FG.config.version, date: FG.formatDate(FG.config.datePublished) })),
        analysis ? h("p", null, h("strong", null, FG.t("footer.basis") + ": "), citeWork(analysis)) : null,
        h("p", null, h("strong", null, FG.t("footer.cite") + ": "), citeGuide(root), " · ", h("a", { href: FG.href("page", "about") + "/credits" }, FG.t("footer.credits"))),
        h("p", null, FG.t("footer.licence")),
        h(
          "ul",
          null,
          h("li", null, h("a", { href: FG.href("page", "accessibility") }, FG.t("footer.accessibility"))),
          h("li", null, h("a", { href: FG.href("page", "about") }, FG.t("footer.ai"))),
          h("li", null, FG.external(root.url, FG.t("footer.repository"))),
          h("li", null, h("a", { href: "ro-crate-metadata.json" }, FG.t("footer.crate")))
        ),
        h("p", null, FG.span(root.usageInfo)),
        h("p", null, FG.span(root.creditText)),
        logolink()
      )
    );
  };

  /** The published logolink in two windows onto the same image: the EU and MŠMT pair, kept whole, and the EOSC CZ
      logo, which moves below the pair on a narrow screen so both stay legible. Each logo links to its owner through
      a link laid over its part of the image. */
  function logolink() {
    const project = FG.refs(FG.root, "funder")[0];
    const ministry = project && FG.refs(project, "funder")[0];
    const image = () => h("img", { src: `assets/img/logolink-${FG.state.lang}.svg`, alt: "" });
    const part = (url, name, which) => (url ? FG.external(url, h("span", { class: "visually-hidden" }, name), { class: "logolink-part logolink-" + which }) : null);
    return h(
      "div",
      { class: "logolink logolink-" + FG.state.lang },
      h("div", { class: "logolink-crop logolink-funding" }, image(), part(FG.config.links.opJak, FG.t("footer.logoEu"), "eu"), part(ministry && ministry.url, FG.text(ministry && ministry.name), "ministry")),
      h("div", { class: "logolink-crop logolink-initiative" }, image(), part(FG.config.links.eoscHome, FG.t("footer.logoEosc"), "eosc"))
    );
  }

  /* ---------------------------------------------------------------- path */

  /** The stage switch on the path: the chosen stage, changeable without returning to the landing. */
  function stageSwitch() {
    const stages = stageRanges();
    const chosen = chosenStage(stages);
    const icons = (FG.config.icons && FG.config.icons.stage) || {};
    return h(
      "details",
      { class: "stage-switch" },
      h(
        "summary",
        null,
        h("span", { class: "small muted" }, FG.t("stage.yours")),
        h("strong", null, chosen ? FG.span(chosen.stage.name) : FG.t("stage.none")),
        h("span", { class: "small stage-switch-action" }, FG.t("stage.change"))
      ),
      h(
        "ul",
        null,
        stages.map((entry) =>
          h(
            "li",
            null,
            h(
              "button",
              { type: "button", "aria-pressed": String(entry === chosen), onclick: () => chooseStage(entry.stage) },
              FG.icon(icons[entry.stage.termCode]),
              h("span", null, FG.span(entry.stage.name), h("span", { class: "small muted" }, " · " + stepsLabel(entry.from, entry.to)))
            )
          )
        )
      )
    );
  }

  function rail(route, currentId) {
    const current = FG.stations().find((station) => station.identifier === currentId);
    return [
      stageSwitch(),
      h("nav", { class: "rail rail-desktop", "aria-label": FG.t("nav.stations") }, railList(currentId), railLegend()),
      h(
        "details",
        { class: "rail rail-mobile" },
        h("summary", null, FG.t("nav.stations"), current ? ": " + current.position + " · " + FG.text(current.name) : ""),
        h("nav", { "aria-label": FG.t("nav.stations") }, railList(currentId), railLegend())
      ),
    ];
  }

  function railList(currentId) {
    const icons = (FG.config.icons && FG.config.icons.station) || {};
    const entryStation = FG.state.entryStation;
    let beforeEntry = Boolean(entryStation);
    return h(
        "ol",
        null,
        FG.stations().map((station) => {
          if (station.identifier === entryStation) beforeEntry = false;
          const gaps = FG.gapsAt ? FG.gapsAt(station.identifier) : 0;
          return h(
            "li",
            { class: beforeEntry ? "earlier" : null },
            h(
              "a",
              { href: FG.href("path", station.identifier), "aria-current": station.identifier === currentId ? "step" : null },
              h("span", { class: "number" }, String(station.position)),
              FG.icon(icons[station.identifier]) || h("span"),
              FG.span(station.name),
              gaps ? h("span", { class: "gap-mark" }, h("span", { "aria-hidden": "true" }, String(gaps)), h("span", { class: "visually-hidden" }, " " + FG.t("selfcheck.gapsHere", { n: gaps }))) : null
            )
          );
        })
    );
  }

  /** The legend for the self-check marks on the rail, shown only when there is a mark to explain. */
  function railLegend() {
    const total = FG.gapsAt ? FG.stations().reduce((sum, station) => sum + FG.gapsAt(station.identifier), 0) : 0;
    if (!total) return null;
    return h(
      "p",
      { class: "rail-legend" },
      h("span", { class: "gap-mark", "aria-hidden": "true" }, String(total)),
      h("a", { href: FG.href("selfcheck") }, FG.t("selfcheck.gapsLegend"))
    );
  }

  function resumeLine() {
    const station = FG.stations().find((item) => item.identifier === FG.state.lastStation);
    if (!station) return null;
    return h(
      "p",
      { class: "resume" },
      h("a", { href: FG.href("path", station.identifier) }, FG.t("stage.resume", { n: station.position, station: FG.text(station.name) }))
    );
  }

  /** The four stages in path order, each with the range of steps it covers. */
  function stageRanges() {
    const stages = FG.ofType("DefinedTerm")
      .filter((term) => FG.id(term.inDefinedTermSet) === "#stages")
      .map((stage) => ({ stage, from: FG.get(stage.startsAt).position }))
      .sort((a, b) => a.from - b.from);
    stages.forEach((entry, index) => (entry.to = index + 1 < stages.length ? stages[index + 1].from - 1 : FG.stations().length));
    return stages;
  }

  const stepsLabel = (from, to) => (from === to ? FG.t("stage.step", { n: from }) : FG.t("stage.steps", { from, to }));

  /** Choosing a stage starts the path at its first station; the menu's path item and the rail follow the choice. */
  function chooseStage(stage) {
    const station = FG.get(stage.startsAt).identifier;
    FG.state.started = true;
    FG.state.entryStation = station;
    FG.saveState();
    FG.navigate(FG.href("path", station));
  }

  /** The stage the visitor chose; none until they choose one. */
  function chosenStage(stages) {
    return FG.state.started ? stages.find(({ stage }) => FG.get(stage.startsAt).identifier === FG.state.entryStation) || null : null;
  }

  /** The stage question as a journey: four cards in path order, each naming the steps it covers. The card of the
      stage the visitor chose says so, with the date of their last visit to the path. */
  function stageCards() {
    const stages = stageRanges();
    const chosen = chosenStage(stages);
    const icons = (FG.config.icons && FG.config.icons.stage) || {};
    return h(
      "ol",
      { class: "stage-options" },
      stages.map((entry) => {
        const { stage, from, to } = entry;
        const current = entry === chosen;
        return h(
          "li",
          null,
          h(
            "button",
            {
              type: "button",
              class: "stage-card" + (current ? " stage-current" : ""),
              onclick: () => chooseStage(stage),
            },
            h(
              "span",
              { class: "stage-steps" },
              FG.icon(icons[stage.termCode], { class: "icon-large" }),
              stepsLabel(from, to),
              current
                ? h("span", { class: "badge" }, FG.state.lastVisit ? FG.t("stage.chosenOn", { date: FG.formatDate(FG.state.lastVisit) }) : FG.t("stage.chosen"))
                : null
            ),
            h("strong", null, FG.span(stage.name)),
            stage.description ? h("span", { class: "small muted" }, FG.span(stage.description)) : null
          )
        );
      })
    );
  }

  function taskTile(task) {
    const label = task.label[FG.state.lang] || task.label.cs;
    const children = [FG.icon(task.icon, { class: "icon-large" }), h("span", null, label)];
    return h(
      "li",
      null,
      task.href.startsWith("#") ? h("a", { class: "task", href: FG.actionHref(task.href) }, children) : FG.external(task.href, children, { class: "task" })
    );
  }

  function trustLine() {
    const analysis = FG.refs(FG.root, "isBasedOn")[0];
    const firstAuthor = analysis && String(analysis.creditText || "").split(";")[0].trim().split(" ").pop();
    return h(
      "p",
      { class: "trust" },
      FG.t("landing.trustBasis") + " ",
      analysis ? FG.external(analysis.url, FG.t("basis.analysis")) : FG.t("basis.analysis"),
      firstAuthor ? " (" + FG.t("landing.trustAuthors", { author: firstAuthor }) + ")" : "",
      " · " + FG.t("landing.trustPrivacy"),
      " · " + FG.t("landing.trustUpdated", { date: FG.formatDate(FG.config.datePublished) })
    );
  }

  /** The landing view, which is the path's start: search, stage, tasks, resume line, routes to help. */
  function landing(route) {
    const tasks = FG.list(FG.config.tasks).filter((task) => task.lens === route.lens);
    const steward = FG.get("#help-data-steward");
    return h(
      "div",
      { class: "landing wrap" },
      heading(1, null, FG.t("app.title")),
      h("p", { class: "lead" }, FG.t("app.tagline")),
      FG.search ? FG.search.form() : null,
      h(
        "section",
        { class: "stage-entry", "aria-labelledby": "stage-question" },
        h("h2", { id: "stage-question" }, FG.t("stage.question")),
        h("p", { class: "muted" }, FG.t("stage.intro")),
        stageCards()
      ),
      tasks.length
        ? h("section", { "aria-labelledby": "tasks-title" }, h("h2", { id: "tasks-title" }, FG.t("landing.tasks")), h("ul", { class: "tasks" }, tasks.map(taskTile)))
        : null,
      resumeLine(),
      h(
        "p",
        { class: "routes" },
        steward ? h("span", null, FG.icon("help"), " " + FG.t("landing.helpRoute") + " ", FG.external(steward.url, FG.text(steward.name))) : null,
        h("span", null, FG.icon("dashboard"), " " + FG.t("landing.dashboardRoute") + " ", FG.external(FG.config.links.fipDashboard, "FIP Dashboard"))
      ),
      trustLine()
    );
  }

  function adviceItem(item) {
    const steps = FG.refs(item, "hasPart").sort(FG.byPosition);
    return h("li", null, FG.span(item.text), steps.length ? h("ul", null, steps.map((step) => h("li", null, FG.span(step.text)))) : null);
  }

  /** A disclosure level whose open state survives a lens switch while the page stays open. */
  function details(summary, key, ...content) {
    return h(
      "details",
      {
        "data-key": key,
        open: FG.openLevels.has(key),
        ontoggle: (event) => (event.target.open ? FG.openLevels.add(key) : FG.openLevels.delete(key)),
      },
      h("summary", null, summary),
      h("div", { class: "content" }, ...content)
    );
  }

  function whyContent(station, items) {
    const notes = items.filter((item) => FG.id(item.disclosureLevel) === "#level-L2" && item.adviceKind !== "ai").sort(FG.byPosition);
    const principles = FG.refs(station, "about");
    const clauses = [];
    for (const item of items) {
      for (const clause of FG.refs(item, "citation")) if (!clauses.includes(clause)) clauses.push(clause);
    }
    return [
      notes.length ? h("ul", null, notes.map((note) => h("li", null, FG.span(note.text)))) : null,
      h("h3", null, FG.t("station.whyPrinciples")),
      principleTiles(principles),
      h("h3", null, FG.t("station.whyClauses")),
      h(
        "ul",
        { class: "clauses" },
        clauses.map((clause) => {
          const source = FG.get(clause.isPartOf);
          return h(
            "li",
            null,
            h("span", { class: "clause-id" }, clause.identifier),
            " ",
            FG.span(clause.text),
            source ? h("span", { class: "muted small" }, " (", source.url ? FG.external(source.url, FG.text(source.name)) : FG.text(source.name), ")") : null
          );
        })
      ),
    ];
  }

  /** The published sources the given items cite, through their clauses. */
  function sourcesOf(items) {
    const sources = [];
    for (const item of items) {
      for (const clause of FG.refs(item, "citation")) {
        const source = FG.get(clause.isPartOf);
        if (source && !sources.includes(source)) sources.push(source);
      }
    }
    return sources;
  }

  /** The provenance actions that produced or changed the given items. */
  function actionsOf(items) {
    const ids = new Set(items.map((item) => item["@id"]));
    return FG.graph.filter((entity) => /Action$/.test(FG.list(entity["@type"])[0]) && FG.refIds(entity, "result").some((id) => ids.has(id)));
  }

  /** One quiet line on what a station's content is based on and when it last changed, without person names. */
  function provenanceLine(items) {
    const sources = sourcesOf(items);
    const analysis = FG.refs(FG.root, "isBasedOn")[0];
    const others = sources.filter((source) => source !== analysis).length;
    const basis = sources.includes(analysis)
      ? others
        ? FG.t("basis.withOthers", { analysis: FG.t("basis.analysis"), n: others })
        : FG.t("basis.onlyAnalysis", { analysis: FG.t("basis.analysis") })
      : FG.t("basis.sources", { n: sources.length });
    const latest = actionsOf(items)
      .map((action) => String(action.endTime || ""))
      .sort()
      .pop();
    const openDetails = () => {
      const level = document.querySelector('details[data-key="L3"]');
      if (!level) return;
      level.open = true;
      FG.openLevels.add("L3");
      level.scrollIntoView({ block: "start" });
      level.querySelector("summary").focus({ preventScroll: true });
    };
    return h(
      "p",
      { class: "provenance-line" },
      FG.icon("sources"),
      h("span", null, basis + (latest ? " · " + FG.t("landing.trustUpdated", { date: FG.formatDate(latest) }) : "") + " · "),
      h("button", { type: "button", class: "button-link", onclick: openDetails }, FG.t("basis.details"))
    );
  }

  function madeContent(items) {
    const sources = sourcesOf(items);
    const actions = actionsOf(items);
    return [
      h("h3", null, FG.t("station.sources")),
      h("ul", null, sources.map((source) => h("li", null, source.url ? FG.external(source.url, FG.text(source.name)) : FG.text(source.name)))),
      h("h3", null, FG.t("station.madeBy")),
      h(
        "ul",
        null,
        actions.map((action) => {
          const agent = FG.get(action.agent);
          const tools = FG.refs(action, "instrument").map((tool) => tool.name).join(", ");
          return h(
            "li",
            null,
            FG.t("station.madeByText", { agent: agent ? agent.name : "", tools, date: FG.formatDate(action.endTime) }),
            " ",
            h("span", { class: "muted small" }, action.name)
          );
        })
      ),
    ];
  }

  function orderedCalloutItems(callout, lens) {
    const items = FG.refs(callout, "hasPart").sort(FG.byPosition).filter((item) => lensOf(item, lens));
    const order = FG.list(callout.lensOrder)
      .map((line) => line.split(":"))
      .find(([key]) => key.trim() === lens);
    if (!order) return items;
    const sequence = order[1].split(",").map((part) => part.trim());
    return items.slice().sort((a, b) => sequence.indexOf(a.identifier) - sequence.indexOf(b.identifier));
  }

  function callouts(station, lens) {
    return FG.refs(station, "hasPart")
      .filter((part) => part["@id"].startsWith("#callout-"))
      .map((callout) =>
        h(
          "aside",
          { class: "callout callout-" + callout.identifier, "aria-label": FG.text(callout.headline) },
          h("h3", null, FG.span(callout.headline)),
          callout.text ? h("p", null, FG.span(callout.text)) : null,
          h(
            "ol",
            null,
            orderedCalloutItems(callout, lens).map((item) =>
              h("li", null, item.url ? FG.external(item.url, FG.text(item.text)) : FG.span(item.text))
            )
          ),
          FG.helpers && FG.helpers.callout ? FG.helpers.callout(callout) : null
        )
      );
  }

  function station(route) {
    const entity = FG.get("#station-" + route.arg) || FG.stations()[0];
    const stations = FG.stations();
    const index = stations.indexOf(entity);
    const items = FG.refs(entity, "itemListElement").filter((item) => lensOf(item, route.lens));
    const level = (code) => items.filter((item) => FG.id(item.disclosureLevel) === "#level-" + code && item.adviceKind !== "ai").sort(FG.byPosition);
    const now = level("L0")[0];
    const steps = level("L1");
    const ai = items.filter((item) => item.adviceKind === "ai");
    const resources = FG.refs(entity, "mentions").filter((item) => item.resourceType && lensOf(item, route.lens));
    const terms = FG.refs(entity, "mentions").filter((item) => item["@id"].startsWith("#term-"));
    const helps = FG.graph.filter((item) => item["@id"].startsWith("#help-") && lensOf(item, route.lens));
    const action = now ? FG.get(now.potentialAction) : null;
    const minutes = String(entity.timeRequired || "").replace(/\D/g, "");
    const levelName = (code) => FG.termName("#level-" + code);
    const levelTitle = (code) => [levelIcon(code), h("span", null, levelName(code))];
    const stationIcon = FG.config.icons && FG.config.icons.station && FG.config.icons.station[entity.identifier];
    const stepLine = FG.t("station.step", { n: entity.position, total: stations.length }) + (minutes ? " · " + FG.t("station.minutes", { n: minutes }) : "");
    return h(
      "article",
      { class: "station" },
      h(
        "header",
        { class: "station-header" },
        FG.icon(stationIcon, { class: "station-icon" }),
        h(
          "div",
          null,
          h("p", { class: "muted" }, stepLine),
          heading(1, null, FG.span(entity.name), " · ", FG.span(entity.headline)),
          principleTiles(FG.refs(entity, "about"), FG.t("station.principles"))
        )
      ),
      now
        ? h(
            "section",
            { class: "now", "aria-label": levelName("L0") },
            h("div", null, h("p", { class: "level" }, levelTitle("L0")), h("p", { class: "now-text" }, FG.span(now.text))),
            action
              ? FG.id(action.target).startsWith("#")
                ? h("a", { class: "button button-primary button-small", href: FG.actionHref(FG.id(action.target)) }, FG.span(action.name))
                : FG.external(FG.id(action.target), [FG.text(action.name), FG.icon("external")], { class: "button button-primary button-small" })
              : null
          )
        : h("p", null, FG.t("station.empty")),
      steps.length ? details(levelTitle("L1"), "L1", h("ol", { class: "steps" }, steps.map(adviceItem))) : null,
      ai.length
        ? details([FG.icon("ai"), h("span", null, FG.t("station.ai"))], "ai", ai.map((item) => h("p", { class: "tip" }, FG.span(item.text))), h("p", null, h("a", { href: FG.href("page", "ai") }, FG.text(FG.get("#page-ai").headline))))
        : null,
      details(levelTitle("L2"), "L2", whyContent(entity, items)),
      details(levelTitle("L3"), "L3", madeContent(items)),
      provenanceLine(items),
      callouts(entity, route.lens),
      resources.length ? h("section", null, h("h2", null, FG.t("station.resources")), h("ul", { class: "cards" }, resources.map(resourceCard))) : null,
      terms.length
        ? h("section", null, h("h2", null, FG.t("station.glossary")), h("ul", { class: "chips" }, terms.map((term) => h("li", null, FG.external(term.url, FG.text(term.name), { class: "chip" })))))
        : null,
      h(
        "section",
        null,
        h("h2", null, FG.t("station.help")),
        h("ul", null, helps.map((help) => h("li", null, help.url.startsWith("mailto:") ? h("a", { href: help.url }, FG.text(help.name)) : FG.external(help.url, FG.text(help.name)))))
      ),
      h(
        "nav",
        { class: "pager", "aria-label": FG.t("nav.stations") },
        index > 0 ? h("a", { class: "button", href: FG.href("path", stations[index - 1].identifier) }, "← " + FG.t("station.previous", { name: FG.text(stations[index - 1].name) })) : h("span"),
        index < stations.length - 1 ? h("a", { class: "button button-primary", href: FG.href("path", stations[index + 1].identifier) }, FG.t("station.next", { name: FG.text(stations[index + 1].name) }) + " →") : null
      )
    );
  }

  FG.views.path = function (route) {
    const showEntry = FG.landingShown(route);
    const currentId = showEntry ? null : route.arg || FG.state.lastStation || FG.state.entryStation || FG.stations()[0].identifier;
    if (currentId && FG.stations().some((station) => station.identifier === currentId) && (currentId !== FG.state.lastStation || FG.state.lastVisit !== FG.today())) {
      FG.state.lastStation = currentId;
      FG.state.lastVisit = FG.today();
      FG.saveState();
    }
    if (showEntry) return landing(route);
    return h("div", { class: "layout layout-path wrap" }, h("div", { class: "path-side" }, rail(route, currentId)), h("div", null, station(Object.assign({}, route, { arg: currentId }))));
  };

  /* ---------------------------------------------------------------- principle explorer */

  FG.views.explorer = function (route) {
    const principles = FG.principles();
    const selected = principles.find((principle) => principle.termCode === route.arg);
    const clauses = selected
      ? FG.graph.filter((entity) => entity.clauseKind && FG.hasRef(entity, "about", selected["@id"]))
      : [];
    const actors = ["#actor-nrp", "#actor-repository", "#actor-fip", "#actor-other"];
    const menu = h(
      "nav",
      { class: "principle-menu", "aria-label": FG.t("explorer.choose") },
      ["F", "A", "I", "R"].map((letter) =>
        h(
          "div",
          { class: "principle-group" },
          h("p", { class: "principle-group-name" }, h("span", { class: "principle-letter", "data-letter": letter }, letter), FG.t("explorer.group." + letter)),
          h(
            "ul",
            null,
            principles
              .filter((principle) => String(principle.termCode).charAt(0) === letter)
              .map((principle) => h("li", null, FG.principleTile(principle, { "aria-current": principle === selected ? "true" : null })))
          )
        )
      )
    );
    return h(
      "div",
      { class: "wrap explorer" },
      heading(1, null, FG.t("explorer.title")),
      h("p", null, FG.t("explorer.intro")),
      h(
        "div",
        { class: "layout layout-explorer" },
        menu,
        selected
          ? h(
              "section",
              { "aria-labelledby": "principle-heading" },
              heading(2, { id: "principle-heading" }, h("span", { class: "principle-letter", "data-letter": String(selected.termCode).charAt(0) }, String(selected.termCode).charAt(0)), String(selected.termCode).slice(1) + " · ", FG.span(selected.name)),
              h("p", { class: "lead" }, FG.span(selected.description)),
              h("p", null, FG.external(FG.DASHBOARD + "resources?principles=" + encodeURIComponent(selected.termCode), FG.t("explorer.dashboard", { p: selected.termCode }))),
              relatedTerms(selected),
              h("p", { class: "muted" }, FG.t("explorer.count", { n: clauses.length })),
              actors.map((actor) => {
                const group = clauses.filter((clause) => FG.hasRef(clause, "audience", actor));
                if (!group.length) return null;
                return h("section", null, h("h3", null, FG.termName(actor)), h("ul", { class: "clauses" }, group.map(clauseItem)));
              })
            )
          : h("p", { class: "muted" }, FG.t("explorer.pick"))
      )
    );
  };

  function relatedTerms(principle) {
    const related = FG.refs(principle, "relatedTo");
    const cts = related.filter((term) => FG.id(term.inDefinedTermSet) === "#coretrustseal");
    const cdif = related.filter((term) => FG.id(term.inDefinedTermSet) === "#cdif");
    return h(
      "div",
      null,
      cts.length ? h("p", null, h("strong", null, FG.t("explorer.cts") + ": "), cts.map((term) => term.termCode).join(", ")) : null,
      cdif.length ? h("p", null, h("strong", null, FG.t("explorer.cdif") + ": "), cdif.map((term) => term.termCode).join(", ")) : null
    );
  }

  function clauseItem(clause) {
    const source = FG.get(clause.isPartOf);
    const status = clause.creativeWorkStatus;
    return h(
      "li",
      null,
      h("span", { class: "clause-id" }, clause.identifier),
      " ",
      FG.span(clause.text),
      source ? h("div", { class: "muted small" }, FG.t("explorer.source") + ": ", source.url ? FG.external(source.url, FG.text(source.name)) : FG.text(source.name)) : null,
      status && status !== "current" && clause.note
        ? h("div", { class: "small" }, h("strong", null, FG.t(status === "superseded" ? "explorer.superseded" : "explorer.refresh") + ": "), FG.span(clause.note))
        : null
    );
  }

  /* ---------------------------------------------------------------- resource finder */

  const filters = { station: "", type: "", status: "", language: "" };

  function select(name, label, options) {
    return h(
      "label",
      null,
      label,
      h(
        "select",
        {
          name,
          onchange: (event) => {
            filters[name] = event.target.value;
            FG.render();
          },
        },
        h("option", { value: "" }, FG.t("finder.all")),
        options.map(([value, text]) => h("option", { value, selected: filters[name] === value }, text))
      )
    );
  }

  FG.views.resources = function (route) {
    if (route.arg && FG.get("#resource-" + route.arg)) filters.station = "";
    const resources = FG.graph.filter((entity) => entity.resourceType && entity["@id"].startsWith("#resource-"));
    const stationOf = new Map();
    for (const station of FG.stations()) for (const id of FG.refIds(station, "mentions")) stationOf.set(id, (stationOf.get(id) || []).concat(station.identifier));
    const shown = resources.filter(
      (resource) =>
        (!filters.station || (stationOf.get(resource["@id"]) || []).includes(filters.station)) &&
        lensOf(resource, route.lens) &&
        (!filters.type || FG.id(resource.resourceType) === filters.type) &&
        (!filters.status || FG.id(resource.serviceStatus) === filters.status) &&
        (!filters.language || FG.list(resource.inLanguage).includes(filters.language))
    );
    const termsOf = (set) => FG.ofType("DefinedTerm").filter((term) => FG.id(term.inDefinedTermSet) === set);
    return h(
      "div",
      { class: "layout wrap" },
      h(
        "section",
        null,
        heading(1, null, FG.t("finder.title")),
        h("p", null, FG.t("finder.intro")),
        h(
          "div",
          { class: "filters" },
          select("station", FG.t("finder.station"), FG.stations().map((station) => [station.identifier, station.position + " · " + FG.text(station.name)])),
          select("type", FG.t("finder.type"), termsOf("#resource-types").map((term) => [term["@id"], FG.text(term.name)])),
          select("status", FG.t("finder.status"), termsOf("#statuses").map((term) => [term["@id"], FG.text(term.name)])),
          select("language", FG.t("finder.language"), [["cs", "čeština / Czech"], ["en", "angličtina / English"]])
        ),
        h("p", { role: "status" }, FG.t("finder.count", { n: shown.length })),
        h("ul", { class: "cards" }, shown.map(resourceCard)),
        catalogue()
      )
    );
  };

  function catalogue() {
    const snapshot = FG.get("#snapshot-fip-dashboard");
    const fers = FG.refs(FG.get("#fers"), "hasPart");
    if (!snapshot || !fers.length) return null;
    return h(
      "section",
      { "aria-labelledby": "fers-heading" },
      h("h2", { id: "fers-heading" }, FG.t("finder.fers")),
      h("p", null, FG.t("finder.fersIntro"), " ", FG.external(FG.DASHBOARD, FG.t("finder.openDashboard")), " · ", FG.external(FG.DASHBOARD + "matrix", FG.t("finder.matrix"))),
      h("p", { class: "muted" }, FG.t("finder.snapshot", { date: FG.formatDate(snapshot.dateCreated) })),
      snapshot.disclaimer ? h("p", { class: "notice" }, h("strong", null, FG.t("finder.disclaimer") + ": "), FG.span(snapshot.disclaimer)) : null,
      h(
        "ul",
        { class: "cards" },
        fers.map((fer) =>
          h(
            "li",
            { class: "card" },
            h("h3", null, FG.external(FG.refIds(fer, "sameAs")[0], fer.name)),
            fer.description ? h("p", null, FG.span(fer.description)) : null,
            h("div", { class: "badges" }, h("span", { class: "badge" }, FG.termName(FG.id(fer.catalogueType))), verificationBadges(fer))
          )
        )
      )
    );
  }

  /* ---------------------------------------------------------------- repositories */

  let repositoryQuery = "";
  let repositoryKind = "";

  /** Add live NKR records: a repository already listed gains NKR as a source; a new one is appended. */
  function withNkr(repositories) {
    const records = FG.live && FG.live.nkr ? FG.live.nkr.records : [];
    const merged = repositories.map((repository) => Object.assign({}, repository, { nkr: false }));
    for (const record of records) {
      const match = merged.find(
        (repository) =>
          (record.re3data && FG.list(repository.identifier).includes(record.re3data)) ||
          (record.url && repository.url && repository.url.replace(/\/$/, "").toLowerCase() === record.url.replace(/\/$/, "").toLowerCase())
      );
      if (match) match.nkr = true;
      else merged.push({ name: record.name, url: record.url, repositoryKind: record.kind, keywords: record.keywords, nkr: true, isBasedOn: [] });
    }
    return merged;
  }

  FG.views.repositories = function () {
    const repositories = withNkr(FG.refs(FG.get("#repositories"), "hasPart"));
    const sourceName = (id) => (id === "#repositories-curated" ? FG.t("repositories.curated") : FG.text((FG.get(id) || {}).name).replace(/^Snapshot of /, ""));
    const matches = (repository) => {
      const haystack = [FG.text(repository.name), ...FG.list(repository.keywords).map((keyword) => (typeof keyword === "string" ? keyword : keyword["@value"]))].join(" ").toLowerCase();
      return (!repositoryQuery || haystack.includes(repositoryQuery.toLowerCase())) && (!repositoryKind || FG.id(repository.repositoryKind) === repositoryKind);
    };
    const shown = repositories
      .filter(matches)
      .sort((a, b) => {
        const order = (repository) => {
          const index = KIND_ORDER.indexOf(FG.id(repository.repositoryKind));
          return index < 0 ? KIND_ORDER.length : index;
        };
        return order(a) - order(b) || FG.text(a.name).localeCompare(FG.text(b.name));
      });
    return h(
      "div",
      { class: "layout wrap" },
      h(
        "section",
        null,
        heading(1, null, FG.t("repositories.title")),
        h("p", null, FG.t("repositories.intro")),
        h(
          "div",
          { class: "filters" },
          h("label", null, FG.t("repositories.search"), h("input", { type: "search", value: repositoryQuery, oninput: (event) => { repositoryQuery = event.target.value; FG.renderList("repository-list", shownRepositories); } })),
          h(
            "label",
            null,
            FG.t("repositories.kind"),
            h(
              "select",
              { onchange: (event) => { repositoryKind = event.target.value; FG.renderList("repository-list", shownRepositories); } },
              h("option", { value: "" }, FG.t("finder.all")),
              KIND_ORDER.map((kind) => h("option", { value: kind, selected: repositoryKind === kind }, FG.termName(kind)))
            )
          ),
          FG.live && FG.live.nkrButton ? FG.live.nkrButton() : null
        ),
        h("div", { id: "repository-list" }, repositoryList(shown, sourceName))
      )
    );

    function shownRepositories() {
      return repositoryList(repositories.filter(matches), sourceName);
    }
  };

  function repositoryList(repositories, sourceName) {
    return h(
      "div",
      null,
      h("p", { role: "status" }, FG.t("finder.count", { n: repositories.length })),
      h(
        "ul",
        { class: "cards" },
        repositories.map((repository) =>
          h(
            "li",
            { class: "card" },
            h("h3", null, FG.external(repository.url, FG.text(repository.name))),
            repository.keywords ? h("p", { class: "small" }, FG.list(repository.keywords).map((keyword) => (typeof keyword === "string" ? keyword : keyword["@value"])).filter((value, index, all) => all.indexOf(value) === index).join(", ")) : null,
            h(
              "div",
              { class: "badges" },
              repository.repositoryKind ? h("span", { class: "badge" }, FG.termName(FG.id(repository.repositoryKind))) : null,
              statusBadge(repository),
              h("span", { class: "badge" }, FG.t("repositories.sources", { sources: FG.refIds(repository, "isBasedOn").map(sourceName).concat(repository.nkr ? ["NKR"] : []).join(", ") }))
            )
          )
        )
      )
    );
  }

  FG.renderList = function (id, build) {
    const container = document.getElementById(id);
    if (container) container.replaceChildren(build());
  };

  /* ---------------------------------------------------------------- pages */

  /** The roles behind the guide, from the guide's metadata. */
  function creditsTable() {
    const who = (entry) => {
      const name = FG.text(entry.name) || String(entry.name);
      return entry.url ? FG.external(entry.url, name) : name;
    };
    return h(
      "table",
      { class: "credits" },
      h("thead", null, h("tr", null, h("th", { scope: "col" }, FG.t("credits.role")), h("th", { scope: "col" }, FG.t("credits.who")))),
      h(
        "tbody",
        null,
        FG.list(FG.config.credits).map((credit) =>
          h(
            "tr",
            null,
            h("th", { scope: "row" }, FG.t("credits." + credit.role, { work: credit.work || "" })),
            h(
              "td",
              null,
              credit.people.map((entry, index) => [index ? ", " : "", who(entry)])
            )
          )
        )
      )
    );
  }

  FG.views.page = function (route) {
    const page = FG.get("#page-" + route.arg) || FG.get("#page-about");
    const sections = FG.refs(page, "hasPart").sort(FG.byPosition);
    return h(
      "div",
      { class: "layout wrap" },
      h(
        "article",
        null,
        heading(1, null, FG.span(page.headline)),
        sections.map((section) =>
          h(
            "section",
            section.identifier ? { id: section.identifier, tabindex: "-1" } : null,
            section.headline ? h("h2", null, FG.span(section.headline)) : null,
            FG.paragraphs(section.text),
            section.identifier === "credits" ? creditsTable() : null
          )
        ),
        FG.helpers && FG.helpers[page.identifier] ? FG.helpers[page.identifier]() : null
      )
    );
  };
})();
