import math
import codecs
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from tqdm import tqdm

from .base import BaseDownloader, Segment


class DashTrack:
    def __init__(self, kind, name, segments, bandwidth=0, codecs="", mime_type=""):
        self.kind = kind
        self.name = name
        self.segments = segments
        self.bandwidth = bandwidth
        self.codecs = codecs
        self.mime_type = mime_type


class DASHDownloader(BaseDownloader):
    def __init__(self, threads=16):
        super().__init__(threads)

    def can_handle(self, url, content=None):
        content = content or ""
        return ".mpd" in url or "application/dash+xml" in content

    def fetch_manifest(self, url):
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        return response.content

    def parse_duration(self, value):
        if not value:
            return None

        match = re.fullmatch(
            r"P(?:(?P<days>\d+(?:\.\d+)?)D)?"
            r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?(?:(?P<minutes>\d+(?:\.\d+)?)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?",
            value,
        )
        if not match:
            return None

        days = float(match.group("days") or 0)
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        return int(days * 86400 + hours * 3600 + minutes * 60 + seconds)

    def get_child_text(self, elem, name):
        child = elem.find(f"{{*}}{name}")
        if child is None or child.text is None:
            return None
        text = child.text.strip()
        return text or None

    def collect_base_url(self, fallback, *elements):
        base_url = fallback
        for elem in elements:
            if elem is None:
                continue
            child = elem.find("{*}BaseURL")
            if child is not None and child.text:
                base_url = urljoin(base_url, child.text.strip())
        return base_url

    def choose_representation(self, adaptation):
        reps = adaptation.findall("{*}Representation")
        if not reps:
            return None

        def score(rep):
            try:
                return int(rep.get("bandwidth", "0"))
            except ValueError:
                return 0

        return sorted(reps, key=score, reverse=True)[0]

    def substitute_template(self, template, representation, number=None, time_value=None):
        rep_id = representation.get("id", "")
        bandwidth = representation.get("bandwidth", "")

        def substitute_token(value, token_name):
            pattern = re.compile(rf"\${token_name}(?P<fmt>%0\d+d)?\$")

            def repl(match):
                fmt = match.group("fmt")
                if fmt and isinstance(value, int):
                    width = int(fmt[2:-1])
                    return f"{value:0{width}d}"
                return str(value)

            return pattern.sub(repl, template)

        result = template
        result = substitute_token(rep_id, "RepresentationID")
        result = substitute_token(bandwidth, "Bandwidth")
        if number is not None:
            result = substitute_token(number, "Number")
        if time_value is not None:
            result = substitute_token(time_value, "Time")
        return result

    def build_template_segments(self, base_url, representation, template, duration_seconds=None):
        segments = []
        init = template.get("initialization")
        media = template.get("media")
        start_number = int(template.get("startNumber", "1"))
        timescale = int(template.get("timescale", "1"))
        duration = int(template.get("duration", "0"))
        timeline = template.find("{*}SegmentTimeline")

        if init:
            segments.append(Segment(
                url=urljoin(base_url, self.substitute_template(init, representation)),
                is_init=True,
            ))

        if timeline is not None:
            current_number = start_number
            current_time = None
            for s in timeline.findall("{*}S"):
                seg_duration = int(s.get("d"))
                repeat = int(s.get("r", "0"))
                if s.get("t") is not None:
                    current_time = int(s.get("t"))
                elif current_time is None:
                    current_time = 0

                if repeat < 0:
                    repeat = 0

                for _ in range(repeat + 1):
                    segment_url = self.substitute_template(
                        media,
                        representation,
                        number=current_number,
                        time_value=current_time,
                    )
                    segments.append(Segment(url=urljoin(base_url, segment_url)))
                    current_number += 1
                    current_time += seg_duration

            return segments

        if not media or duration <= 0 or not duration_seconds:
            return segments

        segment_count = max(1, math.ceil((duration_seconds * timescale) / duration))
        for index in range(segment_count):
            segment_number = start_number + index
            segment_url = self.substitute_template(
                media,
                representation,
                number=segment_number,
            )
            segments.append(Segment(url=urljoin(base_url, segment_url)))

        return segments

    def build_list_segments(self, base_url, segment_list):
        segments = []
        init = segment_list.find("{*}Initialization")
        if init is not None:
            source_url = init.get("sourceURL")
            if source_url:
                segments.append(Segment(
                    url=urljoin(base_url, source_url),
                    is_init=True,
                ))

        for seg in segment_list.findall("{*}SegmentURL"):
            media = seg.get("media")
            if media:
                segments.append(Segment(url=urljoin(base_url, media)))

        return segments

    def build_track(self, mpd_url, period, adaptation, duration_seconds):
        representation = self.choose_representation(adaptation)
        if representation is None:
            return None

        kind = (adaptation.get("contentType") or adaptation.get("mimeType") or "").split("/")[0].lower()
        mime_type = (adaptation.get("mimeType") or representation.get("mimeType") or "").lower()
        codecs = representation.get("codecs", "")
        bandwidth = int(representation.get("bandwidth", "0") or 0)
        name = representation.get("id") or kind or "track"

        base_url = self.collect_base_url(mpd_url, period, adaptation, representation)

        template = representation.find("{*}SegmentTemplate") or adaptation.find("{*}SegmentTemplate")
        segment_list = representation.find("{*}SegmentList") or adaptation.find("{*}SegmentList")
        segment_base = representation.find("{*}SegmentBase") or adaptation.find("{*}SegmentBase")

        segments = []
        if template is not None:
            segments = self.build_template_segments(base_url, representation, template, duration_seconds)
        elif segment_list is not None:
            segments = self.build_list_segments(base_url, segment_list)
        elif segment_base is not None:
            segments = [Segment(url=base_url)]

        if not segments:
            return None

        return DashTrack(
            kind=kind,
            name=name,
            segments=segments,
            bandwidth=bandwidth,
            codecs=codecs,
            mime_type=mime_type,
        )

    def parse(self, url):
        manifest_bytes = self.fetch_manifest(url)

        if manifest_bytes.startswith(codecs.BOM_UTF8):
            manifest_bytes = manifest_bytes[len(codecs.BOM_UTF8):]

        manifest_text = manifest_bytes.decode("utf-8", errors="replace").lstrip()
        if not manifest_text.startswith("<"):
            if url.lower().endswith(".m4s") or "mime=video" in url.lower() or "mime=audio" in url.lower():
                return [
                    DashTrack(
                        kind="video",
                        name="segment",
                        segments=[Segment(url=url)],
                    )
                ]
            preview = manifest_text[:120].replace("\n", "\\n")
            raise Exception(
                "DASH manifest parse failed: expected an MPD XML document, "
                f"got content starting with {preview!r}"
            )

        root = ET.fromstring(manifest_text)

        duration_seconds = self.parse_duration(root.get("mediaPresentationDuration"))
        period = root.find("{*}Period")
        if period is None:
            return []

        if duration_seconds is None:
            duration_seconds = self.parse_duration(period.get("duration"))

        tracks = {}
        for adaptation in period.findall("{*}AdaptationSet"):
            kind = (adaptation.get("contentType") or adaptation.get("mimeType") or "").split("/")[0].lower()
            if kind not in {"video", "audio"}:
                continue

            track = self.build_track(url, period, adaptation, duration_seconds)
            if track and (kind not in tracks or track.bandwidth > tracks[kind].bandwidth):
                tracks[kind] = track

        ordered = list(tracks.values())
        ordered.sort(key=lambda track: (0 if track.kind == "video" else 1, -track.bandwidth))
        return ordered

    def download_file(self, segment, filename):
        for attempt in range(5):
            try:
                response = self.session.get(segment.url, stream=True, timeout=20)
                response.raise_for_status()
                data = b"".join(response.iter_content(1024 * 64))

                if segment.key:
                    key = self.get_key(segment.key)
                    data = self.decrypt(data, key, segment.iv)

                with open(filename, "wb") as f:
                    f.write(data)
                return filename
            except Exception:
                time.sleep(1 + attempt)

        open(filename, "wb").close()
        return filename

    def download_segments(self, segments, workdir, prefix):
        files = [None] * len(segments)
        total_bytes = 0
        start_time = None

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {
                executor.submit(
                    self.download_file,
                    segment,
                    os.path.join(workdir, f"{prefix}_{index:05d}.part"),
                ): index
                for index, segment in enumerate(segments)
            }

            with tqdm(
                total=len(segments),
                desc=f"Downloading {prefix}",
                unit="seg",
                dynamic_ncols=True,
                mininterval=0.1,
            ) as pbar:
                for future in as_completed(futures):
                    if start_time is None:
                        start_time = time.time()
                    index = futures[future]
                    filename = future.result()
                    files[index] = filename
                    if filename and os.path.exists(filename):
                        total_bytes += os.path.getsize(filename)
                    if start_time:
                        pbar.set_description(
                            f"{prefix} ({self.format_speed(total_bytes, time.time() - start_time)})"
                        )
                    pbar.update(1)

        return files

    def concatenate(self, files, output):
        with open(output, "wb") as out:
            for filename in files:
                if not filename:
                    continue
                with open(filename, "rb") as inp:
                    shutil.copyfileobj(inp, out)

        for filename in files:
            if filename and os.path.exists(filename):
                os.remove(filename)

    def mux_with_ffmpeg(self, video_file, audio_file, output):
        if not shutil.which("ffmpeg"):
            return False

        cmd = ["ffmpeg", "-y"]
        if video_file:
            cmd += ["-i", video_file]
        if audio_file:
            cmd += ["-i", audio_file]
        cmd += ["-c", "copy", output]
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def download_track(self, track, workdir):
        track_dir = os.path.join(workdir, track.kind)
        os.makedirs(track_dir, exist_ok=True)
        files = self.download_segments(track.segments, track_dir, track.name)
        track_file = os.path.join(workdir, f"{track.kind}.mp4")
        self.concatenate(files, track_file)
        shutil.rmtree(track_dir, ignore_errors=True)
        return track_file

    def download(self, capture, output: str):
        print("Downloading DASH 👀...")
        self.session = requests.Session()
        self.session.headers.update(capture.headers)

        tracks = self.parse(capture.url)
        if not tracks:
            raise Exception("No DASH tracks found")

        workdir = tempfile.mkdtemp(prefix="dash_")
        try:
            track_files = {}
            for track in tracks:
                track_files[track.kind] = self.download_track(track, workdir)

            video_file = track_files.get("video")
            audio_file = track_files.get("audio")

            if video_file and audio_file and self.mux_with_ffmpeg(video_file, audio_file, output):
                return

            fallback = video_file or audio_file or next(iter(track_files.values()))
            shutil.copyfile(fallback, output)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
