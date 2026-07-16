# ariadne-docs

Documentation retrieval engine + the **open** documentation MCP server for
Project Ariadne. Most Ariadne implementations will be done *by* AI coding
agents (Claude Code / Codex / Copilot); this serves the protocol corpus in an
AI-ready, exactly-citable form so those agents implement the protocol from the
docs instead of guessing (and writing their own non-conforming adapters).

## The split this serves

Ariadne has an **open/proprietary boundary** (decided at the 2026-06-12 SEL
weekly). The documentation surface mirrors it as **two servers on one shared
engine**:

| | Corpus | Audience | Home |
|---|---|---|---|
| **Open server** | Public protocol docs — SPEC, IMPLEMENTATION/CONFORMANCE companions, GLOSSARY, CHANGELOG | Adopters' coding agents + a public web-chat head | this repo (publishable) |
| **Enterprise server** | Proprietary Ignis-OS corpus — context-via-traversal, intention-writing, `:SEL*` extensions | Internal SEL agents + licensed customers | `ignis-langgraph` (private) |

The boundary is enforced by **physical separation**, not a runtime filter: two
`CorpusSpec`s, two indexes. A shared engine can never leak a proprietary chunk
into an open answer because the open server is never handed the proprietary
corpus. (This server is distinct from `ignis-mcp-server`, which exposes the
*agent org*, not docs.)

## Architecture — one substrate, several transports

```
        CorpusSpec (open | enterprise)          <- the only thing that differs
                 │
   ┌─────────────┴───────────────┐
   │        ariadne_docs.core     │             <- shared, corpus-agnostic engine
   │  chunker → index → retriever │
   └─────────────┬───────────────┘
                 │  Retriever (exact lookup now; semantic search = slice 2)
   ┌─────────────┼───────────────┬──────────────────┐
   ▼             ▼               ▼                  ▼
 MCP (open)   web chat (open)   MCP (enterprise)   ...          <- thin adapters
```

### The chunker is structure-aware

The corpus is a *specification*, not prose. Its retrieval units are exact
objects, and the chunker splits on their real boundaries so lookups are
deterministic, not fuzzy:

- **numbered sections** — `## 6. Governance Rules`, `### 2.5.1 …`
- **governance rules** `G-1 … G-36` — written four ways in the source (heading,
  bold paragraph, bullet, blockquote), all normalized to one anchor space
- **conformance vectors** — `**WF-001** — …`, `CEL-003`, 20 families

## Status

- **Slice 1 — retrieval core (exact lookup): DONE.** `CorpusSpec` + loader,
  structure-aware chunker, exact-lookup index, `Retriever`. Verified against
  the live `ariadne-protocol` corpus: 13 docs, ~700 chunks, governance
  **contiguous G-1…G-36**, 124 conformance vectors across 20 families.
- **Slice 3 — open MCP transport: DONE.** FastMCP server
  (`ariadne_docs.server`) exposing `search_spec`, `get_governance_rule`,
  `get_conformance_vectors`, `get_section`, `get_hash_preimage`, `corpus_info`,
  following the `research-mcp-server` pattern + an Atlas manifest (all read).
  Tool logic is pure functions in `server/tools.py` (testable without `mcp`);
  the FastMCP layer is a thin wrapper. Verified end-to-end via `call_tool`.
  `search_spec` is **lexical** until slice 2 (`search_method` reports which).
- **Slice 2 — semantic search:** embeddings + vector store behind
  `Retriever.search()` (the seam is already declared; `search_lexical()` is the
  stopgap). Simple/local backend for the open bar; QDrant for enterprise.
- **Slice 4 — open web-chat head** (Clotho-lite) and a checked-in
  `llms.txt` / `AGENTS.md` pointer.

## Develop

```bash
# Core is pure-stdlib. Point at a checkout of the public protocol repo:
export ARIADNE_PROTOCOL_DIR=~/projects/ariadne-protocol

PYTHONPATH=src python3 scripts/build_open_index.py   # build + sample lookups
PYTHONPATH=src python3 -m pytest tests/ -q            # tests (integration ones
                                                     # skip if the repo is absent)

# Run the open MCP server (needs the `mcp` extra: pip install -e '.[mcp]'):
python -m ariadne_docs.server                        # stdio transport
```

The core is pure-stdlib; only the MCP transport needs `mcp`. `search_spec` and
`get_hash_preimage` are lexical until slice 2 adds embeddings.
