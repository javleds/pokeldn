"""Courtesy offers must not depend on a player's National Dex unlock."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from pokeldn import pokemon
from pokeldn.app import command
from tests.test_pokemon_service import service  # noqa: F401

GAMES = ("frlg", "lgpe", "swsh", "bdsp", "pla", "sv", "za")
TRAINER = {"ot": "TEST", "tid": 12345, "sid": 54321, "language": 2, "gender": 0}


@pytest.mark.parametrize("game", GAMES)
def test_courtesy_never_draws_from_national_catalog(monkeypatch, game):
    calls = []
    def make(game, species, trainer, *, version):
        calls.append((game, species, trainer, version))
        return dict(file="fixture", species="Magikarp", species_id=129, form_id=0,
                    level=5, legal=True)
    # No species() or random selection is available on this service.
    monkeypatch.setattr(pokemon, "SERVICE", SimpleNamespace(make=make))
    result = command.courtesy_offer(game, TRAINER, "selected-version")
    assert calls == [(game, 129, TRAINER, "selected-version")]
    assert result["legal"] is True
    assert result["summary"].startswith("Magikarp")


@pytest.mark.parametrize("change", [
    {"legal": False}, {"legal": None}, {"species_id": 330},
    {"species_id": 319}, {"form_id": 1},
])
def test_invalid_courtesy_is_rejected_without_random_fallback(monkeypatch, change):
    def make(*args, **kwargs):
        return dict(dict(legal=True, species_id=129, form_id=0), **change)
    monkeypatch.setattr(pokemon, "SERVICE", SimpleNamespace(make=make))
    with pytest.raises(ValueError, match="Magikarp"):
        command.courtesy_offer("frlg", TRAINER)


def test_builder_failure_does_not_fall_back_to_another_species(monkeypatch):
    def make(*args, **kwargs):
        raise pokemon.BuilderError("cannot build")
    monkeypatch.setattr(pokemon, "SERVICE", SimpleNamespace(make=make))
    with pytest.raises(pokemon.BuilderError, match="cannot build"):
        command.courtesy_offer("frlg", TRAINER)


@pytest.mark.parametrize("game,version", [
    ("frlg", "FR"), ("frlg", "LG"),
    ("lgpe", "GP"), ("lgpe", "GE"),
    ("swsh", "SW"), ("swsh", "SH"),
    ("bdsp", "BD"), ("bdsp", "SP"),
    ("pla", "PLA"), ("sv", "SL"), ("sv", "VL"), ("za", "ZA"),
])
def test_real_courtesy_is_legal_non_egg_in_every_game(service, game, version):
    info = command.courtesy_offer(game, TRAINER, version)
    data = Path(info["file"]).read_bytes()
    checked = service.check_bytes(game, data)
    assert checked["legal"] is True, checked.get("report")
    assert checked["species_id"] == 129
    assert checked["form_id"] == 0
    assert not checked["held_item_id"]
    assert service.owner(game, data)["egg"] is False
