# Skill X-Ray backlog

## Overview

`/skill-xray` is a visual skill analysis tool.

It generates interactive HTML reports from Agent Skills directories with
architecture diagrams, file analysis, security review, and grading.

## todos

0. does the overview tab need to show the yaml description? if not, how will the user assess its validity if not reading through the rest of the info in other tabs?
1. suggesting to add a box to the overview tab with all user approval steps in the skill, so reviewers can quickly see "are there any user approvals? yes/no, how many, where are they?" without having to read through all the findings.
2. can we somehow highlight the user approval steps in the flow diagram?
3. what does the "Key sections" contribute in the deep dive section? it's per-file info.
4. improve the review aspect of the skill:
5. come up with better categories for the findings, maybe with severity levels (e.g. critical, major, minor) to help prioritize fixes.
6. e.g. this is definitely not a warning:
   Warning Best Practice
   No gotchas or 'what NOT to do' section
7. add an --update-specs flag so we can update the skill spec rules from https://agentskills.io/specification
8. add a skill readme, including instructions on how to run it, and maybe some screenshots of the output report. also add a license file (e.g. MIT) to clarify the usage rights of the code. we can also add a CONTRIBUTING.md file with guidelines for contributing to the project, if we want to make it open source and encourage contributions from the community.
9. **BEFORE PUBLISHING**:
10. run the skill on itself and see what it finds!
11. run skill-creator
12. run skill-review skills
13. how do we review a skill that has subagents defined outside the skill dir (in case of shared plugin skills)
14. how do we review a skill that calls other skills that are not under the same dir?

---

## UX review

see @UX_REVIEW.md

---

## Review by skill-creator skill

see @SKILL-CREATOR-REVIEW.md

---

## skill-xray VS skill-review

### Borrowing from skill-review → skill-xray reviewer improvements

Ideas from comparing skill-xray with other skill-review skills.

Secret pre-scanning was already implemented. The remaining items:

- [ ] **Risk classification with capability tags** — Scan for capability indicators during pre-analysis and tag the skill: `HAS_SCRIPTS`, `HAS_SHELL`, `HAS_EXTERNAL_API`, `MODIFIES_STATE`, `HANDLES_SECRETS`, `SENDS_COMMS`, `HAS_MCP_TOOLS`, `INSTALLS_PACKAGES`, `READ_ONLY`. Pass these to the reviewer agent so it can weight checks contextually (e.g. skip shell checks for read-only skills, emphasize security for skills that handle secrets). Also surface tags as badges in the overview tab.
- [ ] **Tiered verdict (PASS / CONDITIONAL PASS / FAIL)** — Add a deterministic verdict on top of the existing letter grade. Map review findings into blocking vs non-blocking categories, apply a decision tree (any blocking error → FAIL, any non-blocking error → CONDITIONAL PASS, else → PASS). Show the verdict front and center on the review tab alongside the grade. Keep the scores for the visual breakdown — they answer "how good", the verdict answers "go or no-go".
- [ ] **Hallucination-pattern checks** — Add a section to `best-practices.md` (or the reviewer agent prompt) that flags patterns where LLMs are known to fail: asking the model to count items precisely, do exact string matching, perform multi-step arithmetic, aggregate across large datasets, or make deterministic decisions that should be in code. These are skill-specific risks that a human reviewer might also miss.
- [ ] **Structured finding format (file:line + quoted text + concrete fix)** — Change the reviewer agent's output schema so each finding includes: severity, file path, line number, quoted text from the skill, a "Problem" explanation, and a "Fix" with the concrete change needed. Update `generate-report.py` to render these richer findings in the action items section.
