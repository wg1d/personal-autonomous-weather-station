"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/dashboard.py

Description:
The dashboard: the health of the station, the last measurement, and the
graphs of temperature, humidity and pressure. Four tabs, in a
navigation panel on the left (at the bottom on a phone):

- Now: the health of the station, and the last measurement;
- Graphs: the graphs over a period chosen with the buttons (24 hours,
  7 days, 30 days, 1 year), moved by one period with the arrows, or by
  dragging the graphs with the mouse or a finger, and zoomed with the
  mouse wheel or two fingers;
- Compare: two days, weeks, months or years drawn over each other,
  aligned on their start, then dragged and zoomed together;
- Data: the export of all the measurements, and the upload by hand of
  the files downloaded from the maintenance page of the station (see
  transfer.py).

Over a long period, the graphs show the minimum, average and maximum of
each day. The page has a dark theme only.

Built with Dash: the page is described in Python, Plotly draws the graphs
in the browser, and Dash calls the functions marked @app.callback when
the visitor clicks, and every few minutes to show the new data. Its style
is in assets/style.css, which Dash adds to the page.

The timestamps are stored in UTC; the dashboard shows them in the local
time of the server.

Dependencies: dash (which includes plotly).
"""

import base64
import calendar
import math
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import plotly.io as pio
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from . import database, logs, sky, transfer, weather
from .protocol import TIMESTAMP_FORMAT

# The periods of the buttons of the Graphs tab, and their length
PERIODS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "1y": timedelta(days=365),
}
PERIOD_LABELS = {"24h": "24 heures", "7d": "7 jours", "30d": "30 jours",
                 "1y": "1 an"}
# The tabs of the navigation panel: value, name. The icon of a tab is
# chosen in style.css (see .tab-icon)
TABS = [
    ("now", "Maintenant"),
    ("graphs", "Courbes"),
    ("advice", "Conseils"),
    ("station", "Station"),
    ("compare", "Comparer"),
    ("data", "Données"),
]

# Shorter labels, shown on a phone instead (see style.css)
SHORT_LABELS = {"24h": "24 h", "7d": "7 j", "30d": "30 j", "1y": "1 an"}

# The units of the Compare tab. A period is chosen in short lists: the
# day, the month and the year for a day; the week number and the year for
# a week; the month and the year for a month; the year for a year
UNITS = {"day": "Jour", "week": "Semaine", "month": "Mois", "year": "Année"}

# The quantities shown: column of the database, name, unit, color. The
# three colors stay distinct for the most common forms of color blindness,
# and readable on the dark background of the cards
QUANTITIES = [
    ("temperature_c", "Température", "°C", "#d95926"),
    ("humidity_pct", "Humidité", "%", "#3987e5"),
    ("sea_level_hpa", "Pression au niveau de la mer", "hPa", "#199e70"),
]

# The computed quantities drawn in the graph of a quantity of the Graphs
# tab (see weather.py): column, name, unit, color, line, and the value of
# each day shown over a long period. The dew point in violet; the
# feels-like temperature, a variant of the temperature, in its color,
# dotted, and only in the heat. Over a long period, its maximum: the
# hottest the day felt
EXTRA_CURVES = {
    "temperature_c": [
        ("dew_point_c", "Point de rosée", "°C", "#9085e9", "solid", "avg"),
        ("feels_like_c", "Ressenti", "°C", "#d95926", "dot", "max"),
    ],
}

# How the air feels, from its dew point: up to each limit, in °C
DEW_COMFORT = [(10, "air sec"), (16, "confortable"), (20, "un peu lourd"),
               (None, "étouffant")]


def dew_comfort(dew):
    """How the air feels with this dew point, such as "air sec"."""
    for limit, feeling in DEW_COMFORT:
        if limit is None or dew < limit:
            return feeling


# How to read the values, at the bottom of the Now tab: one block per
# subject, closed until clicked, with its title and its paragraphs
EXPLANATIONS = [
    ("La pression et sa tendance", [
        "La pression est le poids de l'air au-dessus de la station. Sa "
        "valeur seule dit peu de choses : c'est sa variation qui annonce "
        "le temps.",
        "Quand elle baisse, une dépression approche : l'air monte, se "
        "refroidit et forme des nuages, d'où la pluie et le vent. Quand "
        "elle monte, un anticyclone s'installe : le temps devient plus "
        "sec et plus calme.",
        "Variation en 3 heures : moins de 0,1 hPa, stable ; jusqu'à "
        "1,5 hPa, légère ; jusqu'à 3,5 hPa, nette ; jusqu'à 6 hPa, forte ; "
        "au-delà, très forte. Ce sont des tendances, pas des prévisions "
        "sûres.",
        "La valeur est ramenée au niveau de la mer, comme dans les "
        "bulletins météo, pour se comparer aux autres villes : 1013 hPa "
        "en moyenne, moins de 1000 hPa dans une dépression marquée, plus "
        "de 1025 hPa dans un anticyclone.",
    ]),
    ("Le point de rosée", [
        "C'est la température à laquelle il faudrait refroidir l'air pour "
        "qu'il soit saturé d'eau : la vapeur se condense alors en rosée, "
        "en givre sous 0 °C, ou en brouillard.",
        "Ce qui compte, c'est l'écart avec la température : moins de "
        "2 °C, la rosée ou le brouillard sont probables ; un grand écart, "
        "l'air est sec.",
        "Il mesure la quantité d'eau dans l'air, et dit le confort : "
        "moins de 10 °C, air sec ; 10 à 16 °C, confortable ; 16 à 20 °C, "
        "un peu lourd ; plus de 20 °C, étouffant, avec des orages "
        "possibles en été.",
        "Par nuit calme et dégagée, la température descend rarement "
        "beaucoup sous le point de rosée : il donne une idée du minimum "
        "de la nuit.",
    ]),
    ("L'humidité relative", [
        "C'est la vapeur d'eau dans l'air, en pourcentage du maximum que "
        "l'air peut contenir à sa température. L'air chaud contient plus "
        "d'eau que l'air froid : la nuit, l'humidité monte souvent "
        "seulement parce que l'air se refroidit, sans eau en plus.",
        "Pour savoir si l'air est vraiment humide, le point de rosée est "
        "plus parlant.",
    ]),
    ("Le déficit de pression de vapeur", [
        "À une température donnée, l'air ne peut contenir qu'une quantité "
        "maximale de vapeur d'eau. Le déficit est l'écart entre ce maximum "
        "et ce que l'air contient : la force avec laquelle il « aspire » "
        "l'eau des plantes, du sol ou du linge. Il s'exprime en "
        "kilopascals (kPa).",
        "Contrairement à l'humidité relative, il tient compte de la "
        "température : à 80 % d'humidité, l'air à 30 °C sèche bien plus "
        "vite que l'air à 5 °C.",
        "Pour les plantes : moins de 0,4 kPa, elles transpirent peu, et "
        "les maladies à champignons se développent bien ; 0,8 à 1,2 kPa "
        "convient à la plupart des cultures ; au-delà de 1,6 kPa, elles "
        "ferment leurs pores pour garder leur eau, et poussent moins.",
    ]),
    ("Les conseils d'arrosage et de linge", [
        "Le conseil d'arrosage regarde le déficit le plus fort des "
        "dernières 24 heures : plus il est fort, plus les plantes et le "
        "sol ont perdu d'eau. La station ne mesure ni la pluie ni "
        "l'humidité du sol : vérifiez la terre avec le doigt avant "
        "d'arroser. Il donne aussi le bon moment : le matin jusqu'à 3 "
        "heures après le lever du soleil, ou le soir à partir de 2 heures "
        "avant son coucher, quand l'eau s'évapore moins.",
        "Le conseil de linge regarde le déficit du moment, la rosée et la "
        "pression : une pression qui baisse vite annonce souvent la pluie. "
        "Le vent et le soleil sèchent aussi le linge, mais la station ne "
        "les mesure pas. La nuit, l'air fraîchit et le linge reprend "
        "l'humidité : le conseil propose de l'étendre 2 heures après le "
        "lever du soleil, une fois la rosée partie, et de le rentrer une "
        "heure avant son coucher.",
    ]),
    ("La prévision du baromètre", [
        "Elle vient de la méthode Zambretti, celle des baromètres "
        "prévisionnistes vendus dès 1915 et des stations météo du "
        "commerce : la pression ramenée au niveau de la mer et sa "
        "tendance sur 3 heures donnent l'une de 26 prévisions pour les "
        "12 heures qui suivent la dernière mesure.",
        "Une pression haute et stable annonce le beau temps ; une "
        "pression basse qui baisse, la pluie. La méthode d'origine "
        "tient aussi compte du vent et de la saison, que la station ne "
        "mesure pas : c'est une estimation, moins sûre qu'une prévision "
        "de Météo-France.",
    ]),
    ("La tenue et la course à pied", [
        "La tenue suit la température ressentie : moins de 0 °C, "
        "manteau, bonnet et gants ; jusqu'à 8 °C, manteau ; jusqu'à "
        "14 °C, veste ; jusqu'à 19 °C, pull léger ; au-delà, tee-shirt. "
        "Le parapluie vient de la prévision du baromètre. La station ne "
        "mesure pas le vent : par jour de vent, ajoutez une couche.",
        "En courant, le corps se réchauffe, mais pas tout de suite : on "
        "porte environ une couche de moins que pour sortir. Au-delà de "
        "30 °C ressentis, le corps se refroidit mal, et mieux vaut "
        "courir tôt le matin.",
    ]),
    ("Le gel", [
        "La nuit, le sol et les plantes perdent leur chaleur vers le "
        "ciel, et gèlent avant l'air mesuré à hauteur de l'abri : une "
        "gelée est possible avec 2 ou 3 °C dans l'abri.",
        "Par nuit claire et calme, la température descend vers le point "
        "de rosée, où l'eau de l'air se condense et rend un peu de "
        "chaleur. Le soir, un point de rosée proche de 0 °C annonce donc "
        "une gelée possible. Les nuages et le vent la rendent moins "
        "probable, mais la station ne les mesure pas.",
    ]),
    ("La température ressentie", [
        "Au-dessus de 27 °C, l'humidité freine l'évaporation de la sueur : "
        "le corps se refroidit moins bien, et on a plus chaud que la "
        "température. La station calcule alors l'indice de chaleur des "
        "services météo américains.",
        "Par temps froid, le ressenti dépend surtout du vent, que la "
        "station ne mesure pas : il n'est pas calculé.",
    ]),
]


def explanations():
    """The blocks of EXPLANATIONS: each one opens on a click on its
    title (the <details> element of HTML, without any callback)."""
    return [html.Details(className="explanation", children=[
                html.Summary(title),
                *[html.P(paragraph) for paragraph in paragraphs]])
            for title, paragraphs in EXPLANATIONS]

# How the comparison is drawn in the Compare tab: the same color as the
# reference, paler and dashed, so that both can be told apart without
# relying on color
COMPARISON_OPACITY = 0.65
COMPARISON_DASH = "dash"

# The station uploads every hour: after 2 hours without data, it has
# missed an upload, and the dashboard warns
STALE_AFTER = timedelta(hours=2)

# How often the page asks for new data, in milliseconds
REFRESH_MS = 5 * 60 * 1000

# The format of the times given to Plotly, in local time
PLOTLY_TIME = "%Y-%m-%d %H:%M:%S"

# The page is in French. The names of the days and months are written
# here, instead of asking them to the system, whose language may be
# another one (see french_date())
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi",
        "dimanche"]
SHORT_DAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
          "août", "septembre", "octobre", "novembre", "décembre"]
SHORT_MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
                "août", "sept.", "oct.", "nov.", "déc."]

# The same names for Plotly, which writes the dates of the time axes and
# of the values under the mouse in the browser (the "locale" of the
# graphs). separators: a decimal comma, and a space between thousands
PLOTLY_FRENCH = {"fr": {"format": {
    "days": [DAYS[-1]] + DAYS[:-1],             # Plotly starts on Sunday
    "shortDays": [SHORT_DAYS[-1]] + SHORT_DAYS[:-1],
    "months": MONTHS, "shortMonths": SHORT_MONTHS,
    "date": "%d/%m/%Y", "decimal": ",", "thousands": " ",
}}}


# The dates of the time axes, in the French order, depending on the gap
# between two ticks, in milliseconds or in months ("M1"): the hour and the
# day ("ven. 30") below 1 day, the day below 1 month, the month below 1 year, then the
# year. <br> starts a second line
DATE_TICKS = [
    {"dtickrange": [None, 86400000], "value": "%H:%M<br>%a %d"},
    {"dtickrange": [86400000, "M1"], "value": "%a %d %b"},
    {"dtickrange": ["M1", "M12"], "value": "%b %Y"},
    {"dtickrange": ["M12", None], "value": "%Y"},
]


def french_date(moment, form):
    """Writes a date with strftime(), the names of the days (%A, %a) and
    of the months (%B, %b) in French: french_date(moment, "%a %d %b") gives
    "jeu. 29 oct."."""
    form = (form.replace("%A", DAYS[moment.weekday()])
            .replace("%a", SHORT_DAYS[moment.weekday()])
            .replace("%B", MONTHS[moment.month - 1])
            .replace("%b", SHORT_MONTHS[moment.month - 1]))
    return moment.strftime(form)


def number(value, decimals=1, sign=False):
    """Writes a number in French, with a decimal comma: "11,4", or "+1,2"
    with sign."""
    text = f"{value:+.{decimals}f}" if sign else f"{value:.{decimals}f}"
    return text.replace(".", ",")


def parse_timestamp(text):
    """Turns a timestamp of the station into a datetime in UTC.

    The format of the station is ISO 8601, which fromisoformat() reads,
    the Z suffix included, much faster than strptime().
    """
    return datetime.fromisoformat(text)


def to_timestamp(moment):
    """Turns a datetime in UTC into a timestamp of the station."""
    return moment.strftime(TIMESTAMP_FORMAT)


def to_local(moment):
    """Turns a datetime in UTC into the local time of the server."""
    return moment.astimezone().replace(tzinfo=None)


def from_local(text):
    """Turns a local time of the page, such as "2026-10-04 10:12:33" or
    "2026-10-04", into a datetime in UTC."""
    return datetime.fromisoformat(text).astimezone(timezone.utc)


# --- Navigation in time ----------------------------------------------------
# The Graphs tab keeps the period shown as {"length": seconds, "end": ...}:
# its length, and its end as a timestamp, or None while it shows the
# latest data. The buttons set the length; the arrows, a drag or a zoom
# set the end.

def shown(view, now):
    """Returns (start, stop), the period shown, as datetimes in UTC."""
    stop = now if view["end"] is None else parse_timestamp(view["end"])
    return stop - timedelta(seconds=view["length"]), stop


def shown_limits(relayout):
    """The first and last times shown, after a drag or a zoom.

    relayout is what Plotly reports after a change of the view: the new
    limits of the time axes, which move together, in local time, such as
    {"xaxis.range[0]": "2026-10-04 10:12:33", "xaxis.range[1]": ...,
    "xaxis2.range[0]": ..., ...}. Returns None for any other change, such
    as a click in the legend.
    """
    for key in (relayout or {}):
        if key.startswith("xaxis") and key.endswith(".range[0]"):
            axis = key.split(".")[0]
            last = relayout.get(f"{axis}.range[1]")
            if last is not None:
                return [relayout[key], last]
    return None


def view_after_move(limits, now):
    """The period shown after the graphs were dragged or zoomed.

    limits are the first and last times shown, in local time (see
    shown_limits()), such as ["2026-10-04 10:12:33", "2026-10-05 10:12:33"].
    When the graphs end at the present (within 5 minutes), the page
    follows the new data again.
    """
    first, last = sorted(from_local(value) for value in limits)
    end = None if last >= now - timedelta(minutes=5) else to_timestamp(last)
    return {"length": (last - first).total_seconds(), "end": end}


def view_after_step(view, direction, now):
    """The period shown after a click on an arrow: the period before
    (direction -1) or after (+1), of the same length.

    The page follows the new data again when the period reaches the
    present.
    """
    _, stop = shown(view, now)
    stop += direction * timedelta(seconds=view["length"])
    end = None if stop >= now - timedelta(minutes=5) else to_timestamp(stop)
    return {**view, "end": end}


# The shortest and the longest periods that the zoom buttons reach
ZOOM_SHORTEST = timedelta(hours=3)
ZOOM_LONGEST = timedelta(days=2 * 365)


def view_after_zoom(view, factor, now):
    """The period shown after a click on a zoom button: half as long
    (factor 0.5) or twice as long (2), around the same middle, within
    ZOOM_SHORTEST and ZOOM_LONGEST. A phone cannot zoom the graphs with
    two fingers: Plotly only moves them.

    While the page follows the new data, it keeps ending at the present.
    """
    start, stop = shown(view, now)
    length = min(max((stop - start) * factor, ZOOM_SHORTEST), ZOOM_LONGEST)
    if view["end"] is None:
        return {"length": length.total_seconds(), "end": None}
    stop = start + (stop - start) / 2 + length / 2
    end = None if stop >= now - timedelta(minutes=5) else to_timestamp(stop)
    return {"length": length.total_seconds(), "end": end}


def period_of(view):
    """The period button that matches the length shown, or None."""
    length = timedelta(seconds=view["length"])
    matching = [key for key, value in PERIODS.items() if value == length]
    return matching[0] if matching else None


def resolution(length):
    """The points shown for a period of this length (a timedelta).

    Every row up to 2 days, the average of each hour up to 3 months, the
    minimum, average and maximum of each day beyond: the screen shows no
    more detail, and the page stays light, for the server and for a phone.
    """
    if length <= timedelta(days=2):
        return "rows"
    if length <= timedelta(days=92):
        return "hours"
    return "days"


def period_title(view, now):
    """Writes the period shown in the Graphs tab, above the graphs, with
    the day of the week: "jeu. 29 oct., 14:30 → ven. 30 oct., 14:30" up to
    2 days, "mer. 30 sept. 2026 → ven. 30 oct. 2026" beyond. While it
    shows the present, its end is written "maintenant"."""
    start, stop = shown(view, now)
    first, last = to_local(start), to_local(stop)
    form = "%a %d %b, %H:%M" if stop - start <= timedelta(days=2) \
        else "%a %d %b %Y"
    end = "maintenant" if view["end"] is None else french_date(last, form)
    return f"{french_date(first, form)} → {end}"


def span_label(start, stop):
    """Writes a period in local time: "04 oct. 15:30 → 05 oct. 15:30" up
    to 2 days, "05 sept. 2026 → 05 oct. 2026" beyond."""
    first, last = to_local(start), to_local(stop)
    form = "%d %b %H:%M" if stop - start <= timedelta(days=2) \
        else "%d %b %Y"
    return f"{french_date(first, form)} → {french_date(last, form)}"


# --- Health and last measurement -------------------------------------------

def format_age(age):
    """Writes a duration in words: "12 min", "3 h 05 min" or "4 jours"."""
    minutes = int(age.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 48 * 60:
        return f"{minutes // 60} h {minutes % 60:02d} min"
    return f"{minutes // (24 * 60)} jours"


def health(last, now):
    """Returns (stale, status, alert): the health of the station.

    stale tells whether the station is silent; status describes the last
    measurement, shown above the cards; alert is the warning shown at the
    top of the page when the station is silent, empty otherwise.
    """
    if last is None:
        return (True, "Aucune mesure reçue pour l'instant",
                "Aucune mesure reçue pour l'instant : vérifiez la station.")
    measured = parse_timestamp(last["timestamp"])
    age = now - measured
    # The time alone for a measurement of today, with its day otherwise
    local = to_local(measured)
    when = (f"de {local:%H:%M}" if local.date() == to_local(now).date()
            else f"du {french_date(local, '%d %b à %H:%M')}")
    status = f"Mesure {when} · il y a {format_age(age)}"
    if age > STALE_AFTER:
        return (True, status, "Aucune nouvelle mesure depuis "
                f"{format_age(age)} : vérifiez la station.")
    return False, status, ""


# The change shown on the cards: since this long before the last
# measurement
TREND_SPAN = timedelta(hours=3)


def trend(rows, last, column):
    """The change of a quantity over TREND_SPAN: the last value minus the
    one of the last row at least TREND_SPAN older. rows are the rows of
    the last day, oldest first. Returns None without such a row, or
    without value."""
    limit = to_timestamp(parse_timestamp(last["timestamp"]) - TREND_SPAN)
    older = [row for row in rows if row["timestamp"] <= limit]
    if not older or older[-1][column] is None or last[column] is None:
        return None
    return last[column] - older[-1][column]


def day_extremes(rows, day, column):
    """The minimum and maximum of a quantity on a local day ("2026-10-05"),
    each with the local time of its row: ((value, "04:45"), (value,
    "14:00")). Returns None when the day has no value."""
    values = [(row[column], row["local_time"][11:16]) for row in rows
              if row["local_time"].startswith(day)
              and row[column] is not None]
    if not values:
        return None
    return (min(values, key=lambda pair: pair[0]),
            max(values, key=lambda pair: pair[0]))


# The change of the pressure over 3 hours, from the scale used by weather
# services (the UK Met Office): below 0.1 hPa, the pressure is steady;
# then, up to each limit, in hPa, the word of the change
PRESSURE_STEADY = 0.1
PRESSURE_CHANGES = [(1.5, "légère "), (3.5, ""), (6.0, "forte "),
                    (None, "très forte ")]

# The pressure at sea level is 1013 hPa on average: below the first
# limit, in hPa, it is said low, above the second, high
PRESSURE_LOW = 1006
PRESSURE_HIGH = 1020


def pressure_state(pressure, change):
    """What the Pressure tile tells: the level of the pressure at sea
    level and its change over 3 hours (see PRESSURE_CHANGES), such as
    "Pression haute · en légère hausse"; without change, the level
    only. "" without pressure."""
    if pressure is None:
        return ""
    level = ("basse" if pressure < PRESSURE_LOW
             else "haute" if pressure > PRESSURE_HIGH else "moyenne")
    text = f"Pression {level}"
    if change is None:
        return text
    size = round(abs(change), 1)
    if size < PRESSURE_STEADY:
        return f"{text} · stable"
    for limit, word in PRESSURE_CHANGES:
        if limit is None or size <= limit:
            way = "hausse" if change > 0 else "baisse"
            return f"{text} · en {word}{way}"


def humidity_state(last):
    """What the Humidity tile tells: the dew point, then how the air
    feels with it (see dew_comfort()), such as "Point de rosée 17,0 °C ·
    un peu lourd". Below the first limit of DEW_COMFORT, no word: "air
    sec" next to a humidity of 90 % on a cold day reads as a mistake,
    although the cold air holds little water. "" without dew point."""
    dew = last["dew_point_c"]
    if dew is None:
        return ""
    text = f"Point de rosée {number(dew)} °C"
    if dew < DEW_COMFORT[0][0]:
        return text
    return f"{text} · {dew_comfort(dew)}"


# When the temperature is this close to the dew point, the air is nearly
# saturated: water condenses on cold surfaces (dew, or frost below 0 °C),
# or in the air (fog)
DEW_SPREAD_C = 2.0


# A fall of the pressure larger than this in 3 hours, in hPa, often
# brings rain (see PRESSURE_CHANGES)
RAIN_PRESSURE_DROP = 3.5

# Below this deficit all day long, in kPa, plants lose little water; above
# the second one, the soil dries fast
WATERING_LOW_VPD = 0.6
WATERING_HIGH_VPD = 1.2


# The good moments to water: in the morning, until 3 hours after sunrise,
# and in the evening, from 2 hours before sunset. In the heat of the day,
# the water evaporates before it reaches the roots
WATERING_MORNING = timedelta(hours=3)
WATERING_EVENING = timedelta(hours=2)


def watering_moment(local_now, sun):
    """When to water, for the watering advice: (word, sentence), such as
    ("ce soir", "Attendez 16:30 : ..."). sun is (sunrise, sunset) of
    today in local time, or None: then the advice gives no hour."""
    if sun is None:
        return "", "Arrosez le soir ou tôt le matin."
    sunrise, sunset = sun
    morning_end = sunrise + WATERING_MORNING
    evening_start = sunset - WATERING_EVENING
    if local_now < morning_end:
        return " ce matin", (f"Arrosez avant {morning_end:%H:%M}, tant "
                             "que le soleil chauffe peu.")
    if local_now < evening_start:
        return " ce soir", (f"Attendez {evening_start:%H:%M} : en pleine "
                            "journée, l'eau s'évapore avant d'atteindre "
                            "les racines.")
    return " ce soir", "C'est le bon moment, le soleil chauffe peu."


def watering_advice(rows, changes, local_now=None, sun=None):
    """The advice about watering, from the highest vapour pressure deficit
    of the last day (rows): how much water the plants and the soil lost,
    then the good moment to water, from the hour (local_now) and the sun
    (see watering_moment()). The station does not measure the soil nor
    the rain: the advice tells when watering is useful, if the soil is
    dry. Returns (headline, detail), or None without values."""
    deficits = [row["vpd_kpa"] for row in rows if row["vpd_kpa"] is not None]
    if not deficits:
        return None
    highest = max(deficits)
    if highest < WATERING_LOW_VPD:
        return ("Pas nécessaire", "L'air est resté humide, les plantes "
                "ont perdu peu d'eau. Évitez de mouiller les feuilles : "
                "l'humidité favorise les maladies.")
    moment, when = watering_moment(local_now, sun)
    if highest < WATERING_HIGH_VPD:
        headline = "À vérifier" + moment
        detail = ("Évaporation moyenne sur la journée : touchez la terre, "
                  "et arrosez si elle est sèche sur 2 à 3 cm. ")
    else:
        headline = "Conseillé" + moment
        detail = (f"Air très asséchant (jusqu'à {number(highest, 2)} kPa) : "
                  "le sol sèche vite. Si la terre est sèche, arrosez au "
                  "pied des plantes. ")
    detail += when
    pressure = changes.get("sea_level_hpa")
    if pressure is not None and pressure < -RAIN_PRESSURE_DROP:
        detail += " La pression baisse vite : la pluie pourrait arroser "\
                  "à votre place."
    return headline, detail


# How fast the air dries laundry, from its vapour pressure deficit, in
# kPa: slowly from the first limit, fast from the second
DRYING_SLOW_KPA = 0.4
DRYING_FAST_KPA = 1.0

# The laundry dries badly in the morning, while the dew of the night is
# still there, and at the end of the day, when the air cools and its
# humidity rises before sunset
LAUNDRY_MORNING = timedelta(hours=2)
LAUNDRY_EVENING = timedelta(hours=1)


def laundry_advice(last, changes, local_now=None, sun=None):
    """The advice about drying laundry outside: the rain that a fast fall
    of the pressure announces, the night, the dew, then the vapour
    pressure deficit of the last measurement, and the hour to hang it out
    or bring it in. local_now is the local time, sun (sunrise, sunset) of
    today in local time, or None: then the advice gives no hour. The wind
    and the sun, which also dry laundry, are not measured. Returns
    (headline, detail), or None without values."""
    pressure = changes.get("sea_level_hpa")
    if pressure is not None and pressure < -RAIN_PRESSURE_DROP:
        return ("À rentrer", "La pression baisse vite, la pluie est "
                "probable.")
    if sun is not None:
        sunrise, sunset = sun
        # The next morning: today before sunrise, tomorrow after sunset
        # (the sunrise of tomorrow is within a few minutes of today's)
        hang_out = sunrise + LAUNDRY_MORNING
        if local_now < sunrise or local_now >= sunset:
            day = "demain" if local_now >= sunset else "ce matin"
            return ("Pas de séchage la nuit", "L'air fraîchit et "
                    "l'humidité monte : un linge resté dehors se mouille. "
                    f"Étendez-le {day} vers {hang_out:%H:%M}.")
        if local_now >= sunset - LAUNDRY_EVENING:
            return ("À rentrer", f"Le soleil se couche à {sunset:%H:%M} : "
                    "l'air fraîchit et l'humidité remonte.")
    temperature, dew = last["temperature_c"], last["dew_point_c"]
    if temperature is not None and dew is not None \
            and temperature - dew <= DEW_SPREAD_C:
        return ("À rentrer", "L'air est saturé : le linge ne sèche plus, "
                "et la rosée va le mouiller.")
    deficit = last["vpd_kpa"]
    if deficit is None:
        return None
    if deficit >= DRYING_FAST_KPA:
        headline, detail = "Bon séchage", "Le linge sèche vite."
    elif deficit >= DRYING_SLOW_KPA:
        headline, detail = ("Séchage lent", "Il sèchera mieux avec du "
                            "vent ou du soleil.")
    else:
        return ("Pas de séchage", "L'air est trop humide, le linge ne "
                "sèchera presque pas dehors.")
    if sun is not None:
        if local_now < hang_out:
            detail += (" La rosée du matin s'évapore d'abord : il "
                       f"séchera mieux après {hang_out:%H:%M}.")
        else:
            bring_in = sunset - LAUNDRY_EVENING
            detail += f" Rentrez-le avant {bring_in:%H:%M}."
    return headline, detail


# The words of a forecast of the barometer that announce rain
RAIN_TERMS = ("pluie", "averse", "tempête")


def rain_expected(last, changes):
    """How likely rain is in the next hours: "probable" when the pressure
    falls fast or the forecast of the barometer announces rain, showers or
    storm; "possible" when it says they are possible; None otherwise."""
    pressure = changes.get("sea_level_hpa")
    if pressure is not None and pressure < -RAIN_PRESSURE_DROP:
        return "probable"
    forecast_number = weather.zambretti(last["sea_level_hpa"], pressure)
    if forecast_number is None:
        return None
    text = ZAMBRETTI_FORECASTS[forecast_number - 1][0].lower()
    if not any(word in text for word in RAIN_TERMS):
        return None
    return "possible" if "possible" in text else "probable"


def is_day(local_now, sun):
    """Whether the sun is up; without the sun (sun is None), from 8:00 to
    18:00."""
    if sun is None:
        return 8 <= local_now.hour < 18
    return sun[0] <= local_now < sun[1]


# What to wear outside: the clothes for a temperature below each limit,
# in °C, as (limit, clothes, why), why telling what the temperature
# feels like, after it. The station does not measure the wind, which
# makes the cold feel stronger: a windy day needs one layer more
CLOTHES = [
    (0, "Manteau, bonnet et gants",
     "il gèle : couvrez la tête, les mains et le cou."),
    (8, "Manteau et écharpe", "il fait froid : couvrez-vous bien."),
    (14, "Veste ou pull épais", "c'est frais."),
    (19, "Pull léger ou veste légère", "c'est doux."),
    (25, "Tee-shirt", "il fait bon."),
    (None, "Tenue légère et claire", "il fait chaud : buvez souvent."),
]
# Above this temperature, in °C, a cap protects from the sun
CAP_C = 22


def rain_note(rain, item):
    """The sentence about the rain expected (see rain_expected()) and
    the item that keeps dry, or None when no rain is expected."""
    if rain == "probable":
        return f"{item.capitalize()} : la pluie est probable."
    if rain == "possible":
        return f"{item.capitalize()} au cas où : des averses sont possibles."
    return None


def clothes_advice(last, changes, local_now, sun):
    """What to wear outside, from the temperature felt (the heat index in
    the heat, the air otherwise): (clothes, notes), the notes being the
    sentences that tell why: what the temperature feels like, a cap in
    the sun of a warm day, an umbrella when rain is likely or possible
    (see rain_expected()). None without temperature."""
    temperature, felt = last["feels_like_c"], " ressentis"
    if temperature is None:
        temperature, felt = last["temperature_c"], ""
    if temperature is None:
        return None
    for limit, clothes, why in CLOTHES:
        if limit is None or temperature < limit:
            break
    notes = [f"{number(temperature, 0)} °C{felt}, {why}"]
    if temperature >= CAP_C and is_day(local_now, sun):
        notes.append("Une casquette au soleil.")
    notes.append(rain_note(rain_expected(last, changes), "un parapluie"))
    return clothes, [note for note in notes if note is not None]


# What to wear for running, for the temperature of the air below each
# limit, in °C, with what it means for a runner. The body warms up with
# the effort, but not at once: at the start, the air feels as cold as for
# anyone. The runner wears about one layer less than to go out (our
# estimate, as the limits)
RUNNING_CLOTHES = [
    (0, "Collant, veste, bonnet et gants",
     "il gèle : couvrez la tête et les mains, même en courant."),
    (5, "Collant, manches longues et gants",
     "il fait froid : on se réchauffe vite, mais pas tout de suite."),
    (10, "Collant et manches longues",
     "c'est frais : une couche de moins que pour sortir."),
    (15, "Short ou collant, manches longues",
     "on se réchauffe vite : une couche légère suffit."),
    (22, "Short et tee-shirt", "pas besoin de se couvrir pour courir."),
    (None, "Short et débardeur", "le plus léger possible, et de l'eau."),
]
# Above this temperature felt, in °C, running is hard on the heart: the
# body cools badly
RUNNING_HOT_C = 30


def running_advice(last, changes, local_now, sun):
    """What to wear for running (see RUNNING_CLOTHES): (clothes, notes),
    the notes being the sentences that tell why: what the temperature
    means for a runner, the heat, a light at night, a rain jacket when
    rain is likely or possible. None without temperature."""
    temperature = last["temperature_c"]
    if temperature is None:
        return None
    feels = last["feels_like_c"]
    if feels is not None and feels >= RUNNING_HOT_C:
        return ("Trop chaud", [f"On ressent {number(feels, 0)} °C : le "
                               "corps se refroidit mal. Courez tôt le "
                               "matin, et buvez."])
    for limit, clothes, why in RUNNING_CLOTHES:
        if limit is None or temperature < limit:
            break
    # The temperature is already given to go out: the sentence alone
    notes = [why[0].upper() + why[1:]]
    if not is_day(local_now, sun):
        notes.append("Il fait nuit : une lampe frontale ou un gilet "
                     "réfléchissant.")
    notes.append(rain_note(rain_expected(last, changes),
                           "une veste coupe-pluie"))
    return clothes, [note for note in notes if note is not None]


def outfit_tile(clothes, running):
    """The Clothes tile of the Advice tab: one part to go out (clothes,
    see clothes_advice()), one to run (running, see running_advice()),
    split by a thin line, each with its name on the left, the clothes in
    bold and their notes below. Nothing without clothes."""
    if clothes is None:
        return []
    rows = [("Sortir", clothes)] + (
        [("Courir", running)] if running is not None else [])
    return [html.Div(className="tile", children=[
        html.Div("Tenue", className="tile-name"),
        *[html.Div(className="outfit-row", children=[
            html.Div(name, className="outfit-name"),
            html.Div([html.Div(what, className="outfit-headline"),
                      *[html.Div(note, className="tile-line")
                        for note in notes]]),
        ]) for name, (what, notes) in rows],
    ])]


def trend_text(change, unit):
    """Writes a change: "↑ +1,2 °C en 3 h", "↓ -0,4 hPa en 3 h", or
    "→ stable en 3 h" when it rounds to 0."""
    if change is None:
        return ""
    hours = int(TREND_SPAN.total_seconds() // 3600)
    if round(change, 1) == 0:
        return f"→ stable en {hours} h"
    arrow = "↑" if change > 0 else "↓"
    return f"{arrow} {number(change, sign=True)} {unit} en {hours} h"


def sparkline(rows, column, color):
    """A small curve of the last day, without axes, as an SVG image: a
    text that describes the line, which the browser draws at any size and
    any zoom, like a letter. Returns the image as a "data:" address, the
    text itself, which <img> shows without any file; None with fewer than
    two values.

    The curve is drawn in a box of 300 × 60 that the page stretches to
    its width (preserveAspectRatio="none"); its line keeps its width
    (vector-effect). A missing value cuts the line in pieces.
    """
    points = [(datetime.fromisoformat(row["local_time"]), row[column])
              for row in rows]
    values = [value for _, value in points if value is not None]
    if len(values) < 2:
        return None
    first, last = points[0][0], points[-1][0]
    span = (last - first).total_seconds() or 1
    low, high = min(values), max(values)
    height = (high - low) or 1
    pieces, piece = [], []
    for moment, value in points:
        if value is None:
            pieces.append(piece)
            piece = []
            continue
        x = 300 * (moment - first).total_seconds() / span
        y = 56 - 52 * (value - low) / height
        piece.append(f"{x:.1f},{y:.1f}")
    pieces.append(piece)
    lines = "".join(
        f'<polyline points="{" ".join(piece)}" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linejoin="round" '
        'vector-effect="non-scaling-stroke"/>'
        for piece in pieces if len(piece) > 1)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 60" '
           f'preserveAspectRatio="none">{lines}</svg>')
    return "data:image/svg+xml;utf8," + quote(svg)


def extremes_text(rows, day, column):
    """The minimum and maximum of the local day, such as "min 7,0 à 02:30
    · max 18,4 à 11:45", or "" without values."""
    extremes = day_extremes(rows, day, column)
    if extremes is None:
        return ""
    (low, low_time), (high, high_time) = extremes
    return (f"min {number(low)} à {low_time} · "
            f"max {number(high)} à {high_time}")


def extremes_short(rows, day, column):
    """The minimum and maximum of the local day, in short, such as
    "min 7,0° · max 18,4°", or "" without values. Arrows would read as
    the change of the temperature, written above with them."""
    extremes = day_extremes(rows, day, column)
    if extremes is None:
        return ""
    (low, _), (high, _) = extremes
    return f"min {number(low)}° · max {number(high)}°"


def curve(rows, column, color):
    """The small curve of a quantity, as an image, or nothing."""
    image = sparkline(rows, column, color)
    return [] if image is None else [html.Img(src=image, alt="",
                                              className="sparkline")]


def feels_text(last):
    """The feels-like temperature, such as "Ressenti 31 °C", when it
    differs from the temperature by 1 °C or more, or ""."""
    feels, temperature = last["feels_like_c"], last["temperature_c"]
    if feels is None or temperature is None or abs(feels - temperature) < 1:
        return ""
    return f"Ressenti {number(feels, 0)} °C"


def forecast_block(forecast):
    """The forecast at the bottom of the top card: the icon of its sky,
    the part of the day it covers, its text and its details (see
    forecast()), or nothing."""
    if forecast is None:
        return []
    title, text, sky_icon, details = forecast
    return [html.Div(className="hero-forecast", children=[
        # A coloured icon, an image of its own (not a stencil painted
        # with the color of the text, as the other icons)
        html.Img(src=f"/dashboard/assets/icons/sky-{sky_icon}.svg",
                 alt="", className="forecast-icon"),
        html.Div([html.Div(title, className="forecast-title"),
                  html.Div(text, className="forecast-text"),
                  *[html.Div(line, className="forecast-line")
                    for line in details]]),
    ])]


def sun_marks(sun):
    """The sunrise and the sunset (sun, see sun_events()), each as its
    icon and its time."""
    return [html.Span(className="sun-event", title=title, children=[
        icon(kind), f"{moment:%H:%M}"])
        for kind, title, moment in sun]


def hero(last, rows, day, forecast=None, yesterday="", sun=()):
    """The top of the Now tab, the summary, laid out as the tiles: the
    temperature in large, with its change and the comparison with
    yesterday (yesterday, see yesterday_text()) on its right, the
    feels-like temperature when it differs, its curve, then the extremes
    of the day and the sunrise and sunset (sun, see sun_events()) on one
    line, then the forecast of the barometer (see forecast())."""
    if last is None:
        return []
    column, _, unit, color = QUANTITIES[0]
    value = "–" if last[column] is None else number(last[column])
    return [
        html.Div(className="hero-row", children=[
            html.Div(className="hero-value", children=[
                value, html.Span(f" {unit}", className="hero-unit")]),
            html.Div(className="hero-changes", children=[
                html.Div(trend_text(trend(rows, last, column), unit)),
                html.Div(yesterday, className="muted"),
            ]),
        ]),
        html.Div(feels_text(last), className="hero-line"),
        *curve(rows, column, color),
        html.Div(className="hero-row hero-day", children=[
            html.Div(extremes_short(rows, day, column)),
            html.Div(sun_marks(sun), className="sun-events"),
        ]),
        *forecast_block(forecast),
    ]


# Shorter names for the tiles, which are narrow on a phone
TILE_NAMES = {"sea_level_hpa": "Pression (mer)"}


def meaning_text(last, column, change):
    """What a tile of the Now tab tells about the present, below its
    curve: how the air feels for the humidity (see humidity_state()), the
    level and the change of the pressure (see pressure_state()), or ""."""
    if column == "humidity_pct":
        return humidity_state(last)
    if column == "sea_level_hpa":
        return pressure_state(last[column], change)
    return ""


def tiles(last, rows, day, changes):
    """The tiles of the Now tab, below the top: one per other quantity,
    all alike, with its value, its change, its curve, what it means and
    its extremes."""
    if last is None:
        return []
    result = []
    for column, name, unit, color in QUANTITIES[1:]:
        value = "–" if last[column] is None else number(last[column])
        result.append(html.Div(className="tile", children=[
            html.Div(TILE_NAMES.get(column, name), className="tile-name"),
            # The value, and its change on the right
            html.Div(className="tile-row", children=[
                html.Div([value, html.Span(f" {unit}",
                                           className="tile-unit")],
                         className="tile-value", style={"color": color}),
                html.Div(trend_text(trend(rows, last, column), unit),
                         className="tile-line"),
            ]),
            *curve(rows, column, color),
            html.Div(meaning_text(last, column, changes.get(column)),
                     className="tile-line"),
            html.Div(extremes_text(rows, day, column),
                     className="tile-line muted"),
        ]))
    return result


def advice_tile(name, pair):
    """A tile of advice: its name, then pair, (headline, detail), the
    detail being a text or a list of texts."""
    headline, detail = pair
    lines = [detail] if isinstance(detail, str) else detail
    return html.Div(className="tile", children=[
        html.Div(name, className="tile-name"),
        html.Div(headline, className="tile-headline"),
        *[html.Div(line, className="tile-line") for line in lines],
    ])


def advice_tiles(clothes, running, pairs):
    """The tiles of the Advice tab: the clothes (see outfit_tile()), then
    one per (name, pair) of pairs whose pair is not None (see
    advice_tile())."""
    return outfit_tile(clothes, running) + [
        advice_tile(name, pair) for name, pair in pairs if pair is not None]


def frost_banner(pair):
    """The frost warning at the top of the Now tab, from (headline,
    detail) (see frost_advice()), or nothing."""
    if pair is None:
        return []
    headline, detail = pair
    return [html.Strong(headline), f" · {detail}"]


# --- Forecast, frost and sun -----------------------------------------------

# The forecasts of the Zambretti method (see weather.zambretti()), in the
# order of their numbers, from 1 to 32, each with the icon of its sky:
# sun, sun and cloud, rain, or storm
ZAMBRETTI_FORECASTS = [
    ("Beau temps stable", "sun"),
    ("Beau temps", "sun"),
    ("Beau, devenant moins stable", "cloud-sun"),
    ("Assez beau, averses plus tard", "cloud-sun"),
    ("Averses, devenant plus instable", "cloud-rain"),
    ("Instable, pluie plus tard", "cloud-rain"),
    ("Pluie par moments, empirant", "cloud-rain"),
    ("Pluie par moments, devenant très instable", "cloud-rain"),
    ("Très instable, pluie", "cloud-rain"),
    ("Beau temps stable", "sun"),
    ("Beau temps", "sun"),
    ("Beau, averses possibles", "cloud-sun"),
    ("Assez beau, averses probables", "cloud-sun"),
    ("Averses et éclaircies", "cloud-rain"),
    ("Variable, un peu de pluie", "cloud-rain"),
    ("Instable, pluie par moments", "cloud-rain"),
    ("Pluie fréquente", "cloud-rain"),
    ("Très instable, pluie", "cloud-rain"),
    ("Tempête, beaucoup de pluie", "cloud-lightning"),
    ("Beau temps stable", "sun"),
    ("Beau temps", "sun"),
    ("Devenant beau", "sun"),
    ("Assez beau, s'améliorant", "cloud-sun"),
    ("Assez beau, averses possibles au début", "cloud-sun"),
    ("Averses au début, s'améliorant", "cloud-sun"),
    ("Variable, s'améliorant", "cloud-sun"),
    ("Plutôt instable, éclaircies plus tard", "cloud-sun"),
    ("Instable, amélioration probable", "cloud-sun"),
    ("Instable, courtes éclaircies", "cloud-rain"),
    ("Très instable, éclaircies par moments", "cloud-rain"),
    ("Tempête, amélioration possible", "cloud-lightning"),
    ("Tempête, beaucoup de pluie", "cloud-lightning"),
]

# The part of the day that the forecast covers, named from the local hour
# when the page is read: the method looks about 12 hours ahead, so in
# the evening it reaches the next morning, not the whole next day. Up
# to each hour (excluded), the name
FORECAST_TITLES = [(6, "Ce matin"), (12, "Cet après-midi"),
                   (18, "Ce soir et cette nuit"), (24, "Demain matin")]

# The words of the rain line, from rain_expected()
RAIN_WORDS = {None: "Pluie peu probable", "possible": "Pluie possible",
              "probable": "Pluie probable"}


def dew_outlook(last, local_now):
    """The dew, the frost and the fog to expect. From noon to 6:00, the
    end of the night, the coldest time, just before the morning: on a
    clear and calm night, the air seldom cools much below its dew point,
    where its water condenses; such as "D'ici là : vers 6 °C au plus
    bas, rosée ou brouillard possibles par ciel clair". In the
    morning, a warning only when the air is nearly saturated (see
    DEW_SPREAD_C).
    "" otherwise, or without values."""
    temperature, dew = last["temperature_c"], last["dew_point_c"]
    if temperature is None or dew is None:
        return ""
    near = temperature - dew <= DEW_SPREAD_C
    if 6 <= local_now.hour < 12:
        water = "givre" if temperature <= 0 else "rosée"
        return f"{water.capitalize()} ou brouillard probables" if near \
            else ""
    water = "givre" if dew <= 0 else "rosée"
    chance = "probables" if near else "possibles par ciel clair"
    # Under "Ce soir et cette nuit", the night itself; under "Demain
    # matin" or "Ce matin", the time until then (see FORECAST_TITLES)
    when = "Cette nuit" if 12 <= local_now.hour < 18 else "D'ici là"
    return (f"{when} : vers {number(dew, 0)} °C au plus bas, "
            f"{water} ou brouillard {chance}")


def forecast(last, changes, local_now):
    """The forecast of the barometer: (title, text, sky, details), such
    as ("Cet après-midi", "Beau temps stable", "sun", ["Pluie peu
    probable"]): the title named from the local hour local_now (see
    FORECAST_TITLES), the sky the name of its icon, the details the rain
    (see rain_expected()) when the text itself does not speak of it, then
    the dew and the fog (see dew_outlook()).
    None when the pressure or its trend is missing."""
    forecast_number = weather.zambretti(last["sea_level_hpa"],
                                        changes.get("sea_level_hpa"))
    if forecast_number is None:
        return None
    title = next(name for hour, name in FORECAST_TITLES
                 if local_now.hour < hour)
    text, sky_icon = ZAMBRETTI_FORECASTS[forecast_number - 1]
    details = []
    if not any(word in text.lower() for word in RAIN_TERMS):
        details.append(RAIN_WORDS[rain_expected(last, changes)])
    dew = dew_outlook(last, local_now)
    if dew:
        details.append(dew)
    return title, text, sky_icon, details


def yesterday_text(last, yesterday):
    """The temperature now against yesterday at the same time, such as
    "+2,1 °C vs hier", or "" without a row of yesterday."""
    if yesterday is None or last["temperature_c"] is None \
            or yesterday["temperature_c"] is None:
        return ""
    change = last["temperature_c"] - yesterday["temperature_c"]
    if round(change, 1) == 0:
        return "comme hier"
    return f"{number(change, sign=True)} °C vs hier"


# Frost: the ground, and the plants on it, cool down below the air
# measured at the height of the shelter. On a clear and calm night, the
# temperature goes down towards the dew point, where the water of the air
# condenses and gives back heat. Frost is possible at night when the air
# is already cool and its dew point is near 0 °C, or when the air itself
# is close to 0 °C
FROST_AIR_C = 3.0
FROST_DEW_C = 1.0
FROST_COOL_AIR_C = 6.0
# The hours of the evening and the night, in local time
NIGHT_START = 16
NIGHT_END = 9


def frost_advice(last, local_now):
    """The frost tile: (headline, detail) when it freezes, or when frost
    is possible in the night, None otherwise."""
    temperature, dew = last["temperature_c"], last["dew_point_c"]
    if temperature is None:
        return None
    if temperature <= 0:
        return ("Il gèle", "Protégez les plantes sensibles et les "
                "conduites d'eau exposées.")
    night = local_now.hour >= NIGHT_START or local_now.hour < NIGHT_END
    dry_and_cool = (dew is not None and dew <= FROST_DEW_C
                    and temperature <= FROST_COOL_AIR_C)
    if night and (temperature <= FROST_AIR_C or dry_and_cool):
        return ("Gelée possible", "Par nuit claire et calme, le sol et "
                "les plantes peuvent geler avant l'air. Protégez les "
                "plantes sensibles.")
    return None


def sun_today(location, now):
    """The sunrise and the sunset of today, in local time, or None without
    location, or when the sun does not rise or set."""
    if location is None:
        return None
    times = sky.sun_times(to_local(now).date(), *location)
    if times is None:
        return None
    return tuple(to_local(moment) for moment in times)


def sun_events(location, now):
    """The sunrise and the sunset to show, in the order of time, each as
    (icon, name, local time): those of today, or after the sunset, the
    sunset of today and the sunrise of tomorrow. Empty without location,
    or when the sun does not rise or set."""
    today = sun_today(location, now)
    if today is None:
        return []
    sunrise, sunset = today
    tomorrow = sunrise_tomorrow(location, now)
    if tomorrow is not None:
        return [("sunset", "Coucher du soleil", sunset),
                ("sunrise", "Lever du soleil demain", tomorrow)]
    return [("sunrise", "Lever du soleil", sunrise),
            ("sunset", "Coucher du soleil", sunset)]


def sunrise_tomorrow(location, now):
    """In the evening, after the sunset of today, the sunrise of
    tomorrow, in local time; None before, or without location."""
    today = sun_today(location, now)
    local_now = to_local(now)
    if today is None or local_now < today[1]:
        return None
    times = sky.sun_times(local_now.date() + timedelta(days=1), *location)
    return None if times is None else to_local(times[0])


# --- Graphs ----------------------------------------------------------------

def _transparent(color, alpha):
    # "#e4572e" -> "rgba(228,87,46,0.2)", for the band of the daily values
    red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({red},{green},{blue},{alpha})"


# The dark template of Plotly, its set of colors, fonts and grids, read
# once as a dictionary; the background of the cards (--card in style.css),
# and the color of the dotted lines at midnight
TEMPLATE = pio.templates["plotly_dark"].to_plotly_json()
CARD = "#1f242c"
MIDNIGHT = "rgba(255,255,255,0.3)"
# The lines of the values, faint: they help reading without being seen
GRID = "rgba(255,255,255,0.08)"

# Where each graph sits in the figure, from the bottom (0) to the top (1):
# the temperature at the top, the pressure at the bottom
DOMAINS = [[0.72, 1.0], [0.36, 0.64], [0.0, 0.28]]


def midnights(first, last):
    """Returns the local midnights between two local times, in order."""
    day = first.replace(hour=0, minute=0, second=0, microsecond=0)
    result = []
    while day <= last:
        if day >= first:
            result.append(day)
        day += timedelta(days=1)
    return result


def read_values(connection, first, last, points):
    """Reads the points from first to last (datetimes in UTC): "rows",
    "hours" or "days" (see resolution())."""
    bounds = (to_timestamp(first), to_timestamp(last))
    if points == "days":
        return database.daily_summary(connection, *bounds)
    if points == "hours":
        return database.hourly_summary(connection, *bounds)
    return database.rows_between(connection, *bounds)


def moved(values, points, offset):
    """Moves points by offset (a timedelta): the comparison of the Compare
    tab, drawn from the start of the reference."""
    if points == "days":
        days = timedelta(days=round(offset / timedelta(days=1)))
        return [{**day, "day": (date.fromisoformat(day["day"]) + days)
                 .isoformat()} for day in values]
    return [{**row, "local_time": (datetime.fromisoformat(row["local_time"])
                                   + offset).strftime(PLOTLY_TIME)}
            for row in values]


def _curves(values, points, quantity, axes, label=None, compared=False):
    """The curves of one quantity, for one period.

    One curve through the rows or hours (values); with days, the average
    of each day, inside the band of its minimum and maximum. In the
    Compare tab, label (the dates of the period) names the curves, in the
    legend of the first graph only, and the curves of the comparison
    (compared) are drawn paler and dashed, without band.
    """
    column, name, unit, color = quantity
    line = {"color": color, "width": 2}
    if compared:
        line = {"color": _transparent(color, COMPARISON_OPACITY),
                "width": 2, "dash": COMPARISON_DASH}
    title = name if label is None else label
    common = {"type": "scatter", "mode": "lines", **axes,
              "hovertemplate": (f"%{{y:.1f}} {unit}<extra>{name}"
                                + ("" if label is None else f", {label}")
                                + "</extra>")}
    if label is None:
        # In the Graphs tab, the title of each graph names its curve: no
        # legend
        common.update(showlegend=False)
    else:
        # The curves of one period, in the three graphs, are shown or
        # hidden together from the legend
        common.update(legendgroup=label, showlegend=axes["xaxis"] == "x")
    if points != "days":
        return [{**common, "name": title, "line": line,
                 "x": [row["local_time"] for row in values],
                 "y": [row[column] for row in values]}]
    x = [day["day"] for day in values]
    curves = []
    if not compared:
        # The minimum first, without a line, then the maximum, filled down
        # to the minimum: the band between them
        curves.append({**common, "x": x, "showlegend": False,
                       "y": [day[f"{column}_min"] for day in values],
                       "line": {"width": 0}, "hoverinfo": "skip"})
        curves.append({**common, "x": x,
                       "y": [day[f"{column}_max"] for day in values],
                       "line": {"width": 0}, "fill": "tonexty",
                       "fillcolor": _transparent(color, 0.2),
                       "name": f"{title} : min – max du jour",
                       "hoverinfo": "skip"})
    curves.append({**common, "x": x, "line": line,
                   "y": [day[f"{column}_avg"] for day in values],
                   "name": f"{title} : moyenne du jour"})
    return curves


def _extra_curve(values, points, extra, axes):
    """The curve of a computed quantity (see EXTRA_CURVES), drawn over the
    curve of its graph, without band."""
    column, name, unit, color, dash, daily = extra
    curve = {"type": "scatter", "mode": "lines", **axes, "name": name,
             "showlegend": False,
             "line": {"color": color, "width": 2, "dash": dash},
             "hovertemplate": f"%{{y:.1f}} {unit}<extra>{name}</extra>"}
    if points == "days":
        return {**curve, "x": [day["day"] for day in values],
                "y": [day[f"{column}_{daily}"] for day in values]}
    return {**curve, "x": [row["local_time"] for row in values],
            "y": [row[column] for row in values]}


def graph_title(quantity, extras, days=False):
    """The title of a graph: the name of its quantity, such as
    "Température (°C)", then, on a second line, in smaller letters, the
    names of the computed quantities drawn with it, in their color:
    "Point de rosée · Ressenti (pointillés, dès 27 °C)". With days (one
    point per day), a line below the name tells how to read the band."""
    _, name, unit, _ = quantity
    title = f"{name} ({unit})"
    if days:
        title += ("<br><span style='font-size:13px'>bande : min – max du "
                  "jour</span>")
    names = []
    for _, extra_name, _, color, dash, _ in extras:
        dotted = " (pointillés, dès 27 °C)" if dash == "dot" else ""
        names.append(f"<span style='color:{color}'>{extra_name}{dotted}"
                     "</span>")
    if names:
        title += ("<br><span style='font-size:13px'>" + " · ".join(names)
                  + "</span>")
    return title


# The scale of each graph: its limits are rounded to these steps, so that
# it only changes when the values cross one of them, not at each move;
# the humidity always goes from 0 to 100 %
# The numbers of a value axis, when one decimal is not right: the steps
# of the voltage are 0.05 V, the current needs no decimal
TICK_FORMATS = {"battery_v": ".2~f", "battery_ma": ".0f"}
SCALE_STEPS = {"temperature_c": 5, "sea_level_hpa": 5, "battery_v": 0.1,
               "battery_ma": 50}
HUMIDITY_SCALE = [0, 100]


def value_range(curves, start, stop, step):
    """The limits of a value axis: the lowest and highest values of
    curves between start and stop (texts in local time, as the "x" of
    the curves), rounded down and up to step. None without value."""
    values = [y for curve in curves
              for x, y in zip(curve["x"], curve["y"])
              if y is not None and start[:len(x)] <= x <= stop[:len(x)]]
    if not values:
        return None
    # Rounded again: 42 * 0.1 is 4.2000000000000002 for the computer
    low = round(math.floor(min(values) / step) * step, 6)
    high = round(math.ceil(max(values) / step) * step, 6)
    return [low, high if high > low else round(low + step, 6)]


def figure(values, points, start, stop, limits=None, label=None,
           comparison=None, quantities=None, domains=None):
    """The graphs, one above the other, sharing the time axis: by default
    the three of the weather (QUANTITIES, placed by DOMAINS); in the
    Station tab, those of the battery (quantities and domains).

    values are the points of the period from start to stop, plus a margin
    on each side, so that the graphs can be dragged before the page loads
    the data around the new position. points tells their kind (see
    resolution()). limits are the first and last times that the graphs
    may show, in local time: Plotly stops a drag or a zoom at them. In
    the Compare tab, label names the reference, and
    comparison holds the label and the values of the comparison, already
    moved over the reference (see build_comparison()).

    The figure is written as a dictionary, in the format that Plotly reads
    in the browser: "data" holds the curves, "layout" the axes, titles and
    colors. The figure objects of Plotly (plotly.graph_objects) would
    check each of the thousands of values, which takes seconds on the
    small computer of the server.
    """
    quantities = QUANTITIES if quantities is None else quantities
    domains = DOMAINS if domains is None else domains
    # Plotly names the axes x, x2, x3 and y, y2, y3
    suffixes = ["" if index == 0 else str(index + 1)
                for index in range(len(quantities))]
    data = []
    layout = {}
    for index, quantity in enumerate(quantities):
        suffix = suffixes[index]
        axes = {"xaxis": "x" + suffix, "yaxis": "y" + suffix}
        data += _curves(values, points, quantity, axes, label)
        if comparison is not None:
            data += _curves(comparison[1], points, quantity, axes,
                            comparison[0], compared=True)
        else:
            # The computed quantities, in the Graphs tab only
            data += [_extra_curve(values, points, extra, axes)
                     for extra in EXTRA_CURVES.get(quantity[0], [])]
        # Each graph has its own value axis, which keeps its scale (only
        # time moves), and a time axis that follows the first one
        # ("matches"); only the time axis of the bottom graph shows dates
        layout["yaxis" + suffix] = {"domain": domains[index],
                                    "anchor": "x" + suffix,
                                    "gridcolor": GRID,
                                    "fixedrange": True,
                                    # "1029,5", without a space between
                                    # thousands; "4,15" for a voltage
                                    "tickformat": TICK_FORMATS.get(
                                        quantity[0], ".1~f")}
        # A scale of round values, from the period shown only, not from
        # the margins (see value_range()); Plotly keeps it while the
        # graphs are dragged
        if quantity[0] == "humidity_pct":
            scale = HUMIDITY_SCALE
        else:
            scale = value_range(
                [curve for curve in data
                 if curve["yaxis"] == "y" + suffix],
                f"{to_local(start):{PLOTLY_TIME}}",
                f"{to_local(stop):{PLOTLY_TIME}}", SCALE_STEPS[quantity[0]])
        if scale is not None:
            layout["yaxis" + suffix]["range"] = scale
        # The time axis has no grid of its own: the dotted lines at
        # midnight tell the days apart
        layout["xaxis" + suffix] = {"anchor": "y" + suffix, "type": "date",
                                    "showgrid": False,
                                    "showticklabels": (
                                        index == len(quantities) - 1),
                                    "tickformatstops": DATE_TICKS,
                                    "hoverformat": (
                                        "%A %d %B %Y" if points == "days"
                                        else "%A %d %B %Y, %H:%M")}
        if index > 0:
            layout["xaxis" + suffix]["matches"] = "x"

    layout["xaxis"]["range"] = [f"{to_local(start):{PLOTLY_TIME}}",
                                f"{to_local(stop):{PLOTLY_TIME}}"]
    # The graphs cannot be dragged nor zoomed out beyond the data: the
    # limits are given to the three time axes, which move together
    if limits is not None:
        for suffix in suffixes:
            layout["xaxis" + suffix].update(minallowed=limits[0],
                                            maxallowed=limits[1])
    if stop - start <= timedelta(days=31):
        # A dotted line at each midnight, across the three graphs, to tell
        # the days apart
        margin = stop - start
        line = {"color": MIDNIGHT, "width": 1, "dash": "dot"}
        layout["shapes"] = [
            {"type": "line", "x0": f"{midnight:{PLOTLY_TIME}}",
             "x1": f"{midnight:{PLOTLY_TIME}}", "xref": "x",
             "y0": 0, "y1": 1, "yref": "paper", "line": line}
            for midnight in midnights(to_local(start - margin),
                                      to_local(stop + margin))]

    # The title of each graph, above it
    layout["annotations"] = [
        {"text": graph_title(quantity, [] if comparison is not None
                             else EXTRA_CURVES.get(quantity[0], []),
                             points == "days" and comparison is None),
         "x": 0.5, "xref": "paper",
         "y": domains[index][1], "yref": "paper", "yanchor": "bottom",
         "showarrow": False, "font": {"size": 16}}
        for index, quantity in enumerate(quantities)]
    layout.update(
        template=TEMPLATE,
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        # Dragging the graphs moves them in time, instead of zooming
        dragmode="pan",
        # Room at the top for the title of the temperature graph, on two
        # lines in the Graphs tab (three with one point per day, see
        # graph_title()); at the bottom, for the dates, and for the legend
        # of the Compare tab
        margin={"l": 60, "r": 20,
                "t": 40 if comparison is not None
                else 80 if points == "days" else 60,
                "b": 50 if label is None else 90},
        hovermode="x unified",
        # Numbers in French: a decimal comma, a space between thousands
        separators=", ",
        # The legend at the bottom of the figure ("container"), below the
        # dates of the time axis
        legend={"orientation": "h", "x": 0, "y": 0, "yref": "container",
                "yanchor": "bottom"},
        font={"family": "system-ui, sans-serif"})
    return {"data": data, "layout": layout}


def build_graphs(connection, view, now):
    """Computes the graphs of the Courbes and Station tabs, for the period
    shown (view, see shown()): "title" (the period shown, see
    period_title()), "figure" (the graphs of the weather) and
    "battery_figure" (those of the battery). A drag of the graphs only
    computes these, not the rest of the page."""
    start, stop = shown(view, now)
    # The period shown, and as much again on each side to drag into
    length = stop - start
    points = resolution(length)
    values = read_values(connection, start - length, stop + length, points)
    oldest = database.first_local_time(connection)
    limits = None
    if oldest is not None:
        # A period that ends now is shown whole, even if it starts before
        # the data, such as a year of a young station: the time before
        # the data stays empty. Once dragged, the graphs stop at the data
        first = oldest
        if view["end"] is None:
            first = min(oldest, f"{to_local(start):{PLOTLY_TIME}}")
        limits = (first, f"{to_local(now):{PLOTLY_TIME}}")
    return {"title": period_title(view, now),
            "figure": figure(values, points, start, stop, limits),
            "battery_figure": figure(values, points, start, stop, limits,
                                     quantities=BATTERY_QUANTITIES,
                                     domains=BATTERY_DOMAINS)}


def build_now(connection, now, location=None, log_text=""):
    """Computes the Now and Advice tabs. Returns a dictionary: "stale",
    "status" and "alert" (the health of the station, see health()),
    "date" (today, in words), "frost", "hero" and "tiles" (the Now tab,
    see frost_banner(), hero() and tiles(); location is (latitude,
    longitude) of the station, for the sun, or None), "advice" (the
    Advice tab, see advice_tiles()) and "station" (the warning about the
    station on the Now tab, from the end of its log, log_text, see
    station_banner())."""
    last = database.last_row(connection)
    stale, status, alert = health(last, now)
    # The rows of the last day, for the cards
    day_rows = database.rows_between(
        connection, to_timestamp(now - timedelta(days=1)),
        to_timestamp(now + timedelta(minutes=1)))
    local_now = to_local(now)
    changes = {}
    if last is not None:
        changes = {column: trend(day_rows, last, column)
                   for column, _, _, _ in QUANTITIES}
    day = f"{local_now:%Y-%m-%d}"
    prediction, yesterday, frost, advice = None, "", None, []
    if last is not None:
        prediction = forecast(last, changes, local_now)
        yesterday = yesterday_text(
            last, database.row_near(connection, to_timestamp(
                parse_timestamp(last["timestamp"]) - timedelta(days=1))))
        frost = frost_advice(last, local_now)
        sun = sun_today(location, now)
        advice = advice_tiles(
            clothes_advice(last, changes, local_now, sun),
            running_advice(last, changes, local_now, sun),
            [("Linge", laundry_advice(last, changes, local_now, sun)),
             ("Arrosage", watering_advice(day_rows, changes, local_now,
                                          sun))])
    return {"stale": stale, "status": status, "alert": alert,
            "date": french_date(local_now, "%A %d %B").capitalize(),
            "frost": frost_banner(frost),
            "hero": hero(last, day_rows, day, prediction, yesterday,
                         sun_events(location, now)),
            "tiles": tiles(last, day_rows, day, changes),
            "advice": advice,
            "station": station_banner(
                last, log_problems(log_text, now - LOG_RECENT))}


def build_view(connection, view, now, location=None, log_text=""):
    """Everything the page shows: build_now() and build_graphs() together,
    in one dictionary, as the tests read it."""
    return {**build_now(connection, now, location, log_text),
            **build_graphs(connection, view, now)}


# --- Station tab -----------------------------------------------------------

# The graphs of the battery, measured by the INA219: column, name, unit,
# color, as QUANTITIES, and their place in the height of the figure
BATTERY_QUANTITIES = [
    ("battery_v", "Tension de la batterie", "V", "#e5a92b"),
    ("battery_ma", "Courant de la batterie", "mA", "#c27ae0"),
]
BATTERY_DOMAINS = [[0.56, 1.0], [0.0, 0.44]]

# The charge of a lithium polymer battery at rest, from its voltage: up to
# each voltage, in V, the charge in %. The usual table of the makers of
# these batteries, an estimate: the voltage also depends on the current,
# on the temperature and on the age of the battery. The station measures
# while it is awake and draws about 50 mA: a little below the voltage at
# rest
LIPO_CHARGE = [(3.27, 0), (3.61, 5), (3.69, 10), (3.71, 15), (3.73, 20),
               (3.75, 25), (3.77, 30), (3.79, 35), (3.80, 40), (3.82, 45),
               (3.84, 50), (3.85, 55), (3.87, 60), (3.91, 65), (3.95, 70),
               (3.98, 75), (4.02, 80), (4.08, 85), (4.11, 90), (4.15, 95),
               (4.20, 100)]

# Below this voltage, in V, the battery is low: about 5 % of its charge
# left (see LIPO_CHARGE), our limit for a warning on the Now tab
BATTERY_LOW_V = 3.6

# Below this current, in mA, the battery is said neither to charge nor to
# discharge: about the finest step of the INA219
STILL_MA = 0.5

# Without the times of the sun, the night is said to end at this hour
NIGHT_END_HOUR = 7

# The days of the log shown in the Station tab, and the part of the end of
# the log that is read for them: the log grows by about 33 KB a day (600
# KB in 18 days on the server), about 230 KB for 7 days
LOG_DAYS = 7
LOG_TAIL_BYTES = 256 * 1024
# The problems of the last hours are told on the Now tab, from a shorter
# end of the log: the Now tab is the first page opened
LOG_RECENT = timedelta(hours=24)
LOG_RECENT_BYTES = 64 * 1024
# At most this many problems are listed, the newest first: the graphs
# below must still fit on the screen of a computer
LOG_SHOWN = 5

# The reasons of a restart written by the firmware, in French
RESTART_REASONS = {
    "power on": "mise sous tension",
    "reset pin": "bouton reset",
    "restart by the firmware": "redémarrage par le firmware",
    "crash of the firmware": "plantage du firmware",
    "watchdog": "chien de garde",
    "brownout, the voltage fell": "chute de tension",
    "unknown": "raison inconnue",
}


def battery_charge(voltage):
    """The charge of the battery, in %, rounded to 5, from its voltage
    (see LIPO_CHARGE): straight lines between the points of the table."""
    if voltage <= LIPO_CHARGE[0][0]:
        return 0
    for (low_v, low_pct), (high_v, high_pct) in zip(LIPO_CHARGE,
                                                    LIPO_CHARGE[1:]):
        if voltage <= high_v:
            share = (voltage - low_v) / (high_v - low_v)
            return round((low_pct + share * (high_pct - low_pct)) / 5) * 5
    return 100


def current_text(current):
    """What the current of the battery tells, such as "↑ +120 mA : la
    batterie se charge"."""
    if current >= STILL_MA:
        return f"↑ {number(current, 0, sign=True)} mA : la batterie se charge"
    if current <= -STILL_MA:
        return (f"↓ {number(current, 0, sign=True)} mA : la batterie "
                "alimente la station, mesuré pendant son réveil")
    return "→ 0 mA : la batterie ne charge ni ne se décharge"


def night_ends(rows, location, now):
    """The voltage of the battery at the end of the last two nights, the
    newest first: the last row before each sunrise (before NIGHT_END_HOUR
    without location). rows are the rows of the last days, oldest first.
    The end of the night is the lowest point of the battery: it tells
    whether the sun of the day before filled it again."""
    local_now = to_local(now)
    ends = []
    for back in range(3):
        day = local_now.date() - timedelta(days=back)
        times = None if location is None else sky.sun_times(day, *location)
        end = (to_local(times[0]) if times is not None
               else datetime.combine(day, datetime.min.time())
               + timedelta(hours=NIGHT_END_HOUR))
        if end > local_now:
            continue
        before = [row for row in rows
                  if row["battery_v"] is not None
                  and datetime.fromisoformat(row["local_time"]) <= end]
        if before:
            ends.append(before[-1]["battery_v"])
        if len(ends) == 2:
            break
    return ends


def battery_tile(last, rows, location, now):
    """The Battery tile of the Station tab: (headline, lines), such as
    ("4,05 V · environ 85 %", ["↑ +120 mA : la batterie se charge",
    "Fin de nuit : 3,98 V (la veille 3,99 V)"]). rows are the rows of the
    last days, for the ends of the nights (see night_ends())."""
    if last is None or last["battery_v"] is None:
        return ("Pas encore de mesure",
                ["La station n'envoie pas encore la tension de sa "
                 "batterie : l'INA219 n'est pas encore installé."])
    voltage = last["battery_v"]
    lines = []
    if last["battery_ma"] is not None:
        lines.append(current_text(last["battery_ma"]))
    ends = night_ends(rows, location, now)
    if ends:
        text = f"Fin de nuit : {number(ends[0], 2)} V"
        if len(ends) > 1:
            text += f" (la veille {number(ends[1], 2)} V)"
        lines.append(text)
    return (f"{number(voltage, 2)} V · environ {battery_charge(voltage)} %",
            lines)


def problem_text(line):
    """A problem of the log (see logs.problems()), in French when it is a
    known message of the firmware, as it is otherwise."""
    if line.startswith("restart: "):
        reason = line[len("restart: "):]
        return f"Redémarrage : {RESTART_REASONS.get(reason, reason)}"
    if line.endswith(" not responding"):
        return f"{line[:-len(' not responding')]} ne répond pas"
    if line == "Wi-Fi not reachable":
        return "Wi-Fi injoignable"
    if line == "NTP not answering":
        return "L'heure par internet (NTP) ne répond pas"
    return line


def log_problems(log_text, since):
    """The problems of the log since a time (UTC), the newest first, as
    (when, text): when is the local time, such as "14 nov. 03:15", or
    "après 14 nov. 03:15" for an entry written while the clock was not
    set."""
    shown = []
    for moment, clock_set, line in logs.problems(log_text):
        if moment is None or moment < since:
            continue
        when = french_date(to_local(moment), "%d %b %H:%M")
        shown.append((when if clock_set else f"après {when}",
                      problem_text(line)))
    return shown[::-1]


def log_tile(problems):
    """The Log tile of the Station tab, from the problems of the last
    LOG_DAYS days (see log_problems()): (ok, headline, lines), ok telling
    whether there is none."""
    if not problems:
        return (True, f"Aucun problème sur {LOG_DAYS} jours", [])
    count = len(problems)
    headline = (f"{count} problème{'s' if count > 1 else ''} sur "
                f"{LOG_DAYS} jours")
    lines = [f"{when} · {text}" for when, text in problems[:LOG_SHOWN]]
    if count > LOG_SHOWN:
        lines.append(f"… et {count - LOG_SHOWN} de plus dans le journal")
    return False, headline, lines


def station_banner(last, recent_problems):
    """The warning about the station at the top of the Now tab: a low
    battery (see BATTERY_LOW_V), and the problems of the last hours of the
    log; "" when all is well."""
    texts = []
    if last is not None and last["battery_v"] is not None \
            and last["battery_v"] < BATTERY_LOW_V:
        texts.append(f"Batterie faible ({number(last['battery_v'], 2)} V) : "
                     "vérifiez le panneau solaire.")
    if recent_problems:
        count = len(recent_problems)
        texts.append(f"{count} problème{'s' if count > 1 else ''} dans le "
                     "journal depuis 24 h : voir l'onglet Station.")
    return " ".join(texts)


def build_station(connection, log_text, now, location=None):
    """Computes the tiles of the Station tab: "battery" and "log", each
    (headline, lines); "log_ok" tells whether the log shows no problem."""
    last = database.last_row(connection)
    rows = database.rows_between(
        connection, to_timestamp(now - timedelta(days=3)),
        to_timestamp(now + timedelta(minutes=1)))
    log_ok, headline, lines = log_tile(
        log_problems(log_text, now - timedelta(days=LOG_DAYS)))
    return {"battery": battery_tile(last, rows, location, now),
            "log": (headline, lines), "log_ok": log_ok}


# --- Compare tab -----------------------------------------------------------
# The tab keeps the two periods compared as {"unit": "month", "length":
# seconds, "reference": timestamp, "comparison": timestamp, "chosen":
# True}: the unit chosen, the length shown, the start of each period, in
# UTC, and whether they are still the periods chosen in the lists (not
# yet dragged nor zoomed).

def unit_start(unit, day):
    """The first day of the day, week, month or year holding day."""
    if unit == "week":
        return day - timedelta(days=day.weekday())
    if unit == "month":
        return day.replace(day=1)
    if unit == "year":
        return day.replace(month=1, day=1)
    return day


def unit_length(unit, start):
    """The length of the day, week, month or year starting on start."""
    if unit == "week":
        return timedelta(days=7)
    if unit == "month":
        return timedelta(days=calendar.monthrange(start.year,
                                                  start.month)[1])
    if unit == "year":
        return timedelta(days=366 if calendar.isleap(start.year) else 365)
    return timedelta(days=1)


def unit_label(unit, start):
    """Names a period: "lun. 05 oct. 2026", "Semaine 41 · 05 oct. – 11 oct.
    2026", "Octobre 2026" or "2026"."""
    if unit == "week":
        end = start + timedelta(days=6)
        return (f"Semaine {start.isocalendar().week} · "
                f"{french_date(start, '%d %b')} – "
                f"{french_date(end, '%d %b %Y')}")
    if unit == "month":
        return french_date(start, "%B %Y").capitalize()
    if unit == "year":
        return f"{start:%Y}"
    return french_date(start, "%a %d %b %Y")


# The time axis of the Compare tab shows the place in the period, the
# same for both periods, not the dates of the reference: the hour of a
# day, the day of a week or of a month, the month of a year. Its labels,
# and the time shown under the mouse
COMPARE_TICKS = {"day": ("%H:%M", "%H:%M"), "week": ("%a", "%a %H:%M"),
                 "month": ("%d", "le %d à %H:%M"), "year": ("%b", "%d %b")}
# How the first and last measurements of a period are written, when the
# data does not cover it all (when both fall on the same day or month,
# the second text), and the margin allowed at each end
COVERAGE = {
    "day": ("de {} à {}", "à {}", "%H:%M", timedelta(hours=1)),
    "week": ("du {} au {}", "le {}", "%a", timedelta(hours=6)),
    "month": ("du {} au {}", "le {}", "%-d", timedelta(hours=6)),
    "year": ("de {} à {}", "en {}", "%b", timedelta(days=2)),
}


def coverage_text(unit, values, start, length):
    """When the measurements do not cover a period (start, its local
    time, and length), when they were taken, such as "mesures du 28 au
    31"; "" when they cover it, or without any."""
    times = sorted(datetime.fromisoformat(value.get("local_time")
                                          or value["day"])
                   for value in values)
    times = [moment for moment in times if start <= moment < start + length]
    if not times:
        return ""
    text, single, form, margin = COVERAGE[unit]
    if times[0] <= start + margin and times[-1] >= start + length - margin:
        return ""
    first, last = (french_date(moment, form) for moment in (times[0],
                                                           times[-1]))
    if first == last:
        return "mesures " + single.format(first)
    return "mesures " + text.format(first, last)


def part_options(unit):
    """The list of the week or the month: "S1" to "S53", or "janv." to
    "déc." (for a month or a day)."""
    if unit == "week":
        return [{"label": f"S{week}", "value": week}
                for week in range(1, 54)]
    return [{"label": SHORT_MONTHS[month - 1], "value": month}
            for month in range(1, 13)]


def year_options(first, last):
    """The list of years, from the year of the date last back to the year
    of the date first."""
    return [{"label": str(year), "value": year}
            for year in range(last.year, first.year - 1, -1)]


def start_of(unit, year, part=None, day=None):
    """The first day of a period, from the values of the lists: the year,
    the week number or the month (part), and the day of the month.

    A year has 52 or 53 weeks, and a month 28 to 31 days: week 53 of a
    year of 52 weeks is its last week, and February 31 is the last day of
    February.
    """
    if unit == "week":
        weeks = date(year, 12, 28).isocalendar().week
        return date.fromisocalendar(year, min(part, weeks), 1)
    if unit == "month":
        return date(year, part, 1)
    if unit == "day":
        return date(year, part, min(day, calendar.monthrange(year, part)[1]))
    return date(year, 1, 1)


def parts_of(unit, start):
    """The values of the lists for a period starting on start: the year,
    the week number or the month, and the day of the month."""
    if unit == "week":
        week = start.isocalendar()
        return week.year, week.week, None
    return start.year, start.month, start.day


def compare_dates(unit, reference, comparison):
    """The periods compared, from the days chosen in the two calendars
    ("2026-10-14"): each one is the day, week, month or year holding its
    day, from local midnight of its first day, and the graphs show the
    length of the reference."""
    starts = [unit_start(unit, date.fromisoformat(day[:10]))
              for day in (reference, comparison)]
    return {"unit": unit,
            "length": unit_length(unit, starts[0]).total_seconds(),
            "reference": to_timestamp(from_local(starts[0].isoformat())),
            "comparison": to_timestamp(from_local(starts[1].isoformat())),
            "chosen": True}


def compare_after_move(limits, compared):
    """Moves both periods as the graphs were dragged or zoomed.

    limits are the times shown after the move, in local time (see
    shown_limits()). The gap between the reference and the comparison
    stays the same.
    """
    first, last = sorted(from_local(value) for value in limits)
    shift = first - parse_timestamp(compared["reference"])
    return {**compared, "length": (last - first).total_seconds(),
            "chosen": False, "reference": to_timestamp(first),
            "comparison": to_timestamp(
                parse_timestamp(compared["comparison"]) + shift)}


def build_comparison(connection, compared, now):
    """The figure of the Compare tab.

    The time axis is the one of the reference; the comparison is moved
    over it. A drag or a zoom stops when both periods would leave the
    data: as long as one of them shows measurements, the graphs move.
    """
    length = timedelta(seconds=compared["length"])
    reference = parse_timestamp(compared["reference"])
    comparison = parse_timestamp(compared["comparison"])
    offset = reference - comparison
    points = resolution(length)
    values = read_values(connection, reference - length,
                         reference + 2 * length, points)
    compared_values = read_values(connection, comparison - length,
                                  comparison + 2 * length, points)
    limits = None
    oldest = database.first_local_time(connection)
    if oldest is not None:
        # On the axis of the reference, the data of the comparison is
        # offset by the gap between the periods: the graphs may go from
        # the first data of either period to the last. With only a few
        # weeks of data, stopping where either period runs out would
        # leave no room to move. The periods chosen always fit: the
        # current month, for example, goes on after the present
        start = from_local(oldest)
        first = min(start, start + offset, reference)
        last = max(now, now + offset, reference + length)
        limits = (f"{to_local(first):{PLOTLY_TIME}}",
                  f"{to_local(last):{PLOTLY_TIME}}")
    # The legend names the periods chosen in the lists ("October 2026"),
    # or, once dragged or zoomed, the exact times shown
    if compared["chosen"]:
        # With, when the data does not cover the period, when it was
        # measured, such as "Octobre 2026 (mesures du 28 au 31)"
        labels = []
        for moment, period_values in ((reference, values),
                                      (comparison, compared_values)):
            # Each period over its own length: October has 31 days, even
            # drawn over the 30 days of November
            local = to_local(moment)
            label = unit_label(compared["unit"], local.date())
            covered = coverage_text(compared["unit"], period_values, local,
                                    unit_length(compared["unit"],
                                                local.date()))
            labels.append(f"{label} ({covered})" if covered else label)
    else:
        labels = [span_label(moment, moment + length)
                  for moment in (reference, comparison)]
    result = figure(values, points, reference, reference + length,
                    limits, labels[0],
                    (labels[1], moved(compared_values, points, offset)))
    tick, hover = COMPARE_TICKS[compared["unit"]]
    for suffix in ["", "2", "3"]:
        axis = result["layout"]["xaxis" + suffix]
        axis.pop("tickformatstops")
        axis.update(tickformat=tick, hoverformat=hover)
    return result


# --- The page --------------------------------------------------------------

# The icon of the browser tab: a sunflower drawn from an emoji, as on the
# maintenance page of the station, so that no image file is needed
SUNFLOWER_ICON = (
    "<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns="
    "'http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' "
    "font-size='90'>&#127803;</text></svg>\">")


def stored_text(connection):
    """Describes the measurements stored, for the Data tab: (headline,
    detail), such as ("105 121 mesures", "du 05 oct. 2023 au 05 oct.
    2026")."""
    count, oldest, newest = database.summary(connection)
    if count == 0:
        return "Aucune mesure", "La station n'a encore rien envoyé."
    first, last = (to_local(parse_timestamp(text)) for text in (oldest,
                                                                newest))
    # 105121 is written "105 121"
    count_text = f"{count:,}".replace(",", " ")
    return (f"{count_text} mesures",
            f"du {french_date(first, '%d %b %Y')} au "
            f"{french_date(last, '%d %b %Y')}")


# A backup older than this is late: the timer or the copy no longer works
BACKUP_LATE = timedelta(days=2)


def backup_text(status, now):
    """Describes the last backup, for the Data tab; returns (late, text).

    late is True when the last backup failed or is older than BACKUP_LATE:
    the Data tab then shows it in red.
    """
    if status is None:
        return False, "Aucune sauvegarde pour l'instant."
    made = datetime.fromisoformat(status["time"])
    text = ("Dernière sauvegarde : "
            f"{french_date(to_local(made), '%d %b, %H:%M')}")
    if not status["ok"]:
        return True, f"{text}, échec : {status['error']}"
    if status["remote"]:
        text += f", copiée sur {status['remote']}"
    if now - made > BACKUP_LATE:
        return True, f"{text} : en retard, aucune sauvegarde depuis."
    return False, text + "."


def decode_upload(contents):
    """The text of a file sent by the upload area of Dash.

    Dash gives the file as "data:<type>;base64,<content>": the content,
    encoded in base64 (bytes written as text), follows the comma.
    """
    encoded = contents.split(",", 1)[1]
    return base64.b64decode(encoded).decode("utf-8", errors="replace")


def icon(name):
    """An icon of the Lucide set, painted with the color of the text: its
    drawing is chosen in style.css (see .icon)."""
    return html.Span(className=f"icon icon-{name}")


def create_dashboard(open_database, log_path, backup_status,
                     location=None):
    """Creates the Dash application.

    open_database is the function that opens the database, log_path the
    one that gives the path of the log of the station, and backup_status
    the one that gives the result of the last backup: the dashboard
    receives them from main.py, which knows where the data lives.
    location is (latitude, longitude) of the station, for the sun, or
    None.
    """
    # The dashboard is served under /dashboard/ (see main.py): the page
    # must ask for its files and its updates under this address. The
    # viewport tag tells a phone to show the page at its own width,
    # instead of a shrunk desktop page
    app = Dash(__name__, requests_pathname_prefix="/dashboard/",
               title="PAWS",
               meta_tags=[{"name": "viewport",
                           "content": "width=device-width, initial-scale=1, "
                                      "viewport-fit=cover"}])
    # The page that Dash sends holds the icon at the place of {%favicon%}
    # The page is in French: <html lang="fr"> tells it to the browser,
    # for the reading aloud and the hyphenation
    app.index_string = app.index_string.replace("<html>", '<html lang="fr">')
    app.index_string = app.index_string.replace("{%favicon%}",
                                                SUNFLOWER_ICON)

    def graph(graph_id):
        # The graphs take the width of the page, and the height of the
        # screen below the controls (see style.css). The mouse wheel zooms
        # in time (scrollZoom). The bar of icons of Plotly is hidden: the
        # buttons of the page are enough
        return dcc.Graph(id=graph_id, responsive=True,
                         config={"displayModeBar": False,
                                 "scrollZoom": True, "locale": "fr",
                                 "locales": PLOTLY_FRENCH})

    def short_list(list_id):
        # A short list, without a text field nor an empty choice
        return html.Div(id=f"{list_id}-box", className="short-list",
                        children=[dcc.Dropdown(id=list_id, clearable=False,
                                               searchable=False)])

    def time_controls(prefix):
        # The period buttons, Aujourd'hui, then the steps: zoom out, the
        # period before, the period shown, the period after, zoom in. The
        # Courbes and Station tabs have each their own, with the prefix
        # "" or "station-" in their ids; both move the same period shown
        return [
            html.Div(className="controls", children=[
                # Each button holds a long and a short label: style.css
                # shows one or the other, depending on the screen
                dcc.RadioItems(
                    id=f"{prefix}period", value="24h", className="periods",
                    options=[{"label": [
                                  html.Span(label, className="long"),
                                  html.Span(SHORT_LABELS[period],
                                            className="short")],
                              "value": period}
                             for period, label in PERIOD_LABELS.items()]),
                html.Button("Aujourd'hui", id=f"{prefix}today",
                            title="Revenir au présent"),
            ]),
            # The icons are drawn as those of the tabs
            html.Div(className="steps", children=[
                html.Button(icon("zoom-out"), id=f"{prefix}zoom-out",
                            title="Voir une période plus longue"),
                html.Button(icon("chevron-left"), id=f"{prefix}previous",
                            title="La période d'avant"),
                html.Div(id=f"{prefix}period-title",
                         className="period-title"),
                html.Button(icon("chevron-right"), id=f"{prefix}next",
                            title="La période d'après"),
                html.Button(icon("zoom-in"), id=f"{prefix}zoom-in",
                            title="Voir une période plus courte"),
            ]),
        ]

    def period_choice(choice_id, label, line):
        # The lists of a period: the day of the month, the week or the
        # month, and the year. Only the ones the unit needs are shown.
        # Before them, the line of the period in the graphs (solid or
        # dashed) and its name
        return html.Div(className="period-choice", children=[
            html.Span(className=f"swatch {line}"),
            html.Span(label, className="choice-label"),
            short_list(f"{choice_id}-day"),
            short_list(f"{choice_id}-part"),
            short_list(f"{choice_id}-year"),
        ])

    # The navigation panel on the left (at the bottom on a phone, see
    # style.css), then the page, which shows one tab at a time
    app.layout = html.Div(className="root", children=[
      html.Nav(className="sidebar", children=[
        html.Div([html.H1("PAWS"),
                  html.Div("Station météo personnelle autonome",
                           className="subtitle")], className="brand"),
        # The tabs: radio buttons drawn as the entries of the panel
        dcc.RadioItems(
            id="tab", value="now", className="tabs",
            options=[{"label": [
                html.Span(className=f"tab-icon icon-{value}"),
                html.Span(name)], "value": value}
                     for value, name in TABS]),
      ]),
      html.Main(className="page", children=[
        # Shown only when the station is silent, whatever the tab
        html.Div(id="alert", className="alert hidden"),
        html.Div(id="now-tab", children=[
            # Shown only when the battery is low, or the log of the station
            # tells a problem
            html.Div(id="station-alert", className="station-alert hidden"),
            # Shown only when it freezes, or may freeze in the night
            html.Div(id="frost", className="frost hidden"),
            # The top: today and the help button, the time of the last
            # measurement with a dot, green or red, then the temperature
            html.Div(className="hero", children=[
                html.Div(className="hero-top", children=[
                    html.Div([html.Div(id="today-date",
                                       className="today-date"),
                              html.Div(id="status", className="status")]),
                    html.Button("?", id="help-open", className="help-button",
                                title="Comment lire ces valeurs"),
                ]),
                html.Div(id="hero-body"),
            ]),
            html.Div(id="tiles", className="tiles"),
        ]),
        html.Div(id="graphs-tab", style={"display": "none"}, children=[
            *time_controls(""),
            graph("graph"),
        ]),
        # The health of the station: its battery and the problems of its
        # log, then the graphs of the battery
        html.Div(id="station-tab", style={"display": "none"}, children=[
            html.Div(className="tiles", children=[
                html.Div(className="tile", children=[
                    html.Div("Batterie", className="tile-name"),
                    html.Div(id="battery-tile"),
                ]),
                html.Div(className="tile", children=[
                    # The name, and on its right a small button that
                    # downloads the whole log
                    html.Div(className="tile-top", children=[
                        html.Div("Journal", className="tile-name"),
                        html.Button(icon("download"), id="log-export",
                                    className="small-button",
                                    title="Télécharger le journal"),
                    ]),
                    html.Div(id="log-tile"),
                    dcc.Download(id="log-download"),
                ]),
            ]),
            html.Div(className="station-graphs", children=[
                *time_controls("station-"),
                graph("station-graph"),
            ]),
        ]),
        # The advice drawn from the measurements: clothes, laundry,
        # watering, running
        html.Div(id="advice-tab", style={"display": "none"}, children=[
            # The title, and the measurement the advice reads
            html.Div(className="tab-title", children=[
                html.H2("Conseils du moment"),
                html.Div(id="advice-status", className="status"),
            ]),
            html.Div(id="advice-tiles", className="tiles"),
        ]),
        html.Div(id="compare-tab", style={"display": "none"}, children=[
            # The unit, then the reference and the comparison, on one line
            html.Div(className="controls", children=[
                dcc.RadioItems(
                    id="unit", value="month", className="periods",
                    options=[{"label": label, "value": unit}
                             for unit, label in UNITS.items()]),
            ]),
            # The reference, then the comparison
            html.Div(className="compare", children=[
                period_choice("reference", "Référence", "solid"),
                period_choice("comparison", "Comparaison", "dashed"),
            ]),
            graph("compare-graph"),
        ]),
        # Three tiles, as in the other tabs: the measurements stored and
        # their export, the last backup, and the files of the station
        # sent by hand
        html.Div(id="data-tab", style={"display": "none"}, children=[
          html.Div(className="tiles", children=[
            html.Div(className="tile", children=[
                html.Div("Mesures", className="tile-name"),
                html.Div(id="stored"),
                html.Button([icon("download"), "Télécharger (CSV)"],
                            id="export", className="icon-button"),
                dcc.Download(id="download"),
            ]),
            html.Div(className="tile", children=[
                html.Div("Sauvegarde", className="tile-name"),
                # A dot, green or red, then the last backup
                html.Div(id="backup", className="backup"),
            ]),
            html.Div(className="tile", children=[
                html.Div("Importer", className="tile-name"),
                # The files are read by the browser and sent to the
                # page; several can be chosen at once
                dcc.Upload(id="upload", multiple=True, className="upload",
                           children=html.Div([
                               icon("upload"),
                               html.Div("Les fichiers de la page de "
                                        "maintenance de la station : "
                                        "mesures (CSV) et journal."),
                           ])),
                html.Ul(id="upload-result", className="upload-result"),
            ]),
          ]),
        ]),
        # How to read the values: a sheet over the page, hidden until the
        # help button is pressed
        html.Div(id="help", className="help hidden", children=[
            html.Div(className="help-sheet", children=[
                html.Div(className="help-header", children=[
                    html.H2("Comment lire ces valeurs"),
                    html.Button("✕", id="help-close", title="Fermer"),
                ]),
                *explanations(),
            ]),
        ]),
        # The period shown in the Graphs tab (see shown())
        dcc.Store(id="view", data={"length": 86400, "end": None}),
        # The periods of the Compare tab (see compare_dates())
        dcc.Store(id="compared", data=None),
        # The tab last shown, set by the clientside callback below
        dcc.Store(id="resized"),
        # Asks for new data every few minutes, while the page is open
        dcc.Interval(id="refresh", interval=REFRESH_MS),
      ]),
    ])

    @app.callback(
        *[Output(f"{value}-tab", "style") for value, _ in TABS],
        Input("tab", "value"))
    def show_tab(tab):
        # The tab chosen is shown, the others hidden
        return [{} if tab == value else {"display": "none"}
                for value, _ in TABS]

    # Plotly sizes the graphs when it draws them, and again when the
    # window changes size; a hidden tab has no size. When a tab is shown,
    # this function, run by the browser itself (a "clientside" callback,
    # written in JavaScript), tells Plotly that the window changed, so
    # that the graphs take the room of their tab. It changes nothing on
    # the page: Dash needs an output, the store "resized"
    app.clientside_callback(
        """function (tab) {
            // A new tab starts at its top, not where the previous one was
            // scrolled to
            window.scrollTo(0, 0);
            setTimeout(function () {
                window.dispatchEvent(new Event("resize"));
            }, 50);
            return tab;
        }""",
        Output("resized", "data"), Input("tab", "value"))

    # The help sheet opens with the help button, and closes with its cross:
    # the browser shows or hides it by its class, without the server
    app.clientside_callback(
        """function () {
            const trigger = dash_clientside.callback_context.triggered_id;
            return trigger === "help-open" ? "help" : "help hidden";
        }""",
        Output("help", "className"),
        Input("help-open", "n_clicks"), Input("help-close", "n_clicks"),
        prevent_initial_call=True)

    @app.callback(
        Output("download", "data"),
        Input("export", "n_clicks"), prevent_initial_call=True)
    def export(_clicks):
        # Sends the file to the browser, which saves it
        connection = open_database()
        try:
            text = transfer.export_csv(connection)
        finally:
            connection.close()
        name = f"paws_measurements_{datetime.now():%Y-%m-%d}.csv"
        return dcc.send_string(text, name)

    @app.callback(
        Output("stored", "children"), Output("backup", "children"),
        Output("backup", "className"),
        Output("upload-result", "children"), Output("upload", "contents"),
        Input("tab", "value"), Input("upload", "contents"),
        State("upload", "filename"))
    def show_data(_tab, contents, names):
        # Called when a tab is chosen, and when files are uploaded: stores
        # them, then describes the measurements stored. The files are then
        # forgotten by the upload area, so that the same file can be sent
        # again
        connection = open_database()
        try:
            results = no_update
            if ctx.triggered_id == "upload" and contents:
                results = []
                for name, content in zip(names, contents):
                    success, text = transfer.import_file(
                        connection, log_path(), name,
                        decode_upload(content))
                    results.append(html.Li(("✔ " if success else "✘ ")
                                           + text))
            status = backup_status()
            late, text = backup_text(status, datetime.now(timezone.utc))
            headline, detail = stored_text(connection)
            stored = [html.Div(headline, className="tile-headline"),
                      html.Div(detail, className="tile-line muted")]
            # The dot only once there is a backup to judge
            backup = [text] if status is None else [
                html.Span(className="dot"), text]
            return (stored, backup,
                    "backup late" if late else "backup", results, None)
        finally:
            connection.close()

    @app.callback(
        Output("view", "data"), Output("period", "value"),
        Output("station-period", "value"),
        *[Input(f"{prefix}{name}", prop) for prefix in ("", "station-")
          for name, prop in (("period", "value"), ("today", "n_clicks"),
                             ("previous", "n_clicks"), ("next", "n_clicks"),
                             ("zoom-in", "n_clicks"),
                             ("zoom-out", "n_clicks"))],
        Input("graph", "relayoutData"),
        Input("station-graph", "relayoutData"), State("view", "data"),
        prevent_initial_call=True)
    def navigate(period, _today, _previous, _next, _zoom_in, _zoom_out,
                 station_period, _station_today, _station_previous,
                 _station_next, _station_zoom_in, _station_zoom_out,
                 relayout, station_relayout, view):
        # Called on a click on a period, an arrow, a zoom button or Today,
        # or after the graphs were dragged or zoomed, in the Courbes or the
        # Station tab: ctx.triggered_id tells which. Both tabs show the
        # same period, and both period buttons follow it. When the length
        # shown is no longer the one of a period button, none is selected,
        # and a click on any of them sets its length again
        now = datetime.now(timezone.utc)
        trigger = ctx.triggered_id or ""
        in_station = trigger.startswith("station-")
        trigger = trigger.removeprefix("station-")
        if trigger == "graph":
            limits = shown_limits(station_relayout if in_station
                                  else relayout)
            if limits is None:
                return no_update, no_update, no_update
            view = view_after_move(limits, now)
            return view, period_of(view), period_of(view)
        if trigger in ("zoom-in", "zoom-out"):
            factor = 0.5 if trigger == "zoom-in" else 2
            view = view_after_zoom(view, factor, now)
            return view, period_of(view), period_of(view)
        if trigger == "today":
            return {**view, "end": None}, no_update, no_update
        if trigger in ("previous", "next"):
            direction = -1 if trigger == "previous" else 1
            return view_after_step(view, direction, now), no_update, no_update
        chosen = station_period if in_station else period
        if chosen is None:
            return no_update, no_update, no_update
        return ({**view, "length": PERIODS[chosen].total_seconds()},
                chosen, chosen)

    sides = ("reference", "comparison")
    lists = ("day", "part", "year")

    @app.callback(
        Output("compared", "data"),
        # For each list of each side: its value, its choices, whether shown
        *[Output(f"{side}-{name}", "value") for name in lists
          for side in sides],
        *[Output(f"{side}-{name}", "options") for name in lists
          for side in sides],
        *[Output(f"{side}-{name}-box", "style") for name in lists
          for side in sides],
        Input("unit", "value"),
        *[Input(f"{side}-{name}", "value") for name in lists
          for side in sides],
        Input("compare-graph", "relayoutData"),
        State("compared", "data"))
    def choose_periods(unit, reference_day, comparison_day, reference_part,
                       comparison_part, reference_year, comparison_year,
                       relayout, compared):
        # Called when the page opens, when a unit or a period is chosen,
        # or after the graphs were dragged or zoomed. After a move, the
        # lists keep the periods chosen: changing them would count as a
        # new choice, and bring the graphs back to the start of the
        # periods. When the page opens, Dash may name any input as the
        # trigger: a move or a choice is only handled when its values are
        # there
        nothing = [no_update] * 18
        trigger = ctx.triggered_id
        if trigger == "compare-graph":
            limits = shown_limits(relayout)
            if limits is None or compared is None:
                return no_update, *nothing
            return compare_after_move(limits, compared), *nothing
        if trigger is not None and trigger != "unit":
            chosen = [(reference_year, reference_part, reference_day),
                      (comparison_year, comparison_part, comparison_day)]
            needed = {"day": 3, "week": 2, "month": 2, "year": 1}[unit]
            if any(None in values[:needed] for values in chosen):
                return no_update, *nothing
            starts = [start_of(unit, *values).isoformat()
                      for values in chosen]
            return compare_dates(unit, *starts), *nothing
        # A new unit: compare the current period with the one before
        connection = open_database()
        try:
            oldest = database.first_local_time(connection)
        finally:
            connection.close()
        today = to_local(datetime.now(timezone.utc)).date()
        first = date.fromisoformat(oldest[:10]) if oldest else today
        current = unit_start(unit, today)
        before = unit_start(unit, current - timedelta(days=1))
        compared = compare_dates(unit, current.isoformat(),
                                 before.isoformat())
        (reference_year, reference_part, reference_day) = parts_of(
            unit, current)
        (comparison_year, comparison_part, comparison_day) = parts_of(
            unit, before)
        days = [{"label": str(day), "value": day} for day in range(1, 32)]
        parts = part_options(unit) if unit != "year" else []
        years = year_options(first, today)
        shown_style, hidden_style = {}, {"display": "none"}
        day_style = shown_style if unit == "day" else hidden_style
        part_style = hidden_style if unit == "year" else shown_style
        return (compared,
                reference_day, comparison_day,
                reference_part, comparison_part,
                reference_year, comparison_year,
                days, days, parts, parts, years, years,
                day_style, day_style, part_style, part_style,
                shown_style, shown_style)

    @app.callback(
        Output("compare-graph", "figure"),
        Input("compared", "data"))
    def update_comparison(compared):
        if compared is None:
            return no_update
        connection = open_database()
        try:
            return build_comparison(connection, compared,
                                    datetime.now(timezone.utc))
        finally:
            connection.close()

    @app.callback(
        Output("alert", "children"), Output("alert", "className"),
        Output("status", "children"), Output("status", "className"),
        Output("today-date", "children"), Output("frost", "children"),
        Output("frost", "className"), Output("hero-body", "children"),
        Output("tiles", "children"), Output("advice-tiles", "children"),
        Output("advice-status", "children"),
        Output("advice-status", "className"),
        Output("station-alert", "children"),
        Output("station-alert", "className"),
        Input("refresh", "n_intervals"))
    def update_now(_refresh_count):
        # Called when the page opens, and at each refresh: the Now and
        # Advice tabs
        connection = open_database()
        try:
            result = build_now(connection, datetime.now(timezone.utc),
                               location,
                               logs.read_tail(log_path(), LOG_RECENT_BYTES))
        finally:
            connection.close()
        state = "stale" if result["stale"] else "ok"
        alert_class = "alert" if result["alert"] else "alert hidden"
        status = [html.Span(className="dot"), result["status"]]
        frost_class = "frost" if result["frost"] else "frost hidden"
        station_class = ("station-alert" if result["station"]
                         else "station-alert hidden")
        return (result["alert"], alert_class, status, f"status {state}",
                result["date"], result["frost"], frost_class,
                result["hero"], result["tiles"], result["advice"],
                # The advice reads the last measurement: its time, with
                # the same dot as on the Now tab
                status, f"status {state}",
                result["station"], station_class)

    @app.callback(
        Output("graph", "figure"),
        Output("period-title", "children"),
        Output("next", "disabled"),
        Output("station-graph", "figure"),
        Output("station-period-title", "children"),
        Output("station-next", "disabled"),
        Input("view", "data"), Input("refresh", "n_intervals"))
    def update_graphs(view, _refresh_count):
        # Called when the page opens, when the period shown changes, and
        # at each refresh: only the graphs, so that a drag is quick.
        # There is no period after the present
        connection = open_database()
        try:
            result = build_graphs(connection, view,
                                  datetime.now(timezone.utc))
        finally:
            connection.close()
        present = view["end"] is None
        return (result["figure"], result["title"], present,
                result["battery_figure"], result["title"], present)

    @app.callback(
        Output("battery-tile", "children"), Output("log-tile", "children"),
        Input("tab", "value"), Input("refresh", "n_intervals"))
    def show_station(tab, _refresh_count):
        # Called when a tab is chosen, and at each refresh: only the
        # Station tab reads the log, which takes longer than the database
        if tab != "station":
            return no_update, no_update
        connection = open_database()
        try:
            result = build_station(
                connection, logs.read_tail(log_path(), LOG_TAIL_BYTES),
                datetime.now(timezone.utc), location)
        finally:
            connection.close()
        tiles = []
        for headline, lines in (result["battery"], result["log"]):
            tiles.append([html.Div(headline, className="tile-headline"),
                          *[html.Div(line, className="tile-line")
                            for line in lines]])
        # A dot, green or red, before the headline of the log, as for the
        # health of the station
        dot = "dot" if result["log_ok"] else "dot bad"
        tiles[1][0] = html.Div([html.Span(className=dot),
                                result["log"][0]],
                               className="tile-headline")
        return tiles[0], tiles[1]

    @app.callback(
        Output("log-download", "data"),
        Input("log-export", "n_clicks"), prevent_initial_call=True)
    def export_log(_clicks):
        # Sends the whole log of the station to the browser, which saves it
        name = f"paws_log_{datetime.now():%Y-%m-%d}.txt"
        return dcc.send_file(str(log_path()), filename=name)

    return app
