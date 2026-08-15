import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import backend.rag as rag


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append([
                float("red key" in lowered or "key" == lowered),
                float("spaceship" in lowered),
                0.1,
            ])
        return vectors


class RagTests(unittest.TestCase):
    def setUp(self):
        self.original_chunk_chars = rag.RAG_CHUNK_CHARS
        self.original_top_k = rag.RAG_TOP_K
        rag.RAG_CHUNK_CHARS = 55
        rag.RAG_TOP_K = 1

    def tearDown(self):
        rag.RAG_CHUNK_CHARS = self.original_chunk_chars
        rag.RAG_TOP_K = self.original_top_k

    def test_semantic_retrieval_finds_old_context_and_excludes_future(self):
        transcript = [
            SimpleNamespace(start=0, dur=2, text="The red key opens the cellar door."),
            SimpleNamespace(start=60, dur=2, text="They board the spaceship and leave."),
            SimpleNamespace(start=120, dur=2, text="Future spoiler: the key was fake."),
        ]
        embedder = FakeEmbedder()
        with tempfile.TemporaryDirectory() as directory:
            context, count, chars = rag.retrieve_context(
                transcript, "video-1", 90, "key", rag.VectorStore(Path(directory) / "vectors.db"), embedder
            )
        self.assertIn("red key", context)
        self.assertIn("spaceship", context)  # latest watched chunk is retained
        self.assertNotIn("Future spoiler", context)
        self.assertEqual(count, 2)
        self.assertEqual(chars, len(context))

    def test_chunk_embeddings_are_cached(self):
        transcript = [SimpleNamespace(start=0, dur=2, text="The red key is on the table.")]
        embedder = FakeEmbedder()
        with tempfile.TemporaryDirectory() as directory:
            store = rag.VectorStore(Path(directory) / "vectors.db")
            rag.retrieve_context(transcript, "video-1", 10, "key", store, embedder)
            rag.retrieve_context(transcript, "video-1", 10, "key", store, embedder)
        self.assertEqual(len(embedder.calls), 3)  # chunks+query, then query only
        self.assertEqual(len(embedder.calls[0]), 1)


if __name__ == "__main__":
    unittest.main()
