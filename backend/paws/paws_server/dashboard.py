"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/dashboard.py

Description:
The dashboard: the health of the station, the last measurement, and the
graphs of temperature, humidity and pressure. Two tabs:

- Graphs: the graphs over a period chosen with the buttons (24 hours,
  7 days, 30 days, 1 year), then moved by dragging the graphs and zoomed
  with the mouse wheel;
- Compare: two days, weeks, months or years drawn over each other,
  aligned on their start, then dragged and zoomed together.

Over a long period, the graphs show the minimum, average and maximum of
each day. A button switches between a dark and a light theme.

Built with Dash: the page is described in Python, Plotly draws the graphs
in the browser, and Dash calls the functions marked @app.callback when
the visitor clicks, and every few minutes to show the new data. Its style
is in assets/style.css, which Dash adds to the page.

The timestamps are stored in UTC; the dashboard shows them in the local
time of the server.

Dependencies: dash (which includes plotly).
"""

import calendar
from datetime import date, datetime, timedelta, timezone

import plotly.io as pio
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from . import database
from .protocol import TIMESTAMP_FORMAT

# The periods of the buttons of the Graphs tab, and their length
PERIODS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "1y": timedelta(days=365),
}
PERIOD_LABELS = {"24h": "24 hours", "7d": "7 days", "30d": "30 days",
                 "1y": "1 year"}
# Shorter labels, shown on a phone instead (see style.css)
SHORT_LABELS = {"24h": "24h", "7d": "7d", "30d": "30d", "1y": "1y"}

# The units of the Compare tab. A period is chosen in short lists: the
# day, the month and the year for a day; the week number and the year for
# a week; the month and the year for a month; the year for a year
UNITS = {"day": "Day", "week": "Week", "month": "Month", "year": "Year"}

# The quantities shown: column of the database, name, unit, color. The
# three colors stay distinct for the most common forms of color blindness
QUANTITIES = [
    ("temperature_c", "Temperature", "°C", "#e4572e"),
    ("humidity_pct", "Humidity", "%", "#2f8fe0"),
    ("pressure_hpa", "Pressure", "hPa", "#d063b5"),
]

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
# latest data. The buttons set the length; a drag or a zoom sets both.

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


def span_label(start, stop):
    """Writes a period in local time: "04 Oct 15:30 → 05 Oct 15:30" up to
    2 days, "05 Sep 2026 → 05 Oct 2026" beyond."""
    first, last = to_local(start), to_local(stop)
    if stop - start <= timedelta(days=2):
        return f"{first:%d %b %H:%M} → {last:%d %b %H:%M}"
    return f"{first:%d %b %Y} → {last:%d %b %Y}"


# --- Health and last measurement -------------------------------------------

def format_age(age):
    """Writes a duration in words: "12 min", "3 h 05 min" or "4 days"."""
    minutes = int(age.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 48 * 60:
        return f"{minutes // 60} h {minutes % 60:02d} min"
    return f"{minutes // (24 * 60)} days"


def health(last, now):
    """Returns (stale, status, alert): the health of the station.

    stale tells whether the station is silent; status describes the last
    measurement, shown above the cards; alert is the warning shown at the
    top of the page when the station is silent, empty otherwise.
    """
    if last is None:
        return (True, "No measurement received yet",
                "No measurement received yet: check the station.")
    measured = parse_timestamp(last["timestamp"])
    age = now - measured
    status = (f"Last measurement · {to_local(measured):%d %b, %H:%M} "
              f"({format_age(age)} ago)")
    if age > STALE_AFTER:
        return (True, status, f"No new measurement for {format_age(age)}: "
                "check the station.")
    return False, status, ""


def cards(last):
    """One card per quantity, with the value of the last measurement."""
    if last is None:
        return []
    result = []
    for column, name, unit, color in QUANTITIES:
        value = "–" if last[column] is None else f"{last[column]:.1f}"
        result.append(html.Div(className="card", style={"borderColor": color},
                               children=[
            html.Div(name, className="card-name"),
            html.Div([value, html.Span(f" {unit}", className="card-unit")],
                     className="card-value", style={"color": color}),
        ]))
    return result


# --- Graphs ----------------------------------------------------------------

def _transparent(color, alpha):
    # "#e4572e" -> "rgba(228,87,46,0.2)", for the band of the daily values
    red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({red},{green},{blue},{alpha})"


# Colors of the two themes: background of the cards, and of the dotted
# lines at midnight. The graphs use the matching template of Plotly, its
# set of colors, fonts and grids, read once as a dictionary
THEMES = {
    "dark": {"template": pio.templates["plotly_dark"].to_plotly_json(),
             "card": "#1f242c", "midnight": "rgba(255,255,255,0.3)"},
    "light": {"template": pio.templates["plotly_white"].to_plotly_json(),
              "card": "#ffffff", "midnight": "rgba(0,0,0,0.3)"},
}

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
    if label is not None:
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
                       "name": f"{title}: daily min – max",
                       "hoverinfo": "skip"})
    curves.append({**common, "x": x, "line": line,
                   "y": [day[f"{column}_avg"] for day in values],
                   "name": f"{title}: daily average"})
    return curves


def figure(values, points, start, stop, theme, limits=None, label=None,
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
        # Each graph has its own value axis, which keeps its scale (only
        # time moves), and a time axis that follows the first one
        # ("matches"); only the time axis of the bottom graph shows dates
        layout["yaxis" + suffix] = {"domain": DOMAINS[index],
                                    "anchor": "x" + suffix,
                                    "fixedrange": True}
        layout["xaxis" + suffix] = {"anchor": "y" + suffix, "type": "date",
                                    "showticklabels": index == 2}
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
        line = {"color": THEMES[theme]["midnight"], "width": 1, "dash": "dot"}
        layout["shapes"] = [
            {"type": "line", "x0": f"{midnight:{PLOTLY_TIME}}",
             "x1": f"{midnight:{PLOTLY_TIME}}", "xref": "x",
             "y0": 0, "y1": 1, "yref": "paper", "line": line}
            for midnight in midnights(to_local(start - margin),
                                      to_local(stop + margin))]

    # The title of each graph, above it
    layout["annotations"] = [
        {"text": f"{name} ({unit})", "x": 0.5, "xref": "paper",
         "y": DOMAINS[index][1], "yref": "paper", "yanchor": "bottom",
         "showarrow": False, "font": {"size": 16}}
        for index, (_, name, unit, _) in enumerate(QUANTITIES)]
    layout.update(
        template=THEMES[theme]["template"],
        paper_bgcolor=THEMES[theme]["card"],
        plot_bgcolor=THEMES[theme]["card"],
        # Dragging the graphs moves them in time, instead of zooming
        dragmode="pan",
        margin={"l": 60, "r": 20, "t": 40, "b": 90},
        hovermode="x unified",
        # The legend at the bottom of the figure ("container"), below the
        # dates of the time axis
        legend={"orientation": "h", "x": 0, "y": 0, "yref": "container",
                "yanchor": "bottom"},
        font={"family": "system-ui, sans-serif"})
    return {"data": data, "layout": layout}


def build_view(connection, view, now, theme="dark"):
    """Computes everything the Graphs tab shows.

    view is the period shown (see shown()). Returns a dictionary:
    "stale", "status" and "alert" (the health of the station, see
    health()), "last" (the last measurement) and "figure" (the graphs).
    """
    last = database.last_row(connection)
    stale, status, alert = health(last, now)
    start, stop = shown(view, now)
    # The period shown, and as much again on each side to drag into
    length = stop - start
    points = resolution(length)
    values = read_values(connection, start - length, stop + length, points)
    oldest = database.first_local_time(connection)
    limits = None
    if oldest is not None:
        limits = (oldest, f"{to_local(now):{PLOTLY_TIME}}")
    return {"stale": stale, "status": status, "alert": alert, "last": last,
            "figure": figure(values, points, start, stop, theme, limits)}


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
    """Names a period: "Mon 05 Oct 2026", "Week 41 · 05 – 11 Oct 2026",
    "October 2026" or "2026"."""
    if unit == "week":
        end = start + timedelta(days=6)
        return (f"Week {start.isocalendar().week} · {start:%d %b} – "
                f"{end:%d %b %Y}")
    if unit == "month":
        return f"{start:%B %Y}"
    if unit == "year":
        return f"{start:%Y}"
    return f"{start:%a %d %b %Y}"


def part_options(unit):
    """The list of the week or the month: "W1" to "W53", or "Jan" to
    "Dec" (for a month or a day)."""
    if unit == "week":
        return [{"label": f"W{week}", "value": week}
                for week in range(1, 54)]
    return [{"label": calendar.month_abbr[month], "value": month}
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


def build_comparison(connection, compared, now, theme="dark"):
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
    return figure(values, points, reference, reference + length, theme,
                  limits, labels[0],
                  (labels[1], moved(compared_values, points, offset)))


# --- The page --------------------------------------------------------------

# The icon of the browser tab: a sunflower drawn from an emoji, as on the
# maintenance page of the station, so that no image file is needed
SUNFLOWER_ICON = (
    "<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns="
    "'http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' "
    "font-size='90'>&#127803;</text></svg>\">")


def create_dashboard(open_database):
    """Creates the Dash application.

    open_database is the function that opens the database: the dashboard
    receives it from main.py, which knows where the data lives.
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
    app.index_string = app.index_string.replace("{%favicon%}",
                                                SUNFLOWER_ICON)

    def graph(graph_id):
        # The graphs take the width of the page, and a height that fits
        # below the controls on a laptop screen, legend included. The
        # mouse wheel zooms in time (scrollZoom)
        return dcc.Graph(id=graph_id, responsive=True,
                         style={"height": "560px"},
                         config={"displaylogo": False, "scrollZoom": True})

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

    # The outer block carries the theme ("root dark" or "root light"):
    # style.css gives the page its colors from it
    app.layout = html.Div(id="root", className="root dark", children=[
      html.Div(className="page", children=[
        html.Header(className="header", children=[
            html.Div([html.H1("PAWS"),
                      html.Div("Personal Autonomous Weather Station",
                               className="subtitle")]),
            html.Div(className="header-right", children=[
                # The two tabs, drawn as a row of buttons like the periods
                dcc.RadioItems(
                    id="tab", value="graphs", className="periods",
                    options=[{"label": "Graphs", "value": "graphs"},
                             {"label": "Compare", "value": "compare"}]),
                html.Button("☀", id="theme-button",
                            title="Dark or light theme"),
            ]),
        ]),
        # Shown only when the station is silent
        html.Div(id="alert", className="alert hidden"),
        # A dot, green or red, then the time of the last measurement
        html.Div(id="status", className="status"),
        html.Div(id="cards", className="cards"),
        html.Div(id="graphs-tab", children=[
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
                html.Button("Today", id="today",
                            title="Come back to the present"),
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
                period_choice("reference", "Reference", "solid"),
                period_choice("comparison", "Comparison", "dashed"),
            ]),
            graph("compare-graph"),
        ]),
        html.P("Drag the graphs to move in time, turn the mouse wheel over "
               "them to zoom.", className="hint"),
        # The period shown in the Graphs tab (see shown())
        dcc.Store(id="view", data={"length": 86400, "end": None}),
        # The periods of the Compare tab (see compare_dates())
        dcc.Store(id="compared", data=None),
        # The theme, kept by the browser from one visit to the next
        dcc.Store(id="theme", data="dark", storage_type="local"),
        # Asks for new data every few minutes, while the page is open
        dcc.Interval(id="refresh", interval=REFRESH_MS),
      ]),
    ])

    @app.callback(
        Output("graphs-tab", "style"), Output("compare-tab", "style"),
        Input("tab", "value"))
    def show_tab(tab):
        hidden = {"display": "none"}
        return (hidden, {}) if tab == "compare" else ({}, hidden)

    @app.callback(
        Output("view", "data"), Output("period", "value"),
        Input("period", "value"), Input("today", "n_clicks"),
        Input("graph", "relayoutData"), State("view", "data"),
        prevent_initial_call=True)
    def navigate(period, _today, relayout, view):
        # Called on a click on a period or on Today, or after the graphs
        # were dragged or zoomed: ctx.triggered_id tells which
        limits = shown_limits(relayout)
        if ctx.triggered_id == "graph":
            if limits is None:
                return no_update, no_update
            view = view_after_move(limits, datetime.now(timezone.utc))
            # The length shown is no longer the one of a button: none is
            # selected, and a click on any of them sets its length again
            length = timedelta(seconds=view["length"])
            matching = [key for key, value in PERIODS.items()
                        if value == length]
            return view, (matching[0] if matching else None)
        if ctx.triggered_id == "today":
            return {**view, "end": None}, no_update
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
        Input("compared", "data"), Input("theme", "data"))
    def update_comparison(compared, theme):
        if compared is None:
            return no_update
        connection = open_database()
        try:
            return build_comparison(connection, compared,
                                    datetime.now(timezone.utc), theme)
        finally:
            connection.close()

    @app.callback(
        Output("theme", "data"),
        Input("theme-button", "n_clicks"), State("theme", "data"),
        prevent_initial_call=True)
    def switch_theme(_clicks, theme):
        return "light" if theme == "dark" else "dark"

    @app.callback(
        Output("alert", "children"), Output("alert", "className"),
        Output("status", "children"), Output("status", "className"),
        Output("cards", "children"),
        Output("graph", "figure"),
        Output("root", "className"), Output("theme-button", "children"),
        Input("view", "data"),
        Input("theme", "data"), Input("refresh", "n_intervals"))
    def update(view, theme, _refresh_count):
        # Called when the page opens, when the period shown or the theme
        # changes, and at each refresh
        connection = open_database()
        try:
            result = build_view(connection, view,
                                datetime.now(timezone.utc), theme)
        finally:
            connection.close()
        state = "stale" if result["stale"] else "ok"
        alert_class = "alert" if result["alert"] else "alert hidden"
        status = [html.Span(className="dot"), result["status"]]
        # The button shows the theme it switches to
        icon = "☀" if theme == "dark" else "☾"
        return (result["alert"], alert_class, status, f"status {state}",
                cards(result["last"]), result["figure"], f"root {theme}",
                icon)

    return app
