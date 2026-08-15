from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence, Tuple

import requests

RAG_DB_PATH = Path(os.getenv("RAG_DB_PATH", str(Path(__file__).with_name("rag_vectors.sqlite3"))))
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
RAG_CHUNK_CHARS = int(os.getenv("RAG_CHUNK_CHARS", "900"))
RAG_CHUNK_OVERLAP_LINES = int(os.getenv("RAG_CHUNK_OVERLAP_LINES", "2"))
RAG_MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "12000"))


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    start: float
    end: float
    text: str


def format_seconds(seconds: int) -> str:
    hrs, remainder = divmod(seconds, 3600)
    mins, secs = divmod(remainder, 60)
    return f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _watched_items(transcript: Iterable[object], current_time: float) -> list[tuple[float, float, str]]:
    items = []
    for item in transcript:
        start = float(getattr(item, "start", 0))
        if start > current_time:
            continue
        text = normalize_text(getattr(item, "text", ""))
        if text:
            items.append((start, start + float(getattr(item, "dur", 0) or 0), text))
    return sorted(items, key=lambda row: row[0])


def chunk_transcript(transcript: Iterable[object], current_time: float) -> list[Chunk]:
    items = _watched_items(transcript, current_time)
    chunks: list[Chunk] = []
    cursor = 0
    while cursor < len(items):
        selected: list[tuple[float, float, str]] = []
        size = 0
        while cursor < len(items):
            line = f"[{format_seconds(int(items[cursor][0]))}] {items[cursor][2]}"
            if selected and size + len(line) + 1 > RAG_CHUNK_CHARS:
                break
            selected.append(items[cursor])
            size += len(line) + 1
            cursor += 1
        text = "\n".join(f"[{format_seconds(int(row[0]))}] {row[2]}" for row in selected)
        digest = hashlib.sha256(text.encode()).hexdigest()
        chunks.append(Chunk(digest, selected[0][0], selected[-1][1], text))
        if cursor < len(items):
            cursor = max(cursor - min(RAG_CHUNK_OVERLAP_LINES, len(selected) - 1), 0)
    return chunks


class VectorStore:
    """Persistent SQLite vector store with local cosine search."""

    def __init__(self, path: Path | str = RAG_DB_PATH):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS transcript_vectors (
                video_id TEXT NOT NULL, model TEXT NOT NULL, chunk_id TEXT NOT NULL,
                start REAL NOT NULL, end REAL NOT NULL, text TEXT NOT NULL,
                embedding TEXT NOT NULL, PRIMARY KEY (video_id, model, chunk_id))""")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def get_ids(self, video_id: str, model: str, ids: Sequence[str]) -> set[str]:
        if not ids:
            return set()
        marks = ",".join("?" for _ in ids)
        with self._connect() as db:
            rows = db.execute(f"SELECT chunk_id FROM transcript_vectors WHERE video_id=? AND model=? AND chunk_id IN ({marks})", (video_id, model, *ids)).fetchall()
        return {row[0] for row in rows}

    def add(self, video_id: str, model: str, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        with self._connect() as db:
            db.executemany("INSERT OR IGNORE INTO transcript_vectors VALUES (?, ?, ?, ?, ?, ?, ?)", [(video_id, model, c.chunk_id, c.start, c.end, c.text, json.dumps(list(v))) for c, v in zip(chunks, vectors)])

    def vectors_for(self, video_id: str, model: str, ids: Sequence[str]) -> list[tuple[Chunk, list[float]]]:
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        with self._connect() as db:
            rows = db.execute(f"SELECT chunk_id,start,end,text,embedding FROM transcript_vectors WHERE video_id=? AND model=? AND chunk_id IN ({marks})", (video_id, model, *ids)).fetchall()
        return [(Chunk(r[0], r[1], r[2], r[3]), json.loads(r[4])) for r in rows]


def ollama_embed(texts: Sequence[str]) -> list[list[float]]:
    response = requests.post(OLLAMA_EMBED_URL, json={"model": OLLAMA_EMBED_MODEL, "input": list(texts)}, timeout=120)
    response.raise_for_status()
    vectors = response.json().get("embeddings")
    if not vectors or len(vectors) != len(texts):
        raise RuntimeError("Ollama embedding response did not contain the expected vectors.")
    return vectors


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return -1.0
    denominator = math.sqrt(sum(x*x for x in left)) * math.sqrt(sum(x*x for x in right))
    return sum(x*y for x, y in zip(left, right)) / denominator if denominator else 0.0


def retrieve_context(transcript: Iterable[object], video_id: str, current_time: float, question: str,
                     store: VectorStore | None = None,
                     embed: Callable[[Sequence[str]], list[list[float]]] = ollama_embed) -> Tuple[str, int, int]:
    chunks = chunk_transcript(transcript, current_time)
    if not chunks:
        return "", 0, 0
    store = store or VectorStore()
    existing = store.get_ids(video_id, OLLAMA_EMBED_MODEL, [c.chunk_id for c in chunks])
    missing = [c for c in chunks if c.chunk_id not in existing]
    if missing:
        store.add(video_id, OLLAMA_EMBED_MODEL, missing, embed([c.text for c in missing]))
    candidates = store.vectors_for(video_id, OLLAMA_EMBED_MODEL, [c.chunk_id for c in chunks])
    query_vector = embed([question])[0]
    ranked = sorted(candidates, key=lambda row: _cosine(query_vector, row[1]), reverse=True)
    chosen = [row[0] for row in ranked[:RAG_TOP_K]]
    latest = chunks[-1]
    if all(c.chunk_id != latest.chunk_id for c in chosen):
        chosen.append(latest)
    chosen.sort(key=lambda c: c.start)
    selected, used = [], 0
    for chunk in chosen:
        cost = len(chunk.text) + 2
        if selected and used + cost > RAG_MAX_CONTEXT_CHARS:
            continue
        selected.append(chunk)
        used += cost
    context = "\n\n".join(c.text for c in selected)
    return context, len(selected), len(context)


def build_context(transcript: Iterable[object], max_chars: int = RAG_MAX_CONTEXT_CHARS) -> Tuple[str, int, int]:
    """Legacy recent-window helper retained for compatibility."""
    context = "\n".join(c.text for c in chunk_transcript(transcript, float("inf")))[-max_chars:]
    return context, len(context.splitlines()), len(context)


def build_prompt(title: str, current_time_human: str, question: str, context: str) -> str:
    return f"""You are Spoiler Safe, an assistant that answers questions about a video without revealing future events.

Rules:
- Answer ONLY using the retrieved transcript excerpts below.
- The user has watched only up to timestamp: {current_time_human}.
- NEVER mention anything that could happen after that point.
- Excerpts may be non-contiguous; use their timestamps to interpret their order.
- If the answer is not supported by the excerpts, say that the watched portion does not provide enough information yet.
- Do not speculate. Be concise, clear, and helpful.

Video title: {title}
Current watched time: {current_time_human}
User question: {question}

Retrieved transcript excerpts from the watched portion:
{context}

Now answer the user's question safely."""
