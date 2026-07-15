/*
 * 01_button_led
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept: 
 * This sketch demonstrates standard digital input and output on the ESP32.
 * It reads a push button connected to GPIO 39 (VN pin) and controls the
 * built-in blue LED on GPIO 2.
 * 
 * Hardware Layout:
 * - Built-in LED on GPIO 2.
 * - Push Button on GPIO 39 with an external 10k resistor pulling the pin to 3.3V.
 *   - When the button is open (released), GPIO 39 is pulled HIGH (3.3V).
 *   - When the button is closed (pressed), GPIO 39 is connected to GND (LOW).
 *   - This is an "active-low" configuration.
 */

#include <Arduino.h>

// Pin Definitions
#define LED_PIN 2       // Onboard blue LED on the uPesy WROVER DevKit
#define BUTTON_PIN 39   // GPIO 39 (VN pin) connected to the push button

// Button State Definitions (Active-High button circuit: HIGH when pressed, LOW when released)
#define BUTTON_PRESSED  HIGH
#define BUTTON_RELEASED LOW

// LED State definitions (Onboard LED is active-high: HIGH turns it ON, LOW turns it OFF)
#define LED_ON  HIGH
#define LED_OFF LOW

// Track the previous state to log changes to the Serial monitor only on transitions
int lastButtonState = BUTTON_RELEASED;

void setup() {
  // Initialize Serial Monitor
  Serial.begin(115200);
  while (!Serial) {
    delay(10); // Wait for Serial port to open
  }

  Serial.println("==================================================");
  Serial.println("PAWS Step 01: Button & LED (Pull-Up/Pull-Down)");
  Serial.println("==================================================");

  // Configure LED pin as OUTPUT
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LED_OFF); // Start with LED OFF

  // Configure Button pin as INPUT
  pinMode(BUTTON_PIN, INPUT);

  Serial.println("Setup complete. GPIO 39 is pulled LOW/HIGH based on configuration.");
  Serial.println("Press the button to toggle the LED.");
}

void loop() {
  // Read current physical button state
  int buttonState = digitalRead(BUTTON_PIN);

  // Detect state change
  if (buttonState != lastButtonState) {
    lastButtonState = buttonState;

    if (buttonState == BUTTON_PRESSED) {
      // Button is pressed
      Serial.println("Button Pressed (HIGH) -> LED ON");
      digitalWrite(LED_PIN, LED_ON);
    } else {
      // Button is released
      Serial.println("Button Released (LOW) -> LED OFF");
      digitalWrite(LED_PIN, LED_OFF);
    }
  }

  // Small debounce delay
  delay(20);
}
