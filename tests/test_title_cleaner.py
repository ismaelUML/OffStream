"""Unit tests for title cleaning and filename sanitization."""
from core.title_cleaner import clean_title, sanitize_filename


def test_clean_title_removes_noise_tags():
    raw_1 = "Never Gonna Give You Up (Official Music Video)"
    assert clean_title(raw_1) == "Never Gonna Give You Up"

    raw_2 = "Queen - Bohemian Rhapsody [4K 60FPS HD]"
    assert clean_title(raw_2) == "Queen - Bohemian Rhapsody"

    raw_3 = "Linkin Park - In The End (Lyrics Video)"
    assert clean_title(raw_3) == "Linkin Park - In The End"


def test_sanitize_filename_removes_windows_forbidden_chars():
    dirty_name = 'Artist: Song "Title" <Remix> | Part 1 / 2 ? *'
    safe_name = sanitize_filename(dirty_name)
    for bad_char in '<>:"/\\|?*':
        assert bad_char not in safe_name
    assert "Artist_ Song _Title_ _Remix_ _ Part 1 _ 2" in safe_name
