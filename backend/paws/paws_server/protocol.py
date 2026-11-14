"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/protocol.py

Description:
The CSV formats of the upload protocol (see the Data and Upload chapter
of the Phase 4 design): checks a request and turns its rows into values
ready to be stored. A request is refused as a whole if one of its rows is
wrong, so that it is never stored halfway.

Two formats are accepted, told apart by the header of the request: the
format v1, with the three measurements of the air, and the format v2,
which adds the voltage and the current of the battery, measured by the
INA219. A station that still writes the format v1 keeps working.

Dependencies: Python standard library.
"""

import csv
import io
from datetime import datetime

# Columns of the CSV format v1, in order
COLUMNS_V1 = ["timestamp", "time_valid", "temperature_c", "humidity_pct",
              "pressure_hpa"]
# Columns of the CSV format v2: those of v1, then the voltage of the
# battery, in volts, and its current, in milliamperes, positive when the
# battery charges, negative when the station draws from it. These are the
# columns of the database, and of the export
COLUMNS = COLUMNS_V1 + ["battery_v", "battery_ma"]
FORMATS = [COLUMNS_V1, COLUMNS]

# Format of the timestamps: ISO 8601 in UTC, with the explicit Z suffix
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class FormatError(ValueError):
    """The text does not follow the CSV format v1 nor v2."""


def _to_number(field):
    # An empty field is a missing value: None, stored as NULL, never as 0
    return float(field) if field else None


def parse_rows(text):
    """Checks a CSV text of the protocol, v1 or v2, and returns its rows.

    The first line must be the header of the format v1 or v2. Each row
    must have the columns of its header, a timestamp in UTC with the Z
    suffix, a validity of 0 or 1, and numbers or empty fields for the
    values.

    Returns a list of tuples in the order of COLUMNS (the format v2), in
    the order of the text: the rows of the format v1 have no value for
    the battery (None). Raises FormatError, with the line in question, if
    anything is wrong.
    """
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header not in FORMATS:
        raise FormatError("unknown CSV header")
    # The columns that the format leaves out, missing in each row
    missing = (None,) * (len(COLUMNS) - len(header))

    rows = []
    for row in reader:
        if not row:
            continue  # a blank line, such as the end of the text
        try:
            if len(row) != len(header):
                raise ValueError("wrong number of columns")
            datetime.strptime(row[0], TIMESTAMP_FORMAT)
            if row[1] not in ("0", "1"):
                raise ValueError("time_valid must be 0 or 1")
            rows.append((row[0], int(row[1]),
                         *(_to_number(field) for field in row[2:]),
                         *missing))
        except ValueError as error:
            raise FormatError(f"malformed row {row}: {error}") from error
    return rows
