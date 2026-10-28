<!-- type: how-to -->
# Remeasure Champion without changing the selection


Set up and build the site using [build and check](build-and-check.md), then run:

```sh
node scripts/probe_champion.mjs --jobs 4 --output .cache/champion-health.json
```

The default [candidate list](../champion/candidates.json) includes the core and all reviewed candidates. Optional
`--candidates` and `--records` arguments accept reviewed JSON inputs. The browser checks PID resolution
first, uses anonymous requests with no redirects, limits concurrency to four and calls to 60 seconds,
caps each response at 2 MiB, and records incomplete coverage. It writes progress after each call. The full
local report retains response logs; the committed measurement omits logs and preserves the measured
outcomes. The script never selects tests or edits authored content. Scheduled health reporting can use
the report; any selection or mapping change requires content review in a pull request.

The [selection record](../champion/selection.md) retains the reviewed scope and evidence.
