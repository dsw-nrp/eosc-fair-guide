/* Optional external evaluators: FAIR-Checker run from the browser and a local F-UJI report. Loaded with the check
   controls. Nothing contacts a provider until the reader chooses it, and only the target identifier is sent. One
   assessment record keeps each accepted assessment: target, inspected subject and representation, dates, supplied
   versions, and every native result with its own identifier, wording, verdict, score, maturity, subtests and
   diagnostics. Questions refer to that record. Each result is read as its provider presents it (`P.reading`), and a
   reviewed mapping (crate `#criterion-*`) for a reviewed version turns that reading into a suggestion: whole coverage
   answers as the reading, partial coverage answers Partly or No (D-168). Provider text is untrusted and is only ever
   shown as text. */
(function () {
  "use strict";

  const FG = window.FairGuide;
  const SC = FG.selfcheck;
  const P = (FG.providers = FG.providers || {});
  const VERDICTS = ["pass", "fail", "indeterminate"];
  const TEXT_MAX = 8000;
  const LOG_MAX = 65536;
  const RESULTS_MAX = 100;
  const SUBTESTS_MAX = 50;
  const HARVEST_MAX = 20;
  const ASSESSMENTS_MAX = 8;
  const ASSESSMENT_ID = /^(fair-checker|f-uji):[A-Za-z0-9:._-]{1,120}$/;

  /* ---------------------------------------------------------------- shared assessment record */

  P.settings = () => FG.config.providers || { list: [] };
  P.provider = (id) => FG.list(P.settings().list).find((entry) => entry.id === id) || null;
  /** An evaluator's badge: the favicon of its entry among the resources, or its monogram. */
  const evaluatorBadge = (provider, id) => FG.serviceBadge(id || provider.id, (FG.get("#resource-" + (id || provider.id)) || {}).url);
  P.criterion = (provider, metric) => FG.sourceEntity(provider, metric);
  P.isAssessmentId = (value) => typeof value === "string" && ASSESSMENT_ID.test(value);

  /** The reviewed mappings of a provider's criteria: metric, question, coverage and the crate entity holding the note. */
  P.mappings = function (provider) {
    if (!provider) return [];
    return FG.list(provider.metrics).flatMap((metric) => {
      const criterion = P.criterion(provider.id, metric);
      return criterion
        ? FG.refs(criterion, "hasPart").map((entity) => ({ metric, question: String(FG.id(entity.about) || "").replace(/^#item-/, ""), coverage: entity.mappingCoverage, entity }))
        : [];
    });
  };

  /** Whether an assessment's supplied versions are ones the mappings were reviewed against: every version a reviewed
      entry names must be supplied with that exact value. An unknown version never borrows a known one's mappings. */
  P.reviewed = (provider, versions) =>
    FG.list(provider && provider.reviewed).some((entry) => Object.keys(entry).length > 0 && Object.entries(entry).every(([key, value]) => Boolean(versions) && versions[key] === value));

  const text = (value, max = TEXT_MAX) => (typeof value === "string" ? value.slice(0, max) : typeof value === "number" && Number.isFinite(value) ? String(value) : null);
  const number = (value) => (typeof value === "number" && Number.isFinite(value) ? value : null);
  const web = (value) => {
    if (typeof value !== "string" || value.length > 2000 || /\s/.test(value)) return null;
    try {
      const url = new URL(value);
      return /^https?:$/.test(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch (error) {
      return null;
    }
  };
  const today = () => new Date().toISOString().slice(0, 10);
  const day = (value) => (/^\d{4}-\d{2}-\d{2}/.test(String(value || "")) ? String(value).slice(0, 10) : null);
  const verdict = (value) => (VERDICTS.includes(value) ? value : null);
  /* F-UJI's own reading, as its client draws a result: a metric passed at its FAIR level when that level is 1 or more,
     and unknown (its question mark) at level 0, whatever the report's test status says; only without a whole-number
     level does the test status decide. A subtest shows passed or unknown by its own status. The report's status stays
     as `native`, and the overview says where the two differ. */
  const fujiVerdict = (maturity, status) => (Number.isInteger(maturity) ? (maturity >= 1 ? "pass" : "indeterminate") : status === "pass" ? "pass" : "indeterminate");
  const fujiSubtestVerdict = (status) => (status === "pass" ? "pass" : "indeterminate");
  const compact = (object) => Object.fromEntries(Object.entries(object).filter(([, value]) => value != null && value !== ""));
  const coded = (code, message) => Object.assign(new Error(message), { code });

  /** The SHA-256 digest that identifies one original report, or null where the browser offers no SubtleCrypto
      (outside a secure context); a weaker hash would let a crafted file claim another report's identity. */
  P.digest = async function (source) {
    if (!window.crypto || !window.crypto.subtle) return null;
    const hash = new Uint8Array(await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(source)));
    return "sha256-" + Array.from(hash, (byte) => byte.toString(16).padStart(2, "0")).join("");
  };

  /** Whether two targets name the same object: the same DOI (case-insensitive) or Handle, else the same address. */
  P.sameTarget = function (a, b) {
    if (!a || !b) return false;
    const left = FG.live.parsePid(a);
    const right = FG.live.parsePid(b);
    if (left || right) return Boolean(left && right && left.type === right.type && (left.type === "doi" ? left.value.toLowerCase() === right.value.toLowerCase() : left.value === right.value));
    const strip = (value) => (web(value) || "").replace(/\/+$/, "");
    return Boolean(strip(a)) && strip(a) === strip(b);
  };

  const subtestOf = ([id, test]) =>
    compact({
      id: text(id, 100),
      name: test && text(test.metric_test_name),
      native: test && text(test.metric_test_status, 40),
      verdict: test && fujiSubtestVerdict(test.metric_test_status),
      score: test && test.metric_test_score && typeof test.metric_test_score === "object" ? compact({ earned: number(test.metric_test_score.earned), total: number(test.metric_test_score.total) }) : null,
      maturity: test && number(test.metric_test_maturity),
    });

  /** One F-UJI metric result with its native fields; score, maturity, the report's status and F-UJI's own reading
      stay separate. Its log stays in the original report, which the overview reads when the report is retained
      (`P.nativeLog`). */
  function fujiResult(result) {
    const tests = result.metric_tests && typeof result.metric_tests === "object" && !Array.isArray(result.metric_tests) ? Object.entries(result.metric_tests) : [];
    return compact({
      id: text(result.metric_identifier, 100),
      name: text(result.metric_name),
      native: text(result.test_status, 40),
      verdict: fujiVerdict(number(result.maturity), result.test_status),
      score: result.score && typeof result.score === "object" ? compact({ earned: number(result.score.earned), total: number(result.score.total) }) : null,
      maturity: number(result.maturity),
      subtests: tests.slice(0, SUBTESTS_MAX).map(subtestOf),
    });
  }

  /** A F-UJI metric's native log, read from the retained original report. */
  const parsed = new Map();
  P.nativeLog = function (assessment, metric) {
    const digest = assessment && assessment.source && assessment.source.digest;
    const source = digest && P.sourceText(digest);
    if (!source) return null;
    if (!parsed.has(digest)) {
      try {
        parsed.set(digest, JSON.parse(source));
      } catch (error) {
        parsed.set(digest, null);
      }
    }
    const result = FG.list((parsed.get(digest) || {}).results).find((entry) => entry && entry.metric_identifier === metric);
    return result ? FG.list(result.test_debug).filter((line) => typeof line === "string").join("\n").slice(0, LOG_MAX) || null : null;
  };

  /** What F-UJI harvested and where: the method and address, with licence, access and identifier statements kept
      apart by source, so a combined statement is never presented as one effective licence. */
  function harvestOf(entry) {
    const metadata = entry && entry.metadata && typeof entry.metadata === "object" ? entry.metadata : {};
    const values = (key) => FG.list(metadata[key]).map((value) => text(value, 500)).filter(Boolean).slice(0, 10);
    return compact({ method: text(entry.method, 80), url: web(entry.url), format: text(entry.format, 80), schema: text(entry.schema, 300), licence: values("license"), access: values("access_level"), identifier: values("object_identifier") });
  }

  /** Read a F-UJI JSON report locally, or say why it cannot be used: too large, not JSON, a guide result, another
      kind of JSON, or a F-UJI-shaped report with broken results. Nothing is fetched or executed. */
  P.readFuji = async function (source, file) {
    const settings = P.settings();
    const bytes = new TextEncoder().encode(source).length;
    if (bytes > settings.maxImportBytes) return { error: "tooLarge", params: { size: FG.formatBytes ? FG.formatBytes(bytes) : String(bytes), max: FG.formatBytes ? FG.formatBytes(settings.maxImportBytes) : String(settings.maxImportBytes) } };
    let data;
    try {
      data = JSON.parse(source);
    } catch (error) {
      return { error: "notJson" };
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) return { error: "foreign" };
    if (data.format === "eosc-fair-guide-result" || FG.list(data["@graph"]).some((entity) => entity && typeof entity.guideState === "string")) return { error: "guideResult" };
    if (!Array.isArray(data.results) || !data.request || typeof data.request !== "object") return { error: "foreign" };
    const shaped = (result) => result && typeof result === "object" && /^FsF-[A-Za-z0-9.-]{1,60}$/.test(String(result.metric_identifier || "")) && typeof result.test_status === "string";
    if (!data.results.length || data.results.length > RESULTS_MAX || !data.results.every(shaped)) return { error: "broken" };
    const target = text(data.request.object_identifier, 2000);
    if (!target) return { error: "broken" };
    const provider = P.provider("f-uji");
    const versions = compact({ software: text(data.software_version, 40), metric: text(data.metric_version, 40), requested: text(data.request.metric_version, 40), specification: web(data.metric_specification) });
    const hash = await P.digest(source);
    if (!hash) return { error: "noDigest" };
    const assessment = {
      id: "f-uji:" + hash,
      provider: "f-uji",
      target,
      subject: text(data.request.normalized_object_identifier, 2000),
      representation: web(data.resolved_url),
      assessed: text(data.end_timestamp || data.start_timestamp, 40),
      retrieved: today(),
      report: text(data.test_id, 100),
      versions,
      reviewed: P.reviewed(provider, versions),
      total: number(data.total_metrics),
      results: data.results.map(fujiResult),
      harvest: FG.list(data.harvested_metadata).filter((entry) => entry && typeof entry === "object").slice(0, HARVEST_MAX).map(harvestOf),
      diagnostics: [],
      source: compact({ kind: "import", name: file && text(file.name, 200), bytes, digest: hash }),
    };
    return { assessment, source };
  };

  /** One FAIR-Checker metric response. Its native outcome is a score on its own 0-2 scale, which FAIR-Checker
      colours green, orange and red; `P.reading` reads it the same way. The response does not always repeat the
      metric, so the requested metric is the identity. */
  P.readFairChecker = function (metric, source, provider) {
    let data;
    try {
      data = JSON.parse(source);
    } catch (error) {
      throw coded("unreadable-response", "The response is not JSON.");
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) throw coded("unreadable-response", "The response is not a metric result.");
    const score = typeof data.score === "number" ? data.score : /^\d+$/.test(String(data.score)) ? Number(data.score) : NaN;
    if (!Number.isInteger(score) || score < 0 || score > provider.scoreMax) throw coded("unexpected-response", "The score is outside the metric's scale: " + String(data.score).slice(0, 40));
    const echoed = text(data.metric, 40);
    return compact({
      id: metric,
      native: String(score),
      score: { value: score, max: provider.scoreMax },
      recommendation: text(data.recommendation),
      comment: text(data.comment),
      time: text(data.eval_time, 40),
      target: text(data.target_uri, 2000),
      echoed: echoed && echoed !== metric ? echoed : null,
    });
  };

  /** A native outcome in the provider's own terms: F-UJI's FAIR level with its name and points, FAIR-Checker's score
      on its scale, or a verdict. */
  P.outcome = function (result, provider) {
    if (!result || result.error) return FG.t("selfcheck.providers.noResult");
    const parts = [];
    if (result.maturity != null && provider && provider.maturityMax) {
      parts.push(FG.t("selfcheck.providers.level", { n: result.maturity, max: provider.maturityMax, name: FG.t("selfcheck.providers.levelName." + Math.min(result.maturity, 3)) }));
    } else if (result.score && result.score.value != null) {
      parts.push(FG.t("selfcheck.providers.nativeScore", { score: FG.formatNumber(result.score.value), max: result.score.max || (provider && provider.scoreMax) ? FG.formatNumber(result.score.max || provider.scoreMax) : "?" }));
    } else if (result.verdict || result.native) parts.push(result.verdict ? FG.t("selfcheck.champion." + result.verdict) : result.native);
    if (result.score && result.score.total != null) parts.push(FG.t("selfcheck.providers.nativeEarned", { earned: FG.formatNumber(result.score.earned), total: FG.formatNumber(result.score.total) }));
    return parts.join(" · ");
  };

  /** Whether the report's own status differs from the reading the provider's overview shows, as F-UJI's test status
      can for a metric it shows as passed. */
  P.statusDiffers = (result) => Boolean(result && result.native && result.maturity != null && (result.native === "pass") !== (result.verdict === "pass"));

  /** How far a native outcome establishes what its criterion checks, read as the provider presents it: met at the top
      of its scale, partly met below the top, not met where the provider shows a failure, and open where it shows no
      result or an unknown. F-UJI shows level 0 as unknown; FAIR-Checker shows a score of 0 as a failure. */
  P.reading = function (result, provider) {
    if (!result || result.error) return "open";
    if (result.maturity != null && provider && provider.maturityMax) return result.maturity >= provider.maturityMax ? "met" : result.maturity >= 1 ? "partly" : "open";
    if (result.score && result.score.value != null && result.score.max) return result.score.value >= result.score.max ? "met" : result.score.value > 0 ? "partly" : "failed";
    return result.verdict === "pass" ? "met" : result.verdict === "fail" ? "failed" : "open";
  };

  /** Which visual state a native outcome takes: its verdict, the score's position on its own scale, or no result. */
  P.state = function (result) {
    if (!result || result.error) return "none";
    if (result.verdict) return result.verdict;
    if (result.score && result.score.value != null) return result.score.value >= result.score.max ? "top" : result.score.value > 0 ? "middle" : "bottom";
    return "indeterminate";
  };

  const versionText = (assessment) =>
    Object.entries(assessment.versions || {}).filter(([key]) => key !== "requested").map(([key, value]) => FG.t("selfcheck.providers.version." + key) + " " + value).join(", ") || FG.t("selfcheck.providers.versionUnknown");
  P.versionText = versionText;

  /** The suggestion one reading gives through a mapping (D-168): whole coverage answers as the reading; partial
      coverage answers Partly when its part is met, even in part, and No when it fails; an open reading answers nothing. */
  const suggestionOf = (reading, coverage) => (reading === "failed" ? "no" : reading === "open" ? null : coverage === "whole" && reading === "met" ? "yes" : "partly");

  /** The evidence an assessment gives one question through its reviewed mappings, read as the provider presents its
      results. Several mappings suggest what they agree on, Partly where they differ only in how much is met, and
      nothing where one fails and another does not; an unreviewed version suggests nothing. A score scale on which
      every metric scored nothing usually means the service read no metadata at all, so it decides nothing. The
      observation names the assessment instead of copying its native results. */
  P.evidence = function (item, rows, assessment) {
    const provider = P.provider(assessment.provider);
    const source = provider ? provider.name : assessment.provider;
    const parts = rows.map((row) => ({ row, result: FG.list(assessment.results).find((result) => result.id === row.metric) }));
    const usable = parts.filter((part) => part.result && !part.result.error);
    const notes = [];
    if (!usable.length) notes.push({ key: "selfcheck.note.providerUnavailable", params: { source } });
    if (!assessment.reviewed) notes.push({ key: "selfcheck.note.providerVersion", params: { source, version: versionText(assessment).slice(0, 280) } });
    const scored = FG.list(assessment.results).filter((result) => !result.error && result.score && result.score.value != null);
    const blank = Boolean(provider && provider.scoreMax) && scored.length > 1 && scored.every((result) => result.score.value === 0);
    if (blank && usable.length) notes.push({ key: "selfcheck.note.providerBlank", params: { source } });
    const readings = usable.map((part) => ({ part, reading: blank ? "open" : P.reading(part.result, provider) }));
    const suggested = readings.map(({ part, reading }) => suggestionOf(reading, part.row.coverage)).filter(Boolean);
    const agreed = !suggested.length ? null : suggested.every((value) => value === suggested[0]) ? suggested[0] : suggested.includes("no") ? null : "partly";
    const value = assessment.reviewed ? agreed : null;
    if (suggested.length && !agreed) notes.push({ key: "selfcheck.note.sourceConflict" });
    if (readings.some(({ reading }) => reading === "failed")) notes.push({ key: "selfcheck.note.providerFail", params: { source } });
    if (readings.some(({ part, reading }) => reading === "open" && part.result.maturity != null)) notes.push({ key: "selfcheck.note.providerUnknown", params: { source } });
    if (value && readings.some(({ part, reading }) => reading !== "open" && part.row.coverage !== "whole")) notes.push({ key: "selfcheck.note.partialCoverage" });
    for (const part of usable) notes.push({ key: "selfcheck.note.providerMapping", params: { provider: assessment.provider, metric: part.row.metric, question: item.identifier } });
    if (assessment.provider === "f-uji") notes.push({ key: "selfcheck.note.providerHarvest" });
    return {
      value,
      notes: notes.slice(0, 10),
      fields: usable.map((part) => ({ path: part.row.metric, values: [P.outcome(part.result, provider)] })),
      subject: assessment.target,
      representation: assessment.representation || null,
      coverage: rows.map((row) => row.metric + " (" + FG.t("selfcheck.providers.coverage." + row.coverage) + ")").join(", ").slice(0, 300),
      assessment: assessment.id,
      date: day(assessment.assessed) || assessment.retrieved,
    };
  };

  /** The mapping note behind a `providerMapping` note, in the current language. */
  P.mappingNote = function (params) {
    const criterion = params && P.criterion(params.provider, params.metric);
    const mapping = criterion && FG.refs(criterion, "hasPart").find((entity) => FG.id(entity.about) === "#item-" + params.question);
    const provider = P.provider(params && params.provider);
    const head = (provider ? provider.name : "") + " " + (params ? params.metric : "") + " (" + FG.t("selfcheck.providers.coverage." + ((mapping && mapping.mappingCoverage) || "partial")) + ")";
    return head.trim() + (mapping && mapping.description ? ": " + FG.text(mapping.description) : "");
  };

  /* ---------------------------------------------------------------- retained original reports */

  /** Original report text is kept once per digest, apart from the answers, so a large report never stops the answers
      from being saved. When the browser refuses to keep it, it stays for this page visit and the overview says so. */
  /* All retained reports together stay within this many characters, so the complete evidence download stays within
     the saved-result file limit and one report cannot exhaust the browser's storage for the answers. */
  const SOURCES_MAX = 4 * 1024 * 1024;
  const memory = new Map();
  /** A retained report's text, read from storage once per visit. */
  P.sourceText = function (digest) {
    if (!memory.has(digest)) {
      const stored = FG.storage.readSource ? FG.storage.readSource(digest) : null;
      if (!stored) return null;
      memory.set(digest, stored);
    }
    return memory.get(digest);
  };
  /** Keep a report for the visit and, where the browser allows it, in storage; answers are saved before this. */
  P.keepSource = function (digest, source) {
    memory.set(digest, source);
    const kept = FG.storage.writeSource ? FG.storage.writeSource(digest, source) : false;
    stored.set(digest, kept);
    return kept;
  };
  const stored = new Map();
  P.sourceKept = function (digest) {
    if (!stored.has(digest)) stored.set(digest, Boolean(FG.storage.readSource && FG.storage.readSource(digest)));
    return stored.get(digest);
  };
  const referenced = () => {
    const used = new Set();
    for (const entry of Object.values(FG.state.answers || {})) for (const assessment of FG.list(entry && entry.assessments)) if (assessment && assessment.source && assessment.source.digest) used.add(assessment.source.digest);
    return used;
  };
  /** The characters the referenced reports take, with one more of `extra` characters. */
  P.sourceRoom = (extra) => [...referenced()].reduce((sum, digest) => sum + (P.sourceText(digest) || "").length, 0) + (extra || 0) <= SOURCES_MAX;

  /** Forget every report this visit holds, as deleting all local data does. */
  P.forgetAll = function () {
    memory.clear();
    stored.clear();
    parsed.clear();
  };

  /** Forget original reports no check refers to any more. */
  P.pruneSources = function () {
    const used = referenced();
    for (const digest of [...memory.keys()]) if (!used.has(digest)) memory.delete(digest);
    for (const digest of [...stored.keys()]) if (!used.has(digest)) stored.delete(digest);
    if (FG.storage.pruneSources) FG.storage.pruneSources(used);
  };

  /* When the answers cannot be saved, the core drops retained reports from storage first; the page keeps them for
     the visit, and the overview then says so. */
  FG.keepSourcesForVisit = function () {
    for (const digest of referenced()) {
      P.sourceText(digest);
      stored.set(digest, false);
    }
  };

  /* ---------------------------------------------------------------- portable copies */

  /** A saved or loaded assessment, keeping only the shapes the guide writes; unknown native output stays in the
      original report, which travels in the complete evidence download. */
  P.readAssessment = function (data) {
    if (!data || typeof data !== "object" || !P.isAssessmentId(data.id) || !P.provider(data.provider) || !String(data.id).startsWith(data.provider + ":")) return null;
    /* An imported report's identity is its digest; a record naming another is refused. */
    if (data.provider === "f-uji" && (!data.source || data.id !== "f-uji:" + data.source.digest)) return null;
    /* F-UJI results are read again from their native fields, so a result saved under an earlier reading follows
       F-UJI's own. */
    const fuji = data.provider === "f-uji";
    const result = (entry) => entry && typeof entry === "object" && typeof entry.id === "string" && entry.id.length <= 100
      ? compact({ id: entry.id, name: text(entry.name), native: text(entry.native, 40), verdict: fuji ? fujiVerdict(number(entry.maturity), text(entry.native, 40)) : verdict(entry.verdict),
        score: entry.score && typeof entry.score === "object" ? compact({ earned: number(entry.score.earned), total: number(entry.score.total), value: number(entry.score.value), max: number(entry.score.max) }) : null,
        maturity: number(entry.maturity), subtests: FG.list(entry.subtests).slice(0, SUBTESTS_MAX).map((test) => test && typeof test === "object" ? compact({ id: text(test.id, 100), name: text(test.name), native: text(test.native, 40), verdict: fuji ? fujiSubtestVerdict(text(test.native, 40)) : verdict(test.verdict),
          score: test.score && typeof test.score === "object" ? compact({ earned: number(test.score.earned), total: number(test.score.total) }) : null, maturity: number(test.maturity) }) : null).filter((test) => test && test.id),
        recommendation: text(entry.recommendation), comment: text(entry.comment), time: text(entry.time, 40), target: text(entry.target, 2000), echoed: text(entry.echoed, 40),
        error: entry.error && typeof entry.error === "object" ? compact({ code: text(entry.error.code, 80) || "unavailable", message: text(entry.error.message, 500) }) : null })
      : null;
    const versions = {};
    for (const [key, value] of Object.entries(data.versions || {}).slice(0, 8)) if (!FG.unsafeKey(key) && /^[a-z]{2,20}$/.test(key) && text(value, 300)) versions[key] = text(value, 300);
    const provider = P.provider(data.provider);
    return compact({
      id: data.id,
      provider: data.provider,
      target: text(data.target, 2000),
      subject: text(data.subject, 2000),
      representation: web(data.representation),
      assessed: text(data.assessed, 40),
      retrieved: day(data.retrieved) || today(),
      report: text(data.report, 100),
      versions,
      reviewed: P.reviewed(provider, versions),
      total: number(data.total),
      results: FG.list(data.results).slice(0, RESULTS_MAX).map(result).filter(Boolean),
      harvest: FG.list(data.harvest).slice(0, HARVEST_MAX).map((entry) => entry && typeof entry === "object" ? compact({ method: text(entry.method, 80), url: web(entry.url), format: text(entry.format, 80), schema: text(entry.schema, 300),
        licence: FG.list(entry.licence).map((value) => text(value, 500)).filter(Boolean).slice(0, 10), access: FG.list(entry.access).map((value) => text(value, 500)).filter(Boolean).slice(0, 10), identifier: FG.list(entry.identifier).map((value) => text(value, 500)).filter(Boolean).slice(0, 10) }) : null).filter(Boolean),
      diagnostics: FG.list(data.diagnostics).slice(0, 20).map((entry) => entry && typeof entry === "object" ? compact({ code: text(entry.code, 80) || "unavailable", metric: text(entry.metric, 100), message: text(entry.message, 500) }) : null).filter(Boolean),
      /* A record read from a file is a claim until its original report is verified against the digest. */
      source: data.source && typeof data.source === "object" ? compact({ kind: data.source.kind === "import" ? "import" : "service", name: text(data.source.name, 200), bytes: number(data.source.bytes), digest: /^sha256-[0-9a-f]{64}$/.test(String(data.source.digest || "")) ? data.source.digest : null, unverified: true }) : { kind: "service", unverified: true },
    });
  };

  /** Replace claimed records with the ones their verified original reports give, keeping verified reports only.
      A report is verified when its SHA-256 digest equals the identity the record names. */
  P.verifySources = async function (state, sources) {
    if (!sources || typeof sources !== "object" || Array.isArray(sources)) sources = {};
    let verified = 0;
    const list = FG.list(state.assessments);
    for (const [index, assessment] of list.entries()) {
      const digest = assessment.source && assessment.source.digest;
      /* A report this browser already keeps was verified when it was kept, and it is the truth for its digest. */
      const source = digest && Object.prototype.hasOwnProperty.call(sources, digest) ? sources[digest] : digest ? P.sourceText(digest) : null;
      if (typeof source !== "string" || source.length > P.settings().maxImportBytes || (await P.digest(source)) !== digest) continue;
      const read = await P.readFuji(source, { name: assessment.source.name });
      if (read.error || read.assessment.id !== assessment.id) continue;
      read.assessment.retrieved = assessment.retrieved || read.assessment.retrieved;
      list[index] = read.assessment;
      P.keepSource(digest, source);
      verified += 1;
    }
    return verified;
  };

  /** The portable copy of a check's assessments: native results without logs, which stay in the retained report. */
  P.portable = (st) => FG.list(st.assessments).slice(0, ASSESSMENTS_MAX).map((assessment) => Object.assign({}, assessment, { results: FG.list(assessment.results).map((result) => Object.assign({}, result, { log: undefined })) }));

  /* ---------------------------------------------------------------- self-check controls */

  SC.providersFactory = function (dependencies) {
    const { h, stateOf, applyEvidence, save, setStatus, observationsOf, jumpToItem, inBatches, retarget } = dependencies;
    const runs = new Map();
    const previews = new Map();

    const targetOf = (st) => st.target || (st.pid && FG.live.parsePid(st.pid) ? FG.live.pidUrl(FG.live.parsePid(st.pid)) : null);
    const assessmentsOf = (st) => (Array.isArray(st.assessments) ? st.assessments : []);
    const providerName = (id) => (P.provider(id) || { name: id }).name;

    /** Put an assessment's evidence on the questions its mappings name; answers the reader gave stay theirs. */
    function applyAssessment(check, assessment) {
      const provider = P.provider(assessment.provider);
      const byQuestion = new Map();
      for (const row of P.mappings(provider)) byQuestion.set(row.question, (byQuestion.get(row.question) || []).concat(row));
      return applyEvidence(check, assessment.provider, (item) => (byQuestion.has(item.identifier) ? P.evidence(item, byQuestion.get(item.identifier), assessment) : null), day(assessment.assessed) || assessment.retrieved, null, true);
    }

    /** Remove one assessment and only what it contributed: its observations, and suggestions that rested on it alone.
        Answers the reader gave or changed stay, as does every other source's evidence. */
    function withdraw(check, id) {
      const st = stateOf(check);
      st.assessments = assessmentsOf(st).filter((assessment) => assessment.id !== id);
      if (!st.assessments.length) delete st.assessments;
      for (const [question, entry] of Object.entries(st.items)) {
        if (!entry || typeof entry !== "object" || !observationsOf(entry).some((seen) => seen.assessment === id)) continue;
        const observations = observationsOf(entry).filter((seen) => seen.assessment !== id);
        const supported = observations.filter((seen) => seen.value);
        const prefill = supported[supported.length - 1] || observations[observations.length - 1] || null;
        const next = Object.assign({}, entry, { observations });
        if (prefill) next.prefill = prefill;
        else delete next.prefill;
        if (entry.origin === "prefill") {
          if (prefill && prefill.value) next.value = prefill.value;
          else {
            delete next.value;
            delete next.origin;
          }
        }
        if (!observations.length) delete next.observations;
        if (!next.value && !next.prefill && !next.origin) delete st.items[question];
        else st.items[question] = next;
      }
      save();
      P.pruneSources();
    }

    /** Attach an assessment, replacing a record with the same identity; an assessment beyond the limit is
        withdrawn with its evidence rather than left behind as observations without a record. */
    function keep(check, assessment) {
      const st = stateOf(check);
      const others = assessmentsOf(st).filter((entry) => entry.id !== assessment.id);
      const surplus = others.slice(0, Math.max(0, others.length + 1 - ASSESSMENTS_MAX));
      for (const old of surplus) withdraw(check, old.id);
      st.assessments = assessmentsOf(st).filter((entry) => entry.id !== assessment.id).concat(assessment);
      const count = applyAssessment(check, assessment);
      save();
      return count;
    }

    /* ------------------------------------------------ FAIR-Checker */

    /** Run the provider's metrics on the check's target, a few at a time. A run whose target or check state changes
        before it ends is discarded whole, so a late result never attaches to another object. A retry asks again
        only for the metrics of the chosen assessment that gave no result. */
    async function runService(check, retryId) {
      const provider = P.provider("fair-checker");
      const st = stateOf(check);
      const target = targetOf(st);
      if (!provider || !target) {
        setStatus(check, FG.t("selfcheck.providers.needTarget"));
        return;
      }
      if (runs.has(check.identifier)) return;
      const previous = retryId ? assessmentsOf(st).find((entry) => entry.id === retryId && P.sameTarget(entry.target, target)) : null;
      if (retryId && !previous) return;
      const assessment = previous ? JSON.parse(JSON.stringify(previous)) : { id: "fair-checker:" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8), provider: provider.id, target, assessed: new Date().toISOString().slice(0, 19) + "Z", retrieved: today(), versions: {}, results: [], diagnostics: [], source: { kind: "service" } };
      const metrics = previous ? provider.metrics.filter((metric) => !assessment.results.some((result) => result.id === metric && !result.error)) : provider.metrics.slice();
      const token = {};
      runs.set(check.identifier, { token, target, total: metrics.length, done: 0 });
      const stale = () => !runs.has(check.identifier) || runs.get(check.identifier).token !== token || stateOf(check) !== st || targetOf(stateOf(check)) !== target;
      setStatus(check, FG.t("selfcheck.providers.running", { source: provider.name, n: metrics.length }));
      FG.rerender("provider-run-fair-checker");
      const options = { maxBytes: provider.maxBytes, timeoutSeconds: provider.timeoutSeconds, accept: "application/json" };
      if (!assessment.versions.api) {
        try {
          const description = await FG.live.fetchText(provider.connector, provider.versionPath, Object.assign({}, options, { maxBytes: 262144 }));
          const version = text((JSON.parse(description.text).info || {}).version, 40);
          if (version) assessment.versions.api = version;
        } catch (error) {
          assessment.diagnostics = FG.list(assessment.diagnostics).filter((entry) => entry.code !== "version").concat({ code: "version", message: String(error.message || error).slice(0, 500) });
        }
      }
      /* A run left behind by another target sends nothing further. */
      const tasks = metrics.map((metric) => async () => {
        if (stale()) return;
        let result;
        try {
          const path = provider.path.replace("{metric}", encodeURIComponent(metric)).replace("{target}", encodeURIComponent(target));
          const response = await FG.live.fetchText(provider.connector, path, options);
          result = P.readFairChecker(metric, response.text, provider);
        } catch (error) {
          result = { id: metric, error: compact({ code: error.code || (error.name === "AbortError" ? "timeout" : "unavailable"), message: String(error.message || error).slice(0, 500) }) };
        }
        if (stale()) return;
        assessment.results = assessment.results.filter((entry) => entry.id !== metric).concat(result);
        const run = runs.get(check.identifier);
        run.done += 1;
        const bar = document.getElementById("provider-progress");
        if (bar) {
          bar.max = run.total;
          bar.value = run.done;
        }
      });
      let lost = true;
      try {
        await inBatches(tasks, Math.min(4, provider.maxParallel || 1));
        lost = stale();
      } finally {
        if (runs.has(check.identifier) && runs.get(check.identifier).token === token) runs.delete(check.identifier);
      }
      if (lost) return;
      assessment.results.sort((a, b) => provider.metrics.indexOf(a.id) - provider.metrics.indexOf(b.id));
      assessment.reviewed = P.reviewed(provider, assessment.versions);
      assessment.retrieved = today();
      keep(check, assessment);
      const answered = assessment.results.filter((result) => !result.error).length;
      setStatus(check, FG.t("selfcheck.providers.ran", { source: provider.name, n: answered, total: provider.metrics.length }));
      FG.rerender("provider-overview-" + assessmentIndex(stateOf(check), assessment.id));
    }

    /** Leaving a check's target ends the run that was for it; the run's late answers are then ignored. */
    function forget(check) {
      runs.delete(check.identifier);
      previews.delete(check.identifier);
      refreshed.delete(check.identifier);
    }

    /* Suggestions follow the current reading of each attached assessment: once per visit, and again after answers are
       adopted from a file or link, every assessment is applied again. That replaces only its own observations, so the
       reader's answers stay theirs and a result saved under an earlier reading follows the current one. */
    const refreshed = new Set();
    function refresh(check) {
      if (refreshed.has(check.identifier)) return;
      refreshed.add(check.identifier);
      for (const assessment of assessmentsOf(stateOf(check))) applyAssessment(check, assessment);
    }

    /* ------------------------------------------------ F-UJI import */

    /** How a previewed report relates to the check as it is now: its target, a duplicate of a verified report, a
        historical report of the same assessment, and room among the retained reports. Recomputed at every use, so a
        target entered after the preview is respected. */
    function relation(check, read) {
      const st = stateOf(check);
      const target = targetOf(st);
      const existing = assessmentsOf(st).find((entry) => entry.id === read.assessment.id);
      return {
        target,
        mismatch: Boolean(target) && !P.sameTarget(target, read.assessment.target),
        /* Only a record with its verified original blocks an import; a claimed record is replaced by the real one. */
        duplicate: Boolean(existing) && !existing.source.unverified && Boolean(P.sourceText(read.assessment.source.digest)),
        historical: assessmentsOf(st).filter((entry) => entry.provider === "f-uji" && entry.id !== read.assessment.id && entry.report && entry.report === read.assessment.report).length,
        full: !existing && !P.sourceRoom(read.source.length),
      };
    }

    async function previewFile(check, file) {
      const settings = P.settings();
      if (!file) return;
      if (file.size > settings.maxImportBytes) {
        previews.set(check.identifier, { error: "tooLarge", params: { size: String(file.size), max: String(settings.maxImportBytes) } });
        FG.rerender("provider-import-fuji");
        return;
      }
      const source = await file.text();
      const read = await P.readFuji(source, file);
      previews.set(check.identifier, read.error ? read : Object.assign(read, relation(check, read)));
      FG.rerender("provider-import-fuji");
    }

    function attach(check) {
      const preview = previews.get(check.identifier);
      if (!preview || preview.error) return;
      Object.assign(preview, relation(check, preview));
      if (preview.mismatch || preview.duplicate || preview.full) {
        FG.rerender("provider-import-fuji");
        return;
      }
      const st = stateOf(check);
      previews.delete(check.identifier);
      if (!targetOf(st)) {
        const pid = FG.live.parsePid(preview.assessment.target);
        if (pid) st.pid = pid.value;
        retarget(check, pid ? FG.live.pidUrl(pid) : web(preview.assessment.target));
      }
      /* The answers are saved first; the report is kept afterwards, within the room the answers leave. */
      const count = keep(check, preview.assessment);
      const kept = P.keepSource(preview.assessment.source.digest, preview.source);
      setStatus(check, FG.t(kept ? "selfcheck.providers.attached" : "selfcheck.providers.attachedSession", { source: providerName("f-uji"), n: count }));
      /* The confirmation stands in the evaluator's own card, where the reader loaded the report. */
      FG.rerender(document.querySelector(".check-evidence") ? "provider-attached-f-uji" : "provider-overview-" + assessmentIndex(stateOf(check), preview.assessment.id));
    }

    const assessmentIndex = (st, id) => Math.max(0, assessmentsOf(st).findIndex((entry) => entry.id === id));

    /** In an evaluator's own card, what of it the check holds: its latest attached result, when it was assessed,
        how many metrics it has and how many questions it suggested answers for, with the way to those answers and to
        the report, where every run's details are. */
    function attachedLine(check, providerId) {
      const st = stateOf(check);
      const list = assessmentsOf(st).filter((entry) => entry.provider === providerId);
      if (!list.length) return null;
      const latest = list[list.length - 1];
      const suggested = Object.values(st.items || {}).filter((entry) => observationsOf(entry).some((observation) => observation.source === providerId && observation.value)).length;
      const base = FG.href("check", check.identifier);
      return h(
        "div",
        { class: "attached", id: "provider-attached-" + providerId, tabindex: "-1", role: "status" },
        h("p", null, FG.icon("met"), " ", h("strong", null, FG.t("selfcheck.providers.attachedTitle", { n: list.length }))),
        h("p", { class: "small" }, FG.t("selfcheck.providers.attachedFacts", {
          date: latest.assessed ? FG.formatDate(day(latest.assessed)) : FG.t("selfcheck.providers.unknown"),
          metrics: latest.results.length,
          n: suggested,
        })),
        h("p", { class: "small" }, h("a", { href: base + "/answers" }, FG.t("selfcheck.providers.toAnswers")), " · ", h("a", { href: base + "/report" }, FG.t("selfcheck.providers.toReport")))
      );
    }

    function previewPanel(check) {
      const preview = previews.get(check.identifier);
      if (!preview) return null;
      const discard = h("button", { type: "button", class: "button-small", id: "provider-import-discard", onclick: () => { previews.delete(check.identifier); FG.rerender("provider-import-fuji"); } }, FG.t("selfcheck.providers.discard"));
      if (preview.error) return h("div", { class: "import-preview", role: "alert" }, h("p", null, FG.t("selfcheck.providers.importError." + preview.error, preview.params || {})), discard);
      const assessment = preview.assessment;
      const provider = P.provider(assessment.provider);
      const rows = [
        ["object", web(assessment.target) ? FG.external(assessment.target, assessment.target) : assessment.target],
        ["assessed", assessment.assessed ? FG.formatDate(day(assessment.assessed)) + " (" + assessment.assessed + ")" : FG.t("selfcheck.providers.unknown")],
        ["versions", versionText(assessment)],
        assessment.versions.specification ? ["specification", FG.external(assessment.versions.specification, assessment.versions.specification)] : null,
        ["report", assessment.report || FG.t("selfcheck.providers.unknown")],
        ["file", [assessment.source.name || "", " · ", FG.t("selfcheck.providers.bytes", { n: assessment.source.bytes }), " · ", h("code", null, assessment.source.digest.slice(0, 22) + "…")]],
        ["metrics", String(assessment.results.length) + (assessment.total != null && assessment.total !== assessment.results.length ? " / " + assessment.total : "")],
      ].filter(Boolean);
      const notices = [
        assessment.reviewed ? FG.t("selfcheck.providers.reviewedVersion") : FG.t("selfcheck.providers.unreviewedVersion", { source: provider.name }),
        preview.mismatch ? FG.t("selfcheck.providers.mismatch", { report: assessment.target, target: preview.target }) : null,
        !preview.target ? FG.t("selfcheck.providers.adoptTarget") : null,
        preview.duplicate ? FG.t("selfcheck.providers.duplicate") : null,
        preview.full ? FG.t("selfcheck.providers.full") : null,
        preview.historical ? FG.t("selfcheck.providers.historical") : null,
      ].filter(Boolean);
      return h(
        "div",
        { class: "import-preview", "aria-labelledby": "import-preview-title" },
        h("p", { class: "import-read", role: "status" }, FG.icon("info"), " ", FG.t("selfcheck.providers.previewRead", { source: provider.name, n: assessment.results.length })),
        h("h4", { id: "import-preview-title" }, FG.t("selfcheck.providers.previewTitle", { source: provider.name })),
        h("dl", { class: "relations import-facts" }, rows.map(([key, value]) => [h("dt", null, FG.t("selfcheck.providers.fact." + key)), h("dd", null, value)])),
        notices.map((notice, index) => h("p", { class: index && (preview.mismatch || preview.duplicate || preview.full) ? "notice small" : "small" }, notice)),
        h("div", { class: "buttons" },
          h("button", { type: "button", class: "button-small button-primary", id: "provider-import-attach", disabled: preview.mismatch || preview.duplicate || preview.full || null, onclick: () => attach(check) }, FG.t("selfcheck.providers.attach")),
          discard)
      );
    }

    /* ------------------------------------------------ evaluation choices */

    /** Every evaluator the check offers, with what it assesses, what it is sent and where, and an explicit choice.
        Nothing is called on entry, while typing, on quick lookup or on preview. */
    function panel(check, st, questions) {
      const settings = P.settings();
      const active = new Set(questions.map((item) => item.identifier));
      const offered = FG.list(settings.list).filter((provider) => P.mappings(provider).some((mapping) => active.has(mapping.question)));
      if (!offered.length) return null;
      const target = targetOf(st);
      const running = runs.has(check.identifier);
      const fairChecker = offered.find((provider) => provider.id === "fair-checker");
      const fuji = offered.find((provider) => provider.id === "f-uji");
      const host = (provider) => {
        try {
          return new URL(FG.live.origin(provider.connector)).host;
        } catch (error) {
          return provider.name;
        }
      };
      const links = (provider) => [FG.external(provider.form, FG.t("selfcheck.providers.openForm", { source: provider.name })),
        provider.documentation ? [" · ", FG.external(provider.documentation, FG.t("selfcheck.providers.documentation"))] : null,
        provider.terms ? [" · ", FG.external(provider.terms, FG.t("selfcheck.providers.terms"))] : null];
      const input = h("input", { type: "file", id: "provider-import-fuji", class: "file-input", accept: ".json,application/json", onchange: (event) => previewFile(check, event.target.files[0]) });
      /* The panel fills the evaluators' evidence card, which carries its heading. */
      return h(
        "div",
        { class: "evaluators no-print" },
        h("p", { class: "small" }, FG.t("selfcheck.providers.intro")),
        h("details", { class: "flow-details" }, h("summary", null, FG.t("visual.evidence.title")), h("div", { class: "content" }, P.flow())),
        target
          ? h("p", { class: "evaluator-target small" }, FG.t("selfcheck.providers.sent") + " ", h("code", { id: "evaluator-target" }, target), " ",
            h("button", { type: "button", class: "button-small", id: "evaluator-target-copy", onclick: (event) => FG.copyText(event, target, "evaluator-target") }, FG.icon("copy"), h("span", { class: "copy-label" }, FG.t("common.copy"))))
          : h("p", { class: "small muted" }, FG.t("selfcheck.providers.needTarget")),
        h(
          "ul",
          { class: "evaluator-choices" },
          fairChecker
            ? h("li", { id: "evaluator-fair-checker" },
              h("p", { class: "evaluator-name" }, evaluatorBadge(fairChecker), h("span", null, h("strong", null, fairChecker.name), " · ", FG.t("selfcheck.providers.fairCheckerScope", { n: fairChecker.metrics.length }))),
              h("p", { class: "small" }, FG.t("selfcheck.providers.fairCheckerSends", { host: host(fairChecker), n: fairChecker.metrics.length, parallel: fairChecker.maxParallel })),
              h("p", { class: "buttons" },
                h("button", { type: "button", class: "button-small", id: "provider-run-fair-checker", disabled: !target || running || null, onclick: () => runService(check) },
                  running ? FG.t("selfcheck.providers.runningShort") : FG.t("selfcheck.providers.run", { source: fairChecker.name }))),
              running ? h("progress", { id: "provider-progress", max: runs.get(check.identifier).total, value: runs.get(check.identifier).done, "aria-label": FG.t("selfcheck.providers.progress") }) : null,
              attachedLine(check, "fair-checker"),
              h("p", { class: "small" }, links(fairChecker)))
            : null,
          fuji
            ? h("li", { id: "evaluator-f-uji" },
              h("p", { class: "evaluator-name" }, evaluatorBadge(fuji), h("span", null, h("strong", null, fuji.name), " · ", FG.t("selfcheck.providers.fujiScope"))),
              h("p", { class: "small" }, FG.t("selfcheck.providers.fujiSteps", { max: FG.t("selfcheck.providers.megabytes", { n: Math.round(settings.maxImportBytes / 1048576) }) })),
              h("p", { class: "buttons" }, input, h("label", { for: "provider-import-fuji", class: "button button-small" }, FG.icon("upload"), FG.t("selfcheck.providers.load", { source: fuji.name }))),
              previewPanel(check),
              attachedLine(check, "f-uji"),
              h("p", { class: "small" }, links(fuji)))
            : null
        )
      );
    }

    /* ------------------------------------------------ assessment overview */

    const PRINCIPLE_LETTERS = ["F", "A", "I", "R"];

    /** The questions of this check a criterion relates to, each leading to the question. */
    function questionLinks(check, st, assessment, metric) {
      const rows = P.mappings(P.provider(assessment.provider)).filter((row) => row.metric === metric);
      const items = FG.refs(check, "hasPart");
      const linked = rows.map((row) => ({ row, item: items.find((item) => item.identifier === row.question) })).filter((entry) => entry.item);
      if (!linked.length) return h("p", { class: "small muted criterion-questions" }, FG.t("selfcheck.providers.unmapped"));
      return h("p", { class: "small criterion-questions" }, FG.t("selfcheck.providers.relates") + ": ",
        linked.map(({ row, item }, index) => [index ? ", " : "",
          h("button", { type: "button", class: "id-chip", onclick: () => jumpToItem(check, item) }, item.identifier),
          " (" + FG.t("selfcheck.providers.coverage." + row.coverage) + ")"]));
    }

    function criterionCard(check, st, assessment, result) {
      const provider = P.provider(assessment.provider);
      const criterion = P.criterion(assessment.provider, result.id);
      const state = P.state(result);
      const name = result.name || (criterion && FG.text(criterion.name)) || "";
      const log = result.log || P.nativeLog(assessment, result.id);
      const details = [
        FG.list(result.subtests).length
          ? h("table", { class: "data-table subtests" }, h("caption", { class: "visually-hidden" }, FG.t("selfcheck.providers.subtests", { id: result.id })),
            h("thead", null, h("tr", null, ["subtest", "outcome"].map((key) => h("th", { scope: "col" }, FG.t("selfcheck.providers.column." + key))))),
            h("tbody", null, result.subtests.map((test) => h("tr", null, h("th", { scope: "row" }, h("span", { class: "id-chip id-chip-static" }, test.id), test.name ? [" ", h("span", { lang: "en" }, test.name)] : null),
              h("td", { "data-verdict": P.state(test) }, h("span", { "aria-hidden": "true" }, (P.ICON[P.state(test)] || "?") + " "), P.outcome(test, provider))))))
          : null,
        result.recommendation ? [h("p", { class: "small" }, h("strong", null, FG.t("selfcheck.providers.recommendation") + ": ")), h("pre", { class: "provider-text", lang: "en", tabindex: "0", role: "region", "aria-label": FG.t("selfcheck.providers.recommendation") }, result.recommendation)] : null,
        result.comment ? [h("p", { class: "small" }, h("strong", null, FG.t("selfcheck.providers.comment") + ": ")), h("pre", { class: "provider-text", lang: "en", tabindex: "0", role: "region", "aria-label": FG.t("selfcheck.providers.comment") }, result.comment)] : null,
        log ? h("details", { class: "probe-log" }, h("summary", null, FG.t("selfcheck.evidence.originalLog")), h("div", { class: "content" }, h("pre", { tabindex: "0", role: "region", "aria-label": FG.t("selfcheck.evidence.originalLog"), lang: "en" }, log))) : null,
        result.error ? h("p", { class: "probe-error small" }, FG.t("selfcheck.evidence.requestError") + ": ", result.error.message || result.error.code) : null,
        P.statusDiffers(result) ? h("p", { class: "small" }, FG.t("selfcheck.providers.statusDiffers", { status: result.native, source: provider.name })) : null,
        result.echoed ? h("p", { class: "small" }, FG.t("selfcheck.providers.echoed", { metric: result.echoed })) : null,
        result.time ? h("p", { class: "small muted" }, FG.t("selfcheck.providers.time", { time: result.time })) : null,
        criterion && criterion.url ? h("p", { class: "small test-invocation" }, FG.external(criterion.url, FG.t(provider.mode === "service" ? "selfcheck.evidence.endpoint" : "selfcheck.providers.form"))) : null,
      ].filter(Boolean);
      return h("li", { class: "criterion", "data-verdict": state },
        h("p", { class: "criterion-head" },
          h("span", { class: "criterion-outcome", "data-verdict": state }, h("span", { "aria-hidden": "true" }, (P.ICON[state] || "?") + " "), P.outcome(result, provider)),
          " ", h("strong", null, criterion ? FG.text(criterion.alternateName) || name : name), " ",
          criterion ? FG.idChip(criterion) : h("span", { class: "id-chip id-chip-static" }, result.id)),
        name ? h("p", { class: "small muted criterion-name", lang: "en" }, name) : null,
        questionLinks(check, st, assessment, result.id),
        details.length ? h("details", { class: "evidence-details" }, h("summary", null, FG.t("selfcheck.providers.native")), h("div", { class: "content" }, details)) : null);
    }

    function download(check, assessment) {
      const source = assessment.source && assessment.source.digest ? P.sourceText(assessment.source.digest) : null;
      const name = "fair-self-check-" + check.identifier + "-" + assessment.provider + "-" + (day(assessment.assessed) || today()) + ".json";
      const body = source || JSON.stringify(assessment, null, 2) + "\n";
      FG.download(name, body, "application/json");
    }

    function assessmentSection(check, st, assessment, index, own) {
      const provider = P.provider(assessment.provider);
      if (!provider) return null;
      const unresolved = provider.mode === "service" ? provider.metrics.filter((metric) => !assessment.results.some((result) => result.id === metric && !result.error)) : [];
      const answered = assessment.results.filter((result) => !result.error).length;
      const stored = assessment.source.digest ? P.sourceKept(assessment.source.digest) : true;
      const available = assessment.source.digest ? Boolean(P.sourceText(assessment.source.digest)) : true;
      const byLetter = new Map(PRINCIPLE_LETTERS.map((letter) => [letter, []]));
      const other = [];
      for (const result of assessment.results) {
        const criterion = P.criterion(assessment.provider, result.id);
        const letter = criterion ? String((FG.get(criterion.about) || {}).termCode || "").charAt(0) : String(result.id).replace(/^FsF-/, "").charAt(0);
        (byLetter.get(letter) || other).push(result);
      }
      const title = provider.name + " · " + (assessment.assessed ? FG.formatDate(day(assessment.assessed)) : "");
      return h(
        "section",
        { class: "assessment", id: "provider-overview-" + index, tabindex: "-1", "aria-labelledby": "assessment-title-" + index },
        h("h4", { id: "assessment-title-" + index, class: "evaluator-name" }, evaluatorBadge(provider, assessment.provider), h("span", null, title)),
        h("dl", { class: "relations assessment-facts small" },
          h("dt", null, FG.t("selfcheck.providers.fact.object")), h("dd", null, web(assessment.target) ? FG.external(assessment.target, assessment.target) : assessment.target),
          assessment.representation ? [h("dt", null, FG.t("selfcheck.providers.fact.representation")), h("dd", null, FG.external(assessment.representation, assessment.representation))] : null,
          h("dt", null, FG.t("selfcheck.providers.fact.versions")), h("dd", null, versionText(assessment), " · ",
            h("span", { class: "badge", "data-reviewed": String(Boolean(assessment.reviewed)) }, FG.t(assessment.reviewed ? "selfcheck.providers.reviewedShort" : "selfcheck.providers.unreviewedShort"))),
          assessment.report ? [h("dt", null, FG.t("selfcheck.providers.fact.report")), h("dd", null, h("code", null, assessment.report))] : null,
          h("dt", null, FG.t("selfcheck.providers.fact.coverage")), h("dd", null, FG.t("selfcheck.providers.answered", { n: answered, total: provider.mode === "service" ? provider.metrics.length : assessment.results.length }))),
        assessment.provider === "f-uji" ? h("p", { class: "small" }, FG.t("selfcheck.providers.harvested", { date: assessment.assessed ? FG.formatDate(day(assessment.assessed)) : "" })) : null,
        FG.list(assessment.harvest).length
          ? h("details", { class: "evidence-details" }, h("summary", null, FG.t("selfcheck.providers.harvestTitle", { n: assessment.harvest.length })),
            h("div", { class: "content" }, h("ul", { class: "harvest-list" }, assessment.harvest.map((entry) => h("li", null,
              h("p", null, h("code", null, entry.method || "?"), entry.url ? [" · ", FG.external(entry.url, entry.url)] : null, entry.format ? " · " + entry.format : null),
              ["licence", "access", "identifier"].filter((key) => FG.list(entry[key]).length).map((key) => h("p", { class: "small" }, FG.t("selfcheck.providers.statement." + key) + ": ", entry[key].join(" | ")))))),
              h("p", { class: "small muted" }, FG.t("selfcheck.providers.statementScope"))))
          : null,
        own && unresolved.length && answered < provider.metrics.length
          ? h("p", { class: "buttons" }, h("button", { type: "button", class: "button-small", id: "provider-retry-" + index, disabled: runs.has(check.identifier) || !P.sameTarget(assessment.target, targetOf(st)) || null, onclick: () => runService(check, assessment.id) }, FG.t("selfcheck.providers.retry", { n: unresolved.length })))
          : null,
        h("div", { class: "assessment-groups" },
          [...byLetter.entries()].filter(([, results]) => results.length).map(([letter, results]) => h("section", { class: "assessment-group" },
            h("h5", null, h("span", { class: "principle-letter", "data-letter": letter }, letter), " ", FG.t("explorer.group." + letter)),
            h("ul", { class: "criteria" }, results.map((result) => criterionCard(check, st, assessment, result))))),
          other.length ? h("section", { class: "assessment-group" }, h("h5", null, FG.t("selfcheck.groupOther")), h("ul", { class: "criteria" }, other.map((result) => criterionCard(check, st, assessment, result)))) : null),
        h("p", { class: "small" }, FG.t("selfcheck.providers.noScore")),
        assessment.source.unverified ? h("p", { class: "notice small" }, FG.t("selfcheck.providers.unverified")) : null,
        assessment.source.digest && !available && !assessment.source.unverified ? h("p", { class: "notice small" }, FG.t("selfcheck.providers.sourceMissing")) : null,
        assessment.source.digest && available && !stored ? h("p", { class: "notice small" }, FG.t("selfcheck.providers.sourceSession")) : null,
        h("p", { class: "buttons no-print" },
          h("button", { type: "button", class: "button-small", id: "provider-download-" + index, onclick: () => download(check, assessment) }, FG.icon("download"),
            FG.t(assessment.source.digest && available ? "selfcheck.providers.downloadOriginal" : "selfcheck.providers.downloadRecord")),
          own ? h("button", { type: "button", class: "button-small", id: "provider-remove-" + index, onclick: () => {
            if (!window.confirm(FG.t("selfcheck.providers.removeConfirm", { source: provider.name }))) return;
            withdraw(check, assessment.id);
            setStatus(check, FG.t("selfcheck.providers.removed", { source: provider.name }));
            FG.rerender("results-title");
          } }, FG.t("selfcheck.providers.remove")) : null)
      );
    }

    /** The assessments of the check's own state, with their controls; a preview of a shared or loaded result shows
        the same overview without controls that would change the reader's own answers. */
    function overview(check, st) {
      const list = assessmentsOf(st);
      if (!list.length) return null;
      const own = FG.state.answers[check.identifier] === st;
      return [
        h("h3", { id: "results-assessments", tabindex: "-1" }, FG.t("selfcheck.providers.overview")),
        h("p", { class: "small muted" }, FG.t("selfcheck.providers.overviewIntro")),
        list.map((assessment, index) => assessmentSection(check, st, assessment, index, own)),
      ];
    }

    /* ------------------------------------------------ exports */

    function markdownLines(check, st, escape) {
      const list = assessmentsOf(st);
      if (!list.length) return [];
      const lines = ["", "## " + FG.t("selfcheck.providers.overview"), "", escape(FG.t("selfcheck.providers.overviewIntro")), ""];
      for (const assessment of list) {
        const provider = P.provider(assessment.provider) || { name: assessment.provider };
        lines.push("### " + escape(provider.name + " · " + (assessment.assessed || assessment.retrieved)), "");
        lines.push("- " + escape(FG.t("selfcheck.providers.fact.object") + ": " + assessment.target));
        if (assessment.representation) lines.push("- " + escape(FG.t("selfcheck.providers.fact.representation") + ": " + assessment.representation));
        lines.push("- " + escape(FG.t("selfcheck.providers.fact.versions") + ": " + versionText(assessment) + " (" + FG.t(assessment.reviewed ? "selfcheck.providers.reviewedShort" : "selfcheck.providers.unreviewedShort") + ")"));
        if (assessment.report) lines.push("- " + escape(FG.t("selfcheck.providers.fact.report") + ": " + assessment.report));
        if (assessment.source.digest) lines.push("- " + escape(FG.t("selfcheck.providers.fact.file") + ": " + [assessment.source.name, assessment.source.bytes != null ? assessment.source.bytes + " B" : null, assessment.source.digest].filter(Boolean).join(", ")));
        lines.push("");
        for (const result of assessment.results) {
          const criterion = P.criterion(assessment.provider, result.id);
          const linked = P.mappings(provider).filter((row) => row.metric === result.id).map((row) => row.question + " (" + FG.t("selfcheck.providers.coverage." + row.coverage) + ")");
          lines.push("- **" + escape(result.id) + "** " + escape((criterion && FG.text(criterion.alternateName)) || result.name || "") + ": " + escape(P.outcome(result, provider)) + (linked.length ? " · " + escape(linked.join(", ")) : " · " + escape(FG.t("selfcheck.providers.unmapped"))));
          for (const test of FG.list(result.subtests)) lines.push("  - " + escape(test.id + ": " + P.outcome(test, provider)));
        }
        lines.push("", escape(FG.t("selfcheck.providers.noScore")), "");
      }
      lines.push(escape(FG.t("selfcheck.providers.exportScope")), "");
      return lines;
    }

    /** Native results as FTR test results: a verdict where the provider gives one, its own score otherwise. */
    function crateMembers(check, st, target) {
      const members = [];
      const activities = [];
      const tests = [];
      for (const [index, assessment] of assessmentsOf(st).entries()) {
        const provider = P.provider(assessment.provider) || { name: assessment.provider };
        for (const result of assessment.results) {
          const criterion = P.criterion(assessment.provider, result.id);
          const testId = (criterion && criterion.url) || provider.form || ("#criterion-" + assessment.provider + "-" + result.id);
          members.push({
            "@id": "#provider-" + index + "-" + result.id,
            "@type": ["CreativeWork", "TestResult"],
            name: provider.name + " " + result.id,
            "prov:value": result.verdict || undefined,
            "ftr:log": [P.outcome(result, provider), result.recommendation, result.comment].filter(Boolean).join("\n"),
            "ftr:outputFromTest": { "@id": testId },
            "ftr:assessmentTarget": assessment.target ? { "@id": web(assessment.target) || assessment.target } : target,
            "prov:wasGeneratedBy": { "@id": "#provider-run-" + index },
          });
          tests.push({ "@id": testId, "@type": "CreativeWork", additionalType: { "@id": FG.config.vocab.ftr + (provider.mode === "service" ? "Test" : "Metric") }, identifier: result.id, name: result.name || (criterion && FG.text(criterion.name)) || result.id });
        }
        activities.push({ "@id": "#provider-run-" + index, "@type": ["Action", "TestExecutionActivity"], name: provider.name, endTime: assessment.assessed || assessment.retrieved, object: assessment.target ? { "@id": web(assessment.target) || assessment.target } : target, instrument: { "@id": provider.form }, description: versionText(assessment) });
        tests.push({ "@id": provider.form, "@type": "CreativeWork", name: provider.name });
      }
      return { members, activities, tests };
    }

    /** Restore the original reports a complete evidence file carries: only reports whose digest matches the record
        that names them, within the retained-report room, each record then rebuilt from its verified report. */
    async function restoreSources(state, sources) {
      if (!sources || typeof sources !== "object" || Array.isArray(sources)) sources = {};
      const room = {};
      let total = 0;
      for (const assessment of FG.list(state.assessments)) {
        const digest = assessment.source && assessment.source.digest;
        const source = digest && Object.prototype.hasOwnProperty.call(sources, digest) ? sources[digest] : null;
        if (typeof source !== "string" || total + source.length > SOURCES_MAX) continue;
        total += source.length;
        room[digest] = source;
      }
      return P.verifySources(state, room);
    }

    function sources(st) {
      const out = {};
      for (const assessment of assessmentsOf(st)) {
        const digest = assessment.source && assessment.source.digest;
        const source = digest && P.sourceText(digest);
        if (source) out[digest] = source;
      }
      return out;
    }

    return { panel, overview, markdownLines, crateMembers, runService, forget, refresh, withdraw, restoreSources, sources, applyAssessment, previewFile, attach, running: (check) => runs.has(check.identifier) };
  };

  /* The marks of the answer states, so a provider's outcome reads like an answer: met, partly met, not met, unknown. */
  P.ICON = { pass: "✓", fail: "✗", indeterminate: "?", none: "–", top: "✓", middle: "◐", bottom: "✗" };
  /* The shared evidence-to-answer visual (content/ui.toml, visual.evidence). */
  P.flow = () => FG.flow("evidence");
  /* Reports left behind by an earlier visit, which no check names any more, are removed when the module loads. */
  P.pruneSources();
})();
