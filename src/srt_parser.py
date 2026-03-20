"""
SRT file parser — reads, writes and manipulates SubRip subtitle files.
Preserves timing exactly. Handles inline HTML tags safely.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# Regex for SRT timecode:  HH:MM:SS,mmm --> HH:MM:SS,mmm
_TIMECODE_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})"
)

# Inline HTML tags we preserve around translation
_TAG_RE = re.compile(r"(<[^>]+>)")


@dataclass
class SubtitleEntry:
    index: int
    start: str          # "HH:MM:SS,mmm"
    end: str            # "HH:MM:SS,mmm"
    text: str           # raw text (may contain <i>, <b>, etc.)
    raw_lines: List[str] = field(default_factory=list, repr=False)

    @property
    def plain_text(self) -> str:
        """Strip inline tags for translation."""
        return _TAG_RE.sub("", self.text).strip()

    @property
    def timecode(self) -> str:
        return f"{self.start} --> {self.end}"

    def with_translated_text(self, translated: str) -> "SubtitleEntry":
        """Return a new entry with translated text, inline tags re-injected."""
        new_text = _reinject_tags(self.text, translated)
        return SubtitleEntry(
            index=self.index,
            start=self.start,
            end=self.end,
            text=new_text,
        )

    def to_srt_block(self) -> str:
        return f"{self.index}\n{self.timecode}\n{self.text}\n"


def _reinject_tags(original: str, translated: str) -> str:
    """
    Re-inject leading/trailing inline tags from the original text
    around the translated text.
    E.g. "<i>Hello world</i>" → translated → "<i>Hola mundo</i>"
    """
    # Extract leading tags
    leading = ""
    trailing = ""
    stripped = original

    lead_match = re.match(r"^((?:<[^>]+>)+)", stripped)
    if lead_match:
        leading = lead_match.group(1)
        stripped = stripped[len(leading):]

    trail_match = re.search(r"((?:</[^>]+>)+)$", stripped)
    if trail_match:
        trailing = trail_match.group(1)

    return f"{leading}{translated}{trailing}"


def parse_srt(path: str | Path) -> List[SubtitleEntry]:
    """
    Parse an SRT file and return a list of SubtitleEntry objects.
    Handles UTF-8 BOM, Windows line endings, missing trailing newline.
    """
    content = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    entries: List[SubtitleEntry] = []
    blocks = re.split(r"\n{2,}", content.strip())

    for block in blocks:
        lines = [l for l in block.split("\n") if l is not None]
        if not lines:
            continue

        # Find index line
        idx_line = lines[0].strip()
        if not idx_line.isdigit():
            continue
        index = int(idx_line)

        # Find timecode line
        if len(lines) < 2:
            continue
        tc_match = _TIMECODE_RE.match(lines[1].strip())
        if not tc_match:
            continue
        start, end = tc_match.group(1), tc_match.group(2)

        # Remaining lines = text
        text = "\n".join(lines[2:]).strip()
        if not text:
            continue

        entries.append(SubtitleEntry(
            index=index,
            start=start,
            end=end,
            text=text,
            raw_lines=lines,
        ))

    return entries


def write_srt(entries: List[SubtitleEntry], path: str | Path) -> None:
    """Write subtitle entries to an SRT file (UTF-8, Unix line endings)."""
    blocks = [entry.to_srt_block() for entry in entries]
    content = "\n".join(blocks) + "\n"
    Path(path).write_text(content, encoding="utf-8")


def suggest_output_path(input_path: str | Path, target_lang: str, suffix: str = "_{lang}") -> Path:
    """
    Generate output file path.
    E.g. movie.srt + "es" → movie_es.srt
    """
    p = Path(input_path)
    lang_suffix = suffix.replace("{lang}", target_lang)
    return p.parent / f"{p.stem}{lang_suffix}{p.suffix}"


def count_words(entries: List[SubtitleEntry]) -> int:
    """Rough word count across all subtitle entries."""
    return sum(len(e.plain_text.split()) for e in entries)
