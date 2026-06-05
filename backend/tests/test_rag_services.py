import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.schemas.transcript import TranscriptSegment
from app.services.rag.generation_service import generate_answer
from app.services.rag.local_store import LocalRagStore
from app.services.rag.metadata_store import LocalVideoMetadataStore
from app.services.rag.models import TranscriptChunk
from app.services.rag.retrieval_service import retrieve_chunks
from app.services.rag.text_processing import chunk_transcript, tokenize
from app.services.rag.vector_store import LocalVectorStore
from app.services.rag.video_index_service import ingest_video_content


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

    def test_local_store_reports_cached_video(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Cached transcript chunk.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])

            self.assertTrue(store.has_video("dQw4w9WgXcQ"))
            self.assertEqual(store.get_video_chunk_count("dQw4w9WgXcQ"), 1)
            self.assertFalse(store.has_video("missing0000"))

    def test_ingest_uses_cached_video_without_fetching_transcript(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Cached transcript chunk.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            metadata_store = LocalVideoMetadataStore(Path(temp_dir) / "metadata.json")
            vector_store = LocalVectorStore(Path(temp_dir) / "vectors.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])
            metadata_store.upsert_video(
                video_id="dQw4w9WgXcQ",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Cached video",
                duration_seconds=5,
                transcript_language="en",
                chunk_count=1,
            )

            with (
                patch("app.services.rag.video_index_service.rag_store", store),
                patch("app.services.rag.video_index_service.metadata_store", metadata_store),
                patch("app.services.rag.video_index_service.vector_store", vector_store),
                patch("app.services.rag.video_index_service.fetch_transcript") as fetch_transcript_mock,
            ):
                response = ingest_video_content(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )

            fetch_transcript_mock.assert_not_called()
            self.assertEqual(response.status, "cached")
            self.assertEqual(response.title, "Cached video")
            self.assertEqual(response.duration_seconds, 5)
            self.assertEqual(response.transcript_language, "en")
            self.assertEqual(response.chunk_count, 1)

    def test_ingest_new_video_stores_metadata(self):
        segments = [
            TranscriptSegment(text="Retrieval finds transcript context.", start_seconds=0, end_seconds=4),
            TranscriptSegment(text="Generation uses retrieved context.", start_seconds=4, end_seconds=9),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            metadata_store = LocalVideoMetadataStore(Path(temp_dir) / "metadata.json")
            vector_store = LocalVectorStore(Path(temp_dir) / "vectors.json")

            with (
                patch("app.services.rag.video_index_service.rag_store", store),
                patch("app.services.rag.video_index_service.metadata_store", metadata_store),
                patch("app.services.rag.video_index_service.vector_store", vector_store),
                patch(
                    "app.services.rag.video_index_service.fetch_transcript",
                    return_value=(segments, "en"),
                ),
            ):
                response = ingest_video_content(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )

            metadata = metadata_store.get_video("dQw4w9WgXcQ")

        self.assertEqual(response.status, "ready")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.duration_seconds, 9)
        self.assertEqual(metadata.transcript_language, "en")
        self.assertGreater(metadata.chunk_count, 0)
        self.assertTrue(vector_store.has_video("dQw4w9WgXcQ"))

    def test_vector_store_retrieves_similar_chunk(self):
        chunks = [
            TranscriptChunk(
                chunk_id="video123456-0001",
                video_id="video123456",
                text="Semantic retrieval uses embeddings and vector search.",
                start_seconds=0,
                end_seconds=5,
            ),
            TranscriptChunk(
                chunk_id="video123456-0002",
                video_id="video123456",
                text="Cooking pasta needs boiling water.",
                start_seconds=5,
                end_seconds=10,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalVectorStore(Path(temp_dir) / "vectors.json")
            store.upsert_video("video123456", chunks)
            results = store.retrieve("video123456", "embedding search", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk.chunk_id, "video123456-0001")

    def test_retrieval_service_supports_hybrid_mode(self):
        chunks = [
            TranscriptChunk(
                chunk_id="video123456-0001",
                video_id="video123456",
                text="Hybrid retrieval combines BM25 keywords with embedding search.",
                start_seconds=0,
                end_seconds=5,
            ),
            TranscriptChunk(
                chunk_id="video123456-0002",
                video_id="video123456",
                text="Cooking pasta needs boiling water.",
                start_seconds=5,
                end_seconds=10,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            rag_test_store = LocalRagStore(Path(temp_dir) / "index.json")
            vector_test_store = LocalVectorStore(Path(temp_dir) / "vectors.json")
            rag_test_store.upsert_video("video123456", chunks)
            vector_test_store.upsert_video("video123456", chunks)

            with (
                patch("app.services.rag.retrieval_service.rag_store", rag_test_store),
                patch("app.services.rag.retrieval_service.vector_store", vector_test_store),
            ):
                results = retrieve_chunks(
                    video_id="video123456",
                    question="How does hybrid embedding retrieval work?",
                    mode="hybrid",
                    top_k=1,
                )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk.chunk_id, "video123456-0001")

    def test_metadata_store_lists_newest_video_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalVideoMetadataStore(Path(temp_dir) / "metadata.json")
            store.upsert_video(
                video_id="firstvideo1",
                url="https://www.youtube.com/watch?v=firstvideo1",
                title="First video",
                duration_seconds=10,
                transcript_language="en",
                chunk_count=2,
            )
            store.upsert_video(
                video_id="secondvid2",
                url="https://www.youtube.com/watch?v=secondvid2",
                title="Second video",
                duration_seconds=20,
                transcript_language="vi",
                chunk_count=3,
            )

            videos = store.list_videos()

        self.assertEqual([video.video_id for video in videos], ["secondvid2", "firstvideo1"])

    def test_generate_answer_has_clear_fallback_without_context(self):
        answer = generate_answer("What is the main idea?", [])

        self.assertIn("chưa tìm thấy", answer.lower())


if __name__ == "__main__":
    unittest.main()
