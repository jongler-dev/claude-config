# Skill X-Ray — UI/UX Review

**Date:** 2026-03-28
**Updated:** 2026-04-14

---

## Observability Gaps

Data produced by agents but not surfaced in the report:

| Gap                                               | Source                                   | Impact                                                                      |
| ------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------- |
| **Tool scoping** — shell scoping shown, but general tool `scoped` boolean not surfaced | analysis.json | Users can't see which non-shell tools have restricted access |
| **Filesystem access type** (read vs write) hidden | `external_interactions.filesystem_paths` | Can't assess write-path risk                                                |
| **File size distribution** not aggregated         | `file_tree[].lines`                      | No visibility into code distribution (scripts vs agents vs references)      |

---

## Findings Tab

Remaining issues:

1. **Findings sorted by severity, not grouped by source** — filtering works but display order doesn't cluster by dimension
2. **Dedup is opaque** — findings get silently removed with no trace
3. **No "Copy Errors" / "Copy Warnings"** — only "Copy All"
4. **No deep-link anchors** for sharing individual findings

---

## Accessibility

1. **Mermaid diagrams have no alt text** — no fallback if render fails
2. **Dark mode hardcoded** — doesn't respect `prefers-color-scheme`

---

## Code-Level Issues

1. **Dedup logic** uses magic numbers (60% keyword overlap threshold, hardcoded domain terms list) — fragile and untestable

---

## Suggested Improvements

### High impact

- Group findings by source (not just filter)

### Medium impact

- Add `prefers-color-scheme` media query
- Surface general tool scoping in report

### Low impact

- Finding deep-link anchors
- Copy by severity buttons
- File size distribution chart
