"""Tests for the MCP tool logic (pure functions, no `mcp` dependency).

Run against the real open corpus; skipped if it isn't resolvable.
"""
import pytest

from ariadne_docs.core import Retriever
from ariadne_docs.server import tools

try:
    from ariadne_docs.corpora import build_open_corpus_spec

    _spec = build_open_corpus_spec()
except FileNotFoundError:
    _spec = None

pytestmark = pytest.mark.skipif(
    _spec is None, reason="ariadne-protocol open docs not resolvable (set ARIADNE_PROTOCOL_DIR)"
)


@pytest.fixture(scope="module")
def r():
    return Retriever.from_spec(_spec)


def test_search_spec_returns_hits(r):
    out = tools.search_spec(r, "position-binding leaf hash preimage", k=5)
    assert out["search_method"] == "tfidf-local"   # default offline embedder
    assert out["count"] > 0
    assert all("citation" in hit for hit in out["results"])
    assert all(hit["score"] is not None for hit in out["results"])


def test_get_governance_rule_tool(r):
    out = tools.get_governance_rule(r, "G-2")
    assert out["count"] == 1
    assert "Reparenting" in out["results"][0]["text"]


def test_get_conformance_family_tool(r):
    out = tools.get_conformance_vectors(r, "WF")
    ids = {hit["anchor"]["id"] for hit in out["results"]}
    assert "WF-004" in ids and out["count"] >= 3


def test_get_section_prefers_spec(r):
    out = tools.get_section(r, "5.2")
    assert out["results"][0]["doc_id"] == "SPEC"


def test_get_hash_preimage_tool(r):
    out = tools.get_hash_preimage(r, "WorkflowDeclaration", k=5)
    assert out["count"] > 0
    # every returned passage actually discusses a hash
    assert all("hash" in hit["text"].lower() for hit in out["results"])


def test_corpus_info_tool(r):
    info = tools.corpus_info(r)
    assert len(info["governance_rules"]) == 36
    assert info["docs"] == 13
