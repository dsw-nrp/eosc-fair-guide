// Hash navigation leaves the previous main visible while deferred data arrives.
export async function navigationRendered(page, navigate) {
  const token = String(Math.random());
  const before = await page.evaluate((token) => {
    const main = document.querySelector("#main");
    if (main) main.dataset.previousView = token;
    return location.href;
  }, token);
  await navigate();
  // A same-address goto need not dispatch hashchange. Explicitly render that case; ordinary actions retain
  // their own behaviour, and a full document navigation has already discarded the marker.
  await page.evaluate(({ token, before }) => {
    if (location.href === before && document.querySelector("#main")?.dataset.previousView === token) {
      window.FairGuide?.render();
    }
  }, { token, before });
  await rendered(page);
}

export async function rendered(page) {
  await page.waitForFunction(() => {
    const FG = window.FairGuide, main = document.querySelector("#main");
    if (!FG?.parseHash || !main || main.dataset.previousView || !main.querySelector("h1")?.textContent.trim()) return false;
    const route = FG.parseHash(location.hash);
    return FG.state.lang === route.lang && FG.state.lens === route.lens && document.documentElement.lang === route.lang &&
      !document.body.textContent.includes("The Guide is loading.");
  });
}

export const gotoView = (page, url) => navigationRendered(page, () => page.goto(url));

export async function searchReady(page, query) {
  await page.waitForFunction((query) => {
    const FG = window.FairGuide, results = document.querySelector("#search-results");
    return FG && ["standards", "questions"].every((part) => FG.partHasLanguage(part, FG.state.lang)) &&
      results?.dataset.query === query;
  }, query);
}
