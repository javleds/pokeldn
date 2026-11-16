import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from pokeldn import pokemon
from tests.test_pokemon_service import service, TRAINER  # noqa: F401


def exact(monkeypatch, game, data):
    monkeypatch.setenv('POKELDN_EXACT_OFFER_GAME', game)
    monkeypatch.setenv('POKELDN_EXACT_OFFER_SHA256', hashlib.sha256(pokemon.entity_bytes(game, data)).hexdigest())
    monkeypatch.setattr(pokemon, '_exact_offer_verified', None)


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za'])
def test_exact_offer_preserves_entity_and_skips_plugins(service, monkeypatch, game):
    info = service.make(game, 129, TRAINER)
    data = Path(info['file']).read_bytes()
    exact(monkeypatch, game, data)
    def forbidden(*args):
        raise AssertionError('An exact offer must not be edited')
    monkeypatch.setattr(pokemon, 'plugin_edits', forbidden)
    monkeypatch.setattr(service, 'prepare', forbidden)
    result = pokemon.prepare_offer(game, data, transform=forbidden)
    expected = pokemon.offer_bytes(game, pokemon.entity_bytes(game, data))
    assert result == expected
    if game in ('swsh', 'pla'):
        from pokeldn import gen8
        from pokeldn.pla import pokemon as pa8
        native = pa8 if game == 'pla' else gen8
        encrypted = native.encrypt(native.load(data))
        assert pokemon.prepare(game, encrypted) == encrypted
        assert pokemon.validate(game, encrypted) == encrypted


def test_wrong_hash_or_game_is_rejected_before_service(monkeypatch):
    exact(monkeypatch, 'frlg', b'original')
    monkeypatch.setattr(pokemon, 'SERVICE', SimpleNamespace())
    with pytest.raises(pokemon.BuilderError, match='changed'):
        pokemon.prepare_offer('frlg', b'changed')
    with pytest.raises(pokemon.BuilderError, match='game'):
        pokemon.prepare_offer('sv', b'original')


@pytest.mark.parametrize('kwargs', [{'fresh': True}, {'fields': {'nickname': 'edited'}}])
def test_exact_offer_rejects_requested_mutations(monkeypatch, kwargs):
    exact(monkeypatch, 'frlg', b'original')
    monkeypatch.setattr(pokemon, 'SERVICE', SimpleNamespace(check_bytes=lambda *a: {'legal': True}))
    with pytest.raises(pokemon.BuilderError, match='cannot change'):
        pokemon.prepare_offer('frlg', b'original', **kwargs)


def test_exact_offer_never_allows_illegal_original(monkeypatch):
    exact(monkeypatch, 'frlg', b'original')
    monkeypatch.setattr(pokemon, 'SERVICE', SimpleNamespace(allow_illegal=True,
        check_bytes=lambda *a: {'legal': False, 'report': 'Illegal record'}))
    with pytest.raises(pokemon.BuilderError, match='Illegal record'):
        pokemon.prepare_offer('frlg', b'original')


def test_secondary_native_check_rejects_actual_edit(service, monkeypatch):
    from pokeldn import gen8
    info = service.make('swsh', 129, TRAINER)
    data = Path(info['file']).read_bytes()
    exact(monkeypatch, 'swsh', data)
    pokemon.prepare_offer('swsh', data)
    changed = bytearray(gen8.load(data))
    changed[0x0C] ^= 1
    with pytest.raises(pokemon.BuilderError, match='changed'):
        pokemon.prepare('swsh', gen8.encrypt(changed))
