"""Portable automatic slots opt in without changing the exact upstream moves contract."""
import base64
import pytest
from pokeldn import pokemon
from tests.test_pokemon_service import service, TRAINER  # noqa: F401


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za'])
def test_mixed_slots_keep_explicit_position_and_complete_legal_moves(service, game):
    result = service.make(game, 25, TRAINER, level=100,
                          options={'moves': [85], 'auto_move_slots': [0, 85, 0, 0]})
    data = base64.b64decode(result['data'])
    moves = service.edit_received(game, data, {})['editable']['moves']
    assert result['legal'] and service.check_bytes(game, data)['legal']
    assert moves[1] == 85
    assert len(set(moves)) == 4 and all(moves)


def test_exact_legacy_moves_are_not_automatically_completed(service):
    result = service.make('lgpe', 3, TRAINER, level=100, options={'moves': [22]})
    assert result['moves'] == ['Vine Whip']


def test_auto_slots_are_authoritative_over_compact_moves(service):
    result = service.make('lgpe', 25, TRAINER, level=100,
                          options={'moves': [150], 'auto_move_slots': [0, 0, 0, 85]})
    moves = service.edit_received('lgpe', base64.b64decode(result['data']), {})['editable']['moves']
    assert result['legal'] and moves[3] == 85 and 150 not in moves


def test_species_with_few_moves_keeps_manual_move_without_invalid_empty_gap(service):
    result = service.make('lgpe', 129, TRAINER, level=5,
                          options={'auto_move_slots': [0, 0, 0, 150]})
    moves = service.edit_received('lgpe', base64.b64decode(result['data']), {})['editable']['moves']
    assert result['legal'] and moves[0] == 150
    assert len([move for move in moves if move]) < 4


@pytest.mark.parametrize('slots', [[85], [0, 0, 85, 85], [0, 0, -1, 0],
                                   [0, 0, 65535, 0], [0, None, 0, 0], [0, True, 0, 0]])
def test_auto_slots_reject_invalid_contract(service, slots):
    with pytest.raises(pokemon.BuilderError):
        service.make('lgpe', 25, TRAINER, level=100, options={'auto_move_slots': slots})


def test_impossible_manual_move_is_not_replaced(service):
    with pytest.raises(pokemon.BuilderError):
        service.make('lgpe', 129, TRAINER, level=100,
                     options={'auto_move_slots': [0, 85, 0, 0]})


@pytest.mark.parametrize('slots', [[85, 0, 0, 87], [85, 87, 98, 86]])
def test_multiple_explicit_moves_are_preserved(service, slots):
    result = service.make('lgpe', 25, TRAINER, level=100, options={'auto_move_slots': slots})
    moves = service.edit_received('lgpe', base64.b64decode(result['data']), {})['editable']['moves']
    assert result['legal'] and len(set(moves)) == 4 and all(moves)
    assert all(not wanted or moves[index] == wanted for index, wanted in enumerate(slots))
