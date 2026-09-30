from unittest.mock import MagicMock
import pytest
from adapters.out_bound.fast_downloader import FastMediaDownloader
from adapters.out_bound.innertube_resolver import InnerTubeResolver
from domain.exceptions import JobCancelledError, StreamNotFoundError
from domain.models import QualityTarget, StreamFormat
from fastapi.testclient import TestClient
from adapters.in_bound.server import app

client = TestClient(app)


def test_fast_downloader_opts():
    downloader = FastMediaDownloader()
    opts = downloader._build_opts("test.mp4", callback=None)
    assert opts["outtmpl"] == "test.mp4"
    assert opts["quiet"] is True

    direct_opts = downloader._build_direct_opts("test.mp3", is_audio=True, quality=QualityTarget.AUDIO_HIGH, callback=None)
    assert "FFmpegExtractAudio" in [p["key"] for p in direct_opts["postprocessors"]]

    video_720_opts = downloader._build_direct_opts("test.mp4", is_audio=False, quality=QualityTarget.P720, callback=None)
    assert "720" in video_720_opts["format"]

    video_best_opts = downloader._build_direct_opts("test.mp4", is_audio=False, quality=QualityTarget.BEST, callback=None)
    assert "bestvideo" in video_best_opts["format"]


def test_fast_downloader_progress_hook():
    downloader = FastMediaDownloader()
    calls = []
    hook = downloader._make_progress_hook(callback=lambda p: calls.append(p), is_cancelled=lambda: False)

    hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
    assert len(calls) == 1
    assert calls[0] == 50.0

    cancelled_hook = downloader._make_progress_hook(callback=None, is_cancelled=lambda: True)
    with pytest.raises(JobCancelledError):
        cancelled_hook({"status": "downloading"})


def test_innertube_resolver_helpers():
    resolver = InnerTubeResolver()
    assert resolver._detect_extension("video/mp4", is_audio=False) == "mp4"
    assert resolver._detect_extension("audio/mp4", is_audio=True) == "m4a"
    assert resolver._detect_extension("video/webm", is_audio=False) == "webm"

    raw_item = {
        "itag": 18,
        "url": "http://example.com/stream.mp4",
        "mimeType": 'video/mp4; codecs="avc1.42001E, mp4a.40.2"',
        "bitrate": 500000,
        "qualityLabel": "360p",
        "contentLength": "12345",
    }
    parsed = resolver._parse_single_item(raw_item)
    assert parsed is not None
    assert parsed.format_id == "18"
    assert parsed.is_video is True

    # Empty url should return None
    assert resolver._parse_single_item({}) is None


def test_server_queue_download_endpoint():
    res = client.post(
        "/api/download",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "kind": "video", "quality": "best"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["status"] in ("pending", "resolving", "downloading")
