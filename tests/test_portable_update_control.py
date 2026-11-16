"""The update hand-off never interrupts radio work or loses the active data path."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from gui import portable_update_control as control
from tests.test_portable_close import view


def candidate():
    return SimpleNamespace(current='a' * 40, target='b' * 40)


def test_update_button_is_left_of_settings_and_hidden_without_candidate():
    ui = view()
    ui.screen = 'home'
    ui.render(update=False)
    assert not ui.updater.button.visible
    ui.updater.candidate = candidate()
    ui.render(update=False)
    assert ui.updater.button.visible
    assert ui.buttons.index(ui.updater.button) < ui.buttons.index(ui.settings_button)


@pytest.mark.parametrize('field', ['busy', 'checking', 'session_busy'])
def test_update_cannot_start_while_hardware_is_busy(field):
    ui = view()
    ui.page.show_dialog = Mock()
    ui.updater.candidate = candidate()
    setattr(ui.setup, field, True)
    ui.updater.sync()
    assert ui.updater.button.disabled
    ui.updater.confirm()
    ui.page.show_dialog.assert_not_called()


def test_update_waits_for_bank_writes():
    ui = view()
    ui.setup.bank_persistence_tasks = [SimpleNamespace(done=lambda: False)]
    assert ui.updater.blocked()
    ui.setup.bank_persistence_tasks[0].done = lambda: True
    assert not ui.updater.blocked()


def test_offline_check_keeps_application_usable(monkeypatch):
    ui = view()
    ui.setup.demo = False
    monkeypatch.setattr(control.portable_update, 'check', Mock(side_effect=control.portable_update.UpdateError('Offline')))
    asyncio.run(ui.updater.check())
    assert not ui.updater.button.visible
    assert ui.updater.error == 'Offline'
    assert ui.connected and not ui.closing


def test_handoff_preserves_data_and_closes_only_after_helper_ready(monkeypatch, tmp_path):
    ui = view()
    ui.page.pop_dialog = Mock()
    ui.page.show_dialog = Mock()
    ui.updater.candidate = candidate()
    create = Mock(return_value=tmp_path)
    monkeypatch.setattr(control.portable_update, 'create_job', create)
    process = Mock()
    spawn = Mock(return_value=process)
    monkeypatch.setattr(control.subprocess, 'Popen', spawn)
    async def ready(job, child):
        assert not ui.closing
        assert ui.updater.handoff and ui.control.disabled
        assert not (job / 'proceed').exists()
    ui.updater.wait_ready = ready
    asyncio.run(ui.updater.begin())
    assert (tmp_path / 'proceed').exists()
    assert ui.closing
    assert spawn.call_args.kwargs['env']['POKELDN_DATA'] == str(control.DATA.resolve())
    assert spawn.call_args.kwargs['start_new_session'] is True
    assert create.call_args.args[1] == control.DATA
    ui.page.window.destroy.assert_awaited_once()


def test_helper_failure_keeps_main_open(monkeypatch, tmp_path):
    ui = view()
    ui.page.pop_dialog = Mock()
    ui.page.show_dialog = Mock()
    ui.updater.candidate = candidate()
    monkeypatch.setattr(control.portable_update, 'create_job', Mock(return_value=tmp_path))
    monkeypatch.setattr(control.subprocess, 'Popen', Mock())
    ui.updater.wait_ready = AsyncMock(side_effect=control.portable_update.UpdateError('Failed'))
    asyncio.run(ui.updater.begin())
    assert (tmp_path / 'cancel').exists()
    assert not (tmp_path / 'proceed').exists()
    assert not ui.closing and not ui.control.disabled and not ui.updater.handoff
    ui.page.window.destroy.assert_not_awaited()


def test_native_close_during_handoff_does_not_abandon_helper():
    ui = view()
    ui.updater.handoff = True
    asyncio.run(ui.close(SimpleNamespace()))
    ui.page.window.destroy.assert_not_awaited()


def test_trial_version_waits_for_commit_before_checks(monkeypatch):
    from gui import portable
    ui = view()
    ui.page.fonts = {}
    ui.page.add = Mock()
    calls = []
    ui.start = AsyncMock(side_effect=lambda: calls.append('checks'))
    monkeypatch.setattr(portable, 'PortableView', lambda p, s: ui)
    monkeypatch.setattr(portable, 'shared_setup', lambda: ui.setup)
    monkeypatch.setenv('POKELDN_UPDATE_JOB', '/temporary/trial')
    def acknowledge():
        assert ui.control.disabled
        calls.append('commit')
    monkeypatch.setattr(control.portable_update, 'acknowledge_startup', acknowledge)
    asyncio.run(portable.main(ui.page))
    assert calls == ['commit', 'checks']
    assert not ui.control.disabled


def test_ready_window_without_engine_lock_does_not_authorize_close(tmp_path, monkeypatch):
    (tmp_path / 'helper.ready').touch()
    process = SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(control.asyncio, 'sleep', AsyncMock())
    with pytest.raises(control.portable_update.UpdateError, match='no respondió'):
        asyncio.run(control.PortableUpdate.wait_ready(tmp_path, process))
    (tmp_path / 'engine.ready').touch()
    asyncio.run(control.PortableUpdate.wait_ready(tmp_path, process))


def test_trial_activation_failure_never_starts_radio_checks(monkeypatch):
    from gui import portable
    ui = view()
    ui.page.fonts = {}
    ui.page.add = Mock()
    ui.start = AsyncMock()
    monkeypatch.setattr(portable, 'PortableView', lambda p, s: ui)
    monkeypatch.setattr(portable, 'shared_setup', lambda: ui.setup)
    monkeypatch.setenv('POKELDN_UPDATE_JOB', '/temporary/trial')
    monkeypatch.setattr(control.portable_update, 'acknowledge_startup',
                        Mock(side_effect=control.portable_update.UpdateError('Timeout')))
    asyncio.run(portable.main(ui.page))
    ui.start.assert_not_awaited()
    ui.page.window.destroy.assert_awaited_once()


def test_check_error_is_readable_in_settings():
    ui = view()
    ui.setup.demo = False
    ui.updater.error = 'Hay cambios locales.'
    ui.updater.sync()
    ui.screen = 'health'
    ui.render(update=False)
    assert 'Hay cambios locales.' in ui.updater.status.value


def test_gallery_up_keeps_settings_and_left_reaches_update():
    ui = view()
    ui.updater.candidate = candidate()
    ui.screen = 'home'
    ui.render(update=False)
    ui.focus = AsyncMock()
    asyncio.run(ui.key(SimpleNamespace(key='Arrow Up')))
    assert ui.buttons[ui.focus_index] is ui.settings_button
    asyncio.run(ui.key(SimpleNamespace(key='Arrow Left')))
    assert ui.buttons[ui.focus_index] is ui.updater.button
    asyncio.run(ui.key(SimpleNamespace(key='Arrow Right')))
    assert ui.buttons[ui.focus_index] is ui.settings_button
