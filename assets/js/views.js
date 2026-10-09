/* Views of the FAIR Data Guide: shell, path, principle explorer, the resource and repository finders (tabs of the
   catalogue, catalogue.js), tools and pages. */
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

  /** The FIP Dashboard snapshot's date and, while it carries one, its disclaimer. */
  FG.dashboardNotice = function () {
    const snapshot = FG.get("#snapshot-fip-dashboard");
    if (!snapshot) return null;
    return [
      h("p", { class: "muted" }, FG.t("finder.snapshot", { date: FG.formatDate(snapshot.dateCreated) })),
      snapshot.disclaimer ? h("p", { class: "notice" }, h("strong", null, FG.t("finder.disclaimer") + ": "), FG.span(snapshot.disclaimer)) : null,
    ];
  };

  FG.verificationBadges = verificationBadges;

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

  /** Orientation tags: the principles an entry serves, as tiles, and the lenses it is for, as icons. */
  function orientationTags(principles, lensIds) {
    const icons = (FG.config.icons && FG.config.icons.lens) || {};
    const lenses = lensIds.map(FG.get).filter(Boolean);
    if (!principles.length && !lenses.length) return null;
    return h(
      "div",
      { class: "orientation" },
      principles.map((principle) => FG.principleTile(principle)),
      lenses.map((lens) => h("span", { class: "lens-tag", title: FG.text(lens.name) }, FG.icon(icons[lens.audienceType]), h("span", { class: "visually-hidden" }, FG.text(lens.name))))
    );
  }

  /** A resource as a card; the catalogue adds its usage marks and where the guide uses it. */
  function resourceCard(resource, extras) {
    const record = dashboardRecord(resource);
    const languages = FG.list(resource.inLanguage);
    return h(
      "li",
      { class: "card", id: "item-" + resource.identifier, tabindex: "-1" },
      h("h3", null, FG.external(resource.url, FG.nameNodes(resource))),
      resource.description ? h("p", null, FG.span(resource.description)) : null,
      orientationTags(record && record.fer ? FG.principlesOf(record.fer) : [], FG.refIds(resource, "audience")),
      h(
        "div",
        { class: "badges" },
        h("span", { class: "badge" }, FG.termName(FG.id(resource.resourceType))),
        statusBadge(resource),
        languages.length ? h("span", { class: "badge" }, FG.t("resource.languages", { languages: languages.join(", ") })) : null,
        record ? verificationBadges(record.fer) : null,
        extras ? extras.badges : null,
        record ? FG.external(record.url, FG.t("resource.dashboard"), { class: "small" }) : null
      ),
      extras ? extras.after : null
    );
  }

  FG.resourceCard = resourceCard;

  /* Persistent identifier schemes, recognised by address, each with the label shown before it. */
  const PID_SCHEMES = [
    [/^https?:\/\/(dx\.)?doi\.org\//, "doi"],
    [/^https?:\/\/hdl\.handle\.net\//, "handle"],
    [/^https?:\/\/(purl\.org|w3id\.org)\/np\//, "nanopub"],
    [/^https?:\/\/ror\.org\//, "ror"],
    [/^https?:\/\/orcid\.org\//, "orcid"],
    [/^https?:\/\/www\.re3data\.org\/repository\//, "re3data"],
    [/^https?:\/\/(n2t\.net\/)?ark:|\/ark:\//, "ark"],
    [/^https?:\/\/(w3id\.org|purl\.org|identifiers\.org)\//, "iri"],
  ];

  /** An entity's persistent identifiers: its own identifier, those it is the same as and its address, when they
      follow a persistent identifier scheme. */
  FG.pids = function (entity) {
    const seen = new Set();
    return [entity["@id"]]
      .concat(FG.refIds(entity, "sameAs"), [entity.url])
      .filter(Boolean)
      .map(String)
      .flatMap((iri) => {
        const scheme = PID_SCHEMES.find(([pattern]) => pattern.test(iri));
        if (!scheme || seen.has(iri)) return [];
        seen.add(iri);
        return [{ iri, scheme: scheme[1] }];
      });
  };

  /* An address that may wrap after each slash, so a narrow screen breaks it between its parts. */
  const breakable = (iri) => iri.split(/(?<=\/)/).flatMap((part, index) => (index ? [h("wbr"), part] : [part]));

  /** A line with an entity's persistent identifiers, each named by its scheme and linked; nothing when it has none. */
  FG.pidLine = function (entity) {
    const pids = FG.pids(entity);
    if (!pids.length) return null;
    return h(
      "p",
      { class: "small pid-line" },
      pids.flatMap((pid, index) => (index ? [" · "] : []).concat([h("span", { class: "pid-scheme" }, FG.t("pid." + pid.scheme)), " ", FG.external(pid.iri, breakable(pid.iri))]))
    );
  };
  FG.statusBadge = statusBadge;
  FG.dashboardRecord = dashboardRecord;

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
          /* The guide's data and its source sit beside the language, so they are found from every view. */
          h(
            "div",
            { class: "header-links" },
            Object.entries(FG.config.pageMenu || {})
              .filter(([, menu]) => menu === "header")
              .map(([id]) =>
                h(
                  "a",
                  { class: "button header-page", href: FG.href("page", id), "aria-current": route.view === "page" && route.arg === id ? "page" : null },
                  FG.icon(((FG.config.icons && FG.config.icons.page) || {})[id]),
                  h("span", null, FG.text((FG.get("#page-" + id) || {}).headline))
                )
              ),
            FG.external(FG.root.url, [FG.icon("repository"), h("span", { class: "visually-hidden" }, FG.t("nav.repository"))], { class: "button button-icon header-repository", title: FG.t("nav.repository") })
          ),
          h("a", { class: "button header-lang", href: FG.href(route.view, route.arg, { lang: otherLang }), lang: otherLang, hreflang: otherLang }, FG.t("nav.switchTo"))
        )
      )
    );
  };

  /* Views whose content the lens changes; the lens band is shown only there. In the catalogue the lens is one of the
     resource filters. */
  const LENS_VIEWS = new Set(["path", "selfcheck"]);
  const lensChanges = (route) => LENS_VIEWS.has(route.view);

  /** The lens switch: four links under the main menu, each shareable, switching in place so roles can be compared
      at the same position; focus stays on the chosen lens. */
  FG.views.lensBand = function (route) {
    if (!lensChanges(route)) return null;
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

  /** The menu item a page sits under: the catalogue, tools or about. */
  const pageMenu = (route) => (route.view === "page" ? (FG.config.pageMenu || {})[route.arg] || "about" : null);

  FG.views.nav = function (route) {
    const first = FG.stations()[0];
    const station = FG.state.lastStation || FG.state.entryStation || (first && first.identifier);
    const landing = FG.landingShown(route);
    const items = [
      ["path", "start", "nav.home", landing],
      ["path", station, "nav.path", route.view === "path" && !landing],
      ["selfcheck", null, "nav.selfcheck", route.view === "selfcheck" || route.view === "check"],
      ["explorer", null, "nav.explorer", route.view === "explorer"],
      ["catalogue", null, "nav.catalogue", route.view === "catalogue" || pageMenu(route) === "catalogue"],
      ["tools", null, "nav.tools", route.view === "tools" || pageMenu(route) === "tools"],
      ["page", "about", "nav.about", pageMenu(route) === "about"],
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
      h("em", null, FG.nameNodes(work)),
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
          h("li", null, h("a", { href: FG.href("page", "about") + "/privacy" }, FG.t("footer.localData"))),
          h("li", null, h("a", { href: FG.href("page", "about") }, FG.t("footer.ai"))),
          h("li", null, FG.external(root.url, FG.t("footer.repository"))),
          h("li", null, h("a", { href: FG.href("page", "machines") }, FG.t("footer.crate")))
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
      /* The funder's published logo set, shown through two windows onto one image: they meet by design. */
      { class: "logolink logolink-" + FG.state.lang, "data-joined": "" },
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
              h("span", null, FG.span(entry.stage.name), h("span", { class: "small muted" }, "\u00a0· " + stepsLabel(entry.from, entry.to)))
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
    return h("li", null, FG.linkedSpan(item), steps.length ? h("ul", null, steps.map((step) => h("li", null, FG.linkedSpan(step)))) : null);
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
    const principles = FG.principlesOf(station);
    const clauses = [];
    for (const item of items) {
      for (const clause of FG.refs(item, "citation")) if (!clauses.includes(clause)) clauses.push(clause);
    }
    return [
      notes.length ? h("ul", null, notes.map((note) => h("li", null, FG.linkedSpan(note)))) : null,
      h("h3", null, FG.t("station.whyPrinciples")),
      principleTiles(principles),
      h("h3", null, FG.t("station.whyClauses")),
      h("ul", { class: "clauses" }, clauses.map(FG.clauseEntry)),
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
      h(
        "span",
        null,
        basis + (latest ? " · " + FG.t("landing.trustUpdated", { date: FG.formatDate(latest) }) : "") + " · ",
        h("button", { type: "button", class: "button-link", onclick: openDetails }, FG.t("basis.details"))
      )
    );
  }

  function madeContent(items, station) {
    const sources = sourcesOf(items);
    const actions = actionsOf(items);
    return [
      h("h3", null, FG.t("station.sources")),
      h("ul", null, sources.map((source) => h("li", null, source.url ? FG.external(source.url, FG.nameNodes(source)) : FG.nameNodes(source)))),
      h("h3", null, FG.t("station.madeBy")),
      h("ul", { class: "change-history" }, changeHistory(actions).map((entry) => h("li", null, FG.t(entry.created ? "station.changeCreate" : "station.changeUpdate", { date: FG.formatDate(entry.date) })))),
      h("p", { class: "small muted" }, FG.t("station.paradata") + " ", h("a", { href: FG.catalogueFilterHref("actions", [station.identifier]) }, FG.t("station.changes"))),
    ];
  }

  /** A simple change history: one line per day and kind of change, newest first; who and with which tools stays in
      the paradata of the knowledge base. */
  function changeHistory(actions) {
    const seen = new Set();
    return actions
      .map((action) => ({ date: String(action.endTime || "").slice(0, 10), created: FG.list(action["@type"]).includes("CreateAction") }))
      .filter((entry) => entry.date)
      .sort((a, b) => b.date.localeCompare(a.date) || Number(a.created) - Number(b.created))
      .filter((entry) => {
        const key = entry.date + entry.created;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
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

  /** A station's callouts, framed so they stand out, and closed until the reader opens them: they matter only to
      some readers, and their question says whether it is theirs. */
  function callouts(station, lens) {
    return FG.refs(station, "hasPart")
      .filter((part) => part["@id"].startsWith("#callout-"))
      .map((callout) =>
        h(
          "aside",
          { class: "callout callout-" + callout.identifier, "aria-label": FG.text(callout.headline) },
          details(
            h("span", null, FG.span(callout.headline)),
            "callout-" + callout.identifier,
            callout.text ? h("p", null, FG.linkedSpan(callout)) : null,
            h(
              "ol",
              null,
              orderedCalloutItems(callout, lens).map((item) =>
                h("li", null, item.url ? FG.external(item.url, FG.text(item.text)) : FG.span(item.text))
              )
            ),
            FG.helpers && FG.helpers.callout ? FG.helpers.callout(callout) : null
          )
        )
      );
  }

  /* Markdown for a station export: text that would start formatting is escaped, list items stay on one line. */
  const mdText = (value) =>
    String(value || "")
      .replace(/([\\`*_[\]<>])/g, "\\$1")
      .replace(/^(#+|[-+]) /gm, "\\$1 ")
      .replace(/^(\d+)\. /gm, "$1\\. ");
  const mdLine = (value) => mdText(FG.text(value).replace(/\s*\n\s*\n\s*/g, " "));
  const mdLink = (text, url) => (url ? "[" + mdText(text) + "](" + String(url).replace(/[ ()]/g, encodeURIComponent) + ")" : mdText(text));
  const guideUrl = (hash) => FG.pageAddress() + hash;

  /** A station as Markdown: what it shows for the reader's lens, in their language, with where it came from. */
  function stationMarkdown(entity, route, parts) {
    const { items, now, steps, ai, action, resources, terms, helps, courses } = parts;
    const levelName = (code) => FG.termName("#level-" + code);
    const lines = ["# " + mdText(FG.text(entity.headline)), ""];
    lines.push(mdText(FG.t("export.mdLens", { lens: FG.text((FG.get("#lens-" + route.lens) || {}).name) })), "");
    const principles = FG.principlesOf(entity);
    if (principles.length) lines.push(mdText(FG.t("station.principles")) + ": " + principles.map((principle) => mdText(principle.termCode + " " + FG.text(principle.name))).join(", "), "");
    const section = (title, body) => {
      if (body.length) lines.push("## " + mdText(title), "", ...body, "");
    };
    const actionUrl = action ? (FG.id(action.target).startsWith("#") ? guideUrl(FG.actionHref(FG.id(action.target))) : FG.id(action.target)) : null;
    section(levelName("L0"), now ? [mdText(FG.text(now.text))].concat(action ? ["", mdLink(FG.text(action.name), actionUrl)] : []) : []);
    section(
      levelName("L1"),
      steps.flatMap((item, index) => [index + 1 + ". " + mdLine(item.text)].concat(FG.refs(item, "hasPart").sort(FG.byPosition).map((step) => "   - " + mdLine(step.text))))
    );
    const notes = items.filter((item) => FG.id(item.disclosureLevel) === "#level-L2" && item.adviceKind !== "ai").sort(FG.byPosition);
    const clauses = [...new Set(items.flatMap((item) => FG.refs(item, "citation")))];
    const clauseLine = (clause) => {
      const source = FG.get(clause.isPartOf);
      return "- " + mdLine(clause.text) + " (" + mdText(clause.identifier) + (source ? ", " + mdLink(FG.nameText(source), source.url) : "") + ")";
    };
    const basis = clauses.length ? ["### " + mdText(FG.t("station.whyClauses")), "", ...clauses.map(clauseLine)] : [];
    section(levelName("L2"), notes.map((note) => "- " + mdLine(note.text)).concat(notes.length && basis.length ? [""] : [], basis));
    /* An AI tip, what to check after it, and its prompt as a code block under the same list item. */
    const aiLines = (item) =>
      ["- " + mdLine(item.text)]
        .concat(item.checkAfter ? ["", "  " + mdText(FG.t("station.aiCheck")) + ": " + mdLine(item.checkAfter)] : [])
        .concat(item.promptSample ? ["", "  ```text", ...FG.text(item.promptSample).split("\n").map((line) => (line ? "  " + line : "")), "  ```"] : []);
    section(FG.t("station.ai"), ai.flatMap((item, index) => (index ? [""] : []).concat(aiLines(item))).concat(ai.length ? ["", mdText(FG.t("station.aiReminder"))] : []));
    for (const callout of FG.refs(entity, "hasPart").filter((part) => part["@id"].startsWith("#callout-"))) {
      section(
        FG.text(callout.headline),
        (callout.text ? [mdText(FG.text(callout.text)), ""] : []).concat(orderedCalloutItems(callout, route.lens).map((item, index) => index + 1 + ". " + (item.url ? mdLink(FG.text(item.text), item.url) : mdLine(item.text))))
      );
    }
    section(FG.t("station.glossary"), terms.map((term) => "- " + mdLink(FG.text(term.name), term.url)));
    section(FG.t("station.resources"), resources.map((resource) => "- " + mdLink(FG.text(resource.name), resource.url) + (resource.description ? " — " + mdLine(resource.description) : "")));
    section(
      FG.t("station.help"),
      helps.map((help) => "- " + mdLink(FG.text(help.name), help.url)).concat(courses.length ? ["- " + mdText(FG.t("station.training")) + ": " + courses.map((course) => mdLink(FG.text(course.name), course.url)).join(", ")] : [])
    );
    section(FG.t("station.sources"), sourcesOf(items).map((source) => "- " + mdLink(FG.nameText(source), source.url)));
    lines.push("---", "", mdText(FG.t("export.mdFooter", { version: FG.root.version, date: FG.formatDate(FG.today()) })) + " " + guideUrl(FG.href("path", entity.identifier)), "");
    return lines.join("\n");
  }

  /** An action as a button: a place in the guide, or an address outside it that opens in a new tab. */
  function actionButton(action) {
    const target = FG.id(action.target);
    return target.startsWith("#")
      ? h("a", { class: "button button-primary button-small", href: FG.actionHref(target) }, FG.span(action.name))
      : FG.external(target, [FG.text(action.name), FG.icon("external")], { class: "button button-primary button-small" });
  }

  /** An AI tip: the tip, what to check afterwards, and a short prompt to copy; where tips of every view are shown
      together, a tip for one view carries its icon. */
  function aiTip(item, showLens) {
    const promptId = "prompt-" + item.identifier.replace(/\W/g, "-");
    const lenses = FG.refIds(item, "audience");
    return h(
      "div",
      { class: "tip ai-tip" },
      showLens === true && lenses.length < FG.lenses().length ? orientationTags([], lenses) : null,
      h("p", null, FG.linkedSpan(item)),
      item.checkAfter ? h("p", null, h("strong", null, FG.t("station.aiCheck") + ": "), FG.linkedSpan(item, "checkAfter")) : null,
      item.promptSample
        ? h(
            "div",
            { class: "ai-prompt" },
            h(
              "div",
              { class: "ai-prompt-head" },
              h("span", { class: "small muted" }, FG.t(FG.text(item.promptSample).includes("[…]") ? "station.aiPromptFill" : "station.aiPrompt")),
              h(
                "button",
                { type: "button", class: "button button-small", onclick: (event) => FG.copyText(event, FG.text(item.promptSample), promptId) },
                FG.icon("copy"),
                h("span", { class: "copy-label" }, FG.t("common.copy"))
              )
            ),
            h("pre", { id: promptId, tabindex: "0", lang: FG.textOf(item.promptSample, FG.state.lang).lang || null }, FG.text(item.promptSample))
          )
        : null
    );
  }

  /** Every station's AI tips for every view, under the station they belong to: what the path offers, gathered on
      the AI page. */
  function aiStationTips() {
    const icons = (FG.config.icons && FG.config.icons.station) || {};
    return h(
      "div",
      { class: "ai-station-tips" },
      FG.stations().map((station) => {
        const tips = FG.refs(station, "itemListElement").filter((item) => item.adviceKind === "ai").sort(FG.byPosition);
        if (!tips.length) return null;
        return h(
          "section",
          { "aria-labelledby": "ai-tips-" + station.identifier },
          h("h3", { id: "ai-tips-" + station.identifier }, h("a", { class: "holder-link", href: FG.href("path", station.identifier) }, FG.icon(icons[station.identifier]), station.position + " · ", FG.span(station.name))),
          tips.map((item) => aiTip(item, true))
        );
      })
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
    const ai = items.filter((item) => item.adviceKind === "ai").sort(FG.byPosition);
    const mentioned = FG.refs(entity, "mentions").filter((item) => item.resourceType && lensOf(item, route.lens));
    const courses = mentioned.filter((item) => FG.id(item.resourceType) === "#rtype-course");
    const resources = mentioned.filter((item) => !courses.includes(item));
    const terms = FG.refs(entity, "mentions").filter((item) => item["@id"].startsWith("#term-"));
    const helps = FG.graph.filter((item) => item["@id"].startsWith("#help-") && lensOf(item, route.lens));
    const action = now ? FG.get(now.potentialAction) : null;
    const minutes = String(entity.timeRequired || "").replace(/\D/g, "");
    const levelName = (code) => FG.termName("#level-" + code);
    const levelTitle = (code) => [levelIcon(code), h("span", null, levelName(code))];
    const stationIcon = FG.config.icons && FG.config.icons.station && FG.config.icons.station[entity.identifier];
    const stepLine = FG.t("station.step", { n: entity.position, total: stations.length }) + (minutes ? " · " + FG.t("station.minutes", { n: minutes }) : "");
    const parts = { items, now, steps, ai, action, resources, terms, helps, courses };
    FG.offerExport({
      id: "markdown",
      label: FG.t("export.markdown"),
      run: () => FG.download(FG.exportName(["station", entity.identifier, route.lens, FG.state.lang], "md"), stationMarkdown(entity, route, parts), "text/markdown"),
    });
    FG.offerRecord(entity);
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
          /* The step's short name is in the path beside it; the heading is its title alone. */
          heading(1, null, FG.span(entity.headline)),
          principleTiles(FG.principlesOf(entity), FG.t("station.principles"))
        )
      ),
      now
        ? h(
            "section",
            { class: "now", "aria-label": levelName("L0") },
            h("div", null, h("p", { class: "level" }, levelTitle("L0")), h("p", { class: "now-text" }, FG.linkedSpan(now))),
            action ? actionButton(action) : null
          )
        : h("p", null, FG.t("station.empty")),
      steps.length ? details(levelTitle("L1"), "L1", h("ol", { class: "steps" }, steps.map(adviceItem))) : null,
      details(levelTitle("L2"), "L2", whyContent(entity, items)),
      ai.length
        ? details(
            [FG.icon("ai"), h("span", null, FG.t("station.ai"))],
            "ai",
            ai.map((item) => aiTip(item)),
            h("p", { class: "small muted" }, FG.t("station.aiReminder")),
            h("p", null, h("a", { href: FG.href("page", "ai") }, FG.text(FG.get("#page-ai").headline)))
          )
        : null,
      details(levelTitle("L3"), "L3", madeContent(items, entity)),
      provenanceLine(items),
      terms.length
        ? h(
            "section",
            { class: "station-terms" },
            h("h2", null, FG.t("station.glossary")),
            h("ul", { class: "chips" }, terms.map((term) => h("li", null, FG.external(term.url, FG.text(term.name), { class: "chip" }))))
          )
        : null,
      callouts(entity, route.lens),
      resources.length ? h("section", null, h("h2", null, FG.t("station.resources")), h("ul", { class: "cards" }, resources.map(resourceCard))) : null,
      h(
        "section",
        null,
        h("h2", null, FG.t("station.help")),
        h(
          "ul",
          null,
          helps.map((help) => h("li", null, help.url.startsWith("mailto:") ? h("a", { href: help.url }, FG.text(help.name)) : FG.external(help.url, FG.text(help.name)))),
          courses.length
            ? h("li", { class: "training" }, FG.t("station.training") + ": ", courses.map((course, index) => [index ? ", " : "", FG.external(course.url, FG.text(course.name).replace(/^[^:]+:\s*/, ""))]))
            : null
        )
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
    if (selected) FG.offerRecord(selected);
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
                return h("section", null, h("h3", null, FG.termName(actor)), h("ul", { class: "clauses" }, group.map(FG.clauseEntry)));
              })
            )
          : explorerOverview(principles, actors)
      )
    );
  };

  /** Before a principle is chosen: how many requirements each FAIR group holds, by whom they address. */
  function explorerOverview(principles, actors) {
    const clauses = FG.graph.filter((entity) => entity.clauseKind);
    const ofGroup = (letter) => {
      const ids = new Set(principles.filter((principle) => String(principle.termCode).charAt(0) === letter).map((principle) => principle["@id"]));
      return clauses.filter((clause) => FG.refs(clause, "about").some((term) => ids.has(term["@id"])));
    };
    const counted = new Set();
    const rows = ["F", "A", "I", "R"].map((letter) => {
      const group = ofGroup(letter);
      group.forEach((clause) => counted.add(clause));
      return h(
        "tr",
        null,
        h("th", { scope: "row" }, h("span", { class: "principle-letter", "data-letter": letter }, letter), h("span", { class: "group-name" }, FG.t("explorer.group." + letter))),
        actors.map((actor) => h("td", null, String(group.filter((clause) => FG.hasRef(clause, "audience", actor)).length))),
        h("td", null, String(group.length))
      );
    });
    return h(
      "section",
      null,
      h("p", { class: "muted" }, FG.t("explorer.pick")),
      h(
        "table",
        { class: "explorer-overview" },
        h("caption", null, FG.t("explorer.overview", { n: counted.size })),
        h("thead", null, h("tr", null, h("th", { scope: "col" }, FG.t("explorer.principle")), actors.map((actor) => h("th", { scope: "col" }, FG.termName(actor))), h("th", { scope: "col" }, FG.t("explorer.all")))),
        h("tbody", null, rows)
      ),
      h("p", { class: "small muted" }, FG.t("explorer.overviewNote"))
    );
  }

  function relatedTerms(principle) {
    const related = FG.refs(principle, "relatedTo");
    const cts = related.filter((entity) => String(entity["@id"]).startsWith("#clause-CTS."));
    const cdif = related.filter((term) => FG.id(term.inDefinedTermSet) === "#cdif");
    /* A CoreTrustSeal requirement by its number and title, leading to its record in the catalogue. */
    const requirement = (clause) => h("a", { href: FG.catalogueHref("clauses", clause.identifier) }, clause.identifier.replace(/^CTS\./, "") + " ", FG.span(clause.name));
    return h(
      "div",
      null,
      cts.length
        ? [
            h("p", null, h("strong", null, FG.t("explorer.cts") + ": "), cts.flatMap((clause, index) => (index ? [", ", requirement(clause)] : [requirement(clause)]))),
            h("p", { class: "small muted" }, FG.t("explorer.ctsNote")),
          ]
        : null,
      cdif.length ? h("p", null, h("strong", null, FG.t("explorer.cdif") + ": "), cdif.map((term) => term.termCode).join(", ")) : null
    );
  }

  /* ---------------------------------------------------------------- the finders' building blocks */

  /** A FAIR-enabling resource of the FIP Dashboard snapshot as a card; the catalogue adds its marks. */
  FG.ferCard = function (fer, extras) {
    return h(
      "li",
      { class: "card", id: "item-fer-" + fer.identifier, tabindex: "-1" },
      h("h3", null, FG.external(FG.refIds(fer, "sameAs")[0] || fer.url, fer.name)),
      fer.description ? h("p", null, FG.span(fer.description)) : null,
      orientationTags(FG.principlesOf(fer), []),
      h("div", { class: "badges" }, h("span", { class: "badge" }, FG.termName(FG.id(fer.catalogueType))), verificationBadges(fer), extras ? extras.badges : null),
      extras ? extras.after : null
    );
  };

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
      if (match) match.nkr = record;
      else merged.push({ name: record.name, url: record.url, identifier: record.re3data ? [record.re3data] : [], repositoryKind: record.kind, keywords: record.keywords, nkr: record, isBasedOn: [] });
    }
    return merged;
  }

  /** Add the FAIRsharing record found for each repository, once the user loaded them. */
  function withFairsharing(repositories) {
    if (!FG.live || !FG.live.fairsharing) return repositories;
    return repositories.map((repository) => Object.assign(repository, { fairsharing: FG.live.fairsharingOf({ identifiers: repository.identifier, url: repository.url }) }));
  }

  /** Every repository: the curated list, the snapshots and, once loaded, NKR records and FAIRsharing links. */
  FG.repositoryEntries = () => withFairsharing(withNkr(FG.refs(FG.get("#repositories"), "hasPart")));
  FG.repositoryKindOrder = KIND_ORDER;

  /** The name of a source a repository record comes from. */
  FG.repositorySource = (id) => (id === "#repositories-curated" ? FG.t("repositories.curated") : FG.text((FG.get(id) || {}).name).replace(/^Snapshot of /, ""));

  /** A repository's subjects in the reader's language, or as the record gives them when it has none in it. */
  function subjectsOf(repository) {
    const words = FG.list(repository.keywords);
    const mine = words.filter((word) => typeof word === "string" || !word["@language"] || word["@language"] === FG.state.lang);
    return (mine.length ? mine : words).map((word) => (typeof word === "string" ? word : word["@value"])).filter((value, index, all) => all.indexOf(value) === index);
  }

  /** A repository as a card, with its kind, status, the sources of its facts and its FAIRsharing record. */
  /** The records a repository's facts came from, each linked where the record has an address of its own: re3data
      and FIP Dashboard snapshots, NKR and FAIRsharing; the guide's own selection is named. */
  function repositorySources(repository) {
    const r3d = FG.refIds(repository, "sameAs").find((id) => /re3data\.org/.test(id));
    const sources = FG.refIds(repository, "isBasedOn").map((id) => {
      const name = FG.repositorySource(id);
      return id === "#snapshot-re3data" && r3d ? FG.external(r3d, name) : name;
    });
    if (repository.nkr) sources.push(repository.nkr.id ? FG.external(FG.config.links.nkr + "objects/" + repository.nkr.id, "NKR") : "NKR");
    if (repository.fairsharing) sources.push(FG.external(FG.live.pidUrl({ type: "doi", value: repository.fairsharing.doi }), "FAIRsharing", { class: "fairsharing-record" }));
    return sources.flatMap((source, index) => (index ? [", ", source] : [source]));
  }

  FG.repositoryCard = function (repository, id) {
    return h(
      "li",
      { class: "card", id: id || null, tabindex: id ? "-1" : null },
      h("h3", null, FG.external(repository.url, FG.text(repository.name))),
      repository.keywords ? h("p", { class: "small" }, subjectsOf(repository).join(", ")) : null,
      h(
        "div",
        { class: "badges" },
        repository.repositoryKind ? h("span", { class: "badge" }, FG.termName(FG.id(repository.repositoryKind))) : null,
        statusBadge(repository),
        h("span", { class: "badge badge-sources" }, FG.t("repositories.sourcesLabel") + ": ", repositorySources(repository)),
        FG.apiLink ? FG.apiLink(repository) : null
      ),
      FG.pidLine(repository)
    );
  };

  /* re3data facts a sample NKR record shows, in the order of a record. */
  const SAMPLE_FIELDS = ["pidTypes", "apis", "dataLicenses", "metadataStandards", "certificates", "policies", "versioning", "qualityManagement"];

  /** Sample NKR records: a few real Czech repositories with only the values their public re3data records state,
      the richest records first, labelled as samples and not NKR records. */
  FG.nkrSamples = function () {
    const facts = (FG.config && FG.config.re3data) || {};
    const stated = (value) => (Array.isArray(value) ? value.length > 0 : value !== undefined && value !== null);
    const chosen = Object.entries(facts)
      .map(([r3d, record]) => ({ r3d, record, repository: FG.get("#repository-" + r3d) }))
      .filter((entry) => entry.repository)
      .sort((a, b) => SAMPLE_FIELDS.filter((key) => stated(b.record[key])).length - SAMPLE_FIELDS.filter((key) => stated(a.record[key])).length || a.r3d.localeCompare(b.r3d))
      .slice(0, 3);
    if (!chosen.length) return null;
    const value = (key, fact) => {
      if (!stated(fact)) return h("span", { class: "muted" }, FG.t("repositories.sample.none"));
      if (typeof fact === "boolean") return FG.t(fact ? "repositories.sample.yes" : "repositories.sample.no");
      return FG.list(fact).join(", ");
    };
    const field = (key, content) => [h("dt", null, FG.t("repositories.sample." + key)), h("dd", null, content)];
    return h(
      "section",
      { class: "nkr-samples", "aria-labelledby": "nkr-samples-title" },
      h("h3", { id: "nkr-samples-title" }, FG.t("repositories.nkrSamplesTitle")),
      h("p", { class: "notice small" }, FG.t("repositories.nkrSamplesNote", { date: FG.formatDate(chosen[0].record.date) })),
      h(
        "ul",
        { class: "cards" },
        chosen.map(({ r3d, record, repository }) =>
          h(
            "li",
            { class: "card nkr-sample" },
            h("p", { class: "badge sample-label" }, FG.t("repositories.sample.label")),
            h("h4", null, FG.external(repository.url, record.name)),
            h(
              "dl",
              { class: "sample-fields" },
              field("kind", repository.repositoryKind ? FG.termName(FG.id(repository.repositoryKind)) : value("kind")),
              field("subjects", subjectsOf(repository).join(", ") || value("subjects")),
              SAMPLE_FIELDS.map((key) => field(key, value(key, record[key]))),
              field("registry", FG.external(FG.config.links.re3dataRecord + r3d, FG.t("repositories.sample.record")))
            )
          )
        )
      )
    );
  };

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
            h("th", { scope: "row" }, FG.t("credits." + credit.role, { work: FG.text(credit.work) })),
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
            FG.linkedParagraphs(section),
            section.potentialAction ? h("p", { class: "section-action" }, actionButton(FG.get(section.potentialAction))) : null,
            page.identifier === "ai" && section.identifier === "station-tips" ? aiStationTips() : null,
            section.identifier === "credits" ? creditsTable() : null,
            page.identifier === "machines" && section.identifier === "tasks" ? machineTasks() : null,
            page.identifier === "machines" && section.identifier === "practice" ? signpostTable() : null,
            page.identifier === "machines" && section.identifier === "endpoints" ? endpointTable() : null,
            section.identifier === "privacy" && FG.selfcheck && FG.selfcheck.localDataNote ? FG.selfcheck.localDataNote() : null
          )
        ),
        FG.helpers && FG.helpers[page.identifier] ? FG.helpers[page.identifier]() : helperComing(page) ? h("p", { class: "notice helper-coming" }, FG.t("page.helperComing")) : null
      )
    );
  };

  /** What a reader may want from the knowledge base and where it is: each row leads to the guide's own data. */
  function machineTasks() {
    const files = FG.config.api.files;
    const link = (href, label, type) => h("a", { href, type: type || null }, label || href);
    const example = "principles/R1.1";
    const rows = [
      ["crate", [link("ro-crate-metadata.json", null, "application/ld+json")]],
      ["record", [h("code", null, files.record.replace("{record}", "<kolekce>/<id>")), " · ", FG.t("machines.example") + ": ", link(files.record.replace("{record}", example), null, "application/json")]],
      ["service", [link(files.description, null, "application/vnd.oai.openapi+json"), " · ", link(files.docs, FG.t("api.docs"), "text/html")]],
      ["harvest", [link("linkset.json", null, "application/linkset+json"), " · ", h("a", { href: "#signposts" }, FG.t("machines.headLinks"))]],
      ["result", [link(FG.href("selfcheck"), FG.t("nav.selfcheck"))]],
      ["list", [link(FG.href("catalogue"), FG.t("nav.catalogue"))]],
    ];
    return h(
      "table",
      { class: "data-table machine-tasks" },
      h("caption", { class: "visually-hidden" }, FG.t("machines.tasksCaption")),
      h("thead", null, h("tr", null, ["want", "use", "what"].map((key) => h("th", { scope: "col" }, FG.t("machines.column." + key))))),
      h(
        "tbody",
        null,
        rows.map(([key, use]) => h("tr", null, h("th", { scope: "row" }, FG.t("machines.task." + key + ".want")), h("td", null, use), h("td", null, FG.t("machines.task." + key + ".what"))))
      )
    );
  }

  /** The guide's own signposts, read from the same list as the page head and the linkset. */
  function signpostTable() {
    const target = (href) => (/^[a-z]+:/i.test(href) ? FG.external(href, href) : h("a", { href }, href));
    return h(
      "table",
      { class: "data-table signposts", id: "signposts" },
      h("caption", null, FG.t("machines.signpostsCaption")),
      h("thead", null, h("tr", null, ["rel", "target", "meaning"].map((key) => h("th", { scope: "col" }, FG.t("machines.column." + key))))),
      h(
        "tbody",
        null,
        FG.list(FG.config.signposts).map((link) => h("tr", null, h("th", { scope: "row" }, h("code", null, link.rel)), h("td", null, target(link.href)), h("td", null, FG.t("machines.rel." + (link.rel === "type" ? "type_" + link.href.split("/").pop() : link.rel.replace("-", "_"))))))
      )
    );
  }

  /** Every endpoint of the API, the accessible counterpart of its interactive documentation. */
  function endpointTable() {
    const files = FG.config.api.files;
    const file = (path, type) => h("a", { href: path, type }, path);
    return h(
      "table",
      { class: "data-table endpoints" },
      h("caption", { class: "visually-hidden" }, FG.t("api.endpoints")),
      h("thead", null, h("tr", null, ["collection", "list", "record"].map((key) => h("th", { scope: "col" }, FG.t("machines.column." + key))))),
      h(
        "tbody",
        null,
        FG.config.api.collections.map((name) =>
          h(
            "tr",
            null,
            h("th", { scope: "row" }, FG.t("api.collection." + name + ".name"), h("span", { class: "small muted endpoint-description" }, FG.t("api.collection." + name + ".description"))),
            h("td", null, file(files.record.replace("{record}", name), "application/json")),
            h("td", null, h("code", null, files.record.replace("{record}", name + "/<id>")))
          )
        ),
        [["meta", files.meta, "application/json"], ["context", files.context, "application/ld+json"]].map(([key, path, type]) =>
          h("tr", null, h("th", { scope: "row" }, FG.t("api." + key)), h("td", null, file(path, type)), h("td", null, ""))
        )
      )
    );
  }

  /** Whether a page holds a helper that the page script does not provide yet. */
  function helperComing(page) {
    return FG.list(page.additionalType).includes(FG.config.vocab.webApplication) && !(FG.helpers && FG.helpers[page.identifier]);
  }

  /** The tools: the helpers for single tasks on the path and the advice on AI, each as a card. */
  FG.views.tools = function () {
    const pages = Object.entries(FG.config.pageMenu || {})
      .filter(([, menu]) => menu === "tools")
      .map(([id]) => FG.get("#page-" + id))
      .filter(Boolean);
    return h(
      "div",
      { class: "layout wrap tools" },
      h(
        "article",
        null,
        heading(1, null, FG.t("tools.title")),
        h("p", { class: "lead" }, FG.t("tools.intro")),
        h(
          "ul",
          { class: "tool-cards" },
          pages.map((page) =>
            h(
              "li",
              { class: "tool-card" },
              FG.icon((FG.config.icons.page || {})[page.identifier], { class: "tool-card-icon" }),
              h(
                "div",
                null,
                h("h2", null, h("a", { href: FG.href("page", page.identifier) }, FG.span(page.headline))),
                page.description ? h("p", null, FG.span(page.description)) : null,
                helperComing(page) ? h("p", { class: "badge tool-coming" }, FG.t("tools.coming")) : null
              )
            )
          )
        )
      )
    );
  };
})();
