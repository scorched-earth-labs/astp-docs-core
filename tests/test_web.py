"""Web-chat head tests.

Prompt assembly + the extractive answerer + the ClaudeAnswerer request shape
run with no network. The FastAPI route tests use the extractive answerer (no
key) and skip if fastapi/httpx or the corpus is unavailable.
"""
import pytest

from ariadne_docs.core import Document, DocIndex, Retriever, chunk_corpus
from ariadne_docs.web.answerer import (
    ClaudeAnswerer,
    ExtractiveAnswerer,
    build_context,
    build_user_prompt,
)

MINI = Document(
    doc_id="SPEC",
    path="SPEC.md",
    text="# Spec\n\n## 5. Hash Chain\n\n### 5.2 Leaf Hash\n\n"
         "The leaf hash binds identity, type, and position into a SHA3-256 commitment.\n",
)


def _results():
    r = Retriever(DocIndex(chunk_corpus([MINI])))
    return r.search("leaf hash commitment", k=3)


def test_build_context_numbers_and_cites():
    ctx = build_context(_results())
    assert "[1]" in ctx and "SPEC §5.2" in ctx
    assert "SHA3-256" in ctx


def test_user_prompt_handles_empty_results():
    p = build_user_prompt("anything", [])
    assert "No documentation passages" in p


def test_extractive_answerer_grounds_and_cites():
    out = ExtractiveAnswerer().answer("leaf hash", _results())
    assert out["generator"] == "extractive"
    assert out["grounded"] is True
    assert out["citations"][0]["citation"].startswith("SPEC §5.2")
    assert "SHA3-256" in out["answer"]


def test_extractive_empty_is_ungrounded():
    out = ExtractiveAnswerer().answer("unrelated", [])
    assert out["grounded"] is False and out["citations"] == []


def test_claude_answerer_builds_correct_request():
    """Stub the client; assert the request shape follows the API guidance
    (Opus 4.8 default, adaptive thinking, no sampling params)."""
    captured = {}

    class _Block:
        type = "text"
        text = "Grounded answer [1]."

    class _Resp:
        stop_reason = "end_turn"
        content = [_Block()]

    class _Messages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Resp()

    class _Client:
        messages = _Messages()

    ans = ClaudeAnswerer(client=_Client())
    out = ans.answer("How is the leaf hash built?", _results())

    assert out["answer"] == "Grounded answer [1]."
    assert out["generator"] == "claude:claude-opus-4-8"
    assert captured["model"] == "claude-opus-4-8"
    assert captured["thinking"] == {"type": "adaptive"}
    assert "temperature" not in captured and "top_p" not in captured
    assert captured["system"].startswith("You are Clotho-lite")
    assert captured["messages"][0]["role"] == "user"


def test_claude_answerer_handles_refusal():
    class _Resp:
        stop_reason = "refusal"
        content = []

    class _Client:
        class messages:
            @staticmethod
            def create(**kwargs):
                return _Resp()

    out = ClaudeAnswerer(client=_Client()).answer("x", _results())
    assert out["grounded"] is False and out["citations"] == []


# -- route tests -----------------------------------------------------------
fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

try:
    from ariadne_docs.corpora import build_open_corpus_spec

    _spec = build_open_corpus_spec()
except FileNotFoundError:
    _spec = None


@pytest.fixture(scope="module")
def client():
    from ariadne_docs.web.app import create_app

    retriever = Retriever.from_spec(_spec) if _spec else Retriever(DocIndex(chunk_corpus([MINI])))
    app = create_app(retriever=retriever, answerer=ExtractiveAnswerer())
    return TestClient(app)


def test_healthz(client):
    j = client.get("/healthz").json()
    assert j["status"] == "ok"
    assert j["generator"] == "extractive"
    assert j["embedder"] == "tfidf-local"


def test_search_route(client):
    j = client.get("/search", params={"q": "leaf hash", "k": 3}).json()
    assert j["count"] >= 1
    assert all("citation" in r for r in j["results"])


def test_chat_route(client):
    j = client.post("/chat", json={"query": "leaf hash", "k": 3}).json()
    assert j["generator"] == "extractive"
    assert j["answer"]
    assert j["citations"]


def test_demo_page_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "Ariadne Docs Assistant" in r.text
