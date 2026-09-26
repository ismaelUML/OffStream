"""Unit tests for LocalStorageAdapter."""
from pathlib import Path
import tempfile
from adapters.out_bound.local_storage import LocalStorageAdapter


def test_local_storage_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageAdapter(base_output_dir=tmpdir)
        path1 = storage.get_output_path("song.mp3", is_audio=True)
        assert Path(path1).name == "song.mp3"

        # Simulating file existence on disk
        Path(path1).touch()

        # Second request with same name should append (1)
        path2 = storage.get_output_path("song.mp3", is_audio=True)
        assert Path(path2).name == "song (1).mp3"

        Path(path2).touch()

        # Third request should append (2)
        path3 = storage.get_output_path("song.mp3", is_audio=True)
        assert Path(path3).name == "song (2).mp3"
