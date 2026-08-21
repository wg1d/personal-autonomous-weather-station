#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// --- PIN DEFINITIONS ---
#define SD_CS_PIN 5
#define SD_OFF_PIN 13
#define RTC_WAKEUP_PIN 36
#define FALLBACK_BUTTON_PIN 39

// --- TIMINGS & SETTINGS ---
const int WAKEUP_INTERVAL_SECONDS = 30; // Normal measurement interval

// Sync hour (0-23) at which the station should upload data and sync NTP
// For example, 2 means 2:00 AM.
const int WIFI_SYNC_HOUR = 2; 

// The backend server endpoint to upload the CSV data
const char* const SERVER_ENDPOINT = "http://192.168.1.15:5000/upload";

// Fallback AP Mode timeout (in milliseconds)
const unsigned long AP_TIMEOUT_MS = 180000; // 3 minutes

#endif // CONFIG_H
