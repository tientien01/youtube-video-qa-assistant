from threading import Event, Lock

from app.infrastructure.ingest.in_process_runner import InProcessIngestJobRunner


def test_runner_allows_only_one_active_job_per_video() -> None:
    started = Event()
    release = Event()
    calls: list[str] = []
    calls_lock = Lock()

    def handler(job_id: str) -> None:
        with calls_lock:
            calls.append(job_id)
        started.set()
        release.wait(timeout=2)

    runner = InProcessIngestJobRunner(handler, max_workers=2)
    try:
        runner.submit("job-1", "video-1")
        assert started.wait(timeout=2)
        runner.submit("job-2", "video-1")
        release.set()
        runner.shutdown()
    finally:
        release.set()

    assert calls == ["job-1"]
