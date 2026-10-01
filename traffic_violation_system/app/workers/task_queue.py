from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskType(str, Enum):
    EVIDENCE_PROCESSING = "EVIDENCE_PROCESSING"
    PLATE_OCR = "PLATE_OCR"
    DATABASE_PERSIST = "DATABASE_PERSIST"
    NOTIFICATION = "NOTIFICATION"


@dataclass
class WorkerTask:
    task_type: TaskType
    payload: dict[str, Any]
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class TaskQueue:
    def __init__(self, maxsize: int = 256) -> None:
        self._queue: queue.Queue[WorkerTask] = queue.Queue(maxsize=maxsize)

    def enqueue(self, task: WorkerTask, *, block: bool = True, timeout: float | None = None) -> None:
        self._queue.put(task, block=block, timeout=timeout)

    def dequeue(self, timeout: float | None = 0.5) -> WorkerTask | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def task_done(self) -> None:
        self._queue.task_done()

    @property
    def size(self) -> int:
        return self._queue.qsize()


Handler = Callable[[WorkerTask], None]


class BackgroundWorkerPool:
    def __init__(self, queue: TaskQueue, handlers: dict[TaskType, Handler], worker_count: int = 2) -> None:
        self.queue = queue
        self.handlers = handlers
        self.worker_count = worker_count
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if self._threads:
            return
        for index in range(self.worker_count):
            thread = threading.Thread(target=self._worker_loop, name=f"bg-worker-{index}", daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads.clear()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            task = self.queue.dequeue(timeout=0.5)
            if task is None:
                continue
            handler = self.handlers.get(task.task_type)
            try:
                if handler:
                    handler(task)
            finally:
                self.queue.task_done()
