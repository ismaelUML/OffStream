from gui import _compute_pipeline_display, _format_duration, _truncate_title


def test_format_duration():
    assert _format_duration(0) == "0:00"
    assert _format_duration(45) == "0:45"
    assert _format_duration(65) == "1:05"
    assert _format_duration(3665) == "1:01:05"


def test_truncate_title():
    short_title = "Short Title"
    assert _truncate_title(short_title, max_chars=20) == "Short Title"

    long_title = "This is a very long video title that needs to be truncated cleanly"
    truncated = _truncate_title(long_title, max_chars=25)
    assert len(truncated) <= 25
    assert truncated.endswith("...")


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
