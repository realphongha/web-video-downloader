# Build script for web-video-downloader (Windows)
# Usage: .\build.ps1

$ErrorActionPreference = "Stop"

# Clean previous builds
Write-Host "[*] Cleaning previous builds..."
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "main.spec") { Remove-Item -Force "main.spec" }

# Build
Write-Host "[*] Building executable..."
pyinstaller --onefile --name web-video-downloader main.py

Write-Host "[+] Done! Executable: dist/web-video-downloader.exe"
