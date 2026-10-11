"""Text-to-speech backends.

Every backend writes a WAV file and returns its duration. Two are shipped:

``SilentVoice``  silence lasting as long as the text would take to read; used in
                 tests and CI, and to preview timing without any engine.
``MacSayVoice``  the built-in macOS ``say`` command; offline and free.

Any other engine (a cloud TTS, a local neural model) fits the same two-method
interface. When choosing one, prefer engines that predict the duration of the
whole utterance: purely autoregressive ones occasionally insert breaths or
noises mid-sentence, which is hard to catch at scale.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Protocol


class Voice(Protocol):
    def speak(self, text: str, out_wav: Path) -> float: ...


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


class SilentVoice:
    def __init__(self, words_per_minute: int = 150, minimum: float = 2.0):
        self.wpm, self.minimum = words_per_minute, minimum

    def speak(self, text: str, out_wav: Path) -> float:
        seconds = max(self.minimum, len(text.split()) * 60 / self.wpm)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                        "-t", f"{seconds:.3f}", str(out_wav)], check=True)
        return duration(out_wav)


class MacSayVoice:
    def __init__(self, voice: str = "Samantha", rate: int = 175):
        if not shutil.which("say"):
            raise RuntimeError("the 'say' command is only available on macOS")
        self.voice, self.rate = voice, rate

    def speak(self, text: str, out_wav: Path) -> float:
        aiff = out_wav.with_suffix(".aiff")
        subprocess.run(["say", "-v", self.voice, "-r", str(self.rate), "-o", str(aiff), text], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", "24000", "-ac", "1", str(out_wav)], check=True)
        aiff.unlink()
        return duration(out_wav)


def make_voice(spec: str) -> Voice:
    """``silent``, ``say`` or ``say:VoiceName``."""
    name, _, arg = spec.partition(":")
    if name == "silent":
        return SilentVoice()
    if name == "say":
        return MacSayVoice(arg or "Samantha")
    raise ValueError(f"unknown voice {spec!r}: use 'silent', 'say' or 'say:VoiceName'")
