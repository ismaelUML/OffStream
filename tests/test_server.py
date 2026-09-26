"""Integration tests for FastAPI server adapter."""
from fastapi.testclient import TestClient
from adapters.in_bound.server import app, manager
from domain.models import DownloadJob, JobStatus, MediaKind, QualityTarget


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "yt-global-dl"


def test_cors_security_policy():
    # Chrome extension origin should be permitted
    res_chrome = client.options(
        "/api/jobs",
        headers={
            "Origin": "chrome-extension://abcdefghijklmnop",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_chrome.headers.get("access-control-allow-origin") == "chrome-extension://abcdefghijklmnop"

    # Localhost dev origins should be permitted
    res_local = client.options(
        "/api/jobs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # External internet web origin MUST be blocked by CORS
    res_evil = client.options(
        "/api/jobs",
        headers={
            "Origin": "https://malicious-phishing-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in res_evil.headers


def test_list_and_cancel_jobs_endpoints():
    # Seed a test job into manager
    job = DownloadJob(
        job_id="test_api_1",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        target_kind=MediaKind.VIDEO,
        target_quality=QualityTarget.BEST,
        status=JobStatus.DOWNLOADING,
    )
    with manager._lock:
        manager._jobs["test_api_1"] = job

    # Verify listing
    res = client.get("/api/jobs")
    assert res.status_code == 200
    jobs = res.json()
    assert any(j["job_id"] == "test_api_1" for j in jobs)

    # Cancel the active job
    res_del = client.delete("/api/jobs/test_api_1")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "cancelled"

    # Clear finished jobs
    res_clear = client.post("/api/jobs/clear")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "ok"
    assert "test_api_1" not in manager._jobs
