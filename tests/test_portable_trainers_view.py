import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

from gui import portable_trainers_view as module


def make_view(monkeypatch):
    row = dict(id="one", game="frlg", game_version=None,
               profile=dict(ot="RED", tid=1, sid=2, gender=0, language=7))
    library = SimpleNamespace(entries=Mock(return_value=[row]), delete=Mock(),
        export_json=Mock(return_value=b'[{"schema":1}]'), import_json=Mock(return_value=1))
    monkeypatch.setattr(module, "TrainerLibrary", lambda setup: library)
    page = SimpleNamespace(web=False, show_dialog=Mock(), pop_dialog=Mock())
    view = module.TrainersView(SimpleNamespace(page=page, setup=object(), go=Mock()))
    return view, library, row


def test_search_and_game_filter_reach_existing_profiles(monkeypatch):
    view, library, _ = make_view(monkeypatch)
    view.query.value, view.game.value = "RED", "frlg"
    view.refresh()
    library.entries.assert_called_with("RED", "frlg")
    assert len(view.rows.controls) == 1


def test_delete_requires_confirmation(monkeypatch):
    view, library, row = make_view(monkeypatch)
    view.confirm_delete(row)
    library.delete.assert_not_called()
    dialog = view.page.show_dialog.call_args.args[0]
    dialog.actions[0].on_click(None)
    library.delete.assert_not_called()
    view.confirm_delete(row)
    view.page.show_dialog.call_args.args[0].actions[1].on_click(None)
    library.delete.assert_called_once_with("frlg", "one")


def test_individual_export_uses_game_folder_and_preserves_existing_file(monkeypatch, tmp_path):
    view, library, row = make_view(monkeypatch)
    view.picker = SimpleNamespace(get_directory_path=AsyncMock(return_value=str(tmp_path)))
    asyncio.run(view.export_one(row))
    path = tmp_path / module.export_filename(row)
    assert json.loads(path.read_bytes()) == [{"schema": 1}]
    path.write_bytes(b"existing")
    asyncio.run(view.export_one(row))
    assert path.read_bytes() == b"existing"
    assert "Ya existe" in view.message.value


def test_import_reads_array_and_refreshes(monkeypatch):
    view, library, _ = make_view(monkeypatch)
    view.picker = SimpleNamespace(pick_files=AsyncMock(return_value=[
        SimpleNamespace(size=2, bytes=b"[]", path=None)]))
    asyncio.run(view.import_json())
    library.import_json.assert_called_once_with(b"[]")
    assert "1 entrenadores nuevos" in view.message.value
