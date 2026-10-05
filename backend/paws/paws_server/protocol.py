"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/protocol.py

Description:
The CSV format of the upload protocol v1 (see the Data and Upload chapter
of the Phase 4 design): checks a request and turns its rows into values
ready to be stored. A request is refused as a whole if one of its rows is
wrong, so that it is never stored halfway.

Dependencies: Python standard library.
"""

import csv
import io
from datetime import datetime

# Columns of the CSV format v1, in order
COLUMNS = ["timestamp", "time_valid", "temperature_c", "humidity_pct",
           "pressure_hpa"]

# Format of the timestamps: ISO 8601 in UTC, with the explicit Z suffix
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class FormatError(ValueError):
    """The text does not follow the CSV format v1."""


def _to_number(field):
    # An empty field is a missing value: None, stored as NULL, never as 0
    return float(field) if field else None


def parse_rows(text):
    """Checks a CSV text of the protocol v1 and returns its rows.

    The first line must be the header of the format v1. Each row must have
    the five columns, a timestamp in UTC with the Z suffix, a validity of 0
    or 1, and numbers or empty fields for the values.

    Returns a list of tuples (timestamp, time_valid, temperature_c,
    humidity_pct, pressure_hpa), in the order of the text. Raises
    FormatError, with the line in question, if anything is wrong.
    """
    reader = csv.reader(io.StringIO(text))
    if next(reader, None) != COLUMNS:
        raise FormatError("unknown CSV header")

    rows = []
    for row in reader:
        if not row:
            continue  # a blank line, such as the end of the text
        try:
            if len(row) != len(COLUMNS):
                raise ValueError("wrong number of columns")
            datetime.strptime(row[0], TIMESTAMP_FORMAT)
            if row[1] not in ("0", "1"):
                raise ValueError("time_valid must be 0 or 1")
            rows.append((row[0], int(row[1]), _to_number(row[2]),
                         _to_number(row[3]), _to_number(row[4])))
        except ValueError as error:
            raise FormatError(f"malformed row {row}: {error}") from error
    return rows
