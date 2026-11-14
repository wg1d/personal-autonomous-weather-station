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
- the absolute humidity: the mass of water vapour in a cubic metre of
  air, whatever its temperature;
- the vapour pressure deficit: how much more water the air could take,
  that is how fast it dries plants, soil and laundry;
- the forecast of the barometer: the Zambretti method, which reads the
  weather to come from the pressure and its trend;
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


def absolute_humidity(temperature, humidity):
    """The absolute humidity, in grams of water per cubic metre of air,
    from the temperature (°C) and the relative humidity (%): the pressure
    of the vapour (Magnus formula, in hPa), turned into a mass with the
    law of ideal gases (216.7 = 100 / 461.5, the constant of water
    vapour, in g·K/(hPa·m³))."""
    if temperature is None or humidity is None:
        return None
    saturated = 6.112 * math.exp(MAGNUS_A * temperature
                                 / (MAGNUS_B + temperature))
    return 216.7 * saturated * humidity / 100 / (273.15 + temperature)


def vapour_pressure_deficit(temperature, humidity):
    """The vapour pressure deficit, in kPa: the pressure of the water
    vapour that saturated air would hold at this temperature (Tetens
    formula), minus the one the air holds, from the temperature (°C) and
    the relative humidity (%)."""
    if temperature is None or humidity is None:
        return None
    saturated = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
    return saturated * (1 - humidity / 100)


def sea_level_factor(altitude):
    """The factor that turns a pressure measured at this altitude, in
    metres, into the pressure at sea level.

    The formula of the standard atmosphere: the pressure falls by about
    1 hPa every 8 metres near the ground. It takes a temperature of 15 °C
    at sea level; the real temperature would change the result by less
    than 1 hPa at a few hundred metres. At 100 metres, the factor is
    1.0119: about 12 hPa more.
    """
    return (1 - 0.0065 * altitude / 288.15) ** -5.255


# start snippet zambretti
# The Zambretti forecaster, sold by Negretti & Zambra in 1915, turns the
# pressure at sea level and its trend into one of 26 forecasts, numbered
# here from 1 to 32 as in the usual tables. Each trend uses its own line:
# a falling pressure gives the numbers 1 to 9, a steady one 10 to 19, a
# rising one 20 to 32. The original is a disc calculator; these lines are the
# form published with the Zambretti example of SAS
# (github.com/sassoftware/iot-zambretti-weather-forcasting), of the same
# family as the older ones of integritext.net/DrKFS/zambretti.htm.
# A change of 1.6 hPa or more in 3 hours counts as rising or falling: in
# the terms of the shipping forecast of the Met Office, up to 1.5 hPa the
# pressure only changes "slowly"
ZAMBRETTI_TREND = 1.6
ZAMBRETTI_LINES = {
    "falling": (127, 0.12, 1, 9),
    "steady": (144, 0.13, 10, 19),
    "rising": (185, 0.16, 20, 32),
}


def zambretti(pressure, change):
    """The number of the Zambretti forecast, from 1 to 32, for a pressure
    at sea level (hPa) and its change over 3 hours (hPa). None when one
    of them is missing. This simple form ignores the wind and the season,
    which the original also uses."""
    if pressure is None or change is None:
        return None
    if change <= -ZAMBRETTI_TREND:
        trend = "falling"
    elif change >= ZAMBRETTI_TREND:
        trend = "rising"
    else:
        trend = "steady"
    start, slope, lowest, highest = ZAMBRETTI_LINES[trend]
    return min(max(round(start - slope * pressure), lowest), highest)
# end snippet zambretti
