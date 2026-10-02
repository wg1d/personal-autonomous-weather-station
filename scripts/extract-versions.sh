#!/usr/bin/env bash
# Extracts the firmware of each published version (git tags v*) into
# docs/_versions/<tag>/, so that the chapters of a step can include the
# code of that step even after later steps have changed it.
# Called by render-book.sh and by the preview task.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf docs/_versions
for tag in $(git tag --list 'v*'); do
  # Versions published before firmware/paws existed have nothing to extract
  if git cat-file -e "$tag:firmware/paws" 2>/dev/null; then
    mkdir -p "docs/_versions/$tag"
    git archive "$tag" firmware/paws | tar -x -C "docs/_versions/$tag"
  fi
done
