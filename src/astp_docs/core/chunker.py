"""Structure-aware chunker for the Ariadne documentation genre.

The Ariadne corpus is not prose-with-headings; it is a *specification*. Its
retrieval units are exact objects:

  - numbered sections   ``## 6. Governance Rules`` / ``### 2.5.1 The ...``
  - governance rules     ``### G-1: Write Guard`` (and ranges ``### G-7 through G-9:``)
  - conformance vectors  ``**WF-001** — WorkflowDeclaration content hash``

This chunker splits on those real boundaries and records each anchor as chunk
metadata, so downstream ``get_governance_rule("G-2")`` /
``get_conformance_vectors("WF")`` are exact lookups, not fuzzy search over prose.
"""
from __future__ import annotations

import re

from .models import Anchor, AnchorKind, Chunk, Document

# A markdown ATX heading: 1-6 '#', text, optional trailing '#'s.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")

# A governance-rule heading: "G-1: Write Guard" or "G-7 through G-9: Signal ...".
_GOV_HEADING_RE = re.compile(
    r"^G-(\d+)(?:\s+through\s+G-(\d+))?\s*:\s*(.*)$", re.IGNORECASE
)

# A numbered-section heading: leading dotted number, e.g. "2.5.1 The ...".
_SECTION_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.*)$")

# A conformance-vector marker at the start of a body line: "**WF-001** — desc".
_VECTOR_RE = re.compile(
    r"^\*\*([A-Z]{2,5}-\d{3})\*\*\s*(?:[—–-]\s*)?(.*)$"
)

# An inline governance-rule definition. G-19 onward (G-43 as of SPEC 6.0.0) are written four ways, none
# of them headings: bold paragraph ("**G-22.** ..."), titled bold
# ("**G-30 (Backdating ...).**"), bullet ("- **G-19.** ..."), and a blockquote
# with a "Conformance" prefix ("> **Conformance G-36 (CIA Declaration).** ...").
_GOV_INLINE_RE = re.compile(
    r"^\s*(?:[>\-*]\s+)*"          # optional blockquote / list markers
    r"\*\*(?:Conformance\s+)?"      # bold open, optional "Conformance "
    r"G-(\d+)"                      # rule number
    r"(?:\s*\(([^)]*)\))?"          # optional (Title)
    r"\s*[.:]?\s*\*\*"              # optional . / : then bold close
    r"\s*(.*)$"
)


def _match_definition_marker(line: str) -> Anchor | None:
    """A body line that *defines* a conformance vector or a governance rule."""
    v = _VECTOR_RE.match(line)
    if v:
        return Anchor(AnchorKind.CONFORMANCE_VECTOR, v.group(1), v.group(2).strip())
    g = _GOV_INLINE_RE.match(line)
    if g:
        label = (g.group(2) or g.group(3) or "").strip()
        return Anchor(AnchorKind.GOVERNANCE_RULE, f"G-{int(g.group(1))}", label)
    return None


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "section"


def _heading_anchors(title: str) -> tuple[list[Anchor], str | None]:
    """Anchors implied by a heading, plus a section-number if one is present.

    A governance heading yields one anchor per rule in its range (so "G-7
    through G-9" resolves G-7, G-8 and G-9 all to the same chunk).
    """
    gov = _GOV_HEADING_RE.match(title)
    if gov:
        start, end, label = int(gov.group(1)), gov.group(2), gov.group(3).strip()
        end_n = int(end) if end else start
        anchors = [
            Anchor(AnchorKind.GOVERNANCE_RULE, f"G-{n}", label)
            for n in range(start, end_n + 1)
        ]
        return anchors, None

    sec = _SECTION_NUM_RE.match(title)
    if sec:
        num, label = sec.group(1), sec.group(2).strip()
        return [Anchor(AnchorKind.SECTION, num, label)], num

    # Unnumbered heading (e.g. "Abstract", "Errata") — anchor by slug so it is
    # still addressable, but it carries no section number.
    return [Anchor(AnchorKind.SECTION, _slug(title), title.strip())], None


def _split_definitions(body_lines: list[str], base_line: int):
    """Split a section body on definition markers (vectors + inline gov rules).

    Returns ``(preamble_lines, def_blocks)`` where each block is
    ``(anchor, block_lines, start_line, end_line)`` with 1-indexed absolute
    line numbers.
    """
    markers: list[tuple[int, Anchor]] = []
    for i, ln in enumerate(body_lines):
        anchor = _match_definition_marker(ln)
        if anchor:
            markers.append((i, anchor))
    if not markers:
        return body_lines, []

    preamble = body_lines[: markers[0][0]]
    blocks = []
    for k, (start_i, anchor) in enumerate(markers):
        end_i = markers[k + 1][0] if k + 1 < len(markers) else len(body_lines)
        block_lines = body_lines[start_i:end_i]
        blocks.append(
            (anchor, block_lines, base_line + start_i, base_line + end_i - 1)
        )
    return preamble, blocks


def chunk_document(doc: Document) -> list[Chunk]:
    """Chunk one document into section / governance / conformance-vector units."""
    lines = doc.text.split("\n")
    chunks: list[Chunk] = []

    # Locate every heading with its level and 0-indexed line.
    headings: list[tuple[int, int, str]] = []  # (line_idx, level, title)
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2)))

    if not headings:
        # Degenerate: a doc with no headings becomes one slug-anchored chunk.
        anchor = Anchor(AnchorKind.SECTION, _slug(doc.title or doc.doc_id), doc.title)
        return [
            Chunk(
                chunk_id=f"{doc.doc_id}::{anchor.id}",
                doc_id=doc.doc_id,
                anchors=[anchor],
                heading_path=[],
                text=doc.text.strip(),
                start_line=1,
                end_line=len(lines),
            )
        ]

    heading_stack: list[tuple[int, str]] = []  # (level, title) breadcrumb

    for h_idx, (line_idx, level, title) in enumerate(headings):
        # Body spans from just after this heading to just before the next.
        next_line = headings[h_idx + 1][0] if h_idx + 1 < len(headings) else len(lines)
        body_lines = lines[line_idx + 1 : next_line]

        # Maintain breadcrumb stack.
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        parent_path = [t for _, t in heading_stack]
        heading_stack.append((level, title))

        anchors, _section_num = _heading_anchors(title)
        heading_line_1 = line_idx + 1  # 1-indexed

        preamble, def_blocks = _split_definitions(body_lines, base_line=line_idx + 2)

        # The section/rule chunk: heading + preamble (everything before the
        # first inline definition, if any).
        section_text = "\n".join([lines[line_idx], *preamble]).strip()
        section_end = (def_blocks[0][2] - 1) if def_blocks else next_line
        chunks.append(
            Chunk(
                chunk_id=f"{doc.doc_id}::{anchors[0].id}",
                doc_id=doc.doc_id,
                anchors=anchors,
                heading_path=parent_path + [title],
                text=section_text,
                start_line=heading_line_1,
                end_line=section_end,
            )
        )

        # One chunk per inline definition (conformance vector or governance
        # rule) found in the body.
        for anchor, block_lines, start_line, end_line in def_blocks:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}::{anchor.id}",
                    doc_id=doc.doc_id,
                    anchors=[anchor],
                    heading_path=parent_path + [title, str(anchor)],
                    text="\n".join(block_lines).strip(),
                    start_line=start_line,
                    end_line=end_line,
                )
            )

    return chunks


def chunk_corpus(documents: list[Document]) -> list[Chunk]:
    out: list[Chunk] = []
    for doc in documents:
        out.extend(chunk_document(doc))
    backfill_prose_governance(out)
    return out


def backfill_prose_governance(chunks: list[Chunk]) -> list[str]:
    """Attach governance anchors for rules defined only in prose (e.g. G-21:
    "``resolution_rationale`` is required (G-21)."), so exact lookup stays
    contiguous. Narrow by design: fires only for ids missing after formal
    extraction, and only binds to a chunk that parenthetically cites the id
    — the reliable "defining citation" pattern in this corpus. Backfilled
    anchors are labelled so consumers can tell them from formally-marked rules.

    Returns the list of ids that were backfilled.
    """
    present = {
        int(a.id.split("-")[1])
        for c in chunks
        for a in c.anchors
        if a.kind is AnchorKind.GOVERNANCE_RULE
    }
    if not present:
        return []

    backfilled: list[str] = []
    for n in range(1, max(present) + 1):
        if n in present:
            continue
        pat = re.compile(rf"\(G-{n}\)")
        # Prefer a citation in SPEC; fall back to any doc.
        candidates = sorted(chunks, key=lambda c: (c.doc_id != "SPEC", c.doc_id))
        for chunk in candidates:
            if pat.search(chunk.text):
                chunk.anchors.append(
                    Anchor(
                        AnchorKind.GOVERNANCE_RULE,
                        f"G-{n}",
                        "(prose-embedded rule — see cited section)",
                    )
                )
                backfilled.append(f"G-{n}")
                break
    return backfilled
