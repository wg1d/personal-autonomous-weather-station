#!/usr/bin/env bash
# Empties the database and the station log of the backend, on the server,
# before the data collection starts.
#
# Usage: bash scripts/reset-backend.sh [ssh-host]
#        host: pi
#
# The backend creates a new, empty database when it starts and finds
# none. The old files are kept next to the new ones, with the suffix
# .before-reset, until the next reset replaces them.
set -euo pipefail

HOST="${1:-pi}"

read -r -p "Empty the database of the backend on $HOST? [y/N] " answer
if [[ "$answer" != "y" ]]; then
    echo "Nothing changed."
    exit 0
fi

ssh "$HOST" 'set -e
cd ~/paws/data
sudo systemctl stop paws-backend
for file in measurements.db station.log; do
    if [ -f "$file" ]; then
        mv "$file" "$file.before-reset"
    fi
done
sudo systemctl start paws-backend
echo "Database emptied; the old files end with .before-reset"'
