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
| `/image` | BMP for the ESP — **clears the candidate pool; don't fetch it by hand** |
| `/log` | ESP POSTs logs here |
| `/guests` | guest report |

### Deploying to the Pi (while the SD card is failing)

```bash
cd ~/beachcam_pic && git pull && sudo systemctl restart surfpi
ls -l pi/*.py          # ANY 0-byte file = the card ate the write
```

- **Signature of a zeroed file:** service exits status 0 in the same second it starts, with no output
  (python running an empty script). A crash gives status 1 + traceback; a missing interpreter gives 203/EXEC.
- **Fix that worked (2026-10-12):** for each touched file
  `curl -o pi/<f>.py https://raw.githubusercontent.com/ronizoller/beachcam_pic/<sha>/pi/<f>.py`,
  then `sync`, compare `md5sum` on the Pi with `md5 -r` on the laptop, restart.
- A successful `touch` does **not** prove the card is fine.
- git on the Pi works for fast-forward pulls (verified 2026-08-28); scp isn't required.
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

### Mental model

- `PALETTES["6color"]` in `pi/processor.py` are **match targets for the quantizer, not displayed colours**.
  Firmware `rgbToPanel6()` maps them to the 6 real inks.
- Moving an anchor **toward** the midtones **grows** its share; away shrinks it.
- Panel brightness = how much area lands on white/yellow ink. Gamma and the brightness multiplier barely matter.
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

Reviewed 2026-11-11 — **scorer left unchanged**; both the 16:41 tower-silhouette and the 17:07
lit-Jaffa frames were judged good. Bad days are reported manually and investigated then.

- **Only the latest evening is kept** in `data/golden_archive/<date>/sunset/` (frames + `manifest.jsonl`
  with score breakdown). It is deleted at the next sunset or service restart, so copy it quickly:
  `scp -r roniz@192.168.1.77:beachcam_pic/data/golden_archive/<date> pi/data/golden_archive/`
- The camera cycles wide / mid / zoomed-Jaffa views every ~2.5 min; we don't control which.
- Within the sunset window the warm-sky bonus is usually maxed at 1.0, so the composition score
  decides — and at dusk it effectively counts streetlights (its detectors look for warm pixels).
  Result: the pick tends to be the last lit-up Jaffa frame before the sky-darkness gate (110).
- Ready alternative if the silhouette look is preferred later (tested on one evening):
  `final = 0.3*base + 0.5*warm_score*sky_brightness/255` during sunset, warm_score uncapped.

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
