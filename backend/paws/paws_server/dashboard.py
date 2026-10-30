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
from datetime import date, datetime, timedelta, timezone

import plotly.io as pio
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from . import database, transfer
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
# The tabs of the navigation panel: value, icon, name
TABS = [
    ("now", "◉", "Maintenant"),
    ("graphs", "〜", "Courbes"),
    ("compare", "⇄", "Comparer"),
    ("data", "⬇", "Données"),
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


# The other values written on the card of a quantity, in the Now tab:
# column, name, unit, and the function that tells what the value means,
# or None
CARD_EXTRAS = {
    "temperature_c": [("dew_point_c", "Point de rosée", "°C", dew_comfort),
                      ("feels_like_c", "Ressenti", "°C", None)],
    "sea_level_hpa": [("pressure_hpa", "À la station", "hPa", None)],
}

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
    status = ("Dernière mesure · "
              f"{french_date(to_local(measured), '%d %b, %H:%M')} "
              f"(il y a {format_age(age)})")
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


# What the change of the pressure over 3 hours tells, from the scale
# used by weather services (the UK Met Office): below 0.1 hPa, the
# pressure is steady; then, up to each limit, in hPa, what a rise and a
# fall usually mean. A low pressure makes the air rise, cool down and form
# clouds: a falling pressure often brings rain. These are tendencies, not
# forecasts: the sentences say "often" or "likely"
PRESSURE_STEADY = "Pression stable : peu de changement du temps."
PRESSURE_OUTLOOK = [
    (1.5, "Pression en légère hausse : peu de changement du temps.",
     "Pression en légère baisse : peu de changement du temps."),
    (3.5, "Pression en hausse : le temps s'améliore souvent.",
     "Pression en baisse : le temps se dégrade souvent."),
    (6.0, "Pression en forte hausse : éclaircies, souvent avec du vent.",
     "Pression en forte baisse : pluie et vent probables."),
    (None, "Pression en très forte hausse : vent fort probable.",
     "Pression en très forte baisse : risque de tempête."),
]

# Below these changes in 3 hours, the temperature and the humidity are
# said steady
STEADY_TEMPERATURE = 1.0
STEADY_HUMIDITY = 10.0


def pressure_outlook(change):
    """The sentence about the change of the pressure over 3 hours, in
    hPa, such as "Pression en forte baisse : pluie et vent probables."."""
    size = round(abs(change), 1)
    if size < 0.1:
        return PRESSURE_STEADY
    for limit, rising, falling in PRESSURE_OUTLOOK:
        if limit is None or size <= limit:
            return rising if change > 0 else falling


def weather_summary(changes, last=None):
    """A short text about the trends of the last 3 hours, at the top of the
    Now tab, then about the last measurement (last, see cards()). changes
    holds the change of each quantity, by column (see trend()), None when
    unknown. Returns "" when nothing is known."""
    sentences = []
    if changes.get("sea_level_hpa") is not None:
        sentences.append(pressure_outlook(changes["sea_level_hpa"]))
    temperature = changes.get("temperature_c")
    if temperature is not None and abs(temperature) >= STEADY_TEMPERATURE:
        sentences.append("Il fait de plus en plus chaud." if temperature > 0
                         else "Il fait de plus en plus frais.")
    humidity = changes.get("humidity_pct")
    if humidity is not None and abs(humidity) >= STEADY_HUMIDITY:
        sentences.append("L'air devient plus humide." if humidity > 0
                         else "L'air devient plus sec.")
    if last is not None:
        sentences += now_sentences(last)
    return " ".join(sentences)


# When the temperature is this close to the dew point, the air is nearly
# saturated: water condenses on cold surfaces (dew, or frost below 0 °C),
# or in the air (fog)
DEW_SPREAD_C = 2.0


def now_sentences(last):
    """What the dew point and the feels-like temperature of the last
    measurement tell, when they tell something."""
    sentences = []
    temperature = last["temperature_c"]
    dew = last["dew_point_c"]
    if temperature is not None and dew is not None \
            and temperature - dew <= DEW_SPREAD_C:
        water = "givre" if temperature <= 0 else "rosée"
        sentences.append("L'air est presque saturé d'eau : "
                         f"{water} ou brouillard probable.")
    feels = last["feels_like_c"]
    if feels is not None and feels - temperature >= 1:
        sentences.append("Avec l'humidité, on ressent "
                         f"{number(feels, 0)} °C.")
    return sentences


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
    """A small curve of the last day, without axes, for a card."""
    return {"data": [{"type": "scatter", "mode": "lines",
                      "x": [row["local_time"] for row in rows],
                      "y": [row[column] for row in rows],
                      "line": {"color": color, "width": 2},
                      "hoverinfo": "skip"}],
            "layout": {"margin": {"l": 0, "r": 0, "t": 4, "b": 4},
                       "xaxis": {"visible": False},
                       "yaxis": {"visible": False},
                       "showlegend": False,
                       "paper_bgcolor": "rgba(0,0,0,0)",
                       "plot_bgcolor": "rgba(0,0,0,0)"}}


def cards(last, rows, day):
    """One card per quantity: the value of the last measurement, its
    change over the last 3 hours, its other values (see CARD_EXTRAS), a
    small curve of the last day, and the minimum and maximum of the local
    day (day, such as "2026-10-05"). rows are the rows of the last day,
    oldest first."""
    if last is None:
        return []
    result = []
    for column, name, unit, color in QUANTITIES:
        value = "–" if last[column] is None else number(last[column])
        extremes = day_extremes(rows, day, column)
        today = ""
        if extremes is not None:
            (low, low_time), (high, high_time) = extremes
            today = (f"Aujourd'hui : min {number(low)} à {low_time} · "
                     f"max {number(high)} à {high_time}")
        # The other values that are known, and what they mean, such as
        # "Point de rosée 8,1 °C (air sec)"
        others = " · ".join(
            f"{other} {number(last[key])} {other_unit}"
            + ("" if meaning is None else f" ({meaning(last[key])})")
            for key, other, other_unit, meaning in CARD_EXTRAS.get(column, [])
            if last[key] is not None)
        result.append(html.Div(className="card", style={"borderColor": color},
                               children=[
            html.Div(name, className="card-name"),
            html.Div(className="card-line", children=[
                html.Div([value, html.Span(f" {unit}",
                                           className="card-unit")],
                         className="card-value", style={"color": color}),
                html.Div(trend_text(trend(rows, last, column), unit),
                         className="card-trend"),
            ]),
            html.Div(others, className="card-others"),
            # A picture of the curve: it cannot be dragged nor zoomed
            dcc.Graph(figure=sparkline(rows, column, color),
                      className="sparkline",
                      config={"staticPlot": True}),
            html.Div(today, className="card-extremes"),
        ]))
    return result


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


def graph_title(quantity, extras):
    """The title of a graph: the name of its quantity, such as
    "Température (°C)", then, on a second line, in smaller letters, the
    names of the computed quantities drawn with it, in their color:
    "Point de rosée · Ressenti (pointillés, dès 27 °C)"."""
    _, name, unit, _ = quantity
    title = f"{name} ({unit})"
    names = []
    for _, extra_name, _, color, dash, _ in extras:
        dotted = " (pointillés, dès 27 °C)" if dash == "dot" else ""
        names.append(f"<span style='color:{color}'>{extra_name}{dotted}"
                     "</span>")
    if names:
        title += ("<br><span style='font-size:13px'>" + " · ".join(names)
                  + "</span>")
    return title


def figure(values, points, start, stop, limits=None, label=None,
           comparison=None):
    """The three graphs, one above the other, sharing the time axis.

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
    data = []
    layout = {}
    for index, quantity in enumerate(QUANTITIES):
        # Plotly names the axes x, x2, x3 and y, y2, y3
        suffix = "" if index == 0 else str(index + 1)
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
        layout["yaxis" + suffix] = {"domain": DOMAINS[index],
                                    "anchor": "x" + suffix,
                                    "gridcolor": GRID,
                                    "fixedrange": True,
                                    # "1029,5", without a space between
                                    # thousands
                                    "tickformat": ".1~f"}
        # The time axis has no grid of its own: the dotted lines at
        # midnight tell the days apart
        layout["xaxis" + suffix] = {"anchor": "y" + suffix, "type": "date",
                                    "showgrid": False,
                                    "showticklabels": index == 2,
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
        for suffix in ["", "2", "3"]:
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
                             else EXTRA_CURVES.get(quantity[0], [])),
         "x": 0.5, "xref": "paper",
         "y": DOMAINS[index][1], "yref": "paper", "yanchor": "bottom",
         "showarrow": False, "font": {"size": 16}}
        for index, quantity in enumerate(QUANTITIES)]
    layout.update(
        template=TEMPLATE,
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        # Dragging the graphs moves them in time, instead of zooming
        dragmode="pan",
        # Room at the top for the title of the temperature graph, on two
        # lines in the Graphs tab; at the bottom, for the dates, and for
        # the legend of the Compare tab
        margin={"l": 60, "r": 20, "t": 60 if comparison is None else 40,
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


def build_view(connection, view, now):
    """Computes everything the Graphs tab shows.

    view is the period shown (see shown()). Returns a dictionary:
    "stale", "status" and "alert" (the health of the station, see
    health()), "date" (today, in words), "summary" (the trends, see
    weather_summary()), "cards" (see cards()), "title"
    (the period shown, see period_title()) and "figure" (the graphs).
    """
    last = database.last_row(connection)
    stale, status, alert = health(last, now)
    # The rows of the last day, for the cards
    day_rows = database.rows_between(
        connection, to_timestamp(now - timedelta(days=1)),
        to_timestamp(now + timedelta(minutes=1)))
    local_now = to_local(now)
    start, stop = shown(view, now)
    # The period shown, and as much again on each side to drag into
    length = stop - start
    points = resolution(length)
    values = read_values(connection, start - length, stop + length, points)
    oldest = database.first_local_time(connection)
    limits = None
    if oldest is not None:
        limits = (oldest, f"{to_local(now):{PLOTLY_TIME}}")
    changes = {}
    if last is not None:
        changes = {column: trend(day_rows, last, column)
                   for column, _, _, _ in QUANTITIES}
    return {"stale": stale, "status": status, "alert": alert,
            "summary": weather_summary(changes, last),
            "date": french_date(local_now, "%A %d %B %Y").capitalize(),
            "cards": cards(last, day_rows, f"{local_now:%Y-%m-%d}"),
            "title": period_title(view, now),
            "figure": figure(values, points, start, stop, limits)}


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
    over it. A drag or a zoom stops when either period would leave the
    data: no earlier than the oldest row, no later than the present.
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
        # On the axis of the reference, the comparison is offset later.
        # The periods chosen always fit: the current month, for example,
        # goes on after the present
        first = min(from_local(oldest) + max(offset, timedelta(0)),
                    reference)
        last = max(now + min(offset, timedelta(0)), reference + length)
        limits = (f"{to_local(first):{PLOTLY_TIME}}",
                  f"{to_local(last):{PLOTLY_TIME}}")
    # The legend names the periods chosen in the lists ("October 2026"),
    # or, once dragged or zoomed, the exact times shown
    if compared["chosen"]:
        labels = [unit_label(compared["unit"], to_local(moment).date())
                  for moment in (reference, comparison)]
    else:
        labels = [span_label(moment, moment + length)
                  for moment in (reference, comparison)]
    return figure(values, points, reference, reference + length,
                  limits, labels[0],
                  (labels[1], moved(compared_values, points, offset)))


# --- The page --------------------------------------------------------------

# The icon of the browser tab: a sunflower drawn from an emoji, as on the
# maintenance page of the station, so that no image file is needed
SUNFLOWER_ICON = (
    "<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns="
    "'http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' "
    "font-size='90'>&#127803;</text></svg>\">")


def stored_text(connection):
    """Describes the measurements stored, for the Data tab."""
    count, oldest, newest = database.summary(connection)
    if count == 0:
        return "Aucune mesure enregistrée pour l'instant."
    first, last = (to_local(parse_timestamp(text)) for text in (oldest,
                                                                newest))
    # 105121 is written "105 121"
    count_text = f"{count:,}".replace(",", " ")
    return (f"Enregistrées : {count_text} mesures, du "
            f"{french_date(first, '%d %b %Y')} au "
            f"{french_date(last, '%d %b %Y')}.")


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


def create_dashboard(open_database, log_path, backup_status):
    """Creates the Dash application.

    open_database is the function that opens the database, log_path the
    one that gives the path of the log of the station, and backup_status
    the one that gives the result of the last backup: the dashboard
    receives them from main.py, which knows where the data lives.
    """
    # The dashboard is served under /dashboard/ (see main.py): the page
    # must ask for its files and its updates under this address. The
    # viewport tag tells a phone to show the page at its own width,
    # instead of a shrunk desktop page
    app = Dash(__name__, requests_pathname_prefix="/dashboard/",
               title="PAWS",
               meta_tags=[{"name": "viewport",
                           "content": "width=device-width, initial-scale=1"}])
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
            options=[{"label": [html.Span(icon, className="tab-icon"),
                                html.Span(name)], "value": value}
                     for value, icon, name in TABS]),
      ]),
      html.Main(className="page", children=[
        # Shown only when the station is silent, whatever the tab
        html.Div(id="alert", className="alert hidden"),
        html.Div(id="now-tab", children=[
            # Today, then a dot, green or red, and the time of the last
            # measurement
            html.H2(id="today-date", className="today-date"),
            html.Div(id="status", className="status"),
            # What the trends of the last 3 hours tell
            html.P(id="summary", className="summary"),
            html.Div(id="cards", className="cards"),
            html.H3("Comment lire ces valeurs", className="explanations"),
            *explanations(),
        ]),
        html.Div(id="graphs-tab", style={"display": "none"}, children=[
            html.Div(className="controls", children=[
                # Each button holds a long and a short label: style.css
                # shows one or the other, depending on the screen
                dcc.RadioItems(
                    id="period", value="24h", className="periods",
                    options=[{"label": [
                                  html.Span(label, className="long"),
                                  html.Span(SHORT_LABELS[period],
                                            className="short")],
                              "value": period}
                             for period, label in PERIOD_LABELS.items()]),
                html.Button("Aujourd'hui", id="today",
                            title="Revenir au présent"),
            ]),
            # The period before, the period shown, the period after
            html.Div(className="steps", children=[
                html.Button("◀", id="previous", title="La période d'avant"),
                html.Div(id="period-title", className="period-title"),
                html.Button("▶", id="next", title="La période d'après"),
            ]),
            graph("graph"),
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
        html.Div(id="data-tab", style={"display": "none"}, children=[
            html.P(id="stored", className="stored"),
            html.P(id="backup", className="backup"),
            html.Button("⬇ Télécharger toutes les mesures (CSV)",
                        id="export"),
            dcc.Download(id="download"),
            # The files are read by the browser and sent to the page;
            # several can be chosen at once
            dcc.Upload(id="upload", multiple=True, className="upload",
                       children=html.Div([
                           "Déposez ici, ou cliquez pour choisir, les "
                           "fichiers téléchargés depuis la page de "
                           "maintenance de la station : les mesures (CSV) "
                           "et le journal."])),
            html.Ul(id="upload-result", className="upload-result"),
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
        *[Output(f"{value}-tab", "style") for value, _, _ in TABS],
        Input("tab", "value"))
    def show_tab(tab):
        # The tab chosen is shown, the others hidden
        return [{} if tab == value else {"display": "none"}
                for value, _, _ in TABS]

    # Plotly sizes the graphs when it draws them, and again when the
    # window changes size; a hidden tab has no size. When a tab is shown,
    # this function, run by the browser itself (a "clientside" callback,
    # written in JavaScript), tells Plotly that the window changed, so
    # that the graphs take the room of their tab. It changes nothing on
    # the page: Dash needs an output, the store "resized"
    app.clientside_callback(
        """function (tab) {
            setTimeout(function () {
                window.dispatchEvent(new Event("resize"));
            }, 50);
            return tab;
        }""",
        Output("resized", "data"), Input("tab", "value"))

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
            late, text = backup_text(backup_status(),
                                     datetime.now(timezone.utc))
            return (stored_text(connection), text,
                    "backup late" if late else "backup", results, None)
        finally:
            connection.close()

    @app.callback(
        Output("view", "data"), Output("period", "value"),
        Input("period", "value"), Input("today", "n_clicks"),
        Input("previous", "n_clicks"), Input("next", "n_clicks"),
        Input("graph", "relayoutData"), State("view", "data"),
        prevent_initial_call=True)
    def navigate(period, _today, _previous, _next, relayout, view):
        # Called on a click on a period, an arrow or Today, or after the
        # graphs were dragged or zoomed: ctx.triggered_id tells which
        now = datetime.now(timezone.utc)
        limits = shown_limits(relayout)
        if ctx.triggered_id == "graph":
            if limits is None:
                return no_update, no_update
            view = view_after_move(limits, now)
            # The length shown is no longer the one of a button: none is
            # selected, and a click on any of them sets its length again
            length = timedelta(seconds=view["length"])
            matching = [key for key, value in PERIODS.items()
                        if value == length]
            return view, (matching[0] if matching else None)
        if ctx.triggered_id == "today":
            return {**view, "end": None}, no_update
        if ctx.triggered_id in ("previous", "next"):
            direction = -1 if ctx.triggered_id == "previous" else 1
            return view_after_step(view, direction, now), no_update
        if period is None:
            return no_update, no_update
        return {**view, "length": PERIODS[period].total_seconds()}, no_update

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
        Output("today-date", "children"), Output("summary", "children"),
        Output("cards", "children"), Output("graph", "figure"), Output("period-title", "children"),
        Output("next", "disabled"),
        Input("view", "data"), Input("refresh", "n_intervals"))
    def update(view, _refresh_count):
        # Called when the page opens, when the period shown changes, and
        # at each refresh. There is no period after the present
        connection = open_database()
        try:
            result = build_view(connection, view,
                                datetime.now(timezone.utc))
        finally:
            connection.close()
        state = "stale" if result["stale"] else "ok"
        alert_class = "alert" if result["alert"] else "alert hidden"
        status = [html.Span(className="dot"), result["status"]]
        return (result["alert"], alert_class, status, f"status {state}",
                result["date"], result["summary"], result["cards"],
                result["figure"],
                result["title"],
                view["end"] is None)

    return app
