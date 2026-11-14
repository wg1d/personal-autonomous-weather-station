"""Tests of the dashboard: health, navigation, queries, views and
comparison."""

from datetime import date, datetime, timedelta, timezone

import time

import pytest

from paws_server import database
from paws_server.dashboard import (build_comparison, build_view,
                                   clothes_advice, running_advice,
                                   compare_after_move,
                                   compare_dates, day_extremes,
                                   dew_comfort, forecast, french_date,
                                   frost_advice, number,
                                   sun_events, value_range, yesterday_text,
                                   sunrise_tomorrow,
                                   laundry_advice, sparkline,
                                   watering_advice,
                                   format_age, health,
                                   midnights, resolution, shown,
                                   parts_of, pressure_state,
                                   shown_limits, start_of, trend,
                                   to_timestamp, trend_text,
                                   feels_text, meaning_text,
                                   dew_outlook, humidity_state,
                                   view_after_move, view_after_step,
                                   view_after_zoom)

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

# The period of the Graphs tab when the page opens: the last 24 hours
DAY = {"length": 86400, "end": None}


@pytest.fixture
def connection(tmp_path):
    connection = database.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def row(timestamp, temperature, time_valid=1):
    return (timestamp, time_valid, temperature, 50.0, 1013.0)


# --- French ------------------------------------------------------------------

def test_dates_and_numbers_in_french():
    moment = datetime(2026, 10, 29, 14, 30)
    assert french_date(moment, "%a %d %b, %H:%M") == "jeu. 29 oct., 14:30"
    assert french_date(moment, "%A %d %B %Y") == "jeudi 29 octobre 2026"
    assert number(11.44) == "11,4"
    assert number(1.2, sign=True) == "+1,2"


def measurement(temperature, dew, deficit):
    return {"temperature_c": temperature, "dew_point_c": dew,
            "vpd_kpa": deficit}


def test_laundry_advice():
    steady = {"sea_level_hpa": 0.2}
    assert laundry_advice(measurement(23.4, 9.5, 1.7),
                          steady)[0] == "Bon séchage"
    assert laundry_advice(measurement(15.0, 9.0, 0.6),
                          steady)[0] == "Séchage lent"
    # Close to the dew point, or with a fast fall of the pressure, the
    # laundry goes in, whatever the deficit
    headline, detail = laundry_advice(measurement(9.8, 8.5, 0.1), steady)
    assert headline == "À rentrer" and "rosée" in detail
    headline, detail = laundry_advice(measurement(23.4, 9.5, 1.7),
                                      {"sea_level_hpa": -4.0})
    assert headline == "À rentrer" and "pluie" in detail


# A day of November: the sun rises at 07:50 and sets at 17:30
SUN = (datetime(2026, 11, 11, 7, 50), datetime(2026, 11, 11, 17, 30))


def at(hour, minute=0):
    return datetime(2026, 11, 11, hour, minute)


def test_laundry_advice_follows_the_hour():
    steady = {"sea_level_hpa": 0.2}
    dry = measurement(15.0, 5.0, 1.2)
    # At night, whatever the air: no drying, hang it out after the dew
    headline, detail = laundry_advice(dry, steady, at(22), SUN)
    assert headline == "Pas de séchage la nuit"
    assert detail.endswith("Étendez-le demain vers 09:50.")
    assert laundry_advice(dry, steady, at(6), SUN)[1].endswith(
        "Étendez-le ce matin vers 09:50.")
    # In the morning, the dew dries first; in the afternoon, the hour to
    # bring it in; in the last hour of the day, bring it in now
    assert "après 09:50" in laundry_advice(dry, steady, at(8, 30), SUN)[1]
    headline, detail = laundry_advice(dry, steady, at(13), SUN)
    assert headline == "Bon séchage"
    assert detail.endswith("Rentrez-le avant 16:30.")
    assert laundry_advice(dry, steady, at(16, 45), SUN)[0] == "À rentrer"


def test_watering_advice_follows_the_hour():
    rows = [{"vpd_kpa": 1.5}]
    headline, detail = watering_advice(rows, {}, at(7), SUN)
    assert headline == "Conseillé ce matin" and "avant 10:50" in detail
    headline, detail = watering_advice(rows, {}, at(13), SUN)
    assert headline == "Conseillé ce soir" and "Attendez 15:30" in detail
    headline, detail = watering_advice(rows, {}, at(16), SUN)
    assert headline == "Conseillé ce soir" and "bon moment" in detail
    # Without the sun, no hour
    assert watering_advice(rows, {})[0] == "Conseillé"


def air(temperature, feels=None, pressure=1030.0):
    return {"temperature_c": temperature, "feels_like_c": feels,
            "sea_level_hpa": pressure}


def test_clothes_advice():
    steady = {"sea_level_hpa": 0.0}
    assert clothes_advice(air(-2.0), steady, at(13), SUN) == (
        "Manteau, bonnet et gants",
        ["-2 °C, il gèle : couvrez la tête, les mains et le cou."])
    assert clothes_advice(air(11.0), steady, at(13), SUN) == (
        "Veste ou pull épais", ["11 °C, c'est frais."])
    # A cap in the sun of a warm day, not at night
    assert clothes_advice(air(24.0), steady, at(13), SUN)[1] == [
        "24 °C, il fait bon.", "Une casquette au soleil."]
    assert clothes_advice(air(24.0), steady, at(22), SUN)[1] == [
        "24 °C, il fait bon."]
    # The heat index counts more than the air
    assert clothes_advice(air(28.0, 31.0), steady, at(13), SUN)[:2] == (
        "Tenue légère et claire",
        ["31 °C ressentis, il fait chaud : buvez souvent.",
         "Une casquette au soleil."])
    # An umbrella when the pressure falls fast
    assert clothes_advice(air(11.0), {"sea_level_hpa": -4.0}, at(13),
                          SUN)[1][1:] == [
        "Un parapluie : la pluie est probable."]
    # Showers only possible: the umbrella just in case (1013 hPa, steady:
    # "Beau, averses possibles")
    assert clothes_advice(air(11.0, pressure=1013.0), steady, at(13),
                          SUN)[1][1:] == [
        "Un parapluie au cas où : des averses sont possibles."]
    assert clothes_advice(air(None), steady, at(13), SUN) is None


def test_running_advice():
    steady = {"sea_level_hpa": 0.0}
    # At 10 °C, a runner dresses as for 20 °C
    assert running_advice(air(10.0), steady, at(13), SUN) == (
        "Short et tee-shirt",
        ["Pas besoin de trop se couvrir pour courir."])
    assert running_advice(air(-6.0), steady, at(13), SUN)[0] == (
        "Collant, veste, bonnet et gants")
    assert running_advice(air(10.0), steady, at(19), SUN)[1][1:] == [
        "Il fait nuit : une lampe frontale ou un gilet réfléchissant."]
    assert running_advice(air(31.0, 34.0), steady, at(13), SUN)[0] == (
        "Trop chaud")


def test_watering_advice_follows_the_driest_moment():
    rows = [{"vpd_kpa": 0.2}, {"vpd_kpa": 1.71}, {"vpd_kpa": None}]
    headline, detail = watering_advice(rows, {"sea_level_hpa": 0.0})
    assert headline == "Conseillé"
    assert detail.startswith("Air très asséchant (jusqu'à 1,71 kPa)")
    assert watering_advice([{"vpd_kpa": 0.3}], {})[0] == "Pas nécessaire"
    assert watering_advice([], {}) is None


def test_sparkline_is_an_svg_image():
    rows = [{"local_time": f"2026-10-05 {hour:02d}:00:00",
             "temperature_c": value}
            for hour, value in [(10, 5.0), (11, None), (12, 7.0),
                                (13, 9.0)]]
    image = sparkline(rows, "temperature_c", "#d95926")
    assert image.startswith("data:image/svg+xml;utf8,")
    # The missing value cuts the line: the first piece holds a single
    # point and is not drawn, the second one is
    assert image.count("polyline") == 1
    assert sparkline(rows[:1], "temperature_c", "#d95926") is None


def test_forecast_names_the_part_of_the_day_ahead():
    last = {"sea_level_hpa": 1035.0, "temperature_c": 15.0,
            "dew_point_c": 6.2}
    steady = {"sea_level_hpa": 0.0}
    assert forecast(last, steady, datetime(2026, 7, 1, 10, 30)) == (
        "Cet après-midi", "Beau temps stable", "sun",
        ["Pluie peu probable"])
    assert forecast(last, steady, datetime(2026, 7, 1, 15, 0))[0] == (
        "Ce soir et cette nuit")
    assert forecast(last, steady, datetime(2026, 7, 1, 21, 0))[0] == (
        "Demain matin")
    assert forecast(last, steady, datetime(2026, 7, 1, 3, 0))[0] == (
        "Ce matin")
    # A low pressure that falls: rain, with its icon
    rain = forecast({**last, "sea_level_hpa": 985.0},
                    {"sea_level_hpa": -3.0}, datetime(2026, 7, 1, 10, 30))
    # The text already speaks of rain: no rain line
    assert rain[2] == "cloud-rain" and rain[3] == []
    assert forecast(last, {"sea_level_hpa": None},
                    datetime(2026, 7, 1, 10, 30)) is None



def test_dew_outlook_for_the_night_and_the_morning():
    dry = {"temperature_c": 15.0, "dew_point_c": 5.6}
    near = {"temperature_c": 7.0, "dew_point_c": 5.6}
    assert dew_outlook(dry, datetime(2026, 7, 1, 21, 0)) == (
        "D'ici là : vers 6 °C au plus bas, rosée ou brouillard "
        "possibles par ciel clair")
    # In the afternoon, the title is "Ce soir et cette nuit"
    assert dew_outlook(dry, datetime(2026, 7, 1, 15, 0)).startswith(
        "Cette nuit : ")
    assert dew_outlook(near, datetime(2026, 7, 1, 21, 0)).endswith(
        "rosée ou brouillard probables")
    assert "givre" in dew_outlook({"temperature_c": 4.0,
                                   "dew_point_c": -1.0},
                                  datetime(2026, 7, 1, 21, 0))
    # In the morning, only when the air is nearly saturated
    assert dew_outlook(dry, datetime(2026, 7, 1, 9, 0)) == ""
    assert dew_outlook(near, datetime(2026, 7, 1, 9, 0)) == (
        "Rosée ou brouillard probables")
    assert dew_outlook({"temperature_c": None, "dew_point_c": 5.6},
                       datetime(2026, 7, 1, 21, 0)) == ""


def test_temperature_against_yesterday():
    last = {"temperature_c": 17.1}
    assert yesterday_text(last, {"temperature_c": 15.0}) == (
        "+2,1 °C vs hier")
    assert yesterday_text(last, None) == ""


def test_frost_advice():
    evening = datetime(2026, 11, 1, 20, 0)
    noon = datetime(2026, 11, 1, 12, 0)
    assert frost_advice(measurement(-1.0, -3.0, 0.1), noon)[0] == "Il gèle"
    assert frost_advice(measurement(5.0, 0.5, 0.3), evening)[0] == (
        "Gelée possible")
    # The same air at noon, or a mild and humid evening: no frost tile
    assert frost_advice(measurement(5.0, 0.5, 0.3), noon) is None
    assert frost_advice(measurement(10.0, 8.0, 0.2), evening) is None


def test_sunrise_of_tomorrow_only_in_the_evening(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Paris")
    time.tzset()
    paris = (48.853, 2.349)
    evening = datetime(2026, 11, 14, 20, 0, tzinfo=timezone.utc)
    assert sunrise_tomorrow(paris, evening).date() == date(2026, 11, 15)
    noon = datetime(2026, 11, 14, 11, 0, tzinfo=timezone.utc)
    assert sunrise_tomorrow(paris, noon) is None
    assert sunrise_tomorrow(None, evening) is None
    # The line of the top card: today's times, then tomorrow's sunrise
    assert [kind for kind, _, _ in sun_events(paris, noon)] == [
        "sunrise", "sunset"]
    # After the sunset: the sunset, then the sunrise of tomorrow
    assert [kind for kind, _, _ in sun_events(paris, evening)] == [
        "sunset", "sunrise"]
    assert sun_events(None, noon) == []
    monkeypatch.undo()
    time.tzset()


def test_dew_point_comfort():
    assert dew_comfort(6.8) == "air sec"
    assert dew_comfort(17.0) == "un peu lourd"
    assert dew_comfort(22.0) == "étouffant"


# --- Health ------------------------------------------------------------------

def test_trend_over_three_hours():
    rows = [{"timestamp": "2026-10-05T08:00:00Z", "temperature_c": 10.0},
            {"timestamp": "2026-10-05T09:00:00Z", "temperature_c": 11.0},
            {"timestamp": "2026-10-05T11:00:00Z", "temperature_c": 13.5}]
    # 3 hours before 12:00 is 09:00: 14.0 - 11.0
    last = {"timestamp": "2026-10-05T12:00:00Z", "temperature_c": 14.0}
    assert trend(rows, last, "temperature_c") == 3.0
    # Without a row old enough, no trend
    assert trend(rows[2:], last, "temperature_c") is None


def test_trend_text():
    assert trend_text(3.0, "°C") == "↑ +3,0 °C en 3 h"
    assert trend_text(-0.42, "hPa") == "↓ -0,4 hPa en 3 h"
    assert trend_text(0.02, "%") == "→ stable en 3 h"
    assert trend_text(None, "%") == ""


def test_pressure_state_follows_the_scale():
    assert pressure_state(1013.0, 0.04) == "Pression moyenne · stable"
    assert pressure_state(1025.0, 1.5) == (
        "Pression haute · en légère hausse")
    assert pressure_state(1000.0, -4.1) == (
        "Pression basse · en forte baisse")
    assert pressure_state(990.0, -6.5) == (
        "Pression basse · en très forte baisse")
    assert pressure_state(1013.0, None) == "Pression moyenne"
    assert pressure_state(None, 1.0) == ""


def test_humidity_state_tells_how_the_air_feels():
    # Cold air holds little water: no "air sec" next to a high humidity
    assert humidity_state({"dew_point_c": 4.9}) == "Point de rosée 4,9 °C"
    assert humidity_state({"dew_point_c": 17.0}) == (
        "Point de rosée 17,0 °C · un peu lourd")
    assert humidity_state({"dew_point_c": None}) == ""


def test_feels_like_only_when_it_differs():
    assert feels_text({"temperature_c": 30.0, "feels_like_c": 33.4}) == (
        "Ressenti 33 °C")
    assert feels_text({"temperature_c": 30.0, "feels_like_c": 30.4}) == ""
    assert feels_text({"temperature_c": 12.0, "feels_like_c": None}) == ""


def test_extremes_of_the_local_day_only():
    rows = [{"local_time": "2026-10-04 23:45:00", "temperature_c": 2.0},
            {"local_time": "2026-10-05 04:45:00", "temperature_c": 5.3},
            {"local_time": "2026-10-05 09:00:00", "temperature_c": None},
            {"local_time": "2026-10-05 14:00:00", "temperature_c": 15.9}]
    assert day_extremes(rows, "2026-10-05", "temperature_c") == (
        (5.3, "04:45"), (15.9, "14:00"))
    assert day_extremes(rows, "2026-10-06", "temperature_c") is None


def test_health_without_data_warns():
    stale, status, alert = health(None, NOW)
    assert stale
    assert alert == "Aucune mesure reçue pour l'instant : vérifiez la station."


def test_health_of_a_recent_measurement():
    last = {"timestamp": "2026-10-05T11:30:00Z"}
    assert health(last, NOW) == (
        False, "Mesure de 11:30 · il y a 30 min", "")


def test_health_of_an_older_day_gives_its_date():
    last = {"timestamp": "2026-10-03T11:30:00Z"}
    _, status, _ = health(last, NOW)
    assert status == "Mesure du 03 oct. à 11:30 · il y a 2 jours"


def test_health_warns_after_two_hours():
    last = {"timestamp": "2026-10-05T08:55:00Z"}
    stale, status, alert = health(last, NOW)
    assert stale
    assert alert == ("Aucune nouvelle mesure depuis 3 h 05 min : vérifiez "
                     "la station.")


def test_long_silence_is_counted_in_days():
    assert format_age(timedelta(days=4, hours=3)) == "4 jours"


# --- Navigation ----------------------------------------------------------------

def test_period_shown_ends_now_by_default():
    start, stop = shown({"length": 7 * 86400, "end": None}, NOW)
    assert (start, stop) == (NOW - timedelta(days=7), NOW)


def test_drag_or_zoom_sets_the_period_shown():
    # In UTC (see utc_local_time): 6 hours, ending 2 hours ago
    limits = ["2026-10-05 04:00:00", "2026-10-05 10:00:00"]
    assert view_after_move(limits, NOW) == {
        "length": 6 * 3600, "end": "2026-10-05T10:00:00Z"}


def test_limits_reported_by_plotly_for_the_three_axes():
    relayout = {f"xaxis{suffix}.range[{bound}]": value
                for suffix in ["", "2", "3"]
                for bound, value in [(0, "2026-10-04 10:00:00"),
                                     (1, "2026-10-05 10:00:00")]}
    assert shown_limits(relayout) == ["2026-10-04 10:00:00",
                                      "2026-10-05 10:00:00"]
    # A click in the legend changes no time axis
    assert shown_limits({"legend.x": 0.1}) is None


def test_back_to_the_present_follows_the_new_data():
    limits = ["2026-10-04 12:00:00", "2026-10-05 12:00:00"]
    assert view_after_move(limits, NOW)["end"] is None


def test_arrows_move_by_the_length_shown():
    before = view_after_step(DAY, -1, NOW)
    assert before == {"length": 86400, "end": "2026-10-04T12:00:00Z"}
    # Two days back, then one forward: still in the past
    two_before = view_after_step(before, -1, NOW)
    assert view_after_step(two_before, 1, NOW) == before


def test_arrow_back_to_the_present_follows_the_new_data():
    before = view_after_step(DAY, -1, NOW)
    assert view_after_step(before, 1, NOW)["end"] is None


def test_zoom_buttons_halve_and_double_the_length():
    # At the present, the zoom keeps the end at the present
    assert view_after_zoom(DAY, 0.5, NOW) == {"length": 43200, "end": None}
    # In the past, around the same middle: 4 October 00:00
    before = view_after_step(DAY, -1, NOW)
    assert view_after_zoom(before, 0.5, NOW) == {
        "length": 43200, "end": "2026-10-04T06:00:00Z"}
    # Twice as long, around the same middle; once more, the period
    # reaches the present: the page follows the new data again
    twice = view_after_zoom(before, 2, NOW)
    assert twice == {"length": 172800, "end": "2026-10-05T00:00:00Z"}
    assert view_after_zoom(twice, 2, NOW)["end"] is None
    # Never shorter than 3 hours
    assert view_after_zoom({"length": 3 * 3600, "end": None}, 0.5,
                           NOW)["length"] == 3 * 3600


def test_resolution_follows_the_length_shown():
    assert resolution(timedelta(hours=24)) == "rows"
    assert resolution(timedelta(days=30)) == "hours"
    assert resolution(timedelta(days=365)) == "days"


def test_midnights_between_two_times():
    first = datetime(2026, 10, 3, 18, 0)
    last = datetime(2026, 10, 5, 12, 0)
    assert midnights(first, last) == [datetime(2026, 10, 4),
                                      datetime(2026, 10, 5)]


# --- Queries -------------------------------------------------------------------

def test_rows_between_skips_rows_outside_and_invalid(connection):
    database.insert_rows(connection, [
        row("2026-10-04T11:45:00Z", 10.0),         # before the period
        row("2026-10-04T12:00:00Z", 11.0),
        row("2026-10-05T11:45:00Z", 12.0),
        row("2026-10-05T12:00:00Z", 13.0),         # end: not included
        row("2000-01-01T00:15:00Z", 99.0, 0),      # clock not valid
    ])
    rows = database.rows_between(connection, "2026-10-04T12:00:00Z",
                                 "2026-10-05T12:00:00Z")
    assert [r["temperature_c"] for r in rows] == [11.0, 12.0]


def test_hourly_summary(connection):
    database.insert_rows(connection, [
        row("2026-10-05T10:00:00Z", 10.0),
        row("2026-10-05T10:45:00Z", 11.0),
        row("2026-10-05T11:00:00Z", 20.0),
    ])
    hours = database.hourly_summary(connection, "2026-10-05T00:00:00Z",
                                    "2026-10-06T00:00:00Z")
    assert [(h["local_time"], h["temperature_c"]) for h in hours] == [
        ("2026-10-05 10:30:00", 10.5), ("2026-10-05 11:30:00", 20.0)]


def test_daily_summary(connection):
    database.insert_rows(connection, [
        row("2026-10-04T06:00:00Z", 10.0),
        row("2026-10-04T14:00:00Z", 20.0),
        row("2026-10-04T15:00:00Z", None),         # missing value: ignored
        row("2026-10-05T06:00:00Z", 12.0),
    ])
    days = database.daily_summary(connection, "2026-01-01T00:00:00Z",
                                  "2026-10-06T00:00:00Z")
    assert [d["day"] for d in days] == ["2026-10-04", "2026-10-05"]
    first = days[0]
    assert (first["temperature_c_min"], first["temperature_c_avg"],
            first["temperature_c_max"]) == (10.0, 15.0, 20.0)


# --- Graphs tab ----------------------------------------------------------------

def test_view_of_a_day_shows_every_row(connection):
    database.insert_rows(connection, [row("2026-10-05T11:45:00Z", 12.0)])
    figure = build_view(connection, DAY, NOW)["figure"]
    assert figure["data"][0]["y"] == [12.0]
    # One line per quantity, then the dew point and the feels-like
    # temperature in the graph of the temperature
    assert len(figure["data"]) == 5
    assert [trace["name"] for trace in figure["data"][1:3]] == [
        "Point de rosée", "Ressenti"]


def test_view_holds_as_much_again_on_each_side(connection):
    database.insert_rows(connection, [
        row("2026-10-03T12:00:00Z", 10.0),          # 2 days before: kept
        row("2026-10-03T11:45:00Z", 9.0),           # too old: not loaded
    ])
    figure = build_view(connection, DAY, NOW)["figure"]
    assert figure["data"][0]["y"] == [10.0]


def test_view_of_a_year_shows_min_average_max(connection):
    database.insert_rows(connection, [row("2026-10-05T11:45:00Z", 12.0)])
    view = {"length": 365 * 86400, "end": None}
    names = [trace.get("name")
             for trace in build_view(connection, view, NOW)["figure"]["data"]]
    assert names[:3] == [None, "Température : min – max du jour",
                         "Température : moyenne du jour"]


def test_figure_holds_the_limits_of_the_data(connection):
    database.insert_rows(connection, [row("2026-10-01T00:00:00Z", 12.0)])
    layout = build_view(connection, DAY, NOW)["figure"]["layout"]
    # On the three time axes, which move together
    for axis in ["xaxis", "xaxis2", "xaxis3"]:
        assert layout[axis]["minallowed"] == "2026-10-01 00:00:00"
        assert layout[axis]["maxallowed"] == "2026-10-05 12:00:00"



def test_a_young_station_shows_its_whole_year(connection):
    # 4 days of data: the year that ends now is shown whole, empty before
    database.insert_rows(connection, [row("2026-10-01T00:00:00Z", 12.0)])
    year = {"length": 365 * 86400, "end": None}
    layout = build_view(connection, year, NOW)["figure"]["layout"]
    assert layout["xaxis"]["minallowed"] == "2025-10-05 12:00:00"
    # Once dragged, the graphs stop at the data
    moved_year = {**year, "end": "2026-10-05T11:00:00Z"}
    layout = build_view(connection, moved_year, NOW)["figure"]["layout"]
    assert layout["xaxis"]["minallowed"] == "2026-10-01 00:00:00"


def test_scale_of_round_values_from_the_period_shown():
    curve = {"x": ["2026-10-04 10:00:00", "2026-10-05 10:00:00",
                   "2026-10-07 10:00:00"],
             "y": [-20.0, 1012.4, 1031.0]}
    # The values in the margins do not count
    assert value_range([curve], "2026-10-05 00:00:00",
                       "2026-10-06 00:00:00", 5) == [1010, 1015]
    # Days are compared by their date
    days = {"x": ["2026-10-05"], "y": [12.0]}
    assert value_range([days], "2026-10-05 12:00:00",
                       "2026-10-06 12:00:00", 5) == [10, 15]
    assert value_range([curve], "2026-11-01 00:00:00",
                       "2026-11-02 00:00:00", 5) is None


def test_graphs_have_fixed_scales(connection):
    database.insert_rows(connection, [row("2026-10-05T11:45:00Z", 12.0)])
    layout = build_view(connection, DAY, NOW)["figure"]["layout"]
    assert layout["yaxis2"]["range"] == [0, 100]
    assert layout["yaxis3"]["range"] == [1010, 1015]



# --- Compare tab ---------------------------------------------------------------

def test_any_day_chooses_its_whole_period():
    # Wednesday 14 October 2026 and Monday 7 December 2025
    for unit, starts in [("day", ("2026-10-14", "2025-12-07")),
                         ("week", ("2026-10-12", "2025-12-01")),
                         ("month", ("2026-10-01", "2025-12-01")),
                         ("year", ("2026-01-01", "2025-01-01"))]:
        compared = compare_dates(unit, "2026-10-14", "2025-12-07")
        assert (compared["reference"][:10],
                compared["comparison"][:10]) == starts


def test_period_from_the_two_lists():
    assert start_of("day", 2026, 10, 14) == date(2026, 10, 14)
    # February has no 31st: its last day instead
    assert start_of("day", 2026, 2, 31) == date(2026, 2, 28)
    assert start_of("month", 2025, 10) == date(2025, 10, 1)
    assert start_of("week", 2026, 41) == date(2026, 10, 5)
    # 2026 has 53 weeks, 2025 only 52: its week 53 is its last week
    assert start_of("week", 2025, 53) == date(2025, 12, 22)
    assert start_of("year", 2025) == date(2025, 1, 1)
    assert parts_of("week", date(2026, 10, 5)) == (2026, 41, None)
    assert parts_of("day", date(2026, 10, 14)) == (2026, 10, 14)


def test_month_is_compared_with_another_month(connection):
    database.insert_rows(connection, [
        row("2026-10-01T01:00:00Z", 15.0),          # October
        row("2025-12-01T01:00:00Z", 2.0),           # December
    ])
    compared = compare_dates("month", "2026-10-01", "2025-12-01")
    assert compared["length"] == 31 * 86400
    data = build_comparison(connection, compared, NOW)["data"]
    reference, comparison = data[:2]
    assert reference["name"] == "Octobre 2026"
    assert comparison["name"] == "Décembre 2025"
    # One hour after the start of each month: drawn at the same place
    # (the middle of the hour, see hourly_summary())
    assert reference["x"] == comparison["x"] == ["2026-10-01 01:30:00"]
    assert comparison["y"] == [2.0]


def test_drag_moves_both_periods_together():
    compared = compare_dates("month", "2026-10-01", "2025-12-01")
    # The reference dragged to start 6 days later
    limits = ["2026-10-07 00:00:00", "2026-11-07 00:00:00"]
    moved = compare_after_move(limits, compared)
    assert (moved["reference"], moved["comparison"]) == (
        "2026-10-07T00:00:00Z", "2025-12-07T00:00:00Z")
    # The legend now gives the exact dates shown
    assert not moved["chosen"]
