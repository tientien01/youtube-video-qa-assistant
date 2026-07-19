import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "fallback"
os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["VECTOR_STORE_PROVIDER"] = "local_json"

from app.core.config import get_settings
from app.api.contracts.transcript import TranscriptSegment
from app.application.legacy.extraction.youtube_metadata_service import YouTubeMetadata
from app.application.legacy.llm.base import LlmError
from app.application.legacy.llm.config import load_llm_settings
from app.application.legacy.llm.generation import OptionalLlmResult
from app.application.legacy.learning.generated_output_store import LocalGeneratedOutputStore
from app.application.legacy.learning.notes_service import generate_study_notes
from app.application.legacy.learning.quiz_service import generate_quiz
from app.application.legacy.learning.summary_service import generate_video_summary
from app.application.legacy.rag.generation_service import generate_answer
from app.infrastructure.embeddings.legacy import HashingEmbeddingService
from app.application.legacy.rag.local_store import LocalRagStore
from app.application.legacy.rag.metadata_store import LocalVideoMetadataStore
from app.application.legacy.rag.models import RetrievedChunk, TranscriptChunk
from app.application.legacy.rag.reranker import LexicalReranker
from app.application.legacy.rag.retrieval_service import retrieve_chunks
from app.application.legacy.rag.text_processing import chunk_transcript, tokenize
from app.infrastructure.vector.legacy import LocalVectorStore
from app.application.legacy.rag.video_index_service import ingest_video_content


class RagServicesTest(unittest.TestCase):
    def setUp(self):
        self._env_patcher = patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "fallback",
                "EMBEDDING_PROVIDER": "hashing",
                "VECTOR_STORE_PROVIDER": "local_json",
            },
        )
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()

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
                patch("app.application.legacy.rag.video_index_service.rag_store", store),
                patch("app.application.legacy.rag.video_index_service.metadata_store", metadata_store),
                patch("app.application.legacy.rag.video_index_service.vector_store", vector_store),
                patch("app.application.legacy.rag.video_index_service.fetch_transcript") as fetch_transcript_mock,
            ):
                response = ingest_video_content("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

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
                patch("app.application.legacy.rag.video_index_service.rag_store", store),
                patch("app.application.legacy.rag.video_index_service.metadata_store", metadata_store),
                patch("app.application.legacy.rag.video_index_service.vector_store", vector_store),
                patch(
                    "app.application.legacy.rag.video_index_service.fetch_transcript",
                    return_value=(segments, "en"),
                ),
                patch(
                    "app.application.legacy.rag.video_index_service.fetch_youtube_metadata",
                    return_value=YouTubeMetadata(
                        title="Real video title",
                        channel_title="Learning channel",
                        thumbnail_url="https://example.com/thumb.jpg",
                        duration_seconds=120,
                    ),
                ),
            ):
                response = ingest_video_content("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            metadata = metadata_store.get_video("dQw4w9WgXcQ")

        self.assertEqual(response.status, "ready")
        self.assertEqual(response.title, "Real video title")
        self.assertEqual(response.channel_title, "Learning channel")
        self.assertEqual(response.thumbnail_url, "https://example.com/thumb.jpg")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.channel_title, "Learning channel")
        self.assertEqual(metadata.thumbnail_url, "https://example.com/thumb.jpg")
        self.assertEqual(metadata.duration_seconds, 120)
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

    def test_vector_store_accepts_injected_embedding_service(self):
        chunks = [
            TranscriptChunk(
                chunk_id="video123456-0001",
                video_id="video123456",
                text="Semantic retrieval chunk.",
                start_seconds=0,
                end_seconds=5,
            )
        ]
        embedding_service = HashingEmbeddingService(dimensions=32)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalVectorStore(
                Path(temp_dir) / "vectors.json",
                text_embedding_service=embedding_service,
            )
            store.upsert_video("video123456", chunks)
            results = store.retrieve("video123456", "semantic retrieval", top_k=1)

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
                patch("app.application.legacy.rag.retrieval_service.rag_store", rag_test_store),
                patch("app.application.legacy.rag.retrieval_service.vector_store", vector_test_store),
            ):
                results = retrieve_chunks(
                    video_id="video123456",
                    question="How does hybrid embedding retrieval work?",
                    mode="hybrid",
                    top_k=1,
                )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk.chunk_id, "video123456-0001")

    def test_lexical_reranker_uses_query_overlap_after_retrieval_score(self):
        candidates = [
            RetrievedChunk(
                chunk=TranscriptChunk(
                    chunk_id="video123456-0001",
                    video_id="video123456",
                    text="Unrelated cooking instructions.",
                    start_seconds=0,
                    end_seconds=5,
                ),
                score=1.0,
            ),
            RetrievedChunk(
                chunk=TranscriptChunk(
                    chunk_id="video123456-0002",
                    video_id="video123456",
                    text="Hybrid retrieval combines BM25 and semantic embeddings.",
                    start_seconds=5,
                    end_seconds=10,
                ),
                score=0.5,
            ),
        ]

        results = LexicalReranker().rerank(
            question="hybrid retrieval embeddings",
            candidates=candidates,
            top_k=1,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk.chunk_id, "video123456-0002")

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

    def test_summary_service_generates_and_caches_short_summary(self):
        chunks = [
            TranscriptChunk(
                chunk_id="video123456-0001",
                video_id="video123456",
                text="Retrieval finds relevant transcript context.",
                start_seconds=0,
                end_seconds=5,
            ),
            TranscriptChunk(
                chunk_id="video123456-0002",
                video_id="video123456",
                text="Generation uses the retrieved context to answer.",
                start_seconds=5,
                end_seconds=10,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", chunks)

            with (
                patch("app.application.legacy.learning.summary_service.rag_store", store),
                patch("app.application.legacy.learning.summary_service.generated_output_store", output_store),
            ):
                first_response = generate_video_summary("video123456", mode="short")
                second_response = generate_video_summary("video123456", mode="short")

        self.assertFalse(first_response.cached)
        self.assertTrue(second_response.cached)
        self.assertIn("Tóm tắt ngắn", first_response.summary)
        self.assertEqual(first_response.summary, second_response.summary)
        self.assertEqual(len(first_response.sources), 2)

    def test_summary_service_supports_timeline_mode(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Timeline summaries keep timestamp context.",
            start_seconds=65,
            end_seconds=70,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.summary_service.rag_store", store),
                patch("app.application.legacy.learning.summary_service.generated_output_store", output_store),
            ):
                response = generate_video_summary("video123456", mode="timeline")

        self.assertIn("01:05-01:10", response.summary)
        self.assertEqual(response.mode, "timeline")

    def test_summary_service_uses_llm_client_when_available(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Summary should use transcript context when an LLM is configured.",
            start_seconds=0,
            end_seconds=5,
        )
        llm_client = FakeLlmClient("Summary từ LLM.")

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.summary_service.rag_store", store),
                patch("app.application.legacy.learning.summary_service.generated_output_store", output_store),
            ):
                response = generate_video_summary("video123456", mode="short", llm_client=llm_client)

        self.assertEqual(response.summary, "Summary từ LLM.")
        self.assertIsNotNone(llm_client.last_prompt)
        self.assertIn("tóm tắt video YouTube", llm_client.last_prompt)
        self.assertIn("Summary should use transcript context", llm_client.last_prompt)

    def test_summary_service_falls_back_when_llm_fails(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Fallback summary remains available without an LLM.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.summary_service.rag_store", store),
                patch("app.application.legacy.learning.summary_service.generated_output_store", output_store),
            ):
                response = generate_video_summary(
                    "video123456",
                    mode="short",
                    llm_client=FailingLlmClient(),
                )

        self.assertIn("Tóm tắt ngắn", response.summary)
        self.assertIn("Fallback summary", response.summary)

    def test_summary_service_falls_back_when_llm_summary_is_incomplete(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Reading changes the brain by connecting vision, sound, language, and attention.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.summary_service.rag_store", store),
                patch("app.application.legacy.learning.summary_service.generated_output_store", output_store),
                patch(
                    "app.application.legacy.learning.summary_service.generate_optional_llm_result",
                    return_value=OptionalLlmResult(
                        text="* Đọc không phải là một khả năng b",
                        generation_mode="llm",
                        provider="gemini",
                    ),
                ),
            ):
                response = generate_video_summary("video123456", mode="short")

        self.assertEqual(response.generation.generation_mode, "fallback")
        self.assertEqual(response.generation.provider, "gemini")
        self.assertIn("too short", response.generation.fallback_reason)
        self.assertIn("Tóm tắt ngắn", response.summary)

    def test_summary_service_ignores_incomplete_cached_summary(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Reading changes the brain by connecting vision, sound, language, and attention.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])
            output_store.upsert_output(
                video_id="video123456",
                output_type="summary",
                mode="short",
                content="* Đọc không phải là một khả năng b",
                source_chunk_ids=[chunk.chunk_id],
            )

            with (
                patch("app.application.legacy.learning.summary_service.rag_store", store),
                patch("app.application.legacy.learning.summary_service.generated_output_store", output_store),
            ):
                response = generate_video_summary("video123456", mode="short")

        self.assertFalse(response.cached)
        self.assertNotEqual(response.summary, "* Đọc không phải là một khả năng b")

    def test_notes_service_generates_and_caches_study_notes(self):
        chunks = [
            TranscriptChunk(
                chunk_id="video123456-0001",
                video_id="video123456",
                text="Study notes should preserve important transcript ideas.",
                start_seconds=0,
                end_seconds=5,
            ),
            TranscriptChunk(
                chunk_id="video123456-0002",
                video_id="video123456",
                text="Timestamp sources help learners review the video.",
                start_seconds=5,
                end_seconds=10,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", chunks)

            with (
                patch("app.application.legacy.learning.notes_service.rag_store", store),
                patch("app.application.legacy.learning.notes_service.generated_output_store", output_store),
            ):
                first_response = generate_study_notes("video123456")
                second_response = generate_study_notes("video123456")

        self.assertFalse(first_response.cached)
        self.assertTrue(second_response.cached)
        self.assertIn("Mục tiêu bài học", first_response.notes)
        self.assertIn("Khái niệm chính", first_response.notes)
        self.assertIn("Timestamp nên xem lại", first_response.notes)
        self.assertEqual(first_response.notes, second_response.notes)
        self.assertEqual(len(first_response.sources), 2)

    def test_notes_service_uses_llm_client_when_available(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Study notes should use transcript context when an LLM is configured.",
            start_seconds=0,
            end_seconds=5,
        )
        llm_client = FakeLlmClient("Study notes từ LLM.")

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.notes_service.rag_store", store),
                patch("app.application.legacy.learning.notes_service.generated_output_store", output_store),
            ):
                response = generate_study_notes("video123456", llm_client=llm_client)

        self.assertEqual(response.notes, "Study notes từ LLM.")
        self.assertIsNotNone(llm_client.last_prompt)
        self.assertIn("study notes", llm_client.last_prompt)
        self.assertIn("Study notes should use transcript context", llm_client.last_prompt)

    def test_notes_service_keeps_generation_metadata_when_cached(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Study notes cache should preserve original generation metadata.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.notes_service.rag_store", store),
                patch("app.application.legacy.learning.notes_service.generated_output_store", output_store),
            ):
                first_response = generate_study_notes(
                    "video123456",
                    llm_client=FakeLlmClient(build_valid_notes_text()),
                )
                second_response = generate_study_notes("video123456")

        self.assertFalse(first_response.cached)
        self.assertTrue(second_response.cached)
        self.assertEqual(second_response.generation.generation_mode, "cached")
        self.assertEqual(second_response.generation.provider, "injected")
        self.assertIn("originally used llm", second_response.generation.fallback_reason)

    def test_notes_service_force_regenerates_cached_notes(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Study notes can be regenerated when cache quality is not good enough.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.notes_service.rag_store", store),
                patch("app.application.legacy.learning.notes_service.generated_output_store", output_store),
            ):
                first_response = generate_study_notes(
                    "video123456",
                    llm_client=FakeLlmClient("First notes."),
                )
                second_response = generate_study_notes(
                    "video123456",
                    force=True,
                    llm_client=FakeLlmClient("Second notes."),
                )

        self.assertEqual(first_response.notes, "First notes.")
        self.assertEqual(second_response.notes, "Second notes.")
        self.assertFalse(second_response.cached)

    def test_notes_service_uses_learning_goal_in_cache_key(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Learning goals should create separate cached study notes.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.notes_service.rag_store", store),
                patch("app.application.legacy.learning.notes_service.generated_output_store", output_store),
            ):
                first_response = generate_study_notes(
                    "video123456",
                    learning_goal="ôn thi",
                    llm_client=FakeLlmClient("Exam notes."),
                )
                second_response = generate_study_notes(
                    "video123456",
                    learning_goal="hiểu cơ bản",
                    llm_client=FakeLlmClient("Beginner notes."),
                )

        self.assertFalse(first_response.cached)
        self.assertFalse(second_response.cached)
        self.assertEqual(first_response.learning_goal, "ôn thi")
        self.assertEqual(second_response.learning_goal, "hiểu cơ bản")

    def test_notes_service_falls_back_when_llm_fails(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Fallback notes remain available without an LLM.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", [chunk])

            with (
                patch("app.application.legacy.learning.notes_service.rag_store", store),
                patch("app.application.legacy.learning.notes_service.generated_output_store", output_store),
            ):
                response = generate_study_notes("video123456", llm_client=FailingLlmClient())

        self.assertIn("Mục tiêu bài học", response.notes)
        self.assertIn("Fallback notes", response.notes)

    def test_notes_service_uses_section_notes_for_long_videos(self):
        chunks = [
            TranscriptChunk(
                chunk_id=f"video123456-{index:04d}",
                video_id="video123456",
                text=f"Long video section {index} explains an important learning concept.",
                start_seconds=index * 10,
                end_seconds=index * 10 + 8,
            )
            for index in range(24)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", chunks)

            with (
                patch("app.application.legacy.learning.notes_service.rag_store", store),
                patch("app.application.legacy.learning.notes_service.generated_output_store", output_store),
            ):
                response = generate_study_notes(
                    "video123456",
                    mode="detailed",
                    llm_client=FailingLlmClient(),
                )

        self.assertIn("Ghi chú theo phần", response.notes)
        self.assertGreater(response.sources[-1].start_seconds, response.sources[0].start_seconds)

    def test_quiz_service_generates_and_caches_quiz(self):
        chunks = [
            TranscriptChunk(
                chunk_id="video123456-0001",
                video_id="video123456",
                text="Retrieval augmented generation answers questions using transcript context.",
                start_seconds=0,
                end_seconds=5,
            ),
            TranscriptChunk(
                chunk_id="video123456-0002",
                video_id="video123456",
                text="Timestamp citations help learners verify the answer in the source video.",
                start_seconds=5,
                end_seconds=10,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("video123456", chunks)

            with (
                patch("app.application.legacy.learning.quiz_service.rag_store", store),
                patch("app.application.legacy.learning.quiz_service.generated_output_store", output_store),
            ):
                first_response = generate_quiz(
                    video_id="video123456",
                    question_count=2,
                    difficulty="medium",
                    question_type="mixed",
                )
                second_response = generate_quiz(
                    video_id="video123456",
                    question_count=2,
                    difficulty="medium",
                    question_type="mixed",
                )

        self.assertFalse(first_response.cached)
        self.assertTrue(second_response.cached)
        self.assertEqual(len(first_response.questions), 2)
        self.assertEqual(first_response.questions[0].question_type, "multiple_choice")
        self.assertEqual(first_response.questions[1].question_type, "true_false")
        self.assertEqual(first_response.questions[0].correct_answer, second_response.questions[0].correct_answer)
        self.assertEqual(len(first_response.sources), 2)

    def test_generate_answer_has_clear_fallback_without_context(self):
        answer = generate_answer("What is the main idea?", [])

        self.assertIn("not enough relevant transcript evidence", answer.lower())

    def test_generate_answer_uses_llm_client_when_available(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Grounded answers must only use transcript context.",
            start_seconds=0,
            end_seconds=5,
        )
        llm_client = FakeLlmClient("Câu trả lời từ LLM dựa trên transcript.")

        answer = generate_answer(
            question="Grounded answer hoạt động thế nào?",
            retrieved_chunks=[RetrievedChunk(chunk=chunk, score=0.9)],
            llm_client=llm_client,
        )

        self.assertEqual(answer, "Câu trả lời từ LLM dựa trên transcript.")
        self.assertIsNotNone(llm_client.last_prompt)
        self.assertIn("Use only the supplied transcript context", llm_client.last_prompt)
        self.assertIn("Answer in Vietnamese", llm_client.last_prompt)
        self.assertIn("Grounded answers", llm_client.last_prompt)

    def test_generate_answer_falls_back_when_llm_fails(self):
        chunk = TranscriptChunk(
            chunk_id="video123456-0001",
            video_id="video123456",
            text="Fallback answer keeps the app usable without an LLM.",
            start_seconds=0,
            end_seconds=5,
        )

        answer = generate_answer(
            question="Fallback dùng khi nào?",
            retrieved_chunks=[RetrievedChunk(chunk=chunk, score=0.9)],
            llm_client=FailingLlmClient(),
        )

        self.assertIn("Dựa trên bằng chứng transcript", answer)
        self.assertIn("Fallback answer", answer)

    def test_llm_settings_default_to_fallback_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = load_llm_settings()

        self.assertEqual(settings.provider, "fallback")
        self.assertFalse(settings.is_gemini_enabled)

    def test_llm_settings_use_fallback_when_gemini_key_is_empty(self):
        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "",
            },
            clear=True,
        ):
            settings = load_llm_settings()

        self.assertEqual(settings.provider, "fallback")
        self.assertFalse(settings.is_gemini_enabled)

    def test_core_settings_enable_gemini_from_environment(self):
        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL": "gemini-test-model",
                "LLM_TIMEOUT_SECONDS": "7",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertEqual(settings.llm_provider, "gemini")
        self.assertEqual(settings.gemini_api_key, "test-key")
        self.assertEqual(settings.gemini_model, "gemini-test-model")
        self.assertEqual(settings.llm_timeout_seconds, 7)

    def test_core_settings_read_phase_i_retrieval_options(self):
        with patch.dict(
            "os.environ",
            {
                "EMBEDDING_PROVIDER": "sentence_transformers",
                "EMBEDDING_MODEL_NAME": "all-MiniLM-L6-v2",
                "VECTOR_STORE_PROVIDER": "chroma",
                "CHROMA_PERSIST_DIR": "backend/data/vector_store/chroma-test",
                "RERANKER_ENABLED": "true",
                "RERANK_TOP_K": "12",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertEqual(settings.embedding_provider, "sentence_transformers")
        self.assertEqual(settings.embedding_model_name, "all-MiniLM-L6-v2")
        self.assertEqual(settings.vector_store_provider, "chroma")
        self.assertTrue(settings.reranker_enabled)
        self.assertEqual(settings.rerank_top_k, 12)

    def test_core_settings_read_local_ollama_models(self):
        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "ollama",
                "LLM_MODEL": "qwen2.5-coder:7b",
                "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
                "OLLAMA_KEEP_ALIVE": "45m",
                "LLM_CONTEXT_WINDOW": "8192",
                "EMBEDDING_PROVIDER": "ollama",
                "EMBEDDING_MODEL": "embeddinggemma",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertEqual(settings.llm_provider, "ollama")
        self.assertEqual(settings.llm_model, "qwen2.5-coder:7b")
        self.assertEqual(settings.ollama_base_url, "http://127.0.0.1:11434")
        self.assertEqual(settings.ollama_keep_alive, "45m")
        self.assertEqual(settings.llm_context_window, 8192)
        self.assertEqual(settings.embedding_provider, "ollama")
        self.assertEqual(settings.embedding_model_name, "embeddinggemma")

    def test_core_settings_resolve_chroma_path_under_backend_root(self):
        with patch.dict(
            "os.environ",
            {"CHROMA_PERSIST_DIR": "backend/data/vector_store/chroma-test"},
            clear=True,
        ):
            settings = get_settings()

        self.assertTrue(str(settings.chroma_persist_dir).endswith("backend\\data\\vector_store\\chroma-test"))
        self.assertNotIn("backend\\backend", str(settings.chroma_persist_dir))


class FakeLlmClient:
    def __init__(self, response: str) -> None:
        self._response = response
        self.last_prompt = None

    def generate_text(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._response


class FailingLlmClient:
    def generate_text(self, prompt: str) -> str:
        raise LlmError("Provider failed.")


def build_valid_notes_text() -> str:
    return (
        "Mục tiêu bài học:\n"
        "- Hiểu các ý chính trong transcript.\n"
        "- Biết đoạn nào cần xem lại khi học.\n\n"
        "Khái niệm chính:\n"
        "- Retrieval lấy ngữ cảnh liên quan từ transcript.\n"
        "- Timestamp giúp kiểm chứng nguồn trong video.\n"
        "- Study notes chuyển transcript thành tài liệu ôn tập.\n"
        "- Cache giúp tránh tạo lại nội dung giống nhau.\n\n"
        "Giải thích dễ hiểu:\n"
        "Nội dung này gom các ý quan trọng thành ghi chú ngắn để người học xem lại nhanh.\n\n"
        "Ví dụ hoặc chi tiết đáng chú ý trong transcript:\n"
        "- Transcript có thể được chia thành nhiều đoạn.\n"
        "- Mỗi đoạn giữ timestamp nguồn.\n"
        "- Notes có thể được tạo bằng LLM hoặc fallback.\n\n"
        "Timestamp nên xem lại:\n"
        "- 00:00-00:05: Xem lại đoạn transcript nguồn."
    )


if __name__ == "__main__":
    unittest.main()
