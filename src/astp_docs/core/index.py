"""Exact-lookup index over chunked corpus.

Slice 1 builds only the deterministic half of the "dual index": exact maps
from anchor -> chunk(s). The embedding half (semantic ``search``) lands in
slice 2 and reuses these same chunks — the two indexes never diverge because
they are built from one chunking pass.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .models import Anchor, AnchorKind, Chunk


def normalize_governance_id(raw: str) -> str | None:
    m = re.search(r"(\d+)", raw)
    return f"G-{int(m.group(1))}" if m else None


def normalize_vector_id(raw: str) -> str | None:
    m = re.match(r"\s*([A-Za-z]{2,5})\s*-?\s*(\d{1,3})\s*$", raw)
    if not m:
        return None
    return f"{m.group(1).upper()}-{int(m.group(2)):03d}"


def normalize_section_id(raw: str) -> str:
    return raw.strip().lstrip("§").strip()


def vector_family(vector_id: str) -> str | None:
    m = re.match(r"([A-Z]{2,5})-\d{3}$", vector_id)
    return m.group(1) if m else None


class DocIndex:
    """Anchor -> chunk lookup built from a chunked corpus."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._by_anchor: dict[tuple[AnchorKind, str], list[Chunk]] = defaultdict(list)
        self._families: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            for anchor in chunk.anchors:
                self._by_anchor[(anchor.kind, anchor.id)].append(chunk)
                if anchor.kind is AnchorKind.CONFORMANCE_VECTOR:
                    fam = vector_family(anchor.id)
                    if fam:
                        self._families[fam].append(chunk)

    # -- exact lookups ---------------------------------------------------
    # The same anchor can appear in several documents — a governance rule is
    # stated in SPEC.md and quoted in CHANGELOG.md, a vector id in a conformance
    # document and in a guide that cites it. An exact lookup returns the
    # normative statement first: SPEC, then the CONFORMANCE documents, then the
    # IMPLEMENTATION guides, then everything else, each group in corpus order.
    _DOC_RANK = (("SPEC",), ("CONFORMANCE",), ("IMPLEMENTATION",))

    @classmethod
    def _doc_rank(cls, doc_id: str) -> int:
        for i, prefixes in enumerate(cls._DOC_RANK):
            if doc_id.upper().startswith(prefixes):
                return i
        return len(cls._DOC_RANK)

    def by_anchor(self, kind: AnchorKind, anchor_id: str) -> list[Chunk]:
        chunks = self._by_anchor.get((kind, anchor_id), [])
        return sorted(chunks, key=lambda c: self._doc_rank(c.doc_id))   # stable: corpus order within a rank

    def governance_rule(self, raw_id: str) -> list[Chunk]:
        norm = normalize_governance_id(raw_id)
        return self.by_anchor(AnchorKind.GOVERNANCE_RULE, norm) if norm else []

    def conformance_vector(self, raw_id: str) -> list[Chunk]:
        norm = normalize_vector_id(raw_id)
        return self.by_anchor(AnchorKind.CONFORMANCE_VECTOR, norm) if norm else []

    def conformance_family(self, family: str) -> list[Chunk]:
        return list(self._families.get(family.upper(), []))

    def section(self, raw_id: str, doc: str | None = None) -> list[Chunk]:
        chunks = self.by_anchor(AnchorKind.SECTION, normalize_section_id(raw_id))
        if doc:
            chunks = [c for c in chunks if c.doc_id == doc]
        return chunks

    # -- introspection ---------------------------------------------------
    def anchors_of_kind(self, kind: AnchorKind) -> list[Anchor]:
        seen: dict[str, Anchor] = {}
        for (k, aid), chunks in self._by_anchor.items():
            if k is kind and aid not in seen:
                seen[aid] = chunks[0].primary if chunks[0].primary.id == aid else Anchor(k, aid)
                # prefer the anchor object that carries the label
                for a in chunks[0].anchors:
                    if a.id == aid:
                        seen[aid] = a
                        break
        return list(seen.values())

    def families(self) -> dict[str, int]:
        return {fam: len(chunks) for fam, chunks in sorted(self._families.items())}

    def stats(self) -> dict:
        from collections import Counter
        kind_counts: Counter = Counter()
        for (kind, _), chunks in self._by_anchor.items():
            kind_counts[kind.value] += 1
        return {
            "chunks": len(self.chunks),
            "docs": len({c.doc_id for c in self.chunks}),
            "anchors_by_kind": dict(kind_counts),
            "vector_families": self.families(),
        }
