#!/usr/bin/env bash
# Runs on the server, called by scripts/deploy-backend.sh once the new
# version is extracted in ~/paws/backend.new.
#
# ~/paws/
# ├── backend/   the running version, replaced by backend.new
# ├── venv/      the Python environment, updated by uv sync
# └── data/      the database, the log and their backups, never touched
#                here
set -euo pipefail

# The tools, installed only if they are missing: a new server needs nothing
# before its first deployment.
# uv, the Python packaging tool: it also downloads the Python version of
# .python-version
if [ ! -x ~/.local/bin/uv ]; then
    echo "Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
# rclone, which copies the backups to the cloud storage. The package of the
# system can be too old for Proton Drive: below version 1.69, the official
# script installs the current version
rclone_ok() {
    command -v rclone > /dev/null || return 1
    local version
    version=$(rclone version | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    [ "${version%%.*}" -gt 1 ] || [ "${version#*.}" -ge 69 ]
}
if ! rclone_ok; then
    echo "Installing rclone"
    curl -fsS https://rclone.org/install.sh | sudo bash
fi

cd ~/paws
mkdir -p data

# Install the dependencies frozen in uv.lock before stopping anything: if
# this fails, the running version keeps running
cd backend.new
UV_PROJECT_ENVIRONMENT=~/paws/venv ~/.local/bin/uv sync --locked --no-dev
cd ..

# Replace the whole application folder: a file deleted from the project
# can never stay on the server
rm -rf backend
mv backend.new backend

# Install the services and the timer of the backup, with the user and
# home folder of this server
for unit in paws-backend.service paws-backup.service paws-backup.timer; do
    sed -e "s|@USER@|$USER|g" -e "s|@HOME@|$HOME|g" \
        "backend/deploy/$unit" \
        | sudo tee "/etc/systemd/system/$unit" > /dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --quiet paws-backend
sudo systemctl enable --quiet --now paws-backup.timer
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
