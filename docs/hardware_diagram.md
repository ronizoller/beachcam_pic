# Surf E-Ink Frame - Hardware Wiring Guide

This document describes all hardware connections for the Surf E-Ink Frame project.

---

## Components List

| Component | Model | Notes |
|-----------|-------|-------|
| Battery | LiPo 3.7V 2000mAh | JST PH2.0 connector |
| Charger | TP4056 USB-C | With protection circuit, PH2.0 socket |
| Switch | KCD11 ON-OFF | 2-pin rocker switch |
| Microcontroller | ESP32 DevKitC 32U | WiFi, USB-C, 38 pins |
| Test Display | Waveshare 1.54" E-Ink | B/W, SPI, includes HAT |
| Production Display | Waveshare 13.3" Spectra 6 | 6-color, 1600x1200, SPI |
| Server | Raspberry Pi Zero W v1.1 | WiFi built-in, wall powered |
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

**Step 4: Battery power (optional, for battery test)**
- TP4056 OUT+ → Switch → breadboard row next to ESP32 5V pin
- TP4056 OUT- → breadboard (-) rail

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

### Step 1: Battery to Charger

**No wiring needed** - the battery plugs directly into the TP4056.

- Battery has JST PH2.0 male plug
- TP4056 has JST PH2.0 female socket
- Just plug them together

### Step 2: Charger Output to Switch

Connect the TP4056 positive output to the switch:

| From | To | Wire Color |
|------|----|------------|
| TP4056 **OUT+** | Switch **pin 1** | Red |

### Step 3: Switch to ESP32

Connect the switch output to ESP32 power input:

| From | To | Wire Color |
|------|----|------------|
| Switch **pin 2** | ESP32 **5V** pin | Red |
| TP4056 **OUT-** | ESP32 **GND** pin | Black |

**Power flow:** Battery → TP4056 → Switch → ESP32

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

2. **Add battery system**
   - Connect battery to TP4056
   - Wire TP4056 OUT+ → Switch → ESP32 5V
   - Wire TP4056 OUT- → ESP32 GND
   - Test with switch ON/OFF

3. **Final assembly**
   - Mount everything in picture frame
   - Ensure USB-C port on TP4056 is accessible for charging

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
        │                 ├─ GPIO4  (BUSY)
        │                 │
        └─────────────────┘
```

**Left side pins used:**
- 3V3 → E-Ink VCC (red wire)
- GND → E-Ink GND and TP4056 OUT- (black wires)
- 5V ← From switch (red wire, power input)

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
- Is the switch ON?
- Is the battery charged? (charge via TP4056 USB-C)
- Check OUT+/OUT- connections from TP4056

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
| Battery empty | 3.3V | TP4056 cuts off below this |
| ESP32 3V3 output | ~3.3V | From onboard regulator |
| E-Ink VCC | 3.3V | Safe for display |

---

## See Also

- `hardware_wiring.png` - Visual wiring diagram
- `../esp32/surf_frame/surf_frame.ino` - ESP32 firmware
- `../config/config.yaml` - Configuration file
