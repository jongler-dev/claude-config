---
allowed-tools: Bash(git *), Bash(gh pr create *)
description: Create a feature branch from main, push, and open a PR
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

Based on the above changes:

1. Create a descriptive feature branch named `<username>_<short-name>` (e.g., `jane_extract-drift-subagents`). Get the username from `whoami`. No type prefixes like `refactor/` or `fix/`.
2. Create the branch, stage all relevant changes, and commit with a conventional commit message
3. Push the branch with `-u`
4. Create a PR against `main` using `gh pr create` with a summary and test plan

Do not use any other tools. Return the PR URL when done.
