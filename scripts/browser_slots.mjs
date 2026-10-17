// Cooperative browser-case budget across the runner's separate Node processes.
import { mkdirSync, readdirSync, readFileSync, writeFileSync, unlinkSync, rmdirSync, statSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { workerCount } from "./browser_env.mjs";

const held = new Set();
const waiting = new Set();
process.on("exit", () => {
  for (const release of held) release();
  for (const path of waiting) { try { unlinkSync(path); } catch { /* Already acquired. */ } }
});

export function slotIsAbandoned(slot) {
  try {
    const pid = Number(readFileSync(resolve(slot, "owner"), "utf8"));
    if (!Number.isSafeInteger(pid) || pid <= 0) return false;
    try { process.kill(pid, 0); return false; }
    catch (error) {
      if (error.code !== "ESRCH") return false;
      // The former owner can release and exit between readFile and kill. Only the same
      // owner still recorded in this slot proves abandonment; release/reassignment is healthy.
      try { return Number(readFileSync(resolve(slot, "owner"), "utf8")) === pid; }
      catch { return false; }
    }
  } catch {
    // An owner may still be writing its pid. Never reclaim a newly created slot.
    try { return Date.now() - statSync(slot).mtimeMs > 30_000; } catch { return false; }
  }
}

export async function acquireSlot(directory = process.env.CHECK_BROWSER_SLOT_DIR, budget = workerCount()) {
  if (!directory) return () => {}; // A direct single-script run is bounded by mapLimit instead.
  const base = resolve(directory);
  mkdirSync(base, { recursive: true });
  const ticket = `wait-${Date.now()}-${randomUUID()}`;
  const ticketPath = resolve(base, ticket);
  writeFileSync(ticketPath, String(process.pid), { flag: "wx" });
  waiting.add(ticketPath);
  const deadline = Date.now() + 300_000;
  try { while (Date.now() < deadline) {
    // Queue order prevents the process releasing a slot from immediately monopolizing it again.
    if (!readdirSync(base).filter((name) => name.startsWith("wait-")).sort().slice(0, budget).includes(ticket)) {
      await delay(10);
      continue;
    }
    for (let index = 0; index < budget; index++) {
      const slot = resolve(base, `slot-${index}`);
      try {
        mkdirSync(slot); // Exclusive, atomic directory creation on Windows and Unix.
        writeFileSync(resolve(slot, "owner"), String(process.pid));
        let released = false;
        const release = () => {
          if (released) return;
          released = true;
          held.delete(release);
          try { unlinkSync(resolve(slot, "owner")); rmdirSync(slot); } catch { /* A later run uses a fresh budget root. */ }
        };
        held.add(release);
        return release;
      } catch (error) {
        if (error.code !== "EEXIST") throw error;
        if (slotIsAbandoned(slot)) {
          throw new Error("A browser worker abandoned its budget slot; start a fresh run", { cause: error });
        }
      }
    }
    await delay(10);
  } } finally {
    waiting.delete(ticketPath);
    try { unlinkSync(ticketPath); } catch { /* Exit cleanup may already have removed it. */ }
  }
  throw new Error("Timed out waiting for the shared browser budget");
}
