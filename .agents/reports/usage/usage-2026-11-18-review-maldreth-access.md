# MaLDReTH Access correspondence and issue follow-up

- **When:** 2026-11-18
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-opus-5-5
- **What:** Rest the RDMkit Reuse to MaLDReTH Access correspondence on MaLDReTH's own definition of Access as the
  Guide's reviewed reading, instead of leaving it unconfirmed pending the working group (issue 30 of
  `dsw-nrp/eosc-fair-guide`), with one provenance action. The life-cycle page test took this entry as its only
  unconfirmed example; it now checks each mark against the basis the crate records. The view sweep now measures
  each view from its top: the page keeps the previous view's scroll position, and content under the opaque sticky
  lens band was reported as a collision no reader sees (reproduced on `main` by scrolling a check page past about
  220 px; screenshots show no overlap). On GitHub, issue 31 was closed with public evidence that DataHub and the
  Map Collection are separate services of two departments.
- **Impacted:** `content/lifecycle/crosswalk.toml`, `content/provenance.toml`, `content/identifiers.toml`,
  `tests/page/check_page.mjs` and this usage entry; issue 31's state and comment.
- **Close-out:** `python scripts/check_content.py --base origin/main` passes, and fails when the provenance action is
  removed. The life-cycle assertion fails in both languages when the renderer marks every correspondence as
  published. All 36 repository checks pass in 247.6 seconds; this entry was written afterwards and the
  agent-surface ownership and documentation checks were run again.
