/*
 * Project: Personal Autonomous Weather Station
 * Phase 02: Power Management
 * File: 04_deep_sleep_timer.ino
 * 
 * Description:
 * A simple "Hello Deep Sleep" example using the ESP32 internal timer.
 */

#include <Arduino.h>

// Conversion factor for micro seconds to seconds
#define uS_TO_S_FACTOR 1000000ULL  
#define TIME_TO_SLEEP  10          // Sleep for 10 seconds

void setup(){
  Serial.begin(115200);
  delay(1000); 
  
  Serial.println("\n--- Waking up! ---");
  Serial.println("Reading sensors (simulated)...");
  delay(500); // Simulate some work
  
  Serial.println("Going to sleep for 10 seconds.");
  Serial.flush(); 
  
  // Configure the timer wake-up
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  
  // Enter deep sleep
  esp_deep_sleep_start();
}

void loop(){
  // This is never reached because esp_deep_sleep_start() halts execution!
}
