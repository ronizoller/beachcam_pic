# Pi Reflash + Restore Checklist

Rebuild the surf-frame Pi onto a **fresh, high-endurance SD card**. Motivation: the
recurring ~once/day kernel hard-hang is masked by the watchdog, but a *failing SD card*
is the one root cause that could escalate to "won't boot at all" (which the watchdog
can't recover). A fresh card is cheap insurance; beach heat/humidity + the constant
logging writes wear cards fast. Bundle this with the FireBeetle ESP bring-up so it's one
maintenance session.

**Hardware:** Raspberry Pi Zero W (original) — ARMv6, **32-bit only**, 512 MB RAM.
**New card:** high-endurance recommended (SanDisk Max Endurance / Samsung PRO Endurance).

---

## Phase 0 — BACK UP from the CURRENT Pi (before wiping!)

These are NOT in git. Copy them to your laptop first. From your Mac:

```bash
mkdir -p ~/beachcam_pi_backup && cd ~/beachcam_pi_backup
scp roniz@192.168.1.77:/etc/systemd/system/surfpi.service .      # exact working service unit
scp roniz@192.168.1.77:/home/roniz/beachcam_pic/.env .          # secrets (weather API key etc.)
scp roniz@192.168.1.77:/home/roniz/beachcam_pic/config/config.yaml config.yaml.pi  # in case of local edits vs git
```

Also worth keeping: **do NOT wipe or reuse the old card.** Keep it as a known-good
bootable fallback — if the fresh card *also* freezes, you've proven it's not the SD
(→ it's the WiFi driver, leave it on the watchdog), and you can pop the old card back in.

Reference (already in the Pi-setup memory): hostname `ronizpi`, user `roniz`,
reserved IP `192.168.1.77`, WiFi MAC `B8:27:EB:3C:24:FB`, WiFi country `IL`.

---

## Phase 1 — Flash the new card

Use **Raspberry Pi Imager**:
- OS: **Raspberry Pi OS (Legacy, 32-bit) Lite** — 64-bit will NOT boot on the Zero W (ARMv6).
- In the customization (gear/⚙️ before writing), set:
  - Hostname: `ronizpi`
  - Enable SSH (password auth)
  - Username `roniz` / password `hadasim1pi`
  - WiFi SSID + password, WiFi country `IL`
  - Locale/timezone as desired

---

## Phase 2 — First boot + connect

```bash
# give it ~1-2 min to boot & join WiFi, then:
ssh roniz@192.168.1.77          # or roniz@ronizpi.local
```
If the reserved IP doesn't come up, the router's DHCP lease is tied to the WiFi MAC
(unchanged — same Pi), so it should reclaim 192.168.1.77.

---

## Phase 3 — System dependencies

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv python3-pip
sudo reboot          # apply any kernel/firmware update before building
```

---

## Phase 4 — Clone repo + restore secrets + venv

```bash
cd ~
git clone <your-repo-url> beachcam_pic     # or scp the repo up if it's not on a remote
cd ~/beachcam_pic

# restore the non-git files backed up in Phase 0 (from your Mac):
#   scp ~/beachcam_pi_backup/.env            roniz@192.168.1.77:/home/roniz/beachcam_pic/.env
#   (config/config.yaml comes from git; only overwrite if you had local edits)

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r pi/requirements.txt         # Pillow, numpy, flask, pyyaml, python-dotenv, schedule, requests, pytz
```
NOTE: on the Pi Zero (ARMv6, 512 MB) `pip install Pillow`/`numpy` may build from source
and take a while / need swap. If it OOMs, temporarily add swap:
`sudo dphys-swapfile swapoff; sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile; sudo dphys-swapfile setup; sudo dphys-swapfile swapon`

---

## Phase 5 — systemd service

Restore the backed-up unit (preferred — it has the exact working `ExecStart`):
```bash
# from your Mac:  scp ~/beachcam_pi_backup/surfpi.service roniz@192.168.1.77:/tmp/
sudo cp /tmp/surfpi.service /etc/systemd/system/surfpi.service
```
If you don't have the backup, recreate it (verify the ExecStart against how the app runs —
entry point is `pi/main.py` with argparse):
```ini
# /etc/systemd/system/surfpi.service
[Unit]
Description=Surf E-Ink Frame server
After=network-online.target
Wants=network-online.target

[Service]
User=roniz
WorkingDirectory=/home/roniz/beachcam_pic
ExecStart=/home/roniz/beachcam_pic/.venv/bin/python /home/roniz/beachcam_pic/pi/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Phase 6 — RE-APPLY the hardening (not in git — must redo)

**a) Persistent journald** (so any future freeze is diagnosable):
```bash
sudo sed -i 's/^#*Storage=.*/Storage=persistent/' /etc/systemd/journald.conf
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
sudo journalctl --flush            # <-- the step that was easy to miss last time
```

**b) WiFi power-save off** (reduces brcmfmac driver stress):
```bash
sudo tee /etc/systemd/system/wifi-powersave-off.service >/dev/null <<'EOF'
[Unit]
Description=Disable WiFi power save
After=multi-user.target
[Service]
Type=oneshot
ExecStart=/sbin/iw dev wlan0 set power_save off
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now wifi-powersave-off.service
```

**c) Hardware watchdog** (auto-recovers hard-hangs in ~15s):
```bash
echo "dtparam=watchdog=on" | sudo tee -a /boot/config.txt      # Legacy path, NOT /boot/firmware/
sudo sed -i 's/^#*RuntimeWatchdogSec=.*/RuntimeWatchdogSec=15/' /etc/systemd/system.conf
```

---

## Phase 7 — Health logger (LIGHTER this time)

It already proved freezes aren't power/mem/thermal, so drop the per-minute `sync` that
was hammering the card. Every 5 min, no forced sync:
```bash
cat > /home/roniz/health.sh <<'EOF'
#!/bin/bash
echo "$(date +%FT%T) thr=$(vcgencmd get_throttled) $(vcgencmd measure_temp) $(free -m | awk '/Mem:/{print "memavail="$7}')" >> /home/roniz/health.log
EOF
chmod +x /home/roniz/health.sh
( crontab -l 2>/dev/null; echo "*/5 * * * * /home/roniz/health.sh" ) | crontab -
```
(Or skip the logger entirely now that persistent journald is on.)

---

## Phase 8 — Enable, start, verify

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now surfpi
sudo reboot                         # arms the watchdog + confirms clean cold boot

# after reboot, verify everything:
sudo systemctl status surfpi                       # active (running)
curl -s http://192.168.1.77:8080/metadata          # server responding
dmesg | grep -i "Watchdog running"                 # "hardware timeout of 15s"
systemctl show -p RuntimeWatchdogUSec              # 15s
iw wlan0 get power_save                             # Power save: off
journalctl --list-boots                            # 2+ boots = persistence works
```

All green → done. Watch it for a couple of days:
- **No more daily reboots** → the SD card was the culprit, freezes eliminated. 🎉
- **Still freezing (watchdog recovering in 2-3 min)** → it's the WiFi driver, not the SD.
  Leave it on the watchdog permanently — root cause is benign and fully masked. Pop the
  old card back only if you ever want it.
```
