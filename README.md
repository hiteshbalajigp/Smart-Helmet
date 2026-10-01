# Smart Helmet Violation Detection System

Production-quality, modular Edge AI system for real-time traffic violation detection using a chin-mounted 90° camera.

## Features

- **Violation detection**: No helmet, triple riding
- **Object detection**: Person, motorcycle, helmet, no_helmet, license_plate (YOLOv8m)
- **Tracking**: ByteTrack multi-object tracking
- **License plates**: WPOD-NET + PaddleOCR with Indian plate validation
- **Evidence**: RAM circular buffer (10s before/after), JPEG + MP4 on violation only
- **Metadata**: GPS, timestamp, device ID, violation ID
- **Backend**: FastAPI + PostgreSQL REST API
- **Dashboard**: React analytics, search, map, live camera, export
- **Edge**: PyTorch → ONNX → TensorRT (FP16)

## Project Structure

```
smart-helmet-violation-detection/
├── configs/           # YAML configuration
├── datasets/          # Raw and processed datasets
├── training/          # Dataset pipeline, augmentation, YOLO training
├── inference/         # Detection, OCR, evidence, edge optimization
├── backend/           # FastAPI application
├── frontend/          # React dashboard
├── database/          # PostgreSQL schema
├── models/            # Checkpoints, ONNX, TensorRT, WPOD
├── scripts/           # CLI helpers
├── tests/             # Unit and integration tests
└── docs/              # Architecture, deployment, testing
```

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Prepare dataset

Place raw videos in `datasets/raw/videos/` and YOLO labels in `datasets/processed/labels/`.

```bash
python scripts/run.py dataset
```

### 3. Train YOLOv8m

```bash
python scripts/run.py train
python scripts/run.py train --resume   # resume from last.pt
```

### 4. Run inference

```bash
python scripts/run.py infer --source 0
python scripts/run.py infer --source path/to/video.mp4
```

### 5. Export edge models

```bash
python scripts/run.py export --format all
```

### 6. Start backend + dashboard (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8000/docs
- Dashboard: http://localhost:5173

## Configuration

Edit `configs/default.yaml` or override via environment variables:

```bash
set HELMET_DATABASE__URL=postgresql+asyncpg://user:pass@host/db
set HELMET_METADATA__DEVICE_ID=HELMET-002
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/violations` | Upload violation |
| GET | `/api/v1/violations` | List violations |
| GET | `/api/v1/violations/search?plate=` | Search by plate |
| GET | `/api/v1/violations/{id}/evidence/{snapshot\|video}` | Download evidence |
| GET | `/api/v1/dashboard/stats` | Dashboard statistics |

## Dataset Classes

| Class | Target Count |
|-------|--------------|
| helmet | 5000+ |
| no_helmet | 5000+ |
| motorcycle | 5000+ |
| triple_riding | 3000+ (derived from person count) |
| license_plate | 5000+ |

## Testing

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Testing Plan](docs/TESTING_PLAN.md)
- [Performance Evaluation](docs/PERFORMANCE.md)

## Accuracy Notes

Achieving 95%+ real-world accuracy requires:

1. 10,000–20,000 labeled images from Indian roads
2. Chin-mounted camera angle matching deployment
3. Balanced classes and diverse lighting/weather
4. Iterative error analysis after each training run

This repository provides the full pipeline; dataset collection and field tuning remain the primary accuracy drivers.

## License

MIT
