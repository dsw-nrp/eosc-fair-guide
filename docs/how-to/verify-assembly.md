<!-- type: how-to -->
# Check production and preview assembly locally


First [build and check](build-and-check.md) the site, then run `python -m unittest discover -s tests -p test_assemble_pages.py`, `node tests/page/check_release.mjs` and
`node tests/page/check_publication.mjs`, then `npm run check:deployment` for the real browser and Swagger request.
The fixtures cover production preservation, all preview HTML pages, first-tag absence, source selection, approval,
merge-queue reuse, publication order, durable byte reuse and refused malformed/mismatched artifacts.

To assemble already checked inputs without publishing:

```bash
python scripts/assemble_pages.py --staging _site --staging-commit <checked-preview-sha> --production .cache/release --production-tag <release-tag> --production-commit <checked-release-sha> --out .cache/pages
```

Omit the three `--production*` arguments to exercise the state before the first release. The preview must have
a completed passing health report naming its supplied commit. The production directory holds `manifest.json`,
the release archive and its checksum. Open `.cache/pages/index.html` or serve that directory locally to inspect
both the production root and `/next/`; this command does not change `_site/`.


See the [deployment reference](../deployment.md) for identity and channel guarantees.
