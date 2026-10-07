"""Settings shared by the tests: pytest reads this file before them."""

import time

import pytest


@pytest.fixture(autouse=True)
def utc_local_time(monkeypatch):
    """Runs every test with the local time set to UTC.

    The dashboard and the backups use the local time of the server, which
    depends on the computer running the tests: in UTC, the results are the
    same anywhere, in the CI too.
    """
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()
