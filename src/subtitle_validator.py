"""
Subtitle validator — checks character/line limits and reading speed.
Flags subtitles that exceed display constraints.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from .srt_parser import SubtitleEntry


# Industry-standard subtitle limits
MAX_CHARS_PER_LINE = 42
MAX_LINES = 2
MIN_CHARS_PER_SEC = 5.0
MAX_CHARS_PER_SEC = 25.0


@dataclass
class ValidationWarning:
    """A single validation issue for a subtitle entry."""
    index: int           # subtitle index
    kind: str            # "length" | "lines" | "speed_fast" | "speed_slow"
    message: str         # human-readable description
    severity: str        # "warning" | "error"
    value: float = 0.0   # the measured value (chars, lines, cps)
    limit: float = 0.0   # the threshold


@dataclass
class ValidationResult:
    """Result of validating a list of subtitle entries."""
    warnings: List[ValidationWarning] = field(default_factory=list)
    total_checked: int = 0
    pass_count: int = 0
    warn_count: int = 0
    error_count: int = 0


def _parse_timecode_ms(tc: str) -> int:
    """Convert 'HH:MM:SS,mmm' to milliseconds."""
    parts = tc.replace(",", ":").split(":")
    h, m, s, ms = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    return h * 3600000 + m * 60000 + s * 1000 + ms


def _duration_seconds(entry: SubtitleEntry) -> float:
    """Duration of a subtitle entry in seconds."""
    start_ms = _parse_timecode_ms(entry.start)
    end_ms = _parse_timecode_ms(entry.end)
    return max((end_ms - start_ms) / 1000.0, 0.1)


def validate_entries(
    entries: List[SubtitleEntry],
    max_chars_per_line: int = MAX_CHARS_PER_LINE,
    max_lines: int = MAX_LINES,
    max_cps: float = MAX_CHARS_PER_SEC,
    min_cps: float = MIN_CHARS_PER_SEC,
) -> ValidationResult:
    """
    Validate subtitle entries against display constraints.
    Returns a ValidationResult with all warnings.
    """
    result = ValidationResult(total_checked=len(entries))

    for entry in entries:
        text = entry.plain_text
        lines = text.split("\n")
        has_issue = False

        # Check line count
        if len(lines) > max_lines:
            result.warnings.append(ValidationWarning(
                index=entry.index,
                kind="lines",
                message=f"#{entry.index}: {len(lines)} lines (max {max_lines})",
                severity="warning",
                value=len(lines),
                limit=max_lines,
            ))
            has_issue = True

        # Check character count per line
        for line_num, line in enumerate(lines, 1):
            char_count = len(line.strip())
            if char_count > max_chars_per_line:
                result.warnings.append(ValidationWarning(
                    index=entry.index,
                    kind="length",
                    message=f"#{entry.index} line {line_num}: {char_count} chars (max {max_chars_per_line})",
                    severity="warning" if char_count <= max_chars_per_line * 1.2 else "error",
                    value=char_count,
                    limit=max_chars_per_line,
                ))
                has_issue = True

        # Check reading speed (characters per second)
        duration = _duration_seconds(entry)
        total_chars = len(text.replace("\n", ""))
        cps = total_chars / duration

        if cps > max_cps:
            result.warnings.append(ValidationWarning(
                index=entry.index,
                kind="speed_fast",
                message=f"#{entry.index}: {cps:.1f} chars/sec (max {max_cps}) — too fast to read",
                severity="warning" if cps <= max_cps * 1.3 else "error",
                value=cps,
                limit=max_cps,
            ))
            has_issue = True
        elif total_chars > 5 and cps < min_cps:
            result.warnings.append(ValidationWarning(
                index=entry.index,
                kind="speed_slow",
                message=f"#{entry.index}: {cps:.1f} chars/sec (min {min_cps}) — unusually slow",
                severity="warning",
                value=cps,
                limit=min_cps,
            ))
            has_issue = True

        if has_issue:
            result.warn_count += 1
        else:
            result.pass_count += 1

    result.error_count = sum(1 for w in result.warnings if w.severity == "error")
    return result


def auto_reflow(text: str, max_chars: int = MAX_CHARS_PER_LINE) -> str:
    """
    Auto-reflow text to fit within max_chars per line.
    Splits at word boundaries, max 2 lines.
    """
    words = text.replace("\n", " ").split()
    if not words:
        return text

    # Try single line first
    single = " ".join(words)
    if len(single) <= max_chars:
        return single

    # Split into two roughly equal lines at a word boundary
    best_split = len(words)
    best_diff = float("inf")

    for i in range(1, len(words)):
        line1 = " ".join(words[:i])
        line2 = " ".join(words[i:])
        if len(line1) <= max_chars and len(line2) <= max_chars:
            diff = abs(len(line1) - len(line2))
            if diff < best_diff:
                best_diff = diff
                best_split = i

    line1 = " ".join(words[:best_split])
    line2 = " ".join(words[best_split:])

    if line2:
        return f"{line1}\n{line2}"
    return line1
