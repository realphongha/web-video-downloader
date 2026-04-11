from .hls import HLSDownloader
from .ffmpeg import FFmpegDownloader
from .mp4 import MP4Downloader
from .dash import DASHDownloader

DOWNLOADERS = {
    "hls": HLSDownloader,
    "mp4": MP4Downloader,
    "dash": DASHDownloader,
    "ffmpeg": FFmpegDownloader
}
