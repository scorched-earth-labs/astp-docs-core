"""Shared tokenization for lexical + TF-IDF retrieval.

Pure-stdlib. Keeping one tokenizer means lexical search, the TF-IDF embedder,
and any future analyzer all segment text the same way.
"""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-]*")

STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "is", "are", "in", "on", "for",
    "by", "as", "at", "be", "it", "that", "this", "with", "from", "how", "what",
    "does", "do", "which", "must",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]
