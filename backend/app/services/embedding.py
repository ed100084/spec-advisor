"""Embedding 服務 - 使用 fastembed + BAAI/bge-small-zh-v1.5"""
import re
import numpy as np
from fastembed import TextEmbedding

_model = None
MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(MODEL_NAME, cache_dir="/opt/models")
    return _model


def chunk_text(text: str, max_chars: int = 500, overlap: int = 80) -> list[str]:
    if not text or not text.strip():
        return []
    raw_parts = re.split(r'(?=第[一二三四五六七八九十百千\d]+條)', text)
    if len(raw_parts) <= 1:
        raw_parts = re.split(r'\n{2,}', text)
    paragraphs = [p.strip() for p in raw_parts if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            sentences = re.split(r'(?<=[。；\n])', para)
            sub = ""
            for sent in sentences:
                if len(sub) + len(sent) > max_chars and sub:
                    chunks.append(sub.strip())
                    sub = sub[-overlap:] if overlap else ""
                sub += sent
            if sub.strip():
                chunks.append(sub.strip())
        elif len(current) + len(para) > max_chars:
            chunks.append(current)
            current = current[-overlap:] + "\n" + para if overlap else para
        else:
            current = current + "\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) >= 20]


def compute_embeddings(texts: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = list(model.embed(texts))
    return [emb.tolist() for emb in embeddings]


def compute_single_embedding(text: str) -> list[float]:
    model = get_model()
    result = list(model.embed([text]))
    return result[0].tolist()


def cosine_similarity_search(
    query_embedding: list[float],
    chunk_embeddings: list[list[float]],
    top_k: int = 10,
) -> list[tuple[int, float]]:
    if not chunk_embeddings:
        return []
    query = np.array(query_embedding)
    chunks = np.array(chunk_embeddings)
    query_norm = query / (np.linalg.norm(query) + 1e-10)
    chunks_norm = chunks / (np.linalg.norm(chunks, axis=1, keepdims=True) + 1e-10)
    scores = np.dot(chunks_norm, query_norm)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_indices]
