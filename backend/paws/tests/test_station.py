"""Tests of the Station tab: the battery and the problems of the log."""

from datetime import datetime, timezone

from paws_server import logs
from paws_server.dashboard import (BATTERY_LOW_V, air_note, battery_charge,
                                   battery_tile, log_problems, log_tile,
                                   station_banner,
                                   station_key)

NOW = datetime(2026, 11, 14, 22, 0, tzinfo=timezone.utc)

LOG = """=== 2026-11-12T09:00:00Z ===
-> BOOT
   restart: brownout, the voltage fell
-> MEASURE
   BME280 not responding
=== 1970-01-01T00:00:00Z ===
   DS3231 not responding
=== 2026-11-14T21:00:00Z ===
-> UPLOAD
   sent 132 bytes of measurements, server answered 200 {}
   sent 669 bytes of log, server answered 500 error
"""


def test_charge_of_the_battery_from_its_voltage():
    assert battery_charge(4.25) == 100
    assert battery_charge(4.20) == 100
    assert battery_charge(3.84) == 50
    assert battery_charge(3.20) == 0
    # Between two points of the table, rounded to 5
    assert battery_charge(4.05) == 80


def test_battery_tile_gives_the_voltage_and_its_time():
    battery = {"timestamp": "2026-11-14T21:45:00Z", "battery_v": 4.12}
    headline, lines = battery_tile(battery, NOW)
    assert headline == "4,12 V · environ 90 %"
    assert lines[0].startswith("Mesure de ")
    headline, lines = battery_tile(None, NOW)
    assert headline == "Pas encore de mesure" and "INA219" in lines[0]


def test_air_note_when_the_last_rows_have_no_air():
    air = {"timestamp": "2026-11-14T21:00:00Z"}
    received = {"timestamp": "2026-11-14T21:45:00Z"}
    assert air_note(received, air).startswith(
        "Le capteur d'air ne répond plus : valeurs de ")
    assert air_note(air, air) == ""
    assert air_note(None, None) == ""


def test_problems_of_the_log():
    found = logs.problems(LOG)
    assert [line for _, _, line in found] == [
        "restart: brownout, the voltage fell", "BME280 not responding",
        "DS3231 not responding",
        "sent 669 bytes of log, server answered 500 error"]
    # The entry without a set clock takes the time of the one before it
    assert found[2][0] == found[1][0] and not found[2][1]


def test_problems_in_french_newest_first():
    shown = log_problems(LOG, datetime(2026, 11, 7, tzinfo=timezone.utc))
    assert shown[-1][1] == "Redémarrage : chute de tension"
    assert shown[1] == ("après 12 nov. 09:00", "DS3231 ne répond pas")
    ok, headline, lines = log_tile(shown)
    assert not ok and headline == "4 problèmes sur 7 jours"
    # Every problem is listed: the box scrolls
    assert len(lines) == 4
    assert log_tile([]) == (True, "Aucun problème sur 7 jours", [])


def test_log_read_from_the_start_of_an_entry(tmp_path):
    path = tmp_path / "station.log"
    path.write_text(LOG)
    tail = logs.read_tail(path, 200)
    assert tail.startswith("=== ") and tail.endswith("500 error\n")
    assert logs.read_tail(path, 10_000) == LOG
    assert logs.read_tail(path, 10) == ""
    assert logs.read_tail(tmp_path / "missing.log", 100) == ""


def test_banner_for_the_air_a_low_battery_or_recent_problems():
    full = {"battery_v": 4.1}
    low = {"battery_v": BATTERY_LOW_V - 0.1}
    problem = [("21:00", "Wi-Fi injoignable")]
    assert station_banner(full, []) == ""
    assert station_banner(low, []).startswith("Batterie faible")
    assert "1 problème dans le journal" in station_banner(None, problem)
    assert station_banner(None, [], "Le capteur d'air ne répond plus.") == (
        "Le capteur d'air ne répond plus.")
    # A new problem changes what the warning is about: it shows again
    assert station_key(full, problem) != station_key(
        full, [("21:15", "BME280 ne répond pas")] + problem)

