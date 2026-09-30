from bootstrap import build_default_manager
from core.download_manager import DownloadManager


def test_bootstrap_build_default_manager():
    manager = build_default_manager()
    assert isinstance(manager, DownloadManager)
