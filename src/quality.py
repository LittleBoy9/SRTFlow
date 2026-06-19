"""
Translation quality scorer — flags suspicious translations per line.
Checks for: length anomalies, untranslated words, missing punctuation, etc.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class QualityFlag:
    """A single quality issue for a translated line."""
    index: int          # subtitle index
    kind: str           # "length_ratio" | "untranslated" | "punctuation" | "empty" | "identical"
    message: str        # human-readable description
    severity: str       # "info" | "warning" | "error"
    score_penalty: int  # points deducted from 100


@dataclass
class LineScore:
    """Quality assessment for a single subtitle line."""
    index: int
    score: int          # 0–100
    flags: List[QualityFlag] = field(default_factory=list)


@dataclass
class QualityReport:
    """Overall quality report for a translation batch."""
    scores: List[LineScore] = field(default_factory=list)
    average_score: float = 100.0
    flagged_count: int = 0
    total_count: int = 0


def _word_set(text: str) -> Set[str]:
    """Extract set of words (lowercase, 3+ chars) from text."""
    return {w.lower() for w in re.findall(r"[a-zA-Z\u00C0-\u024F]{3,}", text)}


def score_translation(
    original: str,
    translated: str,
    index: int = 0,
    source_lang: str = "",
    target_lang: str = "",
) -> LineScore:
    """
    Score a single translated line. Returns LineScore (0–100).
    Higher is better. Flags specific issues.
    """
    score = 100
    flags: List[QualityFlag] = []

    orig_stripped = original.strip()
    trans_stripped = translated.strip()

    # Check: empty translation
    if not trans_stripped and orig_stripped:
        flags.append(QualityFlag(
            index=index, kind="empty",
            message="Translation is empty",
            severity="error", score_penalty=100,
        ))
        return LineScore(index=index, score=0, flags=flags)

    # Check: identical (no translation happened)
    if orig_stripped and orig_stripped == trans_stripped and source_lang != target_lang:
        flags.append(QualityFlag(
            index=index, kind="identical",
            message="Translation is identical to original",
            severity="warning", score_penalty=20,
        ))
        score -= 20

    # Check: length ratio anomaly
    if orig_stripped and trans_stripped:
        ratio = len(trans_stripped) / len(orig_stripped)
        if ratio < 0.3:
            penalty = 25
            flags.append(QualityFlag(
                index=index, kind="length_ratio",
                message=f"Translation is much shorter ({ratio:.0%} of original)",
                severity="warning", score_penalty=penalty,
            ))
            score -= penalty
        elif ratio > 3.0:
            penalty = 20
            flags.append(QualityFlag(
                index=index, kind="length_ratio",
                message=f"Translation is much longer ({ratio:.0%} of original)",
                severity="warning", score_penalty=penalty,
            ))
            score -= penalty

    # Check: untranslated words (words from original appearing in translation)
    # Only check for languages with Latin script differences
    latin_source = source_lang in ("en", "fr", "de", "es", "it", "pt", "nl", "sv", "da", "no", "")
    latin_target = target_lang in ("en", "fr", "de", "es", "it", "pt", "nl", "sv", "da", "no", "")

    if latin_source and latin_target and source_lang != target_lang:
        orig_words = _word_set(orig_stripped)
        trans_words = _word_set(trans_stripped)
        # Filter out common cross-language words (names, technical terms)
        common_words = {"the", "and", "for", "but", "not", "you", "all", "can", "her",
                        "was", "one", "our", "out", "are", "has", "his", "how", "its",
                        "may", "new", "now", "old", "see", "way", "who", "did", "get",
                        "let", "say", "she", "too", "use", "dad", "mom", "hey", "yes",
                        "okay", "sure", "just", "like", "well", "good", "look", "come",
                        "know", "think", "right", "thing", "about", "every", "still"}
        overlap = orig_words & trans_words - common_words
        if len(overlap) > 0 and orig_words:
            overlap_ratio = len(overlap) / len(orig_words)
            if overlap_ratio > 0.5:
                penalty = 15
                words_preview = ", ".join(list(overlap)[:3])
                flags.append(QualityFlag(
                    index=index, kind="untranslated",
                    message=f"Many words appear untranslated: {words_preview}",
                    severity="warning", score_penalty=penalty,
                ))
                score -= penalty

    # Check: punctuation mismatch (question mark, exclamation)
    orig_has_question = "?" in orig_stripped
    trans_has_question = "?" in trans_stripped or "\u00BF" in trans_stripped  # Spanish ¿
    if orig_has_question and not trans_has_question:
        penalty = 5
        flags.append(QualityFlag(
            index=index, kind="punctuation",
            message="Original has '?' but translation does not",
            severity="info", score_penalty=penalty,
        ))
        score -= penalty

    orig_has_exclamation = "!" in orig_stripped
    trans_has_exclamation = "!" in trans_stripped or "\u00A1" in trans_stripped  # Spanish ¡
    if orig_has_exclamation and not trans_has_exclamation:
        penalty = 5
        flags.append(QualityFlag(
            index=index, kind="punctuation",
            message="Original has '!' but translation does not",
            severity="info", score_penalty=penalty,
        ))
        score -= penalty

    return LineScore(index=index, score=max(0, score), flags=flags)


def score_batch(
    originals: List[str],
    translations: List[str],
    source_lang: str = "",
    target_lang: str = "",
) -> QualityReport:
    """Score an entire batch of translations. Returns QualityReport."""
    scores: List[LineScore] = []

    for i, (orig, trans) in enumerate(zip(originals, translations)):
        ls = score_translation(orig, trans, index=i + 1,
                               source_lang=source_lang, target_lang=target_lang)
        scores.append(ls)

    total = len(scores)
    flagged = sum(1 for s in scores if s.flags)
    avg = sum(s.score for s in scores) / total if total else 100.0

    return QualityReport(
        scores=scores,
        average_score=round(avg, 1),
        flagged_count=flagged,
        total_count=total,
    )
