import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import RLock


logger = logging.getLogger(__name__)


class InProcessIngestJobRunner:
    """Small local runner with one active future per video in this process."""

    def __init__(self, handler: Callable[[str], None], *, max_workers: int = 2) -> None:
        self._handler = handler
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ingest")
        self._futures_by_video: dict[str, Future[None]] = {}
        self._lock = RLock()

    def submit(self, job_id: str, video_id: str) -> None:
        with self._lock:
            existing = self._futures_by_video.get(video_id)
            if existing is not None and not existing.done():
                return
            future = self._executor.submit(self._run, job_id)
            self._futures_by_video[video_id] = future
            future.add_done_callback(lambda completed: self._forget(video_id, completed))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _run(self, job_id: str) -> None:
        try:
            self._handler(job_id)
        except Exception:
            logger.exception("Ingest job %s stopped with an unexpected error", job_id)

    def _forget(self, video_id: str, completed: Future[None]) -> None:
        with self._lock:
            if self._futures_by_video.get(video_id) is completed:
                self._futures_by_video.pop(video_id, None)
