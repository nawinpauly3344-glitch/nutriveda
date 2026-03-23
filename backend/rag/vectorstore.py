"""
Simple custom vector store using numpy + JSON.
Avoids ChromaDB's Python 3.14 pydantic v1 incompatibility.
Uses OpenAI embeddings stored as numpy arrays for fast cosine similarity search.
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

log = logging.getLogger(__name__)

STORE_DIR = Path(__file__).parent.parent.parent / "vector_store"
VECTORS_FILE = STORE_DIR / "embeddings.npy"
METADATA_FILE = STORE_DIR / "metadata.json"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of texts using OpenAI. Returns (N, 1536) array."""
    client = get_openai_client()
    all_embeddings = []

    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        batch_embeddings = [r.embedding for r in response.data]
        all_embeddings.extend(batch_embeddings)
        log.info(f"  Embedded batch {i//batch_size + 1}/{(len(texts)//batch_size)+1} ({len(batch)} texts)")

    return np.array(all_embeddings, dtype=np.float32)


def embed_query(text: str) -> np.ndarray:
    """Embed a single query text. Returns (1536,) array."""
    client = get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return np.array(response.data[0].embedding, dtype=np.float32)


def cosine_similarity(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query and all vectors."""
    query_norm = query / (np.linalg.norm(query) + 1e-10)
    vectors_norm = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-10)
    return vectors_norm @ query_norm


def save_vectorstore(embeddings: np.ndarray, metadata: List[dict]):
    """Save embeddings and metadata to disk."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(str(VECTORS_FILE), embeddings)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    log.info(f"Saved {len(metadata)} vectors to {STORE_DIR}")


def load_vectorstore() -> Tuple[Optional[np.ndarray], Optional[List[dict]]]:
    """Load embeddings and metadata from disk. Returns (None, None) if not found."""
    if not VECTORS_FILE.exists() or not METADATA_FILE.exists():
        return None, None
    embeddings = np.load(str(VECTORS_FILE))
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    log.info(f"Loaded {len(metadata)} vectors from {STORE_DIR}")
    return embeddings, metadata


def vectorstore_exists() -> Tuple[bool, int]:
    """Check if vector store exists and how many chunks it has."""
    if not VECTORS_FILE.exists() or not METADATA_FILE.exists():
        return False, 0
    try:
        with open(METADATA_FILE, "r") as f:
            meta = json.load(f)
        return len(meta) > 0, len(meta)
    except Exception:
        return False, 0


def search(query: str, k: int = 6, score_threshold: float = 0.3) -> List[Tuple[dict, float]]:
    """
    Search the vector store for chunks similar to the query.
    Returns list of (metadata_dict, score) tuples.
    """
    embeddings, metadata = load_vectorstore()
    if embeddings is None or metadata is None:
        log.warning("Vector store not found. Run the ingestion pipeline first.")
        return []

    query_embedding = embed_query(query)
    scores = cosine_similarity(query_embedding, embeddings)

    top_k_indices = np.argsort(scores)[::-1][:k]
    results = []
    for idx in top_k_indices:
        score = float(scores[idx])
        if score >= score_threshold:
            results.append((metadata[idx], score))

    return results
