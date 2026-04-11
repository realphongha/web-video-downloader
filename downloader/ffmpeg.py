import subprocess
from .base import BaseDownloader

class FFmpegDownloader(BaseDownloader):
    def __init__(self, threads=16):
        assert self.can_handle(), "ffmpeg not found"

    def can_handle(self):
        return subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode == 0

    def download(self, capture, output: str):
        print("Downloading with ffmpeg 👀...")
        header_str = ""
        for k, v in capture.headers.items():
            header_str += f"{k}: {v}\r\n"

        cmd = [
            "ffmpeg",
            "-headers", header_str,
            "-i", capture.url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            output
        ]

        subprocess.run(cmd)
