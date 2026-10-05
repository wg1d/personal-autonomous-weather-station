"""
Project: Personal Autonomous Weather Station
File: backend/paws/dev/make_test_data.py

Description:
Fills a database with made-up measurements, one row every 15 minutes over
several years, to try the dashboard on the development computer without
waiting for the station. The values follow the seasons and the hours of
the day, with some noise.

Usage (from backend/paws):
    uv run python dev/make_test_data.py [years]   # default: 3 years
    PAWS_DATA_DIR=dev/data uv run uvicorn paws_server.main:app --port 8080

The database is written to dev/data/measurements.db, ignored by git. It
is made again at each run, so that it always ends at the present time.

Dependencies: Python standard library.
"""

import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paws_server import database  # noqa: E402
from paws_server.protocol import TIMESTAMP_FORMAT  # noqa: E402

years = int(sys.argv[1]) if len(sys.argv) > 1 else 3
folder = Path(__file__).parent / "data"
folder.mkdir(exist_ok=True)

# Ends at the last quarter of an hour, like a station that has just sent
end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
end -= timedelta(minutes=end.minute % 15)
time = end - timedelta(days=365 * years)

rows = []
pressure = 1013.0
while time <= end:
    # Warmest in July and at 15:00, coldest in January and at 3:00
    season = math.cos(2 * math.pi * (time.timetuple().tm_yday - 200) / 365)
    day = math.cos(2 * math.pi * (time.hour + time.minute / 60 - 15) / 24)
    temperature = 12 + 8 * season + 5 * day + random.gauss(0, 0.5)
    # More humid at night and in winter
    humidity = 72 - 8 * season - 15 * day + random.gauss(0, 3)
    # The pressure drifts slowly, pulled back towards 1013 hPa: highs and
    # lows lasting a few days, as weather systems pass
    pressure += random.gauss(0, 0.25) - 0.005 * (pressure - 1013)
    rows.append((time.strftime(TIMESTAMP_FORMAT), 1, round(temperature, 2),
                 round(min(humidity, 100), 2), round(pressure, 2)))
    time += timedelta(minutes=15)

path = folder / "measurements.db"
path.unlink(missing_ok=True)
connection = database.connect(path)
inserted = database.insert_rows(connection, rows)
connection.close()
print(f"{inserted} rows inserted in {path}")
