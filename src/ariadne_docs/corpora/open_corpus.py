"""The OPEN corpus spec: the public Project Ariadne protocol documents.

This is the *only* corpus the open server ever sees. It is drawn from the
public ``ariadne-protocol`` repo: the normative SPEC, its IMPLEMENTATION /
CONFORMANCE companions, the amendments still referenced for Layer-3 semantics,
plus GLOSSARY and CHANGELOG. Nothing proprietary. The enterprise corpus is a
separate spec in a separate (private) repo — never merged with this one.
"""
from __future__ import annotations

import os

from ..core.corpus import CorpusSpec, Visibility, docrefs_from_dir

# The public protocol repo. Configurable so the server does not hard-code a
# developer's checkout; at package/publish time the docs are vendored instead.
DEFAULT_PROTOCOL_DIR = os.path.expanduser("~/projects/ariadne-protocol")

# Normative + reference documents that make up the open corpus. Glob patterns
# keep new companion docs picked up automatically; historical/marketing docs
# are excluded so adopters' agents only see the *current* normative surface.
#
# AMENDMENT-*.md are deliberately excluded: the v3.2.1 integration pass folded
# them into the SPEC body (§20 cross-episode, §21 Layer 3) and retired them to
# historical-reference banners. They retain their *authoring* governance
# numbering (e.g. CIA = G-19, since renumbered to G-36), which would pollute
# exact lookup with superseded anchors. The SPEC body is authoritative.
OPEN_DOC_PATTERNS = [
    "SPEC.md",
    "IMPLEMENTATION-*.md",
    "CONFORMANCE*.md",
    "GLOSSARY.md",
    "CHANGELOG.md",
    "VERSIONING.md",
    "README.md",
]

OPEN_DOC_EXCLUDE = [
    "SPEC-v1.md",   # superseded by SPEC.md
    "VISION.md",    # narrative, not normative
]


def build_open_corpus_spec(protocol_dir: str | None = None) -> CorpusSpec:
    base = protocol_dir or os.environ.get("ARIADNE_PROTOCOL_DIR") or DEFAULT_PROTOCOL_DIR
    base = os.path.abspath(os.path.expanduser(base))
    docs = docrefs_from_dir(base, OPEN_DOC_PATTERNS, exclude=OPEN_DOC_EXCLUDE)
    if not docs:
        raise FileNotFoundError(
            f"No open protocol docs found under {base!r}. Set ARIADNE_PROTOCOL_DIR "
            f"to a checkout of the public ariadne-protocol repo."
        )
    return CorpusSpec(name="ariadne-open", visibility=Visibility.OPEN, docs=docs)
