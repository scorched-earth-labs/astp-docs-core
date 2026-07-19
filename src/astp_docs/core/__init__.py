"""Corpus-agnostic retrieval engine for the Ariadne documentation servers."""
from .models import Anchor, AnchorKind, Chunk, Citation, Document, Result
from .corpus import CorpusSpec, DocRef, Visibility, docrefs_from_dir
from .chunker import chunk_corpus, chunk_document
from .index import DocIndex
from .retriever import Retriever

__all__ = [
    "Anchor",
    "AnchorKind",
    "Chunk",
    "Citation",
    "Document",
    "Result",
    "CorpusSpec",
    "DocRef",
    "Visibility",
    "docrefs_from_dir",
    "chunk_corpus",
    "chunk_document",
    "DocIndex",
    "Retriever",
]
