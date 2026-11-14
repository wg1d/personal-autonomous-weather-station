"""
Project: Personal Autonomous Weather Station
File: backend/paws/dev/make_test_data.py

Description:
Fills a database with made-up measurements, one row every 15 minutes over
several years, to try the dashboard on the development computer without
waiting for the station. The values follow the seasons and the hours of
the day, with some noise. The battery charges with the sun of the day,
less in winter and under clouds, and the station draws from it at night.

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
# The charge of the battery, from 0 (empty) to 1 (full), and the clouds of
# the day, from 0.2 (overcast) to 1 (clear)
charge = 0.9
clouds = 1.0
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
    # The sun: highest at 13:00 in UTC, higher and longer in summer; new
    # clouds each morning
    if time.hour == 6 and time.minute == 0:
        clouds = random.uniform(0.2, 1.0)
    noon = math.cos(2 * math.pi * (time.hour + time.minute / 60 - 13) / 24)
    light = max(0.0, noon + 0.25 * season) * clouds
    # The panel charges the battery, up to about 200 mA, until it is full,
    # and powers the station itself; at night, the station draws about
    # 0.5 mA on average from the battery
    current = 200 * light if charge < 0.999 else 0.0
    charge = min(1.0, charge + (current - (0 if light else 0.5))
                 * 0.25 / 1000)
    # The station measures while it is awake: without sun, the battery
    # gives it about 50 mA. Its voltage follows its charge, from about
    # 3.6 V nearly empty to 4.2 V full
    measured = current if light else -50 + random.gauss(0, 2)
    voltage = 3.6 + 0.6 * charge + random.gauss(0, 0.005)
    rows.append((time.strftime(TIMESTAMP_FORMAT), 1, round(temperature, 2),
                 round(min(humidity, 100), 2), round(pressure, 2),
                 round(voltage, 2), round(measured, 2)))
    time += timedelta(minutes=15)

path = folder / "measurements.db"
path.unlink(missing_ok=True)
connection = database.connect(path)
inserted = database.insert_rows(connection, rows)
connection.close()
print(f"{inserted} rows inserted in {path}")
