"""Pluggable vector stores behind one interface.

``InMemoryVectorStore`` (numpy) is the default and all the open server needs.
The enterprise server will add a ``QdrantVectorStore`` implementing the same
``VectorStore`` interface — deferred until there is a live Qdrant to verify
against (per "verify against the real integration surface"), rather than shipped
blind.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class VectorStore(ABC):
    @abstractmethod
    def add(self, ids: list[str], vectors: np.ndarray, payloads: list) -> None: ...

    @abstractmethod
    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float, object]]:
        """Return up to k ``(id, cosine_score, payload)`` ranked descending."""
        ...


class InMemoryVectorStore(VectorStore):
    """Dense cosine search over a numpy matrix. Vectors are assumed
    L2-normalized by the embedder, so cosine similarity is a plain dot product.
    """

    def __init__(self, dim: int):
        self.dim = dim
        self._matrix: np.ndarray | None = None
        self._ids: list[str] = []
        self._payloads: list = []

    def add(self, ids: list[str], vectors: np.ndarray, payloads: list) -> None:
        if vectors.shape[0] != len(ids) or len(ids) != len(payloads):
            raise ValueError("ids, vectors, and payloads must align in length.")
        self._matrix = vectors if self._matrix is None else np.vstack([self._matrix, vectors])
        self._ids.extend(ids)
        self._payloads.extend(payloads)

    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float, object]]:
        if self._matrix is None or self._matrix.shape[0] == 0:
            return []
        scores = self._matrix @ query
        k = min(k, scores.shape[0])
        # argpartition for top-k, then sort those descending (stable tiebreak on id order).
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top], kind="stable")]
        return [(self._ids[i], float(scores[i]), self._payloads[i]) for i in top]
