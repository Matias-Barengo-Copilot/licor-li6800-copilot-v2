"""
RAG layer: document embedding and retrieval via ChromaDB.

EmbeddingService  — wraps Gemini gemini-embedding-2-preview
    Supports text and video (MP4 bytes) in a single unified vector space.

RAGService — ChromaDB retrieval with relevance filtering.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import chromadb
from google import genai
from google.genai import types
from openai import OpenAI

RELEVANCE_THRESHOLD = 0.7
COLLECTION_NAME = "li6800"
EMBEDDING_MODEL = "models/gemini-embedding-2-preview"
EMBEDDING_DIMS = 3072

# Cross-modal calibration: text-to-video cosine similarity peaks ~0.40-0.50
# while text-to-text peaks ~0.70-0.80. VIDEO_SCORE_MULTIPLIER boosts the
# effective score before threshold comparison.
VIDEO_SCORE_MULTIPLIER = 1.5
VIDEO_THRESHOLD = 0.58

_CANDIDATE_COUNT = 25


class EmbeddingService:
    """Gemini gemini-embedding-2-preview — text and video in one vector space."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    def embed(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        return result.embeddings[0].values

    def embed_video(self, video_bytes: bytes, mime_type: str = "video/mp4") -> list[float]:
        result = self._client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[types.Part.from_bytes(data=video_bytes, mime_type=mime_type)],
        )
        return result.embeddings[0].values


class OpenAIEmbeddingService:
    """OpenAI text-embedding-3-large fallback. Not compatible with Gemini vectors."""

    def __init__(self) -> None:
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model="text-embedding-3-large",
            input=text,
        )
        return response.data[0].embedding


class RAGService:
    def __init__(self, embedding_service: EmbeddingService, collection) -> None:
        self._embedding = embedding_service
        self._collection = collection

    def retrieve(self, query: str, top_k: int = 8) -> list[dict]:
        """
        Return up to top_k relevant chunks for the query.
        Pulls _CANDIDATE_COUNT raw candidates so video chunks are included.
        Text chunks below RELEVANCE_THRESHOLD and video chunks below
        VIDEO_THRESHOLD (after multiplier) are dropped.
        """
        query_embedding = self._embedding.embed(query)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=_CANDIDATE_COUNT,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            raw_similarity = 1 - dist
            is_video = meta.get("type") == "video"

            effective_similarity = (
                raw_similarity * VIDEO_SCORE_MULTIPLIER if is_video else raw_similarity
            )

            threshold = VIDEO_THRESHOLD if is_video else RELEVANCE_THRESHOLD
            if effective_similarity >= threshold:
                chunk = {
                    "id": meta.get("chunk_id", ""),
                    "text": doc,
                    "source": meta.get("source", ""),
                    "score": round(effective_similarity, 4),
                    "raw_score": round(raw_similarity, 4),
                }
                if is_video:
                    chunk["type"] = "video"
                    chunk["local_file"] = meta.get("local_file", "")
                    chunk["start_time"] = meta.get("start_time", 0)
                    chunk["end_time"] = meta.get("end_time", 0)
                chunks.append(chunk)

        return chunks[:top_k]


_CHROMA_SOURCE = (Path(__file__).parent.parent / "data" / "chroma").resolve()


def _chroma_path() -> str:
    # Vercel filesystem is read-only outside /tmp — copy data on cold start
    if os.environ.get("VERCEL"):
        dest = Path("/tmp/licor-chroma")
        if not dest.exists():
            shutil.copytree(str(_CHROMA_SOURCE), str(dest))
        return str(dest)
    return str(_CHROMA_SOURCE)


def build_rag_service() -> tuple[RAGService, EmbeddingService]:
    embedding_service = EmbeddingService()
    chroma_client = chromadb.PersistentClient(path=_chroma_path())
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return RAGService(embedding_service, collection), embedding_service
