/*
 * 02_button_wakeup
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept:
 * Microcontrollers like the ESP32 must enter Deep Sleep to conserve battery.
 * In deep sleep, the CPU, Wi-Fi, and main RAM are powered down.
 * 
 * Wakeup states and variables:
 * - Boot count is stored in RTC slow memory using RTC_DATA_ATTR to survive deep sleep.
 * - External wakeup EXT1 monitors GPIO 39. When the button is pressed, pulling the
 *   pin to GND (LOW), the RTC controller detects it and wakes up the ESP32.
 * 
 * Hardware Layout:
 * - Built-in LED on GPIO 2 (turned ON briefly during boot, then OFF when going to sleep).
 * - Push Button on GPIO 39 with external 10k resistor pulling it to 3.3V.
 */

#include <Arduino.h>

#define LED_PIN 2       // uPesy WROVER DevKit onboard LED
#define BUTTON_PIN 39   // Push button GPIO

// Variable stored in RTC slow memory (persists across deep sleep cycles)
RTC_DATA_ATTR int bootCount = 0;

void printWakeupReason() {
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();

  switch (wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT1:
      Serial.println("Wakeup caused by external signal using RTC_CNTL (EXT1 - Button on GPIO 39)");
      break;
    case ESP_SLEEP_WAKEUP_EXT0:
      Serial.println("Wakeup caused by external signal using RTC_IO (EXT0)");
      break;
    case ESP_SLEEP_WAKEUP_TIMER:
      Serial.println("Wakeup caused by timer");
      break;
    default:
      Serial.printf("Wakeup not caused by deep sleep (%d)\n", wakeup_reason);
      break;
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(1000); // Give the Serial monitor time to connect

  // Increment and display the boot counter
  bootCount++;

  Serial.println("==================================================");
  Serial.println("PAWS Step 02: Button Wakeup (Deep Sleep EXT1)");
  Serial.println("==================================================");
  Serial.printf("Boot number: %d\n", bootCount);

  // Print the wakeup reason
  printWakeupReason();

  // Turn ON the onboard LED to signal the ESP32 is awake
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  delay(2000); // Keep it ON for 2 seconds so we can see it

  // Configure Button Pin
  pinMode(BUTTON_PIN, INPUT);

  // Configure EXT1 wakeup on GPIO 39
  // EXT1 requires a bitmask of the chosen pins: 1ULL << pin_number
  uint64_t pinMask = 1ULL << BUTTON_PIN;
  
  // Set wakeup trigger: when the pin goes LOW (button pressed)
  esp_sleep_enable_ext1_wakeup(pinMask, ESP_EXT1_WAKEUP_ALL_LOW);

  Serial.println("Entering Deep Sleep now...");
  Serial.println("Press the button (GPIO 39 to GND) to wake me up.");
  Serial.flush(); // Wait for Serial messages to finish sending

  // Turn off the LED and enter Deep Sleep
  digitalWrite(LED_PIN, LOW);
  esp_deep_sleep_start();
}

void loop() {
  // loop() is never reached because the ESP32 goes to deep sleep in setup()
}
