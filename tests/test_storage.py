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


def test_configure_windows_folder_win32():
    from unittest.mock import MagicMock, patch
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir) / "fresh_folder"
        folder.mkdir()
        storage = LocalStorageAdapter(base_output_dir=tmpdir)
        mock_windll = MagicMock()
        with patch("sys.platform", "win32"), patch("ctypes.windll", mock_windll, create=True):
            storage._configure_windows_folder(folder, "Music")
            ini_file = folder / "desktop.ini"
            assert ini_file.exists()
            assert "FolderType=Music" in ini_file.read_text(encoding="utf-8")
            assert mock_windll.kernel32.SetFileAttributesW.call_count == 2

            # Calling again should not re-write or fail
            storage._configure_windows_folder(folder, "Music")


def test_configure_windows_folder_non_win32():
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir) / "custom"
        folder.mkdir()
        storage = LocalStorageAdapter(base_output_dir=tmpdir)
        with patch("sys.platform", "darwin"):
            storage._configure_windows_folder(folder, "Music")
            assert not (folder / "desktop.ini").exists()


def test_configure_windows_folder_os_error_resilience():
    from unittest.mock import MagicMock, patch
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir) / "failing"
        folder.mkdir()
        storage = LocalStorageAdapter(base_output_dir=tmpdir)
        mock_windll = MagicMock()
        mock_windll.kernel32.SetFileAttributesW.side_effect = OSError("Access denied")
        with patch("sys.platform", "win32"), patch("ctypes.windll", mock_windll, create=True):
            # Should not raise exception
            storage._configure_windows_folder(folder, "Videos")

