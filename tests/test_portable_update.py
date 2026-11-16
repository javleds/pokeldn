import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from pokeldn.app import portable_update as update
from scripts.portable_launch import active_root

REAL_HANDOFF = update._handoff


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


@pytest.fixture
def history(tmp_path, monkeypatch):
    remote = tmp_path / 'remote'
    remote.mkdir()
    git(remote, 'init', '-b', 'main')
    git(remote, 'config', 'user.name', 'Test')
    git(remote, 'config', 'user.email', 'test@example.invalid')
    (remote / '.gitignore').write_text('.portable-updates/\n.portable-ready.json\n')
    (remote / 'code').write_text('old')
    git(remote, 'add', '.')
    git(remote, 'commit', '-m', 'old')
    root = tmp_path / 'installed'
    subprocess.run(['git', 'clone', str(remote), str(root)], check=True, capture_output=True)
    git(root, 'config', 'user.name', 'Test')
    git(root, 'config', 'user.email', 'test@example.invalid')
    monkeypatch.setattr(update, 'SOURCE', str(remote))
    monkeypatch.setenv('POKELDN_INSTALL_ROOT', str(root))
    return root, remote


def advance(remote):
    (remote / 'code').write_text('new')
    git(remote, 'add', 'code')
    git(remote, 'commit', '-m', 'new')
    return git(remote, 'rev-parse', 'HEAD')


def test_check_only_offers_descendant_and_never_changes_worktree(history):
    root, remote = history
    assert update.check(root) is None
    target = advance(remote)
    candidate = update.check(root)
    assert candidate.target == target
    assert candidate.current_root == root
    assert candidate.install_root == root
    assert (root / 'code').read_text() == 'old'
    assert git(root, 'rev-parse', 'HEAD') == candidate.current


def test_local_dirty_and_divergence_refuse_update(history):
    root, remote = history
    advance(remote)
    (root / 'code').write_text('local')
    with pytest.raises(update.UpdateError, match='cambios locales'):
        update.check(root)
    git(root, 'add', 'code')
    git(root, 'commit', '-m', 'local')
    with pytest.raises(update.UpdateError, match='diverge'):
        update.check(root)


def test_local_ahead_is_not_downgraded(history):
    root, _ = history
    (root / 'code').write_text('local')
    git(root, 'add', 'code')
    git(root, 'commit', '-m', 'local')
    assert update.check(root) is None


@pytest.fixture
def transaction(history, tmp_path, monkeypatch):
    root, remote = history
    advance(remote)
    candidate = update.check(root)
    data = tmp_path / 'personal'
    data.mkdir()
    (data / 'prod.keys').write_text('fixture')
    monkeypatch.setenv('FLET_SERVER_PORT', '8599')
    job = update.create_job(candidate, data, 23456)
    monkeypatch.setattr(update, '_handoff', lambda *args: None)
    stage = root / '.portable-updates/releases' / candidate.target
    stage.mkdir(parents=True)
    monkeypatch.setattr(update, '_prepare', lambda *args: stage)
    launches, stopped = [], []
    def launch(path, request, job, handshake):
        launches.append((path, handshake, request))
        return SimpleNamespace(pid=999)
    monkeypatch.setattr(update, '_launch', launch)
    monkeypatch.setattr(update, '_stop', lambda process: stopped.append(process.pid))
    monkeypatch.setattr(update, '_startup', lambda *args: None)
    return root, stage, job, data, launches, stopped


def test_success_activates_complete_stage_and_preserves_data(transaction):
    root, stage, job, data, launches, _ = transaction
    assert update.apply(job)
    assert json.loads((root / '.portable-updates/current.json').read_text())['root'] == str(stage)
    assert (job / 'app.commit').exists()
    assert launches[0][:2] == (stage, True)
    assert launches[0][2]['data'] == str(data)
    assert launches[0][2]['port'] == '8599'
    assert (data / 'prod.keys').read_text() == 'fixture'


def test_build_failure_preserves_pointer_and_reopens_old(transaction, monkeypatch):
    root, _, job, _, launches, _ = transaction
    def fail(*args):
        raise update.UpdateError('build failed')
    monkeypatch.setattr(update, '_prepare', fail)
    assert not update.apply(job)
    assert not (root / '.portable-updates/current.json').exists()
    assert launches[0][:2] == (root, False)
    assert 'build failed' in json.loads((job / 'outcome.json').read_text())['error']


def test_start_failure_stops_new_before_rollback_and_restores_pointer(transaction, monkeypatch):
    root, _, job, _, launches, stopped = transaction
    pointer = root / '.portable-updates/current.json'
    original = {'root': str(root / 'previous'), 'commit': 'a' * 40}
    update._write(pointer, original)
    def fail(*args):
        raise update.UpdateError('no window')
    monkeypatch.setattr(update, '_startup', fail)
    assert not update.apply(job)
    assert stopped == [999]
    assert launches[-1][:2] == (root, False)
    assert json.loads(pointer.read_text()) == original
    assert not (job / 'app.commit').exists()


def test_cancel_before_handoff_never_reopens_or_changes_pointer(transaction, monkeypatch):
    root, _, job, _, launches, _ = transaction
    def cancel(*args):
        raise update.UpdateError('cancelled')
    monkeypatch.setattr(update, '_handoff', cancel)
    assert not update.apply(job)
    assert launches == []
    assert not (root / '.portable-updates/current.json').exists()


def test_concurrent_update_is_rejected_without_launch(transaction):
    root, _, job, _, launches, _ = transaction
    with update._lock(root):
        assert not update.apply(job)
    assert launches == []
    assert not (job / 'engine.ready').exists()


def test_environment_preserves_display_and_data_but_not_old_engine(monkeypatch):
    monkeypatch.setenv('DISPLAY', ':0')
    monkeypatch.setenv('DOTNET_ROOT', '/sdk')
    monkeypatch.setenv('POKELDN_PKHEX', '/old/engine')
    monkeypatch.setenv('POKELDN_UPDATE_JOB', '/old/job')
    env = update._environment(dict(install_root='/install', data='/personal', port='8599'))
    assert env['DISPLAY'] == ':0' and env['DOTNET_ROOT'] == '/sdk'
    assert env['POKELDN_DATA'] == '/personal' and env['FLET_SERVER_PORT'] == '8599'
    assert 'POKELDN_PKHEX' not in env and 'POKELDN_UPDATE_JOB' not in env


def test_launcher_rejects_unprepared_or_external_pointer(tmp_path):
    root = tmp_path
    assert active_root(root) == root
    pointer = root / '.portable-updates/current.json'
    update._write(pointer, {'root': '/tmp/foreign', 'commit': 'a' * 40})
    with pytest.raises(ValueError):
        active_root(root)
    stage = root / '.portable-updates/releases' / ('a' * 40)
    stage.mkdir(parents=True)
    update._write(pointer, {'root': str(stage), 'commit': 'a' * 40})
    with pytest.raises(OSError):
        active_root(root)
    update._write(stage / '.portable-ready.json', {'commit': 'a' * 40})
    (stage / '.venv/bin').mkdir(parents=True)
    (stage / '.venv/bin/python').touch()
    (stage / 'scripts').mkdir()
    (stage / 'scripts/run_portable.sh').touch()
    assert active_root(root) == stage


def test_handoff_needs_proceed_and_parent_exit(transaction, monkeypatch):
    _, _, job, _, _, _ = transaction
    monkeypatch.setattr(update, 'PARENT_TIMEOUT', .01)
    monkeypatch.setattr(update, '_alive', lambda pid: False)
    handoff = REAL_HANDOFF
    with pytest.raises(update.UpdateError, match='no terminó'):
        handoff(job, 12345)
    (job / 'proceed').touch()
    handoff(job, 12345)


def test_startup_ack_requires_activation(tmp_path, monkeypatch):
    candidate = update.Candidate('a' * 40, 'b' * 40, tmp_path, tmp_path)
    job = update.create_job(candidate, tmp_path / 'data', 1234)
    monkeypatch.setenv('POKELDN_UPDATE_JOB', str(job))
    update._write(job / 'app.commit', {'commit': candidate.target})
    update.acknowledge_startup()
    assert json.loads((job / 'app.ready').read_text())['pid'] == os.getpid()
    assert 'POKELDN_UPDATE_JOB' not in os.environ


def test_offline_timeout_becomes_actionable_check_error(history, monkeypatch):
    root, _ = history
    original = subprocess.run
    def run(args, **kwargs):
        if 'ls-remote' in args:
            raise subprocess.TimeoutExpired(args, 30)
        return original(args, **kwargs)
    monkeypatch.setattr(subprocess, 'run', run)
    with pytest.raises(update.UpdateError, match='conexión'):
        update.check(root)


def test_ancestor_timeout_is_normalized(history, monkeypatch):
    root, remote = history
    target = advance(remote)
    monkeypatch.setattr(subprocess, 'run', lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired('git', 30)))
    with pytest.raises(update.UpdateError, match='historial'):
        update._ancestor(root, 'a' * 40, target)


def test_pointer_is_not_changed_until_trial_window_ready(transaction, monkeypatch):
    root, stage, job, _, _, _ = transaction
    def trial_ready(process, folder):
        assert not (root / '.portable-updates/current.json').exists()
        assert not (job / 'app.commit').exists()
    monkeypatch.setattr(update, '_startup', trial_ready)
    assert update.apply(job)


def test_outcome_failure_does_not_release_new_ui_and_rolls_back(transaction, monkeypatch):
    root, _, job, _, launches, stopped = transaction
    write = update._write
    def fail_outcome(path, value):
        if path.name == 'outcome.json' and value['ok']:
            raise OSError('disk full')
        write(path, value)
    monkeypatch.setattr(update, '_write', fail_outcome)
    assert not update.apply(job)
    assert not (job / 'app.commit').exists()
    assert not (root / '.portable-updates/current.json').exists()
    assert stopped == [999]
    assert launches[-1][:2] == (root, False)


def test_staging_uses_immutable_git_and_separate_venv_before_smoke(history, tmp_path, monkeypatch):
    root, remote = history
    for filename in ('gui/portable.py', 'pokeldn/app/portable_update.py', 'scripts/run_portable.sh', 'scripts/build_portable.sh'):
        path = remote / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# fixture')
    git(remote, 'add', '.')
    git(remote, 'commit', '-m', 'portable fixture')
    candidate = update.check(root)
    job = update.create_job(candidate, tmp_path / 'personal', 12345)
    request = update._request(job)
    run = update._run
    commands = []
    def controlled(args, cwd, env, log, timeout):
        commands.append((args, cwd, env))
        if args[0] == 'git':
            run(args, cwd, env, log, timeout)
    monkeypatch.setattr(update, '_run', controlled)
    stage = update._prepare(request, job, lambda *args: None)
    assert git(stage, 'rev-parse', 'HEAD') == candidate.target
    assert (root / 'code').read_text() == 'old'
    assert commands[3][0][-1] == str(stage / '.venv')
    assert commands[4][0][0] == str(stage / '.venv/bin/python')
    assert commands[-1][2]['POKELDN_DATA'] != request['data']
    assert json.loads((stage / '.portable-ready.json').read_text())['commit'] == candidate.target


def test_startup_timeout_never_releases_radio_barrier(tmp_path, monkeypatch):
    candidate = update.Candidate('a' * 40, 'b' * 40, tmp_path, tmp_path)
    job = update.create_job(candidate, tmp_path / 'data', 1234)
    monkeypatch.setenv('POKELDN_UPDATE_JOB', str(job))
    monkeypatch.setattr(update, 'START_TIMEOUT', .01)
    with pytest.raises(update.UpdateError, match='no confirmó'):
        update.acknowledge_startup()
    assert (job / 'app.ready').exists()
    assert not (job / 'app.commit').exists()


def test_stable_shell_launcher_forwards_data_sdk_and_build_to_active_version(tmp_path, monkeypatch):
    import shutil
    root = tmp_path / 'installation with spaces'
    scripts = root / 'scripts'
    scripts.mkdir(parents=True)
    project = Path(__file__).resolve().parents[1]
    for filename in ('run_portable.sh', 'portable_launch.py'):
        shutil.copy2(project / 'scripts' / filename, scripts / filename)
    sdk = root / '.tools/dotnet'
    sdk.mkdir(parents=True)
    (sdk / 'dotnet').write_text('#!/bin/sh\nexit 0\n')
    (sdk / 'dotnet').chmod(0o755)
    stage = root / '.portable-updates/releases' / ('a' * 40)
    (stage / 'scripts').mkdir(parents=True)
    (stage / '.venv/bin').mkdir(parents=True)
    (stage / '.venv/bin/python').touch()
    (stage / 'scripts/run_portable.sh').write_text('''#!/bin/sh
python3 -c 'import json,os,sys; open(os.environ["RESULT"],"w").write(json.dumps({"data":os.environ.get("POKELDN_DATA"),"sdk":os.environ["DOTNET_ROOT"],"root":os.environ["POKELDN_INSTALL_ROOT"],"args":sys.argv[1:]}))' "$@"
''')
    update._write(stage / '.portable-ready.json', {'commit': 'a' * 40})
    update._write(root / '.portable-updates/current.json', {'root': str(stage), 'commit': 'a' * 40})
    for key in ('POKELDN_INSTALL_ROOT', 'POKELDN_DISPATCHED', 'POKELDN_DATA', 'DOTNET_ROOT'):
        monkeypatch.delenv(key, raising=False)
    result = tmp_path / 'result.json'
    env = {**os.environ, 'RESULT': str(result)}
    subprocess.run(['bash', str(scripts / 'run_portable.sh'), '--build'], env=env, cwd=tmp_path, check=True)
    assert json.loads(result.read_text()) == {
        'data': None, 'sdk': str(sdk), 'root': str(root), 'args': ['--build']}
    explicit = {**env, 'POKELDN_DATA': str(tmp_path / 'chosen data')}
    subprocess.run(['bash', str(scripts / 'run_portable.sh')], env=explicit, cwd=tmp_path, check=True)
    assert json.loads(result.read_text())['data'] == str(tmp_path / 'chosen data')
    with update._lock(root):
        blocked = subprocess.run(['bash', str(scripts / 'run_portable.sh')], env=env, cwd=tmp_path, capture_output=True)
    assert blocked.returncode != 0
    assert 'actualización en curso' in blocked.stderr.decode()
