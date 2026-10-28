// The block that ends every automated output: who acts next, the way round a blocker, and the evidence of
// completion. The JavaScript twin of scripts/handoff.py, for the trusted publishers. A missing element is a
// programming error, so an output can never end without saying what happens next.
const LABELS = { next: "Next", blocked: "If blocked", done: "Done when" };

function handoff({ next, blocked, done }) {
  const values = { next, blocked, done };
  for (const [key, label] of Object.entries(LABELS)) {
    if (!String(values[key] ?? "").trim()) throw Error(`A handoff needs its "${label}" element`);
  }
  return Object.entries(LABELS).map(([key, label]) => `- **${label}:** ${values[key]}`).join("\n");
}

module.exports = { handoff };
