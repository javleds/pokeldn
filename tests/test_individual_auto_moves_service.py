"""Three-state moves preserve explicit empties and received Pokémon identity."""
import base64

import pytest

from pokeldn import pokemon
from tests.test_pokemon_service import TRAINER, service  # noqa: F401


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za'])
def test_new_generation_and_received_slots_complete_only_automatic(service, game):
    made = service.make(game, 25, TRAINER, level=100,
                        options={'move_slots': [None, 85, None, None]})
    original = base64.b64decode(made['data'])
    before = service.edit_received(game, original)
    assert made['legal'] and before['editable']['moves'][1] == 85
    assert all(before['editable']['moves'])
    # Clear first so the subsequent edit must actually populate former empty slots.
    sparse = service.edit_received(game, original, {'moves': [85, 0, 0, 0]})
    result = service.edit_received(game, base64.b64decode(sparse['data']),
                                   {'move_slots': [None, 85, None, None]})
    moves = result['editable']['moves']
    assert result['legal'], result['report']
    assert moves[1] == 85 and len(set(moves)) == 4 and all(moves)
    assert result['identity'] == before['identity']
    assert service.edit_received(game, original) == before


@pytest.mark.parametrize('slots', [[85, None, None, 0], [85, 0, 0, 0]])
def test_explicit_empty_stays_empty_during_generation_and_edit(service, slots):
    made = service.make('lgpe', 25, TRAINER, level=100, options={'move_slots': slots})
    original = base64.b64decode(made['data'])
    result = service.edit_received('lgpe', original, {'move_slots': slots})
    assert made['legal'] and result['legal']
    moves = result['editable']['moves']
    assert moves[0] == 85
    for index, requested in enumerate(slots):
        assert moves[index] != 0 if requested is None else moves[index] == requested


@pytest.mark.parametrize('slots', [[0, 0, 0, 0], [85, 0, 98, 0], [147, None, None, None]])
def test_illegal_selection_is_reported_without_rewriting_manual_or_empty(service, slots):
    original = base64.b64decode(service.make('lgpe', 25, TRAINER, level=100)['data'])
    before = service.edit_received('lgpe', original)
    result = service.edit_received('lgpe', original, {'move_slots': slots})
    assert not result['legal'] and result['report']
    assert result['identity'] == before['identity']
    for index, requested in enumerate(slots):
        if requested is not None:
            assert result['editable']['moves'][index] == requested


@pytest.mark.parametrize('slots', [[85], [85, 85, None, None], [None, -1, None, None],
                                   [None, 65535, None, None], [None, True, None, None],
                                   [None, '85', None, None]])
def test_invalid_slot_contract_rejected_in_both_paths(service, slots):
    original = base64.b64decode(service.make('lgpe', 25, TRAINER)['data'])
    with pytest.raises(pokemon.BuilderError):
        service.make('lgpe', 25, TRAINER, options={'move_slots': slots})
    with pytest.raises(pokemon.BuilderError):
        service.edit_received('lgpe', original, {'move_slots': slots})


def test_conflicting_contracts_are_rejected(service):
    original = base64.b64decode(service.make('lgpe', 25, TRAINER)['data'])
    with pytest.raises(pokemon.BuilderError):
        service.edit_received('lgpe', original, {'moves': [85], 'move_slots': [None] * 4})
    with pytest.raises(pokemon.BuilderError):
        service.make('lgpe', 25, TRAINER,
                     options={'auto_move_slots': [0] * 4, 'move_slots': [None] * 4})


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za'])
def test_all_automatic_fills_received_empty_slots(service, game):
    original = base64.b64decode(service.make(game, 25, TRAINER, level=100)['data'])
    sparse = service.edit_received(game, original, {'moves': [85, 0, 0, 0]})
    result = service.edit_received(game, base64.b64decode(sparse['data']),
                                   {'move_slots': [None] * 4})
    assert result['legal'], result['report']
    assert all(result['editable']['moves']) and len(set(result['editable']['moves'])) == 4
    assert result['identity'] == sparse['identity']


@pytest.mark.parametrize('slots', [[0, 0, 0, 0], [85, 0, 98, 0]])
def test_generation_rejects_illegal_empty_arrangements_instead_of_compacting(service, slots):
    with pytest.raises(pokemon.BuilderError):
        service.make('lgpe', 25, TRAINER, level=100, options={'move_slots': slots})


@pytest.mark.parametrize('slots', [[None] * 4, [85, None, None, 0], [85, 0, 0, 0]])
def test_automatic_edit_preserves_explicit_illegal_lgpe_effort(service, slots):
    original = base64.b64decode(service.make('lgpe', 25, TRAINER, level=100)['data'])
    effort = dict.fromkeys(('hp', 'atk', 'def', 'spa', 'spd', 'spe'), 0)
    before = service.edit_received('lgpe', original, {'effort': effort})
    result = service.edit_received('lgpe', original, {'effort': effort, 'move_slots': slots})
    assert not before['legal'] and not result['legal']
    assert result['editable']['effort'] == effort
    assert result['identity'] == before['identity']


def test_automatic_generation_does_not_silently_raise_explicit_lgpe_effort(service):
    effort = dict.fromkeys(('hp', 'atk', 'def', 'spa', 'spd', 'spe'), 0)
    with pytest.raises(pokemon.BuilderError):
        service.make('lgpe', 25, TRAINER, level=100,
                     options={'effort': effort, 'move_slots': [None] * 4})


def test_automatic_generation_preserves_legal_explicit_lgpe_effort(service):
    effort = dict.fromkeys(('hp', 'atk', 'def', 'spa', 'spd', 'spe'), 150)
    made = service.make('lgpe', 25, TRAINER, level=100,
                        options={'effort': effort, 'move_slots': [None] * 4})
    result = service.edit_received('lgpe', base64.b64decode(made['data']))
    assert made['legal'] and result['editable']['effort'] == effort
