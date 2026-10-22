"""In-memory MRI job store for POST/GET /v1/mri/jobs. Fine for the single-replica deployments (maxReplicas 1);
a restarted replica loses its jobs and GET answers 404."""
from __future__ import annotations

import secrets
import threading
import time


class Job:
    def __init__(self, job_id: str, lock: threading.Lock):
        self.id, self._lock = job_id, lock
        self.created = time.time()
        self.state: dict = {'status': 'queued', 'stage': 'upload', 'progress': 0.0, 'result': None, 'error': None}

    def update(self, **kw) -> None:
        with self._lock:
            self.state.update(kw)

    def view(self) -> dict:
        with self._lock:
            return {'job_id': self.id, **self.state}


class JobStore:
    def __init__(self, ttl_s: int = 1800, max_items: int = 100):
        self.ttl_s, self.max_items = ttl_s, max_items
        self._items: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self) -> Job:
        job = Job(secrets.token_urlsafe(16), self._lock)
        with self._lock:
            self._purge()
            self._items[job.id] = job
            while len(self._items) > self.max_items:
                self._items.pop(next(iter(self._items)))
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            self._purge()
            return self._items.get(job_id)

    def _purge(self) -> None:
        cutoff = time.time() - self.ttl_s
        for k in [k for k, j in self._items.items() if j.created < cutoff]:
            del self._items[k]
