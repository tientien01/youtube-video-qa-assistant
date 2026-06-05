import tempfile
import unittest
from pathlib import Path

from app.schemas.transcript import TranscriptSegment
from app.services.rag.generation_service import generate_answer
from app.services.rag.local_store import LocalRagStore
from app.services.rag.text_processing import chunk_transcript, tokenize


class RagServicesTest(unittest.TestCase):
    def test_tokenize_supports_vietnamese_words(self):
        tokens = tokenize("Truy xuất ngữ nghĩa giúp tìm kiếm tốt hơn.")

        self.assertIn("truy", tokens)
        self.assertIn("xuất", tokens)
        self.assertIn("ngữ", tokens)
        self.assertIn("nghĩa", tokens)

    def test_chunk_transcript_keeps_timestamp_range(self):
        segments = [
            TranscriptSegment(text="First concept about retrieval.", start_seconds=0, end_seconds=4),
            TranscriptSegment(text="Second concept about generation.", start_seconds=4, end_seconds=8),
        ]

        chunks = chunk_transcript("video123456", segments, target_words=5, overlap_words=0)

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].start_seconds, 0)
        self.assertGreaterEqual(chunks[-1].end_seconds, 8)

    def test_chunk_overlap_keeps_source_timestamp(self):
        segments = [
            TranscriptSegment(text="retrieval context transcript source", start_seconds=0, end_seconds=4),
            TranscriptSegment(text="semantic search embedding vector", start_seconds=4, end_seconds=8),
        ]

        chunks = chunk_transcript(
            "video123456",
            segments,
            target_words=4,
            overlap_words=2,
        )

        self.assertGreaterEqual(len(chunks), 2)
        self.assertLess(chunks[1].start_seconds, chunks[0].end_seconds)

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

    def test_generate_answer_has_clear_fallback_without_context(self):
        answer = generate_answer("What is the main idea?", [])

        self.assertIn("chưa tìm thấy", answer.lower())


if __name__ == "__main__":
    unittest.main()
