"""Post-processing to strip auto-punctuation and convert spoken punctuation words."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Characters Whisper inserts automatically — we strip these so the user has full control.
_AUTO_PUNCT_RE = re.compile(r"[.!?,;:]")

# Spoken punctuation → symbol replacements.
# Ordered longest-phrase-first to prevent partial matches
# (e.g. "exclamation point" must match before "point" could interfere).
_PUNCTUATION_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bexclamation\s+point\b", re.IGNORECASE), "!"),
    (re.compile(r"\bexclamation\s+mark\b", re.IGNORECASE), "!"),
    (re.compile(r"\bquestion\s+mark\b", re.IGNORECASE), "?"),
    (re.compile(r"\bopen\s+parenthesis\b", re.IGNORECASE), "("),
    (re.compile(r"\bclose\s+parenthesis\b", re.IGNORECASE), ")"),
    (re.compile(r"\bopen\s+paren\b", re.IGNORECASE), "("),
    (re.compile(r"\bclose\s+paren\b", re.IGNORECASE), ")"),
    (re.compile(r"\bopen\s+quote\b", re.IGNORECASE), "\u201c"),
    (re.compile(r"\bclose\s+quote\b", re.IGNORECASE), "\u201d"),
    (re.compile(r"\bopen\s+bracket\b", re.IGNORECASE), "["),
    (re.compile(r"\bclose\s+bracket\b", re.IGNORECASE), "]"),
    (re.compile(r"\bopen\s+brace\b", re.IGNORECASE), "{"),
    (re.compile(r"\bclose\s+brace\b", re.IGNORECASE), "}"),
    (re.compile(r"\bsemi\s*colon\b", re.IGNORECASE), ";"),
    (re.compile(r"\bfull\s+stop\b", re.IGNORECASE), "."),
    (re.compile(r"\bellipsis\b", re.IGNORECASE), "..."),
    (re.compile(r"\bperiod\b", re.IGNORECASE), "."),
    (re.compile(r"\bcomma\b", re.IGNORECASE), ","),
    (re.compile(r"\bcolon\b", re.IGNORECASE), ":"),
    (re.compile(r"\bdash\b", re.IGNORECASE), "\u2014"),
    (re.compile(r"\bhyphen\b", re.IGNORECASE), "-"),
]

# Spacing cleanup patterns — applied after all replacements.
_SPACE_BEFORE_CLOSING_RE = re.compile(r"\s+([.!?,;:)\]}\u201d])")
_SPACE_AFTER_OPENING_RE = re.compile(r"([\(\[\{\u201c])\s+")
_SPACE_AROUND_HYPHEN_RE = re.compile(r"\s*-\s*")
_MULTI_SPACE_RE = re.compile(r"  +")


def process_punctuation(text: str) -> str:
    """Strip Whisper auto-punctuation and replace spoken punctuation words.

    Processing order:
      1. Remove auto-inserted punctuation marks (. , ! ? ; :)
      2. Replace spoken punctuation words with their symbols
      3. Fix spacing around punctuation
    """
    logger.debug("process_punctuation Start: %r", text)

    # Step 1: strip auto-punctuation
    result = _AUTO_PUNCT_RE.sub("", text)

    # Step 2: replace spoken punctuation words with symbols
    for pattern, symbol in _PUNCTUATION_REPLACEMENTS:
        result = pattern.sub(symbol, result)

    # Step 3: fix spacing
    result = _SPACE_BEFORE_CLOSING_RE.sub(r"\1", result)
    result = _SPACE_AFTER_OPENING_RE.sub(r"\1", result)
    result = _SPACE_AROUND_HYPHEN_RE.sub("-", result)
    result = _MULTI_SPACE_RE.sub(" ", result)
    result = result.strip()

    logger.debug("process_punctuation End: %r", result)
    return result
