#!/usr/bin/env bash
# Deploys the backend (backend/paws) to the server, in one command.
#
# Usage: bash scripts/deploy-backend.sh [ssh-host]   (default host: pi)
#
# 1. Refuses to deploy if backend/paws has changes that are not committed.
# 2. Sends only the committed files, with git archive, to ~/paws/backend.new.
# 3. Runs deploy/install.sh on the server, which puts this version in place
#    and restarts the service.
set -euo pipefail

HOST="${1:-pi}"
cd "$(git rev-parse --show-toplevel)"

if [ -n "$(git status --porcelain -- backend/paws)" ]; then
    echo "backend/paws has uncommitted changes: commit them first." >&2
    exit 1
fi
echo "Deploying $(git describe --tags --always) to $HOST"

# The archive holds backend/paws/...: --strip-components=2 removes these
# two folder levels when it is extracted
git archive --format=tar HEAD backend/paws | ssh "$HOST" \
    "rm -rf ~/paws/backend.new && mkdir -p ~/paws/backend.new &&
     tar -x -C ~/paws/backend.new --strip-components=2"

ssh "$HOST" "bash ~/paws/backend.new/deploy/install.sh"
