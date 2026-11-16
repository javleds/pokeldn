import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import flet as ft

from gui import portable_data_picker as picker


class DataLocationError(Exception):
    pass


class ChoiceRequired(DataLocationError):
    def __init__(self, candidates):
        self.candidates = candidates


def engine(monkeypatch):
    stub = SimpleNamespace(resolve=Mock(), save_choice=Mock(),
                           DataLocationError=DataLocationError, ChoiceRequired=ChoiceRequired)
    monkeypatch.setitem(sys.modules, 'pokeldn.app.portable_data', stub)
    import pokeldn.app
    monkeypatch.setattr(pokeldn.app, 'portable_data', stub, raising=False)
    return stub


def page():
    return SimpleNamespace(fonts={}, add=Mock(), update=Mock(),
                           window=SimpleNamespace(destroy=AsyncMock()))


def test_unambiguous_resolution_does_not_open_window_or_save_override(monkeypatch, tmp_path):
    data = engine(monkeypatch)
    data.resolve.return_value = tmp_path
    launch = Mock()
    monkeypatch.setattr(picker.ft, 'run', launch)
    assert picker.run(tmp_path) == 0
    data.resolve.assert_called_once_with(tmp_path)
    data.save_choice.assert_not_called()
    launch.assert_not_called()


def test_choose_persists_only_selected_path_and_exits_success(monkeypatch, tmp_path):
    data = engine(monkeypatch)
    candidates = [tmp_path / 'legacy', tmp_path / 'standard']
    view = picker.DataPicker(page(), candidates)
    asyncio.run(view.choose(candidates[1]))
    data.save_choice.assert_called_once_with(candidates[1])
    assert view.exit_code == 0
    view.page.window.destroy.assert_awaited_once()


def test_cancel_does_not_save_or_start_application(monkeypatch, tmp_path):
    data = engine(monkeypatch)
    view = picker.DataPicker(page(), [tmp_path])
    asyncio.run(view.window_event(SimpleNamespace(type=ft.WindowEventType.CLOSE)))
    assert view.exit_code == 2
    data.save_choice.assert_not_called()
    view.page.window.destroy.assert_awaited_once()


def test_save_failure_stays_visible_and_can_retry_or_cancel(monkeypatch, tmp_path):
    data = engine(monkeypatch)
    data.save_choice.side_effect = DataLocationError('Carpeta inaccesible')
    view = picker.DataPicker(page(), [tmp_path])
    asyncio.run(view.choose(tmp_path))
    assert view.error.visible and view.error.value == 'Carpeta inaccesible'
    assert not view.busy and not view.cancel.disabled
    assert all(not button.disabled for button in view.buttons)
    view.page.window.destroy.assert_not_awaited()
    assert view.exit_code == 2


def test_no_selection_or_foreign_path_cannot_be_saved(monkeypatch, tmp_path):
    data = engine(monkeypatch)
    view = picker.DataPicker(page(), [tmp_path / 'legacy'])
    asyncio.run(view.choose(tmp_path / 'other'))
    data.save_choice.assert_not_called()
    view.page.window.destroy.assert_not_awaited()


def test_ambiguous_resolver_displays_candidates_with_keyboard_actions(monkeypatch, tmp_path):
    data = engine(monkeypatch)
    candidates = [tmp_path / 'legacy', tmp_path / 'standard']
    data.resolve.side_effect = ChoiceRequired(candidates)
    mounted = page()
    def launch(main, **kwargs):
        assert kwargs['port'] == 0
        asyncio.run(main(mounted))
    monkeypatch.setattr(picker.ft, 'run', launch)
    assert picker.run(tmp_path) == 2
    view = mounted.window.on_event.__self__
    assert view.candidates == candidates
    assert view.buttons[0].autofocus
    assert len(view.buttons) == 2
    assert mounted.window.prevent_close
    assert mounted.window.width == 800


def test_corrupt_binding_shows_error_instead_of_creating_empty_profile(monkeypatch, tmp_path):
    data = engine(monkeypatch)
    data.resolve.side_effect = DataLocationError('Configuración inválida')
    mounted = page()
    monkeypatch.setattr(picker.ft, 'run', lambda main, **kwargs: asyncio.run(main(mounted)))
    assert picker.run(tmp_path) == 2
    view = mounted.window.on_event.__self__
    assert view.error.visible and view.error.value == 'Configuración inválida'
    assert not view.buttons
    data.save_choice.assert_not_called()


def test_picker_import_does_not_load_settings_or_paths():
    import subprocess
    script = ('import sys; import gui.portable_data_picker; '
              'assert "pokeldn.app.paths" not in sys.modules; '
              'assert "pokeldn.app.settings" not in sys.modules; '
              'assert "gui.portable" not in sys.modules')
    subprocess.run([sys.executable, '-c', script], check=True)
