#!/usr/bin/env bash
# Renders the book to HTML, and fails if a code include is missing.
# Used locally (pixi run book) and by the CI.
set -euo pipefail
cd "$(dirname "$0")/../docs"

# The include-code-files filter only warns when a file is missing:
# fail explicitly instead of publishing an empty code block
log=$(mktemp)
quarto render --to html "$@" 2>&1 | tee "$log"
if grep -q 'Cannot open file' "$log"; then
  echo "ERROR: some code includes could not be resolved" >&2
  exit 1
fi
