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
| 2 | Backend MVP | Odroid C4 + gateway + dashboard | ⬜ Planned |
| 3 | Forecasting — basic | LSTM on temp/pressure/humidity | ⬜ Planned |
| 4 | Sensors: BH1750 + VEML6075 | Light + UV, I²C/STEMMA QT | ⬜ Planned |
| 5 | Sensor: Soil moisture | Capacitive probe, ADC, calibration | ⬜ Planned |
| 6 | Sensor: Rain gauge | Tipping bucket, interrupt, pulse counting | ⬜ Planned |
| 7 | Sensor: Wind | Anemometer + wind vane | ⬜ Planned |
| 8 | Model retrain + watering | Expanded LSTM + Random Forest watering model | ⬜ Planned |
| 9 | Power: Solar + battery | MPPT + LiFePO₄, battery monitoring | ⬜ Planned |
| 10 | Stevenson screen + outdoor deployment | Final assembly into enclosure / Stevenson screen | ⬜ Planned |
| ◇ Optional | Wi-Fi push | Direct upload after each wake, no gateway | ⬜ Planned |
| ◇ Optional | Cellular | GSM/LTE for remote deployments | ⬜ Planned |

See [ROADMAP.md](ROADMAP.md) for detailed per-phase deliverables, hardware lists, and exit criteria.

```mermaid
flowchart TD
    P1[Phase 1: Prototype] --> P2[Phase 2: Backend MVP]
    P2 --> P3[Phase 3: Forecasting — basic]
    P3 --> P4[Phase 4: Sensors BH1750 + VEML6075]
    P4 --> P5[Phase 5: Sensor — Soil moisture]
    P5 --> P6[Phase 6: Sensor — Rain gauge]
    P6 --> P7[Phase 7: Sensor — Wind]
    P7 --> P8[Phase 8: Model retrain + watering]
    P8 --> P9[Phase 9: Power — Solar + battery]
    P9 --> P10[Phase 10: Stevenson screen + outdoor]
    P2 -. optional .-> OWifi[Wi-Fi push]
    P9 -. optional, before P10 .-> OCellular[Cellular]
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
