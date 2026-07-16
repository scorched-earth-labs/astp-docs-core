"""Pure tool logic for the documentation MCP servers.

Every function takes a ``Retriever`` and returns a JSON-serializable dict, so
the tools are fully testable without the ``mcp`` package. The FastMCP layer
(``open_server``) is a thin wrapper that binds these to a corpus and decorates
them with ``@mcp.tool()``. The same functions back the enterprise server.
"""
from __future__ import annotations

from ..core import AnchorKind
from ..core.retriever import Retriever


def _pack(results, extra: dict | None = None) -> dict:
    out = {"count": len(results), "results": [r.to_dict() for r in results]}
    if extra:
        out.update(extra)
    return out


def search_spec(retriever: Retriever, query: str, k: int = 5) -> dict:
    """Search the protocol corpus for the passage(s) most relevant to a query.

    Vector search (cosine). The ``search_method`` field reports the active
    embedder — "tfidf-local" by default (offline), or a neural/API embedder if
    the deployment injected one.
    """
    results = retriever.search(query, k=k)
    return _pack(results, {"query": query, "search_method": retriever.embedder_name})


def get_governance_rule(retriever: Retriever, rule_id: str) -> dict:
    """Look up a governance rule (G-1 .. G-36) by id. Exact, deterministic."""
    results = retriever.get_governance_rule(rule_id)
    return _pack(results, {"rule_id": rule_id})


def get_conformance_vectors(retriever: Retriever, id_or_family: str) -> dict:
    """Look up a conformance vector by id (e.g. "WF-004") or a whole family by
    prefix (e.g. "WF"). Exact, deterministic."""
    results = retriever.get_conformance_vectors(id_or_family)
    return _pack(results, {"query": id_or_family})


def get_section(retriever: Retriever, section_id: str, doc: str | None = None) -> dict:
    """Fetch a numbered section (e.g. "5.2", "§21"). Section numbers are
    per-document; pass ``doc`` (e.g. "SPEC") to disambiguate, else the SPEC's
    copy is ranked first."""
    results = retriever.get_section(section_id, doc=doc)
    return _pack(results, {"section_id": section_id, "doc": doc})


def get_hash_preimage(retriever: Retriever, type_name: str, k: int = 5) -> dict:
    """Find the content-hash preimage definition for a node/record type (e.g.
    "WorkflowDeclaration", "EpisodeLink", "leaf hash"). Returns the passages
    that describe what fields the hash binds and in what order.

    Ranks hash-describing passages by relevance to the type name; for the
    canonical field-order guarantee also consult the matching conformance vector
    via get_conformance_vectors.
    """
    # Restrict to passages that actually describe a hash, then rank by the type
    # name. Sections carry the preimage prose; vectors carry the field order.
    results = retriever.search(
        type_name,
        k=k,
        kinds=(AnchorKind.SECTION, AnchorKind.CONFORMANCE_VECTOR),
        must_contain=("hash",),
    )
    return _pack(results, {"type_name": type_name, "search_method": retriever.embedder_name})


def corpus_info(retriever: Retriever) -> dict:
    """Report what this server is serving: corpus name, doc count, and the
    exact-lookup surface (governance rules, conformance families)."""
    return {
        **retriever.stats(),
        "governance_rules": [g["id"] for g in retriever.list_governance_rules()],
        "conformance_families": retriever.list_conformance_families(),
    }
