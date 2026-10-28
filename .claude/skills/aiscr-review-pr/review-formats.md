# PR review formats

<!-- delivery-version: da48582ffc5b5ec4c023b693c2406926fb14fe71 2026-10-28T17:17:14+01:00 -->

## Reference format 1

````markdown
<!-- aiscr-review-pr:summary -->

# PR summary — [OWNER/REPO#NUMBER][pr]

[pr]: PR_URL

| Field | Value |
| --- | --- |
| Title | … |
| URL | … |
| Referenced items | … |
| Author | … |
| Base ← head | … |
| Head SHA | … |
| Size | … |
| State | … |
| Marked AIS CR review baseline | … |
| Prior PR summary | … |

## Change walkthrough

[exactly one concise Mermaid diagram from a core family GitHub renders; no plugin-dependent family]

## Author context

<!-- aiscr-review-pr:author-context -->

[carried machine-read fragments verbatim, and the archive link; or an explicit
statement that the description carried none]

<!-- /aiscr-review-pr:author-context -->

## Lineage

---

This PR summary was prepared with AI assistance through the AIS CR review workflow; the posting reviewer reviewed and approved it for posting.
````

## Reference format 2

```json
{
  "dispositions": [
    {"segment": 0, "action": "absorbed", "target": "Purpose and scope"},
    {"segment": 1, "action": "carried"},
    {"segment": 2, "action": "dropped", "reason": "empty template boilerplate"}
  ],
  "dropped_anchors": [{"anchor": "`v1.2`", "reason": "superseded by the current version"}]
}
```

## Reference format 3

```text
CARRIED    2   Fixes #N  ·  - [ ] run migration
ABSORBED   3   intent para → Purpose and scope
               perf note   → Attention hints
               rollout     → Validation / test surfaces
QUOTED     1   "we deliberately kept the old codepath"
SUPERSEDED 1   stale para describing the v1 approach
DROPPED    1   empty template boilerplate
```
