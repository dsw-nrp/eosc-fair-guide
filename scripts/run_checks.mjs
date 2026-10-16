// Execute each script independently and retain timings/output even when another script fails.
import { root } from "./browser_env.mjs";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const groups = {
  page: ["page", "embed"],
  embed: ["embed"], deployment: ["deployment"], discovery: ["discovery"],
  helpers: ["accessibility", "safety", "helpers", "citation", "datacite", "services", "champion_probe", "pr_comment", "source_publisher", "health_issues", "release", "deployment", "prepare_release", "navigation"],
  model: ["model", "visuals"], visuals: ["visuals"],
  assessment: ["assess", "questions", "sources", "languages", "tests", "providers"], providers: ["providers"],
  live: ["live"], diagrams: ["diagrams"], api: ["../api/check_api"], "live-release": ["live_release"],
  final: ["final_candidate", "repairs", "print"],
};
const group = process.argv[2];
if (!Object.hasOwn(groups, group)) throw new Error(`Unknown check group: ${group}`);
const directory = resolve(process.env.CHECK_REPORT_DIR || resolve(root, ".cache/check-details"), group);
mkdirSync(directory, { recursive: true });
const scripts = [];
for (const name of groups[group]) {
  const file = name.startsWith("../") ? "tests/api/check_api.mjs" : `tests/page/check_${name}.mjs`;
  const start = performance.now();
  const detail = resolve(directory, name.replace(/[^a-zA-Z0-9_-]/g, "_") + ".json");
  if (existsSync(detail)) unlinkSync(detail);
  const result = spawnSync(process.execPath, [file], {
    cwd: root, env: { ...process.env, CHECK_CASE_REPORT: detail }, encoding: "utf8", maxBuffer: 16 * 1024 * 1024,
  });
  const output = (result.stdout || "") + (result.stderr || "") + (result.error ? String(result.error) : "");
  const seconds = (performance.now() - start) / 1000;
  const returncode = result.status ?? 1;
  writeFileSync(detail + ".log", output);
  process.stdout.write(output);
  console.log(`${returncode ? "FAIL" : "ok"} ${seconds.toFixed(2)}s ${file}`);
  const cases = existsSync(detail) ? JSON.parse(readFileSync(detail, "utf8")) : null;
  scripts.push({ file, seconds, returncode, output, cases, status: returncode ? "failed" : cases?.status || "passed" });
}
const status = scripts.some((script) => script.status === "failed") ? "failed" : scripts.some((script) => script.status === "partial") ? "partial" : "passed";
writeFileSync(resolve(directory, "scripts.json"), JSON.stringify({ group, status, scripts }, null, 2) + "\n");
process.exitCode = status === "failed" ? 1 : 0;
