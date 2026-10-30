"""Tests of the quantities computed from the measurements."""

import pytest

from paws_server import database
from paws_server.weather import (absolute_humidity, dew_point, feels_like,
                                 sea_level_factor, vapour_pressure_deficit)


def test_dew_point():
    # Values of reference tables: 20 °C and 50 % give 9.3 °C; saturated
    # air has its dew point at its temperature
    assert dew_point(20.0, 50.0) == pytest.approx(9.3, abs=0.1)
    assert dew_point(5.0, 100.0) == pytest.approx(5.0, abs=0.01)
    assert dew_point(-5.0, 80.0) == pytest.approx(-7.9, abs=0.1)
    assert dew_point(20.0, None) is None
    assert dew_point(20.0, 0.0) is None


def test_feels_like_only_in_the_heat():
    # Table of the US weather service: 90 °F and 70 % feel like 106 °F,
    # that is 32.2 °C feel like 41.1 °C
    assert feels_like(32.2, 70.0) == pytest.approx(41.1, abs=0.3)
    assert feels_like(20.0, 90.0) is None
    assert feels_like(30.0, 30.0) is None


def test_absolute_humidity():
    # Reference values: 8.6 g/m³ at 20 °C and 50 %, 17.3 g/m³ saturated
    assert absolute_humidity(20.0, 50.0) == pytest.approx(8.6, abs=0.1)
    assert absolute_humidity(20.0, 100.0) == pytest.approx(17.3, abs=0.1)
    assert absolute_humidity(20.0, None) is None


def test_vapour_pressure_deficit():
    # At 20 °C, saturated air holds 2.34 kPa of vapour: half of it is
    # missing at 50 %; saturated air has no deficit
    assert vapour_pressure_deficit(20.0, 50.0) == pytest.approx(1.17,
                                                                abs=0.01)
    assert vapour_pressure_deficit(10.0, 100.0) == 0.0
    assert vapour_pressure_deficit(None, 50.0) is None


def test_sea_level_factor():
    assert sea_level_factor(0) == 1.0
    # At 140 metres, about 17 hPa more for 1000 hPa
    assert 1000 * sea_level_factor(140) == pytest.approx(1016.8, abs=0.1)


def test_queries_return_the_computed_quantities(tmp_path):
    connection = database.connect(tmp_path / "test.db", altitude=140)
    database.insert_rows(connection, [
        ("2026-10-05T11:45:00Z", 1, 20.0, 50.0, 1000.0)])
    last = database.last_row(connection)
    assert last["dew_point_c"] == pytest.approx(9.3, abs=0.1)
    assert last["feels_like_c"] is None
    assert last["sea_level_hpa"] == pytest.approx(1016.8, abs=0.1)
    days = database.daily_summary(connection, "2026-10-05T00:00:00Z",
                                  "2026-10-06T00:00:00Z")
    assert days[0]["dew_point_c_max"] == pytest.approx(9.3, abs=0.1)
    connection.close()
