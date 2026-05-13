<img src="docs/assets/images/logo.svg" alt="PAWS logo" width="80" align="right"/>

# PAWS — Personal Autonomous Weather Station

> Low-powered ESP32 weather station — SD card logging, RTC timekeeping, phone-based data gateway, time-series database, online dashboard and weather forecasting.

A learning-oriented project covering the full stack: embedded firmware, solar power, asynchronous data pipeline, and machine learning on local sensor data.

## Documentation

Full design documentation (architecture, hardware, firmware, backend, ML): [personal-autonomous-weather-station](https://wg1d.github.io/personal-autonomous-weather-station/)

## Related projects

- [3D-PAWS](https://3dpaws.comet.ucar.edu/) (UCAR/COMET) — *3D-Printed Automatic Weather Station*: open-source low-cost weather station with 3D-printed sensor housings.

## Project structure

| Folder | Contents |
|--------|----------|
| `docs/` | Quarto book — design & architecture documentation |
| `firmware/` | ESP32 firmware (PlatformIO / Arduino IDE) — SD logging, RTC, data gateway |
| `backend/` | SBC (Single-Board Computer, e.g. Raspberry Pi, Odroid) server — FastAPI, data pipeline, time-series DB, ML models |

## License

MIT — see [LICENSE](LICENSE)
