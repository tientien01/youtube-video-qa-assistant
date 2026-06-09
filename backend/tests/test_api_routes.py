import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.extraction.transcript_service import TranscriptNotFoundError
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
                patch("app.services.rag.video_index_service.vector_store", vector_store),
                patch("app.services.rag.video_index_service.metadata_store", metadata_store),
            ):
                response = self.client.delete("/api/v1/videos/dQw4w9WgXcQ")

            self.assertFalse(store.has_video("dQw4w9WgXcQ"))
            self.assertIsNone(metadata_store.get_video("dQw4w9WgXcQ"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["deleted"])

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
                    "app.services.rag.generation_service._build_configured_llm_client",
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


if __name__ == "__main__":
    unittest.main()
