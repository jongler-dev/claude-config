#!/usr/bin/env bash
# Usage: setup.sh
# Links all commands and skills from this repo to ~/.claude/
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

link_dirs() {
  local src_dir="$1"
  local dest_dir="$2"

  mkdir -p "$dest_dir"

  for src_subdir in "$src_dir"/*/; do
    [ -d "$src_subdir" ] || continue
    src_subdir="${src_subdir%/}"
    local name="$(basename "$src_subdir")"
    local dest_subdir="$dest_dir/$name"

    if [ -d "$dest_subdir" ] && [ ! -L "$dest_subdir" ]; then
      local bak="$dest_subdir.bak"
      if [ -e "$bak" ]; then
        echo "  warning: removing previous backup ${name}.bak/"
        rm -rf "$bak"
      fi
      mv "$dest_subdir" "$bak"
      ln -sfn "$src_subdir" "$dest_subdir"
      echo "  linked: $name/ (original backed up to ${name}.bak/)"
    else
      ln -sfn "$src_subdir" "$dest_subdir"
      echo "  linked: $name/"
    fi
  done
}

[ -d "$REPO_DIR/commands" ] || { echo "Error: commands/ directory not found"; exit 1; }
[ -d "$REPO_DIR/skills" ] || { echo "Error: skills/ directory not found"; exit 1; }

echo "Linking commands..."
link_dirs "$REPO_DIR/commands" "$CLAUDE_DIR/commands"

echo "Linking skills..."
link_dirs "$REPO_DIR/skills" "$CLAUDE_DIR/skills"

echo "Done."
