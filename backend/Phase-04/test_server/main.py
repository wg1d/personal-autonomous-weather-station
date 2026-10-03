"""
Project: Personal Autonomous Weather Station
File: backend/Phase-04/test_server/main.py

Description:
Test server for the upload protocol v1 of the station (see the Upload
Protocol in the Data and Upload chapter of the Phase 4 design). It
receives CSV rows on POST /api/v1/measurements, stores them in a SQLite
database, ignores the rows whose timestamp it already has, and answers
with a short JSON summary. It is a bench tool, not the Phase 5 backend.

Usage: python main.py [--port PORT] (default port: 8080)

Dependencies: FastAPI, uvicorn (pixi backend environment).
"""

import argparse
import csv
import io
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
import uvicorn

# Columns of the CSV format v1, in order
COLUMNS = ["timestamp", "time_valid", "temperature_c", "humidity_pct",
           "pressure_hpa"]

DATABASE = "measurements.db"

app = FastAPI()


def open_database():
    connection = sqlite3.connect(DATABASE)
    # The timestamp identifies a row: inserting it twice is impossible,
    # which makes repeated uploads harmless (idempotence)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS measurements ("
        "timestamp TEXT PRIMARY KEY, time_valid INTEGER, "
        "temperature_c REAL, humidity_pct REAL, pressure_hpa REAL)")
    return connection


def to_number(field):
    # An empty field is a missing value: stored as NULL, not as 0
    return float(field) if field else None


@app.post("/api/v1/measurements")
async def receive_measurements(request: Request):
    text = (await request.body()).decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    if next(reader, None) != COLUMNS:
        raise HTTPException(status_code=400, detail="unknown CSV header")

    received = 0
    inserted = 0
    with open_database() as connection:
        for row in reader:
            if len(row) != len(COLUMNS):
                raise HTTPException(status_code=400,
                                    detail=f"malformed row: {row}")
            received += 1
            cursor = connection.execute(
                "INSERT OR IGNORE INTO measurements VALUES (?, ?, ?, ?, ?)",
                (row[0], int(row[1]), to_number(row[2]), to_number(row[3]),
                 to_number(row[4])))
            inserted += cursor.rowcount

    summary = {"received": received, "inserted": inserted,
               "duplicates": received - inserted}
    print(f"POST /api/v1/measurements: {summary}")
    return summary


def last_rows(count):
    with open_database() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM measurements").fetchone()[0]
        rows = connection.execute(
            "SELECT * FROM measurements ORDER BY timestamp DESC LIMIT ?",
            (count,)).fetchall()
    return total, rows


@app.get("/api/v1/measurements")
def list_measurements():
    # The last rows received, as JSON, for programs
    _, rows = last_rows(20)
    return [dict(zip(COLUMNS, row)) for row in rows]


@app.get("/", response_class=HTMLResponse)
def show_measurements():
    # The same rows as a table, to check the uploads from a browser
    total, rows = last_rows(50)
    header = "".join(f"<th>{name}</th>" for name in COLUMNS)
    lines = "".join(
        "<tr>" + "".join(f"<td>{'' if value is None else value}</td>"
                         for value in row) + "</tr>"
        for row in rows)
    return (f"<html><head><title>PAWS test server</title></head><body>"
            f"<h1>PAWS test server</h1>"
            f"<p>{total} rows received. Last {len(rows)}, newest first:</p>"
            f"<table border='1' cellpadding='4'><tr>{header}</tr>{lines}"
            f"</table></body></html>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test server for the upload protocol v1 of the station")
    parser.add_argument("--port", type=int, default=8080,
                        help="port to listen on (default: 8080)")
    args = parser.parse_args()
    # 0.0.0.0: listen on every network interface, so that the ESP32 can
    # reach the server over the home Wi-Fi
    uvicorn.run(app, host="0.0.0.0", port=args.port)
