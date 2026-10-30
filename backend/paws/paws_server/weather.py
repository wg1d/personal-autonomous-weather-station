"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/weather.py

Description:
The quantities computed from the measurements of the station, which the
sensor does not measure itself:

- the dew point: the temperature at which the air, cooled down, would be
  saturated with water, and dew, frost or fog would form;
- the feels-like temperature in the heat: how hot humid air feels, as
  the heat index of the weather services. In the cold, the feels-like
  temperature depends on the wind, which the station does not measure:
  it is then not computed;
- the pressure at sea level: the pressure the station would measure at
  the altitude 0, which the weather maps and forecasts give, so that
  places at different altitudes can be compared.

Each function returns None when a measurement it needs is missing.

Dependencies: Python standard library (math).
"""

import math

# The constants of the Magnus formula (Sonntag, 1990), precise to about
# 0.1 °C between -45 °C and 60 °C
MAGNUS_A = 17.62
MAGNUS_B = 243.12  # °C

# The heat index is only defined in the heat, with enough humidity: below
# these limits, the air feels as warm as the temperature
HEAT_INDEX_MIN_C = 27.0
HEAT_INDEX_MIN_HUMIDITY = 40.0


def dew_point(temperature, humidity):
    """The dew point, in °C, from the temperature (°C) and the relative
    humidity (%), with the Magnus formula."""
    if temperature is None or humidity is None or humidity <= 0:
        return None
    gamma = (math.log(humidity / 100)
             + MAGNUS_A * temperature / (MAGNUS_B + temperature))
    return MAGNUS_B * gamma / (MAGNUS_A - gamma)


def feels_like(temperature, humidity):
    """The feels-like temperature in the heat, in °C: the heat index of
    the US weather service (the Rothfusz formula, written in °F). None
    below 27 °C or 40 % of humidity, where it is not defined."""
    if temperature is None or humidity is None:
        return None
    if temperature < HEAT_INDEX_MIN_C or humidity < HEAT_INDEX_MIN_HUMIDITY:
        return None
    t = temperature * 9 / 5 + 32
    h = humidity
    index = (-42.379 + 2.04901523 * t + 10.14333127 * h
             - 0.22475541 * t * h - 0.00683783 * t * t
             - 0.05481717 * h * h + 0.00122874 * t * t * h
             + 0.00085282 * t * h * h - 0.00000199 * t * t * h * h)
    return (index - 32) * 5 / 9


def sea_level_factor(altitude):
    """The factor that turns a pressure measured at this altitude, in
    metres, into the pressure at sea level.

    The formula of the standard atmosphere: the pressure falls by about
    1 hPa every 8 metres near the ground. It takes a temperature of 15 °C
    at sea level; the real temperature would change the result by less
    than 1 hPa at a few hundred metres. At 140 metres, the factor is
    1.0168: about 17 hPa more.
    """
    return (1 - 0.0065 * altitude / 288.15) ** -5.255
