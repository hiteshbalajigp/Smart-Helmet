"""Unit tests for evidence buffer."""

import numpy as np

from inference.evidence_capture import CircularEvidenceBuffer, EvidenceCapture


def test_circular_buffer_maxlen():
    buffer = CircularEvidenceBuffer(fps=10, seconds_before=1)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    for _ in range(20):
        buffer.append(frame)
    assert len(buffer.get_before_frames()) == 10


def test_save_violation_evidence(tmp_path):
    capture = EvidenceCapture(output_dir=str(tmp_path), fps=10, seconds_before=1, seconds_after=0)
    frame = np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)
    capture.update(frame)
    paths = capture.save_violation_evidence("test-violation", frame)
    assert paths["snapshot"]
    assert paths["video"]
