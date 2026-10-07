"""Tests of the dashboard: health, navigation, queries, views and
comparison."""

from datetime import date, datetime, timedelta, timezone

import pytest

from paws_server import database
from paws_server.dashboard import (build_comparison, build_view,
                                   compare_after_move,
                                   compare_dates, format_age, health,
                                   midnights, resolution, shown,
                                   parts_of, shown_limits, start_of,
                                   view_after_move)

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

# The period of the Graphs tab when the page opens: the last 24 hours
DAY = {"length": 86400, "end": None}


@pytest.fixture
def connection(tmp_path):
    connection = database.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def row(timestamp, temperature, time_valid=1):
    return (timestamp, time_valid, temperature, 50.0, 1013.0)


# --- Health ------------------------------------------------------------------

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


# --- Navigation ----------------------------------------------------------------

def test_period_shown_ends_now_by_default():
    start, stop = shown({"length": 7 * 86400, "end": None}, NOW)
    assert (start, stop) == (NOW - timedelta(days=7), NOW)


def test_drag_or_zoom_sets_the_period_shown():
    # In UTC (see utc_local_time): 6 hours, ending 2 hours ago
    limits = ["2026-10-05 04:00:00", "2026-10-05 10:00:00"]
    assert view_after_move(limits, NOW) == {
        "length": 6 * 3600, "end": "2026-10-05T10:00:00Z"}


def test_limits_reported_by_plotly_for_the_three_axes():
    relayout = {f"xaxis{suffix}.range[{bound}]": value
                for suffix in ["", "2", "3"]
                for bound, value in [(0, "2026-10-04 10:00:00"),
                                     (1, "2026-10-05 10:00:00")]}
    assert shown_limits(relayout) == ["2026-10-04 10:00:00",
                                      "2026-10-05 10:00:00"]
    # A click in the legend changes no time axis
    assert shown_limits({"legend.x": 0.1}) is None


def test_back_to_the_present_follows_the_new_data():
    limits = ["2026-10-04 12:00:00", "2026-10-05 12:00:00"]
    assert view_after_move(limits, NOW)["end"] is None


def test_resolution_follows_the_length_shown():
    assert resolution(timedelta(hours=24)) == "rows"
    assert resolution(timedelta(days=30)) == "hours"
    assert resolution(timedelta(days=365)) == "days"


def test_midnights_between_two_times():
    first = datetime(2026, 10, 3, 18, 0)
    last = datetime(2026, 10, 5, 12, 0)
    assert midnights(first, last) == [datetime(2026, 10, 4),
                                      datetime(2026, 10, 5)]


# --- Queries -------------------------------------------------------------------

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


def test_hourly_summary(connection):
    database.insert_rows(connection, [
        row("2026-10-05T10:00:00Z", 10.0),
        row("2026-10-05T10:45:00Z", 11.0),
        row("2026-10-05T11:00:00Z", 20.0),
    ])
    hours = database.hourly_summary(connection, "2026-10-05T00:00:00Z",
                                    "2026-10-06T00:00:00Z")
    assert [(h["local_time"], h["temperature_c"]) for h in hours] == [
        ("2026-10-05 10:30:00", 10.5), ("2026-10-05 11:30:00", 20.0)]


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


# --- Graphs tab ----------------------------------------------------------------

def test_view_of_a_day_shows_every_row(connection):
    database.insert_rows(connection, [row("2026-10-05T11:45:00Z", 12.0)])
    figure = build_view(connection, DAY, NOW)["figure"]
    assert figure["data"][0]["y"] == [12.0]
    assert len(figure["data"]) == 3                 # one line per quantity


def test_view_holds_as_much_again_on_each_side(connection):
    database.insert_rows(connection, [
        row("2026-10-03T12:00:00Z", 10.0),          # 2 days before: kept
        row("2026-10-03T11:45:00Z", 9.0),           # too old: not loaded
    ])
    figure = build_view(connection, DAY, NOW)["figure"]
    assert figure["data"][0]["y"] == [10.0]


def test_view_of_a_year_shows_min_average_max(connection):
    database.insert_rows(connection, [row("2026-10-05T11:45:00Z", 12.0)])
    view = {"length": 365 * 86400, "end": None}
    names = [trace.get("name")
             for trace in build_view(connection, view, NOW)["figure"]["data"]]
    assert names[:3] == [None, "Temperature: daily min – max",
                         "Temperature: daily average"]


def test_figure_holds_the_limits_of_the_data(connection):
    database.insert_rows(connection, [row("2026-10-01T00:00:00Z", 12.0)])
    layout = build_view(connection, DAY, NOW)["figure"]["layout"]
    # On the three time axes, which move together
    for axis in ["xaxis", "xaxis2", "xaxis3"]:
        assert layout[axis]["minallowed"] == "2026-10-01 00:00:00"
        assert layout[axis]["maxallowed"] == "2026-10-05 12:00:00"


# --- Compare tab ---------------------------------------------------------------

def test_any_day_chooses_its_whole_period():
    # Wednesday 14 October 2026 and Monday 7 December 2025
    for unit, starts in [("day", ("2026-10-14", "2025-12-07")),
                         ("week", ("2026-10-12", "2025-12-01")),
                         ("month", ("2026-10-01", "2025-12-01")),
                         ("year", ("2026-01-01", "2025-01-01"))]:
        compared = compare_dates(unit, "2026-10-14", "2025-12-07")
        assert (compared["reference"][:10],
                compared["comparison"][:10]) == starts


def test_period_from_the_two_lists():
    assert start_of("day", 2026, 10, 14) == date(2026, 10, 14)
    # February has no 31st: its last day instead
    assert start_of("day", 2026, 2, 31) == date(2026, 2, 28)
    assert start_of("month", 2025, 10) == date(2025, 10, 1)
    assert start_of("week", 2026, 41) == date(2026, 10, 5)
    # 2026 has 53 weeks, 2025 only 52: its week 53 is its last week
    assert start_of("week", 2025, 53) == date(2025, 12, 22)
    assert start_of("year", 2025) == date(2025, 1, 1)
    assert parts_of("week", date(2026, 10, 5)) == (2026, 41, None)
    assert parts_of("day", date(2026, 10, 14)) == (2026, 10, 14)


def test_month_is_compared_with_another_month(connection):
    database.insert_rows(connection, [
        row("2026-10-01T01:00:00Z", 15.0),          # October
        row("2025-12-01T01:00:00Z", 2.0),           # December
    ])
    compared = compare_dates("month", "2026-10-01", "2025-12-01")
    assert compared["length"] == 31 * 86400
    data = build_comparison(connection, compared, NOW)["data"]
    reference, comparison = data[:2]
    assert reference["name"] == "October 2026"
    assert comparison["name"] == "December 2025"
    # One hour after the start of each month: drawn at the same place
    # (the middle of the hour, see hourly_summary())
    assert reference["x"] == comparison["x"] == ["2026-10-01 01:30:00"]
    assert comparison["y"] == [2.0]


def test_drag_moves_both_periods_together():
    compared = compare_dates("month", "2026-10-01", "2025-12-01")
    # The reference dragged to start 6 days later
    limits = ["2026-10-07 00:00:00", "2026-11-07 00:00:00"]
    moved = compare_after_move(limits, compared)
    assert (moved["reference"], moved["comparison"]) == (
        "2026-10-07T00:00:00Z", "2025-12-07T00:00:00Z")
    # The legend now gives the exact dates shown
    assert not moved["chosen"]
