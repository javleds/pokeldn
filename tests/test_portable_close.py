"""Stop portable UI producers before destroying the native window once."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import flet as ft
import pytest

from gui import portable
from gui.portable_setup import Setup


def view():
    page = SimpleNamespace(web=False, update=Mock(), run_task=Mock(return_value=None),
                           window=SimpleNamespace(destroy=AsyncMock()))
    return portable.PortableView(page, Setup(demo=True))


def test_close_stops_resources_focus_and_listeners_before_destroy():
    ui = view()
    focus_task = Mock()
    ui.focus_tasks.add(focus_task)
    sampling_task = Mock()
    ui.resources.task = sampling_task
    ui.resources.enabled = True
    listener = Mock()
    ui.setup_listener = listener
    ui.setup.listeners.add(listener)
    ui.team_view = SimpleNamespace(dispose=Mock())
    async def destroyed():
        assert ui.closing and not ui.connected
        assert not ui.resources.connected and ui.resources.task is None
        sampling_task.cancel.assert_called_once()
        focus_task.cancel.assert_called_once()
        assert listener not in ui.setup.listeners
        ui.team_view.dispose.assert_called_once()
    ui.page.window.destroy.side_effect = destroyed
    asyncio.run(ui.close(None))
    ui.page.window.destroy.assert_awaited_once()


def test_concurrent_close_requests_destroy_only_once():
    ui = view()
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def destroy():
            entered.set()
            await release.wait()
        ui.page.window.destroy.side_effect = destroy
        first = asyncio.create_task(ui.close(None))
        await entered.wait()
        await ui.close(None)
        release.set()
        await first
    asyncio.run(scenario())
    ui.page.window.destroy.assert_awaited_once()


@pytest.mark.parametrize('flash,session', [(True, False), (False, True), (True, True)])
def test_close_never_interrupts_flash_or_session(flash, session):
    ui = view()
    ui.setup.busy, ui.setup.session_busy = flash, session
    ui.go = Mock()
    asyncio.run(ui.close(None))
    assert not ui.closing and ui.connected
    ui.page.window.destroy.assert_not_awaited()
    if flash and not session:
        ui.go.assert_called_once_with('progress')
    else:
        ui.go.assert_not_called()


@pytest.mark.parametrize('closing,connected', [(True, True), (False, False)])
def test_late_refresh_does_not_update_window(closing, connected):
    ui = view()
    ui.closing, ui.connected = closing, connected
    ui.screen = 'team'
    ui.team_view = SimpleNamespace(refresh=Mock())
    ui.changed()
    ui.team_view.refresh.assert_not_called()
    ui.page.update.assert_not_called()


def test_window_close_and_late_page_events_share_lifecycle(monkeypatch):
    ui = view()
    ui.start = AsyncMock()
    page = ui.page
    page.fonts = {}
    page.add = Mock()
    monkeypatch.setattr(portable, 'PortableView', lambda page, setup: ui)
    monkeypatch.setattr(portable, 'shared_setup', lambda: ui.setup)
    monkeypatch.delenv('POKELDN_PORTABLE_DEMO', raising=False)

    async def scenario():
        await portable.main(page)
        assert page.theme_mode == ft.ThemeMode.LIGHT
        assert all(getattr(page.theme.text_theme, field.name).color == portable.INK
                   for field in portable.fields(ft.TextTheme))
        listener = ui.setup_listener
        await page.window.on_event(SimpleNamespace(type=ft.WindowEventType.CLOSE))
        page.run_task.reset_mock()
        listener()  # A queued notification from before listener removal.
        page.run_task.assert_not_called()
        await page.on_disconnect(None)
        await page.on_connect(None)
        assert ui.closing and not ui.connected
        assert listener not in ui.setup.listeners
    asyncio.run(scenario())
    page.window.destroy.assert_awaited_once()
