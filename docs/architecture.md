# Surf E-Ink Frame - Software Architecture

Simple overview of how the system works.

---

## Two Separate Systems

### 1. Raspberry Pi (always on, wall powered)
- Fetches beach camera images every 5 minutes
- Filters out ads and bad frames
- Processes image for E-Ink display
- Serves image via HTTP on port 8080

### 2. ESP32 + E-Ink (battery powered)
- Wakes every 30 minutes
- Checks if image changed (hash check)
- Downloads new image if changed
- Renders to E-Ink display
- Goes back to deep sleep

---

## Data Flow

```
Beach Camera (internet)
       |
       v
   fetcher.py      <- downloads raw JPEG
       |
       v
   filter.py       <- rejects ads/bad frames
       |
       v
   processor.py    <- resize, dither, add overlay
       |
       v
   server.py       <- serves /image, /hash, /metadata
       |
       v
   ESP32           <- fetches over WiFi
       |
       v
   E-Ink Display   <- shows beach image
```

---

## Pi Components

| File | Purpose |
|------|---------|
| `main.py` | Entry point, runs the loop |
| `fetcher.py` | Downloads frames from camera URL |
| `filter.py` | Detects ads, rejects bad frames |
| `processor.py` | Resizes, dithers, adds overlay |
| `server.py` | HTTP server for ESP32 to fetch from |
| `surf_data.py` | Gets wave/wind data from weather API |

---

## ESP32 Wake Cycle

1. Wake from deep sleep (30 min timer)
2. Connect to WiFi
3. GET `/hash` from Pi
4. If hash same as before → go back to sleep
5. If hash changed → GET `/image`
6. Render image to E-Ink
7. Deep sleep for 30 minutes
8. Repeat

---

## Config System

All settings in `config/config.yaml`:

- **cameras** - URL, crop box, priority
- **timing** - fetch interval, sleep duration, active hours
- **display** - resolution, color mode, dithering
- **overlay** - what info to show on image
- **weather** - API for wave/wind data

No code changes needed to switch cameras or adjust timing.

---

## Ad Detection

The filter rejects frames that look like ads:

| Check | Reject if... |
|-------|--------------|
| Text detection | Too much text on image |
| Color check | Unusual colors (not sea/sky/sand) |
| Similarity | Very different from last good frame |

If rejected, keeps the last known good frame.

---

## Image Processing Pipeline

1. **Crop** - Remove camera site borders/watermarks
2. **Resize** - Scale to 800x480 for display
3. **Color reduce** - Map to 6-color E-Ink palette
4. **Dither** - Floyd-Steinberg for smooth gradients
5. **Overlay** - Add location, wave height, wind info

---

## HTTP Endpoints (Pi Server)

| Endpoint | Returns |
|----------|---------|
| `GET /image` | Current processed BMP image |
| `GET /hash` | MD5 hash of current image |
| `GET /metadata` | JSON with conditions, timestamp |

ESP32 checks `/hash` first to avoid downloading unchanged images.

---

## File Locations

```
beachcam_pic/
├── config/
│   └── config.yaml      <- all settings
├── pi/
│   ├── main.py          <- run this
│   ├── fetcher.py
│   ├── filter.py
│   ├── processor.py
│   ├── server.py
│   └── surf_data.py
├── esp32/
│   └── surf_frame/
│       ├── surf_frame.ino
│       └── credentials.h
├── data/
│   ├── current.bmp      <- processed image
│   ├── current_raw.png  <- original from camera
│   └── metadata.json
└── docs/
    ├── architecture.md  <- this file
    └── hardware_diagram.md
```

---

## Timing

| Event | Frequency |
|-------|-----------|
| Pi fetches from camera | Every 5 minutes |
| ESP32 wakes up | Every 30 minutes |
| Active hours | 6:00 - 20:00 |

At night, ESP32 sleeps until morning to save battery.
