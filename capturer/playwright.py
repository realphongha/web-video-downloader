from .base import BaseCapturer, CaptureResult
from playwright.sync_api import sync_playwright

def filter_headers(headers):
    blacklist = {
        "host",
        "content-length",
        "accept-encoding",   # let requests handle this
        "connection",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "sec-fetch-site",
        "sec-fetch-mode",
        "sec-fetch-dest",
    }

    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in blacklist
    }

def inject_cookies(context, headers):
    cookies = context.cookies()
    cookie_header = "; ".join(
        [f"{c['name']}={c['value']}" for c in cookies]
    )

    headers["Cookie"] = cookie_header
    return headers

class PlaywrightCapturer(BaseCapturer):
    def __init__(self):
        pass

    def capture(self, page_url) -> CaptureResult:
        captured_urls = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            def handle_response(response):
                url = response.url
                request = response.request
                headers = response.headers
                media_type = None
                content_type = headers.get("content-type", "").lower()


                if ".m3u8" in url:
                    print(f"[+] Found m3u8: {url}")
                    media_type = "hls"

                elif ".mpd" in url:
                    print(f"[+] Found dash: {url}")
                    media_type = "dash"

                elif any(ext in url for ext in [".mp4", ".webm", ".mkv"]):
                    print(f"[+] Found progressive video: {url}")
                    media_type = "progressive"

                # 🧠 Content-Type fallback (very important)
                elif "application/vnd.apple.mpegurl" in content_type:
                    print(f"[+] Found hls: {url}")
                    media_type = "hls"

                elif "application/x-mpegurl" in content_type:
                    print(f"[+] Found hls: {url}")
                    media_type = "hls"

                elif "application/dash+xml" in content_type:
                    print(f"[+] Found dash: {url}")
                    media_type = "dash"

                elif "video/" in content_type:
                    print(f"[+] Found progressive video: {url}")
                    media_type = "progressive"

                if media_type:
                    headers = filter_headers(headers)
                    headers = inject_cookies(context, headers)
                    if "user-agent" not in headers:
                        headers["user-agent"] = "Mozilla/5.0"
                    if "referer" not in headers and page_url:
                        headers["referer"] = page_url
                    captured_urls[url] = media_type, headers

            page.on("response", handle_response)

            print("[*] Open page and play video manually")
            page.goto(page_url)

            input("[*] Press ENTER after video starts...")

            # wait a bit for network
            for _ in range(5):
                page.wait_for_timeout(1000)

            browser.close()

        if not captured_urls:
            raise Exception("No m3u8 found")

        print("\n[*] Available streams:")
        urls = list(captured_urls.items())
        for i, (u, (t, h)) in enumerate(urls):
            print(f"{i}: {u}, type: {t}")

        idx = int(input("Select stream: "))
        url, (stream_type, headers) = urls[idx]
        return CaptureResult(url, stream_type, headers)

