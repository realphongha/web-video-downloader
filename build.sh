#!/bin/bash
# Build script for web-video-downloader (Linux/Mac)
# Usage: ./build.sh

set -e

# Clean previous builds
echo "[*] Cleaning previous builds..."
rm -rf dist build main.spec

# Build
echo "[*] Building executable..."
pyinstaller --onefile --name web-video-downloader main.py

echo "[+] Done! Executable: dist/web-video-downloader"
