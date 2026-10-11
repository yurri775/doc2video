"""Render slides to 1920x1080 PNG images with Pillow (no browser, no office suite)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .plan import Slide

W, H = 1920, 1080

_FONT_CANDIDATES = {
    "sans": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "C:/Windows/Fonts/arial.ttf"],
    "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "C:/Windows/Fonts/arialbd.ttf"],
    "mono": ["/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
             "C:/Windows/Fonts/consola.ttf"],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES[kind]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


@dataclass(frozen=True)
class Theme:
    background: str = "#F6F5F0"
    dark: str = "#0E1B3A"
    text: str = "#0E1B3A"
    muted: str = "#5A6274"
    accent: str = "#C8A24A"
    code_bg: str = "#0E1B3A"
    code_text: str = "#F2E6C4"


def _wrap(draw, text, fnt, width):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and draw.textlength(trial, font=fnt) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def render_slide(slide: Slide, path: Path, index: int, total: int, theme: Theme = Theme()) -> Path:
    t = theme
    dark = slide.kind == "title"
    img = Image.new("RGB", (W, H), t.dark if dark else t.background)
    d = ImageDraw.Draw(img)
    fg = t.background if dark else t.text

    if slide.kind == "title":
        d.rectangle([128, 470, 128 + 160, 476], fill=t.accent)
        y = 510
        for line in _wrap(d, slide.title, font("bold", 96), W - 256):
            d.text((128, y), line, font=font("bold", 96), fill=fg)
            y += 115
    else:
        d.text((128, 110), slide.title, font=font("bold", 64), fill=fg)
        d.rectangle([128, 200, 128 + 220, 205], fill=t.accent)
        if slide.kind == "code":
            fnt = font("mono", 40)
            box_h = 80 + 60 * len(slide.code)
            d.rounded_rectangle([128, 280, W - 128, 280 + box_h], radius=18, fill=t.code_bg)
            for i, line in enumerate(slide.code):
                d.text((172, 320 + i * 60), line, font=fnt, fill=t.code_text)
        else:
            fnt, y = font("sans", 46), 290
            for b in slide.bullets:
                lines = _wrap(d, b, fnt, W - 128 - 200)
                d.ellipse([140, y + 18, 156, y + 34], fill=t.accent)
                for line in lines:
                    d.text((190, y), line, font=fnt, fill=t.text)
                    y += 62
                y += 26
                if y > H - 200:
                    break
    d.text((128, H - 80), f"{index} / {total}", font=font("sans", 26), fill=t.accent if dark else t.muted)
    img.save(path)
    return path
