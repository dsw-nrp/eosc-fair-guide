import "./browser_env.mjs";
// Anonymous browser health measurements of reviewed FAIR Champion endpoints; never selects or edits tests.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";

export function summarize(results) {
  const ids = [...new Set(results.map((entry) => entry.test))];
  return ids.map((id) => {
    const own = results.filter((entry) => entry.test === id);
    const verdicts = own.filter((entry) => ["pass", "fail", "indeterminate"].includes(entry.value));
    return { id, attempted: own.length, verdicts: verdicts.length,
      definitive: verdicts.filter((entry) => entry.value !== "indeterminate").length,
      indeterminate: verdicts.filter((entry) => entry.value === "indeterminate").length,
      health: verdicts.length === own.length ? "available" : verdicts.length ? "degraded" : "unavailable" };
  });
}

export function reviewedCandidates(candidates, origin) {
  const seen = new Set();
  return candidates.map((entry) => {
    if (!entry.id || seen.has(entry.id)) throw Error("Missing or duplicate candidate identity");
    seen.add(entry.id);
    const url = new URL(entry.endpoint);
    if (url.origin !== origin || url.username || url.password || url.search || url.hash || !/^\/(?:tests|community-tests)\/assess\/test\/[^/]+$/.test(url.pathname)) throw Error("Unreviewed invocation endpoint: " + entry.id);
    if (decodeURIComponent(url.pathname.split("/").at(-1)) !== entry.id) throw Error("Endpoint identity differs from candidate: " + entry.id);
    return entry;
  });
}

export function reviewedRecords(records) {
  const seen = new Set();
  if (!records.length || records.length > 10) throw Error("Expected one to ten public reference PIDs");
  return records.map((entry) => {
    if (typeof entry.id !== "string" || !entry.id.trim() || seen.has(entry.id)) throw Error("Missing or duplicate reference identity");
    seen.add(entry.id);
    const url = new URL(entry.identifier);
    if (url.protocol !== "https:" || !["doi.org", "hdl.handle.net"].includes(url.host) || url.username || url.password || url.search || url.hash || url.pathname.length < 2) throw Error("Expected a public reference PID: " + entry.id);
    return entry;
  });
}

export async function main(args) {
  const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
  const root = resolve(import.meta.dirname, "..");
  const candidatePath = option("--candidates", resolve(root, "docs/champion/candidates.json"));
  const recordPath = option("--records", resolve(root, "docs/champion/reference-records.json"));
  const output = resolve(option("--output", resolve(root, ".cache/champion-health.json")));
  const config = JSON.parse(readFileSync(resolve(root, "_site/assets/data/ui.js"), "utf8").match(/^window\.FairGuideData\.ui = (.*);$/m)[1]).config;
  const origin = config.connectors.find((entry) => entry.id === "champion").origin;
  const candidates = reviewedCandidates(JSON.parse(readFileSync(candidatePath, "utf8")), origin);
  const records = reviewedRecords(JSON.parse(readFileSync(recordPath, "utf8")));
  const workers = Number(option("--jobs", "4"));
  if (!Number.isInteger(workers) || workers < 1 || workers > 4) throw Error("Use one to four concurrent calls");

  const { chromium } = await import("playwright");
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const results = [], unresolved = [];
  try {
    await page.goto(pathToFileURL(resolve(root, "_site/index.html")).href + "#/en/V/path/start");
    await page.waitForFunction(() => window.FairGuide?.live?.championResult);
    for (const record of records) {
      const found = await page.evaluate(async (entry) => {
        try { return (await FairGuide.live.resolvePid(FairGuide.live.parsePid(entry.identifier))).found; } catch { return false; }
      }, record);
      if (!found) unresolved.push(record.id);
    }
    const jobs = candidates.flatMap((candidate) => records.filter((entry) => !unresolved.includes(entry.id)).map((record) => ({ candidate, record })));
    let cursor = 0;
    const worker = async () => {
      while (cursor < jobs.length) {
        const { candidate, record } = jobs[cursor++];
        const result = await page.evaluate(async ({ endpoint, identifier, timeout }) => {
          const start = performance.now(), controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), timeout * 1000);
          let status;
          try {
            const response = await fetch(endpoint, { method: "POST", credentials: "omit", referrerPolicy: "no-referrer", redirect: "error",
              headers: { Accept: "application/ld+json, application/json", "Content-Type": "application/json" },
              body: JSON.stringify({ resource_identifier: identifier }), signal: controller.signal });
            status = response.status;
            if (!response.ok) throw Error("HTTP " + status);
            const reader = response.body.getReader(), decoder = new TextDecoder();
            let size = 0, text = "";
            try {
              while (true) {
                const chunk = await reader.read();
                if (chunk.done) break;
                size += chunk.value.byteLength;
                if (size > 2097152) throw Error("Response exceeds 2 MiB");
                text += decoder.decode(chunk.value, { stream: true });
              }
            } finally { await reader.cancel(); }
            const verdict = FairGuide.live.championResult(JSON.parse(text + decoder.decode()));
            return { ...verdict, status, bytes: size, seconds: (performance.now() - start) / 1000 };
          } catch (error) { return { status, error: error.name === "AbortError" ? "Timeout" : error.message, seconds: (performance.now() - start) / 1000 }; }
          finally { clearTimeout(timer); }
        }, { endpoint: candidate.endpoint, identifier: record.identifier, timeout: config.champion.timeoutSeconds });
        results.push({ test: candidate.id, record: record.id, identifier: record.identifier, endpoint: candidate.endpoint, ...result });
        console.log(`${results.length}/${jobs.length} ${candidate.id} ${record.id}: ${result.value || result.error} (${result.seconds.toFixed(1)}s)`);
        save();
      }
    };
    const save = () => {
      mkdirSync(dirname(output), { recursive: true });
      writeFileSync(output, JSON.stringify({ generatedAt: new Date().toISOString(), origin, candidates, records, unresolved, results, summary: summarize(results) }, null, 2) + "\n");
    };
    await Promise.all(Array.from({ length: workers }, worker));
    save();
    return unresolved.length ? 1 : 0;
  } finally { await browser.close(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try { process.exitCode = await main(process.argv.slice(2)); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
