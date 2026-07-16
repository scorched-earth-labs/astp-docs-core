# AGENTS.md — implementing Project Ariadne

If you are an AI coding agent tasked with implementing (or conforming to) the
Ariadne protocol, read this first.

## Ground rules

1. **The SPEC is authoritative. Do not infer normative behavior.** Hash
   preimages, field sets, field order, governance rules, and conformance
   vectors are exact. Guessing them yields a different content hash and a
   non-conforming implementation — the single most common failure mode.
2. **Look it up, don't approximate.** Use the Ariadne Docs MCP server for exact
   answers rather than semantic recall:
   - `get_governance_rule("G-2")` — a governance rule verbatim (G-1..G-36)
   - `get_conformance_vectors("WF-004")` or `("WF")` — a vector or a whole family
   - `get_section("5.2")` — a numbered spec section
   - `get_hash_preimage("WorkflowDeclaration")` — which fields the hash binds, in order
   - `search_spec("…")` — semantic search when you don't know the anchor
3. **Verify against the conformance vectors.** For any surface you implement,
   pull its vectors (e.g. `CEL-*`, `WF-*`, `DF-*`) and make them pass.

## What Ariadne is (and isn't)

- Ariadne records **that** an agent reasoned, the resulting state, and a
  verifiable audit chain. It does **not** prescribe *how* the agent reasons —
  bring your own architecture (ReAct, BDI, CoT, …).
- The reference implementation uses a graph store (Neo4j/FalkorDB) + embeddings,
  but storage is an adapter concern. Conform to the protocol, not the adapter.

## Where to start

Read SPEC §2 (terminology + protocol/implementation boundary), §3 (three-layer
model), §5 (hash chain), §6 (governance rules). Then the surface you need:
§19 branch/fork/merge, §20 cross-episode linking, §21 Layer-3 DAG. Each has an
IMPLEMENTATION-*.md and CONFORMANCE-*.md companion.
