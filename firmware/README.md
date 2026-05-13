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
│   └── config.h          ← gitignored (contains Wi-Fi credentials)
├── platformio.ini
└── README.md
```

## Hardware target

- ESP32 WROVER (Upesy DevKit v2.1)
- Toolchain: PlatformIO + Arduino framework

## See also

Full hardware and firmware design: [docs/](../docs/)
