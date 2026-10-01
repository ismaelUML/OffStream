import pytest
from domain.exceptions import QueueFullError
from domain.models import (
    DownloadJob,
    JobStatus,
    MediaKind,
    QualityTarget,
    StreamFormat,
    VideoMetadata,
)
from core.download_manager import DownloadManager


class DummyResolver:
    def can_handle(self, url):
        return True

    def resolve(self, url):
        return VideoMetadata(
            video_id="test1234567",
            raw_title="Test Video [HD]",
            clean_title="Test Video",
            uploader="Test Channel",
            duration_seconds=120,
            thumbnail_url="http://example.com/thumb.jpg",
            formats=[
                StreamFormat("1", "mp4", "http://example.com/v.mp4", is_video=True, is_audio=False),
                StreamFormat("2", "m4a", "http://example.com/a.m4a", is_video=False, is_audio=True),
            ],
        )


class DummyDownloader:
    can_download_direct = True

    def download_stream(self, stream, output_path, progress_callback=None):
        if progress_callback:
            progress_callback(100.0)
        return output_path

    def download_direct(self, url, output_path, is_audio=False, quality=None, progress_callback=None, is_cancelled=None):
        if progress_callback:
            progress_callback(100.0)
        return output_path


class DummyProcessor:
    def mux_video_audio(self, video_path, audio_path, output_path, title="", artist=""):
        return output_path

    def convert_to_mp3(self, source_audio_path, output_path, title="", artist=""):
        return output_path


class DummyStorage:
    def get_output_path(self, filename, is_audio=False):
        return f"/tmp/{filename}"

    def create_temp_path(self, prefix, ext):
        return f"/tmp/{prefix}.{ext}"

    def remove_files(self, paths):
        pass


def test_download_audio_pipeline():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        max_workers=2,
    )
    job = manager.queue_download("https://youtu.be/test1234567", MediaKind.AUDIO, QualityTarget.AUDIO_HIGH)
    assert job is not None
    assert job.target_kind == MediaKind.AUDIO


def test_download_video_pipeline():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        max_workers=2,
    )
    job = manager.queue_download("https://youtu.be/test1234567", MediaKind.VIDEO, QualityTarget.P720)
    assert job is not None
    assert job.target_kind == MediaKind.VIDEO


def test_queue_full_capacity():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        max_queue_size=1,
    )
    manager._jobs["existing"] = DownloadJob("existing", "url", MediaKind.VIDEO, QualityTarget.BEST, status=JobStatus.DOWNLOADING)
    with pytest.raises(QueueFullError):
        manager.queue_download("https://youtu.be/test1234567", MediaKind.VIDEO, QualityTarget.BEST)


def test_events_subscription_lifecycle():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
    )
    q = manager.subscribe_events()
    assert q in manager._listeners

    job = DownloadJob("job1", "url", MediaKind.VIDEO, QualityTarget.BEST)
    manager._broadcast_job_event(job)
    event = q.get_nowait()
    assert event["type"] == "job_update"
    assert event["job_id"] == "job1"

    manager.unsubscribe_events(q)
    assert q not in manager._listeners


class FallbackDownloader:
    can_download_direct = False

    def download_stream(self, stream, output_path, progress_callback=None, is_cancelled=None):
        if progress_callback:
            progress_callback(100.0)
        return output_path


class DummyHistoryRepo:
    def __init__(self):
        self.records = {}
        self._next_id = 1

    def add_record(self, record):
        from domain.models import DownloadRecord
        rec = DownloadRecord(
            id=self._next_id,
            video_id=record.video_id,
            title=record.title,
            channel=record.channel,
            duration_seconds=record.duration_seconds,
            created_at=record.created_at,
            file_path=record.file_path,
            media_kind=record.media_kind,
        )
        self.records[self._next_id] = rec
        self._next_id += 1
        return rec.id

    def get_record(self, record_id):
        return self.records.get(record_id)

    def list_records(self, limit=100, query=None):
        return list(self.records.values())[:limit]

    def delete_record(self, record_id):
        return self.records.pop(record_id, None) is not None

    def clear_all(self):
        count = len(self.records)
        self.records.clear()
        return count


def test_fallback_audio_pipeline():
    history = DummyHistoryRepo()
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=FallbackDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        history_repo=history,
        max_workers=1,
    )
    job = DownloadJob("audio_fallback", "https://youtu.be/test1234567", MediaKind.AUDIO, QualityTarget.AUDIO_HIGH)
    manager._run_job_lifecycle(job)
    assert job.status == JobStatus.COMPLETED
    assert len(history.records) == 1
    assert manager.get_history_record(1) is not None


def test_fallback_video_pipeline():
    history = DummyHistoryRepo()
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=FallbackDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        history_repo=history,
        max_workers=1,
    )
    job = DownloadJob("video_fallback", "https://youtu.be/test1234567", MediaKind.VIDEO, QualityTarget.BEST)
    manager._run_job_lifecycle(job)
    assert job.status == JobStatus.COMPLETED
    assert len(history.records) == 1


def test_direct_download_cancellation():
    from domain.exceptions import JobCancelledError

    class CancellingDownloader:
        can_download_direct = True

        def download_direct(self, url, output_path, is_audio=False, quality=None, progress_callback=None, is_cancelled=None):
            raise JobCancelledError("Cancelled in test")

    class TrackingStorage(DummyStorage):
        def __init__(self):
            self.removed = []

        def remove_files(self, paths):
            self.removed.extend(paths)

    storage = TrackingStorage()
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=CancellingDownloader(),
        processor=DummyProcessor(),
        storage=storage,
    )
    job = DownloadJob("cancel_audio", "https://youtu.be/test1234567", MediaKind.AUDIO, QualityTarget.AUDIO_HIGH)
    manager._run_job_lifecycle(job)
    assert job.status == JobStatus.CANCELLED
    assert len(storage.removed) > 0


def test_history_delegation_and_empty_repo():
    manager = DownloadManager(
        resolver=DummyResolver(),
        downloader=DummyDownloader(),
        processor=DummyProcessor(),
        storage=DummyStorage(),
        history_repo=None,
    )
    assert manager.get_history() == []
    assert manager.get_history_record(1) is None
    assert manager.delete_history_record(1) is False
    assert manager.clear_history() == 0
