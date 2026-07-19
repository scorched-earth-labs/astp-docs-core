# astp-docs

The **retrieval core library** behind Project Ariadne's documentation servers.
Corpus-agnostic and transport-agnostic: it turns the Ariadne doc corpus into
exactly-citable retrieval, and the servers are thin packages on top.

- **Open server** (public): [`astp-docs-server`](../astp-docs-server)
  — MCP transport for coding agents + a web-chat head.
- **Enterprise server** (private): a separate license-gated server over the
  proprietary corpus.

Both depend on this library; neither logic nor corpus content crosses between
them. The open/proprietary boundary is enforced by *separate corpora*, not a
runtime filter.

## What's in here

```
astp_docs/
  toolkit.py            # shared tool logic — search_spec / get_governance_rule /
                        #   get_conformance_vectors / get_section / get_hash_preimage /
                        #   corpus_info; pure functions over a Retriever, no transport dep
  core/
    corpus.py           # CorpusSpec + loader (the only thing that differs per server)
    chunker.py          # structure-aware chunker for the Ariadne spec genre
    index.py            # exact-lookup index (sections, governance rules, conformance vectors)
    retriever.py        # query API: exact lookup + vector search
    embeddings.py       # pluggable Embedder (offline TF-IDF default; OpenAI optional)
    store.py            # pluggable VectorStore (in-memory default)
    models.py, text.py
```

### The chunker is structure-aware

The corpus is a *specification*, not prose. Its retrieval units are exact
objects, and the chunker splits on their real boundaries so lookups are
deterministic:

- **numbered sections** — `## 6. Governance Rules`, `### 2.5.1 …`
- **governance rules** `G-1 … G-36` — written four ways (heading, bold paragraph,
  bullet, blockquote), all normalized to one anchor space
- **conformance vectors** — `**WF-001** — …`, `CEL-003`, …

Vector search (`Retriever.search`) is a pluggable `Embedder` + `VectorStore`;
the default is an offline, keyless TF-IDF model over a numpy in-memory store, so
the deterministic exact-lookup path never depends on an embedding backend.

## Develop

```bash
pip install -e '.[embeddings,dev]'
python -m pytest tests/ -q     # self-contained (synthetic corpora; no external deps)
```

Live-corpus checks (against a real `ariadne-protocol` checkout) live in the
server repos, since the corpus spec is a server concern.
