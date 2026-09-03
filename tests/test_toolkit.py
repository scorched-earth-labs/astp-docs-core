"""Shared tool-logic tests (astp_docs.toolkit) over a synthetic corpus.

The toolkit is the transport-agnostic layer both servers import; these run with
no external corpus and no transport dependency.
"""
import pytest

pytest.importorskip("numpy")  # search_spec / get_hash_preimage use vector search

from astp_docs import toolkit
from astp_docs.core import DocIndex, Document, Retriever, chunk_corpus

SPEC = Document(
    doc_id="SPEC",
    path="SPEC.md",
    text=(
        "# Spec\n\n## 6. Governance Rules\n\n### G-1: Write Guard\n\n"
        "No modifications to sealed nodes.\n\n"
        "## 21. Layer 3\n\n### 4. WorkflowDeclaration\n\n"
        "The content hash binds node_id, node_type, workflow_name in that order.\n"
    ),
)
CONF = Document(
    doc_id="CONFORMANCE",
    path="C.md",
    text="# Conf\n\n## 2. Vectors\n\n**WF-001** — content hash field order\n- **Class:** REQUIRED\n",
)


@pytest.fixture
def r():
    return Retriever(DocIndex(chunk_corpus([SPEC, CONF])), corpus_name="mini")


def test_get_governance_rule(r):
    out = toolkit.get_governance_rule(r, "g1")
    assert out["count"] == 1 and "Write Guard" in out["results"][0]["text"]


def test_get_conformance_vectors(r):
    out = toolkit.get_conformance_vectors(r, "WF-001")
    assert out["count"] == 1
    assert out["results"][0]["anchor"]["id"] == "WF-001"


def test_get_section(r):
    out = toolkit.get_section(r, "21")
    assert out["results"][0]["doc_id"] == "SPEC"


def test_search_spec_reports_method(r):
    out = toolkit.search_spec(r, "content hash order", k=3)
    assert out["search_method"] == "tfidf-local"
    assert out["count"] >= 1


def test_get_hash_preimage_filters_to_hash(r):
    out = toolkit.get_hash_preimage(r, "WorkflowDeclaration", k=3)
    assert out["count"] >= 1
    assert all("hash" in hit["text"].lower() for hit in out["results"])


def test_corpus_info(r):
    info = toolkit.corpus_info(r)
    assert info["docs"] == 2
    assert "G-1" in info["governance_rules"]


def test_anchored_search_puts_named_anchors_first(r):
    hits = toolkit.anchored_search(r, "what does g-1 require, and does WF-001 cover it?", k=4)
    ids = [h.chunk.primary.id for h in hits]
    assert ids[:2] == ["G-1", "WF-001"]
    assert len(ids) == len(set(ids)) <= 4


def test_anchored_search_section_and_fill(r):
    hits = toolkit.anchored_search(r, "explain section 21 and the content hash", k=3)
    assert hits[0].chunk.doc_id == "SPEC" and hits[0].chunk.primary.id == "21"
    assert len(hits) == 3


def test_anchored_search_without_anchors_is_plain_search(r):
    assert [h.chunk.chunk_id for h in toolkit.anchored_search(r, "content hash order", k=2)] == \
        [h.chunk.chunk_id for h in r.search("content hash order", k=2)]


def test_anchored_search_ignores_lookalikes(r):
    # "SHA3-256" / "UTF-8" must not be read as conformance vectors.
    hits = toolkit.anchored_search(r, "is SHA3-256 or UTF-8 used?", k=2)
    assert all(h.chunk.primary.kind.value != "conformance_vector" for h in hits)
