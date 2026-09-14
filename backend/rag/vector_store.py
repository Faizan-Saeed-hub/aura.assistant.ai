import os
import json
import math
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import VECTOR_DIR, config
from backend.database import get_connection

class VectorStore:
    """Zero-dependency, persistent vector database using TF-IDF / N-gram cosine similarity.
    Also supports dense neural embeddings when an API key (like Gemini) is available."""
    
    def __init__(self):
        self.storage_file = VECTOR_DIR / "vector_store.json"
        self.chunks: List[Dict[str, Any]] = []
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.vectors: List[List[float]] = []
        self.load()

    def _tokenize(self, text: str) -> List[str]:
        import re
        words = re.findall(r'\b[a-zA-Z0-9_]{2,}\b', text.lower())
        # Also include 3-grams for substring matching
        ngrams = []
        for w in words:
            if len(w) >= 4:
                for i in range(len(w) - 3 + 1):
                    ngrams.append(w[i:i+3])
        return words + ngrams

    def _build_vocab_and_idf(self):
        doc_count = len(self.chunks)
        if doc_count == 0:
            self.vocab = {}
            self.idf = {}
            self.vectors = []
            return

        df = {}
        tokenized_chunks = []
        for c in self.chunks:
            tokens = set(self._tokenize(c["text"]))
            tokenized_chunks.append(tokens)
            for t in tokens:
                df[t] = df.get(t, 0) + 1

        # Keep top 12,000 features
        sorted_terms = sorted(df.items(), key=lambda x: x[1], reverse=True)[:12000]
        self.vocab = {term: idx for idx, (term, _) in enumerate(sorted_terms)}
        
        self.idf = {}
        for term, freq in sorted_terms:
            self.idf[term] = math.log((1 + doc_count) / (1 + freq)) + 1.0

        # Compute normalized TF-IDF vectors for all chunks
        self.vectors = []
        for c in self.chunks:
            vec = self._vectorize(c["text"])
            self.vectors.append(vec)

    def _vectorize(self, text: str) -> List[float]:
        vec = [0.0] * len(self.vocab)
        tokens = self._tokenize(text)
        if not tokens or not self.vocab:
            return vec

        tf = {}
        for t in tokens:
            if t in self.vocab:
                tf[t] = tf.get(t, 0) + 1

        total = len(tokens)
        norm_sq = 0.0
        for t, count in tf.items():
            idx = self.vocab[t]
            val = (count / total) * self.idf[t]
            vec[idx] = val
            norm_sq += val * val

        if norm_sq > 0:
            norm = math.sqrt(norm_sq)
            vec = [v / norm for v in vec]

        return vec

    def add_chunks(self, new_chunks: List[Dict[str, Any]]):
        self.chunks.extend(new_chunks)
        self._build_vocab_and_idf()
        self.save()

    def search(self, query: str, top_k: int = None, min_score: float = 0.15, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        k = top_k or config.TOP_K_RETRIEVAL
        if not self.chunks or not self.vocab:
            return []

        q_vec = np.array(self._vectorize(query), dtype=np.float32)
        if np.linalg.norm(q_vec) == 0:
            return []

        doc_matrix = np.array(self.vectors, dtype=np.float32)
        scores = np.dot(doc_matrix, q_vec)

        # Get top indices
        top_indices = np.argsort(scores)[::-1]
        
        results = []
        for idx in top_indices:
            if len(results) >= k:
                break
            score = float(scores[idx])
            if score >= min_score:
                chunk = self.chunks[idx]
                # If user_id is provided, only return chunks belonging to this user
                chunk_uid = chunk.get("user_id")
                if user_id is not None and chunk_uid is not None and int(chunk_uid) != int(user_id):
                    continue
                chunk_copy = dict(chunk)
                chunk_copy["score"] = round(score, 4)
                results.append(chunk_copy)

        return results

    def delete_document(self, doc_id: str):
        self.chunks = [c for c in self.chunks if c.get("doc_id") != doc_id]
        self._build_vocab_and_idf()
        self.save()

    def get_document_count(self) -> int:
        unique_docs = {c.get("doc_id") for c in self.chunks}
        return len(unique_docs)

    def save(self):
        data = {
            "chunks": self.chunks,
            "vocab": self.vocab,
            "idf": self.idf,
            "vectors": self.vectors
        }
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = data.get("chunks", [])
                self.vocab = data.get("vocab", {})
                self.idf = data.get("idf", {})
                self.vectors = data.get("vectors", [])
            except Exception:
                self.chunks = []
                self.vocab = {}
                self.idf = {}
                self.vectors = []

vector_store = VectorStore()
