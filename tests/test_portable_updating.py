import asyncio
import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import flet as ft

from gui import portable_updating


def window(tmp_path):
    page = SimpleNamespace(add=Mock(), update=Mock(), fonts={},
                           window=SimpleNamespace(destroy=AsyncMock()))
    return portable_updating.UpdateWindow(page, tmp_path)


def install_engine(monkeypatch, apply):
    engine = SimpleNamespace(apply=apply)
    monkeypatch.setitem(sys.modules, 'pokeldn.app.portable_update', engine)
    import pokeldn.app
    monkeypatch.setattr(pokeldn.app, 'portable_update', engine, raising=False)


def test_helper_announces_ready_after_mount_and_closes_after_success(tmp_path, monkeypatch):
    ui = window(tmp_path)
    def apply(job, progress):
        ui.page.add.assert_called_once_with(ui.control)
        assert (job / 'helper.ready').is_file()
        progress('Compilando', 'Motor Pokémon')
        return True
    install_engine(monkeypatch, apply)
    asyncio.run(ui.run())
    assert ui.finished
    assert not ui.spinner.visible
    assert ui.stage.value == 'Actualización completada'
    ui.page.window.destroy.assert_awaited_once()


def test_failure_keeps_error_details_and_close_action_visible(tmp_path, monkeypatch):
    ui = window(tmp_path)
    def apply(job, progress):
        progress('Compilando', 'Error de compilación')
        (job / 'outcome.json').write_text(json.dumps({'ok': False, 'error': 'Compilación fallida; versión anterior abierta.'}))
        return False
    install_engine(monkeypatch, apply)
    asyncio.run(ui.run())
    assert ui.finished and not ui.close_button.disabled
    assert ui.details.visible
    assert ui.detail.value == 'Compilación fallida; versión anterior abierta.'
    ui.page.window.destroy.assert_not_awaited()
    asyncio.run(ui.close(None))
    ui.page.window.destroy.assert_awaited_once()


def test_close_during_installation_does_not_stop_worker(tmp_path):
    ui = window(tmp_path)
    asyncio.run(ui.window_event(SimpleNamespace(type=ft.WindowEventType.CLOSE)))
    ui.page.window.destroy.assert_not_awaited()
    assert not ui.finished


def test_progress_is_thread_safe_bounded_and_keeps_latest_stage(tmp_path, capsys):
    ui = window(tmp_path)
    for number in range(300):
        ui.progress('Instalando', f'Línea {number}')
    ui.page.update.assert_not_called()
    ui.flush()
    assert ui.detail.value == 'Línea 299'
    assert len(ui.details.controls) == 80
    assert 'Línea 0' in capsys.readouterr().out
    assert ui.lines[-1] == 'Instalando: Línea 299'


def test_disconnected_viewer_does_not_abort_worker(tmp_path, monkeypatch):
    ui = window(tmp_path)
    ui.page.update.side_effect = RuntimeError('closed viewer')
    def apply(job, progress):
        progress('Listo', 'Terminó')
        return True
    install_engine(monkeypatch, apply)
    asyncio.run(ui.run())
    assert ui.finished and not ui.connected
    ui.page.window.destroy.assert_not_awaited()


def test_unexpected_worker_error_remains_visible(tmp_path, monkeypatch):
    ui = window(tmp_path)
    def apply(job, progress):
        raise OSError('Disco no disponible')
    install_engine(monkeypatch, apply)
    asyncio.run(ui.run())
    assert ui.finished and not ui.close_button.disabled
    assert ui.detail.value == 'Disco no disponible'
    ui.page.window.destroy.assert_not_awaited()


def test_helper_uses_separate_local_server_and_native_view(tmp_path, monkeypatch):
    for key in ('FLET_SERVER_PORT', 'FLET_FORCE_WEB_SERVER', 'POKELDN_GUI_WEB',
                'POKELDN_PORTABLE_DEMO', 'POKELDN_RADIO'):
        monkeypatch.setenv(key, 'inherited')
    launch = Mock()
    monkeypatch.setattr(portable_updating.ft, 'run', launch)
    portable_updating.run(tmp_path)
    import os
    assert os.environ['FLET_SERVER_IP'] == '127.0.0.1'
    for key in ('FLET_SERVER_PORT', 'FLET_FORCE_WEB_SERVER', 'POKELDN_GUI_WEB',
                'POKELDN_PORTABLE_DEMO', 'POKELDN_RADIO'):
        assert key not in os.environ
    assert launch.call_args.kwargs['port'] == 0


def test_log_tail_is_bounded_and_incremental(tmp_path):
    log = tmp_path / 'update.log'
    log.write_bytes(b'old line\n' * 10000 + b'build error\n')
    offset, lines = portable_updating.read_log_tail(log, 0)
    assert offset == log.stat().st_size
    assert len('\n'.join(lines)) < 16500
    assert lines[-1] == 'build error'
    assert 'salida anterior' in lines[0]
    assert portable_updating.read_log_tail(log, offset) == (offset, [])
    with log.open('ab') as stream:
        stream.write(b'new detail\n')
    next_offset, added = portable_updating.read_log_tail(log, offset)
    assert added == ['new detail'] and next_offset > offset
    log.write_text('truncated\n')
    assert portable_updating.read_log_tail(log, next_offset)[1] == ['truncated']


def test_log_refresh_shows_build_and_app_output_without_changing_stage(tmp_path):
    ui = window(tmp_path)
    (tmp_path / 'update.log').write_text('pip failed\n')
    (tmp_path / 'app.log').write_text('Traceback: launch failed\n')
    asyncio.run(ui.refresh_logs())
    assert list(ui.lines) == ['[update.log] pip failed', '[app.log] Traceback: launch failed']
    assert ui.stage.value == 'Preparando actualización…'
    asyncio.run(ui.refresh_logs())
    assert len(ui.lines) == 2
    assert 'update.log' in ui.log_path.value and 'app.log' in ui.log_path.value


def test_reconnect_restores_updates_after_disconnect(tmp_path):
    ui = window(tmp_path)
    asyncio.run(ui.disconnect(None))
    ui.update()
    ui.page.update.assert_not_called()
    asyncio.run(ui.reconnect(None))
    ui.page.update.assert_called_once()
    assert ui.connected
