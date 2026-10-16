import { root } from "./browser_env.mjs";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";

const cli = resolve(dirname(createRequire(import.meta.url).resolve("playwright/package.json")), "cli.js");
const result = spawnSync(process.execPath, [cli, "install", "chromium", ...process.argv.slice(2)], {
  cwd: root, env: process.env, stdio: "inherit",
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
