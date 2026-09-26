"""Integration tests for FastAPI server adapter."""
import pytest
from fastapi.testclient import TestClient
from adapters.in_bound.server import app, manager, stream_events
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


@pytest.fixture
def seeded_history_record():
    from domain.models import DownloadRecord
    rec = DownloadRecord(
        id=None,
        video_id="hist123",
        title="Daft Punk - One More Time",
        channel="Daft Punk",
        duration_seconds=320,
        created_at="2026-09-25T12:00:00",
        file_path="C:/nonexistent/path/song.mp3",
        media_kind="audio",
    )
    return manager._history_repo.add_record(rec)


def test_history_query_and_file_status(seeded_history_record):
    res = client.get("/api/history?query=Daft")
    assert res.status_code == 200
    data = res.json()
    matched = next((r for r in data if r["video_id"] == "hist123"), None)
    assert matched is not None
    assert matched["file_exists"] is False


def test_history_open_missing_file_410(seeded_history_record):
    res_open = client.post(f"/api/history/{seeded_history_record}/open")
    assert res_open.status_code == 410


def test_history_delete_endpoint(seeded_history_record):
    res_del = client.delete(f"/api/history/{seeded_history_record}")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "ok"


@pytest.mark.anyio
async def test_events_sse_endpoint():
    res = await stream_events()
    assert res.media_type == "text/event-stream"
    gen = res.body_iterator
    first_chunk = await anext(gen)
    assert "connected" in first_chunk
    await gen.aclose()


