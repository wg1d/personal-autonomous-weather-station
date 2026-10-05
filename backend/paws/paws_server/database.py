"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/database.py

Description:
The SQLite database of the measurements: one table, whose primary key is
the timestamp, so that a row received twice is stored once (idempotence of
the upload protocol).

Dependencies: Python standard library (sqlite3).
"""

import sqlite3

from .protocol import COLUMNS


def connect(path):
    """Opens the database, and creates its table if it does not exist.

    One connection per request: SQLite handles the concurrent accesses of
    the server, and a connection is cheap to open.
    """
    connection = sqlite3.connect(path)
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


def last_row(connection):
    """Returns the newest row with a valid time, or None if there is none."""
    rows = connection.execute(
        "SELECT * FROM measurements WHERE time_valid = 1 "
        "ORDER BY timestamp DESC LIMIT 1").fetchall()
    return dict(zip(COLUMNS, rows[0])) if rows else None


def first_timestamp(connection):
    """Returns the oldest timestamp with a valid time, or None."""
    return connection.execute(
        "SELECT MIN(timestamp) FROM measurements WHERE time_valid = 1"
    ).fetchone()[0]


def rows_between(connection, start, end):
    """Returns the rows with a valid time from start to end, oldest first.

    start and end are timestamps in the format of the station; start is
    included, end is not. The timestamps are stored as text, but in this
    format their alphabetical order is the order of time: comparing them
    as text is enough.
    """
    rows = connection.execute(
        "SELECT * FROM measurements WHERE time_valid = 1 "
        "AND timestamp >= ? AND timestamp < ? ORDER BY timestamp",
        (start, end)).fetchall()
    return [dict(zip(COLUMNS, row)) for row in rows]


def daily_summary(connection):
    """Returns the minimum, average and maximum of each day.

    The days are those of the local time of the server: SQLite converts
    each timestamp ('localtime'), then groups the rows of the same date.
    Returns one dictionary per day, oldest first, with the keys "day" and
    "<column>_min", "<column>_avg", "<column>_max" for each quantity.
    """
    quantities = COLUMNS[2:]
    columns = ", ".join(f"MIN({q}), AVG({q}), MAX({q})" for q in quantities)
    rows = connection.execute(
        f"SELECT date(timestamp, 'localtime') AS day, {columns} "
        "FROM measurements WHERE time_valid = 1 "
        "GROUP BY day ORDER BY day").fetchall()
    keys = ["day"] + [f"{q}_{s}" for q in quantities
                      for s in ("min", "avg", "max")]
    return [dict(zip(keys, row)) for row in rows]
