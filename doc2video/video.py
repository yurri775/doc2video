"""Assemble slides and narration into an MP4 with subtitles.

Each slide becomes a segment whose length follows its narration (plus a short
pause), the segments are concatenated without re-encoding, and an SRT file is
written alongside, timed sentence by sentence in proportion to their length.
Intermediate files live in a work directory and are reused on the next run.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .plan import Slide, sentences
from .slides import Theme, render_slide
from .voice import Voice

PAUSE = 0.6  # seconds of silence after each slide's narration


@dataclass
class Segment:
    slide: Slide
    image: Path
    audio: Path
    start: float
    seconds: float


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def subtitles(segments: list[Segment]) -> str:
    cues, n = [], 1
    for seg in segments:
        parts = sentences(seg.slide.narration) or [seg.slide.narration]
        speech = seg.seconds - PAUSE
        total_chars = sum(len(p) for p in parts) or 1
        t = seg.start
        for p in parts:
            dt = speech * len(p) / total_chars
            cues.append(f"{n}\n{_ts(t)} --> {_ts(t + dt)}\n{p}\n")
            t += dt
            n += 1
    return "\n".join(cues)


def build(slides: list[Slide], voice: Voice, out: Path, work: Path | None = None,
          theme: Theme = Theme()) -> tuple[Path, Path]:
    """Render ``slides`` to ``out`` (an .mp4) and return (video, subtitles)."""
    out = Path(out)
    work = Path(work or out.with_suffix(".work"))
    work.mkdir(parents=True, exist_ok=True)
    segments, start = [], 0.0
    for i, slide in enumerate(slides, 1):
        img = render_slide(slide, work / f"{i:03}.png", i, len(slides), theme)
        wav = work / f"{i:03}.wav"
        speech = voice.speak(slide.narration, wav)
        seconds = speech + PAUSE
        clip = work / f"{i:03}.mp4"
        _ffmpeg("-loop", "1", "-i", str(img), "-i", str(wav),
                "-af", f"apad=pad_dur={PAUSE}", "-t", f"{seconds:.3f}",
                "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "25",
                "-c:a", "aac", "-b:a", "128k", "-ar", "24000", str(clip))
        segments.append(Segment(slide, img, wav, start, seconds))
        start += seconds
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{(work / f'{i:03}.mp4').resolve()}'\n" for i in range(1, len(slides) + 1)))
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out))
    srt = out.with_suffix(".srt")
    srt.write_text(subtitles(segments), encoding="utf-8")
    return out, srt
