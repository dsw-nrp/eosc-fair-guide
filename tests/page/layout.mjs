// Controls whose content is off centre, measured on what is drawn so that a stray margin or padding shows. In a
// control on one line every icon and line of text sits on the control's middle; in a control whose label wraps, an
// icon sits on the middle of the label's first line or of the whole label, never in between. A control that aligns
// its content to the start is measured against its label's first line, which may be taller than the label's own text. A control that sizes to its content or centres it has equal space
// left and right; one wider than its content and aligned to the start is left as it is. Runs in the page.
export function misalignedControls() {
  // The range of a text node's visible characters: spaces around them take room but draw nothing. Defined here
  // because only this function reaches the page.
  const inkOf = (node) => {
    const text = node.textContent;
    const range = document.createRange();
    range.setStart(node, text.search(/\S/));
    range.setEnd(node, text.trimEnd().length);
    return range;
  };
  const tolerance = 1;
  const drawn = (rect) => rect.width > 0 && rect.height > 0;
  const textLines = (node) => [...inkOf(node).getClientRects()].filter(drawn);
  const firstLine = (node) => {
    if (node.nodeType === Node.TEXT_NODE) return textLines(node)[0] || null;
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, { acceptNode: (text) => (text.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP) });
    const text = walker.nextNode();
    return text ? textLines(text)[0] || null : null;
  };
  const middle = (rect) => (rect.top + rect.bottom) / 2;
  const found = [];
  for (const control of document.querySelectorAll("button, .button, .button-small, .lens-option")) {
    const box = control.getBoundingClientRect();
    const style = getComputedStyle(control);
    if (!drawn(box) || !style.display.includes("flex") || !style.flexDirection.startsWith("row") || control.closest(".visually-hidden")) continue;
    const parts = [];
    for (const node of control.childNodes) {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
        const lines = textLines(node);
        if (lines.length) parts.push({ node, rect: lines[0], text: true, lines: lines.length });
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        const part = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        if (part.position === "absolute" || part.display === "none" || !drawn(rect)) continue;
        const line = firstLine(node);
        parts.push({ node, rect, text: Boolean(line), line, lines: line ? Math.round(rect.height / line.height) : 0 });
      }
    }
    if (!parts.length) continue;
    const name = `${control.id ? "#" + control.id : "." + String(control.className).trim().split(/\s+/)[0]} "${control.textContent.trim().slice(0, 30) || control.getAttribute("aria-label") || control.title}"`;
    const top = box.top + parseFloat(style.borderTopWidth) + parseFloat(style.paddingTop);
    const bottom = box.bottom - parseFloat(style.borderBottomWidth) - parseFloat(style.paddingBottom);
    const wraps = parts.some((part) => part.lines > 1) || ["flex-start", "start", "baseline"].includes(style.alignItems);
    const label = parts.find((part) => part.text);
    const references = wraps && label ? [middle(label.line || label.rect), middle(label.rect)] : [(top + bottom) / 2];
    const off = parts.find((part) => (!wraps || !part.text) && references.every((reference) => Math.abs(middle(part.text ? part.line || part.rect : part.rect) - reference) > tolerance));
    if (off) {
      found.push(`${name}: ${off.text ? "its text" : "an icon"} is ${(middle(off.text ? off.line || off.rect : off.rect) - references[0]).toFixed(1)} px off the middle of ${wraps ? "its first line and of its label" : "the control"}`);
      continue;
    }
    const left = Math.min(...parts.map((part) => part.rect.left)) - box.left;
    const right = box.right - Math.max(...parts.map((part) => part.rect.right));
    const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight) + parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
    const roomy = left + right - padding > tolerance;
    const centres = ["center", "space-around", "space-evenly"].includes(style.justifyContent);
    if (Math.abs(left - right) > tolerance && (centres || !roomy)) found.push(`${name} has ${left.toFixed(1)} px on the left and ${right.toFixed(1)} px on the right`);
  }
  return found;
}
// Things drawn over each other, or touching, without a deliberate decision. Marks are what the eye separates: a line
// of text, an icon or image, a form field, and a box (a component enclosed by a border on every side, or filled with
// rounded corners); full-width bands, table cells and one-sided separators are layout, not boxes. Two marks collide
// when neither holds the other and they intersect by more than a pixel; lines of text in one block are left to the
// font, an icon counts only against text on its own line, and a box may reach into the lines around it by up to three
// pixels. Two boxes touch when they sit side by side or one above the other less than two pixels apart, and an icon
// touches the text beside it the same way. A container marked data-joined makes its parts' contact deliberate. Only
// what is shown counts: a closed disclosure shows its summary alone, and a mark is cut to the boxes that clip it.
// Something may lie over a form field only within the field's padding, such as a clear button, never over its text.
// Runs in the page.
export function collisions() {
  // The range of a text node's visible characters: spaces around them take room but draw nothing. Defined here
  // because only this function reaches the page.
  const inkOf = (node) => {
    const text = node.textContent;
    const range = document.createRange();
    range.setStart(node, text.search(/\S/));
    range.setEnd(node, text.trimEnd().length);
    return range;
  };
  const found = [];
  const drawn = (rect) => rect.width > 1 && rect.height > 1;
  const viewport = document.documentElement.clientWidth;
  const styles = new Map();
  const css = (element) => styles.get(element) || styles.set(element, getComputedStyle(element)).get(element);
  const clear = (color) => color === "transparent" || /rgba\([^)]*,\s*0\)$/.test(color);
  const enclosed = (style) => ["Top", "Right", "Bottom", "Left"].every((side) => parseFloat(style[`border${side}Width`]) > 0 && !clear(style[`border${side}Color`]));
  const filledRound = (style) => !clear(style.backgroundColor) && parseFloat(style.borderTopLeftRadius) > 0;
  const marks = [];
  const cut = (rect, clip) => {
    const left = Math.max(rect.left, clip.left);
    const top = Math.max(rect.top, clip.top);
    const right = Math.min(rect.right, clip.right);
    const bottom = Math.min(rect.bottom, clip.bottom);
    return { left, top, right, bottom, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
  };
  const everywhere = { left: -Infinity, top: -Infinity, right: Infinity, bottom: Infinity };
  (function walk(element, block, clip) {
    const style = css(element);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0" || element.classList.contains("visually-hidden") || element.classList.contains("sprite") || ["SCRIPT", "STYLE", "TEMPLATE"].includes(element.tagName)) return;
    const own = style.display === "inline" || style.display === "contents" ? block : element;
    const rect = cut(element.getBoundingClientRect(), clip);
    const tag = element.tagName.toLowerCase();
    if (tag === "details" && !element.open) {
      const summary = element.querySelector(":scope > summary");
      if (summary) walk(summary, own, clip);
      return;
    }
    const clips = style.overflowX !== "visible" || style.overflowY !== "visible" || (style.position === "absolute" && style.clip !== "auto");
    const inner = clips ? cut(element.getBoundingClientRect(), clip) : clip;
    if (clips && !drawn(inner)) return;
    if (tag === "svg") {
      if (drawn(rect)) marks.push({ kind: "icon", node: element, rect, block: own === element ? block : own });
      return;
    }
    if (["img", "input", "select", "textarea"].includes(tag)) {
      if (drawn(rect)) marks.push({ kind: "box", node: element, rect, block });
      return;
    }
    if (drawn(rect) && rect.width < 0.9 * viewport && !style.display.startsWith("table") && (enclosed(style) || filledRound(style))) marks.push({ kind: "box", node: element, rect, block });
    for (const child of element.childNodes) {
      if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
        for (const line of inkOf(child).getClientRects()) {
          const shown = cut(line, inner);
          if (drawn(shown)) marks.push({ kind: "text", node: child, rect: shown, block: own });
        }
      } else if (child.nodeType === Node.ELEMENT_NODE) walk(child, own, inner);
    }
  })(document.body, document.body, everywhere);
  const element = (mark) => (mark.node.nodeType === Node.TEXT_NODE ? mark.node.parentElement : mark.node);
  const holds = (a, b) => a.node.contains(b.node) || b.node.contains(a.node);
  const joined = (a, b) => {
    let common = element(a);
    while (common && !common.contains(b.node)) common = common.parentElement;
    return Boolean(common && common.closest("[data-joined]"));
  };
  // Whether a mark reaches into a field's text area, the box inside its border and padding.
  const overField = (field, mark) => {
    const style = css(field.node);
    const box = field.node.getBoundingClientRect();
    const left = box.left + parseFloat(style.borderLeftWidth) + parseFloat(style.paddingLeft);
    const right = box.right - parseFloat(style.borderRightWidth) - parseFloat(style.paddingRight);
    return mark.rect.left < right - 1 && mark.rect.right > left + 1;
  };
  const describe = (mark) => {
    const text = (mark.node.textContent || "").trim().replace(/\s+/g, " ").slice(0, 24);
    const owner = element(mark);
    const label = owner.id ? "#" + owner.id : owner.classList.length ? "." + owner.classList[0] : owner.tagName.toLowerCase();
    return mark.kind === "text" ? `"${text}"` : `${mark.kind} ${label}${text ? ` "${text}"` : ""}`;
  };
  marks.sort((a, b) => a.rect.top - b.rect.top);
  for (let i = 0; i < marks.length; i += 1) {
    const a = marks[i];
    for (let j = i + 1; j < marks.length && marks[j].rect.top < a.rect.bottom + 2; j += 1) {
      const b = marks[j];
      if (holds(a, b)) continue;
      const across = Math.min(a.rect.right, b.rect.right) - Math.max(a.rect.left, b.rect.left);
      const down = Math.min(a.rect.bottom, b.rect.bottom) - Math.max(a.rect.top, b.rect.top);
      const sameBlock = a.block === b.block;
      const icon = a.kind === "icon" ? a : b.kind === "icon" ? b : null;
      const text = a.kind === "text" || b.kind === "text";
      if (across > 1 && down > 1) {
        if (a.kind === "text" && b.kind === "text" && sameBlock) continue;
        if (icon && sameBlock && down < icon.rect.height / 2) continue;
        if (text && (a.kind === "box" || b.kind === "box") && down <= 3) continue;
        const field = [a, b].find((mark) => ["INPUT", "TEXTAREA"].includes(mark.node.tagName));
        if (field && !overField(field, field === a ? b : a)) continue;
        if (!joined(a, b)) found.push(`${describe(a)} overlaps ${describe(b)}`);
        continue;
      }
      const sideBySide = down > Math.min(a.rect.height, b.rect.height) / 2 && across > -2;
      const stacked = across > Math.min(a.rect.width, b.rect.width) / 2 && down > -2;
      const boxes = a.kind === "box" && b.kind === "box";
      const iconBesideText = icon && text && sameBlock && sideBySide;
      if (((boxes && (sideBySide || stacked)) || iconBesideText) && !joined(a, b)) found.push(`${describe(a)} touches ${describe(b)}`);
    }
  }
  return found;
}
