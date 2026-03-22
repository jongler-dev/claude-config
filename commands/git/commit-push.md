---
allowed-tools: Bash(git add *), Bash(git status *), Bash(git commit *), Bash(git push *)
description: Create a git commit and push to the current branch
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes to tracked files): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

Based on the above changes, create a single git commit, then push to the current branch.

Do not stage files that may contain secrets (e.g., .env, credentials, private keys, tokens). If unsure about a file, skip it and mention it to the user.

You have the capability to call multiple tools in a single response. Stage and create the commit using a single message. Do not use any other tools or do anything else. Do not send any other text or messages besides these tool calls, unless a step fails — in that case, briefly tell the user what went wrong.
