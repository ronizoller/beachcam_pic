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
| LiPo or 3V battery | Already have the LiPo | 1 |

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

This builds confidence with components that can break if mishandled (LEDs are sensitive to heat and reverse polarity).

### Circuit
```
LiPo (+) → wire → 220Ω resistor → LED long leg (+) → LED short leg (−) → wire → LiPo (−)
```

The resistor limits current to safe levels (~12mA at 3.7V). **Never connect an LED directly to the battery without a resistor — it'll fry instantly.**

### LED polarity (critical)
- **Long leg** = anode (positive) — connects toward battery +
- **Short leg** = cathode (negative) — connects toward battery −
- Also: the flat edge on the round plastic dome marks the negative side

Reverse polarity won't light the LED (LEDs only conduct one way). It also won't damage them at battery voltages.

### Soldering steps
1. Strip and tin both ends of two short wires (~5cm each)
2. Solder one wire to one leg of the resistor — clip the LED leg / resistor leg short first if needed
3. Solder the other resistor leg to the LED's long leg
4. Solder the other wire to the LED's short leg
5. Touch the loose wire ends to the LiPo terminals (long-leg side to +, short-leg side to −)

LED should light up. If not:
- Polarity reversed → swap the wires at the battery
- Bad solder joint → wiggle each joint with a finger while connected, looking for flicker. A loose joint flickers; a good joint stays steady.

### What if you damage the LED?
LED sensitive to heat. If you dwell on a leg with the iron for >5 seconds, the LED can die. Symptoms:
- Doesn't light even with correct polarity
- Lights very dim
- One color when LED is white/RGB

Just grab another LED and try again. They're cheap.

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
