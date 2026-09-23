"""Core data model for the Ariadne docs retrieval engine.

These types are corpus-agnostic and transport-agnostic: the same ``Chunk`` /
``Anchor`` shapes back both the open and the enterprise servers, and both the
MCP and web-chat heads. Nothing here knows about a specific document set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AnchorKind(str, Enum):
    """The kinds of retrieval-worthy unit the Ariadne doc genre exposes.

    These are the anchors that support *exact* lookup — the answers you never
    want a fuzzy search to approximate (a governance rule, a conformance
    vector, a numbered section). Semantic search (slice 2) is layered on top;
    it never replaces these.
    """

    SECTION = "section"                    # numbered heading, e.g. "5.2"
    GOVERNANCE_RULE = "governance_rule"    # "G-1" .. "G-43" (SPEC 6.0.0)
    CONFORMANCE_VECTOR = "conformance_vector"  # "WF-001", "CEL-003", ...


@dataclass(frozen=True)
class Anchor:
    """A stable, human-quotable pointer into the corpus."""

    kind: AnchorKind
    id: str            # normalized: "5.2", "G-1", "WF-001"
    label: str = ""    # heading title / vector one-liner

    def __str__(self) -> str:
        prefix = "§" if self.kind is AnchorKind.SECTION else ""
        return f"{prefix}{self.id}"


@dataclass
class Document:
    """A single source document loaded into a corpus."""

    doc_id: str        # filename stem, e.g. "SPEC", "CONFORMANCE-LAYER3"
    path: str
    text: str
    title: str = ""


@dataclass
class Chunk:
    """A retrieval unit: a section, a governance rule, or a conformance vector.

    ``anchors`` holds every anchor that resolves to this chunk (a range heading
    like "G-7 through G-9" yields three governance anchors on one chunk).
    ``anchors[0]`` is the primary/canonical anchor.
    """

    chunk_id: str
    doc_id: str
    anchors: list[Anchor]
    heading_path: list[str]   # breadcrumb of ancestor heading titles
    text: str
    start_line: int           # 1-indexed, inclusive
    end_line: int             # 1-indexed, inclusive

    @property
    def primary(self) -> Anchor:
        return self.anchors[0]

    def citation(self) -> "Citation":
        return Citation(
            doc_id=self.doc_id,
            anchor=self.primary,
            start_line=self.start_line,
            end_line=self.end_line,
        )


@dataclass(frozen=True)
class Citation:
    """A precise, checkable reference both heads emit alongside every answer."""

    doc_id: str
    anchor: Anchor
    start_line: int
    end_line: int

    def __str__(self) -> str:
        return f"{self.doc_id} {self.anchor} (L{self.start_line}-{self.end_line})"


@dataclass
class Result:
    """What the retriever returns: a chunk plus its citation, transport-ready."""

    chunk: Chunk
    score: float | None = None   # None for exact lookup; set by semantic search

    def to_dict(self) -> dict:
        c = self.chunk
        return {
            "doc_id": c.doc_id,
            "anchor": {"kind": c.primary.kind.value, "id": c.primary.id, "label": c.primary.label},
            "anchors": [{"kind": a.kind.value, "id": a.id, "label": a.label} for a in c.anchors],
            "heading_path": c.heading_path,
            "citation": str(c.citation()),
            "lines": [c.start_line, c.end_line],
            "text": c.text,
            "score": self.score,
        }
