"""Unit tests for DownloadManager and Little's Law queue limits."""
import pytest
from core.download_manager import DownloadManager
from domain.exceptions import QueueFullError
from domain.models import DownloadJob, JobStatus, MediaKind, QualityTarget, StreamFormat, VideoMetadata


class DummyResolver:
    def can_handle(self, url: str) -> bool:
        return True

    def resolve(self, url: str) -> VideoMetadata:
        return VideoMetadata(
            video_id="dummy123",
            raw_title="Dummy Media",
            clean_title="Dummy Media",
            uploader="Dummy",
            duration_seconds=100,
            thumbnail_url="http://dummy.jpg",
            formats=[
                StreamFormat(format_id="140", extension="m4a", url="http://audio", is_audio=True, is_video=False),
                StreamFormat(format_id="137", extension="mp4", url="http://video", is_audio=False, is_video=True),
            ],
        )


class DummyDownloader:
    def download_stream(self, stream, output_path, progress_callback=None):
        if progress_callback:
            progress_callback(100.0)
        return output_path


class DummyProcessor:
    def mux_video_audio(self, video_path, audio_path, output_path):
        return output_path

    def convert_to_mp3(self, source_audio_path, output_path):
        return output_path


class DummyStorage:
    def get_output_path(self, filename, is_audio=False):
        return f"C:/out/{filename}"

    def create_temp_path(self, prefix, ext):
        return f"C:/temp/{prefix}.{ext}"

    def remove_files(self, paths):
        pass


def test_download_manager_queue_limit_littles_law():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        max_workers=1,
        max_queue_size=2,
    )

    # Fill queue to maximum capacity
    j1 = DownloadJob("1", "url1", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.DOWNLOADING)
    j2 = DownloadJob("2", "url2", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.PENDING)
    manager._jobs["1"] = j1
    manager._jobs["2"] = j2

    # A third request should be rejected by Little's Law capacity guard
    with pytest.raises(QueueFullError):
        manager.queue_download("url3", MediaKind.VIDEO, QualityTarget.BEST)


def test_download_manager_cancel_job():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        max_workers=1,
    )
    job = DownloadJob("job1", "url1", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.DOWNLOADING)
    manager._jobs["job1"] = job

    assert manager.cancel_job("job1") is True
    assert job.status == JobStatus.CANCELLED

    # Cancelling already finished/cancelled job should return False
    assert manager.cancel_job("job1") is False


def test_download_manager_clear_finished():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        max_workers=1,
    )
    manager._jobs["1"] = DownloadJob("1", "url1", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.COMPLETED)
    manager._jobs["2"] = DownloadJob("2", "url2", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.DOWNLOADING)
    manager._jobs["3"] = DownloadJob("3", "url3", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.FAILED)

    cleared = manager.clear_finished_jobs()
    assert cleared == 2
    assert "1" not in manager._jobs
    assert "3" not in manager._jobs
    assert "2" in manager._jobs


def test_download_manager_history_eviction():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        max_workers=1,
        max_history=2,
    )
    for i in range(5):
        jid = f"done_{i}"
        manager._jobs[jid] = DownloadJob(
            jid, f"url_{i}", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.COMPLETED
        )

    # Pruning keeps only the most recent max_history completed jobs
    with manager._lock:
        manager._prune_history_locked()

    assert len(manager._jobs) == 2
    assert "done_3" in manager._jobs
    assert "done_4" in manager._jobs

