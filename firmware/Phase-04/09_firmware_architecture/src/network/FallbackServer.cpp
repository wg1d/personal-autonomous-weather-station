#include "FallbackServer.h"

FallbackServer::FallbackServer() : _server(80) {}

void FallbackServer::start(SDManager& sd) {
    Serial.println("Starting Fallback AP Mode...");
    
    // Delegate power management to SDManager
    if (!sd.beginSession()) {
        Serial.println("Error: Card Mount Failed in AP mode");
    }
    
    // Start Wi-Fi Access Point
    WiFi.softAP("WeatherStation_AP", "12345678");
    Serial.print("AP IP address: ");
    Serial.println(WiFi.softAPIP());
    
    setupRoutes(sd);
    
    _server.begin();
    Serial.println("Web server started.");
}

void FallbackServer::stop(SDManager& sd) {
    _server.end();
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_OFF);
    
    // Safely power off the SD card when done
    sd.endSession();
}

void FallbackServer::setupRoutes(SDManager& sd) {
    _server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
        String html = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
        html += "<style>body{font-family:Arial,sans-serif;text-align:center;padding:50px;}";
        html += "button{padding:15px 30px;font-size:18px;margin:10px;cursor:pointer;border:none;border-radius:8px;}";
        html += ".btn-down{background:#4CAF50;color:white;} .btn-del{background:#f44336;color:white;}</style></head>";
        html += "<body><h1>Weather Station</h1>";
        html += "<a href='/download'><button class='btn-down'>Download CSV</button></a><br><br>";
        html += "<form action='/delete' method='POST'><button type='submit' class='btn-del'>Delete Old Data</button></form>";
        html += "</body></html>";
        request->send(200, "text/html", html);
    });
    
    // We capture a pointer to sd so the lambda can use it.
    // However, capturing local variables in ESPAsyncWebServer lambdas is tricky because
    // it requires std::function if capturing. Since ESPAsyncWebServer supports capturing lambdas,
    // we must capture `&sd`.
    
    _server.on("/download", HTTP_GET, [&sd](AsyncWebServerRequest *request){
        if(!sd.getFS().exists("/weather_data.csv")) {
            request->send(404, "text/plain", "File not found.");
            return;
        }
        Serial.println("User is downloading weather_data.csv...");
        request->send(sd.getFS(), "/weather_data.csv", "text/csv", true);
    });
    
    _server.on("/delete", HTTP_POST, [&sd](AsyncWebServerRequest *request){
        if(sd.getFS().exists("/weather_data.csv")) {
            sd.getFS().remove("/weather_data.csv");
            Serial.println("User deleted weather_data.csv!");
        }
        request->send(200, "text/html", "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{font-family:Arial,text-align:center;padding:50px;}</style></head><body><h2>Data Deleted!</h2><a href='/'>Back</a></body></html>");
    });
}
