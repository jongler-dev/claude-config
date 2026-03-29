# Skill X-Ray backlog

## todos

1. suggesting to add a box to the overview tab with all user approval steps in the skill, so reviewers can quickly see "are there any user approvals? yes/no, how many, where are they?" without having to read through all the findings.
2. can we somehow highlight the user approval steps in the flow diagram?
3. sub-agents tend to fail "silently" - they lack an unknown bash permission and fail. this leads to Claude trying to figure out what to do, this makes the run time much longer.

```
   The issue is your Bash permission settings — when the subagents tried
   to run python3 or bash scripts, the permission system denied every attempt. This is the
   standard Claude Code permission prompt that asks "Allow Bash?" — but subagents running in
   the background can't show you that prompt, so the requests get auto-denied.

   This isn't a bug in the skill. It's how Claude Code's permission system works with
    background agents. There are a few ways to fix this for future runs:

- Pre-approve Bash in settings — allow Bash commands matching the skill's scripts
- Run agents in foreground (but then they'd be sequential, not parallel)
- Use dangerouslyDisableSandbox in the agent prompts (not recommended)

The cleanest fix is option 1. Want me to check your current permission settings and add
 an allow rule for the skill-xray scripts?

```

4. what does the "Key sections" contribute in the deep dive section? it's per-file info.
5. improve the review aspect of the skill:
6. come up with better categories for the findings, maybe with severity levels (e.g. critical, major, minor) to help prioritize fixes.
7. e.g. this is definitely not a warning:
   Warning Best Practice
   No gotchas or 'what NOT to do' section
8. more?
9. add an --update-specs flag so we can update the skill spec rules from https://agentskills.io/specification
10. add a skill readme, including instructions on how to run it, and maybe some screenshots of the output report. also add a license file (e.g. MIT) to clarify the usage rights of the code. we can also add a CONTRIBUTING.md file with guidelines for contributing to the project, if we want to make it open source and encourage contributions from the community.
11. **BEFORE PUBLISHING**:
12. run the skill on itself and see what it finds!
13. run skill-creator
14. run's lotan's skill

---

## UX review

see @UX_REVIEW.md

---

## Review by skill-creator skill

see @SKILL-CREATOR-REVIEW.md

---

## skill-xray VS skill-review

### Borrowing from skill-review → skill-xray reviewer improvements

Ideas from comparing skill-xray with the skill-review skill (sase-marketplace/common/skills/skill-review).
Secret pre-scanning was already implemented. The remaining items:

- [ ] **Risk classification with capability tags** — Scan for capability indicators during pre-analysis and tag the skill: `HAS_SCRIPTS`, `HAS_SHELL`, `HAS_EXTERNAL_API`, `MODIFIES_STATE`, `HANDLES_SECRETS`, `SENDS_COMMS`, `HAS_MCP_TOOLS`, `INSTALLS_PACKAGES`, `READ_ONLY`. Pass these to the reviewer agent so it can weight checks contextually (e.g. skip shell checks for read-only skills, emphasize security for skills that handle secrets). Also surface tags as badges in the overview tab.
- [ ] **Tiered verdict (PASS / CONDITIONAL PASS / FAIL)** — Add a deterministic verdict on top of the existing letter grade. Map review findings into blocking vs non-blocking categories, apply a decision tree (any blocking error → FAIL, any non-blocking error → CONDITIONAL PASS, else → PASS). Show the verdict front and center on the review tab alongside the grade. Keep the scores for the visual breakdown — they answer "how good", the verdict answers "go or no-go".
- [ ] **Hallucination-pattern checks** — Add a section to `best-practices.md` (or the reviewer agent prompt) that flags patterns where LLMs are known to fail: asking the model to count items precisely, do exact string matching, perform multi-step arithmetic, aggregate across large datasets, or make deterministic decisions that should be in code. These are skill-specific risks that a human reviewer might also miss.
- [ ] **Structured finding format (file:line + quoted text + concrete fix)** — Change the reviewer agent's output schema so each finding includes: severity, file path, line number, quoted text from the skill, a "Problem" explanation, and a "Fix" with the concrete change needed. Update `generate-report.py` to render these richer findings in the action items section.

### Borrowing from skill-xray → skill-review improvements

Features skill-review could add, inspired by skill-xray's strengths:

- [ ] **Visual HTML report option** — Offer a `--html` flag that generates a self-contained HTML report alongside the Markdown output. Useful for sharing review results outside of PRs or for archiving.
- [ ] **Architecture diagrams** — Auto-generate Mermaid sequence/flowchart diagrams showing the skill's execution flow and decision logic. Embed in the HTML report or as a collapsible section in the Markdown output. Helps reviewers understand what the skill does before reading findings.
- [ ] **Deep dive per-file analysis** — For each file in the skill, show its purpose, key sections, references to other files, and when it's loaded. Currently skill-review only evaluates quality — it doesn't explain the skill's structure to the reviewer.
- [ ] **Tool usage visualization** — Surface which tools are declared in frontmatter vs actually referenced in instructions vs MCP tools. Helps catch mismatches (declared but unused, or used but not declared).
- [ ] **External interaction mapping** — Catalog all URLs, filesystem paths, and external tool usage. Currently skill-review checks security of these but doesn't present them as a summary for the reviewer to scan.
- [ ] **Execution flow tracing** — Map the step-by-step execution path with decision points, loops, and error handling. Helps reviewers verify that logic/correctness findings actually match how the skill runs.
- [ ] **Narrative summary** — Generate a readable multi-paragraph explanation of what the skill does. Currently skill-review jumps straight to findings without giving the reviewer a "what am I looking at" overview.
- [ ] **Git URL support** — Accept a Git repository URL as input (not just local paths or PRs), shallow-clone it, and review the skill. Useful for reviewing skills before installing them.

---

```

```
