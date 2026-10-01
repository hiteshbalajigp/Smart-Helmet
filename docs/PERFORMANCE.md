# Performance Evaluation

## Metrics

### Detection (YOLOv8)

| Metric | Description | Target |
|--------|-------------|--------|
| Precision | TP / (TP + FP) | ≥ 0.90 |
| Recall | TP / (TP + FN) | ≥ 0.90 |
| mAP@0.5 | COCO-style at IoU 0.5 | ≥ 0.85 |
| mAP@0.5:0.95 | Primary COCO metric | ≥ 0.65 |

Metrics exported to `models/checkpoints/helmet_violation_yolov8m/metrics_summary.json`.

### System Latency

Benchmark with:

```bash
python -m inference.edge_optimizer --format benchmark
```

| Stage | Laptop GPU (FP16 TRT) | Jetson Orin Nano |
|-------|----------------------|------------------|
| YOLO inference | ~15–25 ms | ~25–40 ms |
| Tracking | ~2 ms | ~3 ms |
| WPOD + OCR | ~30–50 ms | ~50–80 ms |
| **Total** | ~50–80 ms | ~80–120 ms |

Target: ≥ 10 FPS sustained on edge hardware.

### Memory

- Circular buffer: ~10s × 30 FPS × frame size (e.g. 640×480×3 ≈ 270 MB max)
- Model weights: YOLOv8m ~50 MB, TensorRT FP16 ~25 MB

## Optimization Techniques

1. **AMP training** — faster convergence, lower VRAM
2. **Cosine LR** — stable fine-tuning with transfer learning
3. **ByteTrack** — identity persistence, reduced duplicate violations
4. **Violation cooldown** — 10s default per track_id
5. **TensorRT FP16** — ~2× inference speedup on NVIDIA hardware
6. **Evidence on violation only** — disk I/O minimized

## Error Analysis Workflow

1. Run validation on held-out test set
2. Export confusion matrix from training run
3. Bucket false positives by scene (night, rain, occlusion)
4. Add targeted samples to dataset
5. Retrain with early stopping (patience=30)

## Dataset Quality (Primary Accuracy Driver)

For 95%+ deployment accuracy:

- 10,000–20,000 labeled frames from Indian roads
- Same chin-mounted 90° viewpoint as production
- Balanced helmet / no_helmet / multi-rider scenes
- Include monsoon, shadow, and night conditions

Model architecture alone cannot compensate for insufficient or biased data.
