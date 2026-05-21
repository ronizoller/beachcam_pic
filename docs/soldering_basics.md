# Soldering Basics — From Zero to Surf-Frame-Ready

A focused guide to learning soldering with the components in this project. By the end you'll be able to solder wires to the TP4056 and MT3608 pads confidently. No prior experience assumed.

---

## What you need to buy

Three items (~$25 total on Amazon):


| Item                 | Notes                                                  | Why                                                                                                                           |
| -------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| **Soldering iron**   | 40-60W, adjustable temperature, with a fine tip (~1mm) | Lower wattage = slower heat-up, harder to use on bigger pads. 60W with a fine tip handles everything in this project.         |
| **Lead-free solder** | 0.6-0.8 mm diameter, rosin-core, lead-free (SAC305)    | Thinner is easier for fine work. Rosin-core has flux inside — you don't need separate flux. Lead-free is safer for hobby use. |


Nice-to-have (not required):

- **Solder wick** (a.k.a. desoldering braid) — copper braid that lifts solder off pads, $3. Makes desoldering mistakes much easier. We'll cover wick-free desoldering techniques below for now, but if you can grab a roll alongside the iron, do it — you'll thank yourself the first time you make a solder bridge.
- **Helping hands** (alligator clip stand) — holds wires while you solder. Otherwise tape works.
- **Damp sponge or brass tip cleaner** — for cleaning the iron tip during use.
- **Safety glasses** — solder splatter is rare but happens.

---

## Practice components you already have


| Item               | Where from                                                                                                                         | Count needed                                 |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Scrap dupont wires | Cut one end off existing wires; you have lots                                                                                      | 4-6 short pieces                             |
| Small LEDs         | If you have a beginner electronics kit, you probably have some. Otherwise grab a $3 pack of "5mm LED assorted colors" from Amazon. | 4-6 (you'll mess some up — that's the point) |
| 220Ω resistor      | Already in your project parts (used with the speaker)                                                                              | 1-2                                          |
| Multimeter         | Already have, used for MT3608 calibration                                                                                          | 1                                            |


**Why not the LiPo directly for practice?** The project's LiPo only has a JST connector — no bare terminals to clip wires to, and an exposed LiPo + accidental shorts is a recipe for trouble. **But** we have a clever workaround: the TP4056 module sits between the LiPo and the rest of the circuit, and it has solder pads (B+/B-) that output the LiPo's voltage but with built-in overcurrent and short-circuit protection. We'll solder onto those pads as our practice target. Bonus: the wires you solder during practice are the **same wires** the production circuit needs — practice IS the project work.

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

1. Plug in the iron, set to ~~350°C (~~660°F) for lead-free solder
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

## Practice 3: Solder wires to the TP4056 + light an LED off it

This is where practice meets the real project. The two wires you solder here are the **same wires** that will connect TP4056 → MT3608 in the final build — no wasted work.

### Why this is safer than it sounds

- TP4056 B+/B- pads output ~3.7–4.2V (the LiPo's voltage, after protection)
- The TP4056 has built-in **overcurrent + short-circuit protection** via its DW01 chip — if you accidentally bridge B+ to B- with a stray bit of solder, the protection cuts off and nothing burns
- Pads are large through-holes — beginner-friendly to solder
- ⚠️ **Always unplug the LiPo from the TP4056 while you have the iron in hand.** Reconnect only after the iron is back in its stand and cooled, and you've inspected the joint.

### Tools and materials

- Iron, solder
- 2× wires (~10 cm each) — these will become the TP4056 → MT3608 wires
- Wire strippers (or a careful knife/fingernail)
- LED (any color)
- 220Ω resistor
- The TP4056 module (LiPo **UNPLUGGED**)

### Step-by-step

#### A. Prep the wires

1. Strip ~5 mm of insulation off both ends of each wire (4 strips total)
2. Twist each stripped end tight so the strands stay together
3. Tin all four wire ends — touch the iron to the bare strands, apply solder until the strands fuse into a single stiff metal tip. They should look silver and smooth, not blobby.

#### B. Pre-tin the TP4056 pads

LiPo **UNPLUGGED**. With the TP4056 on a flat surface:

1. Hold the iron tip against the **B+ pad's metal rim** for ~2 seconds to heat it
2. Touch solder to the heated pad (not the iron) — a small dome of solder should adhere to the pad and fill the through-hole partially
3. Remove solder, then remove iron
4. Repeat for the **B- pad**

The pads now have a small mound of solder sitting on them. This makes attaching the wires much easier.

#### C. Attach the wires

1. Push the tinned end of wire #1 through the **B+ through-hole** from the bottom of the board so a few mm sticks up through the top
2. Hold the iron against the wire+pad on the top — the existing solder on both should re-melt and merge
3. Touch a tiny bit of extra solder if needed for a clean joint
4. Remove iron, hold wire still until it cools (~5 sec)
5. Repeat for wire #2 on **B- pad**

#### D. Inspect

The joints should look like smooth, shiny volcanos with the wire visible going into the apex.

- **Dull / grainy** = moved during cooling — reheat, let cool undisturbed
- **No solder bridging B+ and B-** = check carefully, including the bottom of the board. If you find a bridge, use the drag technique from Practice 4 (Technique C) to clear it.
- **Wire wiggles loose** = cold joint — reheat both sides simultaneously, add a touch of solder

### E. Light an LED off the soldered pads

Now the LiPo is reconnected. The free ends of your two soldered wires output ~4V.

Build a quick test circuit (no soldering — just twist the wires together for now):

```
TP4056 B+ wire ── 220Ω resistor ── LED long leg (+)  ──  LED short leg (−) ── TP4056 B- wire
```

LED polarity:

- **Long leg** = anode → toward the **B+** wire (positive)
- **Short leg** = cathode → toward the **B- ** wire (negative)
- The flat edge on the LED's plastic dome also marks the negative side

The resistor limits current to ~10 mA — safe for any LED.

Plug the LiPo into the TP4056's JST socket. **The LED should light up.**

### F. Troubleshoot


| Symptom                           | Cause                                                                               | Fix                                                                                                                                                                                                |
| --------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LED doesn't light                 | LED polarity reversed                                                               | Swap the LED end-for-end in the chain                                                                                                                                                              |
| LED doesn't light                 | TP4056's B+ wire is on its B- pad, vice versa (LiPo's JST polarity may be reversed) | Probe between the wire ends with the multimeter — you should see ~3.7–4.2V *positive* with red on the B+ wire. Negative means JST polarity reversed; see hardware_diagram.md for the LiPo JST fix. |
| LED doesn't light                 | Cold solder joint at TP4056                                                         | Wiggle each soldered wire gently; if the LED flickers when wiggled, reheat that joint and add a touch more solder                                                                                  |
| LED very dim                      | Voltage low — LiPo nearly dead                                                      | Charge the LiPo via USB on the TP4056                                                                                                                                                              |
| TP4056 LED off, no power anywhere | Solder bridge between B+ and B- triggered protection cutoff                         | Unplug LiPo. Inspect both pads carefully (including the bottom). Use Practice 4 Technique C (drag with clean iron tip) to remove the bridge. Re-test.                                              |


### G. Once the LED works

- Unplug the LiPo
- Disconnect the LED + resistor (they were just a test load)
- Your soldered B+ and B- wires now go to **MT3608 IN+** and **IN-** respectively — see `hardware_diagram.md`. Refer to Practice 5 below for soldering the MT3608 side.

That's it — you've done your first real project soldering, and verified it works.

---

## Practice 4: Desoldering without wick

You **will** make mistakes. Without solder wick, you have three techniques — all use just the iron and gravity. They cover ~95% of the cases you'll hit on this project.

### Technique A: Reheat + pull (for through-hole joints)

Use this when a wire is in a hole and you want to remove it cleanly.

1. Hold the wire near the joint with your other hand (or pliers/tweezers — wire gets hot fast)
2. Touch the iron to the joint until the solder turns shiny + liquid (~2-3 sec)
3. While solder is molten, pull the wire **straight out** of the hole — don't twist
4. Most of the solder comes out with the wire; a small ring stays on the pad — fine for re-soldering later
5. Wipe excess solder off the iron tip on a damp sponge or scrap of cardboard

### Technique B: Reheat + tap (for solder still in the hole)

If the hole stays partially blocked with solder after pulling the wire:

1. Hold the board with one hand, iron in the other
2. Heat the pad until the solder in the hole melts
3. With the molten solder still liquid, give the board a quick **firm tap** against a hard surface (table edge, with a paper towel underneath to catch flying solder)
4. The molten solder droplets out of the hole
5. Repeat if needed

You may have to do this 2-3 times for a fully clean hole. Wear safety glasses if you have them — tiny solder bits do go flying.

### Technique C: Drag for solder bridges (most common project mistake)

If two adjacent pads got bridged by extra solder:

1. Wipe the iron tip clean on the damp sponge (or scrap cardboard if no sponge — drag it sideways, leaving the solder behind on the sponge)
2. With a **clean** tip, touch the iron to the bridge and slowly drag sideways across both pads
3. The bridge solder transfers from the pads to the tip
4. Wipe the tip clean again, repeat if any bridge remains

This works because clean copper attracts molten solder more than the pads do (when both are hot). Each drag pulls a little more solder onto the tip.

### Technique D: Add fresh solder + drag (paradoxical fix for stubborn bridges)

Sometimes a bridge has gone slightly oxidized and won't lift with technique C. Counter-intuitively:

1. Add a small dab of **fresh** solder onto the bridge — the rosin flux in fresh solder re-wets everything
2. Now drag the clean iron tip across — the combined molten pool lifts off easily

Add → wipe iron → drag → wipe iron. Usually one cycle clears it.

### Practice exercise

On your Practice 2 wires:

1. Solder two scrap dupont wires together (good joint)
2. **Un-solder them** using Technique A (heat + pull)
3. Re-strip if needed and **re-solder** them
4. Do this 3-4 times until you can solder + desolder confidently

Pro tip: clean the iron tip every minute or so. A blackened/oxidized tip won't transfer heat well — solder will sit on the tip in beads instead of flowing. Wipe on damp sponge or scrape on cardboard.

---

## Practice 5: MT3608 connections (finishing the project)

TP4056 side is done from Practice 3. Now the MT3608 — three pads: **IN+** and **IN-** (from TP4056), plus **OUT+** (to ESP32 5V). OUT- already grounded.

### ⚠️ VERIFY POLARITY BEFORE TOUCHING THE MT3608

Cheap TP4056 modules sometimes have reversed silkscreen labels, and cheap LiPos sometimes have non-standard JST wire colors. Either alone — or both combined — sends reverse polarity to the MT3608's input. Reverse polarity at MT3608 IN+/IN- causes an instant spark, fries the internal FET, and the module is dead. There's no recovery.

**Before soldering the MT3608 wires:**

1. Plug the LiPo into the TP4056
2. Multimeter in DC voltage mode
3. 🔴 Red probe → the free end of one of your TP4056 wires
4. ⚫ Black probe → the free end of the other wire
5. If the display shows **positive voltage** (~+3.7-4.2V) → the wire with the red probe is your **positive supply**
6. If the display shows **negative** → swap the probes — the wire that the red probe is NOW on is your **positive supply**
7. **Wrap red tape** around the actual positive wire so you don't forget

Then solder:
- Red-tape wire → MT3608 **IN+** (regardless of insulation color)
- Other wire → MT3608 **IN-**

Skipping this step is the most common way first-time builders fry their MT3608. The module appears fine in unpowered resistance checks but trips the TP4056 protection under any load — silent, expensive ($1) destruction.

### Setup

- LiPo **UNPLUGGED** from the TP4056
- Iron, solder at hand
- The two wires from Practice 3 already soldered to TP4056 B+ (red) and B- (black) — their free ends ready to go into the MT3608
- One extra wire (~10 cm, both ends stripped and tinned) for MT3608 OUT+ → ESP32 5V (still floating until calibration)

### Solder wires to MT3608 IN+/IN-

1. **Pre-tin** the MT3608 IN+ and IN- pads (same technique as Practice 3 step B)
2. Push the **TP4056-B+ wire** through the MT3608 IN+ through-hole from the bottom
3. Heat + reflow + remove iron (same as Practice 3 step C)
4. Repeat with **TP4056-B- wire** through MT3608 IN-

### Solder the OUT+ wire (but leave its other end floating)

1. Pre-tin the MT3608 **OUT+** pad
2. Push the extra wire through the OUT+ hole, solderOk 
3. **Leave the other end floating, isolated** — do NOT connect it to ESP32 5V yet
4. Tape the floating end so it can't accidentally touch ESP32 pins

### Inspect everything before plugging in the LiPo

Critical visual checks:

- No solder bridges between adjacent pads (B+/B-, IN+/IN-, OUT+/OUT-)
- All joints shiny + cone-shaped, not dull or blobby
- The OUT+ floating end is clearly away from any ESP pin

### Now you're ready for MT3608 calibration

See `hardware_diagram.md` → "Setting the MT3608 Trimpot" for the 5.0V calibration steps. You finally have reliable connections, so the multimeter will read a clean voltage and the trimpot will respond.

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


| Symptom                                        | Likely cause                                                          | Fix                                                                                                                                                      |
| ---------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Solder ball just sits on the pad, doesn't bond | Pad wasn't hot enough — you applied solder to the iron, not the joint | Remove the bad solder using Practice 4 Technique A (heat + pull) or C (drag with clean tip), retry: heat the joint first, then apply solder to the joint |
| Joint looks dull/grainy/rough                  | Moved during cooling, or not enough heat                              | Reheat the joint, let it cool undisturbed                                                                                                                |
| Solder bridge between two adjacent pads        | Too much solder + pads too close                                      | Drag the iron across the bridge with the tip wiped clean (Practice 4 Technique C)                                                                        |
| Wire pulls out easily                          | Cold joint — solder bonded to wire but not pad (or vice versa)        | Reheat both sides simultaneously, apply a tiny bit more solder                                                                                           |
| Iron tip won't pick up solder anymore          | Tip oxidized                                                          | Clean with brass wool, re-tin with fresh solder. Always tin before storing.                                                                              |
| Brown smoke / smell                            | Burning the PCB or insulation                                         | Move iron away immediately. Brief contact is fine; sustained contact damages.                                                                            |


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
- ✅ Undo a joint without wick (Practice 4 — heat + pull, or drag-clean for bridges)

…you're ready to solder the TP4056 + MT3608 connections for the surf frame. Refer to `hardware_diagram.md` for which pads connect to what.

Total practice time: usually 30-60 minutes. By the end, the project soldering is the easy part.