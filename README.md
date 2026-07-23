# PAWS — Personal Autonomous Weather Station <img src="docs/assets/images/logo.svg" alt="PAWS logo" width="40" align="center"/>

Low-powered ESP32 IoT weather station — SD card logging, RTC timekeeping, direct Wi-Fi upload, phone-based fallback data gateway, time-series database, online dashboard and weather forecasting.

> 🌻 *And yes, that's a sunflower. A sunflower watches the sun. This weather station watches the weather. Close enough.*

## Documentation

Full design documentation (architecture, hardware, firmware, backend, ML) is available here: [personal-autonomous-weather-station](https://wg1d.github.io/personal-autonomous-weather-station/)

## Roadmap

The primary goal of this project is to build a full, end-to-end **Proof of Concept (PoC)**, spanning from initial data collection (Phase 1) up through basic Machine Learning forecasting (Phase 6). Once this core foundation is proven, the remaining items are logged as optional future ideas to expand the station over time.

| Phase | Name | Key addition | Status |
|-------|------|-------------|--------|
| 1 | Core Functionality | Temp/pressure/humidity sensor + SD logging + RTC timekeeping | 🟢 Done |
| 2 | Power Management | ESP32 deep sleep + peripheral power cycling + RTC alarms | 🟢 Done |
| 3 | Wi-Fi & Data Transmission | ESP32 automated Wi-Fi push + phone-based gateway fallback | 🟡 In progress |
| 4 | Firmware Architecture | State machine design + code refactoring (splitting into .h/.cpp) | ⬜ Planned |
| 5 | Backend MVP | SBC deployment + time-series database + online dashboard | ⬜ Planned |
| 6 | Forecasting — basic | LSTM on temp/pressure/humidity | ⬜ Planned |
| 7 | Sensors: BH1750 + VEML6075 | Light + UV sensors | 💭 Idea |
| 8 | Sensor: Soil moisture | Capacitive sensor | 💭 Idea |
| 9 | Sensor: Rain gauge | Tipping bucket | 💭 Idea |
| 10 | Sensor: Wind | Anemometer + wind vane | 💭 Idea |
| 11 | Model retrain + watering | Expanded LSTM + Random Forest watering model | 💭 Idea |
| 12 | Power: Solar + battery | Solar panel + battery monitoring | 💭 Idea |
| 13 | Stevenson screen + outdoor deployment | Final assembly into a Stevenson screen | 💭 Idea |


## Related projects

- [3D-PAWS](https://3dpaws.comet.ucar.edu/) (UCAR/COMET) — *3D-Printed Automatic Weather Station*: An open-source, low-cost weather station with 3D-printed sensor housings.

## License

MIT — see [LICENSE](LICENSE)
