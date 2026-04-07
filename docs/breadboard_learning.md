# Breadboard Learning Exercises

Simple exercises to learn breadboard basics before building the main project.

---

## Parts for Learning

| Part | Quantity | Status |
|------|----------|--------|
| ESP32 DevKitC | 1 | From main project |
| Breadboard | 1 | From main project |
| LEDs 5mm (mixed colors) | 10 | Ordered |
| Resistors 220Ω (1W) | 50 | Ordered |
| Push buttons 6x6mm | 20 | Ordered |
| Male-to-male wires | - | Use male-to-female for now |

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

---

## Exercise 1: Light an LED

**Goal:** Make an LED turn on.

### Circuit

```
ESP32 3V3 ──→ Resistor 220Ω ──→ LED (+) ──→ LED (-) ──→ ESP32 GND
```

### Steps

1. **Power ESP32 via USB-C** (no battery needed)

2. **Place LED on breadboard:**
   - Long leg (+) in row 10
   - Short leg (-) in row 11

3. **Place resistor on breadboard:**
   - One leg in row 10 (same row as LED +)
   - Other leg in row 5

4. **Connect wires:**
   - ESP32 3V3 → row 5 (resistor's other end)
   - ESP32 GND → row 11 (LED's - leg)

5. **LED should light up!**

### Breadboard Layout

```
        Breadboard
    A B C D E   F G H I J
    ─────────────────────
 5  o o[R]o o   o o o o o   ← resistor leg + wire to 3V3
 6  o o o o o   o o o o o
 7  o o o o o   o o o o o
 8  o o o o o   o o o o o
 9  o o o o o   o o o o o
10  o o[R]o o   o[L+]o o o   ← resistor leg + LED long leg (same row)
11  o o o o o   o[L-]o o o   ← LED short leg + wire to GND
```

R = resistor, L+ = LED long leg, L- = LED short leg

### Troubleshooting

| Problem | Solution |
|---------|----------|
| LED doesn't light | Check LED direction (flip it) |
| Still nothing | Check resistor is in same row as LED + |
| Still nothing | Check wires to 3V3 and GND |
| LED very dim | Check resistor value (should be 220Ω) |

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

---

## Exercise 4: Traffic Light

**Goal:** Red, yellow, green LEDs controlled by ESP32 code.

### Circuit

```
ESP32 GPIO23 ──→ [220Ω] ──→ Red LED ──→ GND
ESP32 GPIO18 ──→ [220Ω] ──→ Yellow LED ──→ GND
ESP32 GPIO5  ──→ [220Ω] ──→ Green LED ──→ GND
```

### Arduino Code

```cpp
#define RED_PIN 23
#define YELLOW_PIN 18
#define GREEN_PIN 5

void setup() {
  pinMode(RED_PIN, OUTPUT);
  pinMode(YELLOW_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
}

void loop() {
  // Green on
  digitalWrite(GREEN_PIN, HIGH);
  delay(3000);
  digitalWrite(GREEN_PIN, LOW);

  // Yellow on
  digitalWrite(YELLOW_PIN, HIGH);
  delay(1000);
  digitalWrite(YELLOW_PIN, LOW);

  // Red on
  digitalWrite(RED_PIN, HIGH);
  delay(3000);
  digitalWrite(RED_PIN, LOW);
}
```

This cycles: Green (3s) → Yellow (1s) → Red (3s) → repeat.

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
