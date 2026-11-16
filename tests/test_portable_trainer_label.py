from types import SimpleNamespace

import pytest

from gui.portable_trainer_labels import trainer_details, trainer_label
from tests.test_portable_team_view import view
from tests.test_portable_received_view import view as received_view


@pytest.mark.parametrize('game,expected', [
    ('frlg', 'ID 12345 · SID 54321 · ES'),
    ('sv', 'ID 993401 · SID 3559 · ES'),
])
def test_identity_uses_game_display_ids_without_modifying_profile(game, expected):
    profile = dict(ot='María José', tid=12345, sid=54321, language=7)
    assert trainer_details(game, profile) == expected
    assert trainer_label(game, profile) == 'María José · ' + expected
    assert profile == dict(ot='María José', tid=12345, sid=54321, language=7)


def test_unknown_language_remains_identifiable():
    assert trainer_details('frlg', dict(tid=0, sid=1, language=99)).endswith(' · 99')


@pytest.mark.parametrize('factory', [view, received_view])
def test_shared_header_displays_complete_identity_and_preserves_search(factory):
    ui = factory()
    profile = dict(ot='María José', tid=12345, sid=54321, language=7)
    ui.trainer_model.profiles = {'opaque-hash': profile}
    ui.trainer_model.selected_trainer = 'opaque-hash'
    ui._refresh_trainer(False)
    option = next(item for item in ui.trainer.options if item.key == 'opaque-hash')
    assert option.text == trainer_label(ui.model.game, profile)
    assert 'opaque' not in option.text
    assert ui.trainer.tooltip == option.text
    ui.trainer.on_focus(SimpleNamespace(control=ui.trainer))
    ui.trainer.text = 'María'
    ui._refresh_trainer(False)
    assert ui.trainer.value is None
    assert ui.trainer.text == 'María'
    assert ui.trainer.data == 'opaque-hash'
    ui._refresh_trainer(True)
    assert ui.trainer.disabled and ui.find.disabled


def test_base_option_remains_clear_target_with_visible_identity():
    ui = view()
    assert ui.trainer.options[0].text == 'Base de pokeLDN'
    assert ui.trainer.options[0].key == 'base'
    ui.trainer.selected_suffix.on_click(None)
    ui.model.set_trainer.assert_called_once_with('base')
