# PAWS — Personal Autonomous Weather Station <img src="docs/assets/images/logo.svg" alt="PAWS logo" width="40" align="center"/>

> Low-powered ESP32 weather station — SD card logging, RTC timekeeping, phone-based data gateway, time-series database, online dashboard and weather forecasting.

A learning-oriented project covering the full stack: embedded firmware, solar power, asynchronous data pipeline, and machine learning on local sensor data.

> 🌻 *Yes, that's a sunflower. It watches the sun. This station watches the weather. Close enough.*

## Documentation

Full design documentation (architecture, hardware, firmware, backend, ML): [personal-autonomous-weather-station](https://wg1d.github.io/personal-autonomous-weather-station/)

## Roadmap

| Phase | Name | Key addition | Status |
|-------|------|-------------|--------|
| 1 | Prototype | Core FSM + SD logging | 🟡 In progress |
| 2 | Backend MVP | Odroid C4 + gateway + dashboard (no forecasting) | ⬜ Planned |
| 3 | Clean board | Plug-and-play connectors + new sensors | ⬜ Planned |
| 4 | Outdoor | Stevenson screen deployment | ⬜ Planned |
| 5 | Extended sensors | Rain gauge + wind | ⬜ Planned |
| 6 | Forecasting | RF watering + LSTM weather | ⬜ Planned |
| 7 | Solar + air quality | Autonomy + PM2.5 | ⬜ Planned |
| 8 | Wi-Fi push | Station uploads directly, no gateway | ⬜ Planned |
| 9 | Cellular push | GSM/LTE for remote deployments | ⬜ Planned |

See [ROADMAP.md](ROADMAP.md) for detailed per-phase deliverables, hardware lists, and exit criteria.

```mermaid
flowchart TD
    P1[Phase 1: Prototype] --> P2[Phase 2: Backend MVP]
    P2 --> P3[Phase 3: Clean board]
    P3 --> P4[Phase 4: Outdoor]
    P4 --> P5[Phase 5: Wind + Rain]
    P5 --> P6[Phase 6: Forecasting]
    P4 --> P7[Phase 7: Solar + Air quality]
    P4 --> P8[Phase 8: Wi-Fi push]
    P8 --> P9[Phase 9: Cellular push]
```

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
