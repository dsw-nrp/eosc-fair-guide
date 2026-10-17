// Compact controls keep their own dimensions while retaining WCAG 2.2's 24px target minimum.
export async function compactControlProblems(page) {
  return page.locator('.read-toggle, button.id-chip').evaluateAll((controls) => controls.flatMap((control) => {
    const rect = control.getBoundingClientRect();
    if (!rect.width || !rect.height) return [];
    const style = getComputedStyle(control);
    const label = control.dataset.read || control.textContent.trim();
    if (control.matches('.read-toggle')) {
      return rect.width < 24 || Math.abs(rect.height - rect.width) > 1 ? [`${label}: read control is ${rect.width} × ${rect.height}px`] : [];
    }
    const line = parseFloat(style.lineHeight) + parseFloat(style.paddingTop) + parseFloat(style.paddingBottom)
      + parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
    return rect.height < 24 || parseFloat(style.minHeight) > Math.max(24, line) + 1 ? [`${label}: question chip inherits an oversized minimum height`] : [];
  }));
}
