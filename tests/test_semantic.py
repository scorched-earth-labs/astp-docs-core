"""Vector-search tests. Guarded on numpy; the real-corpus checks skip if the
sibling repo isn't resolvable."""
import pytest

pytest.importorskip("numpy")

from astp_docs.core import AnchorKind, Document, Retriever, DocIndex, chunk_corpus

CORPUS = [
    Document(
        doc_id="SPEC",
        path="SPEC.md",
        text=(
            "# Spec\n\n"
            "## 5. Hash Chain\n\n"
            "### 5.2 Position-Binding Leaf Hash\n\n"
            "The leaf hash preimage binds identity, type, sequence position, and "
            "content into a single SHA3-256 commitment.\n\n"
            "## 7. Witnesses\n\n"
            "### 7.1 Witness Threshold\n\n"
            "A sealed node requires a minimum number of counter signatures from "
            "distinct witnesses before it can transition to the sealed state.\n"
        ),
    ),
]


def _retriever():
    return Retriever(DocIndex(chunk_corpus(CORPUS)), corpus_name="mini")


def test_search_returns_ranked_scored_results():
    r = _retriever()
    hits = r.search("how is the leaf hash preimage computed", k=3)
    assert hits
    scores = [h.score for h in hits]
    assert all(s is not None for s in scores)
    assert scores == sorted(scores, reverse=True)          # descending
    assert all(-1.0001 <= s <= 1.0001 for s in scores)     # cosine range
    # the hash section should outrank the witness section for this query
    assert "hash" in hits[0].chunk.text.lower()


def test_default_embedder_is_offline_tfidf():
    r = _retriever()
    assert r.embedder_name == "tfidf-local"
    r.search("witness threshold signatures", k=1)  # triggers lazy build
    assert r.embedder_name == "tfidf-local"


def test_search_kind_and_contains_filters():
    r = _retriever()
    only_sections = r.search("hash", k=5, kinds=(AnchorKind.SECTION,))
    assert all(h.chunk.primary.kind is AnchorKind.SECTION for h in only_sections)
    must = r.search("state", k=5, must_contain=("witness",))
    assert all("witness" in h.chunk.text.lower() for h in must)


def test_injected_embedder_reports_its_name():
    import numpy as np
    from astp_docs.core.embeddings import Embedder

    class Dummy(Embedder):
        name = "dummy-test"

        @property
        def dim(self):
            return 4

        def embed(self, texts):
            # deterministic non-zero vectors so the store has something to rank
            m = np.ones((len(texts), 4), dtype=np.float64)
            return m / np.linalg.norm(m, axis=1, keepdims=True)

    r = Retriever(DocIndex(chunk_corpus(CORPUS)), embedder=Dummy())
    assert r.embedder_name == "dummy-test"
    assert r.search("anything", k=1)  # store builds via the injected embedder
