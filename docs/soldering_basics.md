# Soldering Basics — From Zero to Surf-Frame-Ready

A focused guide to learning soldering with the components in this project. By the end you'll be able to solder wires to the TP4056 and MT3608 pads confidently. No prior experience assumed.

---

## What you need to buy

Three items (~$25 total on Amazon):

| Item | Notes | Why |
|------|-------|-----|
| **Soldering iron** | 40-60W, adjustable temperature, with a fine tip (~1mm) | Lower wattage = slower heat-up, harder to use on bigger pads. 60W with a fine tip handles everything in this project. |
| **Lead-free solder** | 0.6-0.8 mm diameter, rosin-core, lead-free (SAC305) | Thinner is easier for fine work. Rosin-core has flux inside — you don't need separate flux. Lead-free is safer for hobby use. |
| **Solder wick** (a.k.a. desoldering braid) | Copper braid on a small spool | For undoing mistakes. ~$3, lasts forever. |

Nice-to-have (not required):
- **Helping hands** (alligator clip stand) — holds wires while you solder. Otherwise tape works.
- **Damp sponge or brass tip cleaner** — for cleaning the iron tip during use.
- **Safety glasses** — solder splatter is rare but happens.

---

## Practice components you already have

| Item | Where from | Count needed |
|------|------------|--------------|
| Scrap dupont wires | Cut one end off existing wires; you have lots | 4-6 short pieces |
| Small LEDs | If you have a beginner electronics kit, you probably have some. Otherwise grab a $3 pack of "5mm LED assorted colors" from Amazon. | 4-6 (you'll mess some up — that's the point) |
| 220Ω resistor | Already in your project parts (used with the speaker) | 1-2 |
| Multimeter | Already have, used for MT3608 calibration | 1 |

**Why not the LiPo for practice?** The project's LiPo only has a JST connector — no bare terminals you can clip wires to. Trying to power practice circuits from the JST is fiddly and risks shorting the battery. Instead, we use the **multimeter** to verify your solder joints work (continuity beep + diode test mode), and save the LiPo for the actual project assembly.

If you happen to have a **coin cell (CR2032 = 3V)** or **two AA batteries in a holder (3V)**, those work as optional LED-lighting power. Not required.

---

## How a solder joint works

Think of solder as molten metal glue. Three things must happen at the joint:

1. **Both parts being joined are heated** — wire + pad heated together by the iron
2. **The solder flows TO the heat** — you touch solder to the heated joint (NOT to the iron tip), and the molten solder is drawn onto both surfaces by capillary action
3. **The joint cools** — solder solidifies, mechanical + electrical connection complete

A bad solder joint usually means you only heated one side (so solder bonded to the wire but not the pad, or vice versa), or you applied solder before things were hot enough.

---

## Practice 1: Tin the iron tip

Your iron should always have a tiny shiny layer of solder on it before you touch a joint.

1. Plug in the iron, set to ~350°C (~660°F) for lead-free solder
2. Wait until heated (~30 sec to 2 min depending on iron)
3. Touch the solder to the tip — a small bead should melt onto it instantly
4. Wipe excess on a damp sponge or brass cleaner — the tip should be shiny silver, not dull grey

If the solder doesn't melt instantly, the iron isn't hot enough yet. Wait longer.

If the tip is dull grey and solder won't stick — the tip is "oxidized" (this happens fast at high temp). Clean it with brass wool or a tip-cleaning paste, then re-tin.

---

## Practice 2: Solder two wires together

Goal: join two scrap dupont wires end-to-end into one longer wire.

1. **Strip** ~5mm of insulation off the end of each wire (your fingernail can usually pull it off after a small cut)
2. **Twist** the two stripped ends together, hand-tight
3. **Tin** the iron tip (touch solder, then wipe excess)
4. **Heat the joint** — press the iron's tip against the twisted wire for 2-3 seconds. The wire absorbs heat.
5. **Apply solder to the WIRE** (not the iron) — touch the solder wire to the joint, opposite side from the iron. It should melt and flow onto the wires by itself.
6. **Pull solder away first**, then the iron. Wait ~5 sec for the joint to cool.

A good joint looks **shiny and smooth**, with solder wrapping around the wire strands. A bad joint looks **dull, grainy, or blobby** — usually because you moved during cooling, or it wasn't hot enough.

Try it 3-4 times. The first one will be ugly. By the fourth, you'll have the feel.

---

## Practice 3: Solder an LED + resistor circuit

This builds confidence with components that can break if mishandled (LEDs are sensitive to heat and reverse polarity). You'll verify each joint with the multimeter — no battery needed.

### Circuit you'll build
```
wire ── 220Ω resistor ── LED long leg (+)  ──  LED short leg (−) ── wire
  ^                                                                    ^
  free wire end (will be probe point 1)        free wire end (probe point 2)
```

### LED polarity (critical for the test step)
- **Long leg** = anode (positive)
- **Short leg** = cathode (negative)
- Also: the flat edge on the round plastic dome marks the negative side

LEDs only conduct one way. Reverse polarity won't damage them at low voltages, just won't light.

### Soldering steps
1. Strip and tin both ends of two short wires (~5 cm each)
2. Solder one wire to one leg of the resistor — clip the resistor leg short first if needed (5 mm of leg left is plenty)
3. Solder the other resistor leg to the LED's **long leg**
4. Solder the other wire to the LED's **short leg**

You now have a finished tiny circuit with two free wire ends.

### Test each joint with the multimeter — continuity mode

Most multimeters have a "continuity" mode — usually a speaker/beeper icon on the dial, or it auto-detects very low resistance. When the probes touch two ends of a wire (or any conducting path), the meter **beeps** to confirm electricity can flow.

If your auto-detect meter doesn't beep, look for a beeper icon and rotate to it.

Test sequence:
1. Touch one probe to the bare wire end on the resistor side
2. Touch the other probe to the LED's long leg (the leg between the wire and the LED body, accessible just below the soldered joint)
3. Should **beep** → resistor side wire-to-LED joint is good
4. Now move the second probe to the LED's short leg solder joint area
5. Should **NOT beep** → the LED is in between, and in continuity mode the small voltage isn't enough to forward-bias it. Good — it means there's no accidental short across the LED.
6. Now move the first probe to the other wire's bare end (cathode side)
7. Probe between the two wire ends — no beep (LED blocks DC at this low voltage)
8. **Swap the probes** so red goes to the cathode-side wire — still no beep. Confirms no short across the LED.

### Test the LED itself — diode test mode

Most multimeters have a separate "diode" mode (often labeled with a diode triangle symbol, sometimes on the same dial position as continuity). Diode mode applies a slightly higher voltage (~2-3V) that's enough to forward-bias an LED.

1. Switch the meter to **diode mode** (or press the SELECT/MODE button if your meter combines diode+continuity)
2. 🔴 Red probe → the wire connected to the LED's long leg (anode side)
3. ⚫ Black probe → the other wire (cathode side)
4. **LED should light up faintly** while the probes touch
5. Display shows the LED's forward voltage (typically `1.8` for red, `2.0` for yellow, `3.0` for blue/white)
6. Swap the probes — LED stays dark, display shows `OL` or `1.` — that confirms it only conducts one way

If the LED lights, every solder joint in the chain is working — congratulations.

### If the LED doesn't light in diode mode
- **Probes swapped** → red to anode side, black to cathode side. Try again.
- **Cold solder joint somewhere** → wiggle each joint gently while probes are touching. If the LED flickers or comes alive, that joint is loose — reheat and re-solder it.
- **Burned LED** → if you held the iron on its leg for >5 seconds, the LED may be dead. Grab another and try again.

### What if you damage the LED?
LEDs are sensitive to heat. If you dwell on a leg with the iron for >5 seconds, the LED can die. Symptoms:
- Doesn't light even with correct polarity in diode mode
- Lights very dim
- Display shows weird forward voltage (e.g., `0.5` or `OL`)

Just grab another LED and try again. They're cheap. This is exactly why we practice on $0.03 components before $5 ICs.

---

## Practice 4: Desoldering (undoing mistakes)

You **will** make mistakes. Solder a joint, then practice un-soldering it.

### Method A: Solder wick (the easy way)
1. Lay the wick across the joint
2. Press the iron tip on top of the wick, against the joint
3. Wait 2-3 seconds — solder melts and gets absorbed into the wick (capillary action again)
4. Lift the iron + wick together
5. Cut off the saturated part of the wick — you can't re-use it

### Method B: Reheat + pull
1. Heat the joint until solder is liquid (you'll see it shimmer)
2. Pull the wire/leg out while still molten
3. Wipe excess solder on a damp sponge

Practice on your Practice 2 wires until you can solder + desolder + re-solder without damaging the wires.

---

## Now the actual project: TP4056 and MT3608

You've practiced. Now the real targets.

### Tinning the pads (recommended first step)

For each pad on the TP4056 you'll connect to (B+ and B-):
1. Hold the iron tip against the pad's metal rim for 2 sec
2. Touch solder to the heated pad — a small dome of solder should adhere to the pad
3. Remove solder + iron

This "pre-tins" the pad. Same for the MT3608 pads (IN+, IN-, OUT+, OUT-).

### Attaching a wire

1. Strip ~5mm of insulation, twist the strands tight, and **tin the wire end** (heat + add solder so the strands are fused into a stiff little soldered tip)
2. Hold the tinned wire end against the pre-tinned pad
3. Touch the iron to the wire + pad — the existing solder on both should re-melt and merge into one joint
4. Remove iron, hold the wire still until it cools (~5 sec)

For through-holes (the pads we discussed): push the tinned wire through the hole from the **bottom** of the board, so the wire sticks up through the hole. Then solder from the top. This makes a stronger joint and is the standard way for through-hole work.

### How much solder?
- Not too little — the joint should fully cover the wire + fill the hole (for through-holes)
- Not too much — a giant blob is weaker than a properly-shaped joint and may bridge to adjacent pads
- Target shape: a smooth volcano, with the wire visible going into the apex

---

## Reference: things that will not damage the boards

- Heating the same pad for up to 10 seconds is fine
- Touching the iron to plastic insulation briefly (it'll smell but not start a fire)
- Reverse polarity when testing — both LEDs and TP4056 have protection
- Soldering then desoldering the same pad 5-10 times

## Things that WILL damage the boards

- Holding the iron on the same SMD chip leg for >5 sec
- Pulling a wire out before solder has cooled — strips the copper pad off the PCB ("lifted pad" — very hard to fix)
- Mechanical stress on a joint immediately after soldering — wait 5 sec for it to fully solidify
- Touching the LiPo with a hot iron — LiPo + heat = thermal runaway risk. **Always have the iron unplugged when handling the battery.**

---

## Common beginner mistakes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Solder ball just sits on the pad, doesn't bond | Pad wasn't hot enough — you applied solder to the iron, not the joint | Wipe the bad solder off with wick, retry — heat the joint first, then apply solder to the joint |
| Joint looks dull/grainy/rough | Moved during cooling, or not enough heat | Reheat the joint, let it cool undisturbed |
| Solder bridge between two adjacent pads | Too much solder + pads too close | Drag the iron across the bridge with the tip wiped clean, or use wick to remove the extra |
| Wire pulls out easily | Cold joint — solder bonded to wire but not pad (or vice versa) | Reheat both sides simultaneously, apply a tiny bit more solder |
| Iron tip won't pick up solder anymore | Tip oxidized | Clean with brass wool, re-tin with fresh solder. Always tin before storing. |
| Brown smoke / smell | Burning the PCB or insulation | Move iron away immediately. Brief contact is fine; sustained contact damages. |

---

## Soldering safety in 30 seconds

- Iron is **460°C / 850°F**. It will burn skin instantly. Treat it like a hot stove.
- Solder fumes contain flux fumes — ventilate (open window, fan)
- Wash hands after soldering (lead-free still has flux residue)
- Don't lean over the joint — eyes 30cm+ away. Safety glasses if you have them.
- **Unplug the iron before handling the LiPo.** Hot iron + LiPo = potential thermal runaway.

---

## When you're ready for the real thing

Once you can:
- ✅ Solder two wires together cleanly (Practice 2)
- ✅ Light an LED with a soldered resistor circuit (Practice 3)
- ✅ Undo a joint with wick (Practice 4)

…you're ready to solder the TP4056 + MT3608 connections for the surf frame. Refer to `hardware_diagram.md` for which pads connect to what.

Total practice time: usually 30-60 minutes. By the end, the project soldering is the easy part.
