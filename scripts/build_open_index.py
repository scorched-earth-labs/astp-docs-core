#!/usr/bin/env python3
"""Build the open-corpus index against the real ariadne-protocol docs and
print stats + a few sample exact lookups. This is the slice-1 verification
harness: run it after any chunker change to confirm the engine still matches
the live spec.

    python scripts/build_open_index.py
    ARIADNE_PROTOCOL_DIR=/path/to/ariadne-protocol python scripts/build_open_index.py
"""
from __future__ import annotations

import sys
import textwrap

from ariadne_docs.core import Retriever
from ariadne_docs.corpora import build_open_corpus_spec


def _show(title: str, results):
    print(f"\n=== {title} ===")
    if not results:
        print("  (no results)")
        return
    for r in results[:3]:
        c = r.chunk
        print(f"  {c.citation()}   path: {' > '.join(c.heading_path)}")
        snippet = textwrap.shorten(c.text.replace("\n", " "), width=180)
        print(f"    {snippet}")


def main() -> int:
    spec = build_open_corpus_spec()
    retriever = Retriever.from_spec(spec)

    stats = retriever.stats()
    print("Open corpus index built.")
    print(f"  corpus:  {stats['corpus']}")
    print(f"  docs:    {stats['docs']}")
    print(f"  chunks:  {stats['chunks']}")
    print(f"  anchors: {stats['anchors_by_kind']}")
    print(f"  vector families: {stats['vector_families']}")

    gov = retriever.list_governance_rules()
    gov_nums = sorted(int(g["id"].split("-")[1]) for g in gov)
    print(f"\n  governance rules indexed: {len(gov)}  (G-1 .. G-{gov_nums[-1]})")
    missing = [f"G-{n}" for n in range(1, gov_nums[-1] + 1) if n not in set(gov_nums)]
    if missing:
        print(f"  !! GAPS in contiguous range: {', '.join(missing)}")
    else:
        print("  contiguous: no gaps")

    # Sample exact lookups — the deterministic surface the MCP tools expose.
    _show("get_governance_rule('G-2')", retriever.get_governance_rule("G-2"))
    _show("get_governance_rule('g16')", retriever.get_governance_rule("g16"))
    _show("get_conformance_vectors('WF-004')", retriever.get_conformance_vectors("WF-004"))
    _show("get_conformance_vectors('wf-1')", retriever.get_conformance_vectors("wf-1"))
    _show("get_section('5.2')", retriever.get_section("5.2"))
    _show("get_section('§6')", retriever.get_section("§6"))

    fams = retriever.list_conformance_families()
    print(f"\n  conformance families: {fams}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
