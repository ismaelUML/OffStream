"""Unit tests for ResilientStreamResolver (Circuit Breaker / Failover)."""
import pytest
from core.circuit_breaker import ResilientStreamResolver
from domain.exceptions import ResolutionError
from domain.models import StreamFormat, VideoMetadata


class MockFailingResolver:
    def can_handle(self, url: str) -> bool:
        return True

    def resolve(self, url: str) -> VideoMetadata:
        raise RuntimeError("YouTube bot challenge triggered.")


class MockSuccessResolver:
    def can_handle(self, url: str) -> bool:
        return True

    def resolve(self, url: str) -> VideoMetadata:
        return VideoMetadata(
            video_id="dQw4w9WgXcQ",
            raw_title="Never Gonna Give You Up",
            clean_title="Never Gonna Give You Up",
            uploader="Rick Astley",
            duration_seconds=212,
            thumbnail_url="http://thumb.jpg",
            formats=[
                StreamFormat(format_id="18", extension="mp4", url="http://stream.mp4", is_video=True, is_audio=True)
            ],
        )


def test_circuit_breaker_fails_over_to_secondary():
    primary = MockFailingResolver()
    secondary = MockSuccessResolver()

    router = ResilientStreamResolver([primary, secondary])
    meta = router.resolve("dQw4w9WgXcQ")

    assert meta.video_id == "dQw4w9WgXcQ"
    assert meta.uploader == "Rick Astley"


def test_circuit_breaker_all_fail_raises_resolution_error():
    primary = MockFailingResolver()
    secondary = MockFailingResolver()

    router = ResilientStreamResolver([primary, secondary])
    with pytest.raises(ResolutionError) as exc_info:
        router.resolve("dQw4w9WgXcQ")

    assert "All stream resolvers exhausted" in str(exc_info.value)
