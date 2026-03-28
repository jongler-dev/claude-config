#!/usr/bin/env bash
# Usage: link-skill.sh <skill-name> [skill-name...]
# Links a skill from this repo's skills/ directory to ~/.claude/skills/
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"

if [ $# -eq 0 ]; then
  echo "Usage: $(basename "$0") <skill-name> [skill-name...]"
  echo "Links a skill from this repo's skills/ directory to ~/.claude/skills/"
  echo ""
  echo "Available skills:"
  for d in "$REPO_DIR/skills"/*/; do
    [ -d "$d" ] && echo "  $(basename "$d")"
  done
  exit 1
fi

mkdir -p "$CLAUDE_SKILLS_DIR"

for skill in "$@"; do
  src="$REPO_DIR/skills/$skill"

  if [ ! -d "$src" ]; then
    echo "Error: skill '$skill' not found in $REPO_DIR/skills/"
    exit 1
  fi

  dest="$CLAUDE_SKILLS_DIR/$skill"

  if [ -d "$dest" ] && [ ! -L "$dest" ]; then
    bak="$dest.bak"
    [ -e "$bak" ] && rm -rf "$bak"
    mv "$dest" "$bak"
    ln -sfn "$src" "$dest"
    echo "Linked: $skill (original backed up to ${skill}.bak/)"
  else
    ln -sfn "$src" "$dest"
    echo "Linked: $skill"
  fi
done
