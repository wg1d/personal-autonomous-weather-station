# Firmware

ESP32 firmware for the weather station.

**Status:** planned — Phase 1 (prototype) and Phase 2 (clean board).

## Structure (planned)

```
firmware/
├── src/
│   ├── main.cpp
│   ├── fsm/
│   │   ├── data_logger.cpp
│   │   ├── server.cpp
│   │   └── init_rtc.cpp
│   ├── drivers/
│   │   ├── rtc.cpp
│   │   ├── sensors.cpp
│   │   ├── sd_logger.cpp
│   │   └── pulse.cpp
│   ├── config.h          ← gitignored (copy from config.h.example)
│   └── config.h.example  ← template — commit this, not config.h
├── platformio.ini
└── README.md
```

## Configuration

`config.h` is gitignored to prevent committing credentials. Before building:

```bash
cp src/config.h.example src/config.h
# then edit config.h with your Wi-Fi SSID, password, and backend address
```

## Hardware target

- ESP32 WROVER (Upesy DevKit v2.1)
- Toolchain: PlatformIO + Arduino framework

## See also

Full hardware and firmware design: [docs/](../docs/)
