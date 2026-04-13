---
name: skill-xray
description: >
  Generate a visual HTML report for any Agent Skills skill directory. Use when
  the user wants to analyze, review, visualize, or understand a skill. Triggers
  on phrases like "x-ray this skill", "analyze this skill", "visualize skill",
  "review skill", "skill report", "skill-xray". Accepts a local folder path,
  a GitHub repository URL, or a GitHub PR URL. Produces a self-contained HTML
  report with Overview, How It Works, and Review tabs with a letter grade.
allowed-tools: Read Glob Grep Bash Agent Write TaskCreate TaskUpdate TaskGet TaskList AskUserQuestion
license: MIT
---

# Skill X-Ray

Generate a comprehensive visual report for any Agent Skills skill.

## Step 1: Parse Input

Determine the input source from the user's message. There are three modes:

### Mode A: Local path (default)
- If the user provides a local path, use it
- If the user says "this skill" or similar, ask which skill they mean
- Validate that the path exists and contains a `SKILL.md` file

### Mode B: Git repository URL
- If the user provides a git repository URL (GitHub, GitLab, etc.), run the clone script:
  ```bash
  bash <skill-dir>/scripts/clone-skill.sh <git-url>
  ```
- The script handles: shallow clone to `/tmp/skill-xray/<repo-name>-repo/`, locating `SKILL.md` (checks root then one level deep), and error reporting
- On success, the script prints the skill directory path to stdout — use that as the skill directory for the rest of the flow
- **On failure** (invalid URL, auth error, network issues, no SKILL.md found), the script exits non-zero with an error message on stderr. **Report the error to the user and stop — do not continue the pipeline.**
- Store the git URL — it will be passed to the agents so the report header shows the GitHub URL instead of a local path

### Mode C: GitHub PR URL
- If the user provides a GitHub PR URL (contains `/pull/`), run the fetch script:
  ```bash
  bash <skill-dir>/scripts/fetch-pr.sh <pr-url> <work-dir>
  ```
  Note: `<work-dir>` must already exist — run Step 2 first with a temporary skill name derived from the repo name, then pass it here.
- The script handles: shallow clone, fetching the PR head ref, checking out the PR branch, locating `SKILL.md`, and writing `pr-metadata.json` to the work directory
- **Exit code 0**: success — stdout contains the skill directory path
- **Exit code 1**: error — report to user and stop
- **Exit code 2**: multiple `SKILL.md` files found — stdout contains all candidate paths (one per line). Use `AskUserQuestion` to ask the user which skill directory to analyze, then use that path.
- Store the PR URL as the git URL for the report header

If both a local path and a URL are provided, prioritize the URL and print a warning that the local path is being ignored.

### Extract skill name

Extract the skill name from the directory name (e.g., `/path/to/my-skill` → `my-skill`).

## Step 2: Set Up Working Directory

Run the setup script to handle platform-specific workdir creation (renames previous runs automatically):

```bash
bash <skill-dir>/scripts/setup-workdir.sh <skill-name>
```

The script prints the work directory path to stdout (e.g., `/tmp/skill-xray/my-skill/`). If it renamed a previous run, it prints a message to stderr — relay that to the user.

## Step 3: Run Pre-Analysis & Write Manifest

Run the deterministic pre-analysis script:

```bash
python3 <skill-dir>/scripts/pre-analyze.py <skill-path> <work-dir>/file-inventory.json
```

This produces `file-inventory.json` with: file tree, frontmatter, line counts, and structural spec checks — all data that needs zero LLM reasoning.

Then write a `manifest.json` to the work directory:

```json
{
  "skill_dir": "<absolute-path-to-skill>",
  "skill_name": "<skill-name>",
  "work_dir": "<work-dir>",
  "git_url": "<git-url-or-null>",
  "mode": "local | github | pr",
  "skill_xray_dir": "<absolute-path-to-skill-xray-skill>"
}
```

Write this file using the Write tool. `skill_xray_dir` is the directory containing this SKILL.md. Set `mode` to `"local"`, `"github"`, or `"pr"` based on the input source. For PR mode, `git_url` should be the PR URL.

## Step 4: Create Tasks

Create the following tasks to track progress:

1. **Analyze skill** — Run the analyzer agent
2. **Review skill** — Run the reviewer agent
3. **Generate report** — Build template and generate HTML

## Step 5: Run Analyzer & Reviewer in Parallel

Mark both "Analyze skill" and "Review skill" tasks as in_progress.

Spawn **two sub-agents in parallel** in a single message. **Do NOT use `run_in_background`** — foreground parallel agents already run concurrently and handle permission prompts correctly.

### Agent A: Analyzer
Tell the agent:
- Read `<work-dir>/manifest.json` for all paths
- Read `<skill-xray-dir>/agents/analyzer.md` and follow those instructions
- Output: `<work-dir>/analysis.json`

### Agent B: Reviewer
Tell the agent:
- Read `<work-dir>/manifest.json` for all paths
- Read `<skill-xray-dir>/agents/reviewer.md` and follow those instructions
- Output: `<work-dir>/review.json`

Wait for both to complete. Mark both tasks as completed.

**Important**: Do NOT read the agent prompt files yourself. Each agent reads its own prompt. You only pass the manifest path and the path to the agent's prompt file.

## Step 6: Build Template and Generate Report

Mark the "Generate report" task as in_progress.

Run the build script to combine CSS/JS into a single template file, then run the report generator script:

```bash
bash <skill-dir>/scripts/build-template.sh <skill-dir>/assets <work-dir>/built-template.html
```

```bash
python3 <skill-dir>/scripts/generate-report.py <work-dir>/analysis.json <work-dir>/review.json <work-dir>/built-template.html
```

The report generator validates the JSON schemas of both analysis.json and review.json before rendering. If it exits non-zero, report the error and stop.

The script writes `report.html` to the same directory as `analysis.json`.

Mark the task as completed.

## Step 7: Deliver

Open the report in the user's default browser:

```bash
open <work-dir>/report.html
```

Tell the user:
- Where the report file is located
- A one-line summary of the skill's grade from the review

## Important Notes

- Sub-agents read their own prompt files from `agents/`. Do not read these files in the orchestrator — it wastes context.
- Analyzer and reviewer run **in parallel** — neither depends on the other's output.
- Both agents receive paths via `manifest.json` — single source of truth, no path interpolation needed.
- Both agents consume `file-inventory.json` for pre-computed deterministic data (file tree, frontmatter, structural checks).
- Report generation is handled by a Python script (not an agent) for speed — it runs in under a second.
- The Python script validates JSON schemas before rendering. If an agent produced malformed output, it fails fast with a clear error.
- All intermediate files go to `/tmp/skill-xray/<skill-name>/` to avoid polluting the workspace.
- If any sub-agent or script fails, report the error to the user and stop. Do not continue the pipeline with missing data.
