import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from gui.portable_team_view import TeamView


def model():
    return SimpleNamespace(
        game='sv', settings=SimpleNamespace(sprites=False), slots=[None] * 6,
        states=['empty'] * 6, errors=[''] * 6, results=[None] * 6, metadata={},
        selected_trainer='base', profiles={}, trainer={'ot': 'POKELDN', 'tid': 1, 'sid': 2, 'gender': 0, 'language': 7},
        busy=False, phase='', completed=0, active_slots=[], logs=[], error='', tools={},
        role='host', version='scarlet', code='', can_start=False, listeners=set(),
        edit=Mock(), add=Mock(), clear=Mock(), validate=AsyncMock(), load_options=AsyncMock(),
        names=AsyncMock(return_value=[]), candidate_moves=Mock(return_value=[]), validate_all=AsyncMock(), set_trainer=Mock(), start=AsyncMock(), stop=Mock(),
    )


def view():
    page = SimpleNamespace(run_task=Mock(), show_dialog=Mock(), pop_dialog=Mock())
    shell = SimpleNamespace(page=page, go=Mock(), screen='team')
    return TeamView(shell, model())


def test_empty_team_shows_species_form_without_creating_a_draft():
    ui = view()
    assert ui.start.disabled
    assert len(ui.basic_controls) == 8
    assert not ui.basic_controls[0].disabled
    assert all(control.disabled for control in ui.basic_controls[1:])
    assert [button.disabled for button in ui.slot_buttons] == [False, True, True, True, True, True]
    ui.model.add.assert_not_called()


def test_later_boxes_ignore_selection_until_previous_has_species():
    ui = view()
    ui._select_slot(5)
    assert ui.selected == 0
    ui.model.slots[0] = {'species': 7, 'level': '5', 'options': {}}
    ui.refresh(update=False)
    assert not ui.slot_buttons[1].disabled and ui.slot_buttons[2].disabled
    controls = tuple(ui.basic_controls)
    ui.tab = 'advanced'
    ui._select_slot(1)
    assert ui.selected == 1 and ui.tab == 'basic' and tuple(ui.basic_controls) == controls
    assert ui.basic_controls[0].value is None
    ui.model.add.assert_not_called()


def test_status_updates_preserve_editor_controls_and_do_not_validate_on_input():
    ui = view()
    ui.model.slots[0] = {'species': 25, 'level': '100', 'nickname': '', 'options': {}}
    ui._draw_editor()
    before = ui.editor.content
    field = ui.editor_controls[1]
    field.value = 'Pika'
    field.on_change(SimpleNamespace(control=field))
    ui.model.edit.assert_called_once_with(0, 'nickname', 'Pika', option=False)
    ui.model.validate.assert_not_called()
    ui.refresh(update=False)
    assert ui.editor.content is before
    asyncio.run(field.on_blur(None))
    ui.model.validate.assert_awaited_once_with(0)


def test_active_session_locks_mutations_but_keeps_logs_and_cancel():
    ui = view()
    ui.model.busy = True
    ui.refresh(update=False)
    assert all(button.disabled for button in ui.slot_buttons)
    assert ui.trainer.disabled and ui.back.disabled and ui.find.disabled
    assert ui.cancel.visible and not ui.cancel.disabled
    assert ui.logs.visible and not ui.logs.disabled
    assert ui.loader.visible and not ui.start.visible


def test_max_effort_respects_species_base_stats_and_total():
    ui = view()
    ui.model.slots[0] = {'species': 25, 'options': {}}
    ui.model.metadata[0] = {'base': [35, 55, 40, 50, 50, 90], 'effort': {'max': 252, 'total': 510}}
    ui._max('effort')
    args = ui.model.edit.call_args
    assert args.args[:2] == (0, 'effort')
    values = args.args[2]
    assert values['spe'] == values['atk'] == 252
    assert sum(values.values()) == 510
    assert max(values.values()) <= 252


def test_dispose_unregisters_listener():
    ui = view()
    assert ui._notified in ui.model.listeners
    ui.dispose()
    assert ui._notified not in ui.model.listeners


def test_queued_input_during_session_does_not_mutate_draft():
    ui = view()
    ui.model.slots[0] = {'species': 25, 'level': '100', 'nickname': '', 'options': {}}
    ui._draw_editor()
    field = ui.editor_controls[1]
    ui.model.busy = True
    field.value = 'Late event'
    field.on_change(SimpleNamespace(control=field))
    asyncio.run(field.on_blur(None))
    ui.model.edit.assert_not_called()
    ui.model.validate.assert_not_called()


def test_illegal_result_preserves_draft_and_disables_exchange():
    ui = view()
    draft = {'species': 25, 'level': '500', 'nickname': 'Keep me', 'options': {}}
    ui.model.slots[0] = draft
    ui.model.states[0] = 'invalid'
    ui.model.errors[0] = 'Nivel inválido\nOtro diagnóstico'
    ui._draw_editor()
    ui.refresh(update=False)
    assert ui.start.disabled
    assert ui.status.value == 'Nivel inválido'
    assert ui.model.slots[0] == draft
    ui.model.clear.assert_not_called()


def test_base_trainer_is_valid_and_unmatched_search_restores_selection():
    ui = view()
    dropdown = ui.trainer
    assert dropdown.value == 'base'
    assert dropdown.editable and dropdown.enable_filter and dropdown.enable_search
    assert next(o.text for o in dropdown.options if o.key == 'base') == 'Base de pokeLDN'
    dropdown.text = 'No existe'
    dropdown.value = None
    dropdown.on_select(SimpleNamespace(control=dropdown))
    ui.model.set_trainer.assert_not_called()
    dropdown.on_blur(SimpleNamespace(control=dropdown))
    assert dropdown.value == 'base'
    assert dropdown.text == 'Base de pokeLDN'


def test_search_selection_survives_blur():
    ui = view()
    callback = Mock()
    dropdown = ui.dropdown([('1', 'Uno'), ('2', 'Dos')], '1', callback)
    dropdown.value = '2'
    dropdown.on_select(SimpleNamespace(control=dropdown))
    dropdown.text = 'Otra búsqueda'
    dropdown.on_blur(SimpleNamespace(control=dropdown))
    assert dropdown.value == '2' and dropdown.text == 'Dos'
    callback.assert_called_once()


def test_clear_selector_resets_value_and_cannot_mutate_busy_session():
    ui = view()
    callback = Mock()
    dropdown = ui.dropdown([('', 'Automático'), ('1', 'Uno')], '1', callback, clear_value='')
    dropdown.selected_suffix.on_click(None)
    assert dropdown.value == '' and dropdown.text == 'Automático'
    callback.assert_called_once()
    ui.model.busy = True
    dropdown.selected_suffix.on_click(None)
    assert callback.call_count == 1


def test_clear_trainer_returns_to_valid_base():
    ui = view()
    ui.trainer.selected_suffix.on_click(None)
    assert ui.trainer.value == 'base'
    ui.model.set_trainer.assert_called_once_with('base')


def test_status_follows_selected_slot_while_exchange_remains_blocked():
    ui = view()
    ui.model.slots[0] = {'species': 7, 'options': {}}
    ui.model.states[0] = 'legal'
    ui.model.errors[1] = 'Elige una especie.'
    ui.refresh(update=False)
    assert ui.status.value == 'Pokémon válido · Guardado automáticamente'
    assert ui.start.disabled
    ui.selected = 1
    ui.refresh(update=False)
    assert ui.status.value == 'Elige una especie.'
    ui.selected = 0
    ui.model.errors[1] = ''
    ui.model.states[1] = 'validating'
    ui.refresh(update=False)
    assert ui.status.value == 'Pokémon válido · Guardado automáticamente'
    assert ui.start.disabled


def test_commit_uses_validation_as_single_metadata_and_error_owner():
    ui = view()
    ui.model.slots[0] = {'species': 7, 'options': {}}
    ui.model.load_options.side_effect = ValueError('obsolete metadata error')
    asyncio.run(ui._commit(0, load_options=True))
    ui.model.validate.assert_awaited_once_with(0)
    ui.model.load_options.assert_not_awaited()
    assert not ui.loading_error


def test_focus_clears_query_without_changing_committed_option():
    ui = view()
    callback = Mock()
    dropdown = ui.dropdown([('', 'Automático'), ('1', 'Burbuja')], '', callback)
    dropdown.text = 'Automático'
    dropdown.on_focus(SimpleNamespace(control=dropdown))
    assert dropdown.text == ''
    assert dropdown.value is None
    assert dropdown.data == ''
    dropdown.text = 'bur'
    dropdown.on_blur(SimpleNamespace(control=dropdown))
    assert dropdown.text == 'Automático'
    callback.assert_not_called()
    dropdown.on_focus(SimpleNamespace(control=dropdown))
    dropdown.value = '1'
    dropdown.on_select(SimpleNamespace(control=dropdown))
    dropdown.on_blur(SimpleNamespace(control=dropdown))
    assert dropdown.value == '1' and dropdown.text == 'Burbuja'
    callback.assert_called_once()


def test_non_search_selector_does_not_clear_on_focus():
    ui = view()
    dropdown = ui.dropdown([('host', 'Anfitrión')], 'host', Mock(), search=False)
    assert dropdown.on_focus is None


def test_basic_controls_and_options_survive_slot_navigation():
    ui = view()
    ui.species_names = [{'id': 7, 'name': 'Squirtle'}, {'id': 4, 'name': 'Charmander'}]
    ui.move_names = [{'id': 145, 'name': 'Burbuja'}, {'id': 53, 'name': 'Lanzallamas'}]
    ui.model.candidate_moves.side_effect = lambda i: [145] if i == 0 else [53]
    ui.model.slots[:2] = [dict(species=7, level='10', nickname='Shell', options={}),
                         dict(species=4, level='20', nickname='Flame', options={})]
    ui._draw_editor()
    controls = tuple(ui.editor_controls)
    species_options = controls[0].options
    assert [o.key for o in controls[4].options] == ['', '145']
    ui._select_slot(1)
    assert tuple(ui.editor_controls) == controls
    assert controls[0].options is species_options
    assert controls[0].value == '4' and controls[1].value == 'Flame'
    assert [o.key for o in controls[4].options] == ['', '53']
    controls[1].value = 'New'
    controls[1].on_change(SimpleNamespace(control=controls[1]))
    ui.model.edit.assert_called_with(1, 'nickname', 'New', option=False)
    ui.model.load_options.assert_not_called()
    ui.model.validate.assert_not_called()


def test_blur_without_edit_does_not_validate():
    ui = view()
    ui.model.slots[0] = dict(species=7, level='10', options={})
    ui._draw_editor()
    asyncio.run(ui.editor_controls[1].on_blur(None))
    ui.model.validate.assert_not_called()


def test_selected_move_outside_filter_remains_visible():
    ui = view()
    ui.move_names = [{'id': 145, 'name': 'Burbuja'}, {'id': 53, 'name': 'Lanzallamas'}]
    ui.model.candidate_moves.return_value = [145]
    ui.model.slots[0] = dict(species=7, level='10', options={'moves': [53]})
    ui._draw_editor()
    assert ui.editor_controls[4].value == '53'
    assert [o.text for o in ui.editor_controls[4].options] == ['Automático', 'Burbuja', 'Lanzallamas']


def test_statistics_editor_is_reused_when_returning_to_unchanged_slot():
    ui = view()
    ui.model.slots[:2] = [dict(species=7, level='10', options={}),
                         dict(species=4, level='20', options={})]
    ui.model.metadata = {0: {}, 1: {}}
    ui.tab = 'stats'
    ui._draw_editor()
    first = ui.editor.content
    controls = tuple(ui.editor_controls)
    ui._select_slot(1)
    ui._select_slot(0)
    assert ui.editor.content is first
    assert tuple(ui.editor_controls) == controls
    ui.model.load_options.assert_not_called()


def test_dynamically_populated_selector_keeps_bounded_menu():
    ui = view()
    dropdown = ui.dropdown([('', 'Automático')], '', Mock())
    ui._set_choices(dropdown, [(str(i), f'Move {i}') for i in range(400)])
    assert dropdown.menu_height == 160
    assert dropdown.menu_width == 280
    assert dropdown.width == 280
    assert dropdown.menu_style.max_size.width == 280
    assert dropdown.menu_style.max_size.height == 160


def test_find_trainer_offers_optional_original_return():
    ui = view()
    ui._find_trainer(None)
    dialog = ui.page.show_dialog.call_args.args[0]
    switch = dialog.content.content.controls[1]
    assert switch.value is True
    switch.value = False
    asyncio.run(dialog.actions[1].on_click(None))
    ui.model.start.assert_awaited_once_with(discover=True, return_original=False)


def test_discovery_received_view_keeps_actions_and_hides_editor():
    ui = view()
    m = ui.model
    m.discovering = m.return_original = m.busy = True
    m.completed = 1
    m.return_pending = True
    m.received_info = {'species_id': 7, 'species': 'Squirtle', 'level': 5, 'ot': 'Fixture'}
    m.received_error = ''
    m.found_trainer = {'ot': 'Fixture'}
    ui.refresh(update=False)
    assert ui.session.visible and not ui.editor.visible
    assert all(not button.visible for button in ui.slot_buttons)
    assert ui.slot_row.visible and ui.logs.visible and ui.cancel.visible
    assert ui.logs.visible and ui.cancel.visible and ui.loader.visible
    m.busy = False
    m.phase = 'stopped'
    ui.refresh(update=False)
    assert 'Devolución pendiente' in ui.status.value
    assert ui.session.visible and not ui.cancel.visible


def test_basic_max_checkboxes_apply_only_to_selected_slot_and_reset_to_auto():
    ui = view()
    ui.model.slots[:2] = [{'species': 7, 'options': {}}, {'species': 25, 'options': {}}]
    ui.model.metadata[1] = {'base': [35, 55, 40, 50, 50, 90], 'effort': {'max': 252, 'total': 510}}
    ui.selected = 1
    ui._toggle_max('effort', True)
    index, key, values = ui.model.edit.call_args.args
    assert (index, key) == (1, 'effort')
    assert sum(values.values()) == 510
    assert values['spe'] == values['atk'] == 252
    ui._toggle_max('friendship', True)
    ui.model.edit.assert_called_with(1, 'friendship', 255, option=True)
    ui._toggle_max('effort', False)
    ui.model.edit.assert_called_with(1, 'effort', None, option=True)
    ui._toggle_max('friendship', False)
    ui.model.edit.assert_called_with(1, 'friendship', None, option=True)


def test_max_checkboxes_follow_each_box_and_lock_during_trade():
    ui = view()
    ui.model.slots[:2] = [{'species': 7, 'options': {'friendship': 255}}, {'species': 25, 'options': {}}]
    ui.refresh(update=False)
    assert ui.max_checks['friendship'].value
    assert ui.max_checks['friendship'].visible
    assert ui.max_checks['effort'].disabled  # metadata pending
    ui.selected = 1
    ui.refresh(update=False)
    assert not ui.max_checks['friendship'].value
    ui.model.busy = True
    ui.refresh(update=False)
    assert all(c.disabled for c in ui.max_checks.values())
    ui._toggle_max('friendship', False)
    ui.model.edit.assert_not_called()


def test_trainer_refresh_does_not_replace_active_query():
    ui = view()
    ui.trainer.on_focus(SimpleNamespace(control=ui.trainer))
    ui.trainer.text = 'search'
    ui.refresh(update=False)
    assert ui.trainer.value is None
    assert ui.trainer.data == 'base'
    assert ui.trainer.text == 'search'
    ui.trainer.on_blur(SimpleNamespace(control=ui.trainer))
    assert ui.trainer.value == 'base'
    assert ui.trainer.text == 'Base de pokeLDN'
    ui.model.set_trainer.assert_not_called()


def test_connection_role_toggle_only_saves_when_confirmed():
    ui = view()
    ui.model.tools = {key: SimpleNamespace(fields=[]) for key in ('host', 'join')}
    ui.model.configure = Mock()
    ui._connection(None)
    dialog = ui.page.show_dialog.call_args.args[0]
    role = dialog.content.content.controls[0].content.controls[0].controls[1]
    assert [segment.value for segment in role.segments] == ['host', 'join']
    assert role.selected == ['host']
    assert not role.allow_empty_selection and not role.allow_multiple_selection
    role.selected = ['join']
    dialog.actions[0].on_click(None)
    ui.model.configure.assert_not_called()
    ui._connection(None)
    dialog = ui.page.show_dialog.call_args.args[0]
    role = dialog.content.content.controls[0].content.controls[0].controls[1]
    assert role.selected == ['host']
    role.selected = ['join']
    asyncio.run(dialog.actions[1].on_click(None))
    ui.model.configure.assert_called_once_with('join', 'scarlet', '')


def test_connection_single_role_remains_selected():
    ui = view()
    ui.model.tools = {'host': SimpleNamespace(fields=[])}
    ui._connection(None)
    dialog = ui.page.show_dialog.call_args.args[0]
    role = dialog.content.content.controls[0].content.controls[0].controls[1]
    assert [segment.value for segment in role.segments] == ['host']
    assert role.selected == ['host'] and not role.allow_empty_selection


def discovery_result(ui, *, return_original=True, completed=2, phase='done', busy=False, error=''):
    m = ui.model
    m.discovering = True
    m.return_original = return_original
    m.completed = completed
    m.phase, m.busy, m.error = phase, busy, error
    m.return_pending = return_original and completed == 1
    m.received_info = None
    m.received_error = ''
    m.found_trainer = dict(ot='RED', tid=12345, sid=54321)
    m.game = 'frlg'


def test_identification_success_returns_to_team_with_trainer_identifiers():
    for return_original, completed in ((False, 1), (True, 2)):
        ui = view()
        discovery_result(ui, return_original=return_original, completed=completed)
        # Revalidation can still run after the trainer has been saved.
        ui.model.states[0] = 'validating'
        ui.refresh(update=False)
        assert ui.editor.visible and not ui.session.visible
        assert all(button.visible for button in ui.slot_buttons)
        assert not ui.return_to_team.visible
        assert 'Entrenador identificado: RED' in ui.status.value
        assert 'ID 12345' in ui.status.value and 'SID 54321' in ui.status.value
        # The view must not disrupt the controller's final validation/return journal.
        assert ui.model.discovering


def test_identification_waits_for_return_and_process_exit():
    for completed, busy, phase in ((1, True, 'running'), (2, True, 'running'), (1, False, 'error')):
        ui = view()
        discovery_result(ui, completed=completed, busy=busy, phase=phase)
        ui.refresh(update=False)
        assert ui.session.visible and not ui.editor.visible
        assert ui.return_to_team in ui.slot_row.controls
        assert ui.return_to_team.visible
        assert ui.return_to_team.disabled == busy
        if busy:
            ui._return_to_team(None)
            assert not ui.discovery_dismissed


def test_failed_or_cancelled_identification_does_not_auto_return():
    for phase, error in (('error', 'No se guardó el entrenador'), ('stopped', '')):
        ui = view()
        discovery_result(ui, phase=phase, error=error)
        ui.refresh(update=False)
        assert ui.session.visible
        assert not ui.editor.visible
        assert '✓ Entrenador identificado' not in ui.status.value


def test_manual_return_preserves_pending_warning_and_new_run_shows_discovery():
    ui = view()
    discovery_result(ui, completed=1, phase='stopped')
    ui.refresh(update=False)
    ui.return_to_team.on_click(None)
    assert ui.editor.visible and not ui.session.visible
    assert 'Devolución pendiente' in ui.status.value
    assert ui.model.discovering
    discovery_result(ui, completed=0, busy=True, phase='preparing')
    ui.refresh(update=False)
    assert ui.session.visible and not ui.discovery_dismissed
