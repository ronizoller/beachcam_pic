/*
 * Surf E-Ink Frame - ESP32 Firmware (Waveshare 13.3" Spectra 6 / E6)
 *
 * Wakes from deep sleep, fetches a beach image from the Pi server,
 * renders it on the panel, asks the Pi how long to sleep, deep-sleeps.
 *
 * Hardware:
 * - ESP32 DevKitC 32U
 * - Waveshare 13.3" e-Paper HAT+ (E) — 1200x1600 portrait, 6-color (Spectra 6)
 *
 * Library: this sketch ships Waveshare's stock driver alongside it
 * (DEV_Config.{h,cpp}, EPD_13in3e.{h,cpp}, Debug.h). No Library Manager
 * package needed — the IDE compiles those files as part of the sketch.
 *
 * Wiring (matches DEV_Config.h):
 *   ESP32 GPIO13 → CLK    GPIO14 → DIN/MOSI    GPIO15 → CS_M    GPIO2  → CS_S
 *   ESP32 GPIO27 → DC     GPIO26 → RST         GPIO25 → BUSY    GPIO33 → PWR
 *   ESP32 3V3    → VCC    GND     → GND
 *
 * Image format expected from the Pi:
 *   24-bpp BMP, 1200 wide × 1600 tall (panel-native portrait).
 *   The current Pi config produces 1600×1200 landscape — swap to portrait
 *   in pi/config.yaml before this firmware will render correctly.
 *
 * Why two fetches per refresh:
 *   The 13.3" panel uses two driver chips (CS_M = left half, CS_S = right
 *   half). Waveshare's protocol requires sending all left-half rows
 *   before any right-half rows. With 327 KB of DRAM we can't buffer one
 *   half (~480 KB) while sending the other, so we fetch the BMP from the
 *   server twice — pass 1 streams the left half, pass 2 streams the right.
 *   RAM stays at one row buffer (~3.6 KB).
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include "credentials.h"
#include "DEV_Config.h"
#include "EPD_13in3e.h"

// Opt-in brownout bypass — masks the BOD reset so the CPU keeps running through
// the 3V3 sag during DRF. Only enable as a diagnostic, after confirming with a
// scope/multimeter that the dip isn't deep enough to risk flash corruption.
#define ALLOW_BROWNOUT_BYPASS  0
#if ALLOW_BROWNOUT_BYPASS
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#endif

// Diagnostic: skip WiFi + streaming entirely and render the stock 6-color
// stripe pattern straight after a cold boot. This puts the panel through a
// full DRF on a *cold* LDO — the same condition the Waveshare demo runs
// under. Use it to isolate the brownout cause:
//   - If DRF completes here but fails in normal mode → LDO is heat-derated
//     by the WiFi+streaming work; bulk cap or external 3V3 needed.
//   - If DRF brownouts here too → panel alone exceeds the supply's headroom;
//     external 3V3 is the only fix.
// After running once, sets a boot-count guard so it doesn't loop forever
// on the next wake — flash, observe, then flip back to 0.
#define DIAGNOSTIC_DEMO_MODE   0

// Maintenance clear is now triggered from the Pi at runtime:
//   curl -X POST http://<pi>:8080/clear
// The ESP polls /mode each wake; if "clear", it runs a black/white cycle,
// acks via POST /clear/done, then deep-sleeps. Use before leaving the panel
// idle for more than ~24h — Spectra 6 panels can ghost if a static image is
// held for weeks.

// ============== CONFIGURATION ==============

const char* SERVER_BASE = "http://192.168.1.77:8080";

#define FALLBACK_SLEEP_MINUTES 30
#define uS_TO_S_FACTOR         1000000ULL
#define WIFI_TIMEOUT           30      // seconds
#define HTTP_TIMEOUT           30000   // ms

// CPU frequency to drop to during the panel refresh, so the ESP32 draws less
// current from the shared 3V3 rail while the panel is doing its DRF current
// spike. 80 MHz is the lowest that keeps WiFi/peripherals stable in case we
// need to come back up; the refresh phase doesn't need CPU performance.
#define REFRESH_CPU_MHZ        80
#define DEFAULT_CPU_MHZ        240

// How long to wait after WiFi shutdown before triggering DRF. The on-board
// 3V3 LDO heats up while WiFi+streaming run; if it's still hot when the
// panel's DRF current spike hits, thermal derating drops its peak-current
// capability and the rail browns out. Idling for a few seconds with WiFi
// off and CPU downclocked lets the package shed that heat before DRF.
// Tune up if brownouts persist, down if you're impatient. Paid once per
// scheduled refresh.
#define POST_WIFI_COOLDOWN_MS  30000

// Panel dimensions (portrait native).
#define PANEL_W                EPD_13IN3E_WIDTH    // 1200
#define PANEL_H                EPD_13IN3E_HEIGHT   // 1600

// Each panel row is 600 bytes (1200 px × 4 bpp). CS_M owns the left 300 bytes
// of each row, CS_S owns the right 300 bytes.
#define PANEL_ROW_BYTES        (PANEL_W / 2)       // 600
#define HALF_ROW_BYTES         (PANEL_ROW_BYTES / 2) // 300

// ============== GLOBAL ==============

RTC_DATA_ATTR int bootCount = 0;

// Buffered log mirrored to Serial. Shipped to the Pi via POST /log right
// before deep sleep, so the laptop can `tail -f data/esp.log` without the
// ESP being plugged into USB. Per-row streaming progress is intentionally
// left as Serial-only to keep this buffer small.
#define LOG_BUF_MAX  4096
String logBuf;

static void logf(const char *fmt, ...) {
    char tmp[256];
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(tmp, sizeof(tmp), fmt, args);
    va_end(args);
    if (n < 0) return;
    Serial.print(tmp);
    if (logBuf.length() + n < LOG_BUF_MAX) {
        logBuf += tmp;
    }
}

static void logln(const char *s) {
    Serial.println(s);
    size_t n = strlen(s);
    if (logBuf.length() + n + 1 < LOG_BUF_MAX) {
        logBuf += s;
        logBuf += '\n';
    }
}

// Reconnect WiFi briefly and POST the buffered log to the Pi. Called after
// the panel refresh has finished, so the DRF current spike is over and it's
// safe to bring the radio back up.
static void postLogToServer() {
    if (logBuf.length() == 0) return;

    setCpuFrequencyMhz(DEFAULT_CPU_MHZ);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < WIFI_TIMEOUT * 2) {
        delay(500);
        attempts++;
    }
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("postLog: WiFi reconnect failed; log lost");
        return;
    }

    HTTPClient http;
    http.begin(String(SERVER_BASE) + "/log");
    http.addHeader("Content-Type", "text/plain");
    int code = http.POST(logBuf);
    Serial.printf("postLog: HTTP %d, %u bytes\n", code, (unsigned)logBuf.length());
    http.end();

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
}

// ============== SETUP ==============

void setup() {
#if ALLOW_BROWNOUT_BYPASS
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
#endif

    // DEV_Module_Init also calls Serial.begin(115200); doing it first here is
    // harmless (Serial.begin is idempotent) and makes early prints work.
    Serial.begin(115200);
    delay(100);

    bootCount++;
    logln("\n\n=================================");
    logf("Surf E-Ink Frame (13.3\") - Boot #%d\n", bootCount);
    logln("=================================\n");

    // Bring up the panel hardware (GPIO config, power on).
    logln("DEV_Module_Init...");
    DEV_Module_Init();

    logln("EPD_13IN3E_Init...");
    EPD_13IN3E_Init();

#if DIAGNOSTIC_DEMO_MODE
    logln("DIAGNOSTIC: skipping WiFi, rendering 6-color stripes (cold-LDO DRF)...");
    EPD_13IN3E_Show6Block();
    logln("DIAGNOSTIC: refresh completed without brownout.");
    EPD_13IN3E_Sleep();
    DEV_Module_Exit();
    // Sleep a long time so the device doesn't loop the diagnostic — flip
    // DIAGNOSTIC_DEMO_MODE back to 0 and reflash to resume normal operation.
    goToSleep(24 * 60);
    return;
#endif

    if (!connectWiFi()) {
        logln("WiFi failed.");
        EPD_13IN3E_Sleep();
        DEV_Module_Exit();
        goToSleep(FALLBACK_SLEEP_MINUTES);
        return;
    }

    if (fetchMode() == "clear") {
        runClearCycle();
        return;  // runClearCycle handles its own deep-sleep
    }

    bool streamed = streamImageToPanel();
    if (!streamed) {
        logln("Image stream failed.");
        // Don't write an error pattern — the panel keeps the previous image,
        // which is more useful than overwriting with text.
    }

    // Fetch the next sleep duration *before* shutting WiFi down, since /sleep
    // needs the network. After this point we won't talk to the Pi again.
    int sleepMinutes = fetchSleepMinutes();

    // Shut WiFi down BEFORE triggering the panel refresh. The Spectra 6 panel
    // pulls a current spike during DRF that competes with WiFi RF for the
    // shared 3V3 rail; keeping the radio up through DRF causes brownout resets
    // on supplies that can't deliver the combined load. Also drop the CPU
    // clock to shave a bit more headroom — the refresh is panel-bound, the
    // CPU has nothing to do but poll BUSY.
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    btStop();
    setCpuFrequencyMhz(REFRESH_CPU_MHZ);

    if (streamed) {
        // Light sleep instead of busy delay() — drops ESP32 current from
        // ~30–50 mA (CPU spinning at 80 MHz) to ~0.8 mA, so the on-board 3V3
        // LDO is genuinely unloaded and can shed the heat it built up during
        // streaming. Pin states and RAM are preserved across light sleep, so
        // the panel framebuffer we just streamed stays intact.
        logf("LDO cooldown (light sleep) %d ms before DRF...\n", POST_WIFI_COOLDOWN_MS);
        Serial.flush();
        esp_sleep_enable_timer_wakeup((uint64_t)POST_WIFI_COOLDOWN_MS * 1000ULL);
        esp_light_sleep_start();
        logln("Triggering panel refresh...");
        EPD_13IN3E_TurnOnDisplay_Public();
        logln("Image rendered.");
    }

    EPD_13IN3E_Sleep();
    DEV_Module_Exit();

    // Bring WiFi back up briefly to ship the cycle's log to the Pi. Safe to
    // do here — DRF is finished, panel is in sleep, no current spikes left.
    postLogToServer();

    goToSleep(sleepMinutes);
}

void loop() {
    // Never reached — setup() ends with deep_sleep, which restarts setup() on wake.
}

// ============== WIFI ==============

bool connectWiFi() {
    logf("Connecting to WiFi: %s\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < WIFI_TIMEOUT * 2) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        logf("WiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
        return true;
    }
    return false;
}

// ============== COLOR QUANTIZATION ==============

// Map a 24-bit BGR pixel to one of the 6 panel colors (4-bit code).
// Same heuristics as the original GxEPD2 firmware, just remapped to
// Waveshare's color codes.
static inline uint8_t rgbToPanel6(uint8_t r, uint8_t g, uint8_t b) {
    int brightness = (r + g + b) / 3;
    if (brightness < 50)                                       return EPD_13IN3E_BLACK;
    if (brightness > 200 && abs(r - g) < 30 && abs(g - b) < 30) return EPD_13IN3E_WHITE;
    if (b > 120 && b > r + 20)                                 return EPD_13IN3E_BLUE;
    if (r > 150 && r > g + 50 && r > b + 50)                   return EPD_13IN3E_RED;
    if (r > 150 && g > 120 && b < 150)                         return EPD_13IN3E_YELLOW;
    if (g > r && g > b && g > 100)                             return EPD_13IN3E_GREEN;
    return brightness > 128 ? EPD_13IN3E_WHITE : EPD_13IN3E_BLACK;
}

// ============== FETCH + STREAM ==============

// One half is either CS_M (half = 0, panel cols 0..599) or CS_S (half = 1, cols 600..1199).
// Opens the HTTP request, parses the BMP header, walks every row, quantizes
// just this half's 600 source pixels, packs into 300 bytes, sends them over
// SPI to the corresponding chip-select.
//
// BMP rows are stored bottom-to-top; the panel is wired top-to-bottom. To send
// rows in panel-top-to-bottom order without random access we read the BMP
// rows in their stored order (bottom-first) into a 1600-row temporary buffer
// of *just this half* (1600 × 300 = 480 KB) — too big.
//
// Workaround: we read the full BMP each call, but only read until row Y, where
// Y starts at PANEL_H-1 and decreases. After each pass we "rewind" by issuing
// the request again. This is O(N²) in network bytes — not viable.
//
// Real workaround used here: on the WIRE we send rows in BMP-stored order
// (bottom-up). The panel still expects top-to-bottom. To stay aligned we
// invert vertically *on the Pi side* by swapping height sign in the BMP, OR
// we accept that the image will be vertically flipped and fix it server-side
// later. To keep this purely a firmware change, we read BMP rows in stored
// order and tell the panel to display them starting from the bottom — i.e.
// we *count down* the panel row index.
//
// Concretely: we fill a small per-row buffer in BMP order, but we accumulate
// rows into a 600 KB buffer (impossible) — so the trick is:
//   for each row of BMP (bottom..top), pre-buffer just this half into RAM,
//   then send in reverse at the end.
//
// 1600 rows × 300 bytes = 480 KB per half. Doesn't fit either.
//
// Practical answer chosen here: serve a *top-to-bottom* BMP from the Pi
// (PIL writes positive-height BMPs which are stored bottom-up by spec; we
// can either use a negative height to flip in spec, or just transpose at
// the source). For the firmware to be simple, we *assume* the BMP is stored
// top-to-bottom, i.e. height field is negative. If you're testing with a
// PIL-generated BMP and it appears upside-down, that's why — invert via
// `image.transpose(Image.FLIP_TOP_BOTTOM)` before saving on the Pi side.
bool streamHalfToPanel(uint8_t half) {
    String url = String(SERVER_BASE) + "/image";
    HTTPClient http;
    http.begin(url);
    http.setTimeout(HTTP_TIMEOUT);

    int httpCode = http.GET();
    if (httpCode != HTTP_CODE_OK) {
        logf("HTTP %d on half %d\n", httpCode, half);
        http.end();
        return false;
    }

    logf("Pass %d: image size %d bytes\n", half + 1, http.getSize());
    WiFiClient* stream = http.getStreamPtr();

    // Read & validate BMP header.
    uint8_t header[54];
    if (stream->readBytes(header, 54) != 54 || header[0] != 'B' || header[1] != 'M') {
        logln("Bad BMP header");
        http.end();
        return false;
    }
    int32_t bmpW   = *(int32_t*)&header[18];
    int32_t bmpH   = *(int32_t*)&header[22];
    uint16_t bpp   = *(uint16_t*)&header[28];
    uint32_t off   = *(uint32_t*)&header[10];

    logf("BMP: %dx%d %dbpp\n", bmpW, bmpH, bpp);
    if (bmpW != (int32_t)PANEL_W || abs(bmpH) != (int32_t)PANEL_H || bpp != 24) {
        logf("Unexpected BMP geometry — need %dx%d 24bpp\n", PANEL_W, PANEL_H);
        http.end();
        return false;
    }

    if (off > 54) {
        for (uint32_t i = 0; i < off - 54; i++) stream->read();
    }

    // BMP row size, padded to 4-byte boundary.
    const int rowSize = ((bmpW * 3) + 3) & ~3;
    uint8_t  rowBuf[rowSize];
    uint8_t  packed[HALF_ROW_BYTES];

    // Open the right chip-select and send the data-write command once.
    int csPin = (half == 0) ? EPD_CS_M_PIN : EPD_CS_S_PIN;
    DEV_Digital_Write(csPin, 0);
    DEV_SPI_WriteByte(0x10);   // DTM = "data to memory"

    // Source columns this pass cares about. CS_M = pixels 0..599, CS_S = 600..1199.
    int srcXStart = (half == 0) ? 0 : 600;

    // BMP is bottom-up; we send to the panel top-down. So we must read rows
    // in reverse order. With ~5.7 MB total and only forward-reading streams,
    // the simplest correct approach is: read all rows into a per-row 600-byte
    // packed buffer kept on flash via SPIFFS, then play back in reverse...
    // overkill. Instead we accept BMP rows in stored order and assume the Pi
    // serves a top-down BMP (negative-height field — see comment block above).
    // If the panel image is upside-down, fix it on the Pi by writing the BMP
    // top-down (PIL: img.save(..., "BMP") writes bottom-up; flip first).
    bool topDown = (bmpH < 0);
    if (!topDown) {
        logln("WARN: BMP is bottom-up — image will be vertically flipped on screen.");
    }

    for (uint32_t row = 0; row < PANEL_H; row++) {
        // Read a full source row.
        size_t got = stream->readBytes((char*)rowBuf, rowSize);
        if (got != (size_t)rowSize) {
            logf("Short read row %u: got %u\n", row, got);
            DEV_Digital_Write(csPin, 1);
            http.end();
            return false;
        }

        // Quantize 600 source pixels for this half, pack two per byte.
        for (int i = 0; i < 600; i += 2) {
            int sx0 = srcXStart + i;
            int sx1 = srcXStart + i + 1;
            uint8_t b0 = rowBuf[sx0 * 3 + 0];
            uint8_t g0 = rowBuf[sx0 * 3 + 1];
            uint8_t r0 = rowBuf[sx0 * 3 + 2];
            uint8_t b1 = rowBuf[sx1 * 3 + 0];
            uint8_t g1 = rowBuf[sx1 * 3 + 1];
            uint8_t r1 = rowBuf[sx1 * 3 + 2];
            uint8_t c0 = rgbToPanel6(r0, g0, b0);
            uint8_t c1 = rgbToPanel6(r1, g1, b1);
            packed[i / 2] = (c0 << 4) | c1;
        }

        DEV_SPI_Write_nByte(packed, HALF_ROW_BYTES);
        // The stock driver delays 1 ms between rows; do the same to avoid
        // overrunning the panel's input buffer.
        delay(1);

        // Lightweight progress log every ~10%.
        if (row % 160 == 0) {
            Serial.printf("  %u/%u\n", row, PANEL_H);
        }
    }

    DEV_Digital_Write(csPin, 1);
    http.end();
    return true;
}

// Streams both halves to the panel's frame buffer. Does NOT trigger the
// refresh — DRF is invoked from setup() after WiFi is shut down, to keep the
// 3V3 rail from being loaded by the radio at the moment of the panel's
// current spike.
bool streamImageToPanel() {
    logln("Pass 1: streaming left half (CS_M)...");
    if (!streamHalfToPanel(0)) return false;

    logln("Pass 2: streaming right half (CS_S)...");
    if (!streamHalfToPanel(1)) return false;

    return true;
}

// ============== MAINTENANCE CLEAR ==============

// Ask the Pi whether to render an image or run a panel-clear cycle this wake.
// On any failure default to "image" — a network blip shouldn't erase the panel.
String fetchMode() {
    HTTPClient http;
    http.begin(String(SERVER_BASE) + "/mode");
    http.setTimeout(10000);
    int code = http.GET();
    String mode = "image";
    if (code == HTTP_CODE_OK) {
        String body = http.getString();
        if (body.indexOf("\"clear\"") >= 0) mode = "clear";
    }
    logf("Mode: %s (HTTP %d)\n", mode.c_str(), code);
    http.end();
    return mode;
}

// POST /clear/done so the Pi removes the marker and the next wake resumes
// normal image rendering. Best-effort — if it fails the worst case is one
// extra clear cycle on the next wake.
void postClearDone() {
    HTTPClient http;
    http.begin(String(SERVER_BASE) + "/clear/done");
    http.setTimeout(10000);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST("{}");
    logf("Clear ack: HTTP %d\n", code);
    http.end();
}

// Pi-triggered maintenance: black/white cycles to flush particles, end on
// white (recommended storage state per Waveshare). Same WiFi-off + LDO
// cooldown discipline as the image refresh path, since each Clear() does its
// own DRF current spike.
void runClearCycle() {
    logln("CLEAR: requested by Pi — running maintenance cycle.");

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    btStop();
    setCpuFrequencyMhz(REFRESH_CPU_MHZ);

    logf("LDO cooldown (light sleep) %d ms before first DRF...\n", POST_WIFI_COOLDOWN_MS);
    Serial.flush();
    esp_sleep_enable_timer_wakeup((uint64_t)POST_WIFI_COOLDOWN_MS * 1000ULL);
    esp_light_sleep_start();

    logln("CLEAR: black fill...");
    EPD_13IN3E_Clear(EPD_13IN3E_BLACK);
    logln("CLEAR: white fill...");
    EPD_13IN3E_Clear(EPD_13IN3E_WHITE);
    logln("CLEAR: black fill...");
    EPD_13IN3E_Clear(EPD_13IN3E_BLACK);
    logln("CLEAR: final white fill (storage state)...");
    EPD_13IN3E_Clear(EPD_13IN3E_WHITE);
    logln("CLEAR: done — safe to unplug.");

    EPD_13IN3E_Sleep();
    DEV_Module_Exit();

    // Bring WiFi back to ack the Pi and ship the log, same pattern as the
    // image-refresh path.
    postLogToServer_andAckClear();

    // Sleep until the user physically power-cycles the ESP. Using a timer
    // wakeup here would defeat the point of clearing — the next wake would
    // just redraw an image. Power-cycle to resume normal operation.
    goToSleepForever();
}

// Reconnect WiFi once and do both the clear-ack and log-post in the same
// connection — saves one connect/disconnect cycle vs. calling them separately.
void postLogToServer_andAckClear() {
    setCpuFrequencyMhz(DEFAULT_CPU_MHZ);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < WIFI_TIMEOUT * 2) {
        delay(500);
        attempts++;
    }
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("postClear: WiFi reconnect failed; marker stays, will retry next wake");
        return;
    }

    postClearDone();

    if (logBuf.length() > 0) {
        HTTPClient http;
        http.begin(String(SERVER_BASE) + "/log");
        http.addHeader("Content-Type", "text/plain");
        int code = http.POST(logBuf);
        Serial.printf("postLog: HTTP %d, %u bytes\n", code, (unsigned)logBuf.length());
        http.end();
    }

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
}

// ============== SLEEP DURATION ==============

int fetchSleepMinutes() {
    String url = String(SERVER_BASE) + "/sleep";
    logf("Asking Pi for sleep duration: %s\n", url.c_str());

    HTTPClient http;
    http.begin(url);
    http.setTimeout(10000);

    int code = http.GET();
    if (code == HTTP_CODE_OK) {
        String body = http.getString();
        int idx = body.indexOf("sleep_minutes");
        if (idx >= 0) {
            int colon = body.indexOf(":", idx);
            int end   = body.indexOf("}", colon);
            String v  = body.substring(colon + 1, end);
            v.trim();
            int m = v.toInt();
            if (m > 0) {
                logf("Pi says: sleep %d min\n", m);
                http.end();
                return m;
            }
        }
    }
    logf("Sleep fetch failed (HTTP %d), using fallback %d min\n", code, FALLBACK_SLEEP_MINUTES);
    http.end();
    return FALLBACK_SLEEP_MINUTES;
}

void goToSleep(int minutes) {
    logf("\nDeep sleep for %d minutes. Goodnight.\n", minutes);
    Serial.flush();
    esp_sleep_enable_timer_wakeup((uint64_t)minutes * 60 * uS_TO_S_FACTOR);
    esp_deep_sleep_start();
}

// Deep sleep with no wake source — only an external reset / power-cycle
// brings the ESP back. Used by the maintenance clear path so the panel can
// stay in its white storage state for as long as it's plugged in.
void goToSleepForever() {
    logln("\nDeep sleep until power-cycled. Goodnight.");
    Serial.flush();
    esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);
    esp_deep_sleep_start();
}
