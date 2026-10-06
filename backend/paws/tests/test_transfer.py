"""Tests of the export and of the files uploaded by hand (Data tab)."""

import pytest

from paws_server import database, logs, transfer
from paws_server.protocol import parse_rows

HEADER = "timestamp,time_valid,temperature_c,humidity_pct,pressure_hpa\n"
ROW_1 = "2026-10-05T10:00:00Z,1,21.50,48.20,1012.30\n"
ROW_2 = "2026-10-05T10:15:00Z,1,21.60,,1012.20\n"      # humidity missing
ROW_3 = "2026-10-05T10:30:00Z,1,21.70,48.00,1012.10\n"


@pytest.fixture
def connection(tmp_path):
    connection = database.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_export_has_the_format_of_the_station(connection):
    database.insert_rows(connection, parse_rows(HEADER + ROW_2 + ROW_1))
    # Oldest first, two decimals, an empty field for a missing value
    assert transfer.export_csv(connection) == HEADER + ROW_1 + ROW_2


def test_uploaded_measurements_store_only_the_new_rows(connection,
                                                      tmp_path):
    database.insert_rows(connection, parse_rows(HEADER + ROW_1 + ROW_2))
    success, text = transfer.import_file(
        connection, tmp_path / "station.log", "measurements.csv",
        HEADER + ROW_1 + ROW_2 + ROW_3)
    assert success
    assert text == "measurements.csv: 3 rows read, 1 new, 2 already stored"
    assert database.count_rows(connection) == 3


def test_malformed_file_is_not_stored(connection, tmp_path):
    success, text = transfer.import_file(
        connection, tmp_path / "station.log", "measurements.csv",
        HEADER + ROW_1 + "2026-10-05T10:15:00Z,1,21.6\n")
    assert not success
    assert database.count_rows(connection) == 0


def test_file_saved_by_a_spreadsheet_is_refused(connection, tmp_path):
    # ";" between the fields and "," in the numbers, as written by a
    # spreadsheet in French: refused, and not taken for a log
    french = HEADER.replace(",", ";") + "2026-10-05T10:00:00Z;1;21,50;48,20;1012,30\n"
    log = tmp_path / "station.log"
    success, text = transfer.import_file(connection, log, "excel.csv",
                                         french)
    assert not success
    assert "commas between the fields" in text
    assert not log.exists()


def test_other_file_is_refused(connection, tmp_path):
    success, _ = transfer.import_file(connection, tmp_path / "station.log",
                                      "notes.txt", "some notes\n")
    assert not success


ENTRY_1 = "=== 2026-10-05T10:00:00Z ===\n-> BOOT\n-> MEASURE\n"
ENTRY_2 = "=== 2026-10-05T10:15:00Z ===\n-> BOOT\n-> MEASURE\n"


def test_uploaded_log_adds_only_the_new_entries(connection, tmp_path):
    log = tmp_path / "station.log"
    logs.append(log, ENTRY_1)
    success, text = transfer.import_file(connection, log, "log.txt",
                                         ENTRY_1 + ENTRY_2)
    assert success
    assert text == "log.txt: 2 log entries read, 1 new, 1 already stored"
    assert log.read_text() == ENTRY_1 + ENTRY_2


def test_log_entries_are_cut_at_their_first_line():
    assert logs.split_entries("lost line\n" + ENTRY_1 + ENTRY_2) == [
        "lost line\n", ENTRY_1, ENTRY_2]
