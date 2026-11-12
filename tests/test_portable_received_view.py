import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from gui.portable_received_view import ReceivedView


def model(mode='modifier'):
    return SimpleNamespace(
        mode=mode, game='sv', settings=SimpleNamespace(sprites=False), active=False, busy=False,
        phase='idle', params={'level': '100', 'nature': 0, 'effort': {}},
        slots=[None] * 6, metadata={}, states=['empty'] * 6, errors=[''] * 6,
        results=[None] * 6, listeners=set(), role='host', version='scarlet', code='', tools={},
        received_info=None, report='', original_legal=None, candidate_legal=False,
        return_pending=False, logs=[], error='', supported=True, support_reason='', recovery_notice='',
        run_stamp='fixture', names=AsyncMock(return_value=[]), candidate_moves=Mock(return_value=[]),
        load_options=AsyncMock(), validate=AsyncMock(), validate_all=AsyncMock(), edit=Mock(),
        configure_param=Mock(), configure=Mock(), start=AsyncMock(), stop=Mock(), reset=Mock(),
        return_original_now=AsyncMock(), return_edited_now=AsyncMock(),
    )


def view(mode='modifier'):
    page = SimpleNamespace(run_task=Mock(), show_dialog=Mock(), pop_dialog=Mock())
    shell = SimpleNamespace(page=page, screen='team', go=Mock(), open_trade_mode=Mock(),
                            settings_button=SimpleNamespace(disabled=False, parent=None),
                            close_button=SimpleNamespace(disabled=False, parent=None))
    return ReceivedView(shell, model(mode))


@pytest.mark.parametrize('mode', ['evolution', 'level', 'nature', 'effort', 'modifier', 'validator'])
def test_modes_build_idle_configuration_without_receiving(mode):
    ui = view(mode)
    assert ui.body.controls == [ui.intro]
    assert ui.start.visible and not ui.start.disabled
    assert not ui.cancel.visible and not ui.original.visible
    assert not ui.model.start.called


def test_level_and_effort_configuration_does_not_generate():
    ui = view('level')
    field = ui.param_controls[0]
    field.value = '25'
    field.on_change(SimpleNamespace(control=field))
    ui.model.configure_param.assert_called_once_with('level', '25')
    ui.model.validate.assert_not_called()
    ui = view('effort')
    field = ui.param_controls[0]
    field.value = '252'
    field.on_change(SimpleNamespace(control=field))
    ui.model.configure_param.assert_called_once_with('effort', {'hp': '252'})


def received(ui, phase='editing'):
    m = ui.model
    m.active = True
    m.phase = phase
    m.busy = phase != 'editing' and phase != 'review'
    m.slots[0] = {'species': 7, 'level': '5', 'nickname': '', 'shiny': False, 'options': {}}
    m.received_info = {'species_id': 7, 'species': 'Squirtle', 'level': 5, 'ot': 'Fixture', 'legal': True}
    m.metadata[0] = {'base': [44, 48, 65, 50, 64, 43], 'effort': {'max': 252, 'total': 510}}
    m.return_pending = True
    ui.refresh(update=False)


def test_modifier_opens_editor_on_receipt_and_keeps_actions_above():
    ui = view()
    received(ui)
    assert ui.body.controls == [ui.editor_group]
    assert ui.original.visible and ui.edited.visible and ui.edited.disabled
    assert ui.logs.visible and ui.cancel.visible
    assert ui.mode_menu.disabled and ui.connection.disabled and ui.back.disabled
    assert ui.shell.settings_button.disabled and ui.shell.close_button.disabled
    assert not ui.start.visible
    assert ui.editor_controls
    assert not ui.editor_controls[0].disabled
    ui.model.candidate_legal = True
    ui.model.states[0] = 'legal'
    ui.refresh(update=False)
    assert not ui.edited.disabled
    ui.model.states[0] = 'validating'
    ui.refresh(update=False)
    assert ui.edited.disabled


def test_active_editing_cannot_change_mode_or_connection_or_configuration():
    ui = view()
    received(ui)
    ui._mode('team')
    ui._back(None)
    ui._connection(None)
    ui._configure('level', '10')
    ui.shell.open_trade_mode.assert_not_called()
    ui.shell.go.assert_not_called()
    ui.page.show_dialog.assert_not_called()
    ui.model.configure_param.assert_not_called()


@pytest.mark.parametrize('legal,color', [(True, '#D6EEE0'), (False, '#F4DADF')])
def test_validator_uses_card_and_report_modal_without_inline_report(legal, color):
    ui = view('validator')
    ui.model.original_legal = legal
    ui.model.report = 'First failure\nSecond failure\nThird failure'
    received(ui, 'returning')
    assert ui.body.controls == [ui.card]
    assert ui.card.bgcolor == color
    assert ui.details.visible
    assert ui.model.report not in ui.status.value
    ui._details(None)
    dialog = ui.page.show_dialog.call_args.args[0]
    report_text = dialog.content.content.content.controls[0]
    assert report_text.value == ui.model.report


def test_manual_return_actions_call_controller_and_original_does_not_require_legal_candidate():
    ui = view()
    received(ui)
    assert ui.original.visible and not ui.original.disabled
    asyncio.run(ui._original(None))
    ui.model.return_original_now.assert_awaited_once()
    asyncio.run(ui._edited(None))
    ui.model.return_edited_now.assert_not_awaited()
    ui.model.candidate_legal = True
    ui.model.states[0] = 'legal'
    asyncio.run(ui._edited(None))
    ui.model.return_edited_now.assert_awaited_once()


def test_disallowed_transport_disables_start_and_preserves_reason():
    ui = view('level')
    ui.model.supported = False
    ui.model.support_reason = 'Esta combinación no dispone de devolución controlada.'
    ui.refresh(update=False)
    assert ui.start.disabled
    assert ui.status.value == ui.model.support_reason


def test_nature_search_keeps_config_until_explicit_selection():
    ui = view('nature')
    ui._set_choices(ui.nature, [('0', 'Fuerte'), ('1', 'Huraña')])
    ui._set_selection(ui.nature, 0)
    ui.nature.on_focus(SimpleNamespace(control=ui.nature))
    assert ui.nature.value is None and ui.nature.data == '0'
    ui.nature.text = 'hur'
    ui.model.configure_param.assert_not_called()
    ui.nature.on_blur(SimpleNamespace(control=ui.nature))
    assert ui.nature.value == '0' and ui.nature.text == 'Fuerte'
    ui.nature.value = '1'
    ui.nature.on_select(SimpleNamespace(control=ui.nature))
    ui.model.configure_param.assert_called_once_with('nature', 1)


def test_idle_recovery_notice_is_visible_without_resending():
    ui = view('validator')
    ui.model.recovery_notice = 'Hay una devolución pendiente de una sesión anterior.'
    ui.refresh(update=False)
    assert ui.status.value == ui.model.recovery_notice
    ui.model.return_original_now.assert_not_called()
    ui.model.start.assert_not_called()


def test_finished_run_can_return_to_configuration_without_starting_another_trade():
    ui = view('level')
    received(ui, 'done')
    ui.model.return_pending = False
    ui.model.active = False
    ui.model.busy = False
    def reset():
        ui.model.slots = [None] * 6
        ui.model.received_info = None
        ui.model.phase = 'idle'
    ui.model.reset.side_effect = reset
    ui.refresh(update=False)
    assert ui.new_run.visible and not ui.start.visible
    assert ui.body.controls == [ui.card]
    ui._new_run(None)
    ui.model.reset.assert_called_once()
    assert ui.body.controls == [ui.intro]
    assert ui.start.visible and not ui.new_run.visible
    ui.model.start.assert_not_called()


def test_active_run_cannot_reset_through_queued_configure_action():
    ui = view('modifier')
    received(ui)
    assert not ui.new_run.visible and ui.new_run.disabled
    ui._new_run(None)
    ui.model.reset.assert_not_called()
    assert ui.body.controls == [ui.editor_group]
