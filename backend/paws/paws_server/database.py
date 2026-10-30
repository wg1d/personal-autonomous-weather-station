"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/database.py

Description:
The SQLite database of the measurements: one table, whose primary key is
the timestamp, so that a row received twice is stored once (idempotence of
the upload protocol).

The queries of the dashboard also return the quantities computed from the
measurements (see weather.py): SQLite calls the Python functions given to
it, for each row, so that the averages, minimums and maximums of these
quantities are computed like those of the measurements.

Dependencies: Python standard library (sqlite3).
"""

import sqlite3

from . import weather
from .protocol import COLUMNS

# The quantities that the queries of the dashboard return: the three
# measurements, then the computed ones, each with its SQL expression
QUANTITIES = {
    "temperature_c": "temperature_c",
    "humidity_pct": "humidity_pct",
    "pressure_hpa": "pressure_hpa",
    "dew_point_c": "dew_point(temperature_c, humidity_pct)",
    "feels_like_c": "feels_like(temperature_c, humidity_pct)",
    "sea_level_hpa": "sea_level(pressure_hpa)",
}
# All the quantities, separated by commas, for a SELECT
QUANTITY_COLUMNS = ", ".join(QUANTITIES.values())


def connect(path, altitude=0):
    """Opens the database, and creates its table if it does not exist.

    One connection per request: SQLite handles the concurrent accesses of
    the server, and a connection is cheap to open. altitude is the one of
    the station, in metres, for the pressure at sea level.
    """
    connection = sqlite3.connect(path)
    # The functions of weather.py, which the SQL of QUANTITIES calls,
    # with their number of arguments
    factor = weather.sea_level_factor(altitude)
    connection.create_function("dew_point", 2, weather.dew_point)
    connection.create_function("feels_like", 2, weather.feels_like)
    connection.create_function(
        "sea_level", 1,
        lambda pressure: None if pressure is None else pressure * factor)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS measurements ("
        "timestamp TEXT PRIMARY KEY, "
        "time_valid INTEGER NOT NULL, "
        "temperature_c REAL, humidity_pct REAL, pressure_hpa REAL)")
    return connection


def insert_rows(connection, rows):
    """Stores rows, ignores those whose timestamp is already stored.

    All the rows are written in one transaction: either all of them, or
    none if the server stops in the middle. Returns the number of rows
    actually inserted.
    """
    with connection:
        before = connection.total_changes
        connection.executemany(
            "INSERT OR IGNORE INTO measurements VALUES (?, ?, ?, ?, ?)", rows)
        return connection.total_changes - before


def count_rows(connection):
    """Returns the number of rows stored."""
    return connection.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]


def last_rows(connection, count):
    """Returns the last rows, newest first, as dictionaries."""
    rows = connection.execute(
        "SELECT * FROM measurements ORDER BY timestamp DESC LIMIT ?",
        (count,)).fetchall()
    return [dict(zip(COLUMNS, row)) for row in rows]


def all_rows(connection):
    """Returns every row, oldest first, as tuples in the order of COLUMNS."""
    return connection.execute(
        "SELECT * FROM measurements ORDER BY timestamp").fetchall()


def summary(connection):
    """Returns (number of rows, oldest timestamp, newest timestamp) of the
    rows with a valid time; the timestamps are None without rows."""
    return connection.execute(
        "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM measurements "
        "WHERE time_valid = 1").fetchone()


def last_row(connection):
    """Returns the newest row with a valid time, with all the QUANTITIES,
    or None if there is none."""
    rows = connection.execute(
        f"SELECT timestamp, {QUANTITY_COLUMNS} FROM measurements "
        "WHERE time_valid = 1 ORDER BY timestamp DESC LIMIT 1").fetchall()
    return dict(zip(["timestamp", *QUANTITIES], rows[0])) if rows else None


def first_local_time(connection):
    """Returns the time of the oldest valid row, in local time, or None."""
    return connection.execute(
        "SELECT datetime(MIN(timestamp), 'localtime') FROM measurements "
        "WHERE time_valid = 1").fetchone()[0]


def rows_between(connection, start, end):
    """Returns the rows with a valid time from start to end, oldest first.

    start and end are timestamps in the format of the station; start is
    included, end is not. The timestamps are stored as text, but in this
    format their alphabetical order is the order of time: comparing them
    as text is enough.

    Each row holds its "timestamp", all the QUANTITIES, and "local_time":
    its time in the local time of the server, as text ("2026-10-05
    14:45:00"), converted by SQLite ('localtime') much faster than Python
    would.
    """
    rows = connection.execute(
        f"SELECT timestamp, {QUANTITY_COLUMNS}, "
        "datetime(timestamp, 'localtime') FROM measurements "
        "WHERE time_valid = 1 AND timestamp >= ? AND timestamp < ? "
        "ORDER BY timestamp", (start, end)).fetchall()
    return [dict(zip(["timestamp", *QUANTITIES, "local_time"], row))
            for row in rows]


def hourly_summary(connection, start, end):
    """Returns the average of each hour, from start to end, oldest first.

    Used for the long periods of the dashboard, where a point every 15
    minutes would be more than the screen can show: four times fewer
    points to send to the browser. Each average is placed at the middle
    of its hour ('+30 minutes'), in the local time of the server. Returns
    one dictionary per hour, with the keys "local_time" and one per
    quantity of QUANTITIES, as rows_between().
    """
    quantities = list(QUANTITIES)
    columns = ", ".join(f"ROUND(AVG({sql}), 2)"
                        for sql in QUANTITIES.values())
    rows = connection.execute(
        "SELECT datetime(substr(timestamp, 1, 13) || ':00:00', "
        f"'+30 minutes', 'localtime'), {columns} "
        "FROM measurements WHERE time_valid = 1 "
        "AND timestamp >= ? AND timestamp < ? "
        "GROUP BY substr(timestamp, 1, 13) ORDER BY timestamp",
        (start, end)).fetchall()
    return [dict(zip(["local_time"] + quantities, row)) for row in rows]


def daily_summary(connection, start, end):
    """Returns the minimum, average and maximum of each day, start to end.

    The days are those of UTC: the first ten characters of the timestamp,
    its date. Converting each timestamp to local time first would take
    seconds on the server, for several years of rows; in France, a day in
    UTC starts at 1:00 or 2:00, which changes little to its minimum,
    average and maximum.

    Returns one dictionary per day, oldest first, with the keys "day" and
    "<column>_min", "<column>_avg", "<column>_max" for each quantity of
    QUANTITIES.
    """
    quantities = list(QUANTITIES)
    columns = ", ".join(f"MIN({sql}), AVG({sql}), MAX({sql})"
                        for sql in QUANTITIES.values())
    rows = connection.execute(
        f"SELECT substr(timestamp, 1, 10) AS day, {columns} "
        "FROM measurements WHERE time_valid = 1 "
        "AND timestamp >= ? AND timestamp < ? "
        "GROUP BY day ORDER BY day", (start, end)).fetchall()
    keys = ["day"] + [f"{q}_{s}" for q in quantities
                      for s in ("min", "avg", "max")]
    return [dict(zip(keys, row)) for row in rows]
