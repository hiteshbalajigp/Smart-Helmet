import numpy as np

from app.evidence.manager import EvidenceManager


def test_save_original_and_annotated(tmp_path, monkeypatch) -> None:
    manager = EvidenceManager()
    monkeypatch.setattr(manager, "original_dir", tmp_path / "evidence")
    monkeypatch.setattr(manager, "annotated_dir", tmp_path / "annotated")

    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    annotated = np.ones((120, 160, 3), dtype=np.uint8) * 255

    original_path, annotated_path, checksum = manager.save_from_array(
        camera_id="CAM-01",
        event_id="event-1",
        frame=frame,
        annotated_frame=annotated,
    )

    assert original_path is not None
    assert annotated_path is not None
    assert checksum
    assert (tmp_path / "evidence").exists()
