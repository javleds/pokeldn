import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import flet as ft
import pytest

from gui.portable_touch import TouchOptions, drag_scroll


@pytest.mark.parametrize('horizontal', [False, True])
def test_drag_moves_content_in_opposite_direction_without_selecting(horizontal):
    scroll = AsyncMock()
    listing = ft.ListView(horizontal=horizontal)
    detector = drag_scroll(listing, scroll, horizontal=horizontal)
    handler = detector.on_horizontal_drag_update if horizontal else detector.on_vertical_drag_update
    asyncio.run(handler(SimpleNamespace(primary_delta=-45)))
    scroll.assert_awaited_once_with(45)


def picker():
    control = ft.Dropdown(value='a', options=[
        ft.DropdownOption(key='a', text='Abra'),
        ft.DropdownOption(key='b', text='Bulbasaur'),
        ft.DropdownOption(key='c', text='Charmander', disabled=True),
    ])
    control.update = Mock()
    selected = Mock()
    page = SimpleNamespace(show_dialog=Mock(), pop_dialog=Mock())
    return TouchOptions(page, control, selected)


def test_query_is_temporary_and_cancel_preserves_selection():
    ui = picker()
    ui.query.value = 'BULBA'
    ui.filter(update=False)
    assert len(ui.rows.controls) == 1
    assert ui.rows.controls[0].content.content == 'Bulbasaur'
    assert ui.control.value == 'a'
    asyncio.run(ui.cancel())
    ui.selected.assert_not_called()
    assert ui.control.value == 'a'


def test_select_commits_once_and_ignores_late_events():
    ui = picker()
    asyncio.run(ui.choose('b'))
    asyncio.run(ui.choose('a'))
    assert ui.control.value == 'b'
    assert ui.control.text == 'Bulbasaur'
    ui.selected.assert_called_once()
    ui.page.pop_dialog.assert_called_once()


@pytest.mark.parametrize('case', ['disabled_control', 'disabled_option', 'removed_option'])
def test_stale_or_disabled_choices_cannot_commit(case):
    ui = picker()
    if case == 'disabled_control':
        ui.control.disabled = True
    elif case == 'removed_option':
        ui.control.options = []
    asyncio.run(ui.choose('c' if case == 'disabled_option' else 'b'))
    ui.selected.assert_not_called()
    assert ui.control.value == 'a'


def test_cancel_waits_for_scroll_before_unmounting():
    async def scenario():
        ui = picker()
        started, finish = asyncio.Event(), asyncio.Event()

        async def scroll(**kwargs):
            started.set()
            await finish.wait()

        ui.rows.scroll_to = scroll
        pending = asyncio.create_task(ui.scroll(30))
        await started.wait()
        closing = asyncio.create_task(ui.cancel())
        await asyncio.sleep(0)
        ui.page.pop_dialog.assert_not_called()
        finish.set()
        await asyncio.gather(pending, closing)
        ui.rows.scroll_to = AsyncMock()
        await ui.scroll(20)
        ui.rows.scroll_to.assert_not_called()

    asyncio.run(scenario())


@pytest.mark.parametrize('horizontal', [False, True])
def test_fast_drag_includes_movement_before_first_update(horizontal):
    scroll = AsyncMock()
    detector = drag_scroll(ft.ListView(), scroll, horizontal=horizontal)
    axis = 'horizontal' if horizontal else 'vertical'
    getattr(detector, f'on_{axis}_drag_down')(SimpleNamespace(global_position=ft.Offset(100, 100)))
    asyncio.run(getattr(detector, f'on_{axis}_drag_start')(
        SimpleNamespace(global_position=ft.Offset(40, 40))))
    scroll.assert_awaited_once_with(60)


def test_escape_cancels_query_and_restores_shell_keyboard_handler():
    ui = picker()
    original = AsyncMock()
    ui.page.on_keyboard_event = original
    ui.open()
    ui.query.value = 'something'
    asyncio.run(ui.page.on_keyboard_event(SimpleNamespace(key='Escape')))
    assert ui.closed and ui.control.value == 'a'
    assert ui.page.on_keyboard_event is original
    original.assert_not_called()
    ui.selected.assert_not_called()


def test_selector_has_one_open_route_and_ignores_duplicate_or_disabled_open():
    from gui.portable_touch import TouchSelector
    page = SimpleNamespace(show_dialog=Mock(), pop_dialog=Mock())
    selector = TouchSelector(page, [ft.DropdownOption(key='a', text='Abra')],
                             'a', Mock(), Mock(), lambda: True)
    selector.open_button.on_click(None)
    first = selector.picker
    selector.open_button.on_click(None)
    assert selector.picker is first
    page.show_dialog.assert_called_once_with(first.dialog)
    asyncio.run(first.cancel())
    selector.disabled = True
    selector.open_button.on_click(None)
    assert selector.picker is first
    assert page.show_dialog.call_count == 1


def test_selector_refreshes_caption_when_options_arrive_or_value_changes():
    from gui.portable_touch import TouchSelector
    selector = TouchSelector(SimpleNamespace(), [], 'a', Mock(), Mock(), lambda: True)
    selector.options = [ft.DropdownOption(key='a', text='Abra'), ft.DropdownOption(key='b', text='Bulbasaur')]
    selector.before_update()
    assert selector.caption.value == 'Abra'
    selector.value = 'b'
    selector.before_update()
    assert selector.caption.value == 'Bulbasaur'
