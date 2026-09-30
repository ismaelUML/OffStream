from fastapi.testclient import TestClient
from adapters.in_bound.server import app, manager
from domain.models import DownloadJob, JobStatus, MediaKind, QualityTarget

client = TestClient(app)


def test_get_job_status():
    job = DownloadJob(
        job_id="job_status_test",
        source_url="http://example.com/test",
        target_kind=MediaKind.VIDEO,
        target_quality=QualityTarget.BEST,
        status=JobStatus.RESOLVING,
        progress_percentage=25.0,
    )
    with manager._lock:
        manager._jobs["job_status_test"] = job

    res = client.get("/api/jobs/job_status_test")
    assert res.status_code == 200
    assert res.json()["status"] == "resolving"
    assert res.json()["progress_percentage"] == 25.0

    res_404 = client.get("/api/jobs/nonexistent_job")
    assert res_404.status_code == 404


def test_cancel_job_edge_cases():
    res_404 = client.delete("/api/jobs/nonexistent_job")
    assert res_404.status_code == 404

    completed_job = DownloadJob(
        job_id="job_completed_test",
        source_url="http://example.com/test",
        target_kind=MediaKind.VIDEO,
        target_quality=QualityTarget.BEST,
        status=JobStatus.COMPLETED,
    )
    with manager._lock:
        manager._jobs["job_completed_test"] = completed_job

    res_400 = client.delete("/api/jobs/job_completed_test")
    assert res_400.status_code == 400


def test_history_clear_and_missing_delete():
    res_404 = client.delete("/api/history/99999999")
    assert res_404.status_code == 404

    res_clear = client.post("/api/history/clear")
    assert res_clear.status_code == 200
    assert "cleared_count" in res_clear.json()


def test_inspect_video_error_handling():
    res_bad = client.post("/api/inspect", json={"url": "not_a_valid_url"})
    assert res_bad.status_code == 400
