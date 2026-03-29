# Agent Skills Specification — Review Checklist

Use this checklist to audit a skill against the official Agent Skills specification (https://agentskills.io/specification).

## Structure

- [ ] Skill is a directory containing a `SKILL.md` file at its root
- [ ] Directory name matches the `name` field in frontmatter
- [ ] Optional directories follow convention: `scripts/`, `references/`, `assets/`
- [ ] No deeply nested reference chains (keep file references one level deep from SKILL.md)

## Frontmatter — Required Fields

- [ ] `name`: present, 1-64 characters
- [ ] `name`: only lowercase alphanumeric (a-z, 0-9) and hyphens
- [ ] `name`: does not start or end with a hyphen
- [ ] `name`: no consecutive hyphens (`--`)
- [ ] `description`: present, 1-1024 characters
- [ ] `description`: describes both what the skill does AND when to use it

## Frontmatter — Optional Fields

- [ ] `license`: if present, short license name or reference to bundled file
- [ ] `compatibility`: if present, 1-500 characters, describes environment requirements
- [ ] `metadata`: if present, is a map of string keys to string values
- [ ] `allowed-tools`: if present, is a space-delimited list of tool names

## Body Content

- [ ] SKILL.md total length is under 500 lines (recommended)
- [ ] Instructions body is under ~5000 tokens (recommended for progressive disclosure)
- [ ] Includes step-by-step instructions or clear workflow
- [ ] Includes examples of inputs and/or outputs (recommended)
- [ ] References to other files use relative paths from skill root

## Progressive Disclosure

- [ ] Tier 1 (metadata): name + description are meaningful standalone (~100 tokens)
- [ ] Tier 2 (instructions): full SKILL.md body is self-contained (<5000 tokens recommended)
- [ ] Tier 3 (resources): heavier content is in scripts/references/assets, loaded on demand

## Scripts (if present)

- [ ] Scripts are self-contained with inline dependencies where possible
- [ ] Scripts provide helpful error messages
- [ ] Scripts support `--help` or document their usage
- [ ] Scripts use structured output (JSON/CSV to stdout, diagnostics to stderr)
- [ ] Scripts are designed for non-interactive (agentic) use — no interactive prompts
- [ ] Scripts are idempotent where possible
- [ ] Destructive operations support `--dry-run`

## Description Quality (for trigger accuracy)

- [ ] Uses imperative phrasing ("Use when...")
- [ ] Focuses on user intent, not implementation details
- [ ] Includes specific keywords that help agents identify relevant tasks
- [ ] Covers trigger scenarios (when should this skill activate?)
- [ ] Covers non-trigger scenarios implicitly (not too broad)

## Security & Trust

- [ ] No XML angle brackets (`<` or `>`) in frontmatter values — frontmatter appears in the system prompt and could enable injection
- [ ] `name`: does not contain "claude" or "anthropic" (reserved words)
- [ ] No hardcoded secrets, API keys, or credentials (pre-scanned deterministically — check `file-inventory.json → secret_scan`)
- [ ] Bash commands are scoped (not open-ended shell access)
- [ ] File writes are limited to expected output locations
- [ ] Web/network access is justified and documented
- [ ] No arbitrary code execution from untrusted input
- [ ] `allowed-tools` is used to restrict tool access when possible
- [ ] No unescaped user input interpolated into shell commands (injection risk)
- [ ] Scripts that fetch URLs validate or constrain the target (no open redirects / SSRF via user-controlled URLs)
- [ ] Temporary files are written to `/tmp` or a scoped directory, not to the skill directory or user workspace

## Best Practices

See `best-practices.md` for the full best practices checklist (content quality, architecture, setup, memory, scripts, and judgment checks).
