#ifndef FALLBACKSERVER_H
#define FALLBACKSERVER_H

#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include "../storage/SDManager.h"
#include "../config.h"

/**
 * @class FallbackServer
 * @brief Handles the Fallback AP Mode, spinning up an Access Point and web server.
 */
class FallbackServer {
public:
    FallbackServer();
    
    /**
     * @brief Starts the AP and the Async Web Server.
     * @param sd Reference to the SDManager for serving files.
     */
    void start(SDManager& sd);
    
    /**
     * @brief Stops the server, AP, and safely powers down the SD card.
     * @param sd Reference to the SDManager to stop the session.
     */
    void stop(SDManager& sd);

private:
    AsyncWebServer _server;
    void setupRoutes(SDManager& sd);
};

#endif // FALLBACKSERVER_H
