---
allowed-tools: Read, Write, Edit, Glob
description: Initialize a project backlog (BACKLOG.md) and ensure CLAUDE.md has backlog instructions
---

# Initialize Project Backlog

Set up a BACKLOG.md file and configure CLAUDE.md with backlog management instructions.

## Steps

### 1. Check for existing BACKLOG.md

Use Glob to check if `BACKLOG.md` exists at the project root.

- **If it exists**: Read it, tell the user it already exists, and skip to step 2.
- **If it does not exist**: Create `BACKLOG.md` with this content:

```markdown
# Project Backlog

Tracking features, bugs, ideas, and TBDs for this project.

## Features


## Bugs


## Ideas


## TBDs

```

### 2. Configure CLAUDE.md

Use Glob to check if `CLAUDE.md` exists at the project root.

The instruction to add is:

```
- When implementing an item from BACKLOG.md, delete that item from the backlog file after the implementation is complete. Do not delete the file's section headings (Features, Bugs, Ideas, TBDs) — only remove the specific item.
```

- **If CLAUDE.md does not exist**: Create it with this content:

```markdown
## Agent Instructions

- When implementing an item from BACKLOG.md, delete that item from the backlog file after the implementation is complete. Do not delete the file's section headings (Features, Bugs, Ideas, TBDs) — only remove the specific item.
```

- **If CLAUDE.md exists**: Read it and check if it already contains a backlog-related instruction (e.g., mentions "BACKLOG.md" in context of deleting/removing items after implementation).
  - **If the instruction already exists**: Skip — tell the user it's already configured.
  - **If the instruction does not exist**: Look for a `## Agent Instructions` section (or similar like `## Agent Guidelines`).
    - If found, append the instruction as a new bullet under that section.
    - If no such section exists, append a new `## Agent Instructions` section with the instruction at the end of the file.

## Output

After completing both steps, give a brief summary of what was created or skipped:

```
Backlog initialized:
- BACKLOG.md: [created | already existed]
- CLAUDE.md: [created | updated | already configured]
```
