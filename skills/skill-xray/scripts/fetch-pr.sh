#!/usr/bin/env bash
# Fetch a GitHub PR into /tmp/skill-xray/ and locate its SKILL.md.
#
# Usage: fetch-pr.sh <pr-url> [work-dir]
#   pr-url:   Full GitHub PR URL (e.g., https://github.com/owner/repo/pull/42)
#   work-dir: Optional. If provided, writes pr-metadata.json there.
#
# Output on success (stdout): the absolute path to the directory containing SKILL.md
# Exit codes: 0 = success, 1 = error (message on stderr)
#
# If multiple SKILL.md files are found, prints all candidate paths (one per line)
# and exits with code 2 — the caller should ask the user which one to use.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: fetch-pr.sh <pr-url> [work-dir]" >&2
  exit 1
fi

PR_URL="$1"
WORK_DIR="${2:-}"

# Parse PR URL: https://github.com/owner/repo/pull/123
if [[ "$PR_URL" =~ github\.com/([^/]+)/([^/]+)/pull/([0-9]+) ]]; then
  OWNER="${BASH_REMATCH[1]}"
  REPO="${BASH_REMATCH[2]}"
  PR_NUM="${BASH_REMATCH[3]}"
else
  echo "Error: could not parse PR URL: $PR_URL" >&2
  echo "Expected format: https://github.com/owner/repo/pull/123" >&2
  exit 1
fi

REPO_NAME="${REPO%.git}"

XRAY_BASE="$(python3 -c "import os; print(os.path.realpath('/tmp/skill-xray'))")"
mkdir -p "$XRAY_BASE"
CLONE_DIR="${XRAY_BASE}/${REPO_NAME}-repo"

# Clean up any previous clone
if [[ -d "$CLONE_DIR" ]]; then
  rm -rf "$CLONE_DIR"
fi

# Clone the repo (shallow) then fetch the PR ref
REPO_URL="https://github.com/${OWNER}/${REPO}.git"
if ! git clone --depth 1 --single-branch "$REPO_URL" "$CLONE_DIR" 2>/tmp/skill-xray-pr-err.log; then
  ERR=$(cat /tmp/skill-xray-pr-err.log)
  echo "Error: git clone failed for $REPO_URL" >&2
  echo "$ERR" >&2
  rm -f /tmp/skill-xray-pr-err.log
  exit 1
fi
rm -f /tmp/skill-xray-pr-err.log

# Fetch the PR head
if ! git -C "$CLONE_DIR" fetch --depth 1 origin "pull/${PR_NUM}/head:pr-${PR_NUM}" 2>/tmp/skill-xray-pr-err.log; then
  ERR=$(cat /tmp/skill-xray-pr-err.log)
  echo "Error: could not fetch PR #${PR_NUM}" >&2
  echo "$ERR" >&2
  rm -f /tmp/skill-xray-pr-err.log
  exit 1
fi
rm -f /tmp/skill-xray-pr-err.log

git -C "$CLONE_DIR" checkout "pr-${PR_NUM}" --quiet

# Write PR metadata if work-dir provided
if [[ -n "$WORK_DIR" ]]; then
  # Get PR metadata via gh CLI
  PR_JSON=$(gh pr view "$PR_NUM" --repo "${OWNER}/${REPO}" --json title,author,baseRefName,headRefName,changedFiles,files,url 2>/dev/null || echo '{}')

  if [[ "$PR_JSON" != '{}' ]]; then
    echo "$PR_JSON" > "${WORK_DIR}/pr-metadata.json"
  else
    # Fallback: minimal metadata without gh CLI
    python3 -c "
import json, sys
json.dump({
    'number': ${PR_NUM},
    'url': '${PR_URL}',
    'owner': '${OWNER}',
    'repo': '${REPO}',
}, sys.stdout, indent=2)
" > "${WORK_DIR}/pr-metadata.json"
  fi
fi

# Locate SKILL.md — first try the PR's changed files (precise, no depth limit)
SKILL_PATHS=$(gh pr view "$PR_NUM" --repo "${OWNER}/${REPO}" --json files --jq '.files[].path' 2>/dev/null | grep '/SKILL\.md$' || true)
if [[ -n "$SKILL_PATHS" ]]; then
  COUNT=$(echo "$SKILL_PATHS" | wc -l | tr -d ' ')
  if [[ "$COUNT" -eq 1 ]]; then
    FULL_PATH="${CLONE_DIR}/${SKILL_PATHS}"
    if [[ -f "$FULL_PATH" ]]; then
      echo "$(dirname "$FULL_PATH")"
      exit 0
    fi
  else
    # Multiple SKILL.md files changed — output all candidates, exit 2
    while IFS= read -r p; do
      dirname "${CLONE_DIR}/${p}"
    done <<< "$SKILL_PATHS"
    exit 2
  fi
fi

# Fallback: search the repo tree
if [[ -f "$CLONE_DIR/SKILL.md" ]]; then
  echo "$CLONE_DIR"
  exit 0
fi

FOUND=$(find "$CLONE_DIR" -maxdepth 6 -name "SKILL.md" -type f 2>/dev/null)

if [[ -z "$FOUND" ]]; then
  echo "Error: no SKILL.md found in PR #${PR_NUM} of ${OWNER}/${REPO}" >&2
  echo "Searched: $CLONE_DIR (up to 6 levels deep)" >&2
  exit 1
fi

COUNT=$(echo "$FOUND" | wc -l | tr -d ' ')
if [[ "$COUNT" -eq 1 ]]; then
  echo "$(dirname "$FOUND")"
  exit 0
fi

# Multiple SKILL.md files — output all candidates, exit 2
echo "$FOUND" | while read -r f; do dirname "$f"; done
exit 2
