#!/usr/bin/env bash
# Set up the working directory for a skill-xray run.
# Handles platform-specific timestamp detection (macOS vs Linux).
#
# Usage: setup-workdir.sh <skill-name>
# Output (stdout): the absolute path to the fresh working directory
# Exit codes: 0 = success, 1 = error

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: setup-workdir.sh <skill-name>" >&2
  exit 1
fi

SKILL_NAME="$1"
WORK_DIR="/tmp/skill-xray/${SKILL_NAME}"

if [[ -d "$WORK_DIR" ]]; then
  # Get creation timestamp — macOS vs Linux
  if [[ "$(uname)" == "Darwin" ]]; then
    TS=$(stat -f '%Sm' -t '%Y-%m-%dT%H-%M' "$WORK_DIR")
  else
    # Linux: use modification time as fallback (birth time not always available)
    TS=$(stat -c '%y' "$WORK_DIR" | cut -d'.' -f1 | tr ' :' 'T-')
  fi

  RENAMED="${WORK_DIR}-${TS}"
  mv "$WORK_DIR" "$RENAMED"
  echo "Previous run renamed to ${RENAMED}" >&2
fi

mkdir -p "$WORK_DIR"
echo "$WORK_DIR"
