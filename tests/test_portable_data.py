import json
import os
from pathlib import Path

import pytest

from pokeldn.app import portable_data as data


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('USERPROFILE', str(tmp_path / 'home'))
    monkeypatch.setenv('APPDATA', str(tmp_path / 'roaming'))
    monkeypatch.delenv('POKELDN_DATA', raising=False)
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setattr(data.sys, 'platform', 'linux')
    return tmp_path / 'home'


def populate(path, name='settings.json'):
    path.mkdir(parents=True, exist_ok=True)
    (path / name).write_text('fixture', encoding='utf-8')


def test_new_install_uses_canonical_and_persists_absolute_choice(home, tmp_path):
    root = tmp_path / 'checkout'
    chosen = data.resolve(root)
    assert chosen == home / '.local/share/pokeldn-portable'
    assert chosen.is_dir()
    assert json.loads(data.binding_path().read_text()) == {'version': 1, 'path': str(chosen)}
    assert not (root / '.local-preview/portable').exists()


def test_existing_legacy_data_is_preserved_without_moving(home, tmp_path):
    root = tmp_path / 'checkout'
    legacy = root / '.local-preview/portable'
    populate(legacy)
    assert data.resolve(root) == legacy
    assert (legacy / 'settings.json').read_text() == 'fixture'
    assert not (home / '.local/share/pokeldn-portable').exists()
    # After an update, the binding wins over a different version checkout.
    assert data.resolve(tmp_path / 'new-version') == legacy


def test_existing_canonical_is_reused(home, tmp_path):
    canonical = home / '.local/share/pokeldn-portable'
    populate(canonical)
    assert data.resolve(tmp_path / 'checkout') == canonical


def test_two_populated_locations_require_choice_without_writes(home, tmp_path):
    root = tmp_path / 'checkout'
    locations = data.candidates(root)
    for path in locations:
        populate(path)
    with pytest.raises(data.ChoiceRequired) as raised:
        data.resolve(root)
    assert raised.value.candidates == locations
    assert not data.binding_path().exists()
    assert all((path / 'settings.json').read_text() == 'fixture' for path in locations)
    assert data.save_choice(locations[1]) == locations[1]
    assert data.resolve(root) == locations[1]


def test_explicit_override_never_creates_folder_or_updates_binding(home, tmp_path, monkeypatch):
    prior = data.resolve(tmp_path / 'checkout')
    record = data.binding_path().read_bytes()
    override = tmp_path / 'isolated-fixture'
    monkeypatch.setenv('POKELDN_DATA', str(override))
    assert data.resolve(tmp_path / 'checkout') == override
    assert not override.exists()
    assert data.binding_path().read_bytes() == record
    monkeypatch.delenv('POKELDN_DATA')
    assert data.resolve(tmp_path / 'checkout') == prior


def test_explicit_relative_override_is_resolved_before_launch(home, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('POKELDN_DATA', 'isolated')
    assert data.resolve(tmp_path / 'checkout') == tmp_path / 'isolated'
    assert not data.binding_path().exists()


def test_symlink_alias_is_only_one_candidate(home, tmp_path):
    root = tmp_path / 'checkout'
    canonical, legacy = data.candidates(root)
    populate(canonical)
    legacy.parent.mkdir(parents=True)
    legacy.symlink_to(canonical, target_is_directory=True)
    assert data.candidates(root) == [canonical]
    assert data.resolve(root) == canonical


def test_ds_store_alone_is_empty_but_empty_bank_folder_is_meaningful(home, tmp_path):
    root = tmp_path / 'checkout'
    canonical, legacy = data.candidates(root)
    populate(canonical, '.DS_Store')
    (legacy / 'Bank').mkdir(parents=True)
    assert data.resolve(root) == legacy


@pytest.mark.parametrize('contents', ['not json', '[]', '{"version":1,"path":"relative"}', '{"version":99,"path":"/invalid"}'])
def test_corrupt_binding_never_falls_back_to_another_profile(home, tmp_path, contents):
    root = tmp_path / 'checkout'
    populate(root / '.local-preview/portable')
    binding = data.binding_path()
    binding.parent.mkdir(parents=True)
    binding.write_text(contents)
    with pytest.raises(data.DataLocationError, match='dañada'):
        data.resolve(root)
    assert binding.read_text() == contents


def test_missing_saved_location_does_not_create_replacement(home, tmp_path):
    selected = tmp_path / 'external-data'
    selected.mkdir()
    data.save_choice(selected)
    selected.rmdir()
    with pytest.raises(data.DataLocationError, match='no existe'):
        data.resolve(tmp_path / 'checkout')
    assert not selected.exists()
    assert not (home / '.local/share/pokeldn-portable').exists()


def test_unreadable_candidate_is_not_silently_ignored(home, tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    _, legacy = data.candidates(root)
    populate(legacy)
    monkeypatch.setattr(data.os, 'access', lambda path, mode: path != legacy)
    with pytest.raises(data.DataLocationError, match='permisos'):
        data.resolve(root)
    assert not data.binding_path().exists()


def test_selecting_file_or_missing_path_does_not_write_binding(home, tmp_path):
    file = tmp_path / 'file'
    file.touch()
    for path in (file, tmp_path / 'missing'):
        with pytest.raises(data.DataLocationError):
            data.save_choice(path)
    assert not data.binding_path().exists()


def test_failed_atomic_save_preserves_previous_choice(home, tmp_path, monkeypatch):
    selected = data.resolve(tmp_path / 'checkout')
    record = data.binding_path().read_bytes()
    another = tmp_path / 'another'
    another.mkdir()
    def failed(*args):
        raise OSError('disk full')
    monkeypatch.setattr(data.os, 'replace', failed)
    with pytest.raises(data.DataLocationError, match='guardar'):
        data.save_choice(another)
    assert data.binding_path().read_bytes() == record
    assert list(data.binding_path().parent.glob('*.tmp')) == []
    assert selected.is_dir()


@pytest.mark.parametrize('platform,relative', [
    ('linux', '.config/pokeldn-portable/portable-data.json'),
    ('darwin', 'Library/Application Support/pokeldn-portable-config/portable-data.json'),
])
def test_platform_binding_locations(home, monkeypatch, platform, relative):
    monkeypatch.setattr(data.sys, 'platform', platform)
    assert data.binding_path() == home / relative


def test_windows_and_xdg_locations(home, tmp_path, monkeypatch):
    monkeypatch.setattr(data.sys, 'platform', 'win32')
    assert data.binding_path() == tmp_path / 'roaming/pokeldn-portable/portable-data.json'
    assert data.candidates(tmp_path)[0] == tmp_path / 'roaming/pokeldn-portable'
    monkeypatch.setattr(data.sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    assert data.binding_path() == tmp_path / 'config/pokeldn-portable/portable-data.json'
    assert data.candidates(tmp_path)[0] == tmp_path / 'data/pokeldn-portable'


def test_explicit_override_ignores_corrupt_preference(home, tmp_path, monkeypatch):
    binding = data.binding_path()
    binding.parent.mkdir(parents=True)
    binding.write_text('broken')
    override = tmp_path / 'fixture'
    monkeypatch.setenv('POKELDN_DATA', str(override))
    assert data.resolve(tmp_path) == override
    assert binding.read_text() == 'broken'
    assert not override.exists()


def test_inaccessible_saved_location_never_changes_preference(home, tmp_path, monkeypatch):
    chosen = tmp_path / 'saved'
    chosen.mkdir()
    data.save_choice(chosen)
    record = data.binding_path().read_bytes()
    monkeypatch.setattr(data.os, 'access', lambda path, mode: path != chosen)
    with pytest.raises(data.DataLocationError, match='permisos'):
        data.resolve(tmp_path)
    assert data.binding_path().read_bytes() == record
