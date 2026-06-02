import tempfile
import unittest
from pathlib import Path

from app.schemas.transcript import TranscriptSegment
from app.services.rag.local_store import LocalRagStore
from app.services.rag.text_processing import chunk_transcript


class RagServicesTest(unittest.TestCase):
    def test_chunk_transcript_keeps_timestamp_range(self):
        segments = [
            TranscriptSegment(text="First concept about retrieval.", start_seconds=0, end_seconds=4),
            TranscriptSegment(text="Second concept about generation.", start_seconds=4, end_seconds=8),
        ]

        chunks = chunk_transcript("video123456", segments, target_words=5, overlap_words=0)

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].start_seconds, 0)
        self.assertGreaterEqual(chunks[-1].end_seconds, 8)

    def test_local_store_retrieves_relevant_chunk(self):
        segments = [
            TranscriptSegment(text="Retrieval finds context from transcript.", start_seconds=0, end_seconds=4),
            TranscriptSegment(text="Cooking pasta needs boiling water.", start_seconds=4, end_seconds=8),
        ]
        chunks = chunk_transcript("video123456", segments, target_words=6, overlap_words=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            store.upsert_video("video123456", chunks)

            results = store.retrieve("video123456", "How does retrieval work?", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertIn("Retrieval", results[0].chunk.text)


if __name__ == "__main__":
    unittest.main()
