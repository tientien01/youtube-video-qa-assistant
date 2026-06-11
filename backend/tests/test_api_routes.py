import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "fallback"
os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["VECTOR_STORE_PROVIDER"] = "local_json"

from fastapi.testclient import TestClient

from app.main import app
from app.services.chat_history_store import LocalChatHistoryStore
from app.services.extraction.transcript_service import TranscriptFetchError, TranscriptNotFoundError
from app.services.learning.generated_output_store import LocalGeneratedOutputStore
from app.services.rag.local_store import LocalRagStore
from app.services.rag.metadata_store import LocalVideoMetadataStore
from app.services.rag.models import TranscriptChunk
from app.services.rag.vector_store import LocalVectorStore


class ApiRoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_cors_allows_vite_fallback_port(self):
        response = self.client.options(
            "/api/v1/videos/ingest",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5174")

    def test_ingest_rejects_non_youtube_url(self):
        response = self.client.post(
            "/api/v1/videos/ingest",
            json={"url": "https://example.com/watch?v=dQw4w9WgXcQ"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("YouTube", response.json()["detail"])

    def test_ingest_returns_404_when_transcript_is_unavailable(self):
        with patch(
            "app.api.v1.routes.video.ingest_video_content",
            side_effect=TranscriptNotFoundError("Transcript not found for this video."),
        ):
            response = self.client.post(
                "/api/v1/videos/ingest",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Transcript not found for this video.")

    def test_ingest_returns_503_when_transcript_fetch_fails(self):
        with patch(
            "app.api.v1.routes.video.ingest_video_content",
            side_effect=TranscriptFetchError("Could not connect to YouTube transcript service."),
        ):
            response = self.client.post(
                "/api/v1/videos/ingest",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Could not connect to YouTube transcript service.")

    def test_ingest_returns_cached_video(self):
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
                response = self.client.post(
                    "/api/v1/videos/ingest",
                    json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
                )

        fetch_transcript_mock.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cached")
        self.assertEqual(response.json()["title"], "Cached video")
        self.assertEqual(response.json()["chunk_count"], 1)

    def test_video_history_lists_ingested_videos(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_store = LocalVideoMetadataStore(Path(temp_dir) / "metadata.json")
            metadata_store.upsert_video(
                video_id="dQw4w9WgXcQ",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Cached video",
                duration_seconds=5,
                transcript_language="en",
                chunk_count=1,
            )

            with patch("app.services.rag.video_index_service.metadata_store", metadata_store):
                response = self.client.get("/api/v1/videos")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["video_id"], "dQw4w9WgXcQ")

    def test_video_history_gets_one_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_store = LocalVideoMetadataStore(Path(temp_dir) / "metadata.json")
            metadata_store.upsert_video(
                video_id="dQw4w9WgXcQ",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Cached video",
                duration_seconds=5,
                transcript_language="en",
                chunk_count=1,
            )

            with patch("app.services.rag.video_index_service.metadata_store", metadata_store):
                response = self.client.get("/api/v1/videos/dQw4w9WgXcQ")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Cached video")

    def test_video_history_returns_404_for_missing_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_store = LocalVideoMetadataStore(Path(temp_dir) / "metadata.json")

            with patch("app.services.rag.video_index_service.metadata_store", metadata_store):
                response = self.client.get("/api/v1/videos/missing0000")

        self.assertEqual(response.status_code, 404)

    def test_video_history_deletes_video(self):
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
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])
            metadata_store.upsert_video(
                video_id="dQw4w9WgXcQ",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Cached video",
                duration_seconds=5,
                transcript_language="en",
                chunk_count=1,
            )
            output_store.upsert_output(
                video_id="dQw4w9WgXcQ",
                output_type="summary",
                mode="short",
                content="Cached summary",
                source_chunk_ids=[chunk.chunk_id],
            )

            with (
                patch("app.services.rag.video_index_service.rag_store", store),
                patch("app.services.rag.video_index_service.vector_store", vector_store),
                patch("app.services.rag.video_index_service.metadata_store", metadata_store),
                patch("app.services.rag.video_index_service.generated_output_store", output_store),
            ):
                response = self.client.delete("/api/v1/videos/dQw4w9WgXcQ")

            self.assertFalse(store.has_video("dQw4w9WgXcQ"))
            self.assertIsNone(metadata_store.get_video("dQw4w9WgXcQ"))
            self.assertIsNone(
                output_store.get_output(
                    video_id="dQw4w9WgXcQ",
                    output_type="summary",
                    mode="short",
                )
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["deleted"])

    def test_summary_endpoint_generates_short_summary(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="RAG retrieves transcript chunks before generation.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])

            with (
                patch("app.services.learning.summary_service.rag_store", store),
                patch("app.services.learning.summary_service.generated_output_store", output_store),
            ):
                response = self.client.post(
                    "/api/v1/videos/dQw4w9WgXcQ/summary",
                    json={"mode": "short"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "short")
        self.assertFalse(response.json()["cached"])
        self.assertIn("Tóm tắt ngắn", response.json()["summary"])
        self.assertEqual(len(response.json()["sources"]), 1)

    def test_summary_endpoint_returns_404_for_unindexed_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")

            with (
                patch("app.services.learning.summary_service.rag_store", store),
                patch("app.services.learning.summary_service.generated_output_store", output_store),
            ):
                response = self.client.post(
                    "/api/v1/videos/missing0000/summary",
                    json={"mode": "short"},
                )

        self.assertEqual(response.status_code, 404)

    def test_notes_endpoint_generates_study_notes(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Study notes convert transcript chunks into review material.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])

            with (
                patch("app.services.learning.notes_service.rag_store", store),
                patch("app.services.learning.notes_service.generated_output_store", output_store),
            ):
                response = self.client.post(
                    "/api/v1/videos/dQw4w9WgXcQ/study-notes",
                    json={
                        "mode": "exam_review",
                        "learning_goal": "ôn lại ý chính",
                        "force": True,
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["cached"])
        self.assertEqual(response.json()["mode"], "exam_review")
        self.assertEqual(response.json()["learning_goal"], "ôn lại ý chính")
        self.assertIn("Mục tiêu bài học", response.json()["notes"])
        self.assertEqual(len(response.json()["sources"]), 1)

    def test_notes_endpoint_returns_404_for_unindexed_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")

            with (
                patch("app.services.learning.notes_service.rag_store", store),
                patch("app.services.learning.notes_service.generated_output_store", output_store),
            ):
                response = self.client.post("/api/v1/videos/missing0000/study-notes")

        self.assertEqual(response.status_code, 404)

    def test_quiz_endpoint_generates_quiz(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Quiz generation uses transcript chunks as grounded source material.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])

            with (
                patch("app.services.learning.quiz_service.rag_store", store),
                patch("app.services.learning.quiz_service.generated_output_store", output_store),
            ):
                response = self.client.post(
                    "/api/v1/videos/dQw4w9WgXcQ/quiz",
                    json={
                        "question_count": 1,
                        "difficulty": "medium",
                        "question_type": "multiple_choice",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["cached"])
        self.assertEqual(len(response.json()["questions"]), 1)
        self.assertEqual(response.json()["questions"][0]["question_type"], "multiple_choice")
        self.assertEqual(response.json()["questions"][0]["source"]["chunk_id"], chunk.chunk_id)

    def test_quiz_endpoint_returns_404_for_unindexed_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            output_store = LocalGeneratedOutputStore(Path(temp_dir) / "outputs.json")

            with (
                patch("app.services.learning.quiz_service.rag_store", store),
                patch("app.services.learning.quiz_service.generated_output_store", output_store),
            ):
                response = self.client.post(
                    "/api/v1/videos/missing0000/quiz",
                    json={"question_count": 1},
                )

        self.assertEqual(response.status_code, 404)

    def test_debug_retrieve_endpoint_returns_chunks_and_latency(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Hybrid retrieval combines lexical and vector scores.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])

            with patch("app.services.rag.retrieval_service.rag_store", store):
                response = self.client.post(
                    "/api/v1/debug/retrieve",
                    json={
                        "video_id": "dQw4w9WgXcQ",
                        "question": "How does hybrid retrieval work?",
                        "retrieval_mode": "bm25",
                        "top_k": 1,
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["retrieval_mode"], "bm25")
        self.assertEqual(response.json()["top_k"], 1)
        self.assertGreaterEqual(response.json()["latency_ms"], 0)
        self.assertEqual(response.json()["chunks"][0]["chunk_id"], chunk.chunk_id)

    def test_debug_retrieve_endpoint_returns_404_for_unindexed_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")

            with patch("app.services.rag.retrieval_service.rag_store", store):
                response = self.client.post(
                    "/api/v1/debug/retrieve",
                    json={
                        "video_id": "missing0000",
                        "question": "What is retrieval?",
                        "retrieval_mode": "bm25",
                    },
                )

        self.assertEqual(response.status_code, 404)

    def test_chat_rejects_empty_question(self):
        response = self.client.post(
            "/api/v1/chat/ask",
            json={"video_id": "unindexed01", "question": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Question cannot be empty.")

    def test_chat_returns_404_for_unindexed_video(self):
        response = self.client.post(
            "/api/v1/chat/ask",
            json={"video_id": "unindexed01", "question": "What is this video about?"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Video has not been indexed yet.")

    def test_chat_accepts_retrieval_mode(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Hybrid retrieval combines keyword matching and embedding search.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            vector_store = LocalVectorStore(Path(temp_dir) / "vectors.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])
            vector_store.upsert_video("dQw4w9WgXcQ", [chunk])

            with (
                patch("app.services.rag.retrieval_service.rag_store", store),
                patch("app.services.rag.retrieval_service.vector_store", vector_store),
                patch(
                    "app.services.llm.generation.build_configured_llm_client",
                    return_value=None,
                ),
            ):
                response = self.client.post(
                    "/api/v1/chat/ask",
                    json={
                        "video_id": "dQw4w9WgXcQ",
                        "question": "How does hybrid retrieval work?",
                        "retrieval_mode": "hybrid",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["retrieval_mode"], "hybrid")
        self.assertGreaterEqual(len(response.json()["sources"]), 1)


    def test_rebuild_index_endpoint_rebuilds_vectors(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Rebuild index should use existing transcript chunks.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            vector_store = LocalVectorStore(Path(temp_dir) / "vectors.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])

            with (
                patch("app.services.rag.video_index_service.rag_store", store),
                patch("app.services.rag.video_index_service.vector_store", vector_store),
            ):
                response = self.client.post("/api/v1/videos/dQw4w9WgXcQ/rebuild-index")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["rebuilt"])
        self.assertEqual(response.json()["chunk_count"], 1)
        self.assertTrue(vector_store.has_video("dQw4w9WgXcQ"))

    def test_chat_history_endpoint_returns_backend_messages(self):
        chunk = TranscriptChunk(
            chunk_id="dQw4w9WgXcQ-0001",
            video_id="dQw4w9WgXcQ",
            text="Chat history should sync through the backend.",
            start_seconds=0,
            end_seconds=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalRagStore(Path(temp_dir) / "index.json")
            vector_store = LocalVectorStore(Path(temp_dir) / "vectors.json")
            chat_store = LocalChatHistoryStore(Path(temp_dir) / "chat.json")
            store.upsert_video("dQw4w9WgXcQ", [chunk])
            vector_store.upsert_video("dQw4w9WgXcQ", [chunk])

            with (
                patch("app.services.rag.video_index_service.rag_store", store),
                patch("app.services.rag.video_index_service.vector_store", vector_store),
                patch("app.services.rag.video_index_service.chat_history_store", chat_store),
            ):
                ask_response = self.client.post(
                    "/api/v1/chat/ask",
                    json={
                        "video_id": "dQw4w9WgXcQ",
                        "question": "What does chat history sync?",
                        "retrieval_mode": "hybrid",
                    },
                )
                history_response = self.client.get("/api/v1/chat/history/dQw4w9WgXcQ")

        self.assertEqual(ask_response.status_code, 200)
        self.assertIsNotNone(ask_response.json()["message_id"])
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.json()["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
