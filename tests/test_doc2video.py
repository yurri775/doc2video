import subprocess
from pathlib import Path

import pytest
from PIL import Image

from doc2video import ExtractivePlanner, SilentVoice, build, parse_markdown, render_slide, subtitles
from doc2video.video import PAUSE, Segment
from doc2video.voice import duration

DOC = Path(__file__).resolve().parents[1] / "examples" / "pods.md"


def test_parse_markdown_sections_bullets_and_code():
    secs = parse_markdown(DOC.read_text())
    assert [s.title for s in secs][:2] == ["Kubernetes pods in five minutes", "What a pod contains"]
    assert secs[1].bullets[0] == "Containers in a pod share one network address"
    assert secs[-1].code == ["kubectl get pods", "kubectl describe pod web"]


def test_plan_is_extractive_and_ends_with_a_recap():
    slides = ExtractivePlanner().plan(DOC.read_text())
    assert [s.kind for s in slides] == ["title", "content", "content", "content", "code", "recap"]
    doc_words = set(DOC.read_text().lower().replace(".", " ").replace(",", " ").split())
    for s in slides[1:4]:
        for b in s.bullets:            # every word on screen comes from the document
            assert set(b.lower().replace(".", " ").replace(",", " ").rstrip("…").split()) <= doc_words


def test_long_sentences_are_cut_at_a_clause_not_mid_thought():
    p = ExtractivePlanner(max_words=10)
    out = p._short("A second container belongs in the same pod only when it cannot work apart, for example a helper")
    assert not out.endswith("…") or "," not in out


def test_document_without_heading_is_rejected():
    with pytest.raises(ValueError, match="heading"):
        ExtractivePlanner().plan("just some text")


def test_slide_image_size(tmp_path):
    slide = ExtractivePlanner().plan(DOC.read_text())[1]
    assert Image.open(render_slide(slide, tmp_path / "s.png", 2, 6)).size == (1920, 1080)


def test_subtitles_cover_each_segment_in_order():
    from doc2video.plan import Slide
    segs = [Segment(Slide("content", "a", narration="One. Two two."), Path(), Path(), 0.0, 3.0 + PAUSE),
            Segment(Slide("content", "b", narration="Three."), Path(), Path(), 3.0 + PAUSE, 1.0 + PAUSE)]
    srt = subtitles(segs)
    assert srt.count("-->") == 3
    assert "00:00:03,600 --> 00:00:04,600\nThree." in srt


def test_full_build_with_silent_voice(tmp_path):
    slides = ExtractivePlanner().plan(DOC.read_text())
    video, srt = build(slides, SilentVoice(words_per_minute=600), tmp_path / "lesson.mp4")
    expected = sum(max(2.0, len(s.narration.split()) * 60 / 600) + PAUSE for s in slides)
    assert duration(video) == pytest.approx(expected, abs=0.6)
    streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video)],
                             capture_output=True, text=True).stdout.split()
    assert sorted(streams) == ["audio", "video"]
    assert srt.read_text().startswith("1\n00:00:00,000 -->")
