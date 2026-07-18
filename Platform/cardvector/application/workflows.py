from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Iterable


Job = dict[str, Any]


@dataclass(frozen=True)
class WorkflowDelegates:
    discover_workflow_jobs: Callable[..., list[Job]]
    jobs_from_queue_rows: Callable[[Iterable[Job]], list[Job]]
    merge_job_lists: Callable[..., list[Job]]
    recent_completed_jobs: Callable[..., list[Job]]
    group_processing_jobs: Callable[[Iterable[Job]], dict[str, list[Job]]]
    active_listings_summary: Callable[[Any], dict[str, Any]]
    business_alerts: Callable[..., list[dict[str, str]]]
    update_workflow_context: Callable[..., dict[str, Any]]


class WorkflowApplication:
    """Coordinates workflow queries while legacy modules retain implementation."""

    def __init__(
        self,
        delegates: WorkflowDelegates,
        *,
        cache_seconds: float = 8.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._delegates = delegates
        self._cache_seconds = float(cache_seconds)
        self._clock = clock
        self._local_jobs: list[Job] = []
        self._local_jobs_refreshed = 0.0

    def invalidate(self) -> None:
        self._local_jobs_refreshed = 0.0

    def snapshot(
        self,
        *,
        capture_root: Any,
        mobile_processing_root: Any,
        mobile_failed_root: Any,
        queue_rows: Iterable[Job],
        active_job: Job | None,
        completed_root: Any,
        include_completed: bool = False,
        force: bool = False,
        local_limit: int = 60,
        result_limit: int = 65,
        completed_limit: int = 5,
    ) -> list[Job]:
        now = self._clock()
        if (
            force
            or not self._local_jobs
            or now - self._local_jobs_refreshed > self._cache_seconds
        ):
            self._local_jobs = self._delegates.discover_workflow_jobs(
                capture_root,
                mobile_processing_root,
                mobile_failed_root,
                limit=local_limit,
            )
            self._local_jobs_refreshed = now

        queue_jobs = self._delegates.jobs_from_queue_rows(queue_rows)
        active_jobs = [active_job] if active_job else []
        groups: list[Iterable[Job]] = [self._local_jobs, queue_jobs, active_jobs]
        if include_completed:
            groups.append(
                self._delegates.recent_completed_jobs(
                    completed_root,
                    limit=completed_limit,
                )
            )
        return self._delegates.merge_job_lists(*groups, limit=result_limit)

    def job_by_id(self, jobs: Iterable[Job], job_id: Any) -> Job | None:
        return next(
            (
                job
                for job in jobs
                if str(job.get("job_id")) == str(job_id)
            ),
            None,
        )

    def group_processing_jobs(
        self,
        jobs: Iterable[Job],
    ) -> dict[str, list[Job]]:
        return self._delegates.group_processing_jobs(jobs)

    def active_listings_summary(self, path: Any) -> dict[str, Any]:
        return self._delegates.active_listings_summary(path)

    def business_alerts(
        self,
        jobs: Iterable[Job],
        listings: dict[str, Any],
        *,
        policy_error: str = "",
        limit: int = 6,
    ) -> list[dict[str, str]]:
        return self._delegates.business_alerts(
            jobs,
            listings,
            policy_error=policy_error,
            limit=limit,
        )

    def update_context(self, capture_folder: Any, **updates: Any) -> dict[str, Any]:
        return self._delegates.update_workflow_context(capture_folder, **updates)
