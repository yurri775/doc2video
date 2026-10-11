"""From a Markdown document to a lesson plan: a list of slides with narration.

The default planner is deterministic and extractive: it never writes a fact that
is not in the document. Headings become slide titles, lists become bullets,
fenced code becomes a code slide, and the narration is the section's prose. A
model-based planner can replace it (see examples/llm_planner.py), as long as it
returns the same :class:`Slide` objects.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Section:
    title: str
    level: int
    prose: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)


@dataclass
class Slide:
    kind: str                      # "title", "content", "code" or "recap"
    title: str
    bullets: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)
    narration: str = ""


class Planner(Protocol):
    def plan(self, markdown: str) -> list[Slide]: ...


def _inline(text: str) -> str:
    """Strip Markdown emphasis, inline code ticks and links, keeping the words."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_markdown(md: str) -> list[Section]:
    sections: list[Section] = []
    cur: Section | None = None
    in_code, para = False, []

    def flush_para():
        if para and cur is not None:
            cur.prose.append(_inline(" ".join(para)))
        para.clear()

    for line in md.splitlines():
        if line.strip().startswith("```"):
            flush_para()
            in_code = not in_code
            continue
        if in_code:
            if cur is not None:
                cur.code.append(line.rstrip())
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            flush_para()
            cur = Section(_inline(m.group(2)), len(m.group(1)))
            sections.append(cur)
            continue
        b = re.match(r"^\s*(?:[-*+]|\d+\.)\s+(.*)", line)
        if b and cur is not None:
            flush_para()
            cur.bullets.append(_inline(b.group(1)))
            continue
        if line.strip():
            para.append(line.strip())
        else:
            flush_para()
    flush_para()
    return sections


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


class ExtractivePlanner:
    """Deterministic planner: everything on screen and in the voice-over comes from the document."""

    def __init__(self, max_bullets: int = 5, max_words: int = 20):
        self.max_bullets, self.max_words = max_bullets, max_words

    def _short(self, text: str) -> str:
        """Keep a bullet readable: cut at a clause boundary rather than mid-thought."""
        text = text.rstrip(".")
        words = text.split()
        if len(words) <= self.max_words:
            return text
        head = " ".join(words[: self.max_words])
        cut = max(head.rfind(","), head.rfind(";"), head.rfind(" — "))
        return head[:cut] if cut > len(head) // 3 else head + "…"

    def plan(self, markdown: str) -> list[Slide]:
        sections = parse_markdown(markdown)
        if not sections:
            raise ValueError("the document has no heading: add at least a '# Title'")
        doc, body = sections[0], sections[1:]
        slides = [Slide("title", doc.title, narration=" ".join(doc.prose) or doc.title)]
        for s in body:
            narration = " ".join(s.prose + [b.rstrip(".") + "." for b in s.bullets])
            if s.bullets:
                bullets = [self._short(b) for b in s.bullets[: self.max_bullets]]
            else:
                bullets = [self._short(x) for x in sum((sentences(p) for p in s.prose), [])][: self.max_bullets]
            slides.append(Slide("content", s.title, bullets, narration=narration or s.title))
            if s.code:
                slides.append(Slide("code", s.title, code=s.code,
                                    narration=f"Here is the command for {s.title.lower()}." if len(s.code) == 1
                                    else f"Here are the commands for {s.title.lower()}."))
        recap = [sl.title for sl in slides if sl.kind == "content"][: self.max_bullets]
        if recap:
            slides.append(Slide("recap", "Recap", recap,
                                narration="To recap, we covered " + ", ".join(t.lower() for t in recap) + "."))
        return slides
