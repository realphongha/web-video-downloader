import requests
import os
import sys
import time
from abc import ABC
from Crypto.Cipher import AES
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

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
        print("Downloading 👀...")
        self.session = requests.Session()
        self.session.headers.update(capture.headers)
        url = self.resolve(capture.url)
        parse_result = self.parse(url)
        files = [None] * len(parse_result.segments)

        total_bytes = 0
        start_time = None

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {
                executor.submit(self.download_segment, i, seg): i
                for i, seg in enumerate(parse_result.segments)
            }

            with tqdm(total=len(parse_result.segments), desc="Downloading", unit="seg",
                      dynamic_ncols=True, mininterval=0.1, file=sys.stdout,
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
                for future in as_completed(futures):
                    if start_time is None:
                        start_time = time.time()
                    i = futures[future]
                    filename = future.result()
                    files[i] = filename
                    if filename:
                        total_bytes += os.path.getsize(filename)

                    pbar.set_description(
                        f"({self.format_speed(total_bytes, time.time() - start_time)})"
                    )
                    pbar.update(1)
                    pbar.refresh()

        self.merge(files, output)

    def format_speed(self, bytes_downloaded, elapsed):
        if elapsed == 0:
            return "0 MB/s"
        mb = bytes_downloaded / (1024 * 1024)
        return f"{mb / elapsed:.2f} MB/s"

    def parse(self, url) -> ParseResult:
        pass

    def download_segment(self, i, seg: Segment):
        pass

