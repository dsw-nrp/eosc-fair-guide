// Normalise favicons: each image in the input folder is drawn once into a square PNG of the given size, scaled to fit
// and centred on a transparent background, and written to the output folder as <name>.png. The browser decodes every
// format a favicon comes in (ICO, PNG, GIF, JPEG, WebP, SVG) the way the page would, so one renderer serves them all;
// it is the Playwright Chromium the page checks use. A light icon made for dark browser tabs, which would vanish on the
// white ground of a badge, is drawn on a dark rounded tile instead, as such sites show it. An image that does not
// decode or draws nothing visible is reported and not written. Run by scripts/vendor_favicons.py.
// Usage: node scripts/normalise_favicons.mjs <input folder> <output folder> <size>

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve(root, ".cache/ms-playwright");
const { chromium } = await import("playwright");

const [input, output, sizeText] = process.argv.slice(2);
const size = Number(sizeText);
if (!input || !output || !Number.isInteger(size) || size < 16 || size > 256) {
  console.error("usage: node scripts/normalise_favicons.mjs <input folder> <output folder> <size 16-256>");
  process.exit(2);
}
const TYPES = { png: "image/png", ico: "image/x-icon", gif: "image/gif", jpg: "image/jpeg", webp: "image/webp", svg: "image/svg+xml" };

const browser = await chromium.launch();
const failed = [];
try {
  const page = await browser.newPage();
  // Nothing outside the page is fetched: every image arrives as a data address.
  await page.route(/^https?:/, (route) => route.abort());
  await page.setContent("<!doctype html><title>Favicons</title>");
  for (const name of readdirSync(input).sort()) {
    const extension = name.split(".").pop();
    const base = name.slice(0, -(extension.length + 1));
    if (!TYPES[extension]) {
      failed.push(base);
      continue;
    }
    const source = `data:${TYPES[extension]};base64,${readFileSync(join(input, name)).toString("base64")}`;
    const png = await page
      .evaluate(
        async ({ source, size }) => {
          const image = new Image();
          image.src = source;
          await image.decode();
          /* An SVG without a size of its own fills the square. */
          const width = image.naturalWidth || size;
          const height = image.naturalHeight || size;
          const scale = Math.min(size / width, size / height);
          const canvas = document.createElement("canvas");
          canvas.width = canvas.height = size;
          const context = canvas.getContext("2d");
          context.imageSmoothingEnabled = true;
          context.imageSmoothingQuality = "high";
          const draw = () => context.drawImage(image, (size - width * scale) / 2, (size - height * scale) / 2, width * scale, height * scale);
          /* The share of the square that is opaque enough and darker, or lighter, than the given limits. */
          const share = (test) => {
            const pixels = context.getImageData(0, 0, size, size).data;
            let count = 0;
            for (let at = 0; at < pixels.length; at += 4) if (pixels[at + 3] > 64 && test(pixels[at], pixels[at + 1], pixels[at + 2])) count += 1;
            return count / (size * size);
          };
          draw();
          if (share((r, g, b) => Math.min(r, g, b) < 220) >= 0.03) return canvas.toDataURL("image/png");
          if (share((r, g, b) => Math.max(r, g, b) > 200) < 0.03) return null;
          /* A light icon: on the guide's dark text colour, in a tile with rounded corners. */
          context.clearRect(0, 0, size, size);
          const radius = size / 6;
          context.fillStyle = "#1d2a30";
          context.beginPath();
          context.roundRect(0, 0, size, size, radius);
          context.fill();
          draw();
          return canvas.toDataURL("image/png");
        },
        { source, size }
      )
      .catch(() => null);
    if (png) writeFileSync(join(output, base + ".png"), Buffer.from(png.slice(png.indexOf(",") + 1), "base64"));
    else failed.push(base);
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify({ failed }));
