#!/usr/bin/env bash
# Puts back a backup of the database of the backend, on the server.
#
# Usage: bash scripts/restore-backend.sh [day] [ssh-host]
#        day: 2026-10-07 (default: the newest backup); host: pi
#
# Runs deploy/restore.sh on the server, where the backend must be
# deployed first.
set -euo pipefail

DAY="${1:-newest}"
HOST="${2:-pi}"
ssh "$HOST" "bash ~/paws/backend/deploy/restore.sh $DAY"
