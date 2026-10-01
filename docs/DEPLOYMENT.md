# Deployment Guide

## Prerequisites

- Python 3.11+
- NVIDIA GPU (training) or Jetson Orin Nano (edge inference)
- Docker & Docker Compose (recommended for backend/dashboard)
- PostgreSQL 16+
- Node.js 20+ (local frontend development)

## Edge Device Deployment (Jetson Orin Nano)

### 1. Install JetPack and dependencies

```bash
sudo apt update
sudo apt install python3-pip libopencv-dev
pip3 install -r requirements.txt
```

### 2. Train on workstation, copy weights

Copy `models/checkpoints/helmet_violation_yolov8m/weights/best.pt` to the edge device.

### 3. Export TensorRT engine on Jetson

```bash
python -m inference.edge_optimizer --format tensorrt
```

### 4. Update config

Set in `configs/default.yaml`:

```yaml
inference:
  model_path: models/tensorrt/helmet_violation.engine
  device: 0
metadata:
  gps_port: /dev/ttyUSB0
```

### 5. Run inference service

```bash
python -m inference.pipeline --source 0
```

### 6. Sync violations to backend

Configure edge agent to POST violation JSON to `http://<server>:8000/api/v1/violations`.

## Docker Production Stack

```bash
docker compose up -d postgres backend frontend
```

Optional edge inference profile:

```bash
docker compose --profile edge up inference
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HELMET_DATABASE__URL` | Async PostgreSQL URL |
| `HELMET_BACKEND__SECRET_KEY` | API secret |
| `HELMET_METADATA__DEVICE_ID` | Edge device identifier |
| `HELMET_INFERENCE__MODEL_PATH` | Model weights path |

## WPOD-NET Model

Download pre-trained WPOD-NET weights and place at:

```
models/wpod/wpod-net.h5
```

The system falls back to contour-based plate detection if the model is unavailable.

## Monitoring

- TensorBoard: `tensorboard --logdir models/checkpoints`
- API health: `GET /health`
- Logs: `logs/app.log`

## Security Checklist

- [ ] Change `secret_key` in production
- [ ] Use HTTPS reverse proxy (nginx/traefik)
- [ ] Restrict database network access
- [ ] Do not commit `.env` or evidence files with PII
