"""Tests of the dashboard: health, navigation and daily summary."""

import time
from datetime import datetime, timedelta, timezone

import pytest

from paws_server import database
from dash import no_update

from paws_server.dashboard import (build_view, end_after_drag, format_age,
                                   health, midnights, shift, to_timestamp,
                                   window)

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def utc_local_time(monkeypatch):
    """Runs every test with the local time set to UTC.

    The dashboard shows the local time of the server, which depends on the
    computer running the tests: in UTC, the results are the same anywhere.
    """
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.fixture
def connection(tmp_path):
    connection = database.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def row(timestamp, temperature, time_valid=1):
    return (timestamp, time_valid, temperature, 50.0, 1013.0)


def test_health_without_data_warns():
    stale, status, alert = health(None, NOW)
    assert stale
    assert alert == "No measurement received yet: check the station."


def test_health_of_a_recent_measurement():
    last = {"timestamp": "2026-10-05T11:30:00Z"}
    assert health(last, NOW) == (
        False, "Last measurement · 05 Oct, 11:30 (30 min ago)", "")


def test_health_warns_after_two_hours():
    last = {"timestamp": "2026-10-05T08:55:00Z"}
    stale, status, alert = health(last, NOW)
    assert stale
    assert alert == "No new measurement for 3 h 05 min: check the station."


def test_long_silence_is_counted_in_days():
    assert format_age(timedelta(days=4, hours=3)) == "4 days"


def test_window_ends_now_by_default():
    start, stop = window("7d", None, NOW)
    assert (to_timestamp(start), stop) == ("2026-09-28T12:00:00Z", NOW)


def test_back_and_forth_move_by_one_period():
    end = shift("24h", None, NOW, -1)
    assert end == "2026-10-04T12:00:00Z"
    assert shift("24h", end, NOW, -1) == "2026-10-03T12:00:00Z"
    # Back to the present: the page follows the new data again
    assert shift("24h", end, NOW, +1) is None


def test_drag_moves_the_period():
    # In UTC (see utc_local_time), dragged two hours back in time
    relayout = {"xaxis3.range[0]": "2026-10-04 10:00:00",
                "xaxis3.range[1]": "2026-10-05 10:00:00"}
    assert end_after_drag(relayout, "24h", NOW) == "2026-10-05T10:00:00Z"


def test_drag_to_the_present_follows_the_new_data():
    relayout = {"xaxis.range[0]": "2026-10-04 13:00:00",
                "xaxis.range[1]": "2026-10-05 13:00:00"}
    assert end_after_drag(relayout, "24h", NOW) is None


def test_zoom_and_reset_do_not_move_the_period():
    zoom = {"xaxis.range[0]": "2026-10-05 08:00:00",
            "xaxis.range[1]": "2026-10-05 10:00:00"}
    assert end_after_drag(zoom, "24h", NOW) is no_update
    assert end_after_drag({"xaxis.autorange": True}, "24h", NOW) is no_update


def test_midnights_between_two_times():
    first = datetime(2026, 10, 3, 18, 0)
    last = datetime(2026, 10, 5, 12, 0)
    assert midnights(first, last) == [datetime(2026, 10, 4),
                                      datetime(2026, 10, 5)]


def test_rows_between_skips_rows_outside_and_invalid(connection):
    database.insert_rows(connection, [
        row("2026-10-04T11:45:00Z", 10.0),         # before the period
        row("2026-10-04T12:00:00Z", 11.0),
        row("2026-10-05T11:45:00Z", 12.0),
        row("2026-10-05T12:00:00Z", 13.0),         # end: not included
        row("2000-01-01T00:15:00Z", 99.0, 0),      # clock not valid
    ])
    rows = database.rows_between(connection, "2026-10-04T12:00:00Z",
                                 "2026-10-05T12:00:00Z")
    assert [r["temperature_c"] for r in rows] == [11.0, 12.0]


def test_daily_summary(connection):
    database.insert_rows(connection, [
        row("2026-10-04T06:00:00Z", 10.0),
        row("2026-10-04T14:00:00Z", 20.0),
        row("2026-10-04T15:00:00Z", None),         # missing value: ignored
        row("2026-10-05T06:00:00Z", 12.0),
    ])
    days = database.daily_summary(connection, "2026-01-01T00:00:00Z",
                                  "2026-10-06T00:00:00Z")
    assert [d["day"] for d in days] == ["2026-10-04", "2026-10-05"]
    first = days[0]
    assert (first["temperature_c_min"], first["temperature_c_avg"],
            first["temperature_c_max"]) == (10.0, 15.0, 20.0)


def test_view_of_a_day_shows_every_row(connection):
    database.insert_rows(connection, [row("2026-10-05T11:45:00Z", 12.0)])
    view = build_view(connection, "24h", None, NOW)
    temperature = view["figure"]["data"][0]
    assert temperature["y"] == [12.0]
    assert temperature["x"] == ["2026-10-05 11:45:00"]
    assert len(view["figure"]["data"]) == 3         # one line per quantity


def test_view_holds_a_margin_on_each_side(connection):
    database.insert_rows(connection, [
        row("2026-09-27T12:00:00Z", 10.0),          # 8 days before: kept
        row("2026-09-27T11:45:00Z", 9.0),           # too old: not loaded
    ])
    view = build_view(connection, "24h", None, NOW)
    assert view["figure"]["data"][0]["y"] == [10.0]


def test_view_of_a_year_shows_min_average_max(connection):
    database.insert_rows(connection, [row("2026-10-05T11:45:00Z", 12.0)])
    view = build_view(connection, "1y", None, NOW)
    names = [trace.get("name") for trace in view["figure"]["data"][:3]]
    assert names == [None, "Temperature: daily min – max",
                     "Temperature: daily average"]


def test_back_is_disabled_before_the_first_row(connection):
    database.insert_rows(connection, [row("2026-10-01T00:00:00Z", 12.0)])
    assert not build_view(connection, "24h", None, NOW)["at_start"]
    assert build_view(connection, "7d", None, NOW)["at_start"]
