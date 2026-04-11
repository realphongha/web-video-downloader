import argparse
from downloader import DOWNLOADERS
from capturer import CAPTURERS
from datetime import datetime

def download(args, result):
    downloader = DOWNLOADERS["ffmpeg"]() if args.ffmpeg else None
    if not downloader:
        if result.stream_type == "hls":
            downloader = DOWNLOADERS["hls"](args.threads)
        elif result.stream_type == "progressive":
            downloader = DOWNLOADERS["mp4"]()
        else:
            raise Exception(f"Unsupported stream type: {result.stream_type}")
    datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_fn = f"{datetime_str}.mp4"
    downloader.download(result, output_fn)
    print(f"✅ Saved to {output_fn}")

def run_playwright(args):
    assert args.url, "URL is required"
    capturer = CAPTURERS["playwright"]()
    result = capturer.capture(args.url)
    download(args, result)

def run_api(args):
    capturer = CAPTURERS["api"]()
    for result in capturer.capture():
        download(args, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim", action="store_true",
                        help="Simulate the browser with Playwright")
    parser.add_argument("--url", help="Web URL, if using Playwright")
    parser.add_argument("--ffmpeg", action="store_true",
                        help="Use ffmpeg for downloading, slower but more stable")
    parser.add_argument("-t", "--threads", type=int, default=8,
                        help="Number of threads, higher is faster but can be unsafe")
    args = parser.parse_args()

    if args.sim:
        run_playwright(args)
    else:
        run_api(args)

