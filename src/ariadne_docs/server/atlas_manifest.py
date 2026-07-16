"""Atlas service manifest for the Ariadne Open Docs MCP Server.

Registers the server's read-only capabilities with Atlas so agents can discover
it. All tools are ``read`` (a docs server writes nothing). No API keys.

    from ariadne_docs.server.atlas_manifest import get_ariadne_docs_open_manifest
    await atlas.register_service(get_ariadne_docs_open_manifest())
"""
from __future__ import annotations

from typing import Any


def _read_cap(cap_id: str, tool_name: str, name: str, desc: str, schema: dict) -> dict:
    return {
        "id": cap_id,
        "name": name,
        "tool_name": tool_name,
        "capability_type": "read",
        "description": desc,
        "schema": schema,
        "required_permissions": ["ariadne.docs.read"],
    }


def get_ariadne_docs_open_manifest() -> dict[str, Any]:
    return {
        "service_id": "ariadne-docs-open",
        "name": "Ariadne Open Docs MCP Server",
        "version": "0.1.0",
        "description": (
            "Serves the OPEN Project Ariadne protocol corpus (SPEC, "
            "IMPLEMENTATION/CONFORMANCE companions, GLOSSARY, CHANGELOG) with "
            "exact lookup of governance rules, conformance vectors, and sections "
            "plus lexical search. Read-only; no proprietary content."
        ),
        "mcp_endpoint": "stdio://ariadne-docs-open",
        "health_endpoint": None,
        "docs_url": "https://github.com/scorched-earth-labs/ariadne-docs",
        "contact": {"team": "Ariadne Protocol", "email": "protocol@scorchedearthlabs.com"},
        "metadata": {
            "category": "documentation",
            "corpus_visibility": "open",
            "requires_api_keys": [],
            "cost_model": "free",
        },
        "capabilities": [
            _read_cap(
                "ariadne.docs.search_spec", "search_spec", "Search Spec",
                "Search the protocol corpus for relevant passages (lexical; semantic in a later release).",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to find"},
                        "k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                    },
                    "required": ["query"],
                },
            ),
            _read_cap(
                "ariadne.docs.get_governance_rule", "get_governance_rule", "Get Governance Rule",
                "Fetch a governance rule G-1..G-36 verbatim with citation.",
                {
                    "type": "object",
                    "properties": {"rule_id": {"type": "string", "description": "e.g. G-2"}},
                    "required": ["rule_id"],
                },
            ),
            _read_cap(
                "ariadne.docs.get_conformance_vectors", "get_conformance_vectors", "Get Conformance Vectors",
                "Fetch a conformance vector by id (WF-004) or a family by prefix (WF).",
                {
                    "type": "object",
                    "properties": {"id_or_family": {"type": "string", "description": "e.g. WF-004 or WF"}},
                    "required": ["id_or_family"],
                },
            ),
            _read_cap(
                "ariadne.docs.get_section", "get_section", "Get Section",
                "Fetch a numbered spec section verbatim.",
                {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string", "description": "e.g. 5.2"},
                        "doc": {"type": "string", "description": "Optional doc id, e.g. SPEC"},
                    },
                    "required": ["section_id"],
                },
            ),
            _read_cap(
                "ariadne.docs.get_hash_preimage", "get_hash_preimage", "Get Hash Preimage",
                "Find how a type's content hash is built (fields + order).",
                {
                    "type": "object",
                    "properties": {
                        "type_name": {"type": "string", "description": "e.g. WorkflowDeclaration"},
                        "k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                    },
                    "required": ["type_name"],
                },
            ),
            _read_cap(
                "ariadne.docs.corpus_info", "corpus_info", "Corpus Info",
                "Report served doc count, governance rules, and conformance families.",
                {"type": "object", "properties": {}},
            ),
        ],
    }
