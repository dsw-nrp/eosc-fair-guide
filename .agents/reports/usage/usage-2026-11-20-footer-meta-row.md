# Footer meta row

- **When:** 2026-11-20
- **Agent / runtime:** Kilo
- **Model / backend:** e-infra-cz/deepseek-v4.1-flash-thinking
- **What:** The footer's build identity, the "Kdo se podílel" link and the licence line become one paragraph, so the
  footer loses two rows without losing any of them. The page check that scrolls to the dataset check's item before
  measuring the sticky result control no longer depends on how far the page can scroll: it centres the item, because
  near the document end the summary leaves its container instead of sticking, and the shorter footer made that state
  reachable in the check. `AGENTS.md` now names the targeted `-p test_<module>.py` run beside the eight-minute suite.
- **Impacted:** `assets/js/views.js`, `tests/page/check_page.mjs`, `AGENTS.md` and this entry.
- **Close-out:** `python scripts/build_site.py` builds the site; `npm run -s check:page` passes all four page groups;
  `node tests/page/check_safety.mjs` passes. The merged row is one line at 1280 px, two at 900 px, three at 390 px and
  four at 320 px, with no horizontal overflow at any of them. This change is unrelated to PR 189 and belongs in its
  own commit.
