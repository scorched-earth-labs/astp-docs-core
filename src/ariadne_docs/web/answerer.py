"""Answer generation for the web-chat head ("Clotho-lite").

Pluggable behind the ``Answerer`` interface — same shape as the Embedder /
VectorStore seams — so the endpoint runs keyless (extractive) for local/dev and
testing, and swaps to a Claude-backed generator in deployment without touching
the routes.

Both heads (this and the MCP server) retrieve from the SAME core and cite the
SAME chunks, so the website assistant can't drift from what coding agents are
told. This module only *generates*; retrieval is the shared core.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

from ..core.models import Result

# Default generation model. Per Anthropic guidance the default is Opus 4.8;
# override with ARIADNE_CHAT_MODEL (e.g. a cheaper tier) — that's a deployment
# cost decision, made explicitly, not silently downgraded here.
DEFAULT_CHAT_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
You are Clotho-lite, the documentation assistant for Project Ariadne — an open \
protocol for cognitive persistence and verifiable cognition in multi-agent systems.

Answer questions about the Ariadne protocol using ONLY the numbered context \
passages provided in the user message. Each passage carries a citation like \
[1] SPEC §5.2. Rules:
- Ground every claim in the passages. If the passages don't contain the answer, \
say so plainly — do not invent protocol behavior, field names, hash preimages, \
governance rules, or conformance vectors.
- Cite the passages you used inline with their bracket numbers, e.g. "…as required \
by G-2 [1]." Prefer exact anchors (governance rule ids, conformance vector ids, \
section numbers) when the passages give them.
- Be concise and precise. This is a specification; exactness matters more than prose.
- Stay on the Ariadne protocol. Decline unrelated requests briefly.\
"""


def build_context(results: list[Result]) -> str:
    """Render retrieved chunks as numbered, citation-tagged context."""
    blocks = []
    for i, r in enumerate(results, start=1):
        c = r.chunk
        blocks.append(f"[{i}] {c.citation()}\n{c.text}")
    return "\n\n".join(blocks)


def build_user_prompt(query: str, results: list[Result]) -> str:
    if not results:
        return (
            f"Question: {query}\n\n"
            "No documentation passages were retrieved. Tell the user you don't have "
            "anything in the docs on this and suggest they rephrase."
        )
    return f"Context passages:\n\n{build_context(results)}\n\n---\nQuestion: {query}"


def _citations(results: list[Result]) -> list[dict]:
    out = []
    for i, r in enumerate(results, start=1):
        c = r.chunk
        out.append({
            "n": i,
            "doc_id": c.doc_id,
            "anchor": str(c.primary),
            "citation": str(c.citation()),
            "heading_path": c.heading_path,
        })
    return out


class Answerer(ABC):
    name: str = "answerer"

    @abstractmethod
    def answer(self, query: str, results: list[Result]) -> dict:
        """Return {answer, citations, generator, grounded}."""


class ExtractiveAnswerer(Answerer):
    """Keyless fallback: no LLM, just return the top passages as the answer.

    Honest and useful for a docs *search* box, and it keeps /chat working (and
    testable) with no credentials. Not a real conversational assistant — the
    Claude generator is that.
    """

    name = "extractive"

    def answer(self, query: str, results: list[Result]) -> dict:
        if not results:
            return {"answer": "Nothing in the Ariadne docs matches that query.",
                    "citations": [], "generator": self.name, "grounded": False}
        top = results[0].chunk
        answer = (
            f"Most relevant passage — {top.citation()}:\n\n{top.text.strip()}"
        )
        return {"answer": answer, "citations": _citations(results),
                "generator": self.name, "grounded": True}


class ClaudeAnswerer(Answerer):
    """Doc-grounded RAG answers via Claude. The deployment default."""

    def __init__(self, model: str | None = None, client=None):
        self.model = model or os.environ.get("ARIADNE_CHAT_MODEL", DEFAULT_CHAT_MODEL)
        self.name = f"claude:{self.model}"
        self._client = client  # injected for tests; else built lazily

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic  # lazy: optional dep, resolves creds itself

            self._client = Anthropic()
        return self._client

    def answer(self, query: str, results: list[Result]) -> dict:
        resp = self._get_client().messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},        # low effort: scoped, latency-sensitive
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": build_user_prompt(query, results)}],
        )
        # Safety classifiers can decline (HTTP 200) — check before reading content.
        if getattr(resp, "stop_reason", None) == "refusal":
            return {"answer": "I can't help with that request.",
                    "citations": [], "generator": self.name, "grounded": False}
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return {"answer": text.strip(), "citations": _citations(results),
                "generator": self.name, "grounded": bool(results)}


def default_answerer() -> Answerer:
    """Pick a generator from the environment: extractive when forced or when the
    anthropic SDK isn't importable, else Claude."""
    if os.environ.get("ARIADNE_CHAT_MODE", "").lower() == "extractive":
        return ExtractiveAnswerer()
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return ExtractiveAnswerer()
    return ClaudeAnswerer()
