"""doc2video: turn a Markdown document into a narrated lesson video with subtitles."""
from .plan import ExtractivePlanner, Planner, Section, Slide, parse_markdown
from .slides import Theme, render_slide
from .video import build, subtitles
from .voice import MacSayVoice, SilentVoice, Voice, make_voice

__version__ = "0.1.0"
