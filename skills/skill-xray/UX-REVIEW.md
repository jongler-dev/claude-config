# Skill X-Ray — UI/UX Review

**Date:** 2026-03-28

---

## Observability Gaps

Data produced by agents but not surfaced in the report:

| Gap                                               | Source                                   | Impact                                                                      |
| ------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------- |
| **Tool scoping** (`scoped` boolean) not shown     | analysis.json                            | Users can't see which tools have restricted access — security-critical info |
| **Error handling strategy** not displayed         | `execution_flow.error_handling`          | Users miss how the skill recovers from failures                             |
| **Execution flow steps** only as diagrams         | `execution_flow.steps[]`                 | No copyable/structured view of steps, tools, and conditions                 |
| **Filesystem access type** (read vs write) hidden | `external_interactions.filesystem_paths` | Can't assess write-path risk                                                |
| **File size distribution** not aggregated         | `file_tree[].lines`                      | No visibility into code distribution (scripts vs agents vs references)      |

---

## Findings Tab — Biggest UX Problem

The Review tab merges 4 distinct finding sources (Spec, Security, Best Practice, Judgment) into a flat list:

1. **No grouping by source** — can't tell which _dimension_ needs work
2. **Spec rules invisible** — summary says "30 of 37 passed" but you can't see _which_ failed
3. **No filtering** — can't show only errors, or only security findings (`data-source` attr is ready, JS filter not yet wired)
4. **Dedup is opaque** — findings get silently removed with no trace
5. **No drill-down from scores** — clicking a score bar doesn't navigate to related findings

---

## Missing Interactions

1. **No finding filtering** (by source, severity) — `data-source` attr added, JS filter not yet wired
2. **No "Copy Errors" / "Copy Warnings"** — only "Copy All"
3. **No deep-link anchors** for sharing individual findings

---

## Accessibility

1. **Mermaid diagrams have no alt text** — no fallback if render fails
2. **Dark mode hardcoded** — doesn't respect `prefers-color-scheme`

---

## Code-Level Issues

1. **Dedup logic** uses magic numbers (60% keyword overlap threshold, hardcoded domain terms list) — fragile and untestable
2. **Template string replacement** is order-sensitive and has no protection against placeholder-in-value collisions

---

## Suggested Improvements

### High impact

- Add finding grouping/filtering by source (tabs or accordion in Review tab)
- Show spec compliance as a rules matrix (pass/fail/warn per rule)
- Link score bars to filtered findings view

### Medium impact

- Show error handling strategy in Overview or Architecture tab
- Add `prefers-color-scheme` media query

### Low impact

- Finding deep-link anchors
- Copy by severity buttons
