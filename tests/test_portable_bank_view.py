import asyncio
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

from gui.portable_bank_view import BankView, BankEditorView
from tests.test_portable_bank_team import model  # noqa: F401


def make_view():
    entry = dict(id='magikarp-1', game='frlg', species='Magikarp', nickname='Fish',
                 trainer=dict(ot='RED', tid=1, sid=2, language=7))
    library = SimpleNamespace(list=Mock(return_value=[entry]), delete=Mock(),
                              delete_all=Mock(), data=Mock(return_value=b'original'),
                              export=Mock(return_value=b'[]'))
    setup = SimpleNamespace(bank_library=library, busy=False, checking=False, session_busy=False)
    page = SimpleNamespace(web=False, show_dialog=Mock(), pop_dialog=Mock())
    shell = SimpleNamespace(page=page, setup=setup, go=Mock(), open_bank_record=AsyncMock())
    return BankView(shell), library, entry


def test_bank_filters_and_actions_are_available():
    view, library, entry = make_view()
    view.query.value, view.game.value = 'Fish', 'frlg'
    view.refresh()
    library.list.assert_called_with('Fish', 'frlg')
    asyncio.run(view.open_record(entry, False))
    view.shell.open_bank_record.assert_awaited_once_with('frlg', b'original', edit=False)


def test_delete_all_is_explicit_and_blocked_during_session():
    view, library, _ = make_view()
    view.confirm_delete_all()
    library.delete_all.assert_not_called()
    dialog = view.page.show_dialog.call_args.args[0]
    dialog.actions[0].on_click(None)
    library.delete_all.assert_not_called()
    view.shell.setup.session_busy = True
    asyncio.run(dialog.actions[1].on_click(None))
    library.delete_all.assert_not_called()
    assert 'termine' in view.message.value


def test_bank_editor_locks_original_owner_and_single_slot(model):
    asyncio.run(model.load_original())
    page = SimpleNamespace(run_task=Mock(), show_dialog=Mock(), pop_dialog=Mock())
    shell = SimpleNamespace(page=page, go=Mock(), screen='team')
    view = BankEditorView(shell, model)
    assert view.trainer.disabled and not view.find.visible
    assert view.mode_menu.disabled
    assert all(not button.visible for button in view.slot_buttons[1:])
    assert not view.clear_all.visible and not view.clear_one.visible
    model.edit_enabled = False
    view.refresh(update=False)
    assert view.editor.disabled and view.editor_tabs.disabled
    assert view.start.tooltip == 'Enviar original intacto'
    view._back(None)
    shell.go.assert_called_once_with('bank')


def test_close_waits_for_last_bank_deposit():
    from tests.test_portable_close import view
    ui = view()
    async def scenario():
        released = asyncio.Event()
        persisted = asyncio.Event()
        async def deposit():
            await released.wait()
            persisted.set()
        task = asyncio.create_task(deposit())
        ui.setup.bank_persistence_tasks = {task}
        closing = asyncio.create_task(ui.close(None))
        await asyncio.sleep(0)
        ui.page.window.destroy.assert_not_awaited()
        released.set()
        await closing
        assert persisted.is_set()
        ui.page.window.destroy.assert_awaited_once()
    asyncio.run(scenario())
