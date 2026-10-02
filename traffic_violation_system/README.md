# Traffic Violation Detection and Automated Reporting System

Foundation implementation (Prompt #1) for the locked USB-camera architecture. This package is the new canonical application scaffold. The existing `backend/`, `inference/`, and related folders at the repository root are preserved for prior smart-helmet work and are not removed.

## Architecture Implemented (Scaffold)

```
USB CAMERA (external)
    ↓
CameraManager / CameraDevice / per-camera worker threads
    ↓
PipelineOrchestrator (startup/shutdown)
    ↓
[Future] Frame buffer → YOLOv8 → violation engine → tracking/dedup
    ↓
TaskQueue + BackgroundWorkerPool (evidence, plate/OCR, DB, email)
    ↓
SQLite database + FastAPI dashboard API (auth-protected endpoints)
```

### Locked components present as architecture (not full CV pipeline)

| Area | Status |
|------|--------|
| Config / logging / `.env` | Implemented |
| SQLite models (User, Camera, Vehicle, Violation, Evidence, Notification, AuditLog) | Implemented |
| Auth (bcrypt + JWT, ADMIN / TRAFFIC_POLICE) | Implemented |
| USB camera discovery & registration | Implemented |
| Multi-camera isolated worker threads | Scaffold implemented |
| ViolationEvent schema + violation title constants | Implemented |
| Vehicle cooldown / deduplication service | Implemented |
| Evidence manager (original + annotated paths) | Implemented |
| YOLOv8 / WPOD-NET / PaddleOCR loaders | Interface only |
| Email service | Implemented (SMTP via env, invoked by workers later) |
| Performance metrics collector | Scaffold |
| Police dashboard UI / violation CRUD / hotspot map | Not in Prompt #1 |

Model weights are **not** integrated yet. Loaders report `MODEL WEIGHT NOT YET INTEGRATED` when files are missing.

## Project Layout

```
traffic_violation_system/
├── app/
│   ├── main.py
│   ├── config/
│   ├── api/
│   ├── auth/
│   ├── database/
│   ├── camera/
│   ├── detection/
│   ├── violations/
│   ├── tracking/
│   ├── evidence/
│   ├── plate_detection/
│   ├── ocr/
│   ├── notifications/
│   ├── workers/
│   ├── services/
│   ├── schemas/
│   ├── utils/
│   └── templates/
├── model_weights/
├── data/
├── tests/
├── scripts/
├── logs/
├── run.py
├── requirements.txt
└── .env.example
```

## YOLOv8 Detection Stage

This stage adds the YOLOv8 object detection layer without introducing violation logic or other later-stage components.

### Model behavior

- The system loads a configurable YOLOv8 weights file via `YOLO_MODEL_PATH` / `YOLO_MODEL_PATH`-compatible settings.
- If the project has no trained weights yet, the detector is explicitly marked `MODEL_NOT_AVAILABLE` instead of pretending inference succeeded.
- The runtime reports the actual selected device (`cuda`, `cpu`, or a configured override) and does not silently claim GPU inference when it is running on CPU.
- Generic pretrained models are not treated as the final traffic-violation model. They are a development and integration scaffold only until the custom trained weights exist.

### Config keys

```env
YOLO_MODEL_PATH=./model_weights/yolo/best.pt
YOLO_CONFIDENCE_THRESHOLD=0.25
YOLO_IOU_THRESHOLD=0.45
YOLO_IMAGE_SIZE=640
YOLO_DEVICE=auto
YOLO_MAX_DETECTIONS=300
DETECTION_VISUALIZATION_ENABLED=false
```

### Development notes

- The camera continues to own capture; the YOLO service consumes frames independently.
- Visualization is a separate development utility and is not the production inference path.
- The inference service exposes structured detection results with class id, class name, confidence, and bounding box.

## Quick Start

```powershell
cd traffic_violation_system
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Optional: set BOOTSTRAP_ADMIN_PASSWORD in .env
python run.py
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health and http://127.0.0.1:8000/api/v1/health

## Tests

```powershell
pytest tests -v
```

## PostgreSQL Migration Path

SQLAlchemy uses `DATABASE_URL`. Switch from SQLite to PostgreSQL by updating the URL in `.env` (see comment in `.env.example`). No pipeline rewrite required.

## Development Notes

- Only **authorized external USB cameras** should be selected via configured `usb_device_index` per `Camera` record.
- Real-time detection, association logic, WPOD-NET inference, and PaddleOCR execution are deferred to later prompts.
- Email and database writes for violations are designed to run through background workers so the camera loop stays non-blocking.
