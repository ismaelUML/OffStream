"""Unit tests for GUI display formatting helpers."""
from gui import _compute_pipeline_display


def test_compute_pipeline_display_idle_empty():
    progress, text, color = _compute_pipeline_display([], is_active_bar=False)
    assert progress == 0.0
    assert text == "Ready for download"
    assert color == "#a1a1aa"


def test_compute_pipeline_display_active_jobs():
    jobs = [
        {"job_id": "1", "status": "completed", "progress_percentage": 100.0},
        {"job_id": "2", "status": "downloading", "progress_percentage": 65.5},
    ]
    progress, text, color = _compute_pipeline_display(jobs, is_active_bar=True)
    assert progress == 0.655
    assert "DOWNLOADING" in text
    assert "66%" in text or "65%" in text
    assert color == "#60a5fa"


def test_compute_pipeline_display_completed():
    jobs = [
        {"job_id": "1", "status": "completed", "progress_percentage": 100.0},
    ]
    progress, text, color = _compute_pipeline_display(jobs, is_active_bar=True)
    assert progress == 1.0
    assert "Ready (All downloads finished)" in text
    assert color == "#34d399"


def test_compute_pipeline_display_failed():
    jobs = [
        {"job_id": "1", "status": "failed", "error_message": "Network Timeout"},
    ]
    progress, text, color = _compute_pipeline_display(jobs, is_active_bar=True)
    assert progress == 1.0
    assert "Network Timeout" in text
    assert color == "#f87171"
