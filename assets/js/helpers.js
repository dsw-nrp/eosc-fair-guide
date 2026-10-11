/* Identifier verification. Extraction and checksums stay local; only an explicit lookup calls a connector.
   Checksum algorithms follow ORCID's identifier documentation and ROR's documented Crockford/MOD 97-10 pattern. */
(function () {
  "use strict";
  const FG = window.FairGuide;
  const H = (FG.helpers = FG.helpers || {});
  const h = (...args) => FG.h(...args);
  const NAMES = { doi: "DOI", handle: "Handle", orcid: "ORCID iD", ror: "ROR ID" };
  const BASE32 = "0123456789abcdefghjkmnpqrstvwxyz";
  const CANDIDATE = /(?<![\w./:@-])(?:(?:https?:\/\/)?(?:orcid\.org|ror\.org|(?:dx\.)?doi\.org|hdl\.handle\.net)\/[^\s<>"']+|\d{4}-\d{4}-\d{4}-\d{3}[\dX]|0[a-z0-9]{6}\d{2}|(?:doi|hdl):\s*\d[\w.-]*\/[^\s<>"']+|10\.\d{4,9}\/[^\s<>"']+)/gi;

  H.validOrcid = function (value) {
    if (!/^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/.test(value)) return false;
    const digits = value.replace(/-/g, "");
    let total = 0;
    for (const digit of digits.slice(0, 15)) total = (total + Number(digit)) * 2;
    const check = (12 - total % 11) % 11;
    return digits[15] === (check === 10 ? "X" : String(check));
  };

  H.validRor = function (value) {
    if (!/^0[a-hj-km-np-tv-z0-9]{6}\d{2}$/.test(value)) return false;
    let number = 0;
    for (const letter of value.slice(0, 7)) number = number * 32 + BASE32.indexOf(letter);
    return Number(value.slice(7)) === 98 - (number * 100) % 97;
  };

  // Remove sentence punctuation and unmatched closing brackets, keeping balanced DOI suffixes such as a(b).
  function unquote(value) {
    value = value.replace(/[.,;:!?]+$/, "");
    for (const [open, close] of [["(", ")"], ["[", "]"], ["{", "}"]]) {
      while (value.endsWith(close) && value.split(close).length > value.split(open).length) value = value.slice(0, -1);
    }
    return value;
  }

  function parsed(input) {
    let value = unquote(input);
    if (/^(?:https?:\/\/)?(?:orcid\.org|ror\.org|(?:dx\.)?doi\.org|hdl\.handle\.net)\//i.test(value)) {
      const url = new URL(/^https?:\/\//i.test(value) ? value : "https://" + value);
      if (!["orcid.org", "ror.org"].includes(url.hostname.toLowerCase())) return FG.live.parsePid(url.origin + url.pathname);
      try { value = decodeURIComponent(url.pathname.slice(1)).replace(/\/$/, ""); } catch (error) { return null; }
      if (url.hostname.toLowerCase() === "orcid.org") return { type: "orcid", value: value.toUpperCase() };
      return { type: "ror", value: value.toLowerCase() };
    }
    if (/^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/i.test(value)) return { type: "orcid", value: value.toUpperCase() };
    if (/^0[a-z0-9]{6}\d{2}$/i.test(value)) return { type: "ror", value: value.toLowerCase() };
    return FG.live.parsePid(value);
  }

  H.identifierUrl = (item) => item.type === "orcid" ? FG.config.helpers.orcidUrl + item.value
    : item.type === "ror" ? FG.config.helpers.rorUrl + item.value : FG.live.pidUrl(item);

  H.extract = function (input) {
    const config = FG.config.helpers;
    const text = String(input || "");
    if (text.length > config.maxCharacters) return { items: [], textLimit: true, itemLimit: false };
    const items = [], seen = new Set();
    for (const match of text.matchAll(CANDIDATE)) {
      const next = text[match.index + match[0].length];
      if (next && /[\w/-]/.test(next)) continue;
      const item = parsed(match[0]);
      if (!item) continue;
      // DOI names are case insensitive; Handle suffixes can distinguish case.
      const key = item.type + ":" + (item.type === "doi" ? item.value.toLowerCase() : item.value);
      if (seen.has(key)) continue;
      seen.add(key);
      if (items.length === config.maxItems) return { items, textLimit: false, itemLimit: true };
      item.checksum = item.type === "orcid" ? H.validOrcid(item.value) : item.type === "ror" ? H.validRor(item.value) : null;
      items.push(item);
    }
    return { items, textLimit: false, itemLimit: false };
  };

  H.resolveIdentifier = async function (item) {
    if (item.checksum === false) return { status: "invalid" };
    try {
      if (item.type === "orcid" || item.type === "ror") {
        const name = await FG.live[item.type === "orcid" ? "orcidName" : "rorName"](item.value);
        return name === null ? { status: "notFound" } : { status: "found", title: name === item.value ? null : name, url: H.identifierUrl(item) };
      }
      const record = await FG.live.resolvePid(item);
      if (!record.found) return { status: "notFound" };
      let title = record.title, metadataUnavailable = false;
      if (!title && item.type === "doi") {
        const matches = (value) => typeof value === "string" && value.toLowerCase() === item.value.toLowerCase();
        try {
          const metadata = await FG.live.datacite(item.value);
          if (metadata && matches(metadata.doi)) title = FG.list(metadata.titles).map((entry) => entry && entry.title).find((name) => typeof name === "string" && name.trim());
        } catch (error) { metadataUnavailable = true; }
        if (!title) {
          try {
            const metadata = await FG.live.crossref(item.value);
            if (metadata && matches(metadata.DOI)) title = FG.list(metadata.title).find((name) => typeof name === "string" && name.trim());
          } catch (error) { metadataUnavailable = true; }
        }
        if (title) metadataUnavailable = false;
      }
      return { status: "found", title: title || null, url: record.url, metadataUnavailable };
    } catch (error) {
      return { status: "unavailable" };
    }
  };

  let draft = "", seed = null;
  H.identifiers = function (route) {
    if (route.extra && route.extra !== seed) { draft = route.extra; seed = route.extra; }
    const config = FG.config.helpers;
    const text = h("textarea", { id: "identifier-text", rows: 6, "aria-describedby": "identifier-privacy", oninput: () => { draft = text.value; } }, draft);
    const clear = h("button", { type: "button", class: "field-clear", "aria-label": FG.t("helper.identifiers.clear"), title: FG.t("helper.identifiers.clear"), onclick: () => {
      text.value = ""; draft = ""; seed = null;
      rows = []; queue.length = 0;
      list.replaceChildren(); summary.textContent = "";
      window.history.replaceState(null, "", FG.href("page", "identifiers"));
      controls(); text.focus();
    } }, FG.icon("clear"));
    const summary = h("p", { id: "identifier-summary", role: "status" });
    const list = h("ul", { class: "identifier-list" });
    const find = h("button", { type: "submit", class: "button button-primary" }, FG.t("helper.identifiers.find"));
    const all = h("button", { type: "button", class: "button", hidden: true, onclick: () => {
      rows.filter((row) => row.status === "unresolved").forEach(enqueue);
    } }, FG.t("helper.identifiers.resolveAll"));
    const form = h("form", { onsubmit: (event) => { event.preventDefault(); scan(); } },
      h("label", { for: "identifier-text" }, FG.t("helper.identifiers.label")), h("div", { class: "field-clearable" }, text, clear),
      h("p", { id: "identifier-privacy", class: "small muted" }, FG.t("helper.identifiers.privacy")),
      h("div", { class: "buttons" }, find, all));
    const box = h("section", { class: "identifier-helper", "aria-label": FG.t("helper.identifiers.label") }, form, summary, list);
    let rows = [], active = 0, itemLimit = false;
    const queue = [];

    function controls() {
      const running = active > 0 || queue.length > 0;
      all.hidden = !rows.length;
      all.disabled = running || !rows.some((row) => row.status === "unresolved");
      if (rows.some((row) => !["unresolved", "invalid"].includes(row.status))) {
        summary.textContent = FG.t("helper.identifiers.coverage", {
          done: rows.filter((row) => ["found", "notFound", "unavailable"].includes(row.status)).length,
          total: rows.filter((row) => row.status !== "invalid").length,
        }) + (itemLimit ? " " + FG.t("helper.identifiers.itemLimit", { n: config.maxItems }) : "");
      }
    }

    function show(row) {
      row.element.dataset.status = row.status;
      row.message.replaceChildren();
      const result = row.result;
      if (row.status === "found") {
        row.message.append(h("p", null, h("strong", null, FG.t("helper.identifiers.found")), " ", result.title || FG.t("helper.identifiers.titleMissing")));
        if (result.metadataUnavailable) row.message.append(h("p", { class: "small muted" }, FG.t("helper.identifiers.metadataUnavailable")));
        if (result.url && result.url !== H.identifierUrl(row.item)) row.message.append(h("p", null, FG.external(result.url, FG.t("helper.identifiers.openRecord"))));
      } else row.message.append(h("p", null, FG.t("helper.identifiers." + row.status)));
      row.button.disabled = ["invalid", "queued", "running", "found", "notFound"].includes(row.status);
      row.button.hidden = ["invalid", "found", "notFound"].includes(row.status);
      row.button.textContent = FG.t("helper.identifiers." + (row.status === "unavailable" ? "retry" : "resolve"));
    }

    function enqueue(row) {
      if (!["unresolved", "unavailable"].includes(row.status)) return;
      row.status = "queued";
      queue.push(row);
      show(row);
      drain();
    }

    function drain() {
      while (active < config.maxConcurrent && queue.length) {
        const row = queue.shift();
        active++;
        row.status = "running";
        show(row);
        H.resolveIdentifier(row.item).then((result) => {
          row.result = result;
          row.status = result.status;
          show(row);
        }).finally(() => { active--; drain(); controls(); });
      }
      controls();
    }

    function scan() {
      const found = H.extract(text.value);
      itemLimit = found.itemLimit;
      list.replaceChildren();
      rows = [];
      if (found.textLimit) summary.textContent = FG.t("helper.identifiers.textLimit", { n: config.maxCharacters });
      else summary.textContent = FG.t(found.items.length ? "helper.identifiers.count" : "helper.identifiers.empty", { n: found.items.length })
        + (found.itemLimit ? " " + FG.t("helper.identifiers.itemLimit", { n: config.maxItems }) : "");
      for (const item of found.items) {
        const row = { item, status: item.checksum === false ? "invalid" : "unresolved" };
        row.message = h("div", { role: "status" });
        row.button = h("button", { type: "button", class: "button button-small", onclick: () => enqueue(row) });
        rows.push(row);
        row.element = h("li", null,
          h("p", null, h("strong", null, NAMES[item.type]), " ", FG.external(H.identifierUrl(item), H.identifierUrl(item))),
          item.checksum !== null ? h("p", { class: "small muted" }, FG.t("helper.identifiers." + (item.checksum ? "checksumValid" : "checksumInvalid"))) : null,
          row.message, row.button);
        list.append(row.element);
        show(row);
      }
      controls();
    }
    if (draft) scan();
    return box;
  };
})();
