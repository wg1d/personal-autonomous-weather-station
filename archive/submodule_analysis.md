# Analysis of Previous Attempts (Submodules)

This document provides a detailed review of the `archive/sandbox_esp32` and `archive/weather-dashboard` submodules. It identifies what is functional, what is out-of-date, and how they align with the current weather station book specifications.

---

## 1. ESP32 Firmware Sandbox (`archive/sandbox_esp32`)

### 🟢 What is Nice & Worth Keeping
*   **Low-Level Interrupts:** The deep sleep entry (`esp_deep_sleep_start()`) and `EXT0` wake-up cause dispatch are correctly implemented.
*   **SD Power Gating:** The code in [main.cpp](file:///home/william/Documents/personal-autonomous-weather-station/archive/sandbox_esp32/rtc_interrupts/src/main.cpp#L239-L247) uses a digital control pin (`GPIO_NUM_13`) to cut power to the SD card reader between wakes. This is an excellent low-power design choice that prevents battery leakage and should be preserved in the book's hardware chapter.
*   **Alarm Maintenance:** The setup cleans and clears alarm flags on initialization (lines 224-235), avoiding common bugs where old alarm registers block the RTC interrupt pin from firing.

### 🔴 Out-of-Date / Disaligned Elements
*   **CSV Format Mismatch:** The firmware writes to `/wheather_data.csv` using a **semicolon (`;`)** separator and logs only 5 fields. The book's canonical schema standardizes on a **comma (`,`)** separator and 10 columns (supporting light, UV, soil, rain, wind speed, and wind direction).
*   **No Wi-Fi Sync Logic:** The code acts solely as a logging loop. It does not implement the `SERVER` mode logic (spinning up the ESP32 Access Point to serve a file download page via a browser).
*   **No Momentary Trigger:** The current code does not listen for a momentary button / reed switch on `EXT1` to wake up, which is a key part of the new battery-safe synchronization strategy.

---

## 2. Tinyflux & Dash UI (`archive/weather-dashboard`)

### 🟢 What is Nice & Worth Keeping
*   **Tinyflux & Plotly Integration:** This confirms the validity of using Tinyflux and Plotly Dash. The use of `make_subplots` to overlay Humidity, Pressure, and Temperature in a dark theme looks excellent and runs very fast.
*   **Dependency Management:** The [pixi.toml](file:///home/william/Documents/personal-autonomous-weather-station/archive/weather-dashboard/pixi.toml) configuration is a modern, reproducible way to manage Python dependencies.

### 🔴 Out-of-Date / Disaligned Elements
*   **Manual Upload Workflow:** The previous dashboard relies on a **manual CSV file upload button** (`dcc.Upload`). The current book strategy centers around automated ingestion (the station connects to Wi-Fi and pushes data directly via `POST /api/upload`, or updates on page load).
*   **Timezones:** The dashboard uses local timezones (`Europe/Paris`). The book standardizes strictly on **UTC** to avoid DST offsets and time authority mismatch between the RTC and the server.
*   **Outdated Libraries:** 
    *   `Tinyflux` is locked at `0.4.1` (the library has since progressed to `1.x.x` which introduced a redesigned query engine).
    *   `Dash` is locked at `2.16.1` (latest is `2.18+`).
*   **No REST API:** It does not expose FastAPI endpoints (such as `POST /api/upload` or prediction routes). It is a standalone Dash server.

---

## 💡 Migration & Integration Plan

To transition these previous attempts into the current book project:

1.  **Modularize Firmware:** Reorganize the code in [main.cpp](file:///home/william/Documents/personal-autonomous-weather-station/archive/sandbox_esp32/rtc_interrupts/src/main.cpp) into the modular folder structure (`src/`, `fsm/`, `drivers/`) described in Chapter 4, separating drivers (BME280, RTC, SD) into distinct files.
2.  **Add AP Server Mode:** Implement the web server logic on the ESP32 to serve a basic download webpage when triggered by the momentary button.
3.  **Transition Dashboard to FastAPI + Plotly:** Port the dashboard plotting logic. For the lightweight Pi Zero target, migrate from a standalone Dash server with manual uploads to a unified FastAPI server that exposes the REST API (`POST /api/upload`) and serves a client-side Plotly.js template. Tinyflux will remain the storage backend.
