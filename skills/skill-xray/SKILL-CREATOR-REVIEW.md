# Skill-Creator Review of skill-xray (2026-03-28)

Reviewed using the skill-creator methodology from the Anthropic skill-creator skill.
Updated 2026-04-14.

## High Priority (immediate value)

### 1. Expand evals coverage

Basic eval structure exists (`evals/evals.json`, `evals/test_regression.py`, fixtures) but coverage is thin. Needs:

- More test prompts covering edge cases (missing files, malformed frontmatter, large skills)
- Use skill-creator's eval runner to spawn skill-xray on each, then grade the outputs
- Run the skill on itself as a smoke test

### 2. Optimize the `description` field

The current description is decent but could be tighter per the skill-creator's description optimization methodology. Specific issues:

- Lists trigger phrases but missing **non-trigger boundaries** — e.g., "Do NOT trigger when the user just wants to read a SKILL.md file or edit an existing skill"
- Doesn't follow the best-practices formula from your own `best-practices.md`: `[What it does] + [When to use it] + [Key capabilities]`
- Could benefit from the skill-creator's `run_loop.py` to A/B test descriptions against a trigger eval set

### 3. Structured finding format in reviewer

This is high-value because it directly improves report usefulness — `file:line + quoted text + concrete fix` makes findings actionable instead of vague. The generate-report.py renderer would need a schema update too.

## Medium Priority (quality improvements)

### 4. Tiered verdict (PASS / CONDITIONAL PASS / FAIL)

The letter grade answers "how good" but stakeholders often need a binary "can I ship this?" answer. Deterministic logic on top of the existing scores — low effort, high clarity.

### 5. Hallucination-pattern checks

Flag skill instructions that ask the LLM to do things LLMs are known to fail at (precise counting, exact string matching, multi-step arithmetic). This is a unique value-add that human reviewers would also miss.

## Lower Priority (polish)

- **Collapsible file sections in Deep Dive tab** — UX improvement from first feedback
- **README + LICENSE + CONTRIBUTING** — needed for open-source readiness
- **`--update-specs` flag** — keep spec-rules.md synced with agentskills.io

## Recommended next step

Expand evals (#1) — it unblocks confident iteration on #2 (description optimization) and #3 (structured findings).
