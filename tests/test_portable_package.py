"""Portable package startup must select its profile before paths/settings imports."""
import os
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("explicit_data", [None, "/tmp/portable-custom-data"])
def test_runtime_profile_is_native_and_preserves_explicit_data(monkeypatch, explicit_data):
    monkeypatch.setenv("POKELDN_PORTABLE", "0")
    monkeypatch.setenv("FLET_VIEW_PATH", "/tmp/another-client")
    monkeypatch.setenv("FLET_SERVER_IP", "0.0.0.0")
    monkeypatch.delenv("FLET_SERVER_PORT", raising=False)
    for key in ("POKELDN_GUI_WEB", "FLET_FORCE_WEB_SERVER", "POKELDN_PORTABLE_DEMO"):
        monkeypatch.setenv(key, "1")
    if explicit_data:
        monkeypatch.setenv("POKELDN_DATA", explicit_data)
    else:
        monkeypatch.delenv("POKELDN_DATA", raising=False)
    runpy.run_path(str(ROOT / "scripts/portable_runtime.py"))
    assert os.environ["POKELDN_PORTABLE"] == "1"
    assert "FLET_VIEW_PATH" not in os.environ
    assert os.environ["FLET_SERVER_IP"] == "127.0.0.1"
    assert os.environ["FLET_SERVER_PORT"] == "8590"
    assert all(key not in os.environ for key in
               ("POKELDN_GUI_WEB", "FLET_FORCE_WEB_SERVER", "POKELDN_PORTABLE_DEMO"))
    if explicit_data:
        assert os.environ["POKELDN_DATA"] == explicit_data
    else:
        assert "POKELDN_DATA" not in os.environ  # Main resolves storage before importing paths.


def test_portable_icon_included_even_before_git_add(monkeypatch):
    import scripts.pack_app as pack
    monkeypatch.setattr(pack.subprocess, "check_output", lambda *args, **kwargs: b"LICENSE\0")
    assert "gui/assets/portable/icon.png" in pack.runtime_files(portable=True)
    assert "gui/assets/portable/icon.png" not in pack.runtime_files()


def test_standard_frozen_client_disables_file_drop(monkeypatch, tmp_path):
    import sys
    from gui import drop
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("POKELDN_GUI_WEB", raising=False)
    monkeypatch.setattr(drop, "read_any_compression", lambda: None)
    monkeypatch.setattr(drop, "AVAILABLE", False)
    (tmp_path / "portable-standard-client").touch()
    assert drop.use_client() is False
    (tmp_path / "portable-standard-client").unlink()
    assert drop.use_client() is True
