from .hls import HLSDownloader
from .ffmpeg import FFmpegDownloader
from .mp4 import MP4Downloader

DOWNLOADERS = {
    "hls": HLSDownloader,
    "mp4": MP4Downloader,
    "ffmpeg": FFmpegDownloader
}
