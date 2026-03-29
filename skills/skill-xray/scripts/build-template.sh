#!/usr/bin/env bash
# Combines template.html + template.css + template.js into a single built template.
# The built file has CSS/JS inlined — no {{CSS}} or {{JS}} placeholders remain.
#
# Usage: build-template.sh <assets-dir> <output-path>
# Example: build-template.sh ./assets /tmp/skill-xray/my-skill/built-template.html

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: build-template.sh <assets-dir> <output-path>" >&2
  exit 1
fi

ASSETS_DIR="$1"
OUTPUT="$2"

for f in template.html template.css template.js; do
  if [[ ! -f "$ASSETS_DIR/$f" ]]; then
    echo "Error: missing $ASSETS_DIR/$f" >&2
    exit 1
  fi
done

sed -e "/{{CSS}}/{
r $ASSETS_DIR/template.css
d
}" -e "/{{JS}}/{
r $ASSETS_DIR/template.js
d
}" "$ASSETS_DIR/template.html" > "$OUTPUT"

echo "$OUTPUT"
