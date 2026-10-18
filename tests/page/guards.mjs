// One owner for the console-error and external-request guards used by page checks. Each check states the
// traffic its own fixture allows; axe's stylesheet requests are suppressed only while the audit runs.
export function installGuards(page, {
  allowed = (url) => /^(?:file|data):/.test(url),
  consoleErrors = false,
  consolePrefix = "",
  errorPrefix = "",
} = {}) {
  const problems = [];
  const external = [];
  const state = {axeRunning: false};
  page.on("pageerror", (error) => problems.push(errorPrefix + error.message));
  if (consoleErrors) {
    page.on("console", (message) => {
      if (message.type() === "error" && !state.axeRunning) problems.push(consolePrefix + message.text());
    });
  }
  page.on("request", (request) => {
    const url = request.url();
    if (!state.axeRunning && !allowed(url)) external.push(url);
  });
  return {state, problems, external};
}
