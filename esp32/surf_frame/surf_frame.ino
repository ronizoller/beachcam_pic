/*
 * Surf E-Ink Frame - ESP32 Firmware
 *
 * Wakes from deep sleep, fetches beach image from Pi server,
 * displays on Waveshare 7.3" color E-Ink, goes back to sleep.
 *
 * Hardware:
 * - ESP32 DevKitC
 * - Waveshare 7.3" ACeP 7-Color E-Ink Display (800x480)
 *
 * Libraries needed (install via Arduino Library Manager):
 * - GxEPD2 by Jean-Marc Zingg
 * - Adafruit GFX Library
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <GxEPD2_7C.h>  // 7-color e-paper
#include <Adafruit_GFX.h>
#include <time.h>
#include "credentials.h"

// ============== CONFIGURATION ==============

// Pi server address (change to your Pi's IP)
const char* SERVER_URL = "http://192.168.1.100:8080/image";

// Deep sleep duration (30 minutes = 1800 seconds)
#define SLEEP_MINUTES 30
#define uS_TO_S_FACTOR 1000000ULL

// WiFi timeout (seconds)
#define WIFI_TIMEOUT 30

// Active hours (skip updates at night to save battery)
#define ACTIVE_HOUR_START 6   // 6:00 AM
#define ACTIVE_HOUR_END 20    // 8:00 PM
#define TIMEZONE_OFFSET 3     // Israel = UTC+3 (adjust for daylight saving)

// ============== E-INK DISPLAY PINS ==============
// Waveshare 7.3" connected to ESP32 via SPI
// Adjust these pins based on your wiring!

#define EPD_CS    5    // Chip Select
#define EPD_DC    17   // Data/Command
#define EPD_RST   16   // Reset
#define EPD_BUSY  4    // Busy

// Display: Waveshare 7.3" 6-color Spectra 6 (800x480)
// GxEPD2_730c_GDEY073D46 for 6-color 7.3" display
GxEPD2_7C<GxEPD2_730c_GDEY073D46, GxEPD2_730c_GDEY073D46::HEIGHT> display(
    GxEPD2_730c_GDEY073D46(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY)
);

// ============== GLOBAL VARIABLES ==============

RTC_DATA_ATTR int bootCount = 0;  // Survives deep sleep

// ============== SETUP ==============

void setup() {
    Serial.begin(115200);
    delay(100);

    bootCount++;
    Serial.println("\n\n=================================");
    Serial.printf("Surf E-Ink Frame - Boot #%d\n", bootCount);
    Serial.println("=================================\n");

    // Initialize display
    Serial.println("Initializing display...");
    display.init(115200);
    display.setRotation(0);  // Landscape

    // Connect to WiFi
    if (!connectWiFi()) {
        Serial.println("WiFi failed, going to sleep...");
        goToSleep();
        return;
    }

    // Sync time and check if within active hours
    syncTime();
    if (!isActiveTime()) {
        Serial.println("Outside active hours, sleeping until morning...");
        goToSleepUntilMorning();
        return;
    }

    // Fetch and display image
    if (fetchAndDisplayImage()) {
        Serial.println("Success! Image displayed.");
    } else {
        Serial.println("Failed to fetch/display image.");
        displayError("Failed to load image");
    }

    // Disconnect WiFi to save power
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);

    // Go to deep sleep
    goToSleep();
}

void loop() {
    // Never reached - ESP32 resets after deep sleep
}

// ============== WIFI ==============

bool connectWiFi() {
    Serial.printf("Connecting to WiFi: %s\n", WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < WIFI_TIMEOUT * 2) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected!");
        Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
        return true;
    }

    Serial.println("\nWiFi connection failed!");
    return false;
}

// ============== IMAGE FETCH & DISPLAY ==============

bool fetchAndDisplayImage() {
    Serial.printf("Fetching image from: %s\n", SERVER_URL);

    HTTPClient http;
    http.begin(SERVER_URL);
    http.setTimeout(30000);  // 30 second timeout

    int httpCode = http.GET();

    if (httpCode != HTTP_CODE_OK) {
        Serial.printf("HTTP error: %d\n", httpCode);
        http.end();
        return false;
    }

    int contentLength = http.getSize();
    Serial.printf("Image size: %d bytes\n", contentLength);

    // Get stream
    WiFiClient* stream = http.getStreamPtr();

    // Read BMP header (54 bytes for standard BMP)
    uint8_t header[54];
    if (stream->readBytes(header, 54) != 54) {
        Serial.println("Failed to read BMP header");
        http.end();
        return false;
    }

    // Parse BMP header
    if (header[0] != 'B' || header[1] != 'M') {
        Serial.println("Not a valid BMP file");
        http.end();
        return false;
    }

    int32_t width = *(int32_t*)&header[18];
    int32_t height = *(int32_t*)&header[22];
    uint16_t bpp = *(uint16_t*)&header[28];
    uint32_t dataOffset = *(uint32_t*)&header[10];

    Serial.printf("BMP: %dx%d, %d bpp, offset %d\n", width, height, bpp, dataOffset);

    // Skip to pixel data if needed
    if (dataOffset > 54) {
        uint8_t skip[dataOffset - 54];
        stream->readBytes(skip, dataOffset - 54);
    }

    // Display the image
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
        drawBmpFromStream(stream, width, height, bpp);
    } while (display.nextPage());

    http.end();
    Serial.println("Image displayed!");
    return true;
}

void drawBmpFromStream(WiFiClient* stream, int32_t width, int32_t height, uint16_t bpp) {
    // BMP is stored bottom-to-top, so we read and flip
    int rowSize = ((width * bpp / 8) + 3) & ~3;  // Rows padded to 4 bytes
    uint8_t rowBuffer[rowSize];

    // BMP stores bottom row first
    bool flipVertical = (height > 0);
    height = abs(height);

    for (int y = 0; y < height; y++) {
        if (stream->readBytes(rowBuffer, rowSize) != rowSize) {
            Serial.printf("Failed reading row %d\n", y);
            break;
        }

        int destY = flipVertical ? (height - 1 - y) : y;

        for (int x = 0; x < width; x++) {
            uint8_t r, g, b;

            if (bpp == 24) {
                // BGR format in BMP
                b = rowBuffer[x * 3];
                g = rowBuffer[x * 3 + 1];
                r = rowBuffer[x * 3 + 2];
            } else if (bpp == 32) {
                b = rowBuffer[x * 4];
                g = rowBuffer[x * 4 + 1];
                r = rowBuffer[x * 4 + 2];
            } else {
                continue;  // Unsupported format
            }

            // Map RGB to 7-color E-Ink palette
            uint16_t color = rgbToEinkColor(r, g, b);
            display.drawPixel(x, destY, color);
        }
    }
}

uint16_t rgbToEinkColor(uint8_t r, uint8_t g, uint8_t b) {
    // Map RGB to nearest 6-color E-Ink color (Spectra 6)
    // Colors: Black, White, Blue, Red, Yellow, Green
    // Pi already quantized, so we detect which palette color

    int brightness = (r + g + b) / 3;

    // Black
    if (brightness < 50) return GxEPD_BLACK;

    // White
    if (brightness > 200 && abs(r - g) < 30 && abs(g - b) < 30) return GxEPD_WHITE;

    // Blue (high blue, low red) - ocean and sky
    if (b > 120 && b > r + 20) return GxEPD_BLUE;

    // Red (high red, low green/blue)
    if (r > 150 && r > g + 50 && r > b + 50) return GxEPD_RED;

    // Yellow/Sand (high red + green, low blue)
    if (r > 150 && g > 120 && b < 150) return GxEPD_YELLOW;

    // Green (rare in beach scenes)
    if (g > r && g > b && g > 100) return GxEPD_GREEN;

    // Default: white or black based on brightness
    if (brightness > 128) return GxEPD_WHITE;
    return GxEPD_BLACK;
}

// ============== ERROR DISPLAY ==============

void displayError(const char* message) {
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
        display.setTextColor(GxEPD_BLACK);
        display.setTextSize(2);
        display.setCursor(50, 200);
        display.print("Surf Frame Error:");
        display.setCursor(50, 240);
        display.print(message);
        display.setCursor(50, 300);
        display.printf("Boot #%d", bootCount);
    } while (display.nextPage());
}

// ============== TIME & SLEEP ==============

void syncTime() {
    Serial.println("Syncing time via NTP...");
    configTime(TIMEZONE_OFFSET * 3600, 0, "pool.ntp.org", "time.nist.gov");

    // Wait for time to sync
    int attempts = 0;
    while (time(nullptr) < 100000 && attempts < 20) {
        delay(500);
        attempts++;
    }

    time_t now = time(nullptr);
    struct tm* timeinfo = localtime(&now);
    Serial.printf("Current time: %02d:%02d\n", timeinfo->tm_hour, timeinfo->tm_min);
}

bool isActiveTime() {
    time_t now = time(nullptr);
    struct tm* timeinfo = localtime(&now);
    int hour = timeinfo->tm_hour;

    Serial.printf("Hour: %d (active: %d-%d)\n", hour, ACTIVE_HOUR_START, ACTIVE_HOUR_END);
    return (hour >= ACTIVE_HOUR_START && hour < ACTIVE_HOUR_END);
}

void goToSleepUntilMorning() {
    time_t now = time(nullptr);
    struct tm* timeinfo = localtime(&now);
    int hour = timeinfo->tm_hour;
    int minute = timeinfo->tm_min;

    // Calculate minutes until ACTIVE_HOUR_START
    int minutesUntilMorning;
    if (hour >= ACTIVE_HOUR_END) {
        // Evening: sleep until next morning
        minutesUntilMorning = (24 - hour + ACTIVE_HOUR_START) * 60 - minute;
    } else {
        // Early morning: sleep until start hour
        minutesUntilMorning = (ACTIVE_HOUR_START - hour) * 60 - minute;
    }

    Serial.printf("Sleeping for %d minutes until %d:00\n", minutesUntilMorning, ACTIVE_HOUR_START);

    esp_sleep_enable_timer_wakeup(minutesUntilMorning * 60 * uS_TO_S_FACTOR);
    esp_deep_sleep_start();
}

void goToSleep() {
    Serial.printf("\nGoing to deep sleep for %d minutes...\n", SLEEP_MINUTES);
    Serial.println("Goodnight!\n");

    esp_sleep_enable_timer_wakeup(SLEEP_MINUTES * 60 * uS_TO_S_FACTOR);
    esp_deep_sleep_start();
}
