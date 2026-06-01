"""Mock retry queue for rate-limited recent-search dry-runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class RetryTask:
    query: str
    retry_after_seconds: int
    enqueue_time: datetime
    retry_count: int = 0

    def ready_at(self) -> datetime:
        return self.enqueue_time + timedelta(seconds=max(self.retry_after_seconds, 0))

    def is_ready(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return current >= self.ready_at()


class RetryQueue:
    """In-memory mock queue. It never sleeps and never performs I/O."""

    def __init__(self) -> None:
        self._tasks: list[RetryTask] = []

    def enqueue(
        self,
        query: str,
        retry_after_seconds: int | None,
        *,
        enqueue_time: datetime | None = None,
        retry_count: int = 0,
    ) -> RetryTask:
        task = RetryTask(
            query=str(query),
            retry_after_seconds=max(int(retry_after_seconds or 0), 0),
            enqueue_time=enqueue_time or datetime.now(timezone.utc),
            retry_count=max(int(retry_count), 0),
        )
        self._tasks.append(task)
        return task

    def dequeue_ready(self, now: datetime | None = None) -> list[RetryTask]:
        ready: list[RetryTask] = []
        pending: list[RetryTask] = []
        for task in self._tasks:
            if task.is_ready(now):
                ready.append(task)
            else:
                pending.append(task)
        self._tasks = pending
        return ready

    def size(self) -> int:
        return len(self._tasks)

    def snapshot(self) -> list[RetryTask]:
        return list(self._tasks)
