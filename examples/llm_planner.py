"""Optional: let a model write the slides, with guardloop's harness and validator around it.

The extractive planner never invents anything but only rearranges the document.
A model writes better bullets and narration, and also makes things up: this
planner keeps its output inside the same rules (bullet length, commands copied
verbatim from the source) and repairs violations before anything is rendered.

    pip install -e ../guardloop[anthropic]      # https://github.com/yurri775/guardloop
    export ANTHROPIC_API_KEY=...
    python examples/llm_planner.py examples/pods.md -o pods-llm.mp4
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guardloop import (AnthropicProvider, Harness, Journal, Validator, generate_validated, grounded,
                       max_items, required, word_range)

from doc2video import Slide, build, make_voice
from doc2video.plan import parse_markdown

SYSTEM = """You turn a technical document into lesson slides. Use only facts from the document.
Answer with JSON: {"slides": [{"kind": "title|content|code|recap", "title": str,
"bullets": [str], "code": [str], "narration": str}]}. At most 5 bullets of at most 12 words.
Narration: 40 to 120 words, spoken style, no markdown. Code lines copied verbatim."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--voice", default="say")
    args = ap.parse_args()

    md = args.doc.read_text(encoding="utf-8")
    source_code = "\n".join(line for s in parse_markdown(md) for line in s.code)
    rules = Validator(required("slides"), max_items("slides[*].bullets", 5),
                      word_range("slides[*].bullets[*]", low=2, high=12),
                      word_range("slides[*].narration", low=10, high=120),
                      grounded("slides[*].code", source_code))
    harness = Harness(AnthropicProvider(), ["claude-opus-5-5", "claude-sonnet-5-5"],
                      journal=Journal(args.out.with_suffix(".journal.jsonl")))
    result = generate_validated(harness, SYSTEM, md, rules, max_passes=3, task=args.doc.stem)
    slides = [Slide(s["kind"], s["title"], s.get("bullets", []), s.get("code", []), s["narration"])
              for s in result.data["slides"]]
    print(build(slides, make_voice(args.voice), args.out))
    print(harness.journal.summary())


if __name__ == "__main__":
    main()
