# Breadboard Learning Exercises

Simple exercises to learn breadboard basics before building the main project.

---

## What is a Breadboard?

A breadboard is a reusable plastic board full of holes, used to build circuits **without soldering**. You just push component legs and wires into the holes — the holes are connected to each other internally in a specific pattern, which forms the wiring.

### What the holes look like

```
        ┌─ power rails (red + / blue −) run the full length, horizontally
        ▼
   (+) ●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●  ← all + holes connected
   (−) ●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●  ← all − holes connected

        A B C D E       F G H I J        ← column letters
       ┌───────────┐   ┌───────────┐
     1 │ ● ● ● ● ● │   │ ● ● ● ● ● │
     2 │ ● ● ● ● ● │   │ ● ● ● ● ● │
     3 │ ● ● ● ● ● │   │ ● ● ● ● ● │
       │    ...    │   │    ...    │
       └───────────┘   └───────────┘
        ▲     ▲             ▲
        │     └── A1-E1 connected (one row, one node)
        │         F1-J1 connected separately
        │
        └── center gap splits left half from right half

   (+) ●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●
   (−) ●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●─●
```

### The two key rules

1. **Each row is one electrical node**, but only on one side of the gap.
   - Holes `A1`, `B1`, `C1`, `D1`, `E1` are all connected to each other → same node.
   - Holes `F1`, `G1`, `H1`, `I1`, `J1` are connected to each other → a *different* node.
   - The center gap separates them. This gap exists so you can place a chip (or button) across it without shorting its pins.

2. **The power rails (top + bottom strips) run horizontally the whole length.**
   - The red `(+)` strip is one long node — useful for distributing 3.3V or 5V.
   - The blue `(−)` strip is one long node — useful for GND.
   - On many breadboards the rail is **broken in the middle**; if your LED won't light from a far hole on the rail, bridge the two halves with a short wire.

### How you actually use it

- Push two component legs into the **same row** (e.g. both in row 5, columns A–E) → they're now wired together, no solder needed.
- Push wires from the ESP32 into the breadboard to bring power, ground, and GPIO signals onto the board.
- Use the `(+)` and `(−)` rails as a "bus": connect ESP32 `3V3` once to `(+)`, ESP32 `GND` once to `(−)`, and then any row can tap into power/ground with a short jumper.

### Reading the layouts in this doc

In every exercise you'll see notation like:

```
    A B C D E   F G H I J
    ─────────────────────
10  o o[R]o o   o[L+]o o o
```

That means: row 10, the resistor leg is in column C (left side), and the LED long leg is in column G (right side). Remember that A–E and F–J are *separate* nodes on the same row — so when an exercise says "resistor and LED in the same row," put them **on the same side of the gap** (e.g. both in A–E), or bridge the two sides with a short jumper. If your circuit doesn't work, this is the first thing to check.

---

## Parts for Learning

| Part | Quantity | Status |
|------|----------|--------|
| ESP32 DevKitC | 1 | From main project |
| Breadboard | 1 | From main project |
| LEDs 5mm (yellow) | 10 | Ordered |
| Resistors 220Ω (1W) | 50 | Ordered |
| Push buttons 6x6mm | 20 | Ordered |
| Male-to-male wires | - | Use male-to-female for now |
| Digital multimeter | 1 | Recommended — any cheap one works ($10–20) |

---

## Basic Concepts

### What is a Circuit?

Electricity needs a complete loop to flow:

```
(+) Power ──→ through components ──→ (-) Ground
     ↑                                    │
     └────────── back to source ──────────┘
```

No complete loop = nothing works.

### LED Basics

```
LED has two legs:

  Long leg (+) ──┐    ┌── Short leg (-)
                 │    │
                 ▼    ▼
              ┌──────────┐
              │   ████   │  (colored dome)
              │  ██████  │
              └────┬┬────┘
                   ││
         Anode (+) ┘└ Cathode (-)
         (long)      (short)
```

- **Long leg = positive (+) = Anode** - connects toward power
- **Short leg = negative (-) = Cathode** - connects toward ground
- Backwards = LED won't light (but won't break)

### Why Resistor?

LED without resistor = too much current = LED burns out.

```
Without resistor:
3.3V ──→ LED ──→ GND
         💀 LED dies!

With resistor:
3.3V ──→ [220Ω] ──→ LED ──→ GND
                    ✓ LED works safely
```

The 220Ω resistor limits current to ~15mA (safe for LED).

### Using a Multimeter

A multimeter is a single instrument that can measure several different electrical things. For these exercises you'll use **three** of its modes. Don't worry about the rest of the dial.

```
   ┌─────────────────────┐
   │     ┌──────────┐    │
   │     │  3.27 V  │    │ ← display
   │     └──────────┘    │
   │                     │
   │       ╱─────╲       │
   │   OFF │  ●  │ V⎓    │ ← rotary dial — pick a mode here
   │     Ω─┤     ├─V~    │
   │   📢)─┤     ├─A⎓    │
   │       ╲─────╱       │
   │                     │
   │  COM   VΩ   10A     │ ← probe sockets
   │   ●     ●    ●      │
   └───┼─────┼────┼──────┘
       │     │    │
     black  red  red (only for amps measurement)
```

**The three modes you need:**

| Mode | Symbol on dial | Use for |
|------|----------------|---------|
| DC Voltage | `V⎓` or `V—` (V with a straight line above a dashed line) | Measuring 3.3V, GPIO HIGH/LOW, voltage drop across a component |
| Resistance | `Ω` | Verifying a resistor's value before you wire it in |
| Continuity | `📢)` (speaker icon) or beep symbol | Checking if two points are electrically connected (the meter beeps if they are) |

**Probes:**
- **Black** lead → always in the `COM` socket. This is the meter's "ground reference."
- **Red** lead → in the `VΩ` socket for voltage / resistance / continuity.

**The two golden rules:**

1. **Voltage = power ON, leads in parallel.** Touch the black probe to the ground side of what you want to measure, the red probe to the high side. The circuit keeps running while you measure.
2. **Resistance and continuity = power OFF, component out of circuit (or at least one leg lifted).** If you try to measure resistance with power applied, you'll get a wrong reading and may damage the meter. With other components in parallel you'll measure the parallel combination, not just the part you care about.

**Current measurement (advanced — skip for now):** moves the red lead to the `10A` socket, breaks the circuit, and inserts the meter *in series*. We won't use this in the exercises below — it's easy to fry the meter or pop its fuse if you forget to move the lead back to `VΩ`.

**Stock probe tips don't fit in breadboard holes.** Most probes are ~2mm; the holes are ~0.7mm — you can't push them in without damaging the contact spring. **Don't try.** Instead, probe the *exposed metal that's already in the breadboard*: every component leg, every jumper-wire pin, and every ESP32 pin header sticks up above the plastic. Touch the probe tip to that metal — it's the same electrical node as the hole below it. The exercises below tell you exactly which leg or pin to touch. (If you do this a lot, ~$8 mini-grabber/IC-hook test leads make it permanent.)

---

## Exercise 1: Light an LED

**Goal:** Make an LED turn on.

### Circuit

```
ESP32 3V3 ──→ Resistor 220Ω ──→ LED (+) ──→ LED (-) ──→ ESP32 GND
```

### How to connect the ESP32

The ESP32 DevKitC is a small board with two rows of pin headers (the metal pins sticking out of each long side). You only need two of those pins for this exercise: **`3V3`** (3.3V power out) and any **`GND`** pin. Look for the labels printed on the silkscreen of the board next to each pin.

There are two common ways to wire it up:

**Option A — ESP32 next to the breadboard, using male-to-female jumpers** *(matches the parts list — start here)*

```
   ┌──────────────┐                           ┌─────────────────────┐
   │   ESP32      │ 3V3 ●━━━━━━━━━━━━━━━━━━━━━│ ← M end pushed into │
   │  DevKitC     │                           │   breadboard hole   │
   │              │ GND ●━━━━━━━━━━━━━━━━━━━━━│                     │
   │  [USB-C] ←── plug into laptop for power  │                     │
   └──────────────┘                           └─────────────────────┘
       ▲
       └─ female end of jumper pushed onto this pin
```

1. Lay the ESP32 flat on the desk next to the breadboard.
2. Take a male-to-female jumper. Push the **female** end onto the ESP32 `3V3` pin. Push the **male** end into the breadboard hole where you want 3V3 to arrive (in this exercise: row 5).
3. Take another M-F jumper. Female end onto a `GND` pin, male end into the breadboard hole for ground (in this exercise: row 11).
4. Plug a USB-C cable into the ESP32 and into your laptop — that's the power.

**Option B — ESP32 plugged directly into the breadboard** *(needs male-to-male jumpers, ignore for now)*

Plug the ESP32 across the center gap so its left pin row lands in one A–E block and its right pin row lands in the matching F–J block on the same rows. Each ESP32 pin is now electrically tied to its breadboard row. You then run M-M jumpers from those rows to the rest of your circuit.

### Steps

1. **Place LED on breadboard:**
   - Long leg (+) in row 10, column **A**
   - Short leg (-) in row 11, column **A**

2. **Place resistor on breadboard:**
   - One leg in row 10, column **C** (same side of the gap as LED+ → connected to it)
   - Other leg in row 5, column **C**

3. **Connect ESP32 to breadboard** (Option A above):
   - ESP32 `3V3` → row 5, column **A** (this row also carries the resistor's other leg in column C — A–E are connected)
   - ESP32 `GND` → row 11, column **C** (same row as LED−)

4. **Plug ESP32 into USB-C** — LED should light up!

### Breadboard Layout

```
        Breadboard (left half only — right half unused for this exercise)
    A B C D E   F G H I J
    ─────────────────────
 5 [W]o[R]o o   o o o o o   ← wire from ESP32 3V3 (col A) + resistor leg (col C)
 6  o o o o o   o o o o o
 7  o o o o o   o o o o o
 8  o o o o o   o o o o o
 9  o o o o o   o o o o o
10 [L+]o[R]o o  o o o o o   ← LED long leg (col A) + resistor other leg (col C)
11 [L-]o[W]o o  o o o o o   ← LED short leg (col A) + wire to ESP32 GND (col C)
```

W = jumper wire to ESP32, R = resistor, L+ = LED long leg, L− = LED short leg.

Everything is on the **left side** of the gap (columns A–E), so columns A through E on each row are one electrical node — the LED leg in column A and the resistor leg in column C are connected.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| LED doesn't light | Check LED direction (flip it) |
| Still nothing | Check resistor is in same row as LED + |
| Still nothing | Check wires to 3V3 and GND |
| LED very dim | Check resistor value (should be 220Ω) |

### Multimeter Checks

These three measurements turn this exercise from "did it light?" into "I can prove what each part is doing." Since the probe tips don't fit in the holes, all measurements below touch **exposed metal**: component legs, the ESP32 pin headers, or the metal pin of an M-M jumper plugged into the row.

**1) Verify the resistor (power off, before plugging in USB-C)**

Easiest done **before** the resistor is on the breadboard at all. Set the dial to `Ω` (200 or 2k range). Hold the resistor in one hand and touch a probe to each metal lead.

- Expected: ~220Ω (display reads `220` on the 200Ω range, or `0.220` on the 2k range)
- If wildly different → wrong resistor, wrong range, or poor probe contact.

If it's already plugged in, lift one leg out (just one is enough to isolate it) and probe each lead.

**2) Confirm 3.3V is actually arriving (power on)**

Set the dial to `V⎓` (DC voltage, 20V range). Plug in USB-C so the LED is lit.

The cleanest way is to skip the breadboard entirely and probe the ESP32 directly:

- **Black probe** → touch the metal of the ESP32 `GND` pin (the pin under the female jumper, where it meets the header).
- **Red probe** → touch the metal of the ESP32 `3V3` pin the same way.
- Expected: ~3.3V (often 3.25–3.30V).

Alternative if the ESP32 pins are obscured by the female jumpers: push a spare M-M jumper into row 5 (any free hole) and another into row 11 — now you have two tall metal pins sticking up. Touch the probes to those.

If you read 0V → the ESP32 jumper has slipped off the pin, or you've grabbed the wrong pin on the ESP32 (3V3 vs 3V3-EN vs VIN). Look at the silkscreen.

**3) Check the voltage drop across each component (Kirchhoff's voltage law)**

Same DC voltage mode, power on. The resistor and LED both have legs poking up from the breadboard — touch the probes directly to those legs.

| Across | Where to touch | Expected | Why |
|--------|---------------|----------|-----|
| Resistor | one probe on each of the resistor's two legs | ~1.4V | What the resistor "burns off" |
| LED | one probe on each of the LED's two legs | ~1.9V | The LED's forward voltage drop |
| Whole circuit | probe on resistor's row-5 leg + probe on LED's row-11 leg | ~3.3V | Sum of the two = supply ✓ |

This is the most important measurement in basic electronics: voltages across components in series **add up to the supply**. If your two readings don't sum to ~3.3V, your probes drifted off the metal between readings — try again with firmer contact.

---

## Exercise 2: Button-Controlled LED

**Goal:** Press button = LED on. Release = LED off.

### Circuit

```
ESP32 3V3 ──→ Button ──→ Resistor 220Ω ──→ LED (+) ──→ LED (-) ──→ ESP32 GND
```

### How Button Works

```
Button has 4 pins (but only 2 connections):

    Pin1 ━━━━ Pin2      ← always connected
         ╲  ╱
          ╲╱  (press to connect)
         ╱╲
    Pin3 ━━━━ Pin4      ← always connected

Pin1-Pin2 are connected to each other.
Pin3-Pin4 are connected to each other.
Press button = Pin1/2 connects to Pin3/4.
```

Place button **across the center gap** of breadboard:

```
    A B C D E     F G H I J
    ───────────────────────
15  o o[B][B]o   o[B][B]o o   ← button spans the gap
```

### Steps

1. **Place button across center gap** (row 15)

2. **Place LED on breadboard:**
   - Long leg (+) in row 20
   - Short leg (-) in row 21

3. **Place resistor:**
   - One leg in row 15 (same row as button output side)
   - Other leg in row 20 (same row as LED +)

4. **Connect wires:**
   - ESP32 3V3 → row 15 (button input side, column A-B)
   - ESP32 GND → row 21 (LED -)

5. **Press button = LED lights!**

### Breadboard Layout

```
    A B C D E     F G H I J
    ───────────────────────
15  o[W][B][B]o   o[B][B][R]o   ← wire from 3V3, button, resistor
16  o o o o o     o o o o o
...
20  o o o o o     o o[R][L+]o   ← resistor other leg, LED +
21  o o o o o     o o o[L-][W]  ← LED -, wire to GND
```

W = wire, B = button pin, R = resistor, L = LED

### Multimeter Checks

The button is the **easiest** place to use thick probes — the button's own pins stick out the bottom and sides; you don't need the breadboard at all for the first check.

**1) Map out the button's internal wiring (power off, button held in your hand)**

Set the dial to continuity (`📢)` / beep). Hold the button in your hand, **off** the breadboard. The 4 pins protrude — easy to touch with thick probes. Touch one probe to one pin and the other probe to each of the other three in turn:

- Two of the pairs will beep continuously → **always-connected** pairs.
- The other two pairs only beep **when you press the button** with your finger while probing.

Do this once and you'll know how to orient any 4-pin tactile button forever.

**2) Watch the button output toggle (power on, DC voltage mode)**

Once the circuit is assembled and powered, you need to probe two points without poking holes:

- **Black probe** → ESP32 `GND` pin header (the same metal pin you connected the GND jumper to).
- **Red probe** → the **resistor leg** that's plugged into the button output row (row 15 on the right side of the gap). The leg sticks up; touch the probe to it.

Then:

- Button released → ~0V (output floating — may read small random numbers, that's normal)
- Button pressed → ~3.3V

If pressing changes nothing, the button isn't bridging the gap correctly (revisit check #1 to confirm which two pins switch).

---

## Exercise 3: Multiple LEDs

**Goal:** Light 3 LEDs with one button.

### Circuit

```
                    ┌→ [220Ω] → LED1 → GND
3V3 → Button ───────┼→ [220Ω] → LED2 → GND
                    └→ [220Ω] → LED3 → GND
```

Each LED needs its own resistor!

### Steps

1. Set up button as in Exercise 2
2. Add 3 LEDs, each with own 220Ω resistor
3. All resistors connect to button output (same row)
4. All LED (-) legs connect to GND (use power rail)

### Tips

- Use the **power rails** (+ and -) on breadboard edges
- Connect ESP32 GND to (-) rail once
- Connect all LED (-) legs to (-) rail

### Multimeter Checks

Power rails introduce a new failure mode: a poorly-seated jumper to the rail breaks *all* your LEDs at once. Use the multimeter to verify the rail is live.

**1) Check the GND rail with continuity (power off)**

Set the dial to continuity. The (−) rail is just a long row of holes — to give your thick probes something to touch, **push a spare M-M jumper into the rail at the far-right end**. Now the metal pin of that jumper sticks up and represents the rail.

- Black probe → ESP32 `GND` pin header.
- Red probe → the M-M jumper pin you just inserted at the far end of the rail.
- Should beep. If silent → your breadboard's rail is **split in the middle** (common!). Bridge the two halves with a short M-M jumper across the split and re-test.

**2) Verify each LED actually has voltage across it (power on, button pressed)**

Set the dial to DC voltage, hold the button down. The LED legs poke up out of the breadboard — touch one probe to each leg of an LED.

- Each LED should read ~1.9V across its two legs.
- One LED reads 0V → that branch's resistor or LED is loose; push the legs in deeper.
- One LED reads ~3.3V → it's in backwards (no current flowing, full supply voltage across it). Flip it.

---

## Exercise 4: Wave Chase (5 Yellow LEDs)

**Goal:** Drive 5 yellow LEDs from ESP32 code in a chase pattern — like a surf level meter or running light.

Since all your LEDs are the same color, instead of a traffic light we'll do a *chase / level-meter* pattern. Same wiring concept, more useful for the surf-frame project (you can later use a strip like this as a wave-quality bar).

### Circuit

```
ESP32 GPIO23 ──→ [220Ω] ──→ LED1 ──→ GND
ESP32 GPIO22 ──→ [220Ω] ──→ LED2 ──→ GND
ESP32 GPIO21 ──→ [220Ω] ──→ LED3 ──→ GND
ESP32 GPIO19 ──→ [220Ω] ──→ LED4 ──→ GND
ESP32 GPIO18 ──→ [220Ω] ──→ LED5 ──→ GND
```

Each LED has its own GPIO + own 220Ω resistor. All cathodes (-) tie to the breadboard (-) rail, which goes once to ESP32 GND.

### Uploading Code to the ESP32

This is the first exercise where the ESP32 actually runs your own program. Until now USB-C just delivered 3.3V; from here on you'll be writing C++ in the Arduino IDE and pushing it onto the chip.

**One-time setup (do this once per laptop)**

1. **Install the Arduino IDE** from `arduino.cc/en/software` (free, ~200MB).
2. **Add ESP32 board support:**
   - Open `Arduino IDE → Settings → Additional boards manager URLs`.
   - Paste: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Open `Tools → Board → Boards Manager`, search "esp32", install **"esp32 by Espressif Systems"** (~200MB, takes a few minutes).
3. **Install the USB-serial driver** (only needed if your laptop doesn't see the ESP32 when you plug it in):
   - DevKitC boards usually have a CP210x chip. Driver: `silabs.com/developers/usb-to-uart-bridge-vcp-drivers`.
   - macOS may require allowing the kernel extension in `System Settings → Privacy & Security` after install.

**Per-upload steps (every time you flash a new sketch)**

1. **Plug the ESP32 into USB-C.** Same cable that's been powering it for the LED exercises.
2. **Open the Arduino IDE** and paste the sketch into a new file (`File → New Sketch`).
3. **Select the board:** `Tools → Board → esp32 → ESP32 Dev Module`.
4. **Select the port:** `Tools → Port → /dev/cu.SLAB_USBtoUART` (or `/dev/cu.usbserial-XXXX` on macOS, `COM3`/`COM4`/etc. on Windows). If no port appears, the driver isn't installed or the cable is power-only — try a different cable.
5. **Click the right-arrow "Upload" button** (top-left of the IDE). The IDE compiles, then flashes. You'll see "Connecting...." in the bottom console; if it stalls there, **hold the `BOOT` button** on the ESP32 until "Writing" begins, then release.
6. **Done when you see "Hard resetting via RTS pin..."** — the sketch is now running. The ESP32 keeps running it forever, even after you unplug and replug.

**Common upload errors**

| Symptom | Fix |
|---------|-----|
| `No DFU capable USB device` / port doesn't exist | USB-serial driver not installed, or USB cable is power-only (try another cable) |
| `Failed to connect to ESP32: Timed out waiting for packet header` | Hold `BOOT` button during "Connecting…" until flashing starts |
| Upload succeeds but nothing happens | Press the `EN` (reset) button once to restart the chip |
| `Permission denied` on `/dev/cu...` (macOS/Linux) | Close any other program using the port (screen, minicom, PlatformIO) |

### Arduino Code: Knight-Rider Chase

```cpp
const int LED_PINS[] = {23, 22, 21, 19, 18};
const int NUM_LEDS = 5;

void setup() {
  for (int i = 0; i < NUM_LEDS; i++) {
    pinMode(LED_PINS[i], OUTPUT);
  }
}

void loop() {
  // Sweep left to right
  for (int i = 0; i < NUM_LEDS; i++) {
    digitalWrite(LED_PINS[i], HIGH);
    delay(120);
    digitalWrite(LED_PINS[i], LOW);
  }
  // Sweep right to left
  for (int i = NUM_LEDS - 2; i > 0; i--) {
    digitalWrite(LED_PINS[i], HIGH);
    delay(120);
    digitalWrite(LED_PINS[i], LOW);
  }
}
```

**How the code works**

Every Arduino sketch has exactly two functions: `setup()` runs **once** when the chip boots, and `loop()` runs **forever** in an infinite cycle. You don't write a `main()` — the framework provides one that calls these for you.

- `const int LED_PINS[] = {23, 22, 21, 19, 18};` — an array listing the GPIO numbers you wired LEDs to. Order matters: index 0 is the leftmost LED, index 4 is the rightmost. Change a number here and you've moved an LED in software without touching wires.
- `const int NUM_LEDS = 5;` — how many entries are in the array. C++ doesn't track array length for you, so you pass it around manually.
- `pinMode(pin, OUTPUT)` — tells the ESP32 "I'm going to *drive* this pin, not read it." Required before `digitalWrite` works. The `for` loop inside `setup()` configures all 5 pins in one go.
- `digitalWrite(pin, HIGH)` — sets the pin to ~3.3V (LED on). `digitalWrite(pin, LOW)` sets it to 0V (LED off). Same `digitalWrite` you saw measured in the multimeter section.
- `delay(120)` — pauses the chip for 120 milliseconds. Without this, the LED would flash on and off faster than your eye can see and just look dim.
- The first `for` loop sweeps `i` from 0 to 4 (left → right), turning each LED on for 120ms then off before moving to the next.
- The second `for` loop sweeps backward from `i = 3` down to `1` (right → left), skipping the endpoints so they don't blink twice in a row when the direction reverses. Then `loop()` returns and Arduino calls it again — the chase repeats forever.

To slow the chase, increase `delay(120)`. To reverse direction, swap the two for-loops. To add LEDs, extend `LED_PINS[]` and update `NUM_LEDS`.

### Arduino Code: Level Meter (bonus)

Light up LEDs 1..N to show a "level" — useful later as a surf-score indicator.

```cpp
const int LED_PINS[] = {23, 22, 21, 19, 18};
const int NUM_LEDS = 5;

void showLevel(int level) {  // level 0..5
  for (int i = 0; i < NUM_LEDS; i++) {
    digitalWrite(LED_PINS[i], i < level ? HIGH : LOW);
  }
}

void setup() {
  for (int i = 0; i < NUM_LEDS; i++) pinMode(LED_PINS[i], OUTPUT);
}

void loop() {
  for (int lvl = 0; lvl <= NUM_LEDS; lvl++) {
    showLevel(lvl);
    delay(400);
  }
}
```

**How the code works**

Same `setup()` / `loop()` skeleton as the chase — what's new is the helper function and the use of a *ternary* expression.

- `void showLevel(int level)` — a function you defined yourself. It takes a number 0–5 and lights up that many LEDs from the left. Splitting logic into named helpers like this is what keeps `loop()` readable as sketches grow.
- `i < level ? HIGH : LOW` — C++'s ternary "if-else expression." Reads as: "if `i` is less than `level`, the value is `HIGH`, otherwise `LOW`." Equivalent to writing `if (i < level) digitalWrite(LED_PINS[i], HIGH); else digitalWrite(LED_PINS[i], LOW);` but on one line.
- So when `level == 3`, indices 0, 1, 2 light up (those are `< 3`) and indices 3, 4 stay dark — a 3-of-5 bar.
- The `loop()` cycles `lvl` from 0 to 5, redrawing the bar every 400ms — you'll see the bar fill up, then snap back to empty when the loop restarts.

This is the actual building block for a surf-quality meter: replace the `for (int lvl …)` demo loop with a call like `showLevel(currentSurfScore)` and you have a hardware indicator that mirrors a number from your code.

You have 10 yellow LEDs total — feel free to extend `LED_PINS[]` to 8 or 10 if you want a longer bar (just pick more free GPIOs, e.g. 23, 22, 21, 19, 18, 5, 17, 16).

### Multimeter Checks

Now that the LEDs are driven by code instead of straight 3.3V, the multimeter lets you actually *see* `digitalWrite` change a pin's voltage. Best done by probing the **ESP32 pin headers directly** — no breadboard hole-poking needed.

**1) See a GPIO toggle in real time**

Upload the level-meter sketch with a slow delay (`delay(2000)` between levels). Set to DC voltage.

- **Black probe** → ESP32 `GND` pin header.
- **Red probe** → ESP32 `GPIO23` pin header (or whichever LED you want to watch).

Watch the display as the sketch runs:

- When that LED is OFF → ~0V (GPIO LOW)
- When that LED is ON → ~3.3V (GPIO HIGH)

You're literally watching `digitalWrite(pin, HIGH)` change the voltage on a wire. Move the red probe along the ESP32 header from pin to pin to see different LEDs' GPIOs in turn.

**2) Check what a *floating* pin looks like**

Comment out `pinMode(LED_PINS[i], OUTPUT)` for one pin and re-upload. Probe that GPIO pin on the ESP32 header (black on GND, red on the GPIO pin) — the reading will bounce around to random values (sometimes 1.5V, sometimes 0.8V). That's a "floating" input pin with no defined state. This is why digital inputs need pull-up or pull-down resistors — a topic for the next project.

---

## Exercise 5: Play Sound on a Speaker

**Goal:** Play a tone through a small speaker using ESP32's built-in DAC.

### Parts

| Part | Notes |
|------|-------|
| 8ohm speaker (20mm) | Small, with P2.0 terminal wire |
| 220ohm resistor | Same ones from LED exercises |

### Why a Resistor?

Same reason as LEDs — the speaker without a resistor would draw too much current:

```
Without resistor:
GPIO25 ──→ Speaker (8ohm) ──→ GND
           3.3V / 8ohm = 412mA  💀 ESP32 GPIO max is ~12mA!

With 220ohm resistor:
GPIO25 ──→ [220Ω] ──→ Speaker (8ohm) ──→ GND
           3.3V / 228ohm = 14mA  ✓ Safe!
```

The sound will be quiet but audible — perfect for a notification sound.

### Circuit

```
ESP32 GPIO25 ──→ [220Ω resistor] ──→ Speaker (+) ──→ Speaker (-) ──→ ESP32 GND
```

### Preparing the Speaker

Your speaker has a **JST PH2.0 connector** (small 2-pin white plug) with two wires:
- **Red wire** = (+) positive
- **Black wire** = (-) negative / ground

The JST plug doesn't fit in a breadboard. For prototyping, **cut the connector off**:
1. Cut the wires ~3cm from the connector (keep the connector for later)
2. Strip ~5mm of insulation from each wire end
3. Twist the bare copper so it's neat
4. Push bare wire ends into breadboard holes

```
Before:  [Speaker] ~~~red~~~ ─┐
                               ├─ [JST PH2.0 plug]  ← cut here
         [Speaker] ~~~black~~ ─┘

After:   [Speaker] ~~~red~~~[bare end]    ← push into breadboard
         [Speaker] ~~~black~[bare end]    ← push into breadboard
```

### Steps

1. **Place resistor on breadboard:**
   - One leg in row 25 (same row as ESP32 GPIO25 pin)
   - Other leg in row 26

2. **Connect speaker wires:**
   - Red wire (stripped end) → row 26 (same row as resistor output)
   - Black wire (stripped end) → breadboard (-) rail (GND)

3. **Make sure GND rail is connected:**
   - ESP32 GND → breadboard (-) rail

### Breadboard Layout

```
    A B C D E     F G H I J
    ───────────────────────
25  o o[GPIO25]━━━[R]o o o   ← ESP32 pin + resistor leg 1
26  o o o o o   o[R][red]o o  ← resistor leg 2 + speaker red wire
(-)  ──────────────[blk]────   ← speaker black wire to GND rail
```

R = resistor, red = speaker red wire, blk = speaker black wire

### Arduino Code: Simple Beep

```cpp
#define SPEAKER_PIN 25  // DAC pin

void setup() {
  // Nothing needed - DAC works immediately
}

void loop() {
  // Play a simple tone using DAC
  for (int i = 0; i < 500; i++) {
    dacWrite(SPEAKER_PIN, 255);  // High
    delayMicroseconds(500);      // 1kHz tone
    dacWrite(SPEAKER_PIN, 0);    // Low
    delayMicroseconds(500);
  }
  delay(2000);  // Wait 2 seconds, repeat
}
```

You should hear a 1kHz beep for half a second, then silence, then repeat.

### Arduino Code: Ocean Wave Sound

A real wave isn't a rising pitch — it's **broadband noise** shaped by an **asymmetric volume envelope**: a slow approach, a sharp *crash*, then a long washing fade with rolling turbulence in the foam. A symmetric in-out swell sounds like breathing; an asymmetric build-crash-wash is what reads as a wave.

```cpp
#define SPEAKER_PIN 25

// One ocean wave: ~6 seconds, in three distinct phases.
//   0%   → 30%  : nearly-silent approach, building only at the very end
//   30%  → 36%  : CRASH — short burst of peak-clipped noise (the impact)
//   36%  → 100% : wash that drops fast then slowly tails out (foam fading)
void playWave() {
  const unsigned long duration_us = 6000000;   // 6 s total
  const float crash_start = 0.30f;             // when the crash hits
  const float crash_end   = 0.36f;             // 6% of 6 s = ~360 ms of pure crash
  const float loudness    = 2.5f;              // overall gain — clips heavily during crash

  unsigned long start = micros();
  int prev = 128, prev2 = 128;

  float surge = 1.0f;
  unsigned long surge_next = 0;

  while (micros() - start < duration_us) {
    unsigned long elapsed = micros() - start;
    float t = (float)elapsed / duration_us;

    // Three-phase envelope.
    float env;
    if (t < crash_start) {
      // Approach: pow(.., 4) keeps it near zero until just before the crash —
      // this is what kills the "inhale" feel. The wave is barely there, then
      // suddenly it's on top of you.
      float build_t = t / crash_start;
      env = pow(build_t, 4.0f) * 0.5f;
    } else if (t < crash_end) {
      // Crash: pinned high. Combined with loudness=2.5 this hard-clips the DAC,
      // which is what produces the percussive "smash" transient.
      env = 1.6f;
    } else {
      // Wash: exponential decay — drops fast, then long tail. This is what
      // foam sounds like, vs. the linear pow() fade that sounds like exhaling.
      float decay_t = (t - crash_end) / (1.0f - crash_end);
      env = exp(-2.5f * decay_t);
    }

    // Faster surge re-roll (50 ms) — more violent turbulence in the foam.
    if (elapsed > surge_next) {
      surge = 0.7f + 0.6f * (random(0, 100) / 100.0f);
      surge_next = elapsed + 50000;
    }

    int noise = random(-127, 128);
    int sample = 128 + (int)(noise * env * surge * loudness);

    // Two-pass low-pass for "watery" rather than "static-y" texture.
    sample = (sample + prev)  / 2;  prev  = sample;
    sample = (sample + prev2) / 2;  prev2 = sample;

    if (sample < 0) sample = 0;
    if (sample > 255) sample = 255;
    dacWrite(SPEAKER_PIN, sample);
    delayMicroseconds(60);
  }
  dacWrite(SPEAKER_PIN, 128);
}

void setup() {
  playWave();
}

void loop() {
  delay(1500);
  playWave();
}
```

**The three changes that kill the breathing feel**

| Change | What it fixes |
|--------|---------------|
| `pow(build_t, 4)` instead of `pow(.., 1.5)` in the approach | Wave is silent for most of the build, not gradually rising — no "inhale" |
| Dedicated crash phase pinned at `env = 1.6f` for ~360 ms | A real percussive *smash*, not a peak-of-a-curve |
| `exp(-2.5 * t)` decay instead of `pow(1-t, 1.2)` | Foam drops fast then tails out — wash, not "exhale" |

If it still feels too smooth, the next dial to turn is `loudness` — raise to `3.5f`. The DAC will clip even harder, which on a small speaker reads as more violent crash energy.

**The hardware ceiling (this is probably your real bottleneck)**

Software can shape the *character* of the sound, but **how loud it gets** is set by the resistor + speaker. With your current 220Ω resistor:

- Peak current = 3.3V ÷ (220 + 8) ≈ **14 mA**
- That's safe for the GPIO but really quiet — roughly a wristwatch alarm at arm's length.

To make the crash actually *crash*, lower the resistor:

| Resistor | Peak current | Loudness | Risk |
|----------|--------------|----------|------|
| 220Ω (current) | ~14 mA | Quiet | Totally safe |
| **100Ω** | ~30 mA | 2× louder | Slightly above GPIO spec but fine for short bursts |
| 47Ω | ~57 mA | 4× louder | Over spec — only OK if waves are <10% of the time |
| 0Ω (no resistor) | ~412 mA | Maximum | **Don't.** GPIO permanently damaged. |

For a notification sound that fires every few minutes, **100Ω is the sweet spot**. You have 50 of them in your parts kit.

**For real surf-room volume — add an amp module**

A `PAM8403` board (~$1, ~$5 for a pack of 5) is a tiny class-D amp the size of a postage stamp. Wiring:

```
ESP32 GPIO25 ──→ amp INPUT
ESP32 5V     ──→ amp VCC          (use the 5V pin, not 3V3)
ESP32 GND    ──→ amp GND
amp OUT+/OUT- ──→ speaker
```

No current-limiting resistor needed once the amp is in the loop — the amp drives the speaker, the GPIO just hands it a line-level signal. With this setup the same code becomes loud enough to fill a room. Order one if you actually want a "real wave" experience; the cheap path tops out at "quiet desk notification."

**Other tuning knobs (software-only)**

- **Even longer waves:** raise `duration_us` to `8000000` (8 s).
- **Bigger crash, shorter approach:** lower `crash_start` to `0.20f` and raise `crash_end` to `0.30f`.
- **More turbulent foam:** shorten surge interval — change `+ 50000` to `+ 25000` (25 ms re-rolls).
- **Sets of waves (3 close, then a long lull):**
  ```cpp
  void loop() {
    for (int i = 0; i < 3; i++) { playWave(); delay(1500); }
    delay(6000);
  }
  ```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| No sound | Check speaker wires are in correct rows |
| No sound | Check resistor connects GPIO25 row to speaker (+) row |
| Very quiet | Normal with 220ohm resistor — hold speaker near ear |
| Buzzy/distorted | Reduce dacWrite max value from 255 to 150 |

### Multimeter Checks

The speaker is the first time the signal changes faster than the multimeter can track — a great way to learn what your meter *can't* do.

**1) Speaker coil resistance (power off, speaker disconnected from breadboard)**

This one is easy with thick probes — the speaker wires are bare/stripped at the ends, so you can hold them next to the probe tips or pinch the wire-and-probe together with your fingers.

Set the dial to `Ω` (200 range). Touch a probe to each stripped wire end:

- Expected: ~7–9Ω (matches the "8 ohm" label).
- If `OL` (open / infinite) → the coil or wire is broken.

**2) DAC output voltage while the beep plays**

Set to DC voltage. Probe the ESP32 directly — no breadboard contact needed:

- **Black probe** → ESP32 `GND` pin header.
- **Red probe** → ESP32 `GPIO25` pin header.

With the simple beep sketch running, you'll see something like **1.5V** — *not* 3.3V or 0V.

That's because the DAC is switching between 0V and 3.3V at 1kHz, way faster than the meter samples. The display shows the *average* voltage. The fact that you see ~half of 3.3V is your evidence that the signal really is oscillating — even though the meter can't show the wave shape (an oscilloscope would).

**3) AC voltage mode (bonus)**

Switch the dial to `V~` (AC voltage). Same probe positions on the ESP32 header. You'll now see something like **0.8–1.5V AC** — the meter's estimate of the AC component of the signal. Different number, same underlying waveform.

### What's Different from LEDs?

| LED | Speaker |
|-----|---------|
| ON or OFF (digital) | Varying voltage (analog/DAC) |
| `digitalWrite(pin, HIGH)` | `dacWrite(pin, 0-255)` |
| GPIO can be any pin | DAC only on GPIO25 or GPIO26 |
| Light | Sound |

Both need a resistor to limit current. Same concept, different output!

---

## Exercise 6: E-Ink "Hello, Surf!" (1.54" Display)

**Goal:** Drive the Waveshare 1.54" e-ink display from the ESP32 — write text and draw a rectangle. This is a dry-run for the real frame: same library (`GxEPD2`), same pin assignments, just a smaller screen.

### Why this exercise

The 1.54" panel is the **practice** display. It's cheap, fast to refresh, and uses the exact same SPI wiring as the 13.3" production display. If you can make the small one work on the breadboard, the big one is identical wiring + a different driver class.

### Parts

| Part | Notes |
|------|-------|
| Waveshare 1.54" e-Paper Module | 200×200 pixels, B/W, SSD1681 controller (most common variant) |
| 8 male-to-female jumpers | One per HAT pin |
| ESP32 + breadboard | From previous exercises |

### Circuit (8 wires)

The HAT has 8 labeled pins along its header. Wire them straight to the ESP32 — no resistors, no capacitors. The HAT has all the protection circuitry on-board.

| ESP32 pin | E-Ink HAT pin | Purpose |
|-----------|---------------|---------|
| 3V3 | VCC | Power (3.3V — never 5V) |
| GND | GND | Ground |
| GPIO23 | DIN | SPI Data In (MOSI) |
| GPIO18 | CLK | SPI Clock |
| GPIO5 | CS | Chip Select |
| GPIO17 | DC | Data/Command toggle |
| GPIO16 | RST | Reset |
| GPIO4 | BUSY | Tells ESP32 "I'm refreshing — wait" |

**SPI is just digital outputs in a specific protocol.** DIN/CLK/CS work the same way the LED GPIOs in Exercise 4 worked — the ESP32 toggles them HIGH/LOW. The library handles the protocol; you just provide the pins.

The two e-ink-specific pins:

- **DC (Data/Command):** When LOW the ESP32 is sending a command ("clear yourself"); when HIGH it's sending pixel data. The library flips it for you.
- **BUSY:** This one goes **the other direction** — the *display* tells the *ESP32* whether it's still processing. The library reads it and waits before sending more.

### Library install (one-time)

1. Open the Arduino IDE → `Tools → Manage Libraries...`
2. Search for **`GxEPD2`** (by Jean-Marc Zingg) → click **Install**.
3. The IDE will prompt "install dependencies" — say **yes**. This pulls in `Adafruit GFX` and `Adafruit BusIO` automatically.

That's it. No URLs, no manual zip files.

### Steps

1. **Wire up all 8 connections** per the table above.
2. **Plug ESP32 into USB-C.** Don't power the HAT separately — VCC from the ESP32's 3V3 pin is the only supply.
3. **Open a new sketch**, paste the code below.
4. **Upload** (`Tools → Board → ESP32 Dev Module`, port `/dev/cu.usbserial-0001`, hit Upload).
5. After upload, watch the screen. **Don't panic when it flashes black-white-black for 2 seconds** — that's a full refresh, not a malfunction. After ~3 seconds you should see "Hello, surf!" with a border.

### Arduino Code: Hello, Surf!

```cpp
#include <GxEPD2_BW.h>
#include <Fonts/FreeMonoBold9pt7b.h>

// Pin assignments — match the hardware_diagram.md wiring.
#define EPD_CS    5
#define EPD_DC    17
#define EPD_RST   16
#define EPD_BUSY  4

// 1.54" B/W Waveshare HAT, SSD1681 controller (the "v2" variant).
// If your display is older / different, swap GxEPD2_154_D67 for one of:
//   GxEPD2_154      — original SSD1608 (older HAT, no "v2" sticker)
//   GxEPD2_154_M09  — alternate variant
//   GxEPD2_154c     — 3-color (B/W/Red) variant (use #include <GxEPD2_3C.h>)
GxEPD2_BW<GxEPD2_154_D67, GxEPD2_154_D67::HEIGHT> display(
    GxEPD2_154_D67(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY)
);

void setup() {
  Serial.begin(115200);
  display.init(115200);            // arg = serial debug speed (matches Serial.begin)
  display.setRotation(1);          // 0=portrait, 1=landscape, 2/3=flipped
  display.setFont(&FreeMonoBold9pt7b);
  display.setTextColor(GxEPD_BLACK);

  // Full-window refresh: redraw the entire screen.
  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);             // wipe to white

    display.setCursor(20, 50);
    display.print("Hello, surf!");

    display.setCursor(20, 90);
    display.print("ESP32 + e-ink");

    display.drawRect(5, 5, 190, 190, GxEPD_BLACK);  // border
  } while (display.nextPage());

  // Put the panel into deep sleep — uses microamps, image stays.
  display.hibernate();
}

void loop() {
  // Nothing to do. E-ink keeps the image without any power.
}
```

**How the code works**

- `#include <GxEPD2_BW.h>` — the black/white driver. There's also `<GxEPD2_3C.h>` (3-color) and `<GxEPD2_7C.h>` (7-color, used by the production firmware).
- `GxEPD2_BW<GxEPD2_154_D67, …> display(...)` — declares the global `display` object. The first template parameter is the **panel driver class** — this is what changes between display models. The pin numbers passed to the constructor are exactly the four control pins from the wiring table; the SPI pins (DIN, CLK) are picked up automatically from the ESP32's hardware SPI defaults.
- `display.init(115200)` — wakes the panel and initializes SPI. The number is the serial-debug speed for the library's logs, not an SPI speed.
- `display.setFullWindow()` + `firstPage()` / `nextPage()` — GxEPD2 uses a "paged" rendering loop because the framebuffer is too big to fit in RAM all at once on small chips. The library renders a strip, sends it, renders the next strip, and so on. **You always wrap your drawing in `do { … } while (display.nextPage());`.**
- `fillScreen(GxEPD_WHITE)` — wipe to white. Without this, the previous content stays on-screen and overlaps the new content.
- `setCursor(x, y)` + `print()` — text drawing. `(x, y)` is the **baseline** of the first character (not the top-left corner) — so `y=50` means the text *baseline* is 50px down. If your text disappears off the top, raise `y`.
- `drawRect(x, y, w, h, color)` — outlined rectangle. Use `fillRect()` for solid.
- `display.hibernate()` — put the panel into deep sleep. **Do this whenever you're done drawing.** E-ink draws current only during refresh and while idle-but-awake; once hibernated it's effectively off.

### Arduino Code: Bonus — Surf Score Bar

A fake "surf rating" indicator drawn natively on the e-ink. This is the actual building block for the rating badge in `config.yaml`'s overlay system.

```cpp
#include <GxEPD2_BW.h>
#include <Fonts/FreeMonoBold12pt7b.h>

#define EPD_CS    5
#define EPD_DC    17
#define EPD_RST   16
#define EPD_BUSY  4

GxEPD2_BW<GxEPD2_154_D67, GxEPD2_154_D67::HEIGHT> display(
    GxEPD2_154_D67(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY)
);

void drawScore(int score /* 0..10 */) {
  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);

    display.setFont(&FreeMonoBold12pt7b);
    display.setTextColor(GxEPD_BLACK);
    display.setCursor(10, 30);
    display.print("SURF: ");
    display.print(score);
    display.print("/10");

    // Bar outline
    display.drawRect(10, 60, 180, 30, GxEPD_BLACK);
    // Filled portion proportional to score
    int filled = (180 - 4) * score / 10;
    display.fillRect(12, 62, filled, 26, GxEPD_BLACK);
  } while (display.nextPage());
  display.hibernate();
}

void setup() {
  display.init(115200);
  display.setRotation(1);
  drawScore(7);  // Pretend the surf is good today
}

void loop() { }
```

Change the `7` to any 0–10 value, re-upload, and watch the bar resize. This is exactly the pattern the production firmware uses — render once, hibernate, deep-sleep the ESP32 for 30 minutes, wake up, render again.

### Multimeter Checks

E-ink is the first time you've driven a chip that talks back. Most checks confirm the wires are alive — actual data verification needs an oscilloscope or logic analyzer, which is overkill here.

**1) VCC arrives at the HAT (power on, DC voltage)**

- Black probe → ESP32 GND pin header.
- Red probe → the HAT's `VCC` pin (or the male end of the red jumper, sticking up from a free hole on the breadboard if you're routing through it).
- Expected: ~3.3V. If 0V → jumper slipped off the ESP32 3V3 pin.

**2) BUSY signal toggles during refresh (continuity OFF, DC voltage)**

This is the most useful e-ink-specific check. While the screen is refreshing, BUSY is HIGH (~3.3V); when idle, BUSY is LOW (0V).

- Modify the sketch to refresh in a loop with a long delay:
  ```cpp
  void loop() {
    drawScore(random(0, 11));
    delay(10000);
  }
  ```
- Black probe → GND. Red probe → the male end of the BUSY jumper (GPIO4 side).
- Watch the meter as the screen refreshes. You'll see the voltage flip from ~0V to ~3.3V for ~2 seconds during the refresh, then back to 0V. That's the panel telling the ESP32 "still working… still working… done."
- If BUSY stays at 0V or 3.3V forever → the wire is disconnected or the panel never started a refresh.

**3) Reset pulse on RST (DC voltage, at boot)**

Hard to catch — the reset pulse is ~10 ms. If your meter is fast and you press the ESP32's `EN` button while probing RST, you might see a brief dip to 0V. Mostly: don't worry about RST unless the screen never initializes.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Screen stays blank | Check `EPD_CS=5, DC=17, RST=16, BUSY=4` match your wires |
| `error: 'GxEPD2_154_D67' was not declared` | Library not installed — `Tools → Manage Libraries → GxEPD2` |
| Screen shows garbage / random pixels | Wrong driver class — try `GxEPD2_154` or `GxEPD2_154_M09` (look at the back of the display for a model code) |
| Text appears off the top edge | `setCursor(x, y)` y-coordinate is the **baseline**, not the top — raise `y` |
| Image stays after upload of a blank sketch | E-ink **keeps the last image without power** — that's a feature, not a bug. Run a `fillScreen(GxEPD_WHITE)` sketch to clear it |
| Visible "ghost" of the previous image | Normal between fast refreshes. A single full-window refresh clears it; never refresh more than ~once every 3 seconds in production |
| `display.init()` hangs / times out | BUSY pin not wired or connected to the wrong GPIO — the library waits forever for it |

### Why this exercise matters for the main project

Once you're done, the only differences when you swap to the 13.3" production display are:

1. The driver class changes from `GxEPD2_154_D67` to `GxEPD2_730c_GDEY073D46`.
2. The header changes from `<GxEPD2_BW.h>` to `<GxEPD2_7C.h>` (7-color).
3. The colors change from `GxEPD_BLACK`/`GxEPD_WHITE` to also include `GxEPD_RED`, `GxEPD_YELLOW`, `GxEPD_BLUE`, `GxEPD_GREEN`, `GxEPD_ORANGE`.

Pin assignments, drawing API, paged rendering loop, hibernate-after-draw — all identical. That's why this exercise is "free practice" — the muscle memory you build here transfers 1:1 to the real frame.

---

## Exercise 7: Raspberry Pi Server (Pi Zero 2 W)

**Goal:** Get the Raspberry Pi onto your WiFi, SSH into it from your laptop, and run a Python HTTP server that the ESP32 can fetch from. This is the *server half* of the production system — without it, the ESP32 has nothing to display.

### Why this exercise

The ESP32 doesn't process images — the Pi does. The Pi grabs camera snapshots, scores the surf, draws overlays, and serves a finished `.bmp` over HTTP. The ESP32 just wakes up every 30 minutes, GETs that file, and pushes it to the e-ink display.

So this exercise is about getting the *other side of the wire* working. No breadboard, no GPIOs — pure software setup.

### Parts

| Part | Notes |
|------|-------|
| Raspberry Pi Zero 2 W | The model in the project — has WiFi built in |
| microSD card | 8GB+ recommended, Class 10 |
| Micro USB cable + 5V charger | Pi Zero uses Micro USB for power (not USB-C) |
| Laptop | For flashing the SD card and SSH'ing in |
| Your home WiFi credentials | The Pi needs to be on the same network as the ESP32 |

No breadboard, no jumpers, no soldering. The Pi sits on a desk, plugged into the wall.

### Step 1: Flash Raspberry Pi OS to the SD card

1. Download **Raspberry Pi Imager** from `raspberrypi.com/software` (free, available for macOS).
2. Insert the microSD into your laptop (use a USB adapter if needed).
3. Open Imager:
   - **Choose Device** → "Raspberry Pi Zero 2 W"
   - **Choose OS** → `Raspberry Pi OS Lite (64-bit)` — picks the headless variant under "Raspberry Pi OS (other)". *Lite* = no desktop, smaller, faster, perfect for a server.
   - **Choose Storage** → your microSD card.
4. Click **Next** → when asked "Would you like to apply OS customisation settings?" click **Edit Settings**. This is the most important step — it bakes WiFi + SSH into the SD card so you never need to plug in a keyboard or monitor.

**OS customization (do this — saves an hour of debugging later):**

- **Set hostname:** `beachcam-pi` (or whatever you like — this becomes `beachcam-pi.local` on your network).
- **Set username and password:** username `pi`, password something you'll remember. Write it down.
- **Configure wireless LAN:** SSID = your home WiFi name, password = your WiFi password, country = your country code (`IL` for Israel based on `config.yaml`).
- **Services tab → Enable SSH** → "Use password authentication".

Click **Save**, **Yes** to apply, **Yes** to overwrite the SD card. Wait ~5 minutes for flashing + verification.

### Step 2: First boot

1. Eject the microSD from your laptop, insert into the Pi.
2. Plug the Pi into Micro USB power. **The Pi Zero has TWO Micro USB ports** — use the one labeled `PWR IN` (or just the inner one closer to the SD slot). Plugging into the wrong one boots into "USB-OTG" mode and confuses everything.
3. **Wait 60–90 seconds.** First boot is slow — it expands the filesystem, configures WiFi, generates SSH keys. The green LED will flicker; that's normal. Don't unplug.

### Step 3: SSH in from your laptop

Open a terminal on your laptop:

```bash
ssh pi@beachcam-pi.local
```

(Replace `beachcam-pi` with whatever hostname you chose.) First time will ask "are you sure you want to connect" → type `yes`. Then the password prompt. You're in when you see:

```
pi@beachcam-pi:~ $
```

**If `beachcam-pi.local` doesn't resolve** (common on some networks):

- Find the Pi's IP from your router's admin page (look for the hostname in the DHCP client list).
- Or run `arp -a | grep -i "b8:27\|dc:a6\|d8:3a\|e4:5f"` on your laptop — those are common Raspberry Pi MAC prefixes. Use the IP that comes back: `ssh pi@192.168.1.X`.

### Step 4: Run a mini surf-frame server

Real `python3 -m http.server` only serves static files. We want something that returns *different* data every time — exactly like the real `current.bmp` updates when a new camera frame is processed. Save this on the Pi as `~/mini_server.py`:

```bash
nano ~/mini_server.py
```

Paste in:

```python
#!/usr/bin/env python3
"""Mini surf-frame server.

Returns a score that changes throughout the hour, so the ESP32
sees a different value each time it wakes up.

Endpoint:
  GET /score  ->  "score=7\ntime=14:30\nlabel=Tel Aviv\n"
"""
import http.server
import socketserver
from datetime import datetime

PORT = 8080

def current_state():
    now = datetime.now()
    # Score 1..10 that changes every minute. In production this comes
    # from the real surf-scoring pipeline; here we fake it.
    score = (now.minute % 10) + 1
    return {
        "score": score,
        "time":  now.strftime("%H:%M"),
        "label": "Tel Aviv",
    }

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/score":
            self.send_response(404)
            self.end_headers()
            return
        state = current_state()
        body = "".join(f"{k}={v}\n" for k, v in state.items())
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}")

with socketserver.TCPServer(("", PORT), Handler) as srv:
    print(f"Mini server on port {PORT}. Ctrl+C to stop.")
    srv.serve_forever()
```

Save with `Ctrl+O`, `Enter`, then `Ctrl+X`. Now run it:

```bash
python3 ~/mini_server.py
```

You should see `Mini server on port 8080. Ctrl+C to stop.` Leave this terminal open.

### Step 5: Verify the server returns changing data

Open a **second terminal** on your laptop. Run `curl` a few times, with a minute between calls:

```bash
curl http://beachcam-pi.local:8080/score
# score=3
# time=14:23
# label=Tel Aviv

# wait a minute, then again:
curl http://beachcam-pi.local:8080/score
# score=4
# time=14:24
# label=Tel Aviv
```

The score increments every minute. This is the round-trip you're about to make the ESP32 do automatically.

### Step 6: Smoke test — ESP32 fetches once

Before wiring up the full system, prove WiFi + HTTP work in isolation. Upload this minimal sketch (replace `YOUR_WIFI`/`YOUR_PASS`/`beachcam-pi.local` with your values):

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASS";
const char* URL       = "http://beachcam-pi.local:8080/score";

void setup() {
  Serial.begin(115200);
  delay(500);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf("\nConnected! IP: %s\n", WiFi.localIP().toString().c_str());

  HTTPClient http;
  http.begin(URL);
  int code = http.GET();
  Serial.printf("HTTP %d\n", code);
  if (code == 200) Serial.println(http.getString());
  http.end();
}

void loop() { }
```

Open `Tools → Serial Monitor` at **115200 baud**. You should see:

```
Connected! IP: 192.168.1.42
HTTP 200
score=7
time=14:30
label=Tel Aviv
```

Good — the round-trip works. Now build the real thing.

### Step 7: Full mini-production sketch

This is the capstone. The ESP32 will:

1. Wake from deep sleep.
2. Connect to WiFi.
3. GET `/score` from the Pi.
4. Parse out `score`, `time`, `label`.
5. **Render to the e-ink display** (Exercise 6).
6. **Play the wave sound** (Exercise 5).
7. **Deep-sleep for 5 minutes**, then repeat forever.

That's the production firmware in miniature. Make sure the e-ink HAT and speaker are still wired per Exercises 5 and 6.

> **Before uploading:** disconnect the HAT's `VCC` jumper from 3V3. Peripherals on the rail can starve the chip during flashing and cause "chip stopped responding" errors. Reconnect VCC after upload completes, then press `EN` to start the cycle.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <GxEPD2_BW.h>
#include <Fonts/FreeMonoBold12pt7b.h>

// ----- Config -----
const char* WIFI_SSID    = "YOUR_WIFI";
const char* WIFI_PASS    = "YOUR_PASS";
const char* SCORE_URL    = "http://beachcam-pi.local:8080/score";
const uint64_t SLEEP_MIN = 5;     // wake every 5 minutes

// ----- Pins (match Exercises 5 + 6) -----
#define EPD_CS    5
#define EPD_DC    17
#define EPD_RST   16
#define EPD_BUSY  4
#define SPEAKER_PIN 25

GxEPD2_BW<GxEPD2_154_D67, GxEPD2_154_D67::HEIGHT> display(
    GxEPD2_154_D67(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY)
);

// ----- Tiny parser for "key=value\n" responses -----
String fieldOf(const String& body, const String& key) {
  int idx = body.indexOf(key + "=");
  if (idx < 0) return "";
  int end = body.indexOf('\n', idx);
  return body.substring(idx + key.length() + 1, end == -1 ? body.length() : end);
}

// ----- Wave sound (from Exercise 5) -----
void playWave() {
  const unsigned long duration_us = 6000000;
  const float crash_start = 0.30f, crash_end = 0.36f, loudness = 2.5f;
  unsigned long start = micros();
  int prev = 128, prev2 = 128;
  float surge = 1.0f;
  unsigned long surge_next = 0;
  while (micros() - start < duration_us) {
    unsigned long elapsed = micros() - start;
    float t = (float)elapsed / duration_us;
    float env;
    if (t < crash_start)      env = pow(t / crash_start, 4.0f) * 0.5f;
    else if (t < crash_end)   env = 1.6f;
    else {
      float d = (t - crash_end) / (1.0f - crash_end);
      env = exp(-2.5f * d);
    }
    if (elapsed > surge_next) {
      surge = 0.7f + 0.6f * (random(0, 100) / 100.0f);
      surge_next = elapsed + 50000;
    }
    int sample = 128 + (int)(random(-127, 128) * env * surge * loudness);
    sample = (sample + prev)  / 2;  prev  = sample;
    sample = (sample + prev2) / 2;  prev2 = sample;
    sample = constrain(sample, 0, 255);
    dacWrite(SPEAKER_PIN, sample);
    delayMicroseconds(60);
  }
  dacWrite(SPEAKER_PIN, 128);
}

// ----- E-ink render (from Exercise 6) -----
void renderScreen(int score, const String& timeStr, const String& label) {
  display.init(115200);
  display.setRotation(1);
  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.setFont(&FreeMonoBold12pt7b);
    display.setTextColor(GxEPD_BLACK);

    display.setCursor(10, 30);  display.print(label);
    display.setCursor(10, 55);  display.print(timeStr);

    display.setCursor(10, 95);
    display.print("SURF: "); display.print(score); display.print("/10");

    display.drawRect(10, 110, 180, 30, GxEPD_BLACK);
    int filled = (180 - 4) * score / 10;
    display.fillRect(12, 112, filled, 26, GxEPD_BLACK);
  } while (display.nextPage());
  display.hibernate();
}

void deepSleepMinutes(uint64_t minutes) {
  esp_sleep_enable_timer_wakeup(minutes * 60ULL * 1000000ULL);
  Serial.printf("Sleeping for %llu min...\n", minutes);
  Serial.flush();
  esp_deep_sleep_start();  // never returns; setup() runs again on wake
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== Wake up ===");

  // 1. WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(200);
  if (WiFi.status() != WL_CONNECTED) { Serial.println("WiFi failed"); deepSleepMinutes(SLEEP_MIN); }

  // 2. Fetch
  HTTPClient http;
  http.begin(SCORE_URL);
  int code = http.GET();
  if (code != 200) { Serial.printf("HTTP %d\n", code); http.end(); deepSleepMinutes(SLEEP_MIN); }
  String body = http.getString();
  http.end();

  // 3. Parse
  int    score    = fieldOf(body, "score").toInt();
  String timeStr  = fieldOf(body, "time");
  String label    = fieldOf(body, "label");
  Serial.printf("Got: score=%d time=%s label=%s\n", score, timeStr.c_str(), label.c_str());

  // 4. Render to e-ink
  renderScreen(score, timeStr, label);

  // 5. Play wave sound (announces the new image, like the real frame does for guest beaches)
  playWave();

  // 6. Sleep
  deepSleepMinutes(SLEEP_MIN);
}

void loop() { }  // never reached — setup() is the whole program
```

### Watch it run end-to-end

1. Upload (with HAT VCC unplugged), reconnect VCC, press `EN`.
2. Open Serial Monitor at 115200.
3. You'll see the wake → fetch → render → wave → sleep cycle. The screen updates with a new score; you hear a wave; the chip goes quiet.
4. Wait 5 minutes. The cycle repeats automatically — score changes (since the Pi computes it from the current minute), screen redraws, wave plays again.

That's the production system. The real frame is the same loop with three substitutions:

| Mini exercise | Production |
|---------------|------------|
| Pi serves `/score` (text, generated from the clock) | Pi serves `/current.bmp` (a real beach photo with overlays) |
| ESP32 renders `score` to the 1.54" panel | ESP32 streams the BMP straight to the 13.3" 6-color panel |
| Sleep 5 minutes | Sleep 30 minutes (`timing.esp_sleep_minutes` in `config.yaml`) |

Same WiFi, same `HTTPClient`, same `GxEPD2`, same `dacWrite` wave, same `esp_deep_sleep_start()`. If you got this exercise running, the production firmware is just bigger pictures and longer sleeps.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Pi green LED never flickers | Wrong Micro USB port (use `PWR IN`), or charger too weak — Pi Zero needs ≥1A |
| `ssh: Could not resolve hostname` | mDNS not working on your network — find the IP via router or `arp -a` |
| `Permission denied (password)` | Caps Lock, or you reused the SD card with old credentials — re-flash and set the password fresh |
| Pi connects but no internet | Wrong WiFi country code — re-flash with the right one (radio is locked off until set) |
| `python3: command not found` | Pi OS Lite includes `python3` by default — if missing, run `sudo apt update && sudo apt install -y python3` |
| `curl` works from laptop but ESP32 gets `-1` | ESP32 isn't on the same WiFi as the Pi (5 GHz vs 2.4 GHz — Pi Zero 2 W only supports 2.4 GHz) |
| `Connection refused` from `curl` | The Python server isn't running, or it's listening on `127.0.0.1` only — `python3 -m http.server` listens on `0.0.0.0` by default, so check the SSH terminal |
| ESP32 connects to WiFi but `HTTP status: -1` | Firewall on Pi (rare on Pi OS Lite) or wrong port — confirm with `curl` from laptop first |

### Useful Pi commands

Once SSH'd in:

| Command | What it does |
|---------|--------------|
| `hostname -I` | Print all IP addresses (faster than checking the router) |
| `iwgetid` | Show which WiFi network you're on |
| `df -h /` | Disk usage — make sure the SD isn't full |
| `top` then `q` | See running processes; useful when the server is acting up |
| `sudo shutdown -h now` | Cleanly power off before unplugging (don't yank power on a running Pi — corrupts the SD) |
| `sudo reboot` | Reboot |
| `Ctrl+C` | Stop the running Python server |
| `exit` (or `Ctrl+D`) | End the SSH session (server keeps running only if you backgrounded it) |

### Keeping the server running after you log out

The mini server dies when you close SSH. To survive logout:

```bash
nohup python3 ~/mini_server.py > ~/mini_server.log 2>&1 &
```

Check it's still alive after disconnecting and reconnecting:

```bash
ps aux | grep mini_server          # should list one Python process
tail -f ~/mini_server.log          # watch incoming requests live
```

Stop it with:

```bash
pkill -f mini_server.py
```

The proper production way is a **systemd service** that auto-starts on boot — used by the real code in `/home/pi/beachcam_pic/`. For this exercise, `nohup` is enough to leave the system running overnight and watch the ESP32 wake up every 5 minutes from the Serial Monitor.

### Why this exercise matters for the main project

The production firmware on the ESP32 does *exactly* this every 30 minutes:

1. Wake from deep sleep (`timing.esp_sleep_minutes` in `config.yaml`).
2. Connect to WiFi (the credentials in `credentials.h`).
3. `HTTPClient http; http.begin("http://pi.local:8080/current.bmp"); http.GET();` — same calls as the test sketch above.
4. Stream the BMP bytes into the e-ink driver (the `GxEPD2` library from Exercise 6).
5. `display.hibernate()` and go back to deep sleep.

If you got this exercise to print "Hello from the Pi" on the ESP32's serial monitor, you've already proven the four hardest pieces — flashing, networking, mDNS, HTTP — work on your gear. The real firmware just swaps the URL and writes the response to a screen instead of a serial log.

---

## What You Learned

After these exercises you understand:

| Concept | What it means |
|---------|---------------|
| Circuit | Complete loop from (+) to (-) |
| LED polarity | Long leg = (+), short leg = (-) |
| Resistor | Limits current, protects LED |
| Breadboard rows | Holes in same row are connected |
| Button | Connects/disconnects circuit |
| GPIO | ESP32 pins you control with code |
| DAC | Analog output (GPIO25/26) for audio |
| Speaker + resistor | Same current-limiting concept as LED |
| Multimeter — continuity | Beeps when two points are electrically connected (power off) |
| Multimeter — DC voltage | Measures voltage across components; series voltages add to supply |
| Multimeter — resistance | Verifies a resistor's value before installing it |
| Floating pin | Undriven GPIO reads random voltages — needs pull-up/pull-down |
| SPI | 4-wire serial protocol (DIN/CLK/CS + optional DC) — just timed digital outputs |
| BUSY pin | Output *from* a peripheral telling the MCU "I'm processing — wait" |
| E-ink rendering | Paged loop (`firstPage`/`nextPage`) because the framebuffer doesn't fit in RAM |
| `hibernate()` | Put the panel into deep sleep after drawing — image stays without power |
| Headless Pi setup | OS customization in Imager bakes WiFi + SSH into the SD before first boot |
| SSH | Encrypted remote shell — `ssh user@host.local` is your terminal-into-the-Pi |
| mDNS / `.local` | Hostnames that resolve on the local network without DNS — `beachcam-pi.local` |
| `python3 -m http.server` | Built-in one-line file server, perfect for ESP32 ↔ Pi round-trip tests |
| `HTTPClient` (ESP32) | Same `GET`/response pattern as `curl` — just from C++ on the microcontroller |

---

## Next Steps

Once comfortable with these basics:

1. **Build the E-Ink project** - same concepts, just more wires
2. **The E-Ink HAT** has built-in resistors/protection, so no resistors needed
3. **SPI wires** (DIN, CLK, CS, etc.) are just GPIO → HAT connections

You now understand what's happening when you wire the E-Ink display!

---

## See Also

- `hardware_diagram.md` - Main project wiring
- `architecture.md` - Software overview
