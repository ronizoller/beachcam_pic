# Surf E-Ink Frame - Hardware Wiring Guide

This document describes all hardware connections for the Surf E-Ink Frame project.

---

## Components List

| Component | Model | Notes |
|-----------|-------|-------|
| Battery | LiPo 3.7V 2000mAh | JST PH2.0 connector |
| Charger | TP4056 USB-C | With protection circuit, PH2.0 socket |
| Boost converter | MT3608 | DC-DC step-up; **set output trimpot to 5.0V before connecting** |
| Microcontroller | ESP32 DevKitC 32U | WiFi, USB-C, 38 pins |
| Test Display | Waveshare 1.54" E-Ink | B/W, SPI, includes HAT |
| Production Display | Waveshare 13.3" Spectra 6 | 6-color, 1600x1200, SPI |
| Server | Raspberry Pi Zero 2 W | WiFi built-in, wall powered, 512MB |
| Speaker | 8ohm 2W (or 4ohm 3W) | 25x35mm square, ultra-thin |
| Speaker resistor | 220ohm 1W | Current limiter for DAC output |
| Wires | Dupont male-to-female | 20cm, various colors |
| Breadboard | 830 points (full size) | For prototyping |

---

## Breadboard Setup (For Testing)

Use the breadboard to prototype before final assembly. No soldering needed.

### How a Breadboard Works

```
    A B C D E   F G H I J
    ─────────   ─────────
 1  o o o o o   o o o o o   <- holes in same row are connected
 2  o o o o o   o o o o o      (A-E connected, F-J connected)
 3  o o o o o   o o o o o
    ...         ...
30  o o o o o   o o o o o

+   o o o o o o o o o o o   <- power rail (all connected horizontally)
-   o o o o o o o o o o o   <- ground rail (all connected horizontally)
```

- Each row (1-30) has 5 connected holes on each side
- The center gap separates left (A-E) from right (F-J)
- Power rails (+/-) run the full length of the board

### Placing the ESP32

1. Place ESP32 **across the center gap** so pins are accessible on both sides
2. The ESP32 is wide - it will use rows on both sides of the gap
3. Each ESP32 pin lands in its own row

```
        Breadboard with ESP32
    A B C D E     F G H I J
    ─────────     ─────────
 1  o o o o o     o o o o o
 2  o o[3V3]━━━━━━━[GPIO23]o   <- ESP32 spans the gap
 3  o o[GND]━━━━━━━[GPIO22]o
 4  o o[ 5V]━━━━━━━[GPIO21]o
 5  o o[...]━━━━━━━[GPIO19]o
    ...           ...
```

### Connecting Wires

Use **male-to-male** Dupont wires on the breadboard:
- One end into breadboard row (same row as ESP32 pin)
- Other end into another breadboard row or power rail

Use **male-to-female** Dupont wires to connect to E-Ink HAT:
- Male end into breadboard row (same row as ESP32 pin)
- Female end onto E-Ink HAT pin header

### Breadboard Wiring Steps

**Step 1: Power rails**
- Connect ESP32 GND row → breadboard (-) rail (black wire)
- Connect ESP32 3V3 row → breadboard (+) rail (red wire)

**Step 2: E-Ink power (from rails)**
- Breadboard (+) rail → E-Ink VCC (red, male-to-female)
- Breadboard (-) rail → E-Ink GND (black, male-to-female)

**Step 3: E-Ink SPI (from ESP32 rows)**
- GPIO23 row → E-Ink DIN (blue, male-to-female)
- GPIO18 row → E-Ink CLK (yellow, male-to-female)
- GPIO5 row → E-Ink CS (orange, male-to-female)
- GPIO17 row → E-Ink DC (green, male-to-female)
- GPIO16 row → E-Ink RST (white, male-to-female)
- GPIO4 row → E-Ink BUSY (purple, male-to-female)

**Step 4: Speaker (from ESP32 DAC)**
- GPIO25 row → 220ohm resistor → speaker (+) wire
- Speaker (-) wire → breadboard (-) rail (GND)
- The resistor can sit in two adjacent breadboard rows

```
    Breadboard rows:
    row 20: [GPIO25 pin] ──── [resistor leg 1]
    row 21:                    [resistor leg 2] ──── [speaker + wire]
    (-) rail: ──────────────────────────────────── [speaker - wire]
```

**Step 5: Battery power (optional, for battery test)**
- First, set the MT3608 output to 5.0V using a multimeter. See "Setting the MT3608 Trimpot" below.
- TP4056 OUT+ → MT3608 IN+ (red)
- TP4056 OUT- → breadboard (-) rail and MT3608 IN- / GND (black)
- MT3608 OUT+ → breadboard row next to ESP32 5V pin (red, **only after the trimpot is set to 5.0V**)
- MT3608 OUT- → breadboard (-) rail (black)

The LiPo's 3.0–4.2V output is too low to feed the ESP32's `5V` pin directly — the onboard 5V→3.3V LDO needs ≥4.5V to regulate. The MT3608 boosts the cell voltage to a clean 5V so the LDO has the headroom it needs.

### Breadboard vs Final Assembly

| Breadboard (testing) | Final (in frame) |
|---------------------|------------------|
| ESP32 plugged into breadboard | ESP32 mounted with tape/velcro |
| Wires through breadboard | Wires direct to ESP32 pins |
| Easy to change connections | Permanent connections |
| Bulky, not portable | Compact, fits in frame |

### Tips

- Test with USB power first (no battery)
- Double-check pin rows before powering on
- If display doesn't work, check wire is in correct row
- Keep wires organized by color

---

## Power System Wiring

### ⚠️ Critical: Verify TP4056 polarity with a multimeter before wiring MT3608

Cheap TP4056 USB-C modules sometimes have **reversed silkscreen labels** — the pad labeled "B+" may actually output the LiPo's *negative*, and vice versa. Likewise, some LiPo manufacturers wire their JST plugs with non-standard polarity (red wire on what should be the negative pin). Either defect alone — or both combined — flips the polarity downstream invisibly.

Connecting an MT3608 to reverse-polarity input causes a **brief short circuit through the internal body diode → spark at VIN → permanently damaged FET**. The module appears fine in resistance checks but trips the TP4056 protection under any load. There is no "soft fail" — it's silent destruction.

**Always verify before wiring the MT3608:**

1. Plug the LiPo into the TP4056's JST socket
2. Multimeter in DC voltage mode (any range above 5V — auto-detect is fine)
3. 🔴 Red probe → TP4056 **labeled "B+"** pad
4. ⚫ Black probe → TP4056 **labeled "B-"** pad
5. Read the **sign** on the display:
   - **Positive (+3.7-4.2V)** → labels are correct; wire normally
   - **Negative (−3.7-4.2V)** → silkscreen is reversed; treat labeled "B+" as your negative and "B-" as your positive (or swap LiPo JST wires for clean labeling)

After this verification, tag the actual positive wire (the one giving a positive reading with red probe) with red tape or a marker. Connect that wire to MT3608 **IN+** regardless of its insulation color or the TP4056 label. Same for the negative side.

**Cost of skipping this step:** 1 dead MT3608 ($1) and a few hours of debugging.

### Step 1: Battery to Charger

**No wiring needed** - the battery plugs directly into the TP4056.

- Battery has JST PH2.0 male plug
- TP4056 has JST PH2.0 female socket
- Just plug them together

### Step 2: Charger Output to Boost Converter

Connect the TP4056's protected output to the MT3608's input:

| From | To | Wire Color |
|------|----|------------|
| TP4056 **OUT+** | MT3608 **IN+** | Red |
| TP4056 **OUT-** | MT3608 **IN-** (GND) | Black |

Use the TP4056's `OUT+/OUT-` (not `BAT+/BAT-`) — `OUT-` is downstream of the protection MOSFET, so over-discharge cutoff still works.

### Step 3: Boost Converter to ESP32

**Set the MT3608 output to 5.0V before wiring it to the ESP32** (see "Setting the MT3608 Trimpot" below). Then:

| From | To | Wire Color |
|------|----|------------|
| MT3608 **OUT+** | ESP32 **5V** pin | Red |
| MT3608 **OUT-** | ESP32 **GND** pin | Black |

**Power flow:** Battery → TP4056 → MT3608 boost (3.7V → 5V) → ESP32 5V pin → onboard LDO → 3.3V rail → ESP32 + E-Ink HAT

### Why the MT3608 is required

The LiPo cell sits between 3.0V (empty) and 4.2V (full). The ESP32's onboard 5V→3.3V LDO needs ≥4.5V on its `5V` pin to regulate. Wiring the LiPo straight to `5V` puts the LDO in dropout, the 3.3V rail floats just below the cell voltage, and the panel's DRF current spike collapses the rail into a brownout reset. The MT3608 boosts the LiPo's 3.7V to a clean 5.0V so the LDO has headroom regardless of charge state.

### Setting the MT3608 Trimpot

The MT3608 ships with its trimpot at a random position — often outputting 12V or higher. **Connecting it to the ESP32 in that state will instantly destroy the chip.** Always set output to 5.0V before connecting.

Procedure:
1. Wire LiPo → TP4056 → MT3608 IN. **Do NOT connect MT3608 OUT to the ESP32 yet.**
2. Plug the LiPo into the TP4056.
3. Place a multimeter (DC voltage mode, 20V range) on the MT3608's `OUT+` and `OUT-` pads.
4. Turn the trimpot screw with a small Phillips driver. On most MT3608 modules, **clockwise increases output** — verify by watching the meter as you turn slightly. Some clones are reversed.
5. Stop when the meter reads **5.00V ± 0.05V**.
6. Unplug the LiPo. Wire MT3608 `OUT+/OUT-` to ESP32 `5V/GND`.
7. With nothing else changed, plug the LiPo back in and probe the ESP32's `5V` pin with the meter — should still read ~5.0V. If it reads higher, the trimpot moved during wiring; redo step 5.

### Why no switch

Earlier revisions of this doc used a KCD11 switch between the TP4056 and the ESP32. It's been removed: the ESP32 spends >99% of its time in deep sleep (~10µA), and powering off via switch isn't necessary for daily use. To "turn the frame off" entirely, unplug the LiPo from the TP4056's JST socket. The trade-off is that the MT3608 has ~3–5mA quiescent current, so a battery left connected drains over weeks rather than indefinitely — fine for a frame that's regularly charged.

---

## E-Ink Display Wiring

The E-Ink display connects to the ESP32 via SPI. There are 8 wires total.

### Power Connections (2 wires)

| From | To | Wire Color | Purpose |
|------|----|------------|---------|
| ESP32 **3V3** | E-Ink HAT **VCC** | Red | 3.3V power to display |
| ESP32 **GND** | E-Ink HAT **GND** | Black | Ground |

**Important:** Power the display from ESP32's 3V3 pin (not 5V). The ESP32's onboard regulator provides safe 3.3V output.

### SPI Data Connections (6 wires)

| ESP32 Pin | E-Ink HAT Pin | Wire Color | Signal Purpose |
|-----------|---------------|------------|----------------|
| GPIO23 | DIN | Blue | SPI Data In (MOSI) |
| GPIO18 | CLK | Yellow | SPI Clock |
| GPIO5 | CS | Orange | Chip Select |
| GPIO17 | DC | Green | Data/Command select |
| GPIO16 | RST | White | Reset |
| GPIO4 | BUSY | Purple | Busy status |

### Wire Color Summary

- **Red** = Power (+)
- **Black** = Ground (-)
- **Blue** = DIN (data)
- **Yellow** = CLK (clock)
- **Orange** = CS (chip select)
- **Green** = DC (data/command)
- **White** = RST (reset)
- **Purple** = BUSY (status)

---

## Speaker Wiring (Guest Beach Whoosh Sound)

A small speaker plays a wave/whoosh sound when a guest beach image is displayed.

### Connections (2 wires + 1 resistor)

| From | To | Wire/Component |
|------|----|----------------|
| ESP32 **GPIO25** | **220ohm resistor** leg 1 | Short wire or direct |
| **220ohm resistor** leg 2 | Speaker **(+)** | Wire |
| Speaker **(-)** | ESP32 **GND** | Black wire |

### Why GPIO25?

GPIO25 is one of the ESP32's two built-in DAC (Digital-to-Analog Converter) pins. 
The DAC outputs a real analog audio signal — no PWM buzzing, actual smooth audio.

### Why the 220ohm resistor?

The ESP32 GPIO can only safely output ~12mA. The resistor limits current:
- 8ohm speaker: 3.3V / (220 + 8) = 14mA (safe)
- 4ohm speaker: 3.3V / (220 + 4) = 15mA (safe)
- Without resistor: 3.3V / 8 = 412mA (would damage the ESP32!)

The sound will be quiet but audible — enough for a subtle whoosh notification.

### Speaker choice

- **8ohm 2W** — best match for ESP32 DAC, lower current draw
- **4ohm 3W** — works fine with 220ohm resistor, slightly louder
- Small square speakers (25x35mm) fit inside a picture frame

### Audio file

The whoosh WAV file is stored in ESP32 flash (SPIFFS partition):
- Format: 8-bit, 8kHz, mono WAV
- Size: ~8KB for 1 second
- Stored at: `/whoosh.wav` in SPIFFS
- Plays when ESP32 detects a guest beach image (`"guest": true` in metadata)

---

## Raspberry Pi (Separate System)

The Raspberry Pi is **completely separate** from the battery-powered frame. It stays plugged into the wall.

### Power
- Connect Micro USB to a 5V Android charger
- Pi Zero W v1.1 needs ~150mA, any charger works

### Network
- Pi connects to home WiFi
- Runs Python server on port 8080
- ESP32 fetches images via HTTP over WiFi

### Storage
- microSD card with Raspberry Pi OS
- Project code in `/home/pi/beachcam_pic/`

---

## Assembly Order

When you're ready to assemble, follow this order:

1. **Test without battery first**
   - Power ESP32 via USB-C cable
   - Connect E-Ink display to ESP32
   - Upload firmware and verify display works

2. **Set the MT3608 output to 5.0V**
   - Wire LiPo → TP4056 → MT3608 IN. Do not connect MT3608 OUT yet.
   - Probe MT3608 OUT+/OUT- with a multimeter.
   - Turn the trimpot until the meter reads 5.00V ± 0.05V.

3. **Add battery system**
   - Battery plugs into TP4056 (JST PH2.0, no soldering)
   - Wire TP4056 OUT+ → MT3608 IN+ (red)
   - Wire TP4056 OUT- → MT3608 IN- and ESP32 GND (black)
   - Wire MT3608 OUT+ → ESP32 5V pin (red)
   - Plug the LiPo back in and verify the ESP32 boots normally

4. **Final assembly**
   - Mount everything in picture frame
   - Ensure USB-C port on TP4056 is accessible for charging
   - To "power off" the frame entirely, unplug the LiPo from the TP4056's JST socket

---

## Pin Reference (ESP32 DevKitC 32U)

```
        ESP32 DevKitC 32U
        ┌─────────────────┐
        │    [USB-C]      │
        │                 │
   3V3 ─┤                 ├─ GPIO23 (DIN)
   GND ─┤                 ├─ GPIO18 (CLK)
    5V ─┤                 ├─ GPIO5  (CS)
        │                 ├─ GPIO17 (DC)
        │                 ├─ GPIO16 (RST)
 GPIO25─┤ (Speaker DAC)   ├─ GPIO4  (BUSY)
        │                 │
        └─────────────────┘
```

**Left side pins used:**
- 3V3 → E-Ink VCC (red wire)
- GND → E-Ink GND, MT3608 OUT-, Speaker (-) (black wires)
- 5V ← From MT3608 OUT+ (red wire, power input)
- GPIO25 → 220ohm resistor → Speaker (+)

**Right side pins used:**
- GPIO23 → DIN (blue)
- GPIO18 → CLK (yellow)
- GPIO5 → CS (orange)
- GPIO17 → DC (green)
- GPIO16 → RST (white)
- GPIO4 → BUSY (purple)

---

## Troubleshooting

### Display doesn't turn on
- Check VCC/GND connections
- Verify ESP32 is powered (LED on?)
- Try powering ESP32 via USB-C first

### Display shows garbage
- Check SPI wire connections (DIN, CLK, CS)
- Verify GPIO pin numbers match code
- Check wire connections aren't loose

### ESP32 won't power from battery
- Is the battery charged? (charge via TP4056 USB-C)
- Check OUT+/OUT- connections from TP4056 → MT3608 IN+/IN-
- Verify MT3608 output is ~5.0V with a multimeter (probes on OUT+/OUT-)
- If MT3608 output is wrong, redo the trimpot setting procedure
- Confirm the MT3608's onboard LED lights up when battery is plugged in

### WiFi connection fails
- Verify credentials in `credentials.h`
- Check Pi server is running
- Ensure both devices on same network

---

## Voltage Reference

| Point | Voltage | Notes |
|-------|---------|-------|
| Battery full | 4.2V | Freshly charged |
| Battery nominal | 3.7V | Normal operation |
| Battery empty | ~2.4V | Protection MOSFET cuts off here (DW01 default) |
| MT3608 output | 5.0V | Set via trimpot, feeds ESP32 5V pin |
| ESP32 3V3 output | ~3.3V | From onboard regulator |
| E-Ink VCC | 3.3V | Safe for display |

---

## See Also

- `hardware_wiring.png` - Visual wiring diagram
- `../esp32/surf_frame/surf_frame.ino` - ESP32 firmware
- `../config/config.yaml` - Configuration file
