# Issue triage and reviewed link limitations

- **When:** 2026-11-17
- **Agent / runtime:** Claude Code
- **Model / backend:** claude-fable-5-2
- **What:** Review the open issues of `dsw-nrp/eosc-fair-guide`, finish their triage and resolve what needs no
  outside party. On GitHub, after the maintainer approved the plan: set the Issue Type of issue 171 to Task, label
  issue 169 `area:sources`, move issue 136 to In progress, record six blocked-by relations that the issue bodies
  already state (5, 13 and 16 by 32; 171 by 25 and 136; 11 by 20) and close issue 153, whose address answers again.
  In the repository: record three reviewed limitations of the health watch for KNAV catalogue addresses that are
  gone or do not answer (the tasks of issues 154, 162 and 163).
- **Impacted:** `.github/health-watch.toml` and this usage entry; the issue fields, relations and state named above.
  No content, snapshot, behaviour or contract changes.
- **Close-out:** `python scripts/watch_sources.py check-config` accepts the file with 15 limitations and rejects a
  deliberately invalid duplicate entry. All 36 repository checks pass in 363.6 seconds on the limitation change;
  this entry was written afterwards and the agent-surface ownership check was run again. No push or pull request
  is made before the maintainer approves the diff and the pull-request text.
