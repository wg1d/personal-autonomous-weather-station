/*
 * Project: Personal Autonomous Weather Station
 * File: include/secrets.example.h
 *
 * Description:
 * Example of the settings that must not be published: copy this file
 * to secrets.h (ignored by Git) and replace the values with yours.
 * pixi run build-firmware creates secrets.h from this file when it is
 * missing, so that the firmware builds (but cannot connect).
 *
 * Dependencies: none.
 */

#pragma once

/// Name of the home Wi-Fi network
const char kWifiSsid[] = "YOUR_WIFI_SSID";

/// Password of the home Wi-Fi network
const char kWifiPassword[] = "YOUR_WIFI_PASSWORD";

/// Address of the server that receives the rows: the IP address of the
/// computer running the test server, on the home network
const char kServerUrl[] = "http://192.168.1.15:8080/api/v1/measurements";
