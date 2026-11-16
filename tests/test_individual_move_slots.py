import asyncio
from types import SimpleNamespace
import pytest
from tests.test_portable_received import model as received_model, receive
from tests.test_portable_bank_team import model as bank_model
from tests.test_portable_team_view import view


def test_modifier_sends_auto_and_empty_separately_and_keeps_original(received_model):
    async def scenario():
        await receive(received_model)
        received_model.edit(0, 'moves', [33, None, 0, None], option=True)
        await received_model.validate(0)
        assert received_model.service.edits[-1] == (b'original', {'move_slots': [33, None, 0, None]})
        assert received_model.original_editable['moves'] == [33, 145, 0, 0]
        assert received_model.original == b'original'
    asyncio.run(scenario())


def test_bank_edit_sends_auto_and_empty_without_rewriting_archive(bank_model):
    async def scenario():
        await bank_model.load_original()
        bank_model.edit(0, 'moves', [33, 145, None, 0], option=True)
        await bank_model.validate(0)
        assert bank_model.service.edits[-1][1] == {'move_slots': [33, 145, None, 0]}
        assert bank_model.original == b'original bytes'
        assert bank_model.original_editable['moves'] == [33, 145, 0, 0]
    asyncio.run(scenario())


@pytest.mark.parametrize('value,label', [(0, 'Vacío'), (None, 'Automático')])
def test_move_selector_distinguishes_empty_from_automatic(value, label):
    ui = view()
    ui.model.slots[0] = dict(species=7, level='5', options={'moves': [33, 145, value, 0]})
    ui._draw_editor()
    control = ui.basic_controls[6]
    assert control.text == label
    assert [(o.key, o.text) for o in control.options][:2] == [('', 'Automático'), ('0', 'Vacío')]
    control.value = '0'
    control.on_select(SimpleNamespace(control=control))
    assert ui.model.edit.call_args.args[2][2] == 0
    control.value = ''
    control.on_select(SimpleNamespace(control=control))
    assert ui.model.edit.call_args.args[2][2] is None
