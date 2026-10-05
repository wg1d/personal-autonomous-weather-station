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
