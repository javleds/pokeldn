import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from gui.portable import PortableView
from gui.portable_setup import Setup


@pytest.fixture
def view():
    page = SimpleNamespace(web=True, update=lambda: None, run_task=lambda *a: None)
    return PortableView(page, Setup(demo=True))


@pytest.mark.parametrize("screen", ["health", "keys", "board", "progress", "logs", "ready", "home"])
def test_views_build_without_hardware(view, screen):
    view.screen = screen
    view.render(update=False)
    assert view.body.content is not None
    assert view.buttons


def test_details_do_not_interrupt_installation(view):
    view.setup.busy = True
    view.setup.log("writing")
    view.go("logs")
    view.go("health")
    assert view.screen == "logs"
    assert view.setup.busy
    view.go("progress")
    assert view.setup.busy and len(view.setup.logs) == 1


def test_escape_returns_from_logs_without_cancelling(view):
    view.setup.busy = True
    view.screen = "logs"
    asyncio.run(view.key(SimpleNamespace(key="Escape")))
    assert view.screen == "progress" and view.setup.busy


def test_local_entry_requires_working_engine(view):
    view.setup.engine_ready = False
    view.render(update=False)
    assert view.buttons[1].disabled
    view.setup.engine_ready = True
    view.render(update=False)
    assert not view.buttons[1].disabled


def test_progress_updates_keep_details_button_and_focus(view, monkeypatch):
    view.setup.busy = True
    view.screen = "progress"
    view.render(update=False)
    details = view.buttons[0]
    for control in (view.phase_label, view.progress_bar, view.percent_label):
        monkeypatch.setattr(control, "update", lambda: None)
    view.setup.progress = .64
    view.changed()
    assert view.buttons[0] is details
    assert view.percent_label.value == "64%"


def test_reinstall_confirmation_and_escape_do_not_write(view, monkeypatch):
    install = AsyncMock()
    monkeypatch.setattr(view.setup, 'install', install)
    view.setup.radio_state, view.setup.chip = 'ready', 'ESP32-C6'
    view.go('reinstall')
    assert view.buttons[0].content.value == 'Cancelar'
    assert not view.buttons[1].disabled
    asyncio.run(view.key(SimpleNamespace(key='Escape')))
    assert view.screen == 'board'
    install.assert_not_called()


def test_confirm_reinstall_passes_explicit_intent(view, monkeypatch):
    install = AsyncMock()
    monkeypatch.setattr(view.setup, 'install', install)
    asyncio.run(view.install(reinstall=True))
    install.assert_awaited_once_with(reinstall=True)


@pytest.mark.parametrize("initialized", [False, True])
def test_start_opens_home_when_checks_are_ready(view, monkeypatch, initialized):
    view.setup.initialized = initialized
    async def check():
        view.setup.engine_ready = True
        view.setup.keys_error = ""
        view.setup.radio_state = "ready"
    if initialized:
        asyncio.run(check())
    monkeypatch.setattr(view.setup, "check", check)
    monkeypatch.setattr(view, "focus", AsyncMock())
    asyncio.run(view.start())
    assert view.screen == "home"


@pytest.mark.parametrize("busy,ready,expected", [(False, True, "home"), (False, False, "health"), (True, True, "progress")])
def test_new_session_selects_initial_screen(view, monkeypatch, busy, ready, expected):
    view.setup.initialized = True
    view.setup.engine_ready = ready
    view.setup.keys_error = ""
    view.setup.radio_state = "ready"
    view.setup.busy = busy
    reopened = PortableView(view.page, view.setup)
    assert reopened.screen == expected
    monkeypatch.setattr(reopened, "focus", AsyncMock())
    asyncio.run(reopened.start())
    assert reopened.screen == expected
