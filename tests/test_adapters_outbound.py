import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from adapters.out_bound.ffmpeg_processor import FFmpegProcessorAdapter
from adapters.out_bound.http_downloader import HttpStreamingDownloader
from adapters.out_bound.local_storage import LocalStorageAdapter
from adapters.out_bound.ytdlp_resolver import YtDlpResolver
from domain.exceptions import MuxingError, StreamNotFoundError
from domain.models import StreamFormat


def test_local_storage_filename_collision():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageAdapter(base_output_dir=tmpdir)
        p1 = storage.get_output_path("test_song.mp3", is_audio=True)
        # Create the file to trigger collision
        with open(p1, "w") as f:
            f.write("content")

        p2 = storage.get_output_path("test_song.mp3", is_audio=True)
        assert p2 != p1
        assert "(1)" in p2

        temp_file = storage.create_temp_path("test_chunk", "mp4")
        assert "test_chunk" in temp_file
        storage.remove_files([p1, temp_file])


def test_ffmpeg_processor_muxing():
    processor = FFmpegProcessorAdapter()
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        out = processor.mux_video_audio("video.mp4", "audio.m4a", "output.mp4", title="My Title", artist="My Artist")
        assert out == "output.mp4"
        cmd = mock_run.call_args[0][0]
        assert "-metadata" in cmd
        assert "title=My Title" in cmd
        assert "artist=My Artist" in cmd

        out_mp3 = processor.convert_to_mp3("audio.m4a", "output.mp3", title="Song", artist="Band")
        assert out_mp3 == "output.mp3"
        cmd_mp3 = mock_run.call_args[0][0]
        assert "-metadata" in cmd_mp3
        assert "title=Song" in cmd_mp3
        assert "artist=Band" in cmd_mp3

        mock_proc.returncode = 1
        mock_proc.stderr = "FFmpeg error message"
        with pytest.raises(MuxingError):
            processor.mux_video_audio("video.mp4", "audio.m4a", "output.mp4")


def test_http_downloader_stream():
    downloader = HttpStreamingDownloader()
    stream = StreamFormat(format_id="1", extension="mp4", url="")
    with pytest.raises(StreamNotFoundError):
        downloader.download_stream(stream, "dummy.mp4")

    valid_stream = StreamFormat(format_id="2", extension="mp4", url="http://example.com/video.mp4")
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tmp_name = tf.name

    try:
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content = MagicMock(return_value=[b"chunk1", b"chunk2"])
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(downloader._session, "get", return_value=mock_response):
            progress_values = []
            downloader.download_stream(valid_stream, tmp_name, progress_callback=lambda p: progress_values.append(p))
            assert len(progress_values) > 0
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_http_downloader_cancellation():
    from domain.exceptions import JobCancelledError
    downloader = HttpStreamingDownloader()
    stream = StreamFormat(format_id="2", extension="mp4", url="http://example.com/video.mp4")
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tmp_name = tf.name

    try:
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content = MagicMock(return_value=[b"chunk1", b"chunk2"])
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(downloader._session, "get", return_value=mock_response):
            with pytest.raises(JobCancelledError):
                downloader.download_stream(
                    stream,
                    tmp_name,
                    is_cancelled=lambda: True,
                )
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_ytdlp_resolver_format_parsing():
    raw_formats = [
        {
            "format_id": "137",
            "ext": "mp4",
            "url": "http://example.com/1080p.mp4",
            "height": 1080,
            "tbr": 4000,
            "vcodec": "avc1",
            "acodec": "none",
        },
        {
            "format_id": "140",
            "ext": "m4a",
            "url": "http://example.com/audio.m4a",
            "abr": 128,
            "vcodec": "none",
            "acodec": "mp4a",
        },
    ]
    resolver = YtDlpResolver()
    parsed = resolver._extract_formats(raw_formats)
    assert len(parsed) == 2
    assert parsed[0].is_video is True
    assert parsed[0].is_audio is False
    assert parsed[1].is_audio is True
