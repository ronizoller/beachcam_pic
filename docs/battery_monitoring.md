# Battery monitoring

The Pi side is **done and deployed**. It stays inert until the firmware prints one line.

## What the Pi already does

- `POST /log` (which the ESP already calls every cycle) is scanned for a
  `BATTERY: x.xx V` line — case-insensitive, the `V` is optional.
- The reading is stored in `data/battery.json` (`volts`, `time`, and a
  200-point `history`), written atomically.
- It appears in `GET /metadata` as `battery_volts`, so you can check remotely
  with no ssh.
- Below `battery.warn_volts` (default **3.6 V**) every rendered frame gets a
  small low-battery pill, bottom-left.

Readings outside 2.0–4.6 V are rejected as misreads, and readings older than
`battery.max_age_hours` (default 6) are ignored — otherwise the last gasp before
the battery died would pin the warning on forever, including after a recharge.

## What the firmware still needs — two changes

### 1. Move BUSY off A2

**This is a wire move as well as a code change.** The battery divider is hardwired
to `IO34 / A2`, confirmed from DFRobot's schematic
([DFR0654 wiki](https://wiki.dfrobot.com/dfr0654/) → Schematics PDF):

```
VBAT ──[ R5 1M ]──┬── IO34/A2
                  │
               [ R14 1M ]
                  │
                 GND
```

`EPD_BUSY_PIN` is currently on that same pin. The panel drives BUSY hard and the
divider is only a weak 1 MΩ pull, so **the display works fine today** — the
conflict is one-directional: you cannot *read* the battery through a pin the
panel is driving.

Move BUSY to `IO35 / A3`. On header **P3 that is the physically adjacent pin**
(P3 pin 6 = A3, P3 pin 7 = A2), so it is a one-position move. Safe because:

- IO34–39 are all input-only, and BUSY is read-only
- neither pin has internal pull-ups, and `DEV_Config.cpp` asks for plain
  `pinMode(EPD_BUSY_PIN, INPUT)` — so nothing changes electrically
- both are **ADC1**, the half that still works while WiFi is on. ADC2 cannot be
  read during WiFi at all, which is *why* BUSY moves rather than the battery

```c
#define EPD_BUSY_PIN    35   // [A3] input-only; moved off A2/IO34, the battery divider
```

### 2. Print the voltage at boot

Read it **early, before the panel refresh** — the refresh is the highest-current
moment in the cycle and would show you the sag rather than the resting voltage.
The log is POSTed at the end of the cycle, but the value is from boot, which is
what you want.

```c
// 2x 1M divider on IO34, so the pin sees half the pack voltage.
// analogReadMilliVolts() applies the factory eFuse calibration — much more
// accurate than raw analogRead(), which is markedly non-linear on ESP32.
float vbat = analogReadMilliVolts(34) * 2.0f / 1000.0f;
Serial.printf("BATTERY: %.2fV\n", vbat);
```

That is the whole firmware change: one `#define`, two lines in `setup()`.

## Reference numbers

| | |
|---|---|
| Charger | TP4056X, `R6 = 2 kΩ` on PROG → **~580 mA** |
| Charge LED | `LED1` red, on the open-drain `CHRG` pin: **lit = charging, out = done** |
| Charge time | `(mAh / 580) × 1.3` hours |
| Full | 4.2 V (label says 3.7 V — that is *nominal*, ≈ 40–50%) |
| Warn | 3.6 V |
| Empty | ~3.2 V |
| Measured runtime | **~4.8 days** per charge (Boot #124, 2026-09-10) |

The charger cannot overcharge: 4.2 V float, auto-terminate at ~1/10 current,
auto-recharge only below ~4.05 V.

## Diagnosing a dead frame without any of this

1. `GET /metadata` → if `candidates_count` keeps climbing, the ESP is not
   pulling `/image`. Cheapest check, no ssh.
2. `tail ~/beachcam_pic/data/esp.log` — headers are UTC (`utcnow()`), so add 3 h
   for IDT. Read the pattern:
   - **clean stop** after a good `Image rendered.` → flat battery
   - **repeated `Boot #N`** with failed renders → brownout under load
   - **logs still arriving** → not power at all
3. Multimeter on the pack: `~0 V` = protection latched, `<2.5 V` = damaged,
   `3.1 V` = flat but healthy, `>3.7 V` = not the battery.
