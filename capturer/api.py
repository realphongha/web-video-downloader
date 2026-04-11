from fastapi import FastAPI, Request
from threading import Event, Lock
import uvicorn
import json

from .base import BaseCapturer, CaptureResult


class APICapturer(BaseCapturer):
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port

        self._lock = Lock()
        self._captured = []
        self._selected_url = None

        self.app = FastAPI()

        @self.app.get("/urls")
        async def get_urls():
            with self._lock:
                return {"urls": self._captured}

        @self.app.post("/select")
        async def select_url(req: Request):
            data = await req.json()
            url = data.get("url")

            with self._lock:
                for item in self._captured:
                    if item["url"] == url:
                        self._selected_url = item
                        return {"status": "ok", "url": url}

            return {"status": "error", "message": "URL not found"}

        @self.app.post("/capture")
        async def capture_endpoint(req: Request):
            data = await req.json()

            url = data.get("url")
            stream_type = data.get("type")
            headers = data.get("headers", {})

            print(f"[+] Received from extension: {stream_type} {url}")

            with self._lock:
                self._captured.append({
                    "url": url,
                    "type": stream_type,
                    "headers": headers
                })

            return {"status": "ok"}

    def _run_server(self):
        print(f"[*] API server running at http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)

    def capture(self, page_url=None) -> CaptureResult:
        import threading
        import time

        self._captured = []
        self._selected_url = None

        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()

        print("[*] Open video in Chrome with extension, play video, then select URL from extension popup")

        print("[*] Waiting for the next video URL... (Ctrl+C to exit)")
        while True:
            time.sleep(2)

            with self._lock:
                if self._selected_url:
                    item = self._selected_url
                    print(f"[*] Selected: {item['type']} - {item['url']}")
                    yield CaptureResult(
                        url=item["url"],
                        stream_type=item["type"],
                        headers=item["headers"]
                    )
                    self._selected_url = None
                    print("[*] Waiting for the next video URL... (Ctrl+C to exit)")
