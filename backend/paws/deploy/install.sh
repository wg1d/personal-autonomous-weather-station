#!/usr/bin/env bash
# Runs on the server, called by scripts/deploy-backend.sh once the new
# version is extracted in ~/paws/backend.new.
#
# ~/paws/
# ├── backend/   the running version, replaced by backend.new
# ├── venv/      the Python environment, updated by uv sync
# └── data/      the database and the log, never touched here
set -euo pipefail

cd ~/paws
mkdir -p data

# Install the dependencies frozen in uv.lock before stopping anything: if
# this fails, the running version keeps running
cd backend.new
UV_PROJECT_ENVIRONMENT=~/paws/venv ~/.local/bin/uv sync --frozen --no-dev
cd ..

# Replace the whole application folder: a file deleted from the project
# can never stay on the server
rm -rf backend
mv backend.new backend

# Install the service, with the user and home folder of this server
sed -e "s|@USER@|$USER|g" -e "s|@HOME@|$HOME|g" \
    backend/deploy/paws-backend.service \
    | sudo tee /etc/systemd/system/paws-backend.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable --quiet paws-backend
sudo systemctl restart paws-backend

# Check that the server answers (it needs a few seconds to start)
for attempt in $(seq 1 20); do
    if curl -fsS http://localhost:8080/ > /dev/null 2>&1; then
        echo "Deployed: the backend answers on port 8080"
        exit 0
    fi
    sleep 3
done
echo "The backend does not answer: see 'journalctl -u paws-backend'" >&2
exit 1
