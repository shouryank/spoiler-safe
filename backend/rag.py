from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class Chunk:
    start: float
    end: float
    text: str


class TfidfRAG:
    """
    Tiny RAG store:
    - fit TF-IDF on the "seen" chunks (<= current_time) per request
    - retrieve top-k most relevant chunks for the user query
    """
    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)

    def retrieve(self, query: str, chunks: List[Chunk], k: int = 6) -> List[Tuple[Chunk, float]]:
        if not chunks:
            return []

        texts = [c.text for c in chunks]
        X = self.vectorizer.fit_transform(texts)
        q = self.vectorizer.transform([query])

        scores = (X @ q.T).toarray().ravel()
        if scores.size == 0:
            return []

        top_idx = np.argsort(scores)[::-1][:k]
        out = [(chunks[i], float(scores[i])) for i in top_idx if scores[i] > 0]
        return out