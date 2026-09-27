"""Split a streamed LLM response into speakable sentences (TTS starts on the first one)."""

from __future__ import annotations

import re

# Italian abbreviations whose trailing dot does not end a sentence.
_ABBREVIATIONS = frozenset(
    {
        "sig",
        "sigg",
        "sig.ra",
        "dott",
        "dott.ssa",
        "prof",
        "ing",
        "avv",
        "arch",
        "geom",
        "ecc",
        "etc",
        "es",
        "pag",
        "n",
        "nr",
        "art",
        "tel",
        "vs",
        "dr",
        "mr",
        "mrs",
        "st",
    }
)
_BOUNDARY = re.compile(r"[.!?…]+[\"'»)\]]*(?=\s)")


class SentenceChunker:
    """Accumulates text deltas and yields complete sentences as soon as they close."""

    def __init__(self, min_chars: int = 2) -> None:
        self._buffer = ""
        self._min_chars = min_chars

    def feed(self, delta: str) -> list[str]:
        self._buffer += delta
        sentences: list[str] = []
        start = 0
        for match in _BOUNDARY.finditer(self._buffer):
            end = match.end()
            candidate = self._buffer[start:end].strip()
            if self._is_false_boundary(self._buffer, match.start(), match.group()):
                continue
            if len(candidate) >= self._min_chars:
                sentences.append(candidate)
                start = end
        self._buffer = self._buffer[start:]
        return sentences

    def flush(self) -> list[str]:
        rest = self._buffer.strip()
        self._buffer = ""
        return [rest] if rest else []

    @staticmethod
    def _is_false_boundary(text: str, dot_pos: int, punct: str) -> bool:
        if not punct.startswith(".") or punct.startswith(".."):
            return False
        word = re.search(r"([\w.]+)$", text[:dot_pos])
        if word is None:
            return False
        token = word.group(1)
        # Decimals never match (boundary needs trailing whitespace); initials ("M. Rossi") do.
        return token.lower() in _ABBREVIATIONS or (len(token) == 1 and token.isupper())
