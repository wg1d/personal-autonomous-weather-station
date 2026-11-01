"""Tests of the sun and the moon."""

from datetime import date, datetime, timezone

from paws_server import sky

# Beauzelle, near Toulouse
LOCATION = (43.667, 1.376)


def local_minutes(moment):
    """The time of a datetime in UTC, in minutes, in winter time (UTC+1)."""
    return (moment.hour + 1) * 60 + moment.minute


def test_sunrise_and_sunset_near_toulouse():
    # Published times for Toulouse on 21 December: 08:25 and 17:22
    sunrise, sunset = sky.sun_times(date(2026, 12, 21), *LOCATION)
    assert abs(local_minutes(sunrise) - (8 * 60 + 25)) <= 3
    assert abs(local_minutes(sunset) - (17 * 60 + 22)) <= 3


def test_no_sunrise_in_the_polar_night():
    assert sky.sun_times(date(2026, 12, 21), 80.0, 0.0) is None


def test_moon_age_and_light():
    # The full moon of 26 October 2026: half a lunar month after the new
    # moon, within a day
    full = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    assert abs(sky.moon_age(full) - sky.LUNAR_MONTH / 2) < 1.0
    assert sky.moon_illumination(sky.LUNAR_MONTH / 2) == 1.0
    assert sky.moon_illumination(0.0) == 0.0
