# Skill-Creator Review of skill-xray (2026-03-28)

Reviewed using the skill-creator methodology from the Anthropic skill-creator skill.

## High Priority (immediate value)

### 1. Add evals + test fixtures

This is the #1 gap. Without evals, you can't validate changes, detect regressions, or measure improvement. The skill-creator methodology makes this straightforward:

- Create `evals/evals.json` with 3-5 test prompts pointing at fixture skills
- Use skill-creator's eval runner to spawn skill-xray on each, then grade the outputs
- Key assertions: `analysis.json` has all required fields, `review.json` grade is in expected range, `report.html` renders without error

### 2. Optimize the `description` field

The current description is decent but could be tighter per the skill-creator's description optimization methodology. Specific issues:

- Lists trigger phrases but missing **non-trigger boundaries** — e.g., "Do NOT trigger when the user just wants to read a SKILL.md file or edit an existing skill"
- Doesn't follow the best-practices formula from your own `best-practices.md`: `[What it does] + [When to use it] + [Key capabilities]`
- Could benefit from the skill-creator's `run_loop.py` to A/B test descriptions against a trigger eval set

### 3. Structured finding format in reviewer

Currently in idea.md as a todo. This is high-value because it directly improves report usefulness — `file:line + quoted text + concrete fix` makes findings actionable instead of vague. The generate-report.py renderer would need a schema update too.

## Medium Priority (quality improvements)

### 4. Risk classification / capability tags

Already in idea.md. This would make the reviewer smarter — skip irrelevant checks for simple skills, emphasize security for skills with `HAS_SHELL` or `HANDLES_SECRETS`. The pre-analyze.py script is the right place to detect these (it already does secret scanning).

### 5. Tiered verdict (PASS / CONDITIONAL PASS / FAIL)

Also in idea.md. The letter grade answers "how good" but stakeholders often need a binary "can I ship this?" answer. Deterministic logic on top of the existing scores — low effort, high clarity.

### 6. Hallucination-pattern checks

Flag skill instructions that ask the LLM to do things LLMs are known to fail at (precise counting, exact string matching, multi-step arithmetic). This is a unique value-add that human reviewers would also miss.

## Lower Priority (polish)

- **Collapsible file sections in Deep Dive tab** — UX improvement from first feedback
- **README + LICENSE + CONTRIBUTING** — needed for open-source readiness
- **`--update-specs` flag** — keep spec-rules.md synced with agentskills.io

## What's already solid

- Architecture is clean — parallel agents, deterministic pre-analysis, Python report generation
- SKILL.md is well under the 500-line limit (151 lines)
- Progressive disclosure is good — agents read their own prompts, orchestrator stays lean
- Secret scanning in pre-analyze.py is a differentiator
- The `.claude/settings.json` sandboxing is a nice touch

## Recommended next step

Start with **#1 (evals)** — it unblocks everything else. Once you can measure, you can confidently tackle #2 (description optimization) and #3 (structured findings) knowing whether they actually improved things.
