"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/sky.py

Description:
The sun and the moon, computed from the date and the position of the
station, without any sensor:

- the sunrise and the sunset, with the sunrise equation, precise to about
  a minute;
- the phase of the moon: its age since the last new moon, counted from
  a known new moon and the length of a lunar month.

Dependencies: Python standard library (math, datetime).
"""

import math
from datetime import datetime, timedelta, timezone

# The days of the astronomers (Julian days) are counted from noon, 1
# January 2000, in UTC: day 2451545
J2000 = 2451545.0
J2000_NOON = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)

# The tilt of the axis of the Earth, in degrees
OBLIQUITY = 23.4397

# The sun rises when its top edge appears on the horizon: its centre is
# then 0.833° below it (its radius, and the bending of light by the air)
SUNRISE_ANGLE = -0.833


def _sin(degrees):
    return math.sin(math.radians(degrees))


def _cos(degrees):
    return math.cos(math.radians(degrees))


def sun_times(day, latitude, longitude):
    """The sunrise and the sunset of a day, as datetimes in UTC.

    day is a date; latitude and longitude are in degrees, north and east
    positive. Returns (sunrise, sunset), or None when the sun does not
    rise or does not set that day (near the poles).

    The sunrise equation: the position of the Earth on its orbit gives
    the declination of the sun (how far north or south of the equator it
    stands), then the angle the Earth turns between sunrise and noon at
    this latitude.
    """
    # The days since 1 January 2000, then the solar noon of the day at
    # this longitude, in Julian days
    n = (day - J2000_NOON.date()).days
    mean_noon = n - longitude / 360
    # Where the Earth is on its orbit: the mean anomaly M, the equation of
    # the centre C (the orbit is not a circle), the ecliptic longitude
    anomaly = (357.5291 + 0.98560028 * mean_noon) % 360
    centre = (1.9148 * _sin(anomaly) + 0.0200 * _sin(2 * anomaly)
              + 0.0003 * _sin(3 * anomaly))
    ecliptic = (anomaly + centre + 180 + 102.9372) % 360
    transit = (J2000 + mean_noon + 0.0053 * _sin(anomaly)
               - 0.0069 * _sin(2 * ecliptic))
    declination = math.degrees(math.asin(_sin(ecliptic) * _sin(OBLIQUITY)))
    # The hour angle: how far the Earth turns between sunrise and noon
    cos_angle = ((_sin(SUNRISE_ANGLE) - _sin(latitude) * _sin(declination))
                 / (_cos(latitude) * _cos(declination)))
    if not -1 <= cos_angle <= 1:
        return None
    half_day = math.degrees(math.acos(cos_angle)) / 360
    return tuple(J2000_NOON + timedelta(days=moment - J2000)
                 for moment in (transit - half_day, transit + half_day))


# A known new moon, and the mean length of a lunar month, from one new
# moon to the next, in days
NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
LUNAR_MONTH = 29.530588853


def moon_age(moment):
    """The age of the moon at a moment (a datetime in UTC): the days since
    the last new moon, from 0 to 29.5."""
    days = (moment - NEW_MOON).total_seconds() / 86400
    return days % LUNAR_MONTH


def moon_illumination(age):
    """The part of the moon that is lit, from 0 (new moon) to 1 (full
    moon), for its age in days."""
    return (1 - math.cos(2 * math.pi * age / LUNAR_MONTH)) / 2
