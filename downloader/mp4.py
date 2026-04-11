import os
import time
import requests
from .base import BaseDownloader

class MP4Downloader(BaseDownloader):
    def can_handle(self, url, content=None):
        return ".mp4" in url

    def download(self, capture, output: str):
        self.session = requests.Session()
        self.session.headers.update(capture.headers)

        url = capture.url

        for attempt in range(5):
            try:
                with self.session.get(url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(output, "wb") as f:
                        for chunk in r.iter_content(1024 * 1024):
                            if chunk:
                                f.write(chunk)
                return
            except:
                time.sleep(1 + attempt)

        raise Exception("MP4 download failed")
