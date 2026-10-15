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

  function statusBadge(entity, asOfKey = "status.asOf") {
    const statusId = FG.id(entity.serviceStatus);
    if (!statusId) return null;
    const code = statusId.replace("#status-", "");
    const asOf = entity.statusAsOf;
    return h(
      "span",
      { class: "badge", "data-status": code },
      h("span", { "aria-hidden": "true" }, STATUS_ICON[code] || "•"),
      FG.termName(statusId),
      asOf ? h("span", { class: "muted" }, " · " + FG.t(asOfKey, { date: FG.formatDate(asOf) })) : null,
      isStale(asOf) ? h("span", null, " · " + FG.t("status.stale")) : null
    );
  }

  /** The FIP Dashboard record of a resource, if the guide links one, with its verifications. */
  function dashboardRecord(entity) {
    const url = FG.refIds(entity, "sameAs").find((id) => id.startsWith(FG.DASHBOARD + "resources/"));
    if (!url) return null;
    const fer = FG.sourceEntity("fip-dashboard", url.split("/").pop(), "#fer-");
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
    const levels = { verified: "verified", "self-declared": "selfDeclaredBy", "under-review": "underReviewBy" };
    return FG.refs(fer, "review").filter((review) => levels[review.reviewAspect]).map((review) => {
      const author = FG.get(review.author) || {};
      const name = FG.text(author.alternateName || author.name);
      return h("span", { class: "badge", "data-verification": review.reviewAspect },
        review.reviewAspect === "verified" ? h("span", { "aria-hidden": "true" }, "✓") : null,
        FG.t("resource." + levels[review.reviewAspect], { verifiers: name }),
        review.dateCreated ? h("span", { class: "muted" }, " · " + FG.formatDate(review.dateCreated)) : null);
    });
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
      lenses.map((lens) => h("span", { class: "lens-tag" }, FG.icon(icons[lens.audienceType]), h("span", null, FG.text(lens.name))))
    );
  }

  /* Persistent identifier schemes, recognised by address, each with the label shown before it. */
  const RE3DATA_DOI = /^https?:\/\/(dx\.)?doi\.org\/10\.17616\//i;
  const PID_SCHEMES = [
    [/^https?:\/\/(dx\.)?doi\.org\/10\.25504\/FAIRsharing\./i, "fairsharing"],
    [/^https:\/\/repo\.cz\/objects\//, "nkr"],
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
        /* A re3data record's DOI names the record the re3data address already shows, not the repository. */
        if (!scheme || seen.has(iri) || RE3DATA_DOI.test(iri)) return [];
        seen.add(iri);
        return [{ iri, scheme: scheme[1] }];
      });
  };

  /* An address that may wrap after each slash, so a narrow screen breaks it between its parts. */
  const breakable = (iri) => iri.split(/(?<=\/)/).flatMap((part, index) => (index ? [h("wbr"), part] : [part]));

  /** An entity's persistent identifiers, each named by its scheme and linked in full; none when it has none. */
  FG.pidItems = (entity) => FG.pids(entity).map((pid) => FG.pidItem(pid.scheme, pid.iri));

  /** One identifier or record address as a chip, as the guide shows every identifier (D-185): its scheme named, the
      identifier in full, leading to it. */
  FG.pidItem = (scheme, iri) => FG.external(iri, [h("span", { class: "pid-scheme" }, FG.t("pid." + scheme)), " ", breakable(iri)], { class: "id-chip pid-chip" });

  /** The object a check is about as a chip: its DOI or Handle, or its address. */
  FG.targetChip = (target) => {
    const pid = FG.live && FG.live.parsePid(target);
    if (pid && (pid.type === "doi" || pid.type === "handle")) return FG.pidItem(pid.type, FG.live.pidUrl(pid));
    return /^https?:\/\//.test(String(target || "")) ? FG.external(target, breakable(target), { class: "id-chip pid-chip" }) : h("span", { class: "id-chip id-chip-static" }, String(target || ""));
  };
  FG.statusBadge = statusBadge;

  /** An entry's membership of the EOSC CZ Node as one badge: the node, what the entry is in it as the node's charter
      says (a node service, a repository whose integration is planned by a stated milestone, an incubator service),
      the date checked and the charter it comes from. The badge claims no more than the charter (D-172). */
  FG.nodeBadge = function (entity) {
    const membership = FG.get(FG.id(entity && entity.nodeMembership));
    if (!membership) return null;
    const role = FG.id(membership.roleName).replace("#noderole-", "");
    const source = FG.refs(membership, "citation")[0];
    const what = role === "repository" && membership.nodeMilestone ? FG.t("node.repository", { milestone: membership.nodeMilestone }) : FG.t("node." + role);
    return h(
      "span",
      { class: "badge node-badge", "data-node": role },
      h("span", { "aria-hidden": "true" }, "◆"),
      "EOSC CZ Node · " + what,
      membership.statusAsOf ? h("span", { class: "muted" }, " · " + FG.t("node.checked", { date: FG.formatDate(membership.statusAsOf) })) : null,
      source && (source.url || String(source["@id"]).startsWith("https://")) ? [" · ", FG.external(source.url || source["@id"], FG.t("node.source"))] : null
    );
  };
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
    return route.view === "path" && (route.arg === "start" || (!route.arg && !FG.state.lastStation));
  };

  const phoneMenu = window.matchMedia("(max-width: 39.99rem)");
  phoneMenu.addEventListener("change", (event) => {
    document.querySelectorAll("details.responsive-menu").forEach((menu) => { menu.open = !event.matches; });
  });

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
                  { class: "button header-page", "aria-label": FG.text((FG.get("#page-" + id) || {}).headline), href: FG.href("page", id), "aria-current": route.view === "page" && route.arg === id ? "page" : null },
                  FG.icon(((FG.config.icons && FG.config.icons.page) || {})[id]),
                  h("span", null, FG.text((FG.get("#page-" + id) || {}).headline))
                )
              ),
            FG.external(FG.root.url, [FG.icon("repository"), h("span", { class: "visually-hidden" }, FG.t("nav.repository"))], { class: "button button-icon header-repository", title: FG.t("nav.repository") })
          ),
          h("a", { class: "button header-lang", href: FG.routeHref(route, { lang: otherLang }), lang: otherLang, hreflang: otherLang }, FG.t("nav.switchTo"))
        )
      )
    );
  };

  /* Views whose content the lens changes; the lens band is shown only there. In the catalogue the lens is one of the
     resource filters. */
  /* The role changes the path's steps and a check's questions and help, so those views offer it. */
  const LENS_VIEWS = new Set(["path", "selfcheck", "check"]);
  const lensChanges = (route) => LENS_VIEWS.has(route.view);

  /** The lens switch: four links under the main menu, each shareable, switching in place so roles can be compared
      at the same position; focus stays on the chosen lens. */
  FG.views.lensBand = function (route) {
    if (!lensChanges(route)) return null;
    const icons = (FG.config.icons && FG.config.icons.lens) || {};
    const arg = FG.landingShown(route) ? "start" : route.arg;
    const option = (lens) => {
      /* A check keeps its part, so roles can be compared on the same questions or report. */
      const href = route.view === "check" ? FG.routeHref(route, { lens: lens.audienceType }) : FG.href(route.view, arg, { lens: lens.audienceType });
      const switchInPlace = (event) => {
        if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        FG.navigateInPlace(href, phoneMenu.matches ? ".role-menu > summary" : `.lens-option[data-lens="${lens.audienceType}"]`);
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
      h("div", { class: "wrap" }, h("span", { class: "lens-band-label", "aria-hidden": "true" }, FG.t("nav.lens")),
        h("details", { class: "responsive-menu role-menu", open: !phoneMenu.matches },
          h("summary", null, FG.t("nav.lens") + ": ", FG.text(FG.lenses().find((lens) => lens.audienceType === route.lens)?.name)),
          h("ul", null, FG.lenses().map(option))))
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
    const station = FG.state.lastStation || (first && first.identifier);
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
      h("details", { class: "responsive-menu navigation-menu", open: !phoneMenu.matches },
        h("summary", null, FG.t("nav.menu") + ": ", FG.t(items.find((item) => item[3])?.[2] || "nav.home")),
        h("ul", null, items.map(([view, arg, key, current]) => h("li", null,
          h("a", { href: FG.href(view, arg), "aria-current": current ? "page" : null }, FG.t(key))))))
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
          h("li", null, h("a", { href: FG.href("page", "machines") }, FG.t("footer.crate"))),
          h("li", null, h("a", { href: "health/index.html", hreflang: "en" }, FG.t("footer.health")))
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

  /** The path's life-cycle stages in their order, each with the steps it holds (`lifecycleStage`). Every step belongs
      to a stage; the stage a reader is in is derived from the step and never chosen. */
  FG.journeyStages = function () {
    const stations = FG.stations();
    const first = stations.map((station) => FG.get(FG.id(station.lifecycleStage))).find(Boolean);
    const set = first && FG.id(first.inDefinedTermSet);
    return FG.graph
      .filter((entity) => set && FG.id(entity.inDefinedTermSet) === set)
      .sort(FG.byPosition)
      .map((stage) => ({ stage, steps: stations.filter((station) => FG.id(station.lifecycleStage) === stage["@id"]) }));
  };

  /** The stage of the step a visitor last read; none before any step was read. */
  const lastStage = () => {
    const station = FG.stations().find((item) => item.identifier === FG.state.lastStation);
    return station ? FG.id(station.lifecycleStage) : null;
  };

  /* Each stage has its colour (`--stage-<n>` in tokens.css), the same on the ring, in the list and on the rail. */
  const stageClass = (index) => "stage-" + (index + 1);
  const stationIcon = (station) => ((FG.config.icons && FG.config.icons.station) || {})[station.identifier];

  /* A step's read mark is the reader's own, not a record of visits: this control sets it and takes it off again,
     and every step carries one, so the mark is optional rather than automatic (D-190). */
  const readToggle = (stationId) => {
    const read = FG.list(FG.state.readStations).includes(stationId);
    return h(
      "button",
      { type: "button", class: "read-toggle", "data-read": stationId, "data-state": read ? "read" : "unread",
        "aria-pressed": read ? "true" : "false", title: FG.t(read ? "journey.readOff" : "journey.readOn"),
        onclick: () => FG.toggleReadStation(stationId) },
      h("span", { class: "read-toggle-glyph", "aria-hidden": "true" }, read ? "✓" : "○"),
      h("span", { class: "visually-hidden" }, FG.t("journey.read"))
    );
  };

  /** A stage's steps, one per line, each with its icon and the reader's own read mark. */
  const stepLinks = (steps) =>
    h("ul", { class: "journey-steps" }, steps.map((station) => h("li", { class: "journey-step" },
      h("a", { href: FG.href("path", station.identifier) }, FG.icon(stationIcon(station)), FG.span(station.name)),
      readToggle(station.identifier))));

  function rail(route, currentId) {
    const current = FG.stations().find((station) => station.identifier === currentId);
    const hidden = FG.state.hideCheckBadges ? " rail-hide-checks" : "";
    return [
      h("nav", { class: "rail rail-desktop" + hidden, "aria-label": FG.t("nav.stations") }, railControls("desktop"), railList(currentId), railLegend()),
      h(
        "details",
        { class: "rail rail-mobile" + hidden },
        h("summary", null, FG.t("nav.stations"), current ? ": " + current.position + " · " + FG.text(current.name) : ""),
        h("nav", { "aria-label": FG.t("nav.stations") }, railControls("mobile"), railList(currentId), railLegend())
      ),
    ];
  }

  /** Hide check marks without changing answers, navigation or the open mobile menu. */
  function railControls(where) {
    return h("label", { class: "rail-checks-toggle" },
      h("input", { type: "checkbox", id: "rail-show-checks-" + where, checked: !FG.state.hideCheckBadges || null,
        onchange: (event) => {
          FG.state.hideCheckBadges = !event.target.checked;
          FG.saveState();
          for (const menu of document.querySelectorAll(".rail")) menu.classList.toggle("rail-hide-checks", FG.state.hideCheckBadges);
          for (const toggle of document.querySelectorAll(".rail-checks-toggle input")) toggle.checked = !FG.state.hideCheckBadges;
        } }),
      h("span", null, FG.t("rail.showChecks")));
  }

  /* The self-check's open answers, in the order the self-check reports them, and their counts at a step. */
  const RAIL_STATES = ["gap", "partly", "unknown"];
  const openAt = (stationId) => (FG.openAt ? FG.openAt(stationId) : { gap: 0, partly: 0, unknown: 0 });
  /** A mark for one state, in the self-check's icon and colour, with a count when there is one. */
  const railMark = (state, count) => h("span", { class: "rail-mark", "data-state": state, "aria-hidden": "true" }, FG.STATE_ICON[state] + (count ? " " + count : ""));

  /** The steps under their numbered life-cycle stages; the stage of the step being read is marked as the current one. */
  function railList(currentId) {
    const current = FG.id((FG.stations().find((station) => station.identifier === currentId) || {}).lifecycleStage);
    const step = (station) => {
      const counts = openAt(station.identifier);
      const shown = RAIL_STATES.filter((state) => counts[state]);
      return h(
        "li",
        { class: "rail-step" },
        h(
          "a",
          { href: FG.href("path", station.identifier), "aria-current": station.identifier === currentId ? "step" : null },
          FG.icon(stationIcon(station)) || h("span"),
          FG.span(station.name),
          shown.length
            ? h("span", { class: "rail-marks" }, shown.map((state) => railMark(state, counts[state])),
              h("span", { class: "visually-hidden" }, " " + FG.t("rail.marksHere", { list: shown.map((state) => FG.t("selfcheck.state." + state) + " " + counts[state]).join(", ") })))
            : null
        ),
        readToggle(station.identifier)
      );
    };
    return h(
      "ol",
      { class: "rail-stages" },
      FG.journeyStages().map(({ stage, steps }, index) => {
        const isCurrent = stage["@id"] === current;
        return h(
          "li",
          { class: ["rail-stage", stageClass(index), isCurrent ? "current-stage" : null].filter(Boolean).join(" ") },
          h(
            "span",
            { class: "rail-stage-name" },
            h("span", { class: "rail-stage-number", "aria-hidden": "true" }, String(index + 1)),
            FG.span(stage.name),
            isCurrent ? h("span", { class: "visually-hidden" }, " (" + FG.t("journey.currentStage") + ")") : null
          ),
          h("ol", null, steps.map(step))
        );
      })
    );
  }

  /** What the rail shows, always below it: a stage in its colour, the step being read, and the marks the self-check
      leaves at the steps where its open questions are put right, in the self-check's own icons and colours. */
  function railLegend() {
    const open = FG.stations().some((station) => RAIL_STATES.some((state) => openAt(station.identifier)[state]));
    return h(
      "div",
      { class: "rail-legend" },
      h("p", { class: "rail-legend-title" }, FG.t("rail.legend")),
      h(
        "ul",
        null,
        h("li", null, h("span", { class: "rail-stage-number stage-1", "aria-hidden": "true" }, "1"), h("span", null, FG.t("rail.legendStage"))),
        h("li", null, h("span", { class: "legend-current", "aria-hidden": "true" }), h("span", null, FG.t("rail.legendCurrent"))),
        h("li", null, h("span", { class: "badge read-mark", "aria-hidden": "true" }, "✓"), h("span", null, FG.t("journey.read"))),
        RAIL_STATES.map((state) => h("li", null, railMark(state), h("span", null, FG.t("rail.legendState", { state: FG.t("selfcheck.state." + state) }))))
      ),
      h("p", { class: "rail-legend-note" }, FG.t("rail.legendCount"), " ", h("a", { href: FG.href("selfcheck") }, FG.t(open ? "rail.legendOpen" : "rail.legendNone")))
    );
  }

  function resumeLine() {
    const station = FG.stations().find((item) => item.identifier === FG.state.lastStation);
    if (!station) return null;
    return h(
      "p",
      { class: "resume" },
      h("a", { href: FG.href("path", station.identifier) }, FG.t("journey.resume", { n: station.position, station: FG.text(station.name) }))
    );
  }

  /* The ring: the stages as arrow segments in a closed circle, reuse leading back to planning. */
  /* SVG elements take their namespace from the page's icon sprite, as the icons do. */
  const svg = (tag, attrs, ...children) => {
    const node = document.createElementNS(document.querySelector("svg.sprite").namespaceURI, tag);
    for (const [name, value] of Object.entries(attrs || {})) if (value != null) node.setAttribute(name, value);
    node.append(...children.flat().filter(Boolean));
    return node;
  };

  /** A name on one or two lines, split where the two lines are most even. */
  function lines(text) {
    const words = text.split(" ");
    if (text.length <= 13 || words.length < 2) return [text];
    const difference = (cut) => Math.abs(words.slice(0, cut).join(" ").length - words.slice(cut).join(" ").length);
    let best = 1;
    for (let cut = 2; cut < words.length; cut += 1) if (difference(cut) < difference(best)) best = cut;
    return [words.slice(0, best).join(" "), words.slice(best).join(" ")];
  }

  /** The life cycle drawn as a ring. It repeats the list beside it, so assistive technology skips it; a click on a
      stage opens its first step, as the list's link does. */
  function ring(stages, last) {
    const cx = 390, cy = 282, radius = 174, band = 62, tip = 8, lift = 9, grow = 0, leading = 25;
    const span = 360 / stages.length;
    const outer = radius + band / 2, inner = radius - band / 2;
    const at = (r, degrees) => {
      const angle = (degrees * Math.PI) / 180;
      return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)].map((value) => Number(value.toFixed(1)));
    };
    const segments = stages.map(({ stage, steps }, index) => {
      const from = -90 - span / 2 + index * span;
      const to = from + span;
      const isLast = stage["@id"] === last;
      /* Each segment is an arrow: its head reaches into the next, its tail takes the previous one's head. The stage
         read last is deeper and stands out of the ring towards the reader. */
      const out = outer + (isLast ? grow : 0);
      const mid = (out + inner) / 2;
      const d = "M " + at(out, from) + " A " + out + " " + out + " 0 0 1 " + at(out, to) + " L " + at(mid, to + tip) +
        " L " + at(inner, to) + " A " + inner + " " + inner + " 0 0 0 " + at(inner, from) + " L " + at(mid, from + tip) + " Z";
      const middle = (from + to + tip) / 2;
      const [nx, ny] = at(mid, middle);
      const [lx, ly] = at(out + 16 + (isLast ? lift : 0), middle);
      const cos = Math.cos((middle * Math.PI) / 180);
      const sin = Math.sin((middle * Math.PI) / 180);
      const label = lines(FG.text(stage.name)).concat(isLast ? [FG.t("journey.lastShort")] : []);
      const height = (label.length - 1) * leading;
      const top = sin < -0.6 ? ly - height - 4 : sin > 0.6 ? ly + 16 : ly - height / 2 + 6;
      const anchor = cos > 0.25 ? "start" : cos < -0.25 ? "end" : "middle";
      /* The stage read last stands out of the ring towards the reader. */
      const shift = isLast ? at(lift, middle).map((value, axis) => (value - (axis ? cy : cx)).toFixed(1)) : null;
      const group = svg(
        "g",
        {
          class: ["ring-stage", stageClass(index), isLast ? "ring-last" : null].filter(Boolean).join(" "),
          "data-stage": stage.termCode,
          "data-next": stages[(index + 1) % stages.length].stage.termCode,
          /* Where the segment's copy grows from when it is pointed at: its own middle, so it covers the segment. */
          "data-origin": `${nx}px ${ny}px`,
        },
        /* The segment carries its stage's colour itself, so a copy drawn above the ring keeps it. */
        svg("g", { class: "ring-segment " + stageClass(index), id: "ring-segment-" + index, transform: shift ? `translate(${shift[0]} ${shift[1]})` : null },
          svg("path", { d }),
          svg("path", { d, class: "ring-sheen", fill: "url(#ring-sheen)" }),
          svg("text", { class: "ring-number", x: nx, y: ny, "text-anchor": "middle", "dominant-baseline": "central" }, String(index + 1))),
        label.map((line, number) =>
          svg("text", { class: isLast && number === label.length - 1 ? "ring-note" : "ring-label", x: lx, y: (top + number * leading).toFixed(1), "text-anchor": anchor }, line))
      );
      group.addEventListener("click", () => FG.navigate(FG.href("path", steps[0].identifier)));
      group.addEventListener("mouseenter", () => highlight(stage.termCode, true));
      group.addEventListener("mouseleave", () => highlight(stage.termCode, false));
      return group;
    });
    /* Copies of the stage read last and of the stage pointed at, drawn above both their neighbours; the pointer
       passes through them to the segment they copy. */
    const lastIndex = stages.findIndex(({ stage }) => stage["@id"] === last);
    const above = [
      lastIndex >= 0 ? svg("use", { class: "ring-top ring-top-last", href: "#ring-segment-" + lastIndex }) : null,
      svg("use", { class: "ring-top ring-top-hover", id: "ring-top-hover" }),
    ];
    const title = lines(FG.t("journey.title"));
    /* Light on the outer edge of the band, none on the inner: the ring reads as one turning band. */
    const sheen = svg("radialGradient", { id: "ring-sheen", gradientUnits: "userSpaceOnUse", cx, cy, r: outer },
      svg("stop", { offset: (inner / outer).toFixed(3), "stop-color": "#ffffff", "stop-opacity": "0" }),
      svg("stop", { offset: "1", "stop-color": "#ffffff", "stop-opacity": "0.24" }));
    const shadow = svg("filter", { id: "ring-lift", x: "-30%", y: "-30%", width: "160%", height: "160%" },
      svg("feDropShadow", { dx: "0", dy: "3", stdDeviation: "4", "flood-color": "#1d2a30", "flood-opacity": "0.35" }));
    /* A segment under the pointer, or whose stage has focus in the list, pops out of the ring. */
    const pop = svg("filter", { id: "ring-pop", x: "-30%", y: "-30%", width: "160%", height: "160%" },
      svg("feDropShadow", { dx: "0", dy: "5", stdDeviation: "7", "flood-color": "#1d2a30", "flood-opacity": "0.5" }));
    const drawing = svg(
      "svg",
      { viewBox: "0 0 780 566", "aria-hidden": "true", focusable: "false", class: "ring" },
      svg("defs", null, sheen, shadow, pop),
      svg("circle", { class: "ring-disc", cx, cy, r: inner - 14 }),
      svg("use", { class: "ring-cycle", href: "#i-" + ((FG.config.icons && FG.config.icons.ui && FG.config.icons.ui.lifecycle) || "arrows-spin"), x: cx - 17, y: cy - 78, width: 34, height: 34 }),
      segments,
      title.map((line, number) => svg("text", { class: "ring-center", x: cx, y: cy - 4 + (number - (title.length - 1) / 2) * 23, "text-anchor": "middle" }, line)),
      svg("text", { class: "ring-basis", x: cx, y: cy + 20 + title.length * 11, "text-anchor": "middle" }, FG.t("journey.basis")),
      above
    );
    /* The drawing is cut to what it shows, with room for a segment that grows out of the ring and its shadow, so it
       fills its column without empty margins; it is cut again once the names' font has loaded, and on a phone, where
       the names are hidden, the ring alone fills the width. */
    const fit = () => {
      if (!drawing.isConnected) return;
      const box = drawing.getBBox();
      const pad = 20;
      if (box.width && box.height) drawing.setAttribute("viewBox", [box.x - pad, box.y - pad, box.width + 2 * pad, box.height + 2 * pad].map((value) => value.toFixed(1)).join(" "));
    };
    const figure = h("figure", { class: "journey-ring" }, drawing);
    requestAnimationFrame(fit);
    if (document.fonts) document.fonts.ready.then(fit);
    /* When the ring's column narrows or widens, its names may hide or show again, so the drawing is cut anew. */
    if (window.ResizeObserver) {
      let width = 0;
      const observer = new ResizeObserver(([entry]) => {
        const next = Math.round(entry.contentRect.width);
        if (next === width) return;
        width = next;
        if (!figure.isConnected) observer.disconnect();
        else fit();
      });
      observer.observe(figure);
    }
    return figure;
  }

  /** The journey's introduction, with RDMkit linked to the page that publishes its life cycle. */
  function journeyIntro() {
    const model = FG.get("#lifecycle-rdmkit");
    const [before, after] = FG.t("journey.intro").split("{rdmkit}");
    if (after === undefined) return before;
    return [before, model && model.url ? FG.external(model.url, "RDMkit") : "RDMkit", after];
  }

  /** Mark a stage as pointed at in the ring or focused in the list beside it: its segment pops out above the ring
      and its name is underlined. */
  const highlight = (code, on) => {
    const group = document.querySelector(`.journey-ring .ring-stage[data-stage="${CSS.escape(code)}"]`);
    const copy = document.getElementById("ring-top-hover");
    if (!group || !copy) return;
    group.classList.toggle("ring-hover", on);
    if (on) {
      copy.setAttribute("href", "#" + group.querySelector(".ring-segment").id);
      copy.style.transformOrigin = group.dataset.origin;
    }
    else if (copy.getAttribute("href") === "#" + group.querySelector(".ring-segment").id) copy.removeAttribute("href");
  };

  /** The life cycle on the path's start: the ring and, beside it, the same stages as an ordered list. Each stage opens
      its first step and names its steps; the stage last read is marked in words and by its frame in both. */
  function journey() {
    const stages = FG.journeyStages();
    const last = lastStage();
    return h(
      "section",
      { class: "journey", "aria-labelledby": "journey-title" },
      h("h2", { id: "journey-title" }, FG.t("journey.title")),
      h("p", { class: "muted" }, journeyIntro()),
      h(
        "div",
        { class: "journey-body" },
        ring(stages, last),
        h(
          "ol",
          { class: "journey-stages" },
          stages.map(({ stage, steps }, index) =>
            h(
              "li",
              {
                class: [stageClass(index), stage["@id"] === last ? "journey-last" : null].filter(Boolean).join(" "),
                "data-stage": stage.termCode,
                /* Pointing at a stage in the list, or moving focus into it, shows it in the ring too. */
                onmouseenter: () => highlight(stage.termCode, true),
                onmouseleave: () => highlight(stage.termCode, false),
                onfocusin: () => highlight(stage.termCode, true),
                onfocusout: () => highlight(stage.termCode, false),
              },
              /* The stage on the left, centred beside its steps, which are listed on the right. */
              h(
                "div",
                { class: "journey-stage-head" },
                h(
                  "a",
                  { class: "journey-stage", href: FG.href("path", steps[0].identifier) },
                  h("span", { class: "journey-number", "aria-hidden": "true" }, String(index + 1)),
                  h("strong", null, FG.span(stage.name))
                ),
                stage["@id"] === last ? h("span", { class: "badge" }, FG.t("journey.lastRead")) : null
              ),
              stepLinks(steps)
            )
          )
        )
      )
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

  /** The landing view, which is the path's start: search, the life-cycle journey, tasks, resume line, routes to help. */
  function landing(route) {
    const tasks = FG.list(FG.config.tasks).filter((task) => task.lens === route.lens);
    const steward = FG.get("#help-data-steward");
    return h(
      "div",
      { class: "landing wrap" },
      heading(1, null, FG.t("app.title")),
      h("p", { class: "lead" }, FG.t("app.tagline")),
      FG.search ? FG.search.form() : null,
      journey(),
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

  /** A station's core idea, set apart at the top of the station. */
  function keyPoint(item) {
    return item ? h("aside", { class: "key-point" }, h("p", { class: "key-point-label" }, FG.icon("keyPoint"), FG.t("station.keyPoint")), h("p", null, FG.linkedSpan(item))) : null;
  }

  function adviceItem(item) {
    const steps = FG.refs(item, "hasPart").sort(FG.byPosition);
    return h("li", null, FG.linkedSpan(item), steps.length ? h("ul", null, steps.map((step) => h("li", null, FG.linkedSpan(step)))) : null);
  }

  /** A disclosure level whose open state survives a lens switch while the page stays open; a summary given as
      [title, note] also says, after its title, what the level holds. */
  function details(summaryParts, key, ...content) {
    const [summary, note] = Array.isArray(summaryParts) && summaryParts.length === 2 && typeof summaryParts[1] === "string" ? summaryParts : [summaryParts, null];
    return h(
      "details",
      {
        "data-key": key,
        open: FG.openLevels.has(key),
        ontoggle: (event) => (event.target.open ? FG.openLevels.add(key) : FG.openLevels.delete(key)),
      },
      h("summary", null, summary, note ? h("span", { class: "summary-note small muted" }, note) : null),
      h("div", { class: "content" }, ...content)
    );
  }

  function whyContent(station, items) {
    const notes = items.filter((item) => FG.id(item.disclosureLevel) === "#level-L2" && item.adviceKind !== "ai").sort(FG.byPosition);
    const clauses = [];
    for (const item of items) {
      for (const clause of FG.refs(item, "citation")) if (!clauses.includes(clause)) clauses.push(clause);
    }
    /* At findability and citation the dataset's publication hand-over reads as one chain; elsewhere a context's own
       seams show who passes what to whom. The identifier, page, metadata and files are told apart at publication. */
    const chain = ["findability", "citation"].includes(station.identifier);
    return [
      station.identifier === "publication" ? FG.flow("object") : null,
      FG.modelContexts(station, FG.state.lens).map((context) => h("div", { class: "model-context" }, FG.paragraphs(context.text),
        chain ? FG.publicationFlow() : FG.seamFlow(FG.refs(context, "implementationSeams")),
        h("dl", { class: "relations small" }, FG.modelRows(context)))),
      notes.map(whyNote),
      /* The station's principles show in its header; the reasons go straight to what the advice rests on, which the
         section's title already names. */
      h("ul", { class: "clauses", role: "list" }, clauses.map(FG.clauseEntry)),
    ];
  }

  /** An authored explanation as prose. One that names a service not yet in full operation is a status note, set
      apart with its icon, so advice that rests on a pilot or a plan says so where it is read. */
  function whyNote(note) {
    const named = FG.list(((FG.config && FG.config.textLinks) || {})[note["@id"]]).map((link) => FG.get(link.ref)).filter(Boolean);
    const status = named.some((entity) => FG.id(entity.serviceStatus) && FG.id(entity.serviceStatus) !== "#status-operational");
    return h("p", { class: status ? "why-note status-note" : "why-note" }, status ? FG.icon("info") : null, FG.linkedSpan(note));
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
    const { items, now, key, steps, ai, actions, resources, terms, helps, courses } = parts;
    const levelName = (code) => FG.termName("#level-" + code);
    const lines = ["# " + mdText(FG.text(entity.headline)), ""];
    lines.push(mdText(FG.t("export.mdLens", { lens: FG.text((FG.get("#lens-" + route.lens) || {}).name) })), "");
    const principles = FG.principlesOf(entity);
    if (principles.length) lines.push(mdText(FG.t("station.principles")) + ": " + principles.map((principle) => mdText(principle.termCode + " " + FG.text(principle.name))).join(", "), "");
    const section = (title, body) => {
      if (body.length) lines.push("## " + mdText(title), "", ...body, "");
    };
    const actionUrl = (action) => (FG.id(action.target).startsWith("#") ? guideUrl(FG.actionHref(FG.id(action.target))) : FG.id(action.target));
    if (key) lines.push("> **" + mdText(FG.t("station.keyPoint")) + ":** " + mdLine(key.text), "");
    section(levelName("L0"), now ? [mdText(FG.text(now.text))].concat(actions.length ? [""].concat(actions.map((action) => "- " + mdLink(FG.text(action.name), actionUrl(action)))) : []) : []);
    section(FG.t("station.glossary"), terms.map((term) => "- " + mdLink(FG.text(term.name), term.url)));
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
    const modelContext = FG.modelContexts(entity, route.lens).flatMap((context) => [mdLine(context.text), "",
      ...["implementationLayers", "implementationSeams"].flatMap((property) => FG.refs(context, property).map((term) => "- " + mdLink(FG.text(term.name), guideUrl(FG.entryHref(term))))), ""]);
    section(levelName("L2"), modelContext.concat(notes.flatMap((note, index) => (index ? ["", mdLine(note.text)] : [mdLine(note.text)])), notes.length && basis.length ? [""] : [], basis));
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
    section(FG.t("station.sources"), sourcesOf(items).map((source) => "- " + mdLink(FG.nameText(source), source.url)));
    section(FG.t("station.resources"), resources.map((resource) => "- " + mdLink(FG.text(resource.name), resource.url) + (resource.description ? " — " + mdLine(resource.description) : "")));
    section(
      FG.t("station.help"),
      helps.map((help) => "- " + mdLink(FG.text(help.name), help.url)).concat(courses.length ? ["- " + mdText(FG.t("station.training")) + ": " + courses.map((course) => mdLink(FG.text(course.name), course.url)).join(", ")] : [])
    );
    lines.push("---", "", mdText(FG.t("export.mdFooter", { version: FG.root.version, date: FG.formatDate(FG.today()) })) + " " + guideUrl(FG.href("path", entity.identifier)), "");
    return lines.join("\n");
  }

  /** An action as a button: a place in the guide, or an address outside it that opens in a new tab; a related tool
      beside the next step is a quieter button. */
  function actionButton(action, related) {
    const target = FG.id(action.target);
    const classes = "button button-small" + (related ? " button-related" : " button-primary");
    return target.startsWith("#")
      ? h("a", { class: classes, href: FG.actionHref(target) }, FG.span(action.name))
      : FG.external(target, [FG.text(action.name), FG.icon("external")], { class: classes });
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
    /* The station's core idea opens its how-to, above the steps. */
    const key = level("L1").find((item) => item.adviceKind === "key");
    const steps = level("L1").filter((item) => item !== key);
    const ai = items.filter((item) => item.adviceKind === "ai").sort(FG.byPosition);
    const mentioned = FG.refs(entity, "mentions").filter((item) => item.resourceType && lensOf(item, route.lens));
    const courses = mentioned.filter((item) => FG.id(item.resourceType) === "#rtype-course");
    const resources = mentioned.filter((item) => !courses.includes(item));
    const terms = FG.refs(entity, "mentions").filter((item) => item["@id"].startsWith("#term-"));
    const helps = FG.graph.filter((item) => item["@id"].startsWith("#help-") && lensOf(item, route.lens));
    /* The next step, and at most one related tool beside it. */
    const actions = now ? FG.refs(now, "potentialAction") : [];
    const minutes = String(entity.timeRequired || "").replace(/\D/g, "");
    const levelName = (code) => FG.termName("#level-" + code);
    const levelTitle = (code) => [levelIcon(code), h("span", null, levelName(code))];
    const stationIcon = FG.config.icons && FG.config.icons.station && FG.config.icons.station[entity.identifier];
    const stages = FG.journeyStages();
    const stageAt = stages.findIndex((entry) => entry.stage["@id"] === FG.id(entity.lifecycleStage));
    const stage = stages[stageAt];
    const stepLine = [
      stage ? FG.t("station.stage", { n: stageAt + 1, name: FG.text(stage.stage.name) }) : null,
      stage && stage.steps.length > 1 ? FG.t("station.stageStep", { i: stage.steps.indexOf(entity) + 1, n: stage.steps.length }) : null,
      minutes ? FG.t("station.minutes", { n: minutes }) : null,
    ].filter(Boolean).join(" · ");
    const parts = { items, now, key, steps, ai, actions, resources, terms, helps, courses };
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
      keyPoint(key),
      now
        ? h(
            "section",
            { class: "now", "aria-label": levelName("L0") },
            h("div", null, h("p", { class: "level" }, levelTitle("L0")), h("p", { class: "now-text" }, FG.linkedSpan(now))),
            actions.length ? h("div", { class: "now-actions" }, actions.map((action, index) => actionButton(action, index > 0))) : null
          )
        : h("p", null, FG.t("station.empty")),
      terms.length
        ? h(
            "section",
            { class: "station-terms", "aria-labelledby": "station-terms-title" },
            h("h2", { id: "station-terms-title", class: "inline-heading" }, FG.t("station.glossary")),
            h("ul", { class: "chips" }, terms.map((term) => h("li", null, h("a", { class: "chip", href: FG.catalogueHref("terms", FG.termAnchor(term)) }, FG.text(term.name)))))
          )
        : null,
      steps.length ? details([levelTitle("L1"), FG.t("station.stepsCount", { n: steps.length })], "L1", h("ol", { class: "steps" }, steps.map(adviceItem))) : null,
      details([levelTitle("L2"), FG.t("station.whyNote")], "L2", whyContent(entity, items)),
      ai.length
        ? details(
            [FG.icon("ai"), h("span", null, FG.t("station.ai"))],
            "ai",
            ai.map((item) => aiTip(item)),
            h("p", { class: "small muted" }, FG.t("station.aiReminder")),
            h("p", null, h("a", { href: FG.href("page", "ai") }, FG.text(FG.get("#page-ai").headline)))
          )
        : null,
      callouts(entity, route.lens),
      details(levelTitle("L3"), "L3", madeContent(items, entity)),
      provenanceLine(items),
      resources.length
        ? h("section", { class: "station-resources" }, h("h2", null, FG.t("station.resources")), h("ul", { class: "cards cards-compact" }, resources.map((resource) => FG.resourceCard(resource, entity.identifier, true))))
        : null,
      h(
        "section",
        { class: "station-help" },
        h("h2", null, FG.t("station.help")),
        h(
          "p",
          null,
          FG.icon("help"),
          " ",
          helps.map((help, index) => [index ? " · " : null, help.url.startsWith("mailto:") ? h("a", { href: help.url }, FG.text(help.name)) : FG.external(help.url, FG.text(help.name))])
        ),
        courses.length
          ? h("p", { class: "training" }, FG.icon("training"), " " + FG.t("station.training") + ": ", courses.map((course, index) => [index ? ", " : "", FG.external(course.url, FG.text(course.name).replace(/^[^:]+:\s*/, ""))]))
          : null
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
    const currentId = showEntry ? null : route.arg || FG.state.lastStation || FG.stations()[0].identifier;
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
              { class: "principle-detail", "aria-labelledby": "principle-heading" },
              heading(2, { id: "principle-heading" }, h("span", { class: "principle-letter", "data-letter": String(selected.termCode).charAt(0) }, String(selected.termCode).charAt(0)), String(selected.termCode).slice(1) + " · ", FG.span(selected.name)),
              h("p", { class: "lead" }, FG.span(selected.description)),
              relatedTerms(selected),
              h("p", { class: "muted" }, FG.t("explorer.count", { n: clauses.length })),
              actors.map((actor) => {
                const group = clauses.filter((clause) => FG.hasRef(clause, "audience", actor));
                if (!group.length) return null;
                return h("section", { class: "principle-requirements" }, h("h3", null, FG.termName(actor)), h("ul", { class: "clauses", role: "list" }, group.map(FG.clauseEntry)));
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
    const cdif = related.filter((entity) => String(entity["@id"]).startsWith("#clause-CDIF."));
    /* A CoreTrustSeal requirement by its number and title, leading to its record in the catalogue. */
    const requirement = (clause) => h("a", { href: FG.entryHref(clause) }, clause.identifier.replace(/^CTS\./, "") + " ", FG.span(clause.name));
    const profile = (clause) => h("a", { href: FG.entryHref(clause) }, FG.span(clause.name));
    const row = (label, items, note) => [h("dt", null, label), h("dd", null, items, note ? h("span", { class: "relation-note small muted" }, note) : null)];
    /* The principle's relations in the rows the catalogue uses: what the FIP Dashboard records for it and the
       standards' requirements it links. */
    return h(
      "dl",
      { class: "relations principle-relations" },
      row(FG.t("explorer.dashboardLabel"), FG.external(FG.DASHBOARD + "resources?principles=" + encodeURIComponent(principle.termCode), FG.t("explorer.dashboard", { p: principle.termCode }))),
      cts.length ? row(FG.t("explorer.cts"), cts.map(requirement), FG.t("explorer.ctsNote")) : null,
      cdif.length ? row(FG.t("explorer.cdif"), cdif.map(profile), FG.t("explorer.cdifNote")) : null
    );
  }

  /* ---------------------------------------------------------------- the finders' building blocks */


  /** The FAIRsharing record of a listed repository, by its re3data record, as the FAIRsharing snapshot names it. */
  FG.fairsharingRecord = (r3d) => {
    const repository = FG.repositoryEntries().find((entry) => FG.list(entry.identifier).includes(r3d) || FG.refIds(entry, "sameAs").some((iri) => iri.endsWith("/repository/" + r3d)));
    return (repository && FG.refIds(repository, "sameAs").find((iri) => /\/10\.25504\/FAIRsharing\./i.test(iri))) || null;
  };

  /** Every repository: the curated list and the snapshots, NKR's and FAIRsharing's included, joined at build time. */
  FG.repositoryEntries = () => FG.refs(FG.get("#repositories"), "hasPart");
  FG.repositoryKindOrder = KIND_ORDER;

  /** The name of a source a repository record comes from. */
  FG.repositorySource = (id) => (id === "#repositories-curated" ? FG.t("repositories.curated") : FG.text((FG.get(id) || {}).name).replace(/^Snapshot of /, ""));

  /** A repository's subjects in the reader's language, or as the record gives them when it has none in it. */
  function subjectsOf(repository) {
    const words = FG.list(repository.keywords);
    const mine = words.filter((word) => typeof word === "string" || !word["@language"] || word["@language"] === FG.state.lang);
    return (mine.length ? mine : words).map((word) => (typeof word === "string" ? word : word["@value"])).filter((value, index, all) => all.indexOf(value) === index);
  }

  /** The sources a repository's facts came from, each leading to the source's own entry in the catalogue; the
      guide's own selection is named. The repository's record in each source is among its identifiers (D-185). */
  function repositorySources(repository) {
    return FG.refIds(repository, "isBasedOn").map((id) => {
      const source = FG.get(FG.id((FG.get(id) || {}).about));
      return source ? h("a", { href: FG.entryHref(source) }, FG.repositorySource(id)) : h("span", null, FG.repositorySource(id));
    });
  }

  FG.repositorySourceLinks = repositorySources;
  FG.subjectsOf = subjectsOf;

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
      { class: "layout wrap" + (page.identifier === "model" ? " page-model" : "") },
      h(
        "article",
        null,
        heading(1, null, FG.span(page.headline)),
        page.identifier === "model" ? modelOverview() : null,
        sections.map((section) => {
          const folded = (FG.config.foldedSections || []).includes(section["@id"]);
          const content = [
            FG.linkedParagraphs(section),
            section.potentialAction ? h("p", { class: "section-action" }, actionButton(FG.get(section.potentialAction))) : null,
            page.identifier === "ai" && section.identifier === "station-tips" ? aiStationTips() : null,
            section.identifier === "credits" ? creditsTable() : null,
            page.identifier === "machines" && section.identifier === "tasks" ? machineTasks() : null,
            page.identifier === "machines" && section.identifier === "practice" ? signpostTable() : null,
            page.identifier === "machines" && section.identifier === "endpoints" ? endpointTable() : null,
            page.identifier === "machines" && section.identifier === "model-example" ? modelWorkedExample() : null,
            page.identifier === "model" && section.identifier === "national-mapping" ? modelFigure("czech-ndi-layers", FG.text(section.headline)) : null,
            page.identifier === "model" && section.identifier === "metadata-architecture" ? [modelFigure("metadata-architecture", FG.text(section.headline)), FG.publicationFlow()] : null,
            page.identifier === "software" && section.identifier === "preserve" ? FG.flow("software") : null,
            section.identifier === "privacy" && FG.selfcheck && FG.selfcheck.localDataNote ? FG.selfcheck.localDataNote() : null,
          ];
          return h(
            folded ? "details" : "section",
            section.identifier ? { id: section.identifier, tabindex: "-1" } : null,
            section.headline ? h(folded ? "summary" : "h2", null, FG.span(section.headline)) : null,
            folded ? h("div", { class: "content" }, content) : content
          );
        }),
        page.identifier === "about" ? h("p", { class: "small" }, h("a", { href: FG.href("page", "model") }, FG.t("model.overview"))) : null,
        /* What each part of an identified object is, before the helper inspects one. */
        page.identifier === "identifiers" ? FG.flow("object") : null,
        FG.helpers && FG.helpers[page.identifier] ? FG.helpers[page.identifier](route) : helperComing(page) ? h("p", { class: "notice helper-coming" }, FG.t("page.helperComing")) : null
      )
    );
  };

  /** A connection's carrier and actors describe its function; dated implementation evidence stays scoped. */
  FG.modelDetail = function (term) {
    const fields = ["transfer", "sender", "recipient", "carrier", "maintainers"].filter((key) => term[key]);
    const examples = FG.refs(term, "hasPart").filter((entry) => entry.modelKind === "example");
    return [fields.length ? h("dl", { class: "relations model-detail" }, fields.map((key) => [FG.relationTerm(key, FG.t("model.field." + key)), h("dd", null, FG.span(term[key]))])) : null,
      examples.length ? h("details", { class: "model-examples" }, h("summary", null, FG.t("model.examples")), h("div", { class: "content" }, examples.map((example) => h("section", { class: "model-example" },
        h("h4", null, FG.span(example.name)), example.scope ? h("p", { class: "small" }, FG.span(example.scope)) : null,
        FG.paragraphs(example.description), statusBadge(example, "model.statusAsOf"),
        h("p", { class: "small" }, FG.refs(example, "citation").map((source, index) => [index ? ", " : "", FG.sourceLink(source)])), FG.apiLink(example))))) : null];
  };

  function modelOverview() {
    const model = FG.get("#implementation-model");
    if (!model) return null;
    const layers = FG.modelTerms("layer");
    const seams = FG.modelTerms("seam");
    const selected = seams.find((term) => term.identifier === FG.modelSelected) || seams[0];
    const panel = (term) => h("div", { id: "model-connection", class: "model-connection", role: "region", "aria-label": FG.t("model.kind.seam") },
      h("h3", null, FG.span(term.name)), FG.paragraphs(term.description), FG.modelDetail(term),
      h("dl", { class: "relations small" }, FG.modelRows(term)),
      h("p", { class: "small" }, h("a", { href: FG.entryHref(term) }, FG.t("model.openRecord")), " · ",
        h("a", { href: FG.modelFilterHref("resources", term) }, FG.t("model.related"))));
    return h("div", { class: "implementation-model" },
      model.description ? FG.paragraphs(model.description) : null,
      model.introduction ? FG.paragraphs(model.introduction) : null,
      model.ordering ? h("p", null, FG.span(model.ordering)) : null,
      modelFigure("layers-and-seams", FG.t("model.diagramAlt"), FG.t("model.diagramCaption")),
      h("h2", null, FG.t("model.functions")),
      h("ul", { class: "cards model-layers" }, layers.map((layer) => h("li", { class: "card" }, h("h3", null, FG.modelLink(layer)), FG.paragraphs(layer.description)))),
      model.feedback ? h("p", null, FG.span(model.feedback)) : null,
      h("h2", null, FG.t("model.connections")),
      h("label", { for: "model-seam" }, FG.t("model.choose")),
      h("select", { id: "model-seam", "aria-controls": "model-connection", onchange: (event) => {
        FG.modelSelected = event.target.value;
        document.getElementById("model-connection").replaceWith(panel(seams.find((term) => term.identifier === event.target.value)));
      } }, seams.map((term) => h("option", { value: term.identifier, selected: term === selected }, FG.text(term.name)))),
      selected ? panel(selected) : null,
      modelWorkedExample(),
      h("p", { class: "small" }, h("a", { href: FG.catalogueHref("model") }, FG.t("model.allRecords")))
    );
  }

  /* The publication hand-over a dataset passes through: identifier registration, NMA harvesting and the reporting
     link. The steps' facts are the seam records themselves; only this selection and order belong to the view. */
  const PUBLICATION_CHAIN = ["repository-pid-registry", "repository-nma", "nma-research-register"];

  /** Hand-overs as an ordered visual: for each seam, who passes what to whom and by what carrier, from the model's
      seam records, so the same facts read the same at a station and beside the metadata figure. */
  FG.seamFlow = function (seams, title) {
    const records = seams.map((seam) => (typeof seam === "string" ? FG.get("#seam-" + seam) : seam)).filter((seam) => seam && seam.sender && seam.recipient);
    if (!records.length) return null;
    return h(
      "figure",
      { class: "flow flow-handover", "data-flow": "handover" },
      h("figcaption", { class: "flow-title" }, title || FG.t("visual.handover.title")),
      h("ol", { class: "flow-steps" }, records.map((seam) => h("li", { class: "flow-step", "data-step": seam.identifier },
        h("strong", { class: "flow-label" }, FG.span(seam.sender), " → ", FG.span(seam.recipient)), " ",
        seam.transfer ? h("span", { class: "flow-text" }, FG.span(seam.transfer)) : null,
        seam.carrier ? h("span", { class: "flow-carrier small" }, FG.t("model.field.carrier") + ": ", FG.span(seam.carrier)) : null,
        h("a", { class: "flow-record small", href: FG.entryHref(seam) }, FG.span(seam.name))))),
      records.some((seam) => seam["@id"] === "#seam-nma-research-register") ? h("p", { class: "flow-note small" }, FG.span(FG.get("#seam-nma-research-register").description)) : null
    );
  };
  FG.publicationFlow = () => FG.seamFlow(PUBLICATION_CHAIN, FG.t("visual.handover.publication"));

  /** Reuse the manuscript's figures without changing their geometry or scoped arrow/status meanings. */
  function modelFigure(stem, alternative, caption) {
    const url = "assets/diagrams/" + stem + "-" + FG.state.lang + ".svg";
    return h("figure", { class: "model-diagram" },
      h("div", { class: "diagram-scroll", tabindex: "0", role: "region", "aria-label": alternative },
        h("img", { src: url, alt: alternative, loading: "lazy" })),
      h("figcaption", { class: "small muted" }, caption ? [caption, " · "] : null, FG.external(url, FG.t("model.openFigure"))));
  }

  function modelWorkedExample() {
    const example = FG.get(FG.get("#implementation-model")?.workExample);
    if (!example) return null;
    return h("section", { class: "model-worked-example" }, h("h2", null, FG.span(example.name)), FG.paragraphs(example.description),
      h("ol", null, FG.refs(example, "hasPart").map((entity) => h("li", null,
        h("a", { href: FG.referenceHref(entity["@id"]) }, entity.identifier || FG.span(entity.name)),
        entity.text ? [" · ", FG.span(entity.text)] : entity.identifier && entity.name ? [" · ", FG.span(entity.name)] : null))),
      FG.apiLink(example));
  }

  /** What a reader may want from the knowledge base and where it is: each row leads to the guide's own data. */
  function machineTasks() {
    const files = FG.config.api.files;
    const link = (href, label, type) => h("a", { href, type: type || null }, label || href);
    const example = FG.config.api.records[FG.graph.find((entity) => entity.termCode === "R1.1")["@id"]];
    const rows = [
      ["crate", [link("ro-crate-metadata.json", null, "application/ld+json"), " · ", link("ro-crate-preview.html", FG.t("machines.preview")), " · ", link("profile/0.1/index.html", FG.t("machines.profile"))]],
      ["record", [h("code", null, files.record.replace("{record}", "<kolekce>/<id>")), " · ", FG.t("machines.example") + ": ", link(files.record.replace("{record}", example), null, "application/json")]],
      ["service", [link(files.description, null, "application/vnd.oai.openapi+json"), " · ", link(files.docs, FG.t("api.docs"), "text/html")]],
      ["health", [link("health/index.html", FG.t("footer.health"), "text/html"), " · ", link(files.health, "JSON", "application/json")]],
      ["tests", [link("assets/js/tests/index.html" + (FG.state.lang === "en" ? "#english" : ""), FG.t("machines.testDocs"), "text/html"), " · ", link(FG.href("catalogue", "k!tests"), FG.t("catalogue.tab.tests"))]],
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
        [["meta", files.meta, "application/json"], ["context", files.context, "application/ld+json"], ["health", files.health, "application/json"]].map(([key, path, type]) =>
          h("tr", null, h("th", { scope: "row" }, FG.t("api." + key)), h("td", null, file(path, type)), h("td", null, ""))
        )
      )
    );
  }

  /** Whether a page holds a helper that the page script does not provide yet. */
  function helperComing(page) {
    return FG.list(page.additionalType).includes(FG.config.vocab.webApplication) && !FG.list(FG.config.helpers?.pages).includes(page.identifier) && !(FG.helpers && FG.helpers[page.identifier]);
  }

  /** The tools: the helpers for single tasks on the path and the advice on AI, each as a card. */
  FG.views.tools = function () {
    const pages = Object.entries(FG.config.pageMenu || {})
      .filter(([, menu]) => menu === "tools")
      .map(([id]) => FG.get("#page-" + id))
      .filter(Boolean);
    const groupOf = (page) => (FG.config.toolGroup || {})[page.identifier];
    /* Interactive helpers first, then guidance, each as its own section of cards. */
    const section = (group, key) => {
      const members = pages.filter((page) => groupOf(page) === group);
      if (!members.length) return null;
      return h(
        "section",
        { class: "tool-group", "aria-labelledby": "tools-" + group },
        h("h2", { id: "tools-" + group }, FG.t("tools." + key)),
        h("p", { class: "muted" }, FG.t("tools." + key + "Intro")),
        h(
          "ul",
          { class: "tool-cards" },
          members.map((page) =>
            h(
              "li",
              { class: "tool-card" },
              FG.icon((FG.config.icons.page || {})[page.identifier], { class: "tool-card-icon" }),
              h(
                "div",
                null,
                h("h3", null, h("a", { href: FG.href("page", page.identifier) }, FG.span(page.headline))),
                page.description ? h("p", null, FG.span(page.description)) : null,
                helperComing(page) ? h("p", { class: "badge tool-coming" }, FG.t("tools.coming")) : null
              )
            )
          )
        )
      );
    };
    return h(
      "div",
      { class: "layout wrap tools" },
      h("article", null, heading(1, null, FG.t("tools.title")), h("p", { class: "lead" }, FG.t("tools.intro")), section("tool", "groupTool"), section("guidance", "groupGuidance"))
    );
  };
})();
