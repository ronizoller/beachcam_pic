/*
 * Panel smoke test — Waveshare 13.3" e-Paper (E) + ESP32
 *
 * A standalone wiring check for a NEW panel. No WiFi, no Pi, no credentials —
 * flash it and the panel should, on boot:
 *   1. clear to white
 *   2. render the 6-color stripe block (black / white / yellow / red / blue / green)
 *      across the FULL width, then clear back to white.
 *
 * How to read the result:
 *   - Six clean stripes edge-to-edge  → wiring is GOOD. Both driver chips
 *     (CS_M = left half, CS_S = right half) and all data/control lines work.
 *   - Nothing happens at all           → power (PWR/VCC/GND), RST, or BUSY line.
 *   - Only the LEFT or only the RIGHT
 *     half renders                     → that side's chip-select is bad
 *                                         (CS_M = GPIO15, CS_S = GPIO2).
 *   - Garbled / wrong colors / noise   → DIN/MOSI (GPIO14), CLK (GPIO13),
 *                                         or DC (GPIO27) miswired.
 *
 * Wiring — FireBeetle 2 ESP32-E (DFR0654), silkscreen label → panel signal
 * (must match DEV_Config.h — same as the main surf_frame sketch):
 *   SCK  → CLK    MOSI → DIN/MOSI    D11 → CS_M    D10 → CS_S
 *   D3   → RST    D2   → DC          A2  → BUSY    D7  → PWR
 *   3V3  → VCC    GND  → GND
 *
 * Renders once per boot (e-paper DRF is slow + stressful, so we don't loop).
 * To run it again: press the ESP32's EN/RESET button, or power-cycle.
 * Watch progress on Serial at 115200 baud.
 *
 * NOTE: the driver files here (DEV_Config.*, EPD_13in3e.*, Debug.h) are copies
 * of the ones in ../surf_frame. If you ever change the pin map in the main
 * sketch's DEV_Config.h, re-copy it here so the test checks the real wiring.
 */

#include "DEV_Config.h"
#include "EPD_13in3e.h"

void setup() {
    Serial.begin(115200);
    delay(100);
    Serial.println("\n\n=== Panel smoke test — 13.3\" (E) ===");

    Serial.println("DEV_Module_Init...");
    DEV_Module_Init();

    Serial.println("EPD_13IN3E_Init...");
    EPD_13IN3E_Init();

    Serial.println("Clear to white...");
    EPD_13IN3E_Clear(EPD_13IN3E_WHITE);

    Serial.println("Rendering 6-color block (this takes ~30s)...");
    EPD_13IN3E_Show6Block();
    // Leave the stripes on-screen as the visible pass/fail result. (For long
    // storage, flash the main sketch + run a Pi-triggered /clear to end on white.)

    Serial.println("Panel to sleep. Done.");
    EPD_13IN3E_Sleep();
    DEV_Module_Exit();

    Serial.println("=== Test complete. Press EN/RESET to run again. ===");
}

void loop() {
    // Single-shot test; nothing to do. Reset to re-run.
}
