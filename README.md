# PAWS — Personal Autonomous Weather Station

> Low-power ESP32 weather station with SD logging and phone-based gateway — feeds a Grafana dashboard and ML models for plant watering decisions and local weather forecasting.

A learning-oriented project covering the full stack: embedded firmware, solar power, asynchronous data pipeline, and machine learning on local sensor data.

## Documentation

Full design documentation (architecture, hardware, firmware, backend, ML): **https://\<owner\>.github.io/personal-autonomous-weather-station/**

## Related projects

- [3D-PAWS](https://3dpaws.comet.ucar.edu/) (UCAR/COMET) — *3D-Printed Automatic Weather Station*: open-source low-cost weather station with 3D-printed sensor housings. Useful reference for DIY rain gauge and anemometer designs.

## Project structure

| Folder | Contents |
|--------|----------|
| `docs/` | Quarto book — design & architecture documentation |
| `firmware/` | ESP32 firmware (PlatformIO / Arduino IDE) |
| `backend/` | Odroid C4 server — FastAPI, data pipeline, ML models |

## License

MIT — see [LICENSE](LICENSE)
