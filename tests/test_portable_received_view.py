import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from gui.portable_received_view import ReceivedView


def model(mode='modifier'):
    return SimpleNamespace(
        mode=mode, game='sv', settings=SimpleNamespace(sprites=False), active=False, busy=False,
        profiles={}, selected_trainer='base', set_trainer=Mock(),
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


def test_received_trainer_header_is_locked_through_editing():
    ui = view()
    assert ui.trainer.options[0].key == 'base'
    received(ui)
    assert ui.trainer.disabled and ui.find.disabled
    ui._trainer_selected(SimpleNamespace(control=SimpleNamespace(value='base')))
    ui.model.set_trainer.assert_not_called()


def test_received_offer_uses_shared_profile_without_replacing_original_owner():
    ui = view('level')
    profile = {'ot': 'Fixture', 'tid': 12, 'sid': 34, 'gender': 0, 'language': 7}
    ui.trainer_model = SimpleNamespace(profiles={'fixture': profile}, selected_trainer='fixture')
    ui.model.original_owner = {'ot': 'Original'}
    asyncio.run(ui._start(None))
    assert ui.model.profiles == {'fixture': profile}
    assert ui.model.selected_trainer == 'fixture'
    assert ui.model.original_owner == {'ot': 'Original'}
    ui.model.start.assert_awaited_once()


def test_activity_bar_distinguishes_preparing_running_and_failed_start():
    ui = view('level')
    ui.model.active = ui.model.busy = True
    ui.model.phase = 'preparing'
    ui.refresh(update=False)
    assert 'Aún no busca' in ui.phase_label.value
    assert ui.loader.visible
    ui.model.phase = 'running'
    ui.refresh(update=False)
    assert 'Proceso iniciado' in ui.phase_label.value
    ui.model.active = ui.model.busy = False
    ui.model.phase, ui.model.error = 'error', 'Código no válido'
    ui.refresh(update=False)
    assert ui.activity_bar.bgcolor == '#F4DADF'
    assert ui.status.value == 'Código no válido'
    assert not ui.loader.visible


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
    ui.nature.open_button.on_click(None)
    assert ui.nature.value == ui.nature.data == '0'
    ui.nature.picker.query.value = 'hur'
    ui.model.configure_param.assert_not_called()
    asyncio.run(ui.nature.picker.cancel())
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


def test_comparison_shows_only_current_calculated_changes_without_mutating_data():
    from copy import deepcopy
    ui = view('level')
    received(ui, 'review')
    m = ui.model
    m.received_info.update(editable={'level': 5, 'moves': [33, 145, 0, 0]},
                           identity={'ot': 'Original', 'pid': 123, 'tid': 1, 'sid': 2})
    m.results[0] = deepcopy(m.received_info)
    m.results[0]['editable']['level'] = 50
    m._revision = [2] * 6
    m.candidate_revision = 2
    m.states[0] = 'legal'
    before = deepcopy(m.received_info)
    rows = ui._comparison_rows()
    assert [(label, old, new) for label, old, new in rows if old != new] == [('Nivel', '5', '50')]
    ui._comparison(None)
    assert m.received_info == before
    m._revision[0] = 3
    assert ui._comparison_candidate() is None
    assert all(after == '—' for _, _, after in ui._comparison_rows())
    assert ui.comparison.visible
