---
allowed-tools: Bash(git fetch *), Bash(git reset *), Bash(git checkout -- *)
description: Reset current branch to latest origin/main, preserving untracked files
---

## Context

- Current branch: !`git branch --show-current`
- Current git status: !`git status`

## Your task

Reset the current branch to the latest `origin/main` while preserving all untracked files.

1. If there are **staged or unstaged changes to tracked files**, abort and explain — the user should commit or stash first
2. Run `git fetch origin`
3. Run `git reset origin/main` (soft reset — moves HEAD without touching working tree)
4. Run `git checkout -- .` (restore tracked files to match the new HEAD)
5. Show the new HEAD commit (`git log --oneline -1`) and confirm untracked files are intact (`git status`)

Do not use `git reset --hard` (blocked by hooks). Do not delete or modify untracked files. Do not use any other tools.
