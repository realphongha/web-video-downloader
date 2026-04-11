# Video URL Capturer Extension

A Chrome extension that captures video stream URLs (m3u8, mpd, mp4, webm) from network requests and sends them to an API server.

## Files

- `manifest.json` - Extension manifest (Manifest V3)
- `background.js` - Service worker that intercepts network requests
- `popup.html` - Popup UI for viewing captured URLs
- `popup.js` - Popup logic

## Setup

1. Create icons (16x16, 48x48, 128x128 PNG) - named `icon16.png`, `icon48.png`, `icon128.png`
2. Load in Chrome:
   - Go to `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select this directory

## API Server

The extension sends captured URLs to `http://127.0.0.1:5000/capture`.

Start the API server in Python:
```python
from capturer.api import APICapturer

capturer = APICapturer()
result = capturer.capture()
```

## How It Works

1. Opens a video page in Chrome with the extension installed
2. The extension intercepts all network requests
3. Detects video URLs by extension (.m3u8, .mpd, .mp4, .webm) or Content-Type
4. Filters headers (removes blacklisted headers like `host`, `content-length`, etc.)
5. Injects cookies and referer
6. Sends to API server at `/capture` endpoint

## Detection Logic

Mirrors `playwright.py`:
- URL contains `.m3u8` → hls
- URL contains `.mpd` → dash
- URL contains `.mp4`, `.webm`, `.mkv` → progressive
- Content-Type: `application/vnd.apple.mpegurl` or `application/x-mpegurl` → hls
- Content-Type: `application/dash+xml` → dash
- Content-Type: `video/*` → progressive