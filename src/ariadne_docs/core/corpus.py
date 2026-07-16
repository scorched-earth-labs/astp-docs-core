"""Corpus specification and loading.

A ``CorpusSpec`` is the *only* thing that differs between the open and the
enterprise server: same engine, two specs, two physically isolated corpora.
The boundary is separation — a spec never mixes visibilities — not a runtime
filter over one shared index.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from enum import Enum

from .models import Document


class Visibility(str, Enum):
    OPEN = "open"            # public protocol docs — safe to publish
    ENTERPRISE = "enterprise"  # proprietary Ignis-OS corpus — license-gated


@dataclass
class DocRef:
    """One source document: an absolute path plus the id it indexes under."""

    doc_id: str
    path: str
    title: str = ""


@dataclass
class CorpusSpec:
    """Declarative description of a corpus. Corpus-agnostic engine consumes this."""

    name: str
    visibility: Visibility
    docs: list[DocRef] = field(default_factory=list)

    def load(self) -> list[Document]:
        loaded: list[Document] = []
        missing: list[str] = []
        for ref in self.docs:
            if not os.path.isfile(ref.path):
                missing.append(ref.path)
                continue
            with open(ref.path, "r", encoding="utf-8") as fh:
                text = fh.read()
            loaded.append(
                Document(doc_id=ref.doc_id, path=ref.path, text=text, title=ref.title)
            )
        if missing:
            raise FileNotFoundError(
                f"CorpusSpec '{self.name}' is missing {len(missing)} doc(s):\n  "
                + "\n  ".join(missing)
            )
        return loaded


def docrefs_from_dir(
    base_dir: str,
    patterns: list[str],
    exclude: list[str] | None = None,
) -> list[DocRef]:
    """Resolve DocRefs from a directory by glob pattern.

    ``doc_id`` is the filename stem (``SPEC.md`` -> ``SPEC``). Deterministic
    ordering so indexes and citations are stable across builds.
    """
    exclude_set = set()
    for pat in exclude or []:
        exclude_set.update(glob.glob(os.path.join(base_dir, pat)))

    seen: dict[str, DocRef] = {}
    for pat in patterns:
        for path in glob.glob(os.path.join(base_dir, pat)):
            if path in exclude_set or not os.path.isfile(path):
                continue
            stem = os.path.splitext(os.path.basename(path))[0]
            seen[stem] = DocRef(doc_id=stem, path=os.path.abspath(path))
    return [seen[k] for k in sorted(seen)]
