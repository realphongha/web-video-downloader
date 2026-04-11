# web-video-downloader

Download streaming videos (HLS, DASH, progressive) from any website.

## Install

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e .

# Install Playwright browsers
playwright install chromium
```

## Quick Start

### Playwright Method (Interactive)

```bash
python main.py --capturer playwright --url "https://example.com/video-page"
```

1. Opens a browser with the video page
2. Play the video manually
3. Press ENTER when video starts
4. Select the stream to download

### API Method (Chrome Extension)

```bash
python main.py --capturer api
```

See [Chrome Extension Setup](#chrome-extension-setup) below.

## Usage

```bash
# Playwright - interactive
python main.py --url "https://example.com/video"

# API - with Chrome extension
python main.py --capturer api

# Options
-t, --threads 8     # Number of download threads (default: 8)
--ffmpeg            # Use ffmpeg instead of multi-threaded download
```

## How It Works

### Capturers

| Method | Description |
|--------|-------------|
| `playwright` | Opens browser, captures network requests interactively |
| `api` | Uses Chrome extension to capture, sends to API server |

### Downloaders

| Stream Type | Downloader |
|------------|------------|
| HLS (.m3u8) | Multi-threaded + ffmpeg |
| DASH (.mpd) | ffmpeg |
| Progressive (.mp4/.webm) | ffmpeg |

### Detection Logic

The capturer detects video URLs by:

1. **URL extension**:
   - `.m3u8` → HLS
   - `.mpd` → DASH
   - `.mp4`/`.webm`/`.mkv` → Progressive

2. **Content-Type fallback**:
   - `application/vnd.apple.mpegurl` → HLS
   - `application/x-mpegurl` → HLS
   - `application/dash+xml` → DASH
   - `video/*` → Progressive

---

## Chrome Extension Setup

### 1. Create Icon Files

Create 3 PNG icons in `capturer/extension/`:

| File | Size |
|------|------|
| `icon16.png` | 16x16 |
| `icon48.png` | 48x48 |
| `icon128.png` | 128x128 |

Or use any placeholder PNGs.

### 2. Load Extension in Chrome

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select `capturer/extension` directory
5. Pin the extension in toolbar

### 3. Usage Flow

```
┌─────────────────┐     POST /select    ┌─────────────┐
│   Chrome        │───────────────────→│  API Server │
│   + Extension  │                   │  (Python)  │
│               │   video URL      │            │
│  1. Capture  │←────────────────│  2. Download│
│  2. Select   │                │            │
└───────────────┘                └────────────┘
```

**Step by step:**

1. Start Python: `python main.py --capturer api`
2. Open video page in Chrome
3. In extension popup, turn **ON** capturing (toggle)
4. Play the video
5. Click **"Select to Download"** on the URL you want
6. Python downloads the video

### Extension Features

| Feature | Description |
|---------|------------|
| **Toggle** | Turn capturing ON/OFF (default OFF) |
| **Storage** | URLs stored in browser (chrome.storage.local) |
| **Deduplication** | Same URL won't be added twice |
| **Sort** | Newest URLs first with timestamp |
| **Clear All** | Clear all captured URLs |
| **Reload Page** | Reload current tab to catch URLs again |
| **Select to Download** | Send URL to API server for download |

---

## Development

### Project Structure

```
web-video-downloader/
├── main.py              # CLI entry point
├── capturer/
│   ├── base.py         # Base capturer interface
│   ├── playwright.py  # Playwright capturer
│   ├── api.py          # API server + extension capturer
│   └── extension/      # Chrome extension
│       ├── manifest.json
│       ├── background.js
│       ├── popup.html
│       └── popup.js
├── downloader/
│   ├── base.py         # Base downloader interface
│   ├── hls.py         # HLS downloader
│   ├── mp4.py         # Progressive downloader
│   └── ffmpeg.py      # ffmpeg-based downloader
└── demo.py            # Legacy demo script
```

### Adding New Capturers

Extend `BaseCapturer`:

```python
from capturer import BaseCapturer, CaptureResult

class MyCapturer(BaseCapturer):
    def capture(self, page_url) -> CaptureResult:
        # Your logic here
        return CaptureResult(url, stream_type, headers)
```

Register in `capturer/__init__.py`.

### Adding New Downloaders

Extend `BaseDownloader`:

```python
from downloader import BaseDownloader

class MyDownloader(BaseDownloader):
    def download(self, result, output_path):
        # Your logic here
```

Register in `downloader/__init__.py`.

---

## Requirements

- Python 3.10+
- Chrome (for API capturer)
- ffmpeg (optional, for --ffmpeg)
- Playwright (for playwright capturer)

## License

MIT