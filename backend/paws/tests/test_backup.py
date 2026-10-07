"""Tests of the daily backup."""

import gzip
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from paws_server import backup, database
from paws_server.dashboard import backup_text
from paws_server.protocol import parse_rows

HEADER = "timestamp,time_valid,temperature_c,humidity_pct,pressure_hpa\n"
ROWS = ("2026-10-05T10:00:00Z,1,21.50,48.20,1012.30\n"
        "2026-10-05T10:15:00Z,1,21.60,,1012.20\n")
NOW = datetime(2026, 10, 7, 3, 30, tzinfo=timezone.utc)


@pytest.fixture
def data_dir(tmp_path):
    connection = database.connect(tmp_path / "measurements.db")
    database.insert_rows(connection, parse_rows(HEADER + ROWS))
    connection.close()
    (tmp_path / "station.log").write_text("=== 2026-10-05T10:00:00Z ===\n")
    return tmp_path


def test_backup_holds_the_database_and_the_log(data_dir, tmp_path):
    status = backup.run(data_dir, "", NOW)
    assert status["ok"]
    folder = data_dir / "backups"
    # The copy, once uncompressed, is a database with the same rows
    restored = tmp_path / "restored.db"
    restored.write_bytes(gzip.decompress(
        (folder / "measurements-2026-10-07.db.gz").read_bytes()))
    rows = sqlite3.connect(restored).execute(
        "SELECT COUNT(*) FROM measurements").fetchone()[0]
    assert rows == 2
    assert gzip.decompress((folder / "station-2026-10-07.log.gz")
                           .read_bytes()) == b"=== 2026-10-05T10:00:00Z ===\n"
    assert backup.last_status(data_dir) == status


def test_only_the_last_days_are_kept(data_dir):
    for day in range(10):
        backup.run(data_dir, "", NOW + timedelta(days=day))
    kept = sorted(path.name for path in
                  (data_dir / "backups").glob("measurements-*"))
    assert len(kept) == backup.KEEP
    assert kept[0] == "measurements-2026-10-10.db.gz"


def test_failure_is_recorded(data_dir, monkeypatch):
    # rclone cannot be started: the backup stays on the server, and the
    # failure is written for the dashboard
    monkeypatch.setenv("PATH", "")
    status = backup.run(data_dir, "Proton:paws_backup", NOW)
    assert not status["ok"]
    assert status["error"]
    assert (data_dir / "backups" / "measurements-2026-10-07.db.gz").exists()


def test_dashboard_tells_the_state_of_the_backup():
    status = {"time": "2026-10-07T03:30:00+00:00", "ok": True,
              "remote": "Proton:paws_backup", "error": None}
    assert backup_text(status, NOW) == (
        False, "Last backup: 07 Oct, 03:30, copied to Proton:paws_backup.")
    # Three days later, without a new backup: late
    late, _ = backup_text(status, NOW + timedelta(days=3))
    assert late
    late, text = backup_text({**status, "ok": False, "error": "no network"},
                             NOW)
    assert late and text.endswith("failed: no network")
    assert backup_text(None, NOW) == (False, "No backup yet.")
