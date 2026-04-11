from fastapi import FastAPI, Request
from threading import Event
import uvicorn

from .base import BaseCapturer, CaptureResult


class APICapturer(BaseCapturer):
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port

        self._event = Event()
        self._result = None

        self.app = FastAPI()

        @self.app.post("/download")
        async def download_endpoint(req: Request):
            data = await req.json()
            url = data.get("url")
            stream_type = data.get("type")
            headers = data.get("headers", {})

            print(f"[*] Download requested: {stream_type} {url}")

            self._result = CaptureResult(
                url=url,
                stream_type=stream_type,
                headers=headers
            )
            self._event.set()

            return {"status": "ok"}

    def _run_server(self):
        print(f"[*] API server running at http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)

    def capture(self, page_url=None) -> CaptureResult:
        import threading

        self._result = None
        self._event = Event()

        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()

        print("[*] Open video in Chrome with extension")
        print("[*] 1. Turn ON capturing in extension popup")
        print("[*] 2. Play the video")
        print("[*] 3. Click 'Select to Download' in popup")
        print("[*] Waiting for URL selection...")

        while True:
            print("[*] Waiting for video URL... (Ctrl+C to exit)")
            self._event.wait()
            yield self._result

            self._result = None
            self._event.clear()

