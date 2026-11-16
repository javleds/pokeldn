import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import flet as ft

from gui import board, portable_setup
from gui.portable import PortableView
from tests.test_portable_setup import real_state, port


def test_slow_radio_keeps_loop_responsive_and_cleans_notice(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    entered, release = threading.Event(), threading.Event()
    def identify(*args):
        entered.set()
        assert release.wait(3)
        raise ValueError('No firmware')
    monkeypatch.setattr(portable_setup, 'CHECK_SLOW_SECONDS', .01)
    monkeypatch.setattr(portable_setup.pokemon.SERVICE, 'names', lambda *a: ['test'])
    monkeypatch.setattr(board, 'ports', lambda: [port()])
    monkeypatch.setattr(board, 'identify', identify)
    monkeypatch.setattr(board, 'detect_chip', lambda *a: 'ESP32-S3')
    stages = []
    state.listeners.add(lambda: stages.append(state.check_detail))
    async def scenario():
        task = asyncio.create_task(state.check())
        try:
            async with asyncio.timeout(2):
                while not entered.is_set() or not state.check_slow:
                    await asyncio.sleep(.005)
            assert state.checking and state.radio_state == 'checking'
            await state.check()  # No second USB operation.
        finally:
            release.set()
            await task
    asyncio.run(scenario())
    assert state.radio_state == 'flash' and state.chip == 'ESP32-S3'
    assert any('identificando' in stage for stage in stages)
    assert not state.checking and not state.check_slow and not state.check_detail


def test_health_has_animated_radio_and_local_access_during_check():
    state = portable_setup.Setup(demo=True)
    state.checking = True
    state.engine_ready = True
    state.radio_state = 'checking'
    state.check_detail = 'Comprobando radio y firmware…'
    page = SimpleNamespace(web=False, update=Mock(), run_task=Mock())
    view = PortableView(page, state)
    content = view.view_health()
    statuses = content.controls[1].content.controls
    assert isinstance(statuses[3].content.controls[0], ft.ProgressRing)
    assert all(not button.disabled for button in statuses[-1].controls)
    primary, local, retry = content.controls[-1].controls
    assert primary.disabled and retry.disabled and not local.disabled
