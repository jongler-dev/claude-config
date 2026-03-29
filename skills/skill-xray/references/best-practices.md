# Agent Skills — Best Practices

Use this checklist alongside `spec-rules.md` to evaluate skill quality beyond specification compliance. These practices come from real-world usage patterns and common failure modes.

## Content Quality

- [ ] **Don't state the obvious**: Skill content focuses on knowledge that pushes the agent out of its defaults, not things it already knows about coding or common libraries. The value is in org-specific context, edge cases, and opinionated choices.
- [ ] **Build a gotchas section**: Skill includes a gotchas or "what NOT to do" section capturing common failure points. This is the highest-signal content in any skill and should be updated over time as new edge cases are discovered.
- [ ] **Avoid railroading**: Instructions give the agent information and flexibility to adapt, rather than overly rigid step-by-step scripts. Reusable skills should not be so specific that they break when the situation varies slightly.
- [ ] **Content adds what the agent lacks**: Skill omits general knowledge the agent already has and focuses on what it couldn't derive from the codebase or its training data.
- [ ] **Skill is a coherent unit**: The skill represents one focused capability, not a grab-bag of loosely related instructions.

## Description & Triggers

- [ ] **Description is a trigger condition, not a summary**: The description field is scanned by the agent to decide "should I activate this skill?" — it should describe *when* to use the skill, not *what* it does abstractly.
  - Bad: `A comprehensive tool for monitoring pull request status across the development lifecycle.`
  - Good: `Monitors a PR until it merges. Trigger on 'babysit', 'watch CI', 'make sure this lands'.`
- [ ] **Description follows the structure formula**: `[What it does] + [When to use it] + [Key capabilities]`. Mention relevant file types if applicable.
- [ ] **Includes trigger phrases**: Description lists specific phrases or keywords a user might say that should activate this skill.
- [ ] **Covers non-trigger scenarios**: Description is not so broad that it false-triggers on unrelated tasks. Consider adding "Do NOT trigger when..." for ambiguous boundaries.

## Architecture & Progressive Disclosure

- [ ] **Uses the file system**: Skill treats its entire directory as context engineering — references, scripts, examples, and assets are split into separate files loaded on demand, not inlined into SKILL.md.
- [ ] **Progressive disclosure is well-implemented**: SKILL.md is lean (under ~5000 tokens). Heavier content lives in `references/`, `scripts/`, or `assets/` and is loaded only when needed.
- [ ] **Provides defaults over menus**: Skill makes smart defaults rather than presenting the user with a menu of options to choose from.
- [ ] **Favors procedures over declarations**: Instructions describe *how* to do things step-by-step, not just *what* the rules are.
- [ ] **Complexity is justified**: The skill's architecture matches what it actually does — not over-engineered for a simple task, not under-engineered for a complex one.
- [ ] **Critical instructions are prominent**: Important steps and constraints appear at the top of SKILL.md or under `## Important` / `## Critical` headers — not buried in the middle of a long document.
- [ ] **Use scripts for critical validations**: For checks that must not be skipped or misinterpreted, bundle a validation script rather than relying on language instructions. Code is deterministic; language interpretation isn't.
- [ ] **Composability**: Skill works well alongside other skills — it does not assume it's the only capability available or conflict with common skill patterns.

## Setup & Configuration

- [ ] **Setup is handled gracefully**: If the skill needs user-specific config (channels, credentials, preferences), it stores setup data in a config file (e.g., `config.json` in the skill directory) and prompts the user on first run if not configured.
  - Pattern: Use `!`cat ${CLAUDE_SKILL_DIR}/config.json 2>/dev/null || echo "NOT_CONFIGURED"`` in SKILL.md to inject config at load time, then branch on whether setup is needed.
- [ ] **Uses AskUserQuestion for structured input**: When the skill needs to collect multiple pieces of information from the user, it uses the AskUserQuestion tool rather than free-form prompting.

## Memory & Data Persistence

- [ ] **Persistent data uses stable storage**: Skills that store data (logs, caches, history) use `${CLAUDE_PLUGIN_DATA}` rather than the skill directory, which may be deleted on upgrade.
- [ ] **Memory is useful**: If the skill keeps history (e.g., previous runs, logs), the agent reads it to provide better results over time (e.g., delta-only standups, avoiding repeated suggestions).

## Scripts & Code

- [ ] **Provides composable helpers**: When the skill involves repetitive operations, it includes helper scripts or libraries that the agent can compose rather than reconstructing boilerplate each time.
- [ ] **Scripts are designed for agentic use**: Scripts use structured output (JSON/CSV to stdout, diagnostics to stderr), support `--help`, and require no interactive prompts.
- [ ] **Scripts don't embed credentials**: API keys, tokens, and passwords should be read from environment variables or config files, never hardcoded in script source. If a script needs credentials, it should fail with a clear message explaining which env var to set.
- [ ] **On-demand hooks are used appropriately**: If the skill registers session-scoped hooks, they are situational (not always-on) and clearly documented.

## Judgment Checks

These require reasoning about the skill as a whole rather than checking individual rules:

- [ ] **Name is accurate and descriptive**: A user or agent can understand the skill's purpose from the name alone.
- [ ] **No dead files**: Every file in the skill directory is referenced by at least one other file.
- [ ] **Flow is understandable from SKILL.md**: A developer unfamiliar with the skill can understand the overall flow by reading SKILL.md alone (even if details are in other files).
- [ ] **No fragile implicit assumptions**: The skill does not silently depend on specific environments, external services, or non-standard dependencies without documenting them. (Core tools like Read, Write, Bash, Glob, Grep, Agent, Edit are assumed available.)
