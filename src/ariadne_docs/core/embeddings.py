"""Pluggable embedders behind one interface.

The open server's DEFAULT is ``TfidfEmbedder`` — zero extra deps beyond numpy,
offline, deterministic, and a real ranked-retrieval improvement over raw
term-count lexical (IDF weighting + cosine over the full vector space). It is
NOT neural-semantic; when a true semantic model or an API is available, drop in
``OpenAIEmbedder`` (or any ``Embedder``) via ``Retriever.from_spec(embedder=…)``
without touching the rest of the stack.

numpy is imported here, not in the core exact-lookup path — so
``from ariadne_docs.core import Retriever`` stays pure-stdlib until you call
``search()``.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

import numpy as np

from .text import tokenize


class Embedder(ABC):
    """Maps texts to L2-normalized dense vectors so cosine == dot product."""

    name: str = "embedder"

    @property
    @abstractmethod
    def dim(self) -> int: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:  # shape (len(texts), dim)
        ...


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class TfidfEmbedder(Embedder):
    """Corpus-fitted TF-IDF with sublinear term frequency. Default open embedder.

    Must be ``fit()`` on the corpus before ``embed()``. ``Retriever`` does this
    automatically when no embedder is injected.
    """

    name = "tfidf-local"

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray | None = None

    @property
    def dim(self) -> int:
        return len(self._vocab)

    def fit(self, texts: list[str]) -> "TfidfEmbedder":
        df: dict[str, int] = {}
        for text in texts:
            for term in set(tokenize(text)):
                df[term] = df.get(term, 0) + 1
        self._vocab = {term: i for i, term in enumerate(sorted(df))}
        n = max(len(texts), 1)
        idf = np.zeros(len(self._vocab), dtype=np.float64)
        for term, i in self._vocab.items():
            idf[i] = math.log((1 + n) / (1 + df[term])) + 1.0
        self._idf = idf
        return self

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._idf is None:
            raise RuntimeError("TfidfEmbedder.fit() must be called before embed().")
        out = np.zeros((len(texts), self.dim), dtype=np.float64)
        for row, text in enumerate(texts):
            counts: dict[int, int] = {}
            for term in tokenize(text):
                idx = self._vocab.get(term)
                if idx is not None:
                    counts[idx] = counts.get(idx, 0) + 1
            for idx, tf in counts.items():
                out[row, idx] = (1.0 + math.log(tf)) * self._idf[idx]
        return _l2_normalize(out)


class OpenAIEmbedder(Embedder):
    """True semantic embeddings via the OpenAI API. Optional / keyed — NOT the
    open server's default (that stays offline + keyless). Suitable for the
    enterprise server or an open deployment that opts in.
    """

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        from openai import OpenAI  # imported lazily; optional dep

        self.model = model
        self.name = f"openai:{model}"
        self._client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self._dim = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}.get(model, 1536)

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> np.ndarray:
        resp = self._client.embeddings.create(model=self.model, input=texts)
        vecs = np.array([d.embedding for d in resp.data], dtype=np.float64)
        return _l2_normalize(vecs)
