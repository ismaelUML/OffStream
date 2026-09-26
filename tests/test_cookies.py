import os
from pathlib import Path
from adapters.out_bound.cookies_helper import is_cookie_error, resolve_cookie_opts
from adapters.out_bound.ytdlp_resolver import YtDlpResolver


def test_resolve_cookie_opts_none():
    opts = resolve_cookie_opts(None)
    assert isinstance(opts, dict)


def test_resolve_cookie_opts_browser():
    opts = resolve_cookie_opts("chrome")
    assert opts.get("cookiesfrombrowser") == ("chrome", None, None, None)

    opts_firefox = resolve_cookie_opts("firefox")
    assert opts_firefox.get("cookiesfrombrowser") == ("firefox", None, None, None)


def test_resolve_cookie_opts_cookiefile(tmp_path, monkeypatch):
    test_file = tmp_path / "cookies.txt"
    test_file.write_text("# Netscape HTTP Cookie File\n")
    monkeypatch.chdir(tmp_path)

    opts = resolve_cookie_opts(None)
    assert opts.get("cookiefile") == str(test_file)


def test_is_cookie_error():
    assert is_cookie_error(Exception("Could not copy Chrome cookie database"))
    assert is_cookie_error(Exception("DPAPI decryption error"))
    assert is_cookie_error(Exception("cookie database locked"))
    assert not is_cookie_error(Exception("HTTP Error 404: Not Found"))
