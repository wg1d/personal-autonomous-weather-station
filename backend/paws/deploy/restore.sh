#!/usr/bin/env bash
# Runs on the server, called by scripts/restore-backend.sh: puts back a
# backup of the database.
#
# Usage: bash restore.sh [day]   (day: 2026-10-07; default: the newest)
#
# The backup is taken from ~/paws/data/backups, or, when it is not there
# (a server installed again after a failure), from the cloud storage.
# The database replaced is kept as measurements.db.before-restore.
set -euo pipefail

DAY="${1:-newest}"
REMOTE="${PAWS_BACKUP_REMOTE:-Proton:paws_backup}"
cd ~/paws/data
mkdir -p backups

if [ "$DAY" = newest ]; then
    FILE=$(ls backups/measurements-*.db.gz 2>/dev/null | tail -n 1 || true)
else
    FILE="backups/measurements-$DAY.db.gz"
fi

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "Not on the server: taking the backup from $REMOTE"
    if [ "$DAY" = newest ]; then
        NAME=$(rclone lsf "$REMOTE" --include "measurements-*.db.gz" \
               | sort | tail -n 1)
    else
        NAME="measurements-$DAY.db.gz"
    fi
    if [ -z "$NAME" ]; then
        echo "No backup found in $REMOTE" >&2
        exit 1
    fi
    rclone copyto "$REMOTE/$NAME" "backups/$NAME"
    FILE="backups/$NAME"
fi

# Stop the server while its database is replaced
sudo systemctl stop paws-backend
if [ -f measurements.db ]; then
    mv measurements.db measurements.db.before-restore
fi
gunzip -c "$FILE" > measurements.db
sudo systemctl start paws-backend
echo "Restored $FILE; the database replaced is kept as" \
     "measurements.db.before-restore"
