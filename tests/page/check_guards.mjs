// The shared page guards catch a real error and external request, and suppress axe's own traffic only while auditing.
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { installGuards } from "./guards.mjs";

const page = new EventEmitter();
const {state, problems, external} = installGuards(page, {
  allowed: (url) => url.startsWith("file:"),
  consoleErrors: true,
  consolePrefix: "console: ",
  errorPrefix: "page error: ",
});

page.emit("request", {url: () => "https://external.example/"});
assert.deepEqual(external, ["https://external.example/"], "an external request is caught");
state.axeRunning = true;
page.emit("request", {url: () => "https://axe.example/stylesheet.css"});
page.emit("console", {type: () => "error", text: () => "axe stylesheet warning"});
state.axeRunning = false;
assert.equal(external.length, 1, "axe traffic is ignored only while auditing");
assert.equal(problems.length, 0, "axe console noise is ignored only while auditing");

page.emit("console", {type: () => "error", text: () => "real error"});
page.emit("pageerror", new Error("boom"));
assert.deepEqual(problems, ["console: real error", "page error: boom"]);
console.log("Page guard fixtures: external request, axe suppression and real console/page errors pass.");
