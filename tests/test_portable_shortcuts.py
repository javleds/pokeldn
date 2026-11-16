import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace

import pytest

from pokeldn.app import portable_shortcuts as shortcuts


@pytest.fixture
def installation(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    home.mkdir()
    root = tmp_path / 'pokeldn'
    (root / 'scripts').mkdir(parents=True)
    (root / 'scripts/run_portable.sh').write_text('# never executed')
    (root / 'gui/assets/portable').mkdir(parents=True)
    (root / 'gui/assets/portable/icon.png').write_bytes(b'fixture')
    data = tmp_path / 'private-data'
    data.mkdir()
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setattr(shortcuts.sys, 'platform', 'linux')
    monkeypatch.setattr(shortcuts.sys, 'frozen', False, raising=False)
    monkeypatch.setattr(shortcuts, '_executable', lambda path: None)
    monkeypatch.setattr(shortcuts.shutil, 'which', lambda name: None)
    return home, root, data


def desktop(home, folder='Escritorio'):
    target = home / folder
    target.mkdir(parents=True)
    config = home / '.config/user-dirs.dirs'
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'XDG_DESKTOP_DIR="$HOME/{folder}"\n')
    return target


def test_menu_installs_stable_launcher_and_active_data_without_build(installation):
    home, root, data = installation
    result = shortcuts.install_shortcut('menu', root, data)
    assert result.path == home / '.local/share/applications/pokeldn-portable.desktop'
    content = result.path.read_text()
    assert f'"POKELDN_INSTALL_ROOT={root}"' in content
    assert f'"POKELDN_DATA={data}"' in content
    assert f'"/usr/bin/bash" "{root}/scripts/run_portable.sh"' in content
    assert '--build' not in content
    assert 'Terminal=false' in content
    assert stat.S_IMODE(result.path.stat().st_mode) == 0o644
    assert result.backup is None
    assert result.warning
    assert list(data.iterdir()) == []


def test_desktop_uses_localized_config_and_executable_file(installation):
    home, root, data = installation
    target = desktop(home)
    result = shortcuts.install_shortcut('desktop', root, data)
    assert result.path == target / shortcuts.FILENAME
    assert stat.S_IMODE(result.path.stat().st_mode) == 0o755
    assert 'permitir' in result.warning


def test_idempotent_install_does_not_create_backup(installation):
    _, root, data = installation
    first = shortcuts.install_shortcut('menu', root, data)
    original = first.path.read_bytes()
    first.path.chmod(0o600)
    second = shortcuts.install_shortcut('menu', root, data)
    assert second.path.read_bytes() == original and second.backup is None
    assert list(second.path.parent.glob('*.bak-*')) == []
    assert stat.S_IMODE(second.path.stat().st_mode) == 0o644


def test_different_existing_file_is_backed_up_before_replacement(installation):
    _, root, data = installation
    result = shortcuts.install_shortcut('menu', root, data)
    result.path.write_text('old entry')
    result.path.chmod(0o640)
    replacement = shortcuts.install_shortcut('menu', root, data)
    assert replacement.backup.read_text() == 'old entry'
    assert stat.S_IMODE(replacement.backup.stat().st_mode) == 0o640
    assert replacement.path.read_text().startswith('[Desktop Entry]')


@pytest.mark.parametrize('broken', [False, True])
def test_existing_symlink_is_preserved_as_link_without_touching_target(installation, tmp_path, broken):
    home, root, data = installation
    folder = home / '.local/share/applications'
    folder.mkdir(parents=True)
    external = tmp_path / 'external.desktop'
    if not broken:
        external.write_text('external remains unchanged')
    target = folder / shortcuts.FILENAME
    target.symlink_to(external)
    result = shortcuts.install_shortcut('menu', root, data)
    assert not target.is_symlink()
    assert result.backup.is_symlink()
    assert os.readlink(result.backup) == str(external)
    if broken:
        assert not external.exists()
    else:
        assert external.read_text() == 'external remains unchanged'


def test_atomic_replace_failure_keeps_previous_file(installation, monkeypatch):
    _, root, data = installation
    target = shortcuts.install_shortcut('menu', root, data).path
    target.write_text('old entry')
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(shortcuts.os, 'replace', fail)
    with pytest.raises(shortcuts.ShortcutError, match='disk full'):
        shortcuts.install_shortcut('menu', root, data)
    assert target.read_text() == 'old entry'
    assert len(list(target.parent.glob('*.bak-*'))) == 1
    assert list(target.parent.glob('.pokeldn-portable.desktop.*')) == []


def test_exec_escapes_quotes_dollars_backticks_backslashes_and_percent():
    # Expected on-disk values require string unescaping before argument unquoting.
    assert shortcuts._argument('a b') == '"a b"'
    assert shortcuts._argument('a"b') == '"a\\\\"b"'
    assert shortcuts._argument('a$b') == '"a\\\\$b"'
    assert shortcuts._argument('a`b') == '"a\\\\`b"'
    assert shortcuts._argument('a\\b') == '"a\\\\\\\\b"'
    assert shortcuts._argument('a%b') == '"a%%b"'


def test_special_paths_remain_literal_without_shell(installation, tmp_path):
    _, root, data = installation
    moved = tmp_path / 'poke " $(`touch BAD`) \\ 100% ; &'
    root.rename(moved)
    result = shortcuts.install_shortcut('menu', moved, data)
    content = result.path.read_text()
    assert '100%%' in content.split('Exec=', 1)[1].splitlines()[0]
    assert 'Path=' + shortcuts._string(str(moved)) in content
    assert not (tmp_path / 'BAD').exists()


@pytest.mark.parametrize('control', ['\n', '\r', '\t', '\x00', '\x7f', '\x85'])
def test_control_characters_are_rejected_before_writing(installation, control):
    home, root, data = installation
    with pytest.raises(shortcuts.ShortcutError, match='control'):
        shortcuts.install_shortcut('menu', Path(str(root) + control), data)
    assert not (home / '.local/share/applications').exists()


@pytest.mark.parametrize('configuration', [None, 'XDG_DESKTOP_DIR="$HOME"', 'XDG_DESKTOP_DIR="$HOME/Missing"', 'XDG_DESKTOP_DIR="$(touch /tmp/no)"'])
def test_missing_disabled_or_invalid_desktop_does_not_create_directory(installation, configuration):
    home, root, data = installation
    if configuration is not None:
        (home / '.config').mkdir()
        (home / '.config/user-dirs.dirs').write_text(configuration)
    with pytest.raises(shortcuts.ShortcutError):
        shortcuts.install_shortcut('desktop', root, data)
    assert not (home / 'Desktop').exists()
    assert not (home / 'Missing').exists()
    assert not (home / shortcuts.FILENAME).exists()


def test_xdg_utility_and_optional_metadata_are_argv_only(installation, monkeypatch):
    home, root, data = installation
    folder = desktop(home, 'Mesa de trabajo')
    monkeypatch.setattr(shortcuts.shutil, 'which', lambda name: '/usr/bin/' + name)
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=str(folder) + '\n' if args[0].endswith('xdg-user-dir') else '')
    monkeypatch.setattr(shortcuts.subprocess, 'run', run)
    result = shortcuts.install_shortcut('desktop', root, data)
    assert result.warning == ''
    assert calls[0][0] == ['/usr/bin/xdg-user-dir', 'DESKTOP']
    assert calls[1][0] == ['/usr/bin/gio', 'set', str(result.path), 'metadata::trusted', 'true']
    assert all(not kwargs.get('shell', False) for _, kwargs in calls)


def test_metadata_failure_is_warning_after_successful_install(installation, monkeypatch):
    home, root, data = installation
    folder = desktop(home)
    monkeypatch.setattr(shortcuts.shutil, 'which', lambda name: '/usr/bin/gio' if name == 'gio' else None)
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired('gio', 10)
    monkeypatch.setattr(shortcuts.subprocess, 'run', fail)
    result = shortcuts.install_shortcut('desktop', root, data)
    assert result.path == folder / shortcuts.FILENAME
    assert result.path.exists() and result.warning


def test_menu_cache_refresh_uses_only_user_applications(installation, monkeypatch):
    home, root, data = installation
    monkeypatch.setattr(shortcuts.shutil, 'which', lambda name: '/usr/bin/update-desktop-database')
    calls = []
    monkeypatch.setattr(shortcuts.subprocess, 'run', lambda args, **kw: calls.append(args) or SimpleNamespace(returncode=1))
    result = shortcuts.install_shortcut('menu', root, data)
    assert calls == [['/usr/bin/update-desktop-database', str(home / '.local/share/applications')]]
    assert result.path.exists() and result.warning


def test_source_linux_only(installation, monkeypatch):
    home, root, data = installation
    monkeypatch.setattr(shortcuts.sys, 'platform', 'darwin')
    with pytest.raises(shortcuts.ShortcutError, match='Linux'):
        shortcuts.install_shortcut('menu', root, data)
    monkeypatch.setattr(shortcuts.sys, 'platform', 'linux')
    monkeypatch.setattr(shortcuts.sys, 'frozen', True)
    with pytest.raises(shortcuts.ShortcutError, match='Linux'):
        shortcuts.install_shortcut('menu', root, data)
    assert not (home / '.local/share/applications').exists()


def test_system_or_relative_xdg_destination_is_refused(installation, monkeypatch):
    _, root, data = installation
    for destination in ('/usr/share', 'relative'):
        monkeypatch.setenv('XDG_DATA_HOME', destination)
        with pytest.raises(shortcuts.ShortcutError):
            shortcuts.install_shortcut('menu', root, data)


def test_alias_to_control_character_directory_is_rejected(installation, tmp_path):
    home, root, data = installation
    unsafe = tmp_path / 'line\nbreak'
    root.rename(unsafe)
    root.symlink_to(unsafe, target_is_directory=True)
    with pytest.raises(shortcuts.ShortcutError, match='control'):
        shortcuts.install_shortcut('menu', root, data)
    assert not (home / '.local/share/applications').exists()


def test_applications_symlink_cannot_redirect_to_system_directory(installation):
    home, root, data = installation
    base = home / '.local/share'
    base.mkdir(parents=True)
    (base / 'applications').symlink_to('/usr/share/applications', target_is_directory=True)
    with pytest.raises(shortcuts.ShortcutError, match='usuario'):
        shortcuts.install_shortcut('menu', root, data)


def test_desktop_configuration_cannot_target_system_directory(installation):
    home, root, data = installation
    (home / '.config').mkdir()
    (home / '.config/user-dirs.dirs').write_text('XDG_DESKTOP_DIR="/usr/share"')
    with pytest.raises(shortcuts.ShortcutError, match='usuario'):
        shortcuts.install_shortcut('desktop', root, data)


def test_missing_launcher_icon_or_data_fails_before_creating_menu(installation):
    home, root, data = installation
    icon = root / 'gui/assets/portable/icon.png'
    icon.unlink()
    with pytest.raises(shortcuts.ShortcutError, match='icono'):
        shortcuts.install_shortcut('menu', root, data)
    icon.touch()
    (root / 'scripts/run_portable.sh').unlink()
    with pytest.raises(shortcuts.ShortcutError, match='arranque'):
        shortcuts.install_shortcut('menu', root, data)
    assert not (home / '.local/share/applications').exists()
