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
    /* The stream is read by its declared length: compressed bytes may end with a carriage return, which a
       delimiter such as `\r?\nendstream` would take from the data. */
    const head = content?.match(/\/Length (\d+)[\s\S]*?stream\r?\n/);
    const start = head ? head.index + head[0].length : 0;
    const stream = head ? content.slice(start, start + Number(head[1])) : "";
    assert(stream.length, `PDF page ${index + 1} has content instead of an empty trailing page`);
    assert(/\/FlateDecode/.test(content), "the Chromium content stream can be inspected");
    assert(/\bBT\b/.test(inflateSync(Buffer.from(stream, "latin1")).toString("latin1")), `PDF page ${index + 1} contains text instead of a trailing blank`);
  }
  return pages.length;
}
