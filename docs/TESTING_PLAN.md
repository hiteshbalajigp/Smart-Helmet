# Testing Plan

## Scope

| Layer | Coverage Target | Tool |
|-------|-----------------|------|
| Utils (geometry) | 100% critical paths | pytest |
| Violation rules | All rule branches | pytest |
| OCR validation | Indian plate regex | pytest |
| Evidence buffer | Buffer + save | pytest |
| FastAPI | All endpoints | pytest + httpx |
| Frontend | Smoke manual | Browser |

## Unit Tests

```bash
pytest tests/unit -v
```

### Cases

1. **Geometry**: IoU, clipping, rider-motorcycle association
2. **ViolationDetector**: Triple riding (>2 riders), no helmet, cooldown dedup
3. **PlateOCR**: Regex validation, character correction
4. **EvidenceCapture**: Circular buffer maxlen, JPEG/MP4 output

## Integration Tests

```bash
pytest tests/integration -v
```

### Cases

1. Health check endpoint
2. Create violation → list → search → stats
3. Evidence download (404 when missing)

## Manual / Field Tests

1. **Daylight**: Highway and urban traffic, varied density
2. **Night**: Headlight glare, low-light augmentation validation
3. **Rain**: Windshield/rain droplet occlusion
4. **Angle**: Chin-mount 90° consistency with training data
5. **Tracking**: Same motorcycle not double-counted within cooldown

## Regression Checklist

- [ ] mAP@0.5 ≥ target after retrain
- [ ] False positive rate on non-violations
- [ ] End-to-end latency ≤ 100ms/frame on target hardware
- [ ] Evidence files saved only on violations
- [ ] GPS metadata attached when hardware present

## CI Recommendation

```yaml
# .github/workflows/test.yml
- pip install -r requirements.txt -r requirements-dev.txt
- pytest tests/ --cov --cov-fail-under=70
```
