import assert from "node:assert/strict";
import { inflateSync } from "node:zlib";

// This helper inspects only test-generated Chromium PDFs: one Flate content stream per page.
export function assertNoBlankPages(pdf) {
  const objects = new Map([...pdf.toString("latin1").matchAll(/(\d+) 0 obj\s*([\s\S]*?)endobj/g)].map((match) => [match[1], match[2]]));
  const pages = [...objects.values()].filter((object) => /\/Type \/Page\b/.test(object));
  assert(pages.length > 0, "the PDF contains pages");
  for (const [index, object] of pages.entries()) {
    const reference = object.match(/\/Contents (\d+) 0 R/);
    assert(reference, "a generated page has a content stream");
    const content = objects.get(reference[1]);
    const stream = content?.match(/stream\r?\n([\s\S]*?)\r?\nendstream/);
    assert(stream?.[1].length, `PDF page ${index + 1} has content instead of an empty trailing page`);
    assert(stream && /\/FlateDecode/.test(content), "the Chromium content stream can be inspected");
    assert(/\bBT\b/.test(inflateSync(Buffer.from(stream[1], "latin1")).toString("latin1")), `PDF page ${index + 1} contains text instead of a trailing blank`);
  }
  return pages.length;
}
