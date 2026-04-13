#!/usr/bin/env bash
# Clone a skill from a git URL into /tmp/skill-xray/ and locate its SKILL.md.
#
# Usage: clone-skill.sh <git-url>
# Output on success (stdout): the absolute path to the directory containing SKILL.md
# Exit codes: 0 = success, 1 = error (message on stderr)

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: clone-skill.sh <git-url>" >&2
  exit 1
fi

GIT_URL="$1"

# Derive a directory name from the URL (strip trailing .git, take last path segment)
REPO_NAME=$(basename "$GIT_URL" .git)
if [[ -z "$REPO_NAME" ]]; then
  echo "Error: could not derive repository name from URL: $GIT_URL" >&2
  exit 1
fi

XRAY_BASE="$(python3 -c "import os; print(os.path.realpath('/tmp/skill-xray'))")"
mkdir -p "$XRAY_BASE"
CLONE_DIR="${XRAY_BASE}/${REPO_NAME}-repo"

# Clean up any previous clone at the same path
if [[ -d "$CLONE_DIR" ]]; then
  rm -rf "$CLONE_DIR"
fi

# Clone (shallow, single branch, 30s timeout)
if ! git clone --depth 1 --single-branch "$GIT_URL" "$CLONE_DIR" 2>/tmp/skill-xray-clone-err.log; then
  ERR=$(cat /tmp/skill-xray-clone-err.log)
  echo "Error: git clone failed for $GIT_URL" >&2
  echo "$ERR" >&2
  rm -f /tmp/skill-xray-clone-err.log
  exit 1
fi
rm -f /tmp/skill-xray-clone-err.log

# Locate SKILL.md — check repo root first, then immediate subdirectories
if [[ -f "$CLONE_DIR/SKILL.md" ]]; then
  echo "$CLONE_DIR"
  exit 0
fi

# Search one level deep
FOUND=$(find "$CLONE_DIR" -maxdepth 2 -name "SKILL.md" -type f 2>/dev/null | head -1)
if [[ -n "$FOUND" ]]; then
  echo "$(dirname "$FOUND")"
  exit 0
fi

echo "Error: no SKILL.md found in cloned repository $GIT_URL" >&2
echo "Searched: $CLONE_DIR (root and immediate subdirectories)" >&2
exit 1
