"""Self-contained chunker/index tests over a synthetic mini-spec.

These run with no external corpus — they encode the four governance-rule
formats and the conformance-vector format the real Ariadne docs use, so a
regression in the chunker fails here regardless of the sibling repo.
"""
from ariadne_docs.core import AnchorKind, Document, Retriever, DocIndex, chunk_corpus

MINI_SPEC = """# Mini Protocol Specification

## 1. Abstract

Intro prose.

## 6. Governance Rules

### G-1: Write Guard

No modifications to sealed nodes.

### G-7 through G-9: Signal Governance

- **G-7:** Causal signals require a TRIGGERED edge.
- **G-8:** Exchange entries require a prior initiation_hash.
- **G-9:** Consultation resolution requires an exchange entry.

## 19. Branch/Fork/Merge

### 19.3.1 ForkPointNode

- **G-19.** `fork_objective` non-empty.
- **G-20.** At least 2 alternatives per fork.

`resolve_fork()` writes `FORK_RESOLVED`. `resolution_rationale` is required (G-21).

**G-22.** `merge_summary` non-empty.

### 19.3.5 DepartureForkPointNode

**G-30 (Backdating integrity invariant).** Hashes must match.

## 21. Layer 3

> **Conformance G-36 (CIA Declaration).** Every workspace names the CIA.
"""

MINI_CONFORMANCE = """# Mini Conformance Vectors

## 2. WorkflowDeclaration Vectors

**WF-001** — WorkflowDeclaration content hash — field order
- **Class:** REQUIRED
- **Description:** canonical field order.

**WF-004** — Status transition legality
- **Class:** REQUIRED
- **Description:** legal transitions only.
"""


def _retriever():
    chunks = chunk_corpus(
        [
            Document(doc_id="SPEC", path="SPEC.md", text=MINI_SPEC),
            Document(doc_id="CONFORMANCE", path="C.md", text=MINI_CONFORMANCE),
        ]
    )
    return Retriever(DocIndex(chunks), corpus_name="mini")


def test_governance_all_formats_resolve():
    r = _retriever()
    got = {int(g["id"].split("-")[1]) for g in r.list_governance_rules()}
    # heading (1), range heading (7-9), bullets (19,20), prose backfill (21),
    # bold para (22), titled bold (30), blockquote+Conformance (36)
    for n in (1, 7, 8, 9, 19, 20, 21, 22, 30, 36):
        assert n in got, f"G-{n} not indexed (have {sorted(got)})"


def test_governance_lookup_content():
    r = _retriever()
    assert "Write Guard" in r.get_governance_rule("G-1")[0].chunk.text
    assert "merge_summary" in r.get_governance_rule("G-22")[0].chunk.text
    assert "CIA" in r.get_governance_rule("G-36")[0].chunk.text
    # prose-only G-21 backfills onto the chunk citing it
    assert "resolution_rationale" in r.get_governance_rule("G-21")[0].chunk.text


def test_governance_id_normalization():
    r = _retriever()
    for form in ("G-1", "g1", "G1", " g-1 "):
        assert r.get_governance_rule(form), f"{form!r} failed to normalize"


def test_conformance_vectors_exact_and_family():
    r = _retriever()
    exact = r.get_conformance_vectors("WF-004")
    assert len(exact) == 1
    assert exact[0].chunk.primary.kind is AnchorKind.CONFORMANCE_VECTOR
    assert "transition legality" in exact[0].chunk.text.lower()
    # family lookup returns both WF vectors
    fam = r.get_conformance_vectors("WF")
    assert {c.chunk.primary.id for c in fam} == {"WF-001", "WF-004"}
    # normalization: "wf-1" -> WF-001
    assert r.get_conformance_vectors("wf-1")[0].chunk.primary.id == "WF-001"


def test_section_lookup_and_breadcrumb():
    r = _retriever()
    res = r.get_section("19.3.1")
    assert res and res[0].chunk.doc_id == "SPEC"
    assert "ForkPointNode" in res[0].chunk.heading_path[-1]


def test_citations_have_line_numbers():
    r = _retriever()
    cit = r.get_governance_rule("G-30")[0].chunk.citation()
    assert cit.doc_id == "SPEC"
    assert cit.start_line <= cit.end_line
    assert str(cit).startswith("SPEC G-30")


def test_lexical_search_ranks_and_scores():
    r = _retriever()
    hits = r.search_lexical("fork objective alternatives", k=5)
    assert hits and hits[0].score is not None
    # the fork rules chunk should surface for this query
    joined = " ".join(h.chunk.text for h in hits).lower()
    assert "fork" in joined
    # an exact anchor id query still resolves via the id boost
    top = r.search_lexical("WF-004", k=1)
    assert top and top[0].chunk.primary.id == "WF-004"
