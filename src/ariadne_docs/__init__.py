"""ariadne-docs — the retrieval core library for Project Ariadne's docs servers.

A corpus-agnostic engine (chunker → index → retriever, with pluggable embedder /
vector store) plus the shared, transport-agnostic tool logic (`toolkit`). The
open and enterprise documentation servers are separate packages built on top of
this one; each binds the core to its own corpus and exposes it over a transport
(MCP, HTTP). Nothing here knows about a specific corpus or transport.
"""
__version__ = "0.2.0"
