import asyncio
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

import pytest

from gui import portable_shortcuts as ui_module
from tests.test_portable_close import view


def enabled():
    ui = view()
    ui.shortcuts.supported = lambda: True
    ui.screen = 'home'
    ui.render(update=False)
    return ui


def test_native_dropdown_has_two_explicit_actions():
    ui = enabled()
    assert ui.shortcuts.control.visible
    assert [item.content.controls[1].value for item in ui.shortcuts.control.items] == [
        'Agregar al menú', 'Agregar al escritorio']
    header = ui.control.controls[0].content.controls[0].content
    assert header.controls.index(ui.shortcuts.control) < header.controls.index(ui.updater.button)
    assert header.controls.index(ui.shortcuts.control) < header.controls.index(ui.settings_button)


def test_visibility_tracks_settings_or_available_update():
    ui = enabled()
    ui.screen = 'health'
    ui.render(update=False)
    assert not ui.shortcuts.control.visible
    ui.updater.candidate = SimpleNamespace(current='a', target='b')
    ui.render(update=False)
    assert ui.shortcuts.control.visible


@pytest.mark.parametrize('field', ['busy', 'checking', 'session_busy'])
def test_busy_states_do_not_register_shortcuts(field, monkeypatch):
    ui = enabled()
    setattr(ui.setup, field, True)
    install = Mock()
    monkeypatch.setattr(ui_module.portable_shortcuts, 'install_shortcut', install)
    asyncio.run(ui.shortcuts.install('menu'))
    install.assert_not_called()


def test_install_uses_stable_root_and_current_data(monkeypatch, tmp_path):
    ui = enabled()
    ui.page.show_dialog = Mock()
    monkeypatch.setattr(ui_module.portable_update, 'installation_root', lambda: tmp_path)
    install = Mock(return_value=SimpleNamespace(path=tmp_path/'app.desktop', backup=None, warning='Permitir ejecutar'))
    monkeypatch.setattr(ui_module.portable_shortcuts, 'install_shortcut', install)
    asyncio.run(ui.shortcuts.install('desktop'))
    install.assert_called_once_with('desktop', tmp_path, ui_module.DATA)
    dialog = ui.page.show_dialog.call_args.args[0]
    assert 'escritorio' in dialog.title.value
    assert 'Permitir ejecutar' in dialog.content.controls[0].value
    assert not ui.shortcuts.busy


def test_failure_is_visible_and_menu_reenabled(monkeypatch):
    ui = enabled()
    ui.page.show_dialog = Mock()
    monkeypatch.setattr(ui_module.portable_shortcuts, 'install_shortcut',
                        Mock(side_effect=ui_module.portable_shortcuts.ShortcutError('Sin escritorio configurado')))
    asyncio.run(ui.shortcuts.install('desktop'))
    assert not ui.shortcuts.busy and not ui.shortcuts.control.disabled
    assert 'Sin escritorio' in ui.page.show_dialog.call_args.args[0].content.controls[0].value


def test_open_menu_keeps_native_arrow_and_escape_navigation():
    ui = enabled()
    ui.shortcuts.menu_open = True
    ui.focus = AsyncMock()
    ui.go = Mock()
    asyncio.run(ui.key(SimpleNamespace(key='Arrow Left')))
    asyncio.run(ui.key(SimpleNamespace(key='Escape')))
    ui.focus.assert_not_awaited()
    ui.go.assert_not_called()
    ui.shortcuts.dismissed(None)
    assert not ui.shortcuts.menu_open


def test_non_linux_web_demo_and_frozen_are_not_offered(monkeypatch):
    ui = view()
    monkeypatch.setattr(ui_module.sys, 'platform', 'linux')
    ui.setup.demo = False
    assert ui.shortcuts.supported()
    ui.page.web = True
    assert not ui.shortcuts.supported()
    ui.page.web = False
    monkeypatch.setattr(ui_module.sys, 'frozen', True, raising=False)
    assert not ui.shortcuts.supported()
