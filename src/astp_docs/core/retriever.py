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
from .text import tokenize as _tokenize


class Retriever:
    """Corpus-agnostic retrieval facade over a built ``DocIndex``."""

    def __init__(self, index: DocIndex, corpus_name: str = "", embedder=None):
        self.index = index
        self.corpus_name = corpus_name
        self._embedder = embedder   # None => default TF-IDF, built lazily
        self._store = None

    @classmethod
    def from_spec(cls, spec: CorpusSpec, embedder=None) -> "Retriever":
        documents = spec.load()
        chunks = chunk_corpus(documents)
        return cls(DocIndex(chunks), corpus_name=spec.name, embedder=embedder)

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

    # -- vector search ---------------------------------------------------
    @property
    def embedder_name(self) -> str:
        return self._embedder.name if self._embedder is not None else "tfidf-local"

    def _ensure_semantic(self) -> None:
        if self._store is not None:
            return
        from .embeddings import TfidfEmbedder
        from .store import InMemoryVectorStore

        texts = [c.text for c in self.index.chunks]
        if self._embedder is None:
            self._embedder = TfidfEmbedder().fit(texts)
        vectors = self._embedder.embed(texts)
        store = InMemoryVectorStore(dim=self._embedder.dim)
        store.add([str(i) for i in range(len(texts))], vectors, list(range(len(texts))))
        self._store = store

    def search(
        self,
        query: str,
        k: int = 5,
        kinds: tuple[AnchorKind, ...] | None = None,
        must_contain: tuple[str, ...] = (),
    ) -> list[Result]:
        """Vector search over the corpus (cosine). Default embedder is a local,
        offline TF-IDF model; inject a neural/API ``Embedder`` via ``from_spec``
        for true semantic ranking. ``kinds`` / ``must_contain`` post-filter the
        ranked hits (the store is over-queried so k results survive filtering)."""
        self._ensure_semantic()
        query_vec = self._embedder.embed([query])[0]
        fetch = k * 5 if (kinds or must_contain) else k
        hits = self._store.search(query_vec, k=fetch)
        results: list[Result] = []
        for _id, score, payload in hits:
            chunk = self.index.chunks[payload]
            if kinds and chunk.primary.kind not in kinds:
                continue
            if any(sub not in chunk.text.lower() for sub in must_contain):
                continue
            results.append(Result(chunk=chunk, score=score))
            if len(results) >= k:
                break
        return results

    def search_lexical(
        self,
        query: str,
        k: int = 5,
        kinds: tuple[AnchorKind, ...] | None = None,
        must_contain: tuple[str, ...] = (),
    ) -> list[Result]:
        """Deterministic term-overlap search — the stopgap until slice 2's
        embeddings. Scores query-term frequency in chunk text, with boosts for
        matches in the anchor label and an exact anchor-id hit, so
        ``search_lexical("WF-004")`` still surfaces that vector. ``must_contain``
        filters to chunks whose lowercased text contains every given substring
        (used by hash-preimage lookup)."""
        terms = _tokenize(query)
        if not terms:
            return []
        scored: list[tuple[float, Chunk]] = []
        for chunk in self.index.chunks:
            if kinds and chunk.primary.kind not in kinds:
                continue
            text = chunk.text.lower()
            if any(sub not in text for sub in must_contain):
                continue
            label = (chunk.primary.label or "").lower()
            anchor_ids = {a.id.lower() for a in chunk.anchors}
            score = 0.0
            for t in terms:
                score += text.count(t)
                if t in label:
                    score += 3.0
                if t in anchor_ids:
                    score += 10.0
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda sc: (-sc[0], sc[1].chunk_id))
        return [Result(chunk=c, score=s) for s, c in scored[:k]]

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
