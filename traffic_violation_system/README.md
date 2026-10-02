# Traffic Violation Detection and Automated Reporting System

Foundation implementation (Prompt #1) for the locked USB-camera architecture. This package is the new canonical application scaffold. The existing `backend/`, `inference/`, and related folders at the repository root are preserved for prior smart-helmet work and are not removed.

## Architecture Implemented (Scaffold)

```
USB CAMERA (external)
    ↓
CameraManager / CameraDevice / per-camera worker threads
    ↓
Camera frame provider → YOLOv8 detection → object tracking
    ↓
Vehicle/person association → rider/pillion role candidates
    ↓
[Future] violation classification
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
| Vehicle/person tracking and association | Stage 4 implemented; no violation decisions |
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

## Vehicle/Person Tracking and Association (Stage 4)

`VehiclePersonTrackingService` consumes the structured `DetectionBatch` from the YOLOv8 stage and returns a `SceneTrackingResult`. Its layers remain separate: `IoUObjectTracker` maintains temporal object identities, `VehiclePersonAssociator` groups people with the best spatially matching vehicle, and `RiderPillionRoleAssigner` produces role candidates. The tracker is behind the `ObjectTracker` protocol so a ByteTrack implementation can be substituted without changing association logic.

The default development tracker uses class-aware greedy matching over IoU and normalized center proximity. Duplicate same-class boxes are suppressed within a frame. Tracks retain their IDs through the configured missed-frame grace period; state snapshots expose lifecycle status, age, confidence, first/last observation time, and motion. The implementation holds only active/grace-period tracks and lightweight counters, making its work proportional to the current detections and retained tracks.

Association scores combine the person's bottom-center proximity to the vehicle box, person/vehicle overlap, and the prior frame's vehicle assignment. Each person is assigned to at most one vehicle; groups and person counts are per vehicle. Person/vehicle class names are configurable and matched against YOLO's actual `class_name` values; unrelated model classes are ignored. Configure comma-separated labels in `.env` using `TRACKING_PERSON_CLASSES` and `TRACKING_VEHICLE_CLASSES`.

One confidently associated person may be marked as a rider candidate. For multiple people, the role assigner requires a consistent vehicle image-motion direction and sufficient separation along that direction before proposing the leading person as rider and the others as pillion candidates. If those signals are inconclusive, it reports `UNKNOWN`. Roles are candidates, not determinations. Counts represent associated person tracks per vehicle only.

Tracking configuration is exposed through `TRACKING_ENABLED`, `TRACK_MAX_MISSED_FRAMES`, `TRACK_MIN_CONFIDENCE`, `TRACK_MATCH_THRESHOLD`, `TRACKING_PERSON_CLASSES`, `TRACKING_VEHICLE_CLASSES`, `ASSOCIATION_ENABLED`, `ASSOCIATION_THRESHOLD`, and `ROLE_ASSIGNMENT_THRESHOLD`. The equivalent defaults are documented in `configs/default.yaml`.

The service is constructed independently and can be called with each `DetectionBatch`; it does not capture frames, call OpenCV, load YOLO itself, or use cloud services. Supply `frame_id`, `timestamp`, and `camera_id` explicitly when processing an empty batch, because an empty detection list has no per-detection frame metadata.

**This stage does not determine traffic violations.** It does not classify helmets, triple riding, evidence, plates, or any other violation. On Jetson Orin Nano, the tracker uses small CPU-side box calculations and bounded live-track state; this deterministic IoU implementation is intended as a lightweight development baseline, not a replacement for a production-tuned ByteTrack tracker.

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
- Real-time camera-to-inference orchestration, WPOD-NET inference, and PaddleOCR execution are deferred to later prompts.
- Email and database writes for violations are designed to run through background workers so the camera loop stays non-blocking.
