// One environment policy for browser installation, npm checks and direct Node entry points.
import { mkdirSync, readFileSync } from "node:fs";
import { availableParallelism } from "node:os";
import { resolve } from "node:path";

export const root = resolve(import.meta.dirname, "..");
export function browserEnvironment(env = process.env) {
  return { ...env, PLAYWRIGHT_BROWSERS_PATH: env.PLAYWRIGHT_BROWSERS_PATH ?? resolve(root, ".cache/ms-playwright") };
}
Object.assign(process.env, browserEnvironment());
// Keep test artifacts in the checkout on native Windows; container/Linux temp policy stays with the host.
if (process.platform === "win32") {
  const temporary = resolve(root, ".cache/browser-temp");
  mkdirSync(temporary, { recursive: true });
  process.env.TEMP = temporary;
  process.env.TMP = temporary;
}

export function checkDefaults(env = process.env, cpus = availableParallelism()) {
  const profile = env.CI && !["0", "false"].includes(env.CI.toLowerCase()) ? "ci" : "local";
  const policy = JSON.parse(readFileSync(resolve(root, "scripts/check_policy.json"), "utf8"))[profile];
  return { profile, ...Object.fromEntries(Object.entries(policy).map(([key, value]) => [key, Math.min(value, Math.max(1, cpus))])) };
}

export function workerCount(value = process.env.CHECK_BROWSER_WORKERS ?? checkDefaults().browser_workers) {
  if (!/^[1-9]\d*$/.test(String(value))) throw new Error("CHECK_BROWSER_WORKERS must be a positive integer");
  return Number(value);
}

/** Bounded independent tasks. Callers keep nested work sequential to avoid multiplying this budget. */
export async function mapLimit(items, work, workers = workerCount()) {
  let next = 0;
  const results = new Array(items.length);
  await Promise.all(Array.from({ length: Math.min(workers, items.length) }, async () => {
    while (next < items.length) {
      const index = next++;
      results[index] = await work(items[index], index);
    }
  }));
  return results;
}
