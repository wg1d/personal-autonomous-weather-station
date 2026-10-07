"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/backup.py

Description:
The daily backup of the data (BN1 · No data loss). Each night, the
systemd timer paws-backup.timer runs:

    python -m paws_server.backup

which:
1. copies the database with the backup function of SQLite, which gives
   a consistent copy even while a row is being written, and the log of
   the station, both compressed with gzip, into data/backups/, named
   after the day (measurements-2026-10-07.db.gz, station-2026-10-07.log.gz);
2. keeps the copies of the last KEEP days, and deletes the older ones;
3. copies the backups to a cloud storage with rclone (Proton Drive on our
   server), where the copies older than KEEP days are deleted as well;
4. writes the result to data/backups/last_backup.json, shown by the Data
   tab of the dashboard.

Settings (environment variables): PAWS_DATA_DIR, the data folder, and
PAWS_BACKUP_REMOTE, the folder of the cloud storage in the format of
rclone ("Proton:paws_backup" by default; empty: no copy outside).

Dependencies: Python standard library; rclone, for the cloud storage.
"""

import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# How many days of backups are kept, on the server and outside
KEEP = 7

DEFAULT_REMOTE = "Proton:paws_backup"
STATUS_FILE = "last_backup.json"


def copy_database(database, target):
    """Copies the database into a gzip file, consistently.

    The backup function of SQLite copies the database page by page,
    without blocking the server, and the copy matches one moment: a row
    written during the copy is either fully in it, or not at all.
    """
    plain = target.with_suffix("")             # without the .gz suffix
    source = sqlite3.connect(database)
    copy = sqlite3.connect(plain)
    try:
        source.backup(copy)
    finally:
        copy.close()
        source.close()
    compress(plain, target)
    plain.unlink()


def compress(source, target):
    """Writes a gzip copy of a file."""
    with open(source, "rb") as original, gzip.open(target, "wb") as packed:
        shutil.copyfileobj(original, packed)


def prune(folder, prefix, keep):
    """Keeps the keep newest files of a kind, deletes the older ones.

    The names hold the day ("measurements-2026-10-07.db.gz"): in the
    alphabetical order, they are also in the order of time.
    """
    files = sorted(folder.glob(f"{prefix}-*.gz"))
    for old in files[:-keep]:
        old.unlink()


def copy_outside(folder, remote, keep):
    """Copies the backups to the cloud storage, and deletes there the
    copies older than keep days.

    rclone copy only adds and updates files, never deletes: the old
    copies are deleted by rclone delete, by their age.
    """
    subprocess.run(["rclone", "copy", str(folder), remote],
                   check=True, capture_output=True, timeout=600)
    subprocess.run(["rclone", "delete", remote, "--min-age", f"{keep}d"],
                   check=True, capture_output=True, timeout=600)


def run(data_dir, remote, now):
    """Makes the backup of the day; returns its result, also written to
    last_backup.json: {"time", "ok", "remote", "error"}."""
    folder = data_dir / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    day = f"{now:%Y-%m-%d}"
    status = {"time": now.isoformat(timespec="seconds"), "ok": False,
              "remote": remote or None, "error": None}
    try:
        copy_database(data_dir / "measurements.db",
                      folder / f"measurements-{day}.db.gz")
        log = data_dir / "station.log"
        if log.exists():
            compress(log, folder / f"station-{day}.log.gz")
        prune(folder, "measurements", KEEP)
        prune(folder, "station", KEEP)
        if remote:
            copy_outside(folder, remote, KEEP)
        status["ok"] = True
    except (OSError, sqlite3.Error, subprocess.SubprocessError) as error:
        # The message of rclone, when it failed, is in its error output
        details = getattr(error, "stderr", None)
        status["error"] = (details.decode(errors="replace").strip()
                           if details else str(error))
    (folder / STATUS_FILE).write_text(json.dumps(status))
    return status


def last_status(data_dir):
    """The result of the last backup, or None if there was none."""
    try:
        return json.loads((data_dir / "backups" / STATUS_FILE).read_text())
    except (OSError, ValueError):
        return None


def main():
    data_dir = Path(os.environ.get("PAWS_DATA_DIR", "data"))
    remote = os.environ.get("PAWS_BACKUP_REMOTE", DEFAULT_REMOTE)
    # The local time of the server: the day of the name is its day
    status = run(data_dir, remote, datetime.now().astimezone())
    print(json.dumps(status))
    # A failure ends with an error code: systemd then shows the service
    # as failed
    sys.exit(0 if status["ok"] else 1)


if __name__ == "__main__":
    main()
