"""python -m doc2video lesson.md -o lesson.mp4 [--voice say:Samantha | silent]"""
import argparse
import sys
from pathlib import Path

from .plan import ExtractivePlanner
from .video import build
from .voice import make_voice


def main() -> int:
    ap = argparse.ArgumentParser(prog="doc2video", description="Markdown document to narrated lesson video.")
    ap.add_argument("doc", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True, help="output .mp4")
    ap.add_argument("--voice", default="say", help="'say', 'say:VoiceName' (macOS) or 'silent'")
    args = ap.parse_args()
    slides = ExtractivePlanner().plan(args.doc.read_text(encoding="utf-8"))
    print(f"{len(slides)} slides")
    video, srt = build(slides, make_voice(args.voice), args.out)
    print(video, srt, sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
