import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pokeldn.app import portable_data, portable_startup


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'config'))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    monkeypatch.delenv('POKELDN_DATA', raising=False)
    monkeypatch.delenv('POKELDN_INSTALL_ROOT', raising=False)
    monkeypatch.setattr(portable_data.sys, 'platform', 'linux')
    return tmp_path


def test_bootstrap_sets_absolute_env_before_settings(isolated, monkeypatch):
    chosen = portable_startup.configure_data(isolated / 'checkout')
    assert os.environ['POKELDN_DATA'] == str(chosen)
    assert chosen == isolated / 'data/pokeldn-portable'
    assert chosen.is_dir()
    assert portable_data.binding_path().is_file()


def test_self_updated_code_detects_legacy_at_stable_root(isolated, monkeypatch):
    root = isolated / 'install'
    legacy = root / '.local-preview/portable'
    legacy.mkdir(parents=True)
    (legacy / 'settings.json').write_text('{}')
    monkeypatch.setenv('POKELDN_INSTALL_ROOT', str(root))
    chosen = portable_startup.configure_data(root / '.portable-updates/releases/new')
    assert chosen == legacy


def test_picker_choice_is_reloaded_and_no_data_merged(isolated, monkeypatch):
    root = isolated / 'checkout'
    canonical, legacy = portable_data.candidates(root)
    for path in (canonical, legacy):
        path.mkdir(parents=True)
        (path / 'settings.json').write_text(path.name)
    def run(args, **kwargs):
        assert args[1:3] == ['-m', 'gui.portable_data_picker']
        assert kwargs['cwd'] == root
        portable_data.save_choice(legacy)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(portable_startup.subprocess, 'run', run)
    assert portable_startup.configure_data(root) == legacy
    assert (canonical / 'settings.json').read_text() == canonical.name


def test_cancel_exits_before_setting_a_data_directory(isolated, monkeypatch):
    root = isolated / 'checkout'
    for path in portable_data.candidates(root):
        path.mkdir(parents=True)
        (path / 'settings.json').write_text('{}')
    monkeypatch.setattr(portable_startup.subprocess, 'run', Mock(return_value=SimpleNamespace(returncode=2)))
    with pytest.raises(SystemExit) as error:
        portable_startup.configure_data(root)
    assert error.value.code == 2
    assert 'POKELDN_DATA' not in os.environ
    assert not portable_data.binding_path().exists()


def test_explicit_override_is_not_remembered(isolated, monkeypatch):
    monkeypatch.setenv('POKELDN_DATA', str(isolated / 'temporary'))
    assert portable_startup.configure_data(isolated) == isolated / 'temporary'
    assert not portable_data.binding_path().exists()


def test_frozen_picker_uses_executable_flag(isolated, monkeypatch):
    monkeypatch.setattr(portable_startup.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(portable_data, 'resolve', Mock(side_effect=[portable_data.DataLocationError('bad'), isolated]))
    run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(portable_startup.subprocess, 'run', run)
    assert portable_startup.configure_data(isolated) == isolated
    assert run.call_args.args[0][1:3] == ['--choose-portable-data', '--root']


def test_noninteractive_worker_resolves_saved_data_without_picker(isolated, monkeypatch):
    chosen = isolated / 'saved'
    chosen.mkdir()
    portable_data.save_choice(chosen)
    run = Mock()
    monkeypatch.setattr(portable_startup.subprocess, 'run', run)
    assert portable_startup.configure_data(isolated, interactive=False) == chosen
    run.assert_not_called()


def test_noninteractive_conflict_never_falls_back_to_desktop_data(isolated, monkeypatch):
    for path in portable_data.candidates(isolated):
        path.mkdir(parents=True)
        (path / 'settings.json').write_text('{}')
    run = Mock()
    monkeypatch.setattr(portable_startup.subprocess, 'run', run)
    with pytest.raises(SystemExit, match='más de una'):
        portable_startup.configure_data(isolated, interactive=False)
    run.assert_not_called()
    assert 'POKELDN_DATA' not in os.environ
