"""The query API both transports (MCP, web chat) call.

Slice 1 exposes the exact-lookup surface. ``search()`` (semantic) is declared
here as the seam slice 2 fills, so transports can be wired against the final
shape now.
"""
from __future__ import annotations

from .corpus import CorpusSpec
from .chunker import chunk_corpus
from .index import DocIndex, vector_family
from .models import AnchorKind, Chunk, Result


class Retriever:
    """Corpus-agnostic retrieval facade over a built ``DocIndex``."""

    def __init__(self, index: DocIndex, corpus_name: str = ""):
        self.index = index
        self.corpus_name = corpus_name

    @classmethod
    def from_spec(cls, spec: CorpusSpec) -> "Retriever":
        documents = spec.load()
        chunks = chunk_corpus(documents)
        return cls(DocIndex(chunks), corpus_name=spec.name)

    # -- exact lookups (deterministic) -----------------------------------
    def get_governance_rule(self, rule_id: str) -> list[Result]:
        return _results(self.index.governance_rule(rule_id))

    def get_conformance_vectors(self, id_or_family: str) -> list[Result]:
        """Accepts a single vector id ("WF-004") or a family prefix ("WF")."""
        exact = self.index.conformance_vector(id_or_family)
        if exact:
            return _results(exact)
        fam = id_or_family.strip().upper()
        return _results(self.index.conformance_family(fam))

    def get_section(self, section_id: str, doc: str | None = None) -> list[Result]:
        """Look up a numbered section. Section numbers are per-document; pass
        ``doc`` (e.g. "SPEC") to disambiguate, else all matches are returned
        with the SPEC's copy ranked first."""
        chunks = self.index.section(section_id, doc=doc)
        chunks = sorted(chunks, key=lambda c: (c.doc_id != "SPEC", c.doc_id))
        return _results(chunks)

    # -- semantic search (slice 2 seam) ----------------------------------
    def search(self, query: str, k: int = 5) -> list[Result]:
        raise NotImplementedError(
            "Semantic search lands in slice 2 (embeddings + vector store). "
            "Slice 1 provides deterministic exact lookup only."
        )

    # -- introspection ---------------------------------------------------
    def list_governance_rules(self) -> list[dict]:
        anchors = self.index.anchors_of_kind(AnchorKind.GOVERNANCE_RULE)
        return sorted(
            ({"id": a.id, "label": a.label} for a in anchors),
            key=lambda d: int(d["id"].split("-")[1]),
        )

    def list_conformance_families(self) -> dict[str, int]:
        return self.index.families()

    def stats(self) -> dict:
        return {"corpus": self.corpus_name, **self.index.stats()}


def _results(chunks: list[Chunk]) -> list[Result]:
    return [Result(chunk=c) for c in chunks]
