"""Trainer transfers preserve raw IDs and never overwrite team drafts."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gui.portable_trainers import TrainerLibrary, TYPE, export_filename, profile_id
from gui.portable_team import Team, TeamStore
from pokeldn.app.settings import Settings


PROFILE = dict(ot='RED', tid=12345, sid=54321, gender=0, language=7)


def entry(game='frlg', profile=None, version=None):
    return dict(schema=1, type=TYPE, game=game, game_version=version, profile=profile or deepcopy(PROFILE))


@pytest.fixture
def library(tmp_path):
    setup = SimpleNamespace(settings=Settings(), busy=False, checking=False, session_busy=False)
    teams = {game: Team(game, setup, store=TeamStore(game, root=tmp_path)) for game in ('frlg', 'sv', 'za')}
    return TrainerLibrary(setup, teams=teams)


def test_individual_and_bulk_export_are_arrays_with_raw_ids(library):
    first = entry(version='firered')
    second = entry('sv', dict(PROFILE, ot='Nemona', tid=65535, sid=65535), 'scarlet')
    assert library.import_json(json.dumps([first, second]).encode()) == 2
    rows = library.entries()
    one = json.loads(library.export_json([rows[0]]))
    assert one == [first]
    both = json.loads(library.export_json())
    assert both == [first, second]
    assert library.import_json(library.export_json()) == 0
    assert len(library.entries()) == 2


def test_import_matches_existing_identified_profile_key(library):
    key = profile_id(PROFILE)
    team = library._team('frlg')
    team.profiles[key] = deepcopy(PROFILE)
    team.save()
    assert library.import_json(json.dumps([entry()]).encode()) == 0
    assert list(team.profiles) == [key]


def test_import_preserves_drafts_selected_profile_and_configuration(library):
    team = library._team('frlg')
    team.slots[0] = dict(species=129, level='5')
    original = deepcopy(team.slots)
    team.code = 'old code'
    library.import_json(json.dumps([entry()]).encode())
    assert team.slots == original
    assert team.selected_trainer == 'base'
    saved = team.store.load()
    assert saved['slots'] == original
    assert saved['code'] == 'old code'
    assert saved['profiles'][profile_id(PROFILE)] == PROFILE


def test_delete_selected_profile_restores_base_and_invalidates(library):
    library.import_json(json.dumps([entry()]).encode())
    team = library._team('frlg')
    key = profile_id(PROFILE)
    team.selected_trainer = key
    team.slots[0] = dict(species=129)
    team.states[0] = 'legal'
    team.results[0] = {'file': 'old result'}
    team.metadata[0] = {'old': True}
    library.delete('frlg', key)
    assert not team.profiles
    assert team.selected_trainer == 'base'
    assert team.states[0] == 'pending'
    assert not team.results[0] and not team.metadata
    assert team.store.load()['selected_trainer'] == 'base'


def test_search_game_name_language_and_display_ids(library):
    library.import_json(json.dumps([entry(), entry('sv', dict(PROFILE, ot='NEMONA'))]).encode())
    assert [r['game'] for r in library.entries('rojo_verde')] == ['frlg']
    assert [r['game'] for r in library.entries('nemona', game='sv')] == ['sv']
    assert len(library.entries('ES')) == 2
    assert library.entries('12345', game='frlg')
    assert not library.entries('not-found')


@pytest.mark.parametrize('change', [
    {'schema': True}, {'type': 'other'}, {'game': '../sv'}, {'game_version': 'scarlet'},
    {'profile': dict(PROFILE, tid=True)}, {'profile': dict(PROFILE, tid=65536)},
    {'profile': dict(PROFILE, sid=-1)}, {'profile': dict(PROFILE, gender=2)},
    {'profile': dict(PROFILE, language=9)}, {'profile': dict(PROFILE, ot='toolong8')},
    {'profile': dict(PROFILE, ot='RED\n')}, {'profile': dict(PROFILE, ot='')},
])
def test_import_validates_entire_batch_before_mutation(library, change):
    bad = dict(entry(), **change)
    with pytest.raises(ValueError):
        library.import_json(json.dumps([entry(), bad]).encode())
    assert not library.entries()
    assert not library._team('frlg').store.path.exists()


@pytest.mark.parametrize('payload', [b'{}', b'null', b'[', b'\xff', b'[]' * (1024 * 1024 + 1)])
def test_invalid_payload_is_rejected(library, payload):
    with pytest.raises(ValueError):
        library.import_json(payload)


@pytest.mark.parametrize('field', ['busy', 'checking', 'session_busy'])
def test_setup_activity_blocks_mutations(library, field):
    library.import_json(json.dumps([entry()]).encode())
    setattr(library.setup, field, True)
    with pytest.raises(ValueError):
        library.delete('frlg', profile_id(PROFILE))
    with pytest.raises(ValueError):
        library.import_json(json.dumps([entry('sv')]).encode())
    assert len(library.entries()) == 1


def test_corrupt_team_is_not_overwritten(library):
    team = library._team('frlg')
    team._storage_error = 'corrupt'
    with pytest.raises(ValueError, match='corrupt'):
        library.import_json(json.dumps([entry()]).encode())
    assert not team.store.path.exists()


def test_safe_export_path_and_optional_unknown_version(library):
    library.import_json(json.dumps([entry('sv', dict(PROFILE, ot='A/../B:é'))]).encode())
    row = library.entries()[0]
    name = export_filename(row)
    assert name.parent.name == 'escarlata_purpura'
    assert '..' not in name.name and '/' not in name.name and ':' not in name.name
    assert name.suffix == '.json'
    assert json.loads(library.export_json())[0]['game_version'] is None


def test_save_failure_rolls_back_in_memory_profile_mutation(library, monkeypatch):
    team = library._team('frlg')
    monkeypatch.setattr(team, 'save', Mock(side_effect=OSError('disk full')))
    with pytest.raises(OSError):
        library.import_json(json.dumps([entry()]).encode())
    assert not team.profiles


def test_delete_never_removes_base(library):
    with pytest.raises(ValueError):
        library.delete('frlg', 'base')
