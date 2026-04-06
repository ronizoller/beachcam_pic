# ESP32 Surf Frame Firmware

## Setup Instructions

### 1. Install Arduino IDE
Download from: https://www.arduino.cc/en/software

### 2. Add ESP32 Board Support
1. Open Arduino IDE → Preferences
2. Add to "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Tools → Board → Board Manager → Search "ESP32" → Install

### 3. Install Libraries
Tools → Manage Libraries → Install:
- **GxEPD2** by Jean-Marc Zingg
- **Adafruit GFX Library**

### 4. Configure Credentials
Edit `credentials.h` with your WiFi:
```cpp
const char* WIFI_SSID = "YourWiFiName";
const char* WIFI_PASSWORD = "YourPassword";
```

### 5. Configure Server IP
In `surf_frame.ino`, change the Pi server IP:
```cpp
const char* SERVER_URL = "http://YOUR_PI_IP:8080/image";
```

### 6. Wiring (ESP32 → Waveshare 7.3")

| ESP32 Pin | E-Ink Pin | Color  |
|-----------|-----------|--------|
| 3.3V      | VCC       | Red    |
| GND       | GND       | Black  |
| GPIO 5    | CS        | Orange |
| GPIO 18   | CLK       | Yellow |
| GPIO 23   | DIN       | Blue   |
| GPIO 17   | DC        | Green  |
| GPIO 16   | RST       | White  |
| GPIO 4    | BUSY      | Purple |

### 7. Upload
1. Select Board: Tools → Board → ESP32 Dev Module
2. Select Port: Tools → Port → (your ESP32)
3. Click Upload

### 8. Test
- Open Serial Monitor (115200 baud)
- ESP32 will connect to WiFi, fetch image, display it, then sleep
- Wakes every 30 minutes

## Troubleshooting

**WiFi won't connect:**
- Check SSID/password in credentials.h
- Make sure Pi and ESP32 are on same network

**Display shows nothing:**
- Check wiring connections
- Verify display model matches code

**Image looks wrong:**
- Pi server must be running (`python main.py`)
- Check SERVER_URL is correct Pi IP
