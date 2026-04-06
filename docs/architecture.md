# Surf E-Ink Frame - System Architecture

## Configuration (config.yaml)

All settings are external - no code changes needed to switch cameras or adjust timing.

```yaml
# config.yaml - Easy to edit, no code changes needed

# ========== CAMERA SOURCES ==========
# Multiple cameras with fallback support
cameras:
  - name: "Tel Aviv - Gordon Beach"
    url: "https://example-cam.com/telaviv/snapshot.jpg"
    enabled: true
    crop_box: [120, 80, 1800, 980]  # left, top, right, bottom
    priority: 1  # Primary camera

  - name: "Tel Aviv - Hilton Beach"
    url: "https://backup-cam.com/hilton.jpg"
    enabled: true
    crop_box: [100, 50, 1820, 1000]
    priority: 2  # Fallback if primary fails

  - name: "Herzliya Beach"
    url: "https://another-cam.com/herzliya"
    enabled: false  # Disabled for now
    crop_box: [0, 0, 1920, 1080]
    priority: 3

# ========== TIMING ==========
timing:
  fetch_interval_minutes: 5      # How often Pi fetches new frames
  esp_sleep_minutes: 30          # How long ESP32 sleeps
  retry_on_fail_seconds: 60      # Retry delay if camera fails
  max_retries: 3                 # Give up after N failures

  # Daytime only operation
  active_hours:
    start: "06:00"
    end: "20:00"
    timezone: "Asia/Jerusalem"

# ========== DISPLAY ==========
display:
  width: 800
  height: 480
  colors: 7           # 7-color, or 2 for B&W
  dithering: true

# ========== OVERLAY ==========
overlay:
  enabled: true
  position: "bottom"  # bottom, top, corner
  show_location: true
  show_wave_height: true
  show_wind: true
  show_time: true

# ========== WEATHER API ==========
weather:
  provider: "openweathermap"  # or "windy", "surfline"
  api_key: "${WEATHER_API_KEY}"  # From environment variable
  location: "Tel Aviv, IL"

# ========== SERVER ==========
server:
  host: "0.0.0.0"
  port: 8080
```

## Configuration Flow

```mermaid
flowchart LR
    CONFIG[("📄 config.yaml<br/>─────────<br/>cameras[]<br/>timing{}<br/>display{}")] --> FETCH
    CONFIG --> FILTER
    CONFIG --> PROCESS
    CONFIG --> SERVER

    subgraph Runtime["Runtime Behavior"]
        FETCH["fetcher.py<br/>Uses: cameras[], timing{}"]
        FILTER["filter.py<br/>Uses: cameras[].crop_box"]
        PROCESS["processor.py<br/>Uses: display{}, overlay{}"]
        SERVER["server.py<br/>Uses: server{}"]
    end

    ENV[("🔐 .env<br/>─────────<br/>API keys<br/>Secrets")] --> CONFIG
```

## Camera Fallback Logic

```mermaid
flowchart TD
    START[⏰ Time to fetch] --> CAM1{Try Camera 1<br/>Gordon Beach}
    CAM1 -->|Success| FILTER1{Valid frame?}
    CAM1 -->|Timeout/Error| CAM2

    FILTER1 -->|Yes| DONE[✅ Use this frame]
    FILTER1 -->|No - Ad detected| RETRY1{Retries left?}

    RETRY1 -->|Yes| CAM1
    RETRY1 -->|No| CAM2

    CAM2{Try Camera 2<br/>Hilton Beach} -->|Success| FILTER2{Valid frame?}
    CAM2 -->|Timeout/Error| CAM3

    FILTER2 -->|Yes| DONE
    FILTER2 -->|No| CAM3

    CAM3{Try Camera 3<br/>Herzliya} -->|Success| FILTER3{Valid frame?}
    CAM3 -->|Fail| KEEP[📷 Keep last good frame]

    FILTER3 -->|Yes| DONE
    FILTER3 -->|No| KEEP
```

## Changing Cameras - Zero Code Changes

```bash
# Edit config, no Python changes needed
nano config.yaml

# Just restart the service
sudo systemctl restart beachcam

# Or if running manually
python main.py  # Automatically reloads config
```

## High-Level Overview

```mermaid
flowchart TB
    subgraph Internet["☁️ INTERNET"]
        CAM[🎥 Beach Camera<br/>JPEG stream]
        WEATHER[🌤️ Weather API<br/>wind/temp]
        SURF[🏄 Surf Forecast<br/>wave height]
    end

    subgraph PI["🍓 RASPBERRY PI (Always On)"]
        FETCH[1. Fetcher<br/>Download frames<br/>every 5 min]
        FILTER[2. Filter<br/>Reject ads/text<br/>Pick best frame]
        PROCESS[3. Processor<br/>Resize & dither<br/>Add overlay]
        SERVER[4. HTTP Server<br/>/image /hash /meta]
    end

    subgraph ESP["⚡ ESP32 + E-INK (Battery)"]
        WAKE[Wake from sleep]
        CHECK[Check /hash]
        DOWNLOAD[Download /image]
        RENDER[Render to E-Ink]
        SLEEP[Deep Sleep 30 min]
    end

    CAM --> FETCH
    WEATHER --> PROCESS
    SURF --> PROCESS

    FETCH --> FILTER
    FILTER --> PROCESS
    PROCESS --> SERVER

    WAKE --> CHECK
    CHECK -->|hash changed| DOWNLOAD
    CHECK -->|same hash| SLEEP
    DOWNLOAD --> RENDER
    RENDER --> SLEEP
    SLEEP -.->|30 min later| WAKE

    SERVER <-->|HTTP GET| CHECK
    SERVER <-->|HTTP GET| DOWNLOAD
```

## Raspberry Pi - Data Flow

```mermaid
flowchart LR
    subgraph Input
        URL[("🌐 Beach Camera<br/>URL")]
        API[("🌤️ Weather<br/>API")]
    end

    subgraph Processing["Processing Pipeline"]
        F["📥 fetcher.py<br/>─────────<br/>HTTP request<br/>Save raw frame"]
        CR["✂️ cropper.py<br/>─────────<br/>Remove borders<br/>Extract beach area"]
        FL["🔍 filter.py<br/>─────────<br/>Detect ads<br/>Reject bad frames"]
        P["🎨 processor.py<br/>─────────<br/>Resize to 800x480<br/>Color reduction<br/>Dithering<br/>Add overlay"]
    end

    subgraph Output
        IMG[("🖼️ image.bmp<br/>800x480")]
        META[("📋 metadata.json<br/>hash, conditions")]
        HTTP["🌐 HTTP Server<br/>:8080"]
    end

    URL --> F
    F --> CR
    CR --> FL
    FL -->|valid beach| P
    FL -->|ad/junk| X[🗑️ Discard]
    API --> P
    P --> IMG
    P --> META
    IMG --> HTTP
    META --> HTTP
```

## Ad Detection Logic

```mermaid
flowchart TD
    START[Cropped Frame] --> CHECK1{Too much text?<br/>OCR detects words}
    CHECK1 -->|Yes| REJECT[❌ Reject: Ad Frame]
    CHECK1 -->|No| CHECK2{Unusual colors?<br/>Not sea/sky/sand}
    CHECK2 -->|Yes| REJECT
    CHECK2 -->|No| CHECK3{High edge density?<br/>UI elements/buttons}
    CHECK3 -->|Yes| REJECT
    CHECK3 -->|No| CHECK4{Similar to last<br/>known good frame?}
    CHECK4 -->|Very different| SUSPECT[⚠️ Flag for review]
    CHECK4 -->|Similar enough| ACCEPT[✅ Accept: Beach Frame]
    SUSPECT --> ACCEPT
```

### Frame Classification Examples

| Frame Type | Text? | Colors | Edges | Decision |
|------------|-------|--------|-------|----------|
| Clean beach | No | Blue/tan | Low | ✅ Accept |
| Ad overlay | "50% OFF" | Bright red/yellow | High | ❌ Reject |
| Loading screen | "Please wait" | Gray | Medium | ❌ Reject |
| Night/offline | "Camera offline" | Black | Low | ❌ Reject |
| Partial ad | Logo in corner | Normal | Medium | ⚠️ Maybe |

## ESP32 Wake Cycle

```mermaid
flowchart TD
    A[😴 Deep Sleep] -->|30 min timer| B[⚡ Wake Up]
    B --> C[📶 Connect WiFi]
    C --> D[📡 GET /hash]
    D --> E{Hash<br/>changed?}
    E -->|No| A
    E -->|Yes| F[📥 GET /image]
    F --> G[🖼️ Render E-Ink]
    G --> A
```

## Image Transformation

```mermaid
flowchart LR
    subgraph Original["Raw Camera Frame"]
        O["🖼️ Full webpage<br/>with borders/branding"]
    end

    subgraph Steps["Processing Steps"]
        S0["✂️ Crop borders<br/>Extract beach area only"]
        S1["📐 Resize<br/>to 800x480"]
        S2["🎨 Reduce colors<br/>to 7 or B&W"]
        S3["📊 Floyd-Steinberg<br/>dithering"]
        S4["📝 Add overlay<br/>location + conditions"]
    end

    subgraph Final["E-Ink Ready"]
        F["🖼️ 800x480<br/>7 colors<br/>Clean + metadata"]
    end

    O --> S0 --> S1 --> S2 --> S3 --> S4 --> F
```

### What Gets Cropped

```
┌─────────────────────────────────────────────────────────┐
│  CAMERA SITE HEADER / LOGO / BRANDING                   │
├────────┬───────────────────────────────────┬────────────┤
│        │                                   │            │
│  ADS   │    ┌─────────────────────────┐    │   ADS /    │
│  OR    │    │                         │    │   MENU     │
│  MENU  │    │   🌊 ACTUAL BEACH 🌊    │    │            │
│        │    │      (we want this)     │    │            │
│        │    │                         │    │            │
│        │    └─────────────────────────┘    │            │
│        │         ↑ CROP THIS AREA ↑        │            │
├────────┴───────────────────────────────────┴────────────┤
│  FOOTER / SPONSOR LOGOS / TIMESTAMP                     │
└─────────────────────────────────────────────────────────┘

Config needed:
  crop_box = (left, top, right, bottom)  # pixel coordinates
```

## Project Structure

```mermaid
flowchart TB
    subgraph Project["📁 beachcam_pic/"]
        subgraph Pi["📁 pi/"]
            M[main.py<br/>Entry point]
            FE[fetcher.py<br/>Download images]
            CP[cropper.py<br/>Remove borders]
            FI[filter.py<br/>Detect ads]
            PR[processor.py<br/>E-Ink conversion]
            SE[server.py<br/>HTTP endpoints]
            CO[config.py<br/>Loads YAML]
        end
        subgraph Config["📁 config/"]
            YAML["config.yaml<br/>All settings here!"]
            ENV[".env<br/>API keys"]
            EX["config.example.yaml<br/>Template"]
        end
        subgraph ESP["📁 esp32/"]
            FW[firmware/<br/>Arduino code]
            ESPCONF["config.h<br/>WiFi, server IP"]
        end
        subgraph Docs["📁 docs/"]
            AR[architecture.md]
        end
    end

    YAML --> CO
    ENV --> CO
    CO --> M
    CO --> FE
    CO --> CP
    CO --> FI
    CO --> PR
    CO --> SE
```

## Timing Sequence

```mermaid
sequenceDiagram
    participant CAM as 🎥 Beach Camera
    participant PI as 🍓 Raspberry Pi
    participant ESP as ⚡ ESP32

    Note over ESP: Sleeping...

    loop Every 5 minutes
        PI->>CAM: Fetch frame
        CAM-->>PI: JPEG image
        PI->>PI: Filter & Process
    end

    Note over ESP: Wake up! (30 min timer)

    ESP->>PI: GET /hash
    PI-->>ESP: "a1b2c3..."

    alt Hash changed
        ESP->>PI: GET /image
        PI-->>ESP: image.bmp (50KB)
        ESP->>ESP: Render to E-Ink
    else Hash same
        Note over ESP: Skip update
    end

    Note over ESP: Deep sleep 30 min...
```

## Component Summary

| Component | Runs | Input | Output |
|-----------|------|-------|--------|
| **fetcher.py** | Every 5 min | Beach camera URL | Raw JPEG frames |
| **filter.py** | After each fetch | Raw frames | Valid frames only |
| **processor.py** | When new valid frame | Valid frame + weather data | E-Ink optimized BMP |
| **server.py** | Always | HTTP requests | Image/hash/metadata |
| **ESP32** | Every 30 min | Wakes from sleep | Display update |
