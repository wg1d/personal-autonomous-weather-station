"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/transfer.py

Description:
The files exchanged with the visitor of the dashboard (Data tab):

- the export of all the measurements, as a CSV file in the format of the
  station (BF5);
- the files downloaded from the maintenance page of the station and
  uploaded by hand (BF7): the measurements, stored like an upload of the
  station, and the log, merged into the log of the server.

Dependencies: Python standard library.
"""

import csv
import io

from . import database, logs
from .protocol import COLUMNS, FormatError, parse_rows


def export_csv(connection):
    """All the measurements, oldest first, as the text of a CSV file in the
    format of the station: a value with two decimals, or an empty field
    when it is missing."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(COLUMNS)
    for row in database.all_rows(connection):
        writer.writerow([row[0], row[1]] + ["" if value is None
                                            else f"{value:.2f}"
                                            for value in row[2:]])
    return output.getvalue()


def import_file(connection, log_path, name, content):
    """Stores a file uploaded by hand; returns (success, summary).

    content is the text of the file. A file starting with "timestamp" holds
    measurements: they are checked like an upload of the station, and only
    the new ones are stored. A file holding entries of the log of the
    station (see logs.py) is a log, whose new entries are added to the log
    of the server. Any other file is refused.
    """
    if content.startswith("timestamp"):
        try:
            rows = parse_rows(content)
        except FormatError as error:
            # A file saved again by a spreadsheet often uses ";" between
            # the fields, and "," in the numbers
            return False, (f"{name} : non enregistré, {error} ; il doit "
                           "garder le format de la station, avec des "
                           "virgules entre les champs")
        inserted = database.insert_rows(connection, rows)
        return True, (f"{name} : {len(rows)} lignes lues, {inserted} "
                      f"nouvelles, {len(rows) - inserted} déjà enregistrées")
    if any(logs.ENTRY_START.match(line.strip())
           for line in content.splitlines()):
        read, added = logs.merge(log_path, content)
        return True, (f"{name} : {read} entrées du journal lues, {added} "
                      f"nouvelles, {read - added} déjà enregistrées")
    return False, (f"{name} : non enregistré, ni des mesures ni le journal "
                   "de la station")
