"""
Multi-format subtitle export — VTT, ASS/SSA, TTML, and CSV collaboration sheet.
All functions take a list of SubtitleEntry and write to the given path.
"""

from __future__ import annotations
import csv
import html
from pathlib import Path
from typing import List, Optional, Tuple

from .srt_parser import SubtitleEntry


# ─────────────────────────────────────────────────────────────────────────────
# Timecode helpers
# ─────────────────────────────────────────────────────────────────────────────

def _srt_to_vtt_time(tc: str) -> str:
    """Convert SRT timecode 'HH:MM:SS,mmm' to VTT 'HH:MM:SS.mmm'."""
    return tc.replace(",", ".")


def _srt_to_ass_time(tc: str) -> str:
    """Convert SRT timecode 'HH:MM:SS,mmm' to ASS 'H:MM:SS.cc' (centiseconds)."""
    parts = tc.replace(",", ":").split(":")
    h, m, s, ms = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    cs = ms // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _srt_to_ttml_time(tc: str) -> str:
    """Convert SRT timecode 'HH:MM:SS,mmm' to TTML 'HH:MM:SS.mmm'."""
    return tc.replace(",", ".")


# ─────────────────────────────────────────────────────────────────────────────
# WebVTT Export
# ─────────────────────────────────────────────────────────────────────────────

def write_vtt(entries: List[SubtitleEntry], path: str | Path) -> None:
    """Export subtitles to WebVTT format."""
    lines = ["WEBVTT", ""]

    for entry in entries:
        start = _srt_to_vtt_time(entry.start)
        end = _srt_to_vtt_time(entry.end)
        lines.append(f"{start} --> {end}")
        lines.append(entry.text)
        lines.append("")

    Path(path).write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# ASS/SSA Export (Advanced SubStation Alpha)
# ─────────────────────────────────────────────────────────────────────────────

_ASS_HEADER = """[Script Info]
Title: SRTFlow Export
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,56,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,2,1,2,20,20,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(entries: List[SubtitleEntry], path: str | Path) -> None:
    """Export subtitles to ASS/SSA format."""
    lines = [_ASS_HEADER.strip()]

    for entry in entries:
        start = _srt_to_ass_time(entry.start)
        end = _srt_to_ass_time(entry.end)
        # ASS uses \N for line breaks instead of actual newlines
        text = entry.text.replace("\n", "\\N")
        # Convert basic HTML tags to ASS overrides
        text = text.replace("<i>", "{\\i1}").replace("</i>", "{\\i0}")
        text = text.replace("<b>", "{\\b1}").replace("</b>", "{\\b0}")
        text = text.replace("<u>", "{\\u1}").replace("</u>", "{\\u0}")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# TTML Export (Timed Text Markup Language)
# ─────────────────────────────────────────────────────────────────────────────

def write_ttml(entries: List[SubtitleEntry], path: str | Path) -> None:
    """Export subtitles to TTML (Timed Text) format for broadcast."""
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    header += '<tt xmlns="http://www.w3.org/ns/ttml" xmlns:ttp="http://www.w3.org/ns/ttml#parameter" '
    header += 'xmlns:tts="http://www.w3.org/ns/ttml#styling" xml:lang="en">\n'
    header += '  <head>\n'
    header += '    <styling>\n'
    header += '      <style xml:id="default" tts:fontFamily="Arial" tts:fontSize="100%" '
    header += 'tts:color="white" tts:backgroundColor="transparent" tts:textAlign="center"/>\n'
    header += '    </styling>\n'
    header += '    <layout>\n'
    header += '      <region xml:id="bottom" tts:origin="10% 80%" tts:extent="80% 20%" '
    header += 'tts:displayAlign="after" tts:textAlign="center"/>\n'
    header += '    </layout>\n'
    header += '  </head>\n'
    header += '  <body>\n'
    header += '    <div>\n'

    body_lines = []
    for entry in entries:
        start = _srt_to_ttml_time(entry.start)
        end = _srt_to_ttml_time(entry.end)
        # Escape XML entities and convert newlines to <br/>
        text = html.escape(entry.plain_text).replace("\n", "<br/>")
        body_lines.append(
            f'      <p begin="{start}" end="{end}" style="default" region="bottom">{text}</p>'
        )

    footer = '\n    </div>\n  </body>\n</tt>\n'

    content = header + "\n".join(body_lines) + footer
    Path(path).write_text(content, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# CSV Collaboration Export (original + translated side-by-side)
# ─────────────────────────────────────────────────────────────────────────────

def write_csv_review(
    entries_original: List[SubtitleEntry],
    entries_translated: List[SubtitleEntry],
    path: str | Path,
    source_lang: str = "",
    target_lang: str = "",
) -> None:
    """
    Export a side-by-side review CSV with original and translated text.
    Useful for collaboration — reviewer can edit in a spreadsheet.
    """
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        # Header row
        src_header = f"Original ({source_lang})" if source_lang else "Original"
        tgt_header = f"Translated ({target_lang})" if target_lang else "Translated"
        writer.writerow(["#", "Timecode", src_header, tgt_header, "Notes"])

        for orig, trans in zip(entries_original, entries_translated):
            writer.writerow([
                orig.index,
                orig.timecode,
                orig.plain_text,
                trans.plain_text,
                "",  # Empty notes column for reviewer
            ])


# ─────────────────────────────────────────────────────────────────────────────
# Format detection helper
# ─────────────────────────────────────────────────────────────────────────────

EXPORT_FORMATS = {
    "srt":  ("SubRip Subtitles", "*.srt"),
    "vtt":  ("WebVTT", "*.vtt"),
    "ass":  ("Advanced SubStation Alpha", "*.ass"),
    "ttml": ("Timed Text (TTML)", "*.ttml;*.xml"),
    "csv":  ("Review CSV", "*.csv"),
}


def get_export_filter() -> str:
    """Build a file dialog filter string for all export formats."""
    parts = [f"{name} ({ext})" for name, ext in EXPORT_FORMATS.values()]
    return ";;".join(parts)


def export_by_extension(
    entries: List[SubtitleEntry],
    path: str | Path,
    original_entries: Optional[List[SubtitleEntry]] = None,
    source_lang: str = "",
    target_lang: str = "",
) -> None:
    """Auto-detect format from file extension and export."""
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")

    if ext == "vtt":
        write_vtt(entries, path)
    elif ext == "ass" or ext == "ssa":
        write_ass(entries, path)
    elif ext in ("ttml", "xml"):
        write_ttml(entries, path)
    elif ext == "csv":
        if original_entries:
            write_csv_review(original_entries, entries, path, source_lang, target_lang)
        else:
            # Export translated only as CSV
            write_csv_review(entries, entries, path, source_lang, target_lang)
    else:
        # Default to SRT
        from .srt_parser import write_srt
        write_srt(entries, path)
