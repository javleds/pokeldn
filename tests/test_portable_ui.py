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


def test_gallery_catalog_and_selection_survive_settings(view):
    from gui.portable import PORTABLE_GAMES
    assert [g.key for g in PORTABLE_GAMES] == ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za']
    view.go('home')
    assert view.game_list.horizontal
    asyncio.run(view.select_game(PORTABLE_GAMES[-1]))
    view.go('health')
    view.go('home')
    assert view.selected_game.key == 'za'


def test_selection_waits_for_gallery_scroll_response(view, monkeypatch):
    from gui.portable import PORTABLE_GAMES
    from unittest.mock import Mock

    async def scenario():
        view.go('home')
        started, finish = asyncio.Event(), asyncio.Event()
        async def scroll(**kwargs):
            started.set()
            await finish.wait()
        monkeypatch.setattr(view.game_list, 'scroll_to', scroll)
        opened = Mock(side_effect=lambda game: setattr(view, 'screen', 'team'))
        monkeypatch.setattr(view, 'open_team', opened)
        focus = asyncio.create_task(view.buttons[0].on_focus(None))
        await started.wait()
        selection = asyncio.create_task(view.select_game(PORTABLE_GAMES[0]))
        await asyncio.sleep(0)
        opened.assert_not_called()
        finish.set()
        await asyncio.gather(focus, selection)
        opened.assert_called_once_with(PORTABLE_GAMES[0])
        # A focus event queued before navigation must not call the old gallery.
        await view.buttons[0].on_focus(None)

    asyncio.run(scenario())


def test_start_does_not_override_navigation_during_checks(view, monkeypatch):
    async def check():
        view.setup.engine_ready = True
        view.setup.keys_error = ''
        view.setup.radio_state = 'ready'
        view.go('keys')
    monkeypatch.setattr(view.setup, 'check', check)
    monkeypatch.setattr(view, 'focus', AsyncMock())
    asyncio.run(view.start())
    assert view.screen == 'keys'


def test_gallery_missing_image_uses_pokeball(monkeypatch):
    import flet as ft
    from gui.portable import PORTABLE_GAMES, game_avatar
    from pathlib import Path
    monkeypatch.setattr(Path, 'is_file', lambda self: False)
    assert game_avatar(PORTABLE_GAMES[0]).content.icon == ft.Icons.CATCHING_POKEMON


def test_gallery_existing_image_has_error_fallback():
    import flet as ft
    from gui.portable import PORTABLE_GAMES, game_avatar
    assert game_avatar(PORTABLE_GAMES[0]).content.error_content.icon == ft.Icons.CATCHING_POKEMON


def test_gallery_navigation_keeps_focus_visible_and_reaches_settings(view, monkeypatch):
    from gui.portable import PORTABLE_GAMES
    view.go('home')
    scroll = AsyncMock()
    monkeypatch.setattr(view.game_list, 'scroll_to', scroll)
    for button in view.buttons:
        monkeypatch.setattr(button, 'focus', AsyncMock())
    for _ in range(10):
        asyncio.run(view.key(SimpleNamespace(key='Arrow Right')))
    assert view.focus_index == len(PORTABLE_GAMES) - 1
    scroll.assert_awaited_with(offset=534, duration=150)
    asyncio.run(view.key(SimpleNamespace(key='Arrow Up')))
    assert view.buttons[view.focus_index] is view.settings_button
    asyncio.run(view.key(SimpleNamespace(key='Arrow Down')))
    assert view.focus_index == 0


@pytest.mark.parametrize('ready', [True, False])
def test_start_waits_for_checks_owned_by_another_session(view, monkeypatch, ready):
    view.setup.checking = True
    monkeypatch.setattr(view, 'focus', AsyncMock())
    asyncio.run(view.start())
    assert view.screen == 'health'
    view.setup.engine_ready = ready
    view.setup.keys_error = ''
    view.setup.radio_state = 'ready'
    view.setup.checking = False
    view.setup.initialized = True
    view.changed()
    assert view.screen == ('home' if ready else 'health')
    assert not view.startup_pending


def test_manual_settings_stay_open_after_successful_checks(view):
    view.setup.engine_ready = True
    view.setup.keys_error = ''
    view.setup.radio_state = 'ready'
    view.setup.initialized = True
    view.go('health')
    view.changed()
    assert view.screen == 'health'
