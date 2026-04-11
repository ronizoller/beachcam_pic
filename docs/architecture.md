a# Surf E-Ink Frame - Software Architecture

Simple overview of how the system works.

---

## Two Separate Systems

### 1. Raspberry Pi (always on, wall powered)
- Fetches beach camera images every 5 minutes
- Scores each frame for composition quality (sea/beach/buildings ratio)
- Keeps the best frame from each collection cycle
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
   fetcher.py      <- downloads raw frame
       |
       v
   cropper.py      <- removes watermarks/borders
       |
       v
   filter.py       <- checks for ads/bad frames
       |
       v
   scorer.py       <- scores composition (sea/beach/buildings)
       |
       v
   candidates/     <- accumulates frames, keeps best
       |
       v
   processor.py    <- resize, dither, add overlay
       |
       v
   server.py       <- serves /image, /hash, /metadata
       |                (clears candidates when ESP32 pulls)
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
| `main.py` | Entry point, orchestrates pipeline and candidate selection |
| `fetcher.py` | Downloads frames from camera URL |
| `cropper.py` | Crops out watermarks and borders |
| `filter.py` | Detects ads, checks frame quality |
| `scorer.py` | Scores frame composition (sea/beach/buildings ratio) |
| `processor.py` | Resizes, dithers, adds overlay |
| `server.py` | HTTP server for ESP32 to fetch from |
| `surf_data.py` | Gets wave/wind data from weather API |
| `config.py` | Loads and provides access to config.yaml |

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

## Frame Selection

The camera moves, so frame composition varies. The Pi collects
candidates between ESP32 wakes and picks the best one:

1. Each fetch cycle: fetch → crop → filter → **score** → save to `candidates/`
2. Score is based on color classification (sea/sky, beach, buildings)
3. Ideal frame: ~60% sea/sky, ~15% beach, ~25% buildings
4. Best-scoring candidate is processed and served as `current.bmp`
5. When ESP32 pulls `/image`, candidates are cleared for next cycle

---

## Image Processing Pipeline

1. **Crop** - Remove camera site borders/watermarks
2. **Resize** - Scale to 800x480 for display
3. **Color reduce** - Map to 6-color E-Ink palette
4. **Dither** - Floyd-Steinberg for smooth gradients
5. **Overlay** - Wave height (bold), horizontal rule, time/location/wind (smaller)

---

## HTTP Endpoints (Pi Server)

| Endpoint | Returns |
|----------|---------|
| `GET /image` | Current processed BMP (clears candidates) |
| `GET /hash` | Hash + timestamp of current image |
| `GET /metadata` | JSON with conditions, score, timestamp |
| `GET /preview` | PNG version for browser viewing |
| `GET /raw` | Original unprocessed frame |

ESP32 checks `/hash` first to avoid downloading unchanged images.
Pulling `/image` signals the Pi to start a fresh candidate collection.

---

## File Locations

```
beachcam_pic/
├── config/
│   └── config.yaml      <- all settings
├── pi/
│   ├── main.py          <- run this
│   ├── fetcher.py
│   ├── cropper.py
│   ├── filter.py
│   ├── scorer.py        <- frame composition scoring
│   ├── processor.py
│   ├── server.py
│   ├── surf_data.py
│   ├── config.py
│   └── data/
│       ├── current.bmp      <- processed best image
│       ├── current_raw.png  <- latest raw from camera
│       ├── metadata.json
│       └── candidates/      <- scored frames (cleared on pull)
├── esp32/
│   └── surf_frame/
│       ├── surf_frame.ino
│       └── credentials.h
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
