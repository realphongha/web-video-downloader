from .hls import HLSDownloader
from .ffmpeg import FFmpegDownloader

DOWNLOADERS = {
    "hls": HLSDownloader,
    "ffmpeg": FFmpegDownloader
}
