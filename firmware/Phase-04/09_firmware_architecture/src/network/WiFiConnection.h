#ifndef WIFICONNECTION_H
#define WIFICONNECTION_H

#include <Arduino.h>
#include <WiFi.h>
#include "../secrets.h"

/**
 * @class WiFiConnection
 * @brief Manages connection to the local Wi-Fi router.
 */
class WiFiConnection {
public:
    WiFiConnection();
    
    /**
     * @brief Attempts to connect to the Wi-Fi using SECRETS_H credentials.
     * @return true if successfully connected within timeout.
     */
    bool connect();
    
    /**
     * @brief Disconnects and turns off the Wi-Fi modem.
     */
    void disconnect();
};

#endif // WIFICONNECTION_H
