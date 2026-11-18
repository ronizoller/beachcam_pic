# Project notes

Running notes on the surf frame: current state, open tasks, hard-won lessons, and how-tos.
Consolidated from Claude's session memory on 2026-11-11. Where older notes were superseded,
only the current conclusion is kept (with a short "what we used to think" where the wrong
turn is itself worth remembering).

---

## ⛔ Open tasks (priority order)

1. **Reflash the Pi to a new SD card — URGENT.** The card is confirmed failing: deploys have
   silently written 0-byte files twice (2026-08-25, 2026-10-12). Follow
   `docs/pi_reflash_checklist.md`. Keep the old card intact to swap back and compare.
   Note: the checklist says "Legacy 32-bit"; the Pi actually runs **Bookworm 32-bit** and that is
   fine — what matters is 32-bit (armv6). 64-bit will not boot on the Zero W.
2. **Until then, verify every deploy landed** (see "Deploying to the Pi" below).
3. **Build a net-watchdog** for the WiFi-death failure mode (nothing recovers it today).
4. **ESP firmware reconcile:** `DEV_Config.h` is verified; `surf_frame.ino`, `EPD_13in3e.cpp/.h`,
   `DEV_Config.cpp` are still unverified against the Windows build PC.
5. Small/optional:
   - `battery.json` history is capped at 200 points (~7.7 days), so the start of each charge cycle is lost. Raise the cap?
   - `pi/battery_review.py` still has `CHARGE_START` = cycle 1.
   - Count sdhost timeouts across all boots and record the SD card make (commands in the Pi section).
   - Check `crontab -l` / `sudo crontab -l` for a job at 23:00 (WiFi reset seen at exactly 23:00:00 on 2026-08-19).
   - BMP orientation: firmware logs `WARN: BMP is bottom-up — image will be vertically flipped`
     twice per render, yet the frame shows upright. The Pi's `_orient_for_panel` and the firmware
     disagree on who owns orientation. Harmless now; will bite whoever next touches it.
   - `docs/hardware_diagram.md` says "Pi Zero 2 W"; the real board is a Pi Zero W (original).
6. **Panel looks dark — physical tests next (2026-11-16).** The software is fine (see "Image
   processing"). Try, cheapest first: grey/dark paper over the cream mat; a day without the
   glass (then anti-reflective "museum" glass if it helps); more light on that wall. Optional
   software follow-up only after that: aim red a bit darker (measured red is darker than its
   target, ~18% of a frame), with a before/after.
7. **Sunset scoring — watch the next evenings.** First live run (2026-11-16) picked a close-up;
   fixed with the open-sky term (see Sunset section). If a pick is bad, copy that evening's
   archive the same night (command in the Sunset section).

---

## Hardware at a glance

| Part | Detail |
|---|---|
| Server | Raspberry Pi Zero W (original): single-core ARMv6, 512 MB, 2.4 GHz WiFi only. Too weak for Chromium/Playwright (that's why WebRTC camera support was removed). |
| Frame MCU | DFRobot **FireBeetle 2 ESP32-E (DFR0654)**, ESP32-WROOM-32E, onboard TP4056 LiPo charger, JST battery connector |
| Panel | Waveshare **13.3" e-Paper HAT+ (E)**, Spectra 6 (6 inks), dual controller |
| Battery | 1S LiPo, 2000 mAh |
| Power fix | **1× 2200 µF / 10 V electrolytic across FireBeetle 3V3↔GND** (+ long leg → 3V3, striped leg → GND) |

Sources to verify wiring against (always check these, not memory):
- FireBeetle 2 ESP32-E: https://wiki.dfrobot.com/dfr0654/ (schematic PDF `DFR0654_firebeetle-2-esp32-e_schematics_v1.0.pdf`)
- Waveshare 13.3" e-Paper HAT+ (E): https://www.waveshare.com/13.3inch-e-paper-hat-plus-e.htm and its wiki page

---

## ESP32 / panel

### Pin map (authoritative — `esp32/surf_frame/DEV_Config.h`, verified 2026-09-10)

| Panel signal | GPIO | FireBeetle label |
|---|---|---|
| CLK | 18 | SCK |
| DIN | 23 | MOSI |
| CS_M | 16 | D11 |
| CS_S | 14 | D6 |
| RST | 26 | D3 |
| DC | 25 | D2 |
| BUSY | **17** | **D10** (moved off IO34 on 2026-09-10 to free it for battery sense) |
| PWR | 13 | D7 |
| VCC | 3V3 | 3V3 |
| GND | GND | GND |

- Battery sense: **IO34 / A2**.
- Avoided on purpose: strapping pins (GPIO0/2/5/12/15), onboard LEDs (GPIO2 green, GPIO5 WS2812),
  user button K1 (GPIO27/D4), USB serial (GPIO1/3).
- Panel runs fine at 3.3 V — no 5 V or boost anywhere.

### Flashing

- **Board definition MUST be "ESP32 Dev Module"**, never "FireBeetle 2 ESP32-E". The FireBeetle
  variant remaps the default SPI pins away from 18/23, and the panel stays blank with perfect wiring.
- Build PC is **Windows** (Arduino IDE; FireBeetle on COM5 via CH340). To copy firmware to this repo,
  use the Arduino IDE tabs (each tab is a file): Ctrl+A, Ctrl+C, paste. Overwrite, don't hand-merge.
- `credentials.h` is gitignored — never paste or commit it.
- Flash `panel_test` (6-colour stripes) first when changing wiring, then `surf_frame`.
- Driver is the original Waveshare **bit-bang** SPI + `ReadBusyH` (the HW-SPI / fixed-delay
  experiments were reverted).

### How the panel finally worked (2026-08-11) — the debugging story in brief

Two stacked faults hid each other for weeks:
1. **Bad press-fit SCK wire**: clean 3.27 V at the FireBeetle pin, sagging at the panel end. With SCK
   marginal the panel never started, drew no inrush, and looked "blank" — which invalidated every
   earlier power/SPI/BUSY test. Soldering SCK fixed it. **Solder every signal wire; press-fit can lie.**
2. **Panel power-on inrush browned out the FireBeetle's 600 mA LDO (RT9080)** → `Brownout detector
   was triggered` → boot loop. The ~150 mA average is fine; the brief PON spike isn't. One 2200 µF cap
   on 3V3↔GND fixed it (cf. Pieter van Ginkel's Waveshare brownout write-up on Medium).

Also learned along the way: the wrong board definition (above), and a weak USB cable/charger can drag
the 3V3 rail down to 3.1 V (good cable → 3.27 V).

Handy isolation test that works on any board: a 1.54" B/W panel (SSD1681) via GxEPD2,
`GxEPD2_154_D67(CS=16, DC=25, RST=26, BUSY=34)`, HW-SPI SCK18/MOSI23.

### Watching ESP logs live

The firmware buffers log lines during a wake and POSTs them to the Pi `/log` just before deep sleep.
The Pi appends them to **`~/beachcam_pic/data/esp.log`** (project-root `data/`, not `pi/data/`) under a
`--- <UTC>Z ---` header. Timestamps are only in those headers, so `ts` is wrong (it shows read time).

```bash
tail -n 100 -f ~/beachcam_pic/data/esp.log | while IFS= read -r line; do
  case "$line" in
    ---\ *Z\ ---)
      utc=${line#--- }; utc=${utc% ---}
      echo "=== $(TZ=Asia/Jerusalem date -d "$utc" '+%Y-%m-%d %H:%M:%S %Z') ==="
      ;;
    *) echo "$line" ;;
  esac
done
```

Latest cycle only:
```bash
tac ~/beachcam_pic/data/esp.log | awk '/^--- /{print;exit} {print}' | tac | while IFS= read -r line; do
  case "$line" in
    ---\ *Z\ ---) utc=${line#--- }; utc=${utc% ---}; echo "=== $(TZ=Asia/Jerusalem date -d "$utc" '+%Y-%m-%d %H:%M:%S %Z') ===";;
    *) echo "$line";;
  esac
done
```

A cycle that crashes before deep sleep never POSTs — use USB Serial Monitor (115200) for that.

---

## Battery

### Facts (from the FireBeetle schematic — the wiki text does not say this)

```
VBAT ──[ R5 1M ]──┬── IO34/A2
                  │
               [ R14 1M ]
                  │
                 GND
```
- Exact 1:2 divider → `analogRead(34) × 2`. ~2 µA draw.
- IO34 is ADC1, which keeps working with WiFi on (ADC2 doesn't) — so battery must stay on ADC1.
- Charger: **TP4056X, R6 = 2 kΩ → ~580 mA**. Charge time ≈ `(mAh / 580) × 1.3` h → ~4.5 h for 2000 mAh.
  Charge via USB-C into the FireBeetle itself. Can't overcharge (4.2 V float, auto-terminate).
- Red LED is on `CHRG`: lit = charging. **In practice it never goes off** (probably the ESP wakes keep
  re-triggering charge). Judge "full" by `battery_volts` in `/metadata` reading **4.20–4.21 V**, not by the LED.
- The schematic PDF has no text layer — render it (e.g. `pypdfium2` at scale 5) and read the image.

### Telemetry (shipped 2026-09-10, `2c4d9dd` + `3971d00`)

- ESP reads IO34 on wake **before** the panel refresh (resting voltage, not sag) and logs `BATTERY: x.xxV`.
- Pi parses it into `data/battery.json` (`[utc_iso, volts]` history, capped at 200 points).
- **Warn threshold 3.6 V** → low-battery icon on the panel (120×60, margin 110 since `8166ea9`;
  the old 60×30 was too small to see).
- `bootCount` is `RTC_DATA_ATTR`: survives deep sleep, resets on power loss → valid wake counter per cycle.

```bash
curl -s http://192.168.1.77:8080/metadata     # battery_volts, live
```

### Measured runtime

**Cycle 1: 25.0 days** (charged 2026-09-10 16:57 IDT at 4.21 V → died 2026-10-05 between 16:15 and 16:46 IDT).
- Flat 4.21 → ~3.72 V over days 0–22, then the knee.
- 3.6 V warn crossed 2026-10-04 ~19:00 → **warn-to-death ≈ 1–1.5 days**, as designed.
- Last good wake: Boot #662 at 3.27 V. **Practical cutoff ≈ 3.25 V resting.**
- ~26 wakes/day over a ~13 h active window.
- (The earlier "~4.8 days" estimate was wrong.)

**Cycle 2:** plugged in 2026-10-06 18:53 IDT; first morning reading 2026-10-07 06:17 = 4.15 V
(not 4.21 — maybe unplugged early; unconfirmed).

### Reading a dead frame

- **Cheapest remote check, no ssh:** `/metadata` → `candidates_count`. The pool is only cleared by an
  ESP `/image` pull (or golden hour, or a 3 h cap). A pile-up = the ESP has stopped pulling.
- `esp.log` signatures:
  - Clean stop right after a good `Image rendered.` → **flat battery**.
  - Repeated `Boot #N` bursts with failed renders → **brownout under load** (cap/power fault).
  - Logs still arriving → not a power problem.

---

## Raspberry Pi

### Access

- Hostname `ronizpi` (`ronizpi.local`), user `roniz`, SSH password auth. *(Password not stored in the repo.)*
- Reserved IP **192.168.1.77** (DHCP static lease on the HOT Box 5F router). WiFi MAC `B8:27:EB:3C:24:FB`.
- OS: Raspberry Pi OS **Bookworm 32-bit** (`6.12.87+rpt-rpi-v6`, armv6l). WiFi country IL.
- Boot config: `/boot/config.txt`.

```bash
ssh roniz@192.168.1.77        # more reliable than mDNS
```

### Layout & service

- Repo `/home/roniz/beachcam_pic/`, venv `.venv/`, unit `/etc/systemd/system/surfpi.service`
  (runs as `roniz`, `Restart=always`, `RestartSec=10`, after `network-online.target`).

```bash
sudo systemctl status|restart|stop|start surfpi
sudo journalctl -u surfpi -f
sudo journalctl -u surfpi -n 100
```

### HTTP endpoints (:8080)

| Endpoint | Notes |
|---|---|
| `/preview` | PNG of the current render — safe |
| `/raw` | unprocessed camera frame — safe |
| `/metadata` | JSON: conditions, score, battery, candidates_count — safe |
| `/image` | BMP for the ESP — **clears the candidate pool; don't fetch it by hand** (except while the test card is on) |
| `/hash` | hash + timestamp of the current render — safe |
| `/sleep` | minutes the ESP should sleep (30 by day) — safe |
| `POST /testcard` | from the ESP's next wake, `/image` and `/preview` serve the ink test card (`pi/testcard.py`); pool untouched |
| `POST /testcard/off` | back to camera frames from the next wake |
| `/log` | ESP POSTs logs here |
| `/guests` | guest report |

### Deploying to the Pi (while the SD card is failing)

**git on the Pi is broken since 2026-11-11 (corrupt object). Deploy with curl from GitHub at the
pushed commit, then check md5 + size.** One-liner used on 2026-11-16 (run from the laptop):

```bash
ssh roniz@192.168.1.77 'cd ~/beachcam_pic && B=https://raw.githubusercontent.com/ronizoller/beachcam_pic/<full-sha> && for f in <file> <file>; do curl -fsSL "$B/$f" -o "$f.new" && mv "$f.new" "$f"; done && sync && md5sum <files> && ls -l <files> && sudo systemctl restart surfpi && sleep 5 && systemctl is-active surfpi'
```
Compare with `md5 -r <files>` and `wc -c <files>` on the laptop. ANY 0-byte file = the card ate the write.

- **Signature of a zeroed file:** service exits status 0 in the same second it starts, with no output
  (python running an empty script). A crash gives status 1 + traceback; a missing interpreter gives 203/EXEC.
- **Fix that worked (2026-10-12):** for each touched file
  `curl -o pi/<f>.py https://raw.githubusercontent.com/ronizoller/beachcam_pic/<sha>/pi/<f>.py`,
  then `sync`, compare `md5sum` on the Pi with `md5 -r` on the laptop, restart.
- A successful `touch` does **not** prove the card is fine.
- (Old: git on the Pi worked for fast-forward pulls until 2026-11-11. No longer.)
- Minimise writes until reflashed.

### Failure mode 1: kernel hard-hang (root cause: SD card)

Masked since 2026-07-09 by the hardware watchdog (`RuntimeWatchdogSec=15`), which reboots in 2–3 min.

| Suspect | Verdict |
|---|---|
| Undervoltage | Ruled out — `throttled=0x0` on every freeze |
| Memory leak | Ruled out — memavail steady 261–316 MB |
| Thermal | Ruled out — ≤52 °C |
| Power cut / cable | Ruled out — watchdog fires, so the board is powered |
| WiFi power save | **Refuted** 2026-08-21 (boots with PS *off* actually died sooner; one PS-on boot ran 9 days) |
| **SD card** | **Confirmed** — sdhost timeouts, then two 0-byte deploys |

- Freezes are **bursty**, not daily: clean runs of 9 / 5 / 3.5 days, then clusters (Jul 31: 4 boots in 4 h;
  Aug 17–18: ~10 boots in 23 h). That pattern fits failing storage.
- Still uncaptured: `journalctl --no-pager | grep -c 'timeout waiting for hardware interrupt'` and the
  card make from `/sys/block/mmcblk0/device/{name,manfid,date}`.

WiFi power-save fix (kept as instrument hygiene, not a cure). The original unit raced `wlan0` creation
and lost on 64% of boots. Current unit:
```ini
# /etc/systemd/system/wifi-powersave-off.service
[Unit]
After=sys-subsystem-net-devices-wlan0.device
Wants=sys-subsystem-net-devices-wlan0.device
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'for i in $(seq 30); do /sbin/iw dev wlan0 set power_save off && exit 0; sleep 2; done; exit 1'
```
Plus root crontab `* * * * * /usr/local/sbin/wifi-ps-guard.sh`, which logs to `/var/log/wifi-ps.log` only
when it intervenes. ~1 line per boot is normal; a line hours into a boot means something re-enabled PS.

### Failure mode 2: WiFi death (kernel alive)

The Pi drops off the LAN while the OS runs fine. **The watchdog can never catch this**, because systemd
is healthy and keeps petting it. Only a manual power-cycle recovers it today.

**Tell the two modes apart in 5 seconds — touch the board, look at the green ACT LED:**

| Board | ACT LED | Meaning |
|---|---|---|
| Warm | Flickering | WiFi death (the flicker is `health.sh` syncing every minute) |
| Warm | Solid / off | Kernel hang — watchdog should recover in 2–3 min |
| Cold | Off | No power |

From the LAN: `ping -c2 192.168.1.77` dead + `arp -an | grep 192.168.1.77` shows `(incomplete)` = off the LAN entirely.

Log signature after recovery — the regdom reset means `wlan0` was torn down and re-registered:
```
CTRL-EVENT-DISCONNECTED bssid=... reason=0 locally_generated=1
CTRL-EVENT-REGDOM-CHANGE init=CORE type=WORLD
CTRL-EVENT-REGDOM-CHANGE init=USER type=COUNTRY alpha2=IL
```

**Net-watchdog to build:** cron script pings the gateway `192.168.1.1`; after N failures escalate
`ip link set wlan0 down/up` → `modprobe -r brcmfmac && modprobe brcmfmac` → `reboot`, logging each step
to a `sync`-ed file.

### Diagnostics gotchas

- No RTC: `journalctl --list-boots` FIRST ENTRY times are fake-hwclock junk (up to 1 h off). Measure
  boot lifetime as the delta between consecutive **LAST ENTRY** values.
- Persistent journal needed: `Storage=persistent`, `mkdir /var/log/journal`, `systemd-tmpfiles --create`,
  restart journald, **`journalctl --flush`**. Working since 2026-07-03.
- `health.sh` (roniz cron, every minute, with `sync`) appends `date thr=<throttled> temp memavail` to
  `/home/roniz/health.log`.
- Watchdog check: `ls /dev/watchdog` (not `/proc/sys/kernel/watchdog`).

---

## Image processing / panel colours

Resolved and approved on the glass 2026-08-28 ("now its nice"). Commits `f3d8862` (yellow), `803ef98` (blue).
Re-examined 2026-11-16 when the panel looked dark — see "Real inks measured" below.

### The whole pipeline (as of `836a7ec`, 2026-11-16)

In `pi/main.py`: fetch 1920×1080 → main camera levelled −3.3° about the top-left → `crop_box`
`[0,80,1333,1080]` → score and keep the best recent frame.
In `pi/processor.py`: resize to 1600×1200 (LANCZOS) → saturation ×1.05 → gamma 1.3 → overlay
(pills / forecast card / battery icon) → Floyd-Steinberg dither to the 6 targets → rotate + flip for the panel.
Contrast, the linear brightness multiplier and the warm R/B gains were all no-ops and were
**removed** on 2026-11-16 (output pixel-identical). None of the steps adapts to the picture.

Measured on the 2026-11-16 10:48 frame:
- **Gamma matters for ink share.** Dither only (no saturation, no gamma): black 16%, white 5%.
  Current: black 7%, white 13%. Brightness 109 → 130. Keep gamma.
- **Dithering on the Pi is necessary.** Without it the ESP's `rgbToPanel6()` maps each pixel on its
  own: 40% of the frame went solid black and the sea became green/white blotches.
- The new left-anchored crop shows more of the dark hill under Jaffa than the old centre crop.
  Average brightness is the same (143.6 vs 143.5), but the picture can *feel* heavier.

### Real inks measured (2026-11-16, test card)

How: `curl -X POST http://192.168.1.77:8080/testcard`, wait for the ESP wake (or press RST on the
FireBeetle), photograph in daylight with the mat in shot, `POST /testcard/off`. The frame glass
reflects the room and washes out whichever side catches the window — take two shots from
different angles and use the clean regions of each. Normalised so the cream mat = 225:

| Ink | Pi target | Measured (mat = 225) | Relative to panel white = 255 |
|---|---|---|---|
| black | (15,15,15) | (10,10,11) | (19,19,21) |
| white | (215,212,205) | (128,131,128) | (253,255,253) |
| blue | (105,155,188) | (66,82,112) | (130,162,221) |
| yellow | (200,180,110) | (132,119,11) | (255,235,21) |
| red | (175,45,40) | (77,20,7) | (152,39,13) |
| green | (30,110,40) | (41,64,48) | (81,126,94) |

What it showed:
- **Panel white is only ~57% as bright as the mat next to it.** That, plus glass reflections, is
  why the panel looks dark/dull. It is physical, not software.
- Relative to the panel's own white, blue is close to its target (an early guess that blue ink is
  "dark navy" and the main cause was wrong). Red is darker than its target; green is greyer;
  yellow is much more saturated and is the brightest colour ink.
- **Dithering against the measured inks is worse:** green 10% → 36%, white 13% → 3%, darker overall —
  the greyish real green becomes the best match for muted midtones. Don't ship it.
- The panel and ESP are healthy: every ink lands where it should, black is a true black.
- In the first card photo the top-left black square looked grey — that was a window reflection, not a fault.

### Mental model

- `PALETTES["6color"]` in `pi/processor.py` are **match targets for the quantizer, not displayed colours**.
  Firmware `rgbToPanel6()` maps them to the 6 real inks.
- Moving an anchor **toward** the midtones **grows** its share; away shrinks it.
- Panel brightness = how much area lands on white/yellow ink. (Gamma does shift that share — see above.)
- Anchors must still satisfy `rgbToPanel6()`: black mean < 50; white mean > 200, channels within 30;
  red `r>150 && r>g+50 && r>b+50`; yellow `r>150 && g>120 && b<150`; green mean > 50, `g>r, g>b, g>100`.

### Current anchors

black (15,15,15) · white (215,212,205) · red (175,45,40) · green (30,115,50), jaffa (30,110,40) ·
**yellow (200,180,110)** · **blue (105,155,188)** (jaffa + beach) · saturation 1.05.

### Traps

- **Cross-anchor bleed comes from Floyd-Steinberg dithering, not nearest-colour.** Raising yellow's blue
  to catch sand also turned the sea olive — the ditherer used yellow as a mixing partner for teal.
  RGB distance alone will mislead you; always re-render and count.
- Desaturating an anchor makes it a *better* dither partner, so it bleeds *more*.
- **Fix bleed from the other anchor** — moving blue closer to real sea removed the need for the mixture.
- Dry sand lost to white on the **blue channel**; real sand is a pale warm neutral, so the yellow anchor's
  blue had to go up.
- `processor.process()` does not apply `crop_box` (the fetcher does) — local renders of `/raw` include the
  watermark band. Directions hold, absolute % don't. For true production numbers, count inks in `/preview`.
- The Spectra 6 white is a dull off-white (~30–35% reflectance) — there's a physical brightness ceiling.

### Don't revisit

- Turning dithering off — the speckle is fine at viewing distance; don't judge by a zoomed preview.
- Region/pixel-based processing — palette stays global and position-independent.
- Reddish filter — brighter but kills the blue sea.
- `saturation` — nearly inert after 6-colour quantization.
- Shrinking blue — costs the sea.
- Removing gamma/saturation ("dither only") — measured darker (2026-11-16).
- Dithering against the measured real inks — measured worse (green takes over).

### Experiment recipe

```bash
python3 -m venv v && ./v/bin/pip install pillow numpy pyyaml python-dotenv
cd pi && ../v/bin/python -c "import processor; processor.Processor().process(img, None, color_profile='jaffa')"
```
Swap anchors in memory with `processor.PALETTES['6color'][i] = (r,g,b)`. Always pass
`color_profile='jaffa'`. Count exact RGB values in the output to get the ink distribution.

### Panel UI: ink contrast against the light scrim (232,229,222)

| Ink | Contrast |
|---|---|
| black | 9.00:1 |
| red | 4.53:1 |
| blue | 4.22:1 |
| green | 3.78:1 |
| **yellow** | **1.23:1 — invisible** |

Never encode meaning in yellow on a light background. The forecast card (`bc97451`) uses a black
series with only the highlighted span in green, against a labelled 0/5/10 axis.

---

## Sunset (goodnight) image selection

**2026-11-18 — Jaffa detector fixed; blur guard.** A sea view with a big orange sky won (1.37) with
Jaffa only a dark sliver. Two false positives: (1) the texture check looked at the top 12%, where
the camera's date/time line (since 11-15) is the only detail in a sea view — ratio 14-30, "full
Jaffa"; (2) the orange sky matched the floodlit-stone colour (10% of the upper half). Sunset now
checks texture in rows 10-30% (tower views 3.9-7.4, sea views 0.3-1.0) and counts floodlit pixels
only where there is detail (smooth sky drops out). Also a blur guard (score × ramp(sharpness
1.5→3.0)): a smeared mid-zoom tower frame (sharpness 2.0) would otherwise have won. Re-scored all
seven evenings: 11-18 → 17:06 tower view; 08-27, 11-11, 11-14, 11-15, 11-16, 11-17 picks unchanged
(11-11 margin thin: 1.174 vs a pre-sunset Jaffa frame 1.15). Sunrise still uses the old top-12%
check (date line affects it too; untested, no sunrise archive).

**2026-11-16 — open sky of any colour counts.** First live evening: the camera rotated between a
close-up of Jaffa (no sky, tower top cut off), the tower view, and a sea view to the north. The
pink was only over the sea view; over the tower the sky was blue, so every Jaffa view scored sky 0
and the lamp-filled close-up won on lights (1.125 vs tower view 1.078). The sky term is now
`max(warm sky area, 0.6 × open sky)`, where open sky = share of rows 8–45% that is smooth and not
dark (close-ups 0.05–0.07, tower view 0.50). Re-scored: 11-11/14/15 picks unchanged; 11-16 →
17:07 tower view, 1.30 vs 1.125 (Roni's pick — the pink sea view is prettier only for its colour).

**2026-11-15 — sunset scoring, crop and levelling changed.** `7ee50f1` maxed out: every frame had
Jaffa and the orange sky at sunset filled the sky term, so ~5 frames tied and the sharpness
tie-break picked a flat pre-sunset frame (16:37). Now, inside the sunset window only:
`1.5 × (0.35 Jaffa + 0.25 sky area + 0.20 after-sunset + 0.20 lights)`.
Jaffa = texture OR floodlit stone anywhere in the upper half; sky area = how much smooth warm
sky is visible; after-sunset ramps 0→1 over the first 20 min; lights = brightest points vs the
scene median. Sharpness tie-break margin 0.05 → 0.02. Sunrise and daytime unchanged.
Crop is now `[0, 80, 1333, 1080]` (keeps the left edge, where Jaffa is; the old full-width crop
was centre-cropped by the processor and lost the tower in the zoomed view), and the main camera
is levelled by −3.3° about the top-left corner before cropping (horizon rose 3.2–3.4° to the
right in every view). Re-scored picks: 08-27 19:39, 11-11 17:07, 11-14 17:07 lit Jaffa,
11-15 17:08 (Roni's pick). Since 11-15 the camera burns a date/time line under the watermark;
the 80 px cut leaves it visible top-left — left as is, the frame's passe-partout may hide it.
**Checked on the glass 2026-11-16: the mat hides the date/time line**; Jaffa and the tower are in,
horizon level.

**The panel lags the live camera by 30–60 min.** The Pi fetches every 5 min and keeps the best-scoring
recent frame; the ESP wakes only every 30 min (`esp_sleep_minutes`) to download it. The time in the
bottom-right pill ("Tel Aviv · 10:04") says which frame is showing. Pressing RST on the FireBeetle
forces an immediate wake + download (the ESP fetches `/image` every wake, no hash check).

**2026-11-14 — sunset scoring changed (`7ee50f1`).** An empty-sea frame beat the lit Jaffa view
because the daytime score counts warm pixels, and at sunset everything is warm. Inside the golden
window the Jaffa camera is now scored `1.5 × (0.6 × Jaffa structure + 0.4 × sky warmth)`. Jaffa is
detected by texture (top-left vs the plain-sky top-right), not colour, and beach colour is dropped.
Also `77287ae`: 1-min sampling in the last 10 min of the window. Bad days are reported manually
and investigated then (no automatic multi-day archive).

(The 2026-11-11 notes below describe the scorer before that change.)

- **Only the latest evening is kept** in `data/golden_archive/<date>/sunset/` (frames + `manifest.jsonl`
  with score breakdown). It is deleted at the next sunset or service restart, so copy it quickly:
  `scp -r roniz@192.168.1.77:beachcam_pic/data/golden_archive/<date> pi/data/golden_archive/`
- The camera cycles wide / mid / zoomed-Jaffa views every ~2.5 min; we don't control which.
- Within the sunset window the warm-sky bonus is usually maxed at 1.0, so the composition score
  decides — and at dusk it effectively counts streetlights (its detectors look for warm pixels).
  Result: the pick tends to be the last lit-up Jaffa frame before the sky-darkness gate (110).

---

## Surf profile (for rating tuning)

Tel Aviv, west-facing beach. Max comfortable wave height ~116 cm. Prefers glassy conditions — even light
onshore wind (5–10 km/h) noticeably hurts. Mediterranean swell: 9 s+ period is a great day.

---

## History: the abandoned battery chain (pre-FireBeetle, May–July 2026)

The first design was LiPo → TP4056 → MT3608 boost (5 V) → ESP32 DevKitC. Abandoned 2026-07-09 for the
FireBeetle's built-in charger after:
- An MT3608 killed by **reverse polarity**: a cheap TP4056 had reversed silkscreen (`B+` pad was actually
  negative) and the LiPo JST had non-standard wire colours. A polarity-killed MT3608 still measures
  ~100 kΩ unpowered and looks fine.
- A TP4056 whose battery path died (LiPo at 4.0 V, outputs 0 V).

**Lesson that still applies:** never trust silkscreen or wire colour on cheap modules/batteries —
multimeter-verify polarity before connecting power, and mark the verified positive wire.

Old ESP32 DevKitC pin map (for reference): `SCK13 MOSI14 CS_M15 CS_S2 RST26 DC27 BUSY25 PWR4`
(CS_S=GPIO2 and CS_M=GPIO15 are strapping pins — unplug CS_S if upload fails).
