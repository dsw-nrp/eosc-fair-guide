/* Views of the FAIR data guide: shell, path, principle explorer, resource and repository finders, pages. */
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

  FG.views.header = function (route) {
    const lensSelect = h(
      "select",
      { id: "lens-select", onchange: (event) => FG.navigateInPlace(FG.href(route.view, route.arg, { lens: event.target.value })) },
      FG.lenses().map((lens) => h("option", { value: lens.audienceType, selected: lens.audienceType === route.lens }, FG.text(lens.name)))
    );
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
          h(
            "a",
            { href: FG.config.links.eoscHome, target: "_top" },
            h("img", { src: "assets/img/eosc-cz-logo.svg", alt: FG.t("app.home"), width: "144", height: "30" })
          ),
          h("a", { class: "brand-title", href: FG.href("path", "start") }, FG.t("app.title"))
        ),
        h(
          "div",
          { class: "controls" },
          h("label", { for: "lens-select" }, FG.t("nav.lens")),
          lensSelect,
          h("a", { class: "button", href: FG.href(route.view, route.arg, { lang: otherLang }), lang: otherLang, hreflang: otherLang }, FG.t("nav.switchTo"))
        )
      )
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
    const items = [
      ["path", "start", "nav.path"],
      ["selfcheck", null, "nav.selfcheck"],
      ["explorer", null, "nav.explorer"],
      ["resources", null, "nav.resources"],
      ["repositories", null, "nav.repositories"],
      ["page", "about", "nav.about"],
    ];
    const current = (view, arg) =>
      (view === route.view && (!arg || arg === route.arg || view === "path")) || (view === "selfcheck" && route.view === "check");
    return h(
      "nav",
      { class: "main-nav wrap", "aria-label": FG.t("nav.label") },
      h(
        "ul",
        null,
        items.map(([view, arg, key]) => h("li", null, h("a", { href: FG.href(view, arg), "aria-current": current(view, arg) ? "page" : null }, FG.t(key))))
      )
    );
  };

  FG.views.footer = function () {
    const root = FG.root;
    const authors = FG.refs(root, "author").map((person) => person.name).join(", ");
    const year = String(root.datePublished || "").slice(0, 4);
    const citation = `${authors} (${year}). ${FG.text(root.name)}, ${FG.state.lang === "cs" ? "verze" : "version"} ${root.version}. ${root.url}`;
    return h(
      "footer",
      { class: "site-footer" },
      h(
        "div",
        { class: "wrap" },
        h("p", null, FG.t("footer.version", { version: FG.config.version, date: FG.formatDate(FG.config.datePublished) })),
        h("p", null, h("strong", null, FG.t("footer.cite") + ": "), citation),
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
        h("img", { class: "logolink", src: `assets/img/logolink-${FG.state.lang}.svg`, alt: FG.t("footer.logos"), width: "512", height: "78" })
      )
    );
  };

  /* ---------------------------------------------------------------- path */

  function rail(route, currentId) {
    const current = FG.stations().find((station) => station.identifier === currentId);
    return [
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

  function stageEntry() {
    const stages = FG.ofType("DefinedTerm").filter((term) => FG.id(term.inDefinedTermSet) === "#stages");
    return h(
      "section",
      { class: "stage-entry", "aria-labelledby": "stage-question" },
      heading(1, { id: "stage-question" }, FG.t("stage.question")),
      h("p", null, FG.t("stage.intro")),
      resumeLine(),
      h(
        "ul",
        { class: "stage-options" },
        stages.map((stage) =>
          h(
            "li",
            null,
            h(
              "button",
              {
                type: "button",
                onclick: () => {
                  const station = FG.get(stage.startsAt).identifier;
                  FG.state.started = true;
                  FG.state.entryStation = station;
                  FG.saveState();
                  FG.navigate(FG.href("path", station));
                },
              },
              FG.span(stage.name)
            )
          )
        )
      )
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
      h(
        "ul",
        { class: "chips" },
        principles.map((principle) =>
          h("li", null, h("a", { class: "chip", href: FG.href("explorer", principle.termCode) }, principle.termCode + " · ", FG.span(principle.name)))
        )
      ),
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

  function madeContent(items) {
    const ids = new Set(items.map((item) => item["@id"]));
    const sources = [];
    for (const item of items) {
      for (const clause of FG.refs(item, "citation")) {
        const source = FG.get(clause.isPartOf);
        if (source && !sources.includes(source)) sources.push(source);
      }
    }
    const actions = FG.graph.filter(
      (entity) => /Action$/.test(FG.list(entity["@type"])[0]) && FG.refIds(entity, "result").some((id) => ids.has(id))
    );
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
    return h(
      "article",
      { class: "station" },
      h(
        "header",
        { class: "station-header" },
        h("p", { class: "muted" }, FG.t("station.step", { n: entity.position, total: stations.length })),
        heading(1, null, FG.span(entity.name), " · ", FG.span(entity.headline)),
        h(
          "div",
          { class: "meta" },
          minutes ? h("span", null, FG.t("station.minutes", { n: minutes })) : null,
          h("span", { class: "visually-hidden" }, FG.t("station.principles") + ":"),
          h(
            "ul",
            { class: "chips" },
            FG.refs(entity, "about").map((principle) => h("li", null, h("a", { class: "chip", href: FG.href("explorer", principle.termCode) }, principle.termCode)))
          ),
          h("button", { type: "button", class: "button-link", onclick: () => FG.navigate(FG.href("path", "start")) }, FG.t("stage.change"))
        )
      ),
      now
        ? h(
            "section",
            { class: "now", "aria-label": levelName("L0") },
            h("p", { class: "level" }, levelName("L0")),
            h("p", null, FG.span(now.text)),
            action
              ? FG.id(action.target).startsWith("#")
                ? h("a", { class: "button button-primary", href: FG.actionHref(FG.id(action.target)) }, FG.span(action.name))
                : FG.external(FG.id(action.target), FG.text(action.name), { class: "button button-primary" })
              : null
          )
        : h("p", null, FG.t("station.empty")),
      steps.length ? details(levelName("L1"), "L1", h("ol", { class: "steps" }, steps.map(adviceItem))) : null,
      ai.length ? details(FG.t("station.ai"), "ai", ai.map((item) => h("p", { class: "tip" }, FG.span(item.text))), h("p", null, h("a", { href: FG.href("page", "ai") }, FG.text(FG.get("#page-ai").headline)))) : null,
      details(levelName("L2"), "L2", whyContent(entity, items)),
      details(levelName("L3"), "L3", madeContent(items)),
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
    const showEntry = route.arg === "start" || (!route.arg && !FG.state.started);
    const currentId = showEntry ? null : route.arg || FG.state.lastStation || FG.state.entryStation || FG.stations()[0].identifier;
    if (currentId && currentId !== FG.state.lastStation && FG.stations().some((station) => station.identifier === currentId)) {
      FG.state.lastStation = currentId;
      FG.saveState();
    }
    return h(
      "div",
      { class: "layout layout-path wrap" },
      rail(route, currentId),
      h("div", null, showEntry ? stageEntry() : station(Object.assign({}, route, { arg: currentId })))
    );
  };

  /* ---------------------------------------------------------------- principle explorer */

  FG.views.explorer = function (route) {
    const principles = FG.principles();
    const selected = principles.find((principle) => principle.termCode === route.arg);
    const clauses = selected
      ? FG.graph.filter((entity) => entity.clauseKind && FG.hasRef(entity, "about", selected["@id"]))
      : [];
    const actors = ["#actor-nrp", "#actor-repository", "#actor-fip", "#actor-other"];
    return h(
      "div",
      { class: "layout wrap" },
      h(
        "section",
        null,
        heading(1, null, FG.t("explorer.title")),
        h("p", null, FG.t("explorer.intro")),
        h(
          "ul",
          { class: "principles-grid", "aria-label": FG.t("explorer.choose") },
          principles.map((principle) =>
            h("li", null, h("a", { href: FG.href("explorer", principle.termCode), "aria-current": principle === selected ? "true" : null }, h("strong", null, principle.termCode), " ", FG.span(principle.name)))
          )
        ),
        selected
          ? h(
              "section",
              { "aria-labelledby": "principle-heading" },
              heading(2, { id: "principle-heading" }, selected.termCode + " · ", FG.span(selected.name)),
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
          : null
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

  const filters = { station: "", lens: "", type: "", status: "", language: "" };

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
        (!filters.lens || lensOf(resource, filters.lens)) &&
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
          select("lens", FG.t("finder.lens"), FG.lenses().map((lens) => [lens.audienceType, FG.text(lens.name)])),
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
        sections.map((section) => h("section", null, section.headline ? h("h2", null, FG.span(section.headline)) : null, FG.paragraphs(section.text))),
        FG.helpers && FG.helpers[page.identifier] ? FG.helpers[page.identifier]() : null
      )
    );
  };
})();
