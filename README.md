# PAWS — Personal Autonomous Weather Station <img src="docs/assets/images/logo.svg" alt="PAWS logo" width="40" align="center"/>

Low-powered ESP32 IoT weather station — SD card logging, RTC timekeeping, direct Wi-Fi upload, phone-based fallback data gateway, time-series database, online dashboard and weather forecasting.

> 🌻 *And yes, that's a sunflower. A sunflower watches the sun. This weather station watches the weather. Close enough.*

## Documentation

Full design documentation (architecture, hardware, firmware, backend, ML) is available here: [personal-autonomous-weather-station](https://wg1d.github.io/personal-autonomous-weather-station/)

## Development setup

All the tools (PlatformIO, Quarto, the C++ compiler, Python and the backend dependencies) are installed by [pixi](https://pixi.sh), with the exact versions frozen in `pixi.lock`. The CI uses the same environment, so a build that works locally works in the CI.

### 1. Install pixi

Follow the [official instructions](https://pixi.sh/latest/#installation). On Linux and macOS:

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Then, from the root of the repository, install the environments (optional: `pixi run` also installs them on first use):

```bash
pixi install --all
```

### 2. Available commands

```bash
pixi run build-firmware   # build every PlatformIO project
pixi run book             # generate the book in docs/_output
pixi run preview          # live preview of the book in the browser
pixi run dummy-server     # start the Phase 3 dummy backend server
```

The first build downloads the ESP32 toolchain into `.pio-core/` (about 1.5 GB), inside the repository, so it does not interfere with an existing `~/.platformio`.

### 3. Flash the ESP32

Every PlatformIO command works through pixi. For example, to flash a sketch and open the serial monitor:

```bash
pixi run pio run -d firmware/PoC/Phase-01/01_data_acquisition -t upload
pixi run pio device monitor -b 115200
```

The Wi-Fi sketches read their credentials from a git-ignored `secrets.h`: copy `secrets.example.h` to `secrets.h` in the sketch folder and fill in your values. If `secrets.h` is missing, `pixi run build-firmware` creates it from the example, with placeholder values that only allow the sketch to compile.

### Environments

`pixi.toml` defines two environments:

- `default`: the development tools (PlatformIO, Quarto, C++ compiler);
- `backend`: Python and the backend dependencies. It is separate because PlatformIO requires an old version of `uvicorn` that recent FastAPI versions cannot use.

Each task runs in the right environment automatically.

### Not managed by pixi

Regenerating the wiring diagrams requires a LaTeX distribution with `circuitikz`, `latexmk` and `pdf2svg` (see `docs/assets/diagrams-src/Makefile`). This is only needed when a diagram changes.

## Roadmap

The primary goal of this project is to build a full, end-to-end **Proof of Concept (PoC)**, spanning from initial data collection (Phase 1) up through basic Machine Learning forecasting (Phase 6). Once this core foundation is proven, the remaining items are logged as optional future ideas to expand the station over time.

| Phase | Name | Key addition | Status |
|-------|------|-------------|--------|
| 1 | Core Functionality | Temp/pressure/humidity sensor + SD logging + RTC timekeeping | 🟢 Done |
| 2 | Power Management | ESP32 deep sleep + peripheral power cycling + RTC alarms | 🟢 Done |
| 3 | Wi-Fi & Data Transmission | ESP32 automated Wi-Fi push + phone-based gateway fallback | 🟢 Done |
| 4 | Firmware Architecture | State machine design + modular firmware rewrite with host tests | 🟡 In progress |
| 5 | Backend MVP | SBC deployment + time-series database + online dashboard | 🟡 In progress |
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
