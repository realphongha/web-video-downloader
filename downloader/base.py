import requests
import os
from abc import ABC
from Crypto.Cipher import AES
from concurrent.futures import ThreadPoolExecutor, as_completed

class Segment:
    def __init__(self, url, key=None, iv=None, is_init=False):
        self.url = url
        self.key = key
        self.iv = iv
        self.is_init = is_init

class ParseResult:
    def __init__(self, segments, metadata=None):
        self.segments = segments
        self.metadata = metadata or {}

class BaseDownloader(ABC):
    def __init__(self, threads=16):
        self.session = None
        self.threads = threads
        self.key_cache = {}

    def can_handle(self) -> bool:
        return True

    def fetch(self, url):
        r = self.session.get(url, timeout=10)
        r.raise_for_status()
        return r.text

    def get_key(self, key_url):
        if key_url not in self.key_cache:
            self.key_cache[key_url] = self.session.get(key_url).content
        return self.key_cache[key_url]

    def decrypt(self, data, key, iv):
        if iv is None:
            iv = bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(data)

    def merge(self, files, output):
        with open(output, "wb") as out:
            for f in files:
                with open(f, "rb") as inp:
                    out.write(inp.read())
        for f in files:
            os.remove(f)

    def download(self, capture, output: str):
        self.session = requests.Session()
        self.session.headers.update(capture.headers)
        url = self.resolve(capture.url)
        parse_result = self.parse(url)
        files = [None] * len(parse_result.segments)

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {
                executor.submit(self.download_segment, i, seg): i
                for i, seg in enumerate(parse_result.segments)
            }

            for future in as_completed(futures):
                i = futures[future]
                files[i] = future.result()

        self.merge(files, output)

    def parse(self, url) -> ParseResult:
        pass

    def download_segment(self, i, seg: Segment):
        pass

