"""Tests of the API of the backend, with the test client of FastAPI."""

import pytest
from fastapi.testclient import TestClient

from paws_server.main import app

HEADER = "timestamp,time_valid,temperature_c,humidity_pct,pressure_hpa\n"
ROW_1 = "2026-10-05T10:00:00Z,1,21.50,48.20,1012.30\n"
ROW_2 = "2026-10-05T10:15:00Z,1,21.60,48.10,1012.20\n"
ROW_3 = "2026-10-05T10:30:00Z,1,21.70,48.00,1012.10\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client whose data lives in a temporary folder."""
    monkeypatch.setenv("PAWS_DATA_DIR", str(tmp_path))
    return TestClient(app)


def upload(client, body):
    return client.post("/api/v1/measurements", content=body)


def test_new_rows_are_stored(client):
    answer = upload(client, HEADER + ROW_1 + ROW_2)
    assert answer.status_code == 200
    assert answer.json() == {"received": 2, "inserted": 2, "duplicates": 0}


def test_rows_already_stored_are_ignored(client):
    upload(client, HEADER + ROW_1 + ROW_2)
    answer = upload(client, HEADER + ROW_1 + ROW_2)
    assert answer.json() == {"received": 2, "inserted": 0, "duplicates": 2}


def test_overlap_inserts_only_the_new_rows(client):
    upload(client, HEADER + ROW_1 + ROW_2)
    answer = upload(client, HEADER + ROW_2 + ROW_3)
    assert answer.json() == {"received": 2, "inserted": 1, "duplicates": 1}


def test_wrong_header_is_refused(client):
    answer = upload(client, "time,temp\n" + ROW_1)
    assert answer.status_code == 400


def test_malformed_row_refuses_the_whole_request(client):
    answer = upload(client, HEADER + ROW_1 + "2026-10-05T10:15:00Z,1,21.6\n")
    assert answer.status_code == 400
    assert client.get("/api/v1/measurements").json() == []


@pytest.mark.parametrize("timestamp", ["2026-10-05 10:00:00",
                                       "2026-10-05T10:00:00",
                                       "2026-13-05T10:00:00Z"])
def test_bad_timestamp_is_refused(client, timestamp):
    answer = upload(client, HEADER + f"{timestamp},1,21.5,48.2,1012.3\n")
    assert answer.status_code == 400


def test_bad_time_valid_is_refused(client):
    answer = upload(client, HEADER + "2026-10-05T10:00:00Z,2,21.5,48.2,1012.3\n")
    assert answer.status_code == 400


def test_missing_values_are_stored_as_null(client):
    upload(client, HEADER + "2026-10-05T10:00:00Z,0,,,\n")
    row = client.get("/api/v1/measurements").json()[0]
    assert row == {"timestamp": "2026-10-05T10:00:00Z", "time_valid": 0,
                   "temperature_c": None, "humidity_pct": None,
                   "pressure_hpa": None}


def test_last_rows_come_newest_first(client):
    upload(client, HEADER + ROW_1 + ROW_3 + ROW_2)
    rows = client.get("/api/v1/measurements", params={"count": 2}).json()
    assert [row["timestamp"] for row in rows] == ["2026-10-05T10:30:00Z",
                                                  "2026-10-05T10:15:00Z"]


def test_log_lines_are_appended(client, tmp_path):
    assert client.post("/api/v1/logs", content="-> BOOT\n").json() == {
        "received": 1}
    client.post("/api/v1/logs", content="-> MEASURE\n-> STORE")
    log = (tmp_path / "station.log").read_text()
    assert log == "-> BOOT\n-> MEASURE\n-> STORE\n"


def test_home_redirects_to_the_dashboard(client):
    answer = client.get("/", follow_redirects=False)
    assert answer.status_code == 307
    assert answer.headers["location"] == "/dashboard/"


def test_dashboard_is_served(client):
    assert "<title>PAWS</title>" in client.get("/dashboard/").text
    # The layout, asked by the page under the same prefix
    assert client.get("/dashboard/_dash-layout").status_code == 200
