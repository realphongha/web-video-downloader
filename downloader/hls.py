import os
import time
from urllib.parse import urljoin
from .base import BaseDownloader, Segment, ParseResult

class HLSDownloader(BaseDownloader):
    def __init__(self, threads=16):
        super().__init__(threads)

    def can_handle(self, url, content):
        return ".m3u8" in url or "#EXTM3U" in content

    def resolve(self, url):
        text = self.fetch(url)

        # 🎯 if not master → return directly
        if "#EXT-X-STREAM-INF" not in text:
            return url

        print("\n[*] Master playlist detected\n")

        lines = text.splitlines()
        variants = []

        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                bw_match = re.search(r"BANDWIDTH=(\d+)", line)
                res_match = re.search(r"RESOLUTION=(\d+x\d+)", line)

                bw = int(bw_match.group(1)) if bw_match else 0
                res = res_match.group(1) if res_match else "unknown"

                next_line = lines[i + 1].strip()
                full_url = urljoin(url, next_line)

                variants.append({
                    "bw": bw,
                    "res": res,
                    "url": full_url
                })

        if not variants:
            raise Exception("No variants found")

        # 🎮 show choices
        print("[*] Available streams:")
        for i, v in enumerate(variants):
            print(f"{i}: {v['res']} | {v['bw']} | {v['url']}")

        # 🧍 HITL choice
        while True:
            try:
                idx = int(input("\nSelect stream index: "))
                if 0 <= idx < len(variants):
                    break
            except:
                pass
            print("Invalid choice, try again 😼")

        selected = variants[idx]
        print(f"\n[✓] Selected: {selected['res']} | {selected['bw']}")

        # 🔁 recurse (handles nested masters)
        return self.resolve(selected["url"])

    def parse(self, url):
        url = self.resolve(url)
        text = self.fetch(url)

        segments = []
        current_key = None
        current_iv = None

        for line in text.splitlines():
            line = line.strip()

            if line.startswith("#EXT-X-KEY"):
                if "METHOD=NONE" in line:
                    current_key = None
                    current_iv = None
                else:
                    uri = re.search(r'URI="([^"]+)"', line).group(1)
                    iv_match = re.search(r'IV=0x([0-9a-fA-F]+)', line)

                    current_key = urljoin(url, uri)
                    current_iv = bytes.fromhex(iv_match.group(1)) if iv_match else None

            elif line and not line.startswith("#"):
                segments.append(Segment(
                    url=urljoin(url, line),
                    key=current_key,
                    iv=current_iv
                ))

        return ParseResult(segments)

    def download_segment(self, i, seg: Segment):
        filename = f"seg_{i:05d}.ts"

        if os.path.exists(filename):
            return filename

        for attempt in range(5):
            try:
                r = self.session.get(seg.url, stream=True, timeout=15)
                data = b''.join(r.iter_content(1024 * 64))

                if seg.key:
                    key = self.get_key(seg.key)
                    data = self.decrypt(data, key, seg.iv)

                with open(filename, "wb") as f:
                    f.write(data)

                return filename

            except:
                time.sleep(1 + attempt)

        open(filename, "wb").close()
        return filename

