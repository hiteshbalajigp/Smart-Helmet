"""High-level orchestration scaffold for camera → async post-processing."""

from __future__ import annotations

from app.camera.manager import CameraManager
from app.tracking.cooldown import VehicleCooldownService
from app.utils.logging_config import get_logger
from app.workers.camera_worker import CameraWorkerRegistry
from app.workers.task_queue import BackgroundWorkerPool, TaskQueue, TaskType

logger = get_logger(__name__)


class PipelineOrchestrator:
    def __init__(self) -> None:
        self.camera_manager = CameraManager()
        self.camera_workers = CameraWorkerRegistry(self.camera_manager)
        self.cooldown_service = VehicleCooldownService()
        self.task_queue = TaskQueue()
        self.background_workers = BackgroundWorkerPool(
            queue=self.task_queue,
            handlers={
                TaskType.EVIDENCE_PROCESSING: self._handle_evidence_task,
                TaskType.PLATE_OCR: self._handle_plate_ocr_task,
                TaskType.DATABASE_PERSIST: self._handle_database_task,
                TaskType.NOTIFICATION: self._handle_notification_task,
            },
            worker_count=2,
        )

    def start(self) -> None:
        self.background_workers.start()
        logger.info("Pipeline orchestrator started.")

    def stop(self) -> None:
        self.camera_workers.stop_all()
        self.background_workers.stop()
        logger.info("Pipeline orchestrator stopped.")

    def _handle_evidence_task(self, task) -> None:
        logger.debug("Evidence task received: %s", task.task_id)

    def _handle_plate_ocr_task(self, task) -> None:
        logger.debug("Plate/OCR task received: %s", task.task_id)

    def _handle_database_task(self, task) -> None:
        logger.debug("Database task received: %s", task.task_id)

    def _handle_notification_task(self, task) -> None:
        logger.debug("Notification task received: %s", task.task_id)
