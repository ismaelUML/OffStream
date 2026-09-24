"""Unit tests for pure domain models."""
from domain.models import (
    DownloadJob,
    JobStatus,
    MediaKind,
    QualityTarget,
    StreamFormat,
    VideoMetadata,
)


def test_download_job_lifecycle():
    job = DownloadJob(
        job_id="test-123",
        source_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        target_kind=MediaKind.VIDEO,
        target_quality=QualityTarget.BEST,
    )
    assert job.status == JobStatus.PENDING
    assert job.progress_percentage == 0.0

    job.update_progress(45.5)
    assert job.progress_percentage == 45.5

    # Out of bounds progress clamping
    job.update_progress(150.0)
    assert job.progress_percentage == 100.0

    job.mark_completed("C:/downloads/video.mp4")
    assert job.status == JobStatus.COMPLETED
    assert job.output_path == "C:/downloads/video.mp4"
    assert job.completed_at is not None


def test_download_job_failure():
    job = DownloadJob(
        job_id="test-err",
        source_url="https://youtube.com/watch?v=invalid",
        target_kind=MediaKind.AUDIO,
        target_quality=QualityTarget.AUDIO_HIGH,
    )
    job.mark_failed("Network timeout")
    assert job.status == JobStatus.FAILED
    assert job.error_message == "Network timeout"


def test_stream_format_dataclass():
    stream = StreamFormat(
        format_id="137",
        extension="mp4",
        url="https://googlevideo.com/123",
        bitrate=2500000,
        resolution="1080p",
        is_video=True,
        is_audio=False,
    )
    assert stream.resolution == "1080p"
    assert stream.is_video is True
    assert stream.is_audio is False
