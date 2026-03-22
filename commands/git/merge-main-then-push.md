---
allowed-tools: Bash(git *), Read, Edit
description: Merge latest main into current branch, resolve conflicts, and push
---

## Context

- Current branch: !`git branch --show-current`
- Current git status: !`git status`
- Commits unique to this branch: !`git log --oneline main..HEAD`

## Your task

1. If current branch is `main`, abort with an error
2. If working tree is dirty (unstaged/uncommitted changes), abort and explain why
3. Fetch latest `origin/main`
4. Merge `origin/main` into the current branch
5. If there are merge conflicts:
   - Read each conflicted file and understand both sides
   - Resolve conflicts by combining changes intelligently
   - If any conflict is ambiguous, stop and ask before resolving
   - Run `git diff --check` to verify no conflict markers remain
   - Show a summary of how each conflict was resolved
   - Stage resolved files and complete the merge commit
6. Push to the remote branch

If the merge is clean (no conflicts), just push. Do not use any other tools besides those listed. Return a brief summary of what was merged and any conflicts resolved.
