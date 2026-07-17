"""HTTP composition root for legacy features retained during incremental migration."""

from app.application.legacy.llm.generation import configure_llm_client_factory
from app.application.legacy.rag.retrieval_service import configure_retrieval_runtime
from app.application.legacy.rag.video_index_service import configure_video_runtime
from app.core.config import get_settings
from app.infrastructure.ingest.transcript.runtime import acquire_transcript
from app.infrastructure.llm.legacy import create_legacy_llm_client
from app.infrastructure.vector.legacy import vector_store


def configure_runtime() -> None:
    settings = get_settings()
    configure_llm_client_factory(lambda: create_legacy_llm_client(settings))
    configure_video_runtime(configured_vector_store=vector_store, transcript_acquirer=acquire_transcript)
    configure_retrieval_runtime(configured_vector_store=vector_store)
