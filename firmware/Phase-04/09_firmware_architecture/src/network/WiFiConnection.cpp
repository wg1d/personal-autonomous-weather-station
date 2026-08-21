#include "WiFiConnection.h"

WiFiConnection::WiFiConnection() {}

bool WiFiConnection::connect() {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to WiFi...");
    
    int wifi_timeout = 0;
    while (WiFi.status() != WL_CONNECTED && wifi_timeout < 20) {
        delay(500);
        Serial.print(".");
        wifi_timeout++;
    }

    if(WiFi.status() == WL_CONNECTED) {
        Serial.println("\nConnected to WiFi network");
        return true;
    } else {
        Serial.println("\nWiFi connection failed, aborting upload.");
        return false;
    }
}

void WiFiConnection::disconnect() {
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
}
