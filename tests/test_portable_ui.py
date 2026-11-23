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


def test_pending_focus_survives_collection_until_disconnect(view, monkeypatch):
    import gc
    import weakref

    async def scenario():
        entered = asyncio.Event()
        task_ref = None
        async def waiting_for_client():
            nonlocal task_ref
            task_ref = weakref.ref(asyncio.current_task())
            entered.set()
            await asyncio.Future()
        monkeypatch.setattr(view, '_focus', waiting_for_client)
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(view.page, 'run_task',
                            lambda handler: asyncio.run_coroutine_threadsafe(handler(), loop))
        view.schedule_focus()
        await entered.wait()
        gc.collect()
        assert task_ref() is not None
        assert not task_ref().done()
        assert view.gallery_navigation.locked()
        assert len(view.focus_tasks) == 1
        pending = task_ref()
        view.disconnect_focus()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert pending.cancelled()
        assert not view.gallery_navigation.locked()
        assert not view.focus_tasks
        view.schedule_focus()
        assert not view.focus_tasks

    asyncio.run(scenario())


def test_completed_focus_releases_retained_future(view, monkeypatch):
    async def scenario():
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(view.page, 'run_task',
                            lambda handler: asyncio.run_coroutine_threadsafe(handler(), loop))
        monkeypatch.setattr(view, '_focus', AsyncMock())
        view.schedule_focus()
        scheduled = next(iter(view.focus_tasks))
        await asyncio.wrap_future(scheduled)
        assert not view.focus_tasks
    asyncio.run(scenario())


def test_start_schedules_focus_only_once_when_checks_open_gallery(view, monkeypatch):
    from unittest.mock import Mock
    async def check():
        view.setup.engine_ready = True
        view.setup.keys_error = ''
        view.setup.radio_state = 'ready'
        view.setup.initialized = True
    monkeypatch.setattr(view.setup, 'check', check)
    scheduled = Mock(return_value=None)
    monkeypatch.setattr(view.page, 'run_task', scheduled)
    focus = AsyncMock()
    monkeypatch.setattr(view, 'focus', focus)
    asyncio.run(view.start())
    assert view.screen == 'home'
    scheduled.assert_called_once_with(focus)
    focus.assert_not_awaited()


@pytest.mark.parametrize('platform,web,fullscreen,height', [
    ('linux', False, True, 480),
    ('linux', True, False, 480),
    ('darwin', False, False, 512),
    ('win32', False, False, 480),
])
def test_portable_startup_uses_full_display_only_on_native_linux(
        monkeypatch, platform, web, fullscreen, height):
    import flet as ft
    from gui import portable

    monkeypatch.setattr(portable.sys, 'platform', platform)
    monkeypatch.setenv('POKELDN_PORTABLE_DEMO', '1')
    monkeypatch.delenv('POKELDN_UPDATE_JOB', raising=False)
    monkeypatch.setattr(PortableView, 'start', AsyncMock())
    page = SimpleNamespace(web=web, fonts={}, window=ft.Window(),
                           add=lambda control: None, run_task=lambda *a: None)
    asyncio.run(portable.main(page))
    assert page.window.full_screen is fullscreen
    assert page.window.height == height
    assert page.window.prevent_close


@pytest.mark.parametrize('screen', ['home', 'health', 'team', 'trainers', 'bank'])
def test_f11_toggles_native_window_without_leaving_view(view, screen):
    view.page.web = False
    view.page.window = SimpleNamespace(full_screen=True)
    view.screen = screen
    asyncio.run(view.key(SimpleNamespace(key='F11')))
    assert not view.page.window.full_screen
    assert view.screen == screen
    asyncio.run(view.key(SimpleNamespace(key='F11')))
    assert view.page.window.full_screen
    assert view.screen == screen


def test_f11_does_not_access_native_window_in_web_preview(view):
    view.screen = 'team'
    asyncio.run(view.key(SimpleNamespace(key='F11')))
    assert view.screen == 'team'


@pytest.mark.parametrize('blocker', ['handoff', 'menu'])
def test_f11_preserves_keyboard_block_during_handoff_or_menu(view, blocker):
    view.page.web = False
    view.page.window = SimpleNamespace(full_screen=True)
    view.updater.handoff = blocker == 'handoff'
    view.shortcuts.menu_open = blocker == 'menu'
    asyncio.run(view.key(SimpleNamespace(key='F11')))
    assert view.page.window.full_screen


def test_fullscreen_button_toggles_and_tracks_f11(view):
    import flet as ft
    view.page.web = False
    view.page.window = SimpleNamespace(full_screen=False)
    view.fullscreen_button.on_click(None)
    assert view.page.window.full_screen
    assert view.fullscreen_button.icon == ft.Icons.FULLSCREEN_EXIT
    assert view.fullscreen_button.tooltip == 'Volver a ventana (F11)'
    asyncio.run(view.key(SimpleNamespace(key='F11')))
    assert not view.page.window.full_screen
    assert view.fullscreen_button.icon == ft.Icons.FULLSCREEN


@pytest.mark.parametrize('blocker', ['web', 'closing', 'handoff', 'menu'])
def test_fullscreen_button_respects_window_guards(view, blocker):
    view.page.web = blocker == 'web'
    view.page.window = SimpleNamespace(full_screen=False)
    view.closing = blocker == 'closing'
    view.updater.handoff = blocker == 'handoff'
    view.shortcuts.menu_open = blocker == 'menu'
    view.fullscreen_button.on_click(None)
    assert not view.page.window.full_screen


def test_fullscreen_button_is_hidden_on_web(view):
    assert not view.fullscreen_button.visible
    assert view.fullscreen_button not in view.buttons


def test_native_header_reaches_fullscreen_next_to_settings():
    from gui.portable import PORTABLE_GAMES
    page = SimpleNamespace(web=False, window=SimpleNamespace(full_screen=True),
                           update=lambda: None, run_task=lambda *a: None)
    ui = PortableView(page, Setup(demo=True))
    ui.go('home')
    assert ui.fullscreen_button.visible
    assert ui.buttons.index(ui.fullscreen_button) + 1 == ui.buttons.index(ui.settings_button)
    ui.focus = AsyncMock()
    asyncio.run(ui.key(SimpleNamespace(key='Arrow Up')))
    assert ui.buttons[ui.focus_index] is ui.settings_button
    asyncio.run(ui.key(SimpleNamespace(key='Arrow Left')))
    assert ui.buttons[ui.focus_index] is ui.fullscreen_button
    asyncio.run(ui.key(SimpleNamespace(key='Arrow Down')))
    assert ui.focus_index < len(PORTABLE_GAMES)
