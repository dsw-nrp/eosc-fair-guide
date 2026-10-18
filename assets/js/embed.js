/* FAIR Guide embedding protocol v1, used by both the Guide and its dependency-free host snippet.
   Only height and the view address travel between the frames; answers and evidence stay in the Guide. */
(function () {
  "use strict";
  const script = document.currentScript;
  const version = 1;
  const parameter = "fair-guide-view";
  const validView = (view) => typeof view === "string" && view.length <= 2 * 1024 * 1024 &&
    /^#\/(cs|en)\/(V|DS|SR|K)\/(path|check|explorer|catalogue|tools|page|selfcheck)(\/[^\s\u0000-\u001f]*)?$/.test(view);
  const isMessage = (data, type) => data && typeof data === "object" && data.type === type && data.version === version;

  if (script.dataset.guideFrame) {
    const frame = document.getElementById(script.dataset.guideFrame);
    if (!frame || frame.tagName !== "IFRAME") return;
    const guide = new URL(frame.src, location.href);
    if (!/^https?:$/.test(guide.protocol)) return;
    const savedView = () => new URL(location.href).searchParams.get(parameter);
    const saved = savedView();
    if (validView(saved)) {
      guide.hash = saved;
      frame.src = guide.href;
    }
    const send = () => {
      const view = savedView();
      frame.contentWindow?.postMessage({ type: "fair-guide:init", version, view: validView(view) ? view : guide.hash || "#/cs/V/path/start" }, guide.origin);
    };
    window.addEventListener("message", (event) => {
      if (event.source !== frame.contentWindow || event.origin !== guide.origin || !isMessage(event.data, "fair-guide:state")) return;
      const { height, view } = event.data;
      if (!Number.isSafeInteger(height) || height < 24 || height > 1000000 || !validView(view)) return;
      frame.style.height = height + "px";
      const address = new URL(location.href);
      if (address.searchParams.get(parameter) === view) return;
      address.searchParams.set(parameter, view);
      history.replaceState(history.state, "", address);
    });
    frame.addEventListener("load", send);
    window.addEventListener("popstate", send);
    send();
    return;
  }

  if (window.parent === window) return;
  const origins = new Set((script.dataset.parentOrigins || "").split(/\s+/).map((origin) => origin === "self" ? location.origin : origin)
    .filter((origin) => /^https?:\/\//.test(origin) && (() => { try { return new URL(origin).origin === origin; } catch { return false; } })()));
  let parentOrigin = null;
  let previous = "";
  let pending = false;
  function publish() {
    if (pending || !parentOrigin) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      const view = location.hash;
      if (!validView(view)) return;
      // Body content, rather than the viewport's scrollHeight, also permits the host frame to shrink.
      const height = Math.ceil(Math.max(document.body.getBoundingClientRect().height, document.body.scrollHeight));
      const state = height + " " + view;
      if (height < 24 || height > 1000000 || state === previous) return;
      previous = state;
      window.parent.postMessage({ type: "fair-guide:state", version, height, view }, parentOrigin);
    });
  }
  window.addEventListener("message", (event) => {
    if (event.source !== window.parent || !origins.has(event.origin) || !isMessage(event.data, "fair-guide:init") || !validView(event.data.view)) return;
    parentOrigin = event.origin;
    previous = "";
    if (location.hash !== event.data.view) location.hash = event.data.view;
    publish();
  });
  new ResizeObserver(publish).observe(document.body);
  new MutationObserver(publish).observe(document.body, { childList: true, subtree: true, attributes: true });
  window.addEventListener("hashchange", publish);
  window.addEventListener("load", publish);
}());
