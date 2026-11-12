"""Received editing changes a copy; its original identity is not rebuilt."""
import base64

import pytest

from pokeldn import pokemon
from test_pokemon_service import TRAINER, service  # reuse the real helper fixture


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv'])
def test_received_snapshot_and_edits_preserve_origin_and_trainer(service, game):
    built = service.make(game, 25, TRAINER)
    original = base64.b64decode(built['data'])
    before = service.edit_received(game, original)
    updated = service.edit_received(game, original, {'nickname': 'TEST', 'friendship': 255})
    assert before['editable']['species'] == 25
    assert before['editable']['nickname'] == ''
    assert updated['editable']['nickname'] == 'TEST'
    assert updated['editable']['friendship'] == 255
    assert updated['identity'] == before['identity']
    assert set(before['editable']['ivs']) == {'hp', 'atk', 'def', 'spa', 'spd', 'spe'}
    assert len(before['editable']['moves']) == 4
    assert service.edit_received(game, original)['editable']['nickname'] == ''


def test_level_can_decrease_but_legality_is_not_silently_repaired(service):
    built = service.make('sv', 25, TRAINER)
    data = base64.b64decode(built['data'])
    before = service.edit_received('sv', data)
    changed = service.edit_received('sv', data, {'level': 1})
    assert changed['editable']['level'] == 1
    assert changed['identity'] == before['identity']
    assert not changed['legal'] and changed['report']


def test_battle_nature_and_effort_edit_preserve_identity(service):
    data = base64.b64decode(service.make('sv', 25, TRAINER)['data'])
    before = service.edit_received('sv', data)
    changed = service.edit_received('sv', data, {'nature': 3, 'effort': {'atk': 252, 'spe': 252, 'hp': 6}})
    assert changed['editable']['nature'] == 3
    assert changed['editable']['effort']['atk'] == changed['editable']['effort']['spe'] == 252
    assert changed['identity'] == before['identity']
    assert changed['legal']


def test_illegal_effort_combination_is_returned_for_review(service):
    data = base64.b64decode(service.make('sv', 25, TRAINER)['data'])
    reply = service.edit_received('sv', data, {'effort': dict.fromkeys(('hp', 'atk', 'def', 'spa', 'spd', 'spe'), 252)})
    assert reply['editable']['effort']['hp'] == 252
    assert not reply['legal']
    assert reply['report']


@pytest.mark.parametrize('fields', [
    {'trainer': TRAINER}, {'pid': 1}, {'level': 0}, {'level': 101}, {'ivs': {'hp': 32}},
    {'effort': {'hp': 253}}, {'effort': {'unknown': 1}}, {'nature': 25}, {'moves': [1] * 5},
])
def test_unsupported_and_out_of_range_edits_are_rejected(service, fields):
    data = base64.b64decode(service.make('sv', 25, TRAINER)['data'])
    with pytest.raises(pokemon.BuilderError):
        service.edit_received('sv', data, fields)


def test_gen3_nature_change_is_explicit_and_does_not_change_trainer(service):
    data = base64.b64decode(service.make('frlg', 25, TRAINER)['data'])
    before = service.edit_received('frlg', data)
    desired = (before['editable']['nature'] + 1) % 25
    after = service.edit_received('frlg', data, {'nature': desired})
    assert after['editable']['nature'] == desired
    assert after['editable']['gender'] == before['editable']['gender']
    assert after['editable']['shiny'] == before['editable']['shiny']
    for field in ('ot', 'tid', 'sid', 'version', 'met_location', 'met_level', 'tracker'):
        assert after['identity'][field] == before['identity'][field]


def test_impossible_move_is_an_illegal_copy_not_a_rebuilt_pokemon(service):
    data = base64.b64decode(service.make('sv', 25, TRAINER)['data'])
    before = service.edit_received('sv', data)
    result = service.edit_received('sv', data, {'moves': [147, 0, 0, 0]})  # Spore
    assert result['editable']['moves'] == [147, 0, 0, 0]
    assert result['identity'] == before['identity']
    assert not result['legal']


def test_snapshot_tera_type_can_be_used_as_an_explicit_edit(service):
    data = base64.b64decode(service.make('sv', 25, TRAINER)['data'])
    snapshot = service.edit_received('sv', data)['editable']
    assert 0 <= snapshot['tera'] <= 18
    result = service.edit_received('sv', data, {'tera': snapshot['tera']})
    assert result['editable']['tera'] == snapshot['tera']
