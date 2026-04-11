---
allowed-tools: Bash(git *), Read, Glob
description: Concise project status recap — recent activity, branch state, and open threads
---

# Project Status Recap

Give me a concise "manager's summary" of where this project stands. Follow these steps, then produce a SHORT summary.

## Steps (do all in parallel where possible)

IMPORTANT: Each Bash call MUST be a single git command — never chain commands with `&&`, `||`, or `;`. Run each git command as its own separate Bash tool call.

1. **Recent git activity**: Run `git log --oneline -n 5 --no-merges`.

2. **Uncommitted work**: Run `git status` (never use -uall) and `git stash list` as **separate** Bash calls. Note any dirty state or stashed work.

3. **Branch state**: Run `git branch -v` to see local branches. For the current branch, run `git rev-list --left-right --count HEAD...@{upstream}` (redirect stderr to /dev/null is fine). If the command fails or returns empty, it means no upstream is configured — note that in the summary instead of assuming 0/0. Note any branches other than main.

4. **BACKLOG.md**: Check if a `BACKLOG.md` file exists at the project root. If it does, read it and incorporate relevant items.

5. **Memory recall** (optional): If a `MEMORY.md` file exists in the memory system, read it and any referenced files to surface saved context about ongoing work, decisions, or blockers. Skip this step if no memory system is configured.

## Output format

After gathering all info, produce ONLY this output — nothing else:

```
## Project Status

**Last active**: [date of most recent commit]
**Current branch**: [branch] [ahead/behind info if any]
**Working tree**: [clean | dirty — brief description]

### What happened recently
- [3 bullet points max, grouped by theme, not individual commits]

### Open threads
- [Uncommitted work, non-main branches, stashed changes, backlog items, anything from memory that's still relevant]
- [If nothing: "None — clean slate."]
```

IMPORTANT rules:

- Be EXTREMELY concise. This is a glanceable summary, not a report.
- Collapse multiple related commits into one bullet ("added auth flow" not 5 separate commits).
- Do NOT show raw git output. Synthesize it.
- Do NOT explain what you did to gather info. Just show the summary.
- If the project has had no activity, say so in one line.
