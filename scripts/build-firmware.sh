#!/usr/bin/env bash
# Builds every PlatformIO project of the repository.
# Used locally (pixi run build-firmware) and by the CI.
set -euo pipefail
cd "$(dirname "$0")/.."

# secrets.h is git-ignored: create it from the example where it is
# missing, so that a fresh clone (or the CI) can build
find firmware -name secrets.example.h | while read -r example; do
  secrets="$(dirname "$example")/secrets.h"
  if [ ! -f "$secrets" ]; then
    cp "$example" "$secrets"
    echo "Created $secrets from the example (placeholder values)"
  fi
done

find firmware -name platformio.ini | sort | while read -r ini; do
  dir=$(dirname "$ini")
  echo "== Building $dir"
  pio run -d "$dir"
done
