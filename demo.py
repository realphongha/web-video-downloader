import requests
import os
import argparse
import re
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from playwright.sync_api import sync_playwright
from Crypto.Cipher import AES

import time

# -------- CLI --------
parser = argparse.ArgumentParser()
parser.add_argument("url", help="m3u8 URL")
parser.add_argument("-o", "--output", default="output.mp4")
parser.add_argument("-t", "--threads", type=int, default=16,
                    help="Number of threads, higher is faster but can be unsafe")
parser.add_argument("--referer", default=None)
parser.add_argument("--keep", action="store_true", help="Keep .ts files")
parser.add_argument("--auto", action="store_true", help="Auto-detect m3u8")
parser.add_argument("--ffmpeg", action="store_true", help="Use ffmpeg, slower but more stable")
args = parser.parse_args()

# -------- Session --------
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

if args.referer:
    session.headers["Referer"] = args.referer

def capture_m3u8(page_url):
    m3u8_urls = set()

    def handle_response(response):
        url = response.url
        if ".m3u8" in url:
            print(f"[+] Found m3u8: {url}")
            m3u8_urls.add(url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.on("response", handle_response)

        print("[*] Open page and play video manually")
        page.goto(page_url)

        input("[*] Press ENTER after video starts...")

        # wait a bit for network
        for _ in range(5):
            page.wait_for_timeout(1000)

        browser.close()

    if not m3u8_urls:
        raise Exception("No m3u8 found")

    print("\n[*] Available streams:")
    urls = list(m3u8_urls)
    for i, u in enumerate(urls):
        print(f"{i}: {u}")

    idx = int(input("Select stream: "))
    return urls[idx]

# -------- Helpers --------
def fetch(url):
    for _ in range(5):
        try:
            r = session.get(url, timeout=10)
            r.raise_for_status()
            return r.text
        except:
            time.sleep(1)
    raise Exception(f"Failed to fetch {url}")

key_cache = {}

def get_key(key_url):
    if key_url not in key_cache:
        print(f"[*] Fetching key: {key_url}")
        key_cache[key_url] = session.get(key_url).content
    return key_cache[key_url]

def decrypt(data, key, iv):
    if iv is None:
        iv = bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(data)

def download_segment(i, segment):
    filename = f"seg_{i:05d}.ts"

    if os.path.exists(filename):
        return filename

    for attempt in range(8):
        try:
            r = session.get(segment["url"], stream=True, timeout=15)
            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}")

            data = b''.join(r.iter_content(1024 * 64))

            # 🔥 decrypt if needed
            if segment["key"]:
                key = get_key(segment["key"])
                data = decrypt(data, key, segment["iv"])

            with open(filename, "wb") as f:
                f.write(data)

            return filename

        except Exception as e:
            print(f"[!] Retry {attempt+1} for segment {i}")
            time.sleep(1 + attempt)

    print(f"[X] Failed segment {i}, writing empty")
    open(filename, "wb").close()
    return filename

def merge(files, output):
    with open(output, "wb") as out:
        for f in files:
            with open(f, "rb") as inp:
                out.write(inp.read())


# -------- Main --------
def main():
    print("[*] Parsing m3u8...")
    if args.auto:
        m3u8_url = args.url
    else:
        m3u8_url = capture_m3u8(args.url)

    if not m3u8_url:
        print("[-] No m3u8 found. Maybe DRM or different loading.")
        return

    if args.ffmpeg:
        print("[*] Downloading with ffmpeg...")

        cmd = [
            "ffmpeg",
            "-headers", f"User-Agent: Mozilla/5.0\r\nReferer: {args.url}\r\n",
            "-i", m3u8_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            args.output
        ]

        subprocess.run(cmd)

        print(f"[✓] Saved to {args.output}")
        return

    m3u8_url = resolve_m3u8(m3u8_url)
    segments = parse_m3u8(m3u8_url)
    print(f"[*] {len(segments)} total segments")

    files = [None] * len(segments)

    print(f"[*] Downloading with {args.threads} threads...")

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(download_segment, i, seg): i
            for i, seg in enumerate(segments)
        }

        for future in tqdm(as_completed(futures), total=len(futures)):
            i = futures[future]
            files[i] = future.result()

    print("[*] Merging...")
    merge(files, args.output)

    if not args.keep:
        print("[*] Cleaning up...")
        for f in files:
            os.remove(f)

    print(f"[✓] Saved to {args.output}")


if __name__ == "__main__":
    main()
