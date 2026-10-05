"""
Project: Personal Autonomous Weather Station
File: backend/paws/paws_server/dashboard.py

Description:
The dashboard: the health of the station, the last measurement, and the
graphs of temperature, humidity and pressure over a period of 24 hours,
7 days, 30 days or 1 year. Over a year, the graphs show the minimum,
average and maximum of each day. The visitor moves in time by dragging
the graphs with the mouse, or with the buttons. A button switches between
a dark and a light theme.

Built with Dash: the page is described in Python, Plotly draws the graphs
in the browser, and Dash calls the functions marked @app.callback when
the visitor clicks, and every few minutes to show the new data. Its style
is in assets/style.css, which Dash adds to the page.

The timestamps are stored in UTC; the dashboard shows them in the local
time of the server.

Dependencies: dash (which includes plotly).
"""

from datetime import datetime, timedelta, timezone

import plotly.io as pio
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from . import database
from .protocol import TIMESTAMP_FORMAT

# The periods offered, and their length
PERIODS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "1y": timedelta(days=365),
}
PERIOD_LABELS = {"24h": "24 hours", "7d": "7 days", "30d": "30 days",
                 "1y": "1 year"}

# How much data the graphs hold on each side of the period shown, so that
# dragging them shows the data before or after right away. Plotly only
# tells the server where the graphs are when the mouse is released: the
# page then loads the data around the new position.
MARGINS = {
    "24h": timedelta(days=7),
    "7d": timedelta(days=28),
    "30d": timedelta(days=60),
    "1y": timedelta(days=365),
}

# The quantities shown: column of the database, name, unit, color
QUANTITIES = [
    ("temperature_c", "Temperature", "°C", "#e4572e"),
    ("humidity_pct", "Humidity", "%", "#2e86ab"),
    ("pressure_hpa", "Pressure", "hPa", "#9575cd"),
]

# The station uploads every hour: after 2 hours without data, it has
# missed an upload, and the dashboard warns
STALE_AFTER = timedelta(hours=2)

# How often the page asks for new data, in milliseconds
REFRESH_MS = 5 * 60 * 1000


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


# --- Navigation in time ----------------------------------------------------
# The page keeps the end of the period shown: None while it shows the
# latest data, or a timestamp once the visitor moved back in time.

def window(period, end, now):
    """Returns (start, stop), the period shown, as datetimes in UTC."""
    stop = now if end is None else parse_timestamp(end)
    return stop - PERIODS[period], stop


def shift(period, end, now, direction):
    """Moves the period shown by one length: -1 back, +1 forth.

    Returns the new end, or None when it reaches the present: the page
    then follows the new data again.
    """
    _, stop = window(period, end, now)
    stop += direction * PERIODS[period]
    return None if stop >= now else to_timestamp(stop)


def end_after_drag(relayout, period, now):
    """Returns the new end of the period after the graphs were dragged.

    relayout is what Plotly reports after a change of the view: after a
    drag, the new limits of the time axis, in local time, such as
    {"xaxis.range[0]": "2026-10-04 10:12:33", "xaxis.range[1]": ...}.
    Returns no_update when the view did not move by a drag (a zoom
    changes the length of the period, a double click resets the view).
    """
    limits = [value for key, value in (relayout or {}).items()
              if key.startswith("xaxis") and ".range[" in key]
    if len(limits) != 2:
        return no_update
    # A naive time is read as local time: astimezone() turns it into UTC
    first, last = sorted(datetime.fromisoformat(value).astimezone(
        timezone.utc) for value in limits)
    length = PERIODS[period]
    if abs((last - first) - length) > length * 0.02:
        return no_update
    return None if last >= now else to_timestamp(last)


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

# The format of the times given to Plotly, in local time
PLOTLY_TIME = "%Y-%m-%d %H:%M:%S"


def midnights(first, last):
    """Returns the local midnights between two local times, in order."""
    day = first.replace(hour=0, minute=0, second=0, microsecond=0)
    result = []
    while day <= last:
        if day >= first:
            result.append(day)
        day += timedelta(days=1)
    return result


def figure(period, rows, days, start, stop, theme):
    """The three graphs, one above the other, sharing the time axis.

    Up to 30 days, each row is a point (rows); over a year, each day shows
    its average, between its minimum and maximum (days). The graphs show
    the period from start to stop, but hold more data on each side (see
    MARGINS), so that the visitor can drag them to see what comes before
    or after.

    The figure is written as a dictionary, in the format that Plotly reads
    in the browser: "data" holds the curves, "layout" the axes, titles and
    colors. The figure objects of Plotly (plotly.graph_objects) would
    check each of the thousands of values, which takes seconds on the
    small computer of the server.
    """
    data = []
    layout = {}
    times = [row["local_time"] for row in rows]
    for index, (column, name, unit, color) in enumerate(QUANTITIES):
        # Plotly names the axes x, x2, x3 and y, y2, y3
        suffix = "" if index == 0 else str(index + 1)
        axes = {"xaxis": "x" + suffix, "yaxis": "y" + suffix}
        hover = f"%{{y:.1f}} {unit}<extra>{name}</extra>"
        if period == "1y":
            x = [day["day"] for day in days]
            # The minimum first, without a line, then the maximum, filled
            # down to the minimum: the band between them
            data.append({"type": "scatter", "x": x, **axes,
                         "y": [day[f"{column}_min"] for day in days],
                         "mode": "lines", "line": {"width": 0},
                         "legendgroup": name, "showlegend": False,
                         "hoverinfo": "skip"})
            data.append({"type": "scatter", "x": x, **axes,
                         "y": [day[f"{column}_max"] for day in days],
                         "mode": "lines", "line": {"width": 0},
                         "fill": "tonexty",
                         "fillcolor": _transparent(color, 0.2),
                         "legendgroup": name,
                         "name": f"{name}: daily min – max",
                         "hoverinfo": "skip"})
            data.append({"type": "scatter", "x": x, **axes,
                         "y": [day[f"{column}_avg"] for day in days],
                         "mode": "lines", "line": {"color": color},
                         "legendgroup": name,
                         "name": f"{name}: daily average",
                         "hovertemplate": hover})
        else:
            data.append({"type": "scatter", "x": times, **axes,
                         "y": [row[column] for row in rows],
                         "mode": "lines",
                         "line": {"color": color, "width": 2}, "name": name,
                         "hovertemplate": hover})
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

    if period == "1y":
        layout["xaxis"]["range"] = [f"{to_local(start):%Y-%m-%d}",
                                    f"{to_local(stop):%Y-%m-%d}"]
    else:
        layout["xaxis"]["range"] = [f"{to_local(start):{PLOTLY_TIME}}",
                                    f"{to_local(stop):{PLOTLY_TIME}}"]
        # A dotted line at each midnight, across the three graphs, to tell
        # the days apart
        margin = MARGINS[period]
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


def build_view(connection, period, end, now, theme="dark"):
    """Computes everything the page shows.

    Returns a dictionary: "stale", "status" and "alert" (the health of
    the station, see health()), "last" (the last measurement), "figure"
    (the graphs), and "at_start" (no older data to go back to).
    """
    last = database.last_row(connection)
    stale, status, alert = health(last, now)
    start, stop = window(period, end, now)
    # The period shown, and a margin on each side to drag the graphs into
    loaded = (to_timestamp(start - MARGINS[period]),
              to_timestamp(stop + MARGINS[period]))
    rows, days = [], []
    if period == "1y":
        days = database.daily_summary(connection, *loaded)
    else:
        rows = database.rows_between(connection, *loaded)
    first = database.first_timestamp(connection)
    return {"stale": stale, "status": status, "alert": alert, "last": last,
            "figure": figure(period, rows, days, start, stop, theme),
            "at_start": first is None or to_timestamp(start) <= first}


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
    # must ask for its files and its updates under this address
    # The viewport tag tells a phone to show the page at its own width,
    # instead of a shrunk desktop page
    app = Dash(__name__, requests_pathname_prefix="/dashboard/",
               title="PAWS",
               meta_tags=[{"name": "viewport",
                           "content": "width=device-width, initial-scale=1"}])
    # The page that Dash sends holds the icon at the place of {%favicon%}
    app.index_string = app.index_string.replace("{%favicon%}",
                                                SUNFLOWER_ICON)

    # The outer block carries the theme ("root dark" or "root light"):
    # style.css gives the page its colors from it
    app.layout = html.Div(id="root", className="root dark", children=[
      html.Div(className="page", children=[
        html.Header(className="header", children=[
            html.Div([html.H1("PAWS"),
                      html.Div("Personal Autonomous Weather Station",
                               className="subtitle")]),
            html.Button("☀", id="theme-button", title="Dark or light theme"),
        ]),
        # Shown only when the station is silent
        html.Div(id="alert", className="alert hidden"),
        # A dot, green or red, then the time of the last measurement
        html.Div(id="status", className="status"),
        html.Div(id="cards", className="cards"),
        html.Div(className="controls", children=[
            dcc.RadioItems(
                id="period", value="24h", className="periods",
                options=[{"label": label, "value": period}
                         for period, label in PERIOD_LABELS.items()]),
            html.Div(className="navigation", children=[
                html.Button("◀", id="back", title="Previous period"),
                html.Button("▶", id="forth", title="Next period"),
                html.Button("Today", id="today"),
            ]),
        ]),
        # The graphs take the width of the page, and a height that fits
        # below the controls on a laptop screen, legend included. The
        # wheel zooms in time, with Ctrl held down (assets/ctrl_zoom.js)
        dcc.Graph(id="graph", responsive=True, style={"height": "560px"},
                  config={"displaylogo": False, "scrollZoom": True}),
        html.P("Drag the graphs to move in time, Ctrl + wheel to zoom; "
               "double-click to come back to the period chosen.",
               className="hint"),
        # The end of the period shown: None while following the new data
        dcc.Store(id="end", data=None),
        # The theme, kept by the browser from one visit to the next
        dcc.Store(id="theme", data="dark", storage_type="local"),
        # Asks for new data every few minutes, while the page is open
        dcc.Interval(id="refresh", interval=REFRESH_MS),
      ]),
    ])

    @app.callback(
        Output("end", "data"),
        Input("back", "n_clicks"), Input("forth", "n_clicks"),
        Input("today", "n_clicks"), Input("graph", "relayoutData"),
        State("period", "value"), State("end", "data"),
        prevent_initial_call=True)
    def navigate(_back, _forth, _today, relayout, period, end):
        # Called on a click on one of the three buttons, or after the
        # graphs were dragged: ctx.triggered_id tells which
        now = datetime.now(timezone.utc)
        if ctx.triggered_id == "back":
            return shift(period, end, now, -1)
        if ctx.triggered_id == "forth":
            return shift(period, end, now, +1)
        if ctx.triggered_id == "graph":
            return end_after_drag(relayout, period, now)
        return None

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
        Output("back", "disabled"), Output("forth", "disabled"),
        Output("root", "className"), Output("theme-button", "children"),
        Input("period", "value"), Input("end", "data"),
        Input("theme", "data"), Input("refresh", "n_intervals"))
    def update(period, end, theme, _refresh_count):
        # Called when the page opens, when the period, its end or the
        # theme changes, and at each refresh
        connection = open_database()
        try:
            view = build_view(connection, period, end,
                              datetime.now(timezone.utc), theme)
        finally:
            connection.close()
        state = "stale" if view["stale"] else "ok"
        alert_class = "alert" if view["alert"] else "alert hidden"
        status = [html.Span(className="dot"), view["status"]]
        # The button shows the theme it switches to
        icon = "☀" if theme == "dark" else "☾"
        return (view["alert"], alert_class, status, f"status {state}",
                cards(view["last"]),
                view["figure"], view["at_start"], end is None,
                f"root {theme}", icon)

    return app
