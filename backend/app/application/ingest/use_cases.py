from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from threading import RLock
from time import monotonic

from app.application.ingest.ports import (
    IngestAttemptReport,
    IngestFailure,
    IngestJobRunner,
    IngestProcessor,
    IngestUnitOfWorkFactory,
    ProcessedVideo,
    ProcessVideoRequest,
)
from app.application.ports.repositories import IngestJobRepository
from app.domain.entities import (
    AttemptOutcome,
    IngestAttempt,
    IngestJob,
    IngestJobStatus,
    IngestStage,
    Video,
    VideoStatus,
    utc_now,
)
from app.domain.video_identity import parse_youtube_video_url


class IngestJobNotFound(LookupError):
    pass


class IngestJobApplication:
    """Application use cases for the persistent local ingest lifecycle."""

    def __init__(
        self,
        uow_factory: IngestUnitOfWorkFactory,
        processor: IngestProcessor,
        *,
        target_fingerprint: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._processor = processor
        self._target_fingerprint = target_fingerprint
        self._runner: IngestJobRunner | None = None
        self._create_lock = RLock()

    def attach_runner(self, runner: IngestJobRunner) -> None:
        if self._runner is not None:
            raise RuntimeError("An ingest job runner is already attached.")
        self._runner = runner

    def create(self, url: str, *, client_idempotency_key: str | None = None) -> IngestJob:
        youtube_video_id, canonical_url = parse_youtube_video_url(url)
        idempotency_key = _idempotency_key(
            youtube_video_id,
            self._target_fingerprint,
            client_idempotency_key,
        )

        created = False
        # The database partial unique index is the durable guard. This lock also
        # makes the single-process local path deterministic before the insert.
        with self._create_lock:
            with self._uow_factory() as uow:
                existing_job = uow.jobs.get_by_idempotency_key(idempotency_key)
                if existing_job is not None:
                    job = existing_job
                else:
                    video = uow.videos.get_by_youtube_id(youtube_video_id)
                    if video is None:
                        video = uow.videos.add(
                            Video(
                                youtube_video_id=youtube_video_id,
                                canonical_url=canonical_url,
                                title=f"YouTube video {youtube_video_id}",
                            )
                        )

                    active_job = uow.jobs.find_active(video.id, self._target_fingerprint)
                    if active_job is not None:
                        job = active_job
                    else:
                        job = uow.jobs.add(
                            IngestJob(
                                video_id=video.id,
                                idempotency_key=idempotency_key,
                                target_fingerprint=self._target_fingerprint,
                            )
                        )
                        created = True
                    uow.commit()

        if (created or job.status is IngestJobStatus.PENDING) and self._runner is not None:
            self._runner.submit(job.id, job.video_id)
        return job

    def get(self, job_id: str) -> IngestJob:
        with self._uow_factory() as uow:
            job = uow.jobs.get(job_id)
            if job is None:
                raise IngestJobNotFound(f"Ingest job {job_id} was not found.")
            return job

    def cancel(self, job_id: str) -> IngestJob:
        with self._uow_factory() as uow:
            job = _require_job(uow.jobs.get(job_id), job_id)
            cancelled = job.cancel()
            uow.jobs.save(cancelled)
            uow.commit()
            return cancelled

    def retry(self, job_id: str) -> IngestJob:
        with self._uow_factory() as uow:
            job = _require_job(uow.jobs.get(job_id), job_id)
            retried = job.retry()
            video = uow.videos.get(retried.video_id)
            if video is not None and video.status is VideoStatus.FAILED:
                uow.videos.save(replace(video, status=VideoStatus.PENDING, updated_at=utc_now()))
            uow.jobs.save(retried)
            uow.commit()

        if self._runner is not None:
            self._runner.submit(retried.id, retried.video_id)
        return retried

    def recover_interrupted(self) -> int:
        """Turn jobs left running by a stopped process into diagnosable failures."""

        recovered = 0
        with self._uow_factory() as uow:
            for job in uow.jobs.list_running():
                failed = job.fail(
                    error_code="INGEST_PROCESS_INTERRUPTED",
                    error_message="The local process stopped before this ingest completed.",
                    retryable=True,
                )
                uow.jobs.save(failed)
                video = uow.videos.get(job.video_id)
                if video is not None and video.status is VideoStatus.PROCESSING:
                    uow.videos.save(replace(video, status=VideoStatus.FAILED, updated_at=utc_now()))
                recovered += 1
            if recovered:
                uow.commit()
        return recovered

    def execute(self, job_id: str) -> None:
        request = self._start(job_id)
        if request is None:
            return

        started = monotonic()
        try:
            publication = self._processor.process(
                request,
                report_stage=lambda stage: self._advance(job_id, stage),
                is_cancelled=lambda: self.get(job_id).status is IngestJobStatus.CANCELLED,
            )
            self._publish(job_id, publication, elapsed_ms=_elapsed_ms(started))
        except IngestFailure as error:
            self._record_failure(
                job_id,
                code=error.code,
                message=str(error),
                retryable=error.retryable,
                elapsed_ms=_elapsed_ms(started),
                attempts=error.attempts,
            )
        except Exception:
            self._record_failure(
                job_id,
                code="INTERNAL_INGEST_ERROR",
                message="Unexpected ingest failure. Check local logs for details.",
                retryable=False,
                elapsed_ms=_elapsed_ms(started),
            )
            raise

    def _start(self, job_id: str) -> ProcessVideoRequest | None:
        with self._uow_factory() as uow:
            job = _require_job(uow.jobs.get(job_id), job_id)
            if job.status is not IngestJobStatus.PENDING:
                return None
            video = uow.videos.get(job.video_id)
            if video is None:
                raise RuntimeError(f"Ingest job {job.id} references a missing video.")
            uow.jobs.save(job.start())
            if video.status is not VideoStatus.READY:
                uow.videos.save(replace(video, status=VideoStatus.PROCESSING, updated_at=utc_now()))
            uow.commit()
            return ProcessVideoRequest(video_id=video.youtube_video_id, canonical_url=video.canonical_url)

    def _advance(self, job_id: str, stage: IngestStage) -> None:
        with self._uow_factory() as uow:
            job = _require_job(uow.jobs.get(job_id), job_id)
            if job.status is IngestJobStatus.CANCELLED:
                raise IngestFailure("INGEST_CANCELLED", "Ingest was cancelled.", retryable=False)
            uow.jobs.save(job.advance(stage))
            uow.commit()

    def _publish(self, job_id: str, publication: ProcessedVideo, *, elapsed_ms: int) -> None:
        with self._uow_factory() as uow:
            job = _require_job(uow.jobs.get(job_id), job_id)
            if job.status is IngestJobStatus.CANCELLED:
                return
            if job.current_stage is not IngestStage.COMMITTING:
                job = job.advance(IngestStage.COMMITTING)
            video = uow.videos.get(job.video_id)
            if video is None:
                raise RuntimeError(f"Ingest job {job.id} references a missing video.")

            now = utc_now()
            uow.videos.save(
                replace(
                    video,
                    title=publication.title,
                    channel_title=publication.channel_title,
                    thumbnail_url=publication.thumbnail_url,
                    duration_ms=publication.duration_ms,
                    status=VideoStatus.READY,
                    updated_at=now,
                )
            )
            ready_job = job.succeed(now=now)
            uow.jobs.save(ready_job)
            next_attempt = _persist_attempt_reports(uow.jobs, job.id, publication.attempts)
            uow.jobs.add_attempt(
                _domain_attempt(
                    job.id,
                    next_attempt,
                    provider=self._processor.name,
                    stage=IngestStage.COMMITTING,
                    outcome=AttemptOutcome.SUCCEEDED,
                    elapsed_ms=elapsed_ms,
                )
            )
            uow.commit()

    def _record_failure(
        self,
        job_id: str,
        *,
        code: str,
        message: str,
        retryable: bool,
        elapsed_ms: int,
        attempts: tuple[IngestAttemptReport, ...] = (),
    ) -> None:
        with self._uow_factory() as uow:
            job = _require_job(uow.jobs.get(job_id), job_id)
            if job.status is IngestJobStatus.CANCELLED:
                return
            failed = job.fail(
                error_code=code,
                error_message=_safe_message(message),
                retryable=retryable,
            )
            uow.jobs.save(failed)
            video = uow.videos.get(job.video_id)
            if video is not None and video.status is not VideoStatus.READY:
                uow.videos.save(replace(video, status=VideoStatus.FAILED, updated_at=utc_now()))
            if attempts:
                _persist_attempt_reports(uow.jobs, job.id, attempts)
            else:
                uow.jobs.add_attempt(
                    _domain_attempt(
                        job.id,
                        len(uow.jobs.list_attempts(job.id)) + 1,
                        provider=self._processor.name,
                        stage=job.current_stage,
                        outcome=AttemptOutcome.FAILED,
                        elapsed_ms=elapsed_ms,
                        error_code=code,
                        error_message=_safe_message(message),
                    )
                )
            uow.commit()


def _require_job(job: IngestJob | None, job_id: str) -> IngestJob:
    if job is None:
        raise IngestJobNotFound(f"Ingest job {job_id} was not found.")
    return job


def _idempotency_key(video_id: str, fingerprint: str, client_key: str | None) -> str:
    material = f"{video_id}\n{fingerprint}\n{client_key or ''}".encode()
    return sha256(material).hexdigest()


def _elapsed_ms(started: float) -> int:
    return max(0, round((monotonic() - started) * 1000))


def _safe_message(message: str) -> str:
    return " ".join(message.split())[:500]


def _persist_attempt_reports(
    repository: IngestJobRepository,
    job_id: str,
    reports: tuple[IngestAttemptReport, ...],
) -> int:
    attempt_number = len(repository.list_attempts(job_id)) + 1
    for report in reports:
        repository.add_attempt(
            _domain_attempt(
                job_id,
                attempt_number,
                provider=report.provider,
                stage=report.stage,
                outcome=report.outcome,
                elapsed_ms=report.elapsed_ms,
                error_code=report.error_code,
                error_message=report.error_message,
            )
        )
        attempt_number += 1
    return attempt_number


def _domain_attempt(
    job_id: str,
    attempt_number: int,
    *,
    provider: str,
    stage: IngestStage,
    outcome: AttemptOutcome,
    elapsed_ms: int | None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> IngestAttempt:
    return IngestAttempt(
        ingest_job_id=job_id,
        provider=provider,
        stage=stage,
        attempt_number=attempt_number,
        outcome=outcome,
        elapsed_ms=elapsed_ms,
        error_code=error_code,
        error_message=error_message,
    )
