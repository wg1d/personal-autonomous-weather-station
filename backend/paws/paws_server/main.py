"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/main.py

Description:
The backend server: receives the measurements and the log of the station
(upload protocol v1), stores the measurements in SQLite and appends the log
to a text file. It also serves the dashboard, under /dashboard/.

The data lives in the folder given by the PAWS_DATA_DIR environment
variable (by default "data", next to the code), so that a deployment
replaces the code without touching the data.

Run (development computer):
    uv run uvicorn paws_server.main:app --port 8080

Dependencies: fastapi, uvicorn, a2wsgi, dash.
"""

import os
from pathlib import Path

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from . import backup, database, logs
from .dashboard import create_dashboard
from .protocol import FormatError, parse_rows

app = FastAPI(title="PAWS backend")


def data_dir():
    """Returns the data folder, and creates it if needed."""
    folder = Path(os.environ.get("PAWS_DATA_DIR", "data"))
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def open_database():
    """Opens the database of the measurements, in the data folder."""
    return database.connect(data_dir() / "measurements.db")


def log_path():
    """Returns the path of the log of the station, in the data folder."""
    return data_dir() / "station.log"


def backup_status():
    """Returns the result of the last backup (see backup.py), or None."""
    return backup.last_status(data_dir())


@app.post("/api/v1/measurements")
async def receive_measurements(request: Request):
    """Stores the rows of a CSV upload; ignores those already stored.

    The whole request is checked before anything is stored: a malformed
    request is refused with 400, and the station sends it again later.
    """
    text = (await request.body()).decode("utf-8", errors="replace")
    try:
        rows = parse_rows(text)
    except FormatError as error:
        raise HTTPException(status_code=400, detail=str(error))

    connection = open_database()
    try:
        inserted = database.insert_rows(connection, rows)
    finally:
        connection.close()
    return {"received": len(rows), "inserted": inserted,
            "duplicates": len(rows) - inserted}


@app.post("/api/v1/logs")
async def receive_log(request: Request):
    """Appends the log lines sent by the station to station.log."""
    text = (await request.body()).decode("utf-8", errors="replace")
    return {"received": logs.append(log_path(), text)}


@app.get("/api/v1/measurements")
def get_measurements(count: int = 20):
    """Returns the last rows stored, newest first."""
    connection = open_database()
    try:
        return database.last_rows(connection, count)
    finally:
        connection.close()


@app.get("/")
def home():
    """Sends the browser to the dashboard."""
    return RedirectResponse("/dashboard/")


# Dash runs on Flask, a WSGI application (the older standard of the Python
# web servers), and FastAPI is an ASGI application: WSGIMiddleware lets
# FastAPI serve Dash under /dashboard, on the same port
app.mount("/dashboard", WSGIMiddleware(
    create_dashboard(open_database, log_path, backup_status).server))
