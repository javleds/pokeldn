"""Source updates for the portable fork; old code and user data stay in place."""
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

from pokeldn.app.paths import ROOT

SOURCE = 'https://github.com/javleds/pokeldn.git'
BRANCH = 'main'
SHA = re.compile(r'^[0-9a-f]{40}$')
START_TIMEOUT = 60
PARENT_TIMEOUT = 90


class UpdateError(Exception):
    pass


@dataclass(frozen=True)
class Candidate:
    current: str
    target: str
    current_root: Path
    install_root: Path


def installation_root() -> Path:
    return Path(os.environ.get('POKELDN_INSTALL_ROOT', ROOT)).expanduser().resolve()


def _write(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    with temporary.open('w', encoding='utf-8') as output:
        json.dump(value, output)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def _git(root: Path, *args: str, timeout=30) -> str:
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
    try:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                                text=True, timeout=timeout, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UpdateError('No se pudo consultar Git; revisa la conexión.') from error
    if result.returncode:
        raise UpdateError('Git no pudo completar la comprobación de actualización.')
    return result.stdout.strip()


def _clean(root: Path):
    if _git(root, 'status', '--porcelain', '--untracked-files=all'):
        raise UpdateError('Hay cambios locales. Guárdalos antes de actualizar.')


def _ancestor(root: Path, older: str, newer: str) -> bool:
    try:
        result = subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', older, newer],
                                capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UpdateError('No se pudo comparar el historial de Git.') from error
    if result.returncode not in (0, 1):
        raise UpdateError('No se pudo comparar el historial de Git.')
    return result.returncode == 0


def check(current_root: Path) -> Candidate | None:
    if getattr(sys, 'frozen', False) or os.name != 'posix':
        return None
    root = Path(current_root).resolve()
    if not (root / '.git').exists():
        return None
    _clean(root)
    current = _git(root, 'rev-parse', 'HEAD')
    remote = _git(root, 'ls-remote', SOURCE, 'refs/heads/' + BRANCH)
    target = remote.split()[0] if remote else ''
    if not SHA.fullmatch(target):
        raise UpdateError('La rama main del fork no está disponible.')
    if target == current:
        return None
    _git(root, 'fetch', '--no-tags', SOURCE, target, timeout=120)
    if _ancestor(root, target, current):
        return None  # Local commits ahead of main are never downgraded.
    if not _ancestor(root, current, target):
        raise UpdateError('El historial local diverge de main; requiere revisión manual.')
    return Candidate(current, target, root, installation_root())


def create_job(candidate: Candidate, data: Path, parent_pid: int) -> Path:
    if not all(SHA.fullmatch(value) for value in (candidate.current, candidate.target)):
        raise UpdateError('La versión seleccionada no es válida.')
    root = candidate.install_root.resolve()
    folder = root / '.portable-updates' / 'jobs' / uuid4().hex
    folder.mkdir(parents=True, mode=0o700)
    _write(folder / 'request.json', {
        'current': candidate.current, 'target': candidate.target,
        'current_root': str(candidate.current_root.resolve()), 'install_root': str(root),
        'data': str(Path(data).expanduser().resolve()), 'parent_pid': parent_pid,
        'port': os.environ.get('FLET_SERVER_PORT', '8590'),
    })
    return folder


def _request(job: Path) -> dict:
    request = json.loads((job / 'request.json').read_text())
    root = Path(request['install_root']).resolve()
    if job.resolve().parent != root / '.portable-updates' / 'jobs':
        raise UpdateError('La solicitud no pertenece a esta instalación.')
    if not all(SHA.fullmatch(request[key]) for key in ('current', 'target')):
        raise UpdateError('La versión de actualización no es válida.')
    if not isinstance(request['parent_pid'], int) or request['parent_pid'] <= 1:
        raise UpdateError('El proceso principal no es válido.')
    return request


@contextmanager
def _lock(root: Path):
    import fcntl
    folder = root / '.portable-updates'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'update.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise UpdateError('Ya hay una actualización en curso.') from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _handoff(job: Path, pid: int):
    deadline = time.monotonic() + PARENT_TIMEOUT
    while time.monotonic() < deadline:
        if (job / 'cancel').exists():
            raise UpdateError('Actualización cancelada antes de cerrar la aplicación.')
        if (job / 'proceed').exists() and not _alive(pid):
            return
        time.sleep(.1)
    raise UpdateError('La aplicación anterior no terminó. No se modificó la instalación.')


def _environment(request: dict) -> dict:
    env = os.environ.copy()
    for name in ('POKELDN_PKHEX', 'POKELDN_RADIO', 'PYTHONPATH', 'PYTHONHOME',
                 'POKELDN_GUI_WEB', 'FLET_FORCE_WEB_SERVER', 'POKELDN_PORTABLE_DEMO',
                 'POKELDN_UPDATE_JOB', 'POKELDN_DISPATCHED'):
        env.pop(name, None)
    env.update(POKELDN_INSTALL_ROOT=request['install_root'], POKELDN_DATA=request['data'],
               POKELDN_PORTABLE='1', FLET_SERVER_IP='127.0.0.1', FLET_SERVER_PORT=request['port'],
               GIT_TERMINAL_PROMPT='0')
    return env


def _run(args: list[str], cwd: Path, env: dict, log: Path, timeout: int):
    # A process group lets timeout stop pip/dotnet children, not just their shell.
    with log.open('a', encoding='utf-8') as output:
        process = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            _stop(process)
            raise UpdateError('Se agotó el tiempo de una etapa. Consulta el registro.') from error
    if code:
        raise UpdateError(f'Una etapa terminó con código {code}. Consulta el registro.')


def _stop(process):
    # Flet's viewer may outlive an already-exited Python process in this group.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait(timeout=10)
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=10)


def _prepare(request: dict, job: Path, progress) -> Path:
    root = Path(request['install_root'])
    old = Path(request['current_root'])
    _clean(old)
    if _git(old, 'rev-parse', 'HEAD') != request['current']:
        raise UpdateError('La versión local cambió desde la comprobación.')
    if shutil.disk_usage(root).free < 2 * 1024 ** 3:
        raise UpdateError('Se necesitan al menos 2 GiB libres para preparar la actualización.')
    stage = root / '.portable-updates' / 'releases' / (request['target'] + '-' + uuid4().hex[:8])
    stage.parent.mkdir(parents=True, exist_ok=True)
    env, log = _environment(request), job / 'update.log'
    progress('Descargando cambios', 'Preparando una versión independiente de main.')
    _run(['git', 'clone', '--no-checkout', '--origin', 'origin', SOURCE, str(stage)], root, env, log, 300)
    _run(['git', 'fetch', '--no-tags', 'origin', request['target']], stage, env, log, 180)
    _run(['git', 'checkout', '--detach', request['target']], stage, env, log, 60)
    if _git(stage, 'rev-parse', 'HEAD') != request['target'] or not _ancestor(stage, request['current'], request['target']):
        raise UpdateError('El commit descargado no coincide con la actualización autorizada.')
    for relative in ('gui/portable.py', 'pokeldn/app/portable_update.py', 'scripts/run_portable.sh', 'scripts/build_portable.sh'):
        if not (stage / relative).is_file():
            raise UpdateError('La versión descargada no soporta actualización portátil.')
    progress('Preparando dependencias', 'Creando el entorno Python de esta versión.')
    _run([sys.executable, '-m', 'venv', str(stage / '.venv')], stage, env, log, 120)
    python = str(stage / '.venv/bin/python')
    _run([python, '-m', 'pip', 'install', '--disable-pip-version-check', '-r', 'gui/requirements.txt'], stage, env, log, 1800)
    progress('Compilando motor Pokémon', 'La versión anterior permanece intacta.')
    _run(['bash', 'scripts/build_portable.sh'], stage, env, log, 1200)
    progress('Verificando instalación', 'Comprobando imports y los siete formatos del motor.')
    with tempfile.TemporaryDirectory(prefix='pokeldn-update-smoke-') as scratch:
        smoke_env = {**env, 'POKELDN_DATA': scratch}
        smoke = "from gui import portable; from pokeldn.pokemon import Service; s=Service(); [s.species(g) for g in ('frlg','lgpe','swsh','bdsp','pla','sv','za')]; s.close()"
        _run([python, '-c', smoke], stage, smoke_env, log, 120)
    _write(stage / '.portable-ready.json', {'commit': request['target']})
    return stage


def _launch(root: Path, request: dict, job: Path, handshake: bool):
    env = _environment(request)
    env['POKELDN_DISPATCHED'] = '1'  # Run this exact root for rollback as well.
    if handshake:
        env['POKELDN_UPDATE_JOB'] = str(job)
    with (job / 'app.log').open('a', encoding='utf-8') as output:
        return subprocess.Popen(['bash', str(root / 'scripts/run_portable.sh')], cwd=root,
                                env=env, stdin=subprocess.DEVNULL, stdout=output,
                                stderr=subprocess.STDOUT, start_new_session=True)


def _startup(process, job: Path):
    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise UpdateError('La versión nueva se cerró durante el arranque.')
        if (job / 'app.ready').exists():
            return
        time.sleep(.1)
    raise UpdateError('La versión nueva no confirmó su ventana a tiempo.')


def apply(job: Path, progress=lambda stage, detail: None) -> bool:
    job = Path(job).resolve()
    try:
        request = _request(job)
        with _lock(Path(request['install_root'])):
            _write(job / 'engine.ready', {'ready': True})
            return _apply_locked(job, request, progress)
    except (UpdateError, OSError, ValueError, KeyError) as error:
        _write(job / 'outcome.json', {'ok': False, 'error': str(error)})
        progress('No se pudo actualizar', str(error))
        return False


def _apply_locked(job: Path, request: dict, progress) -> bool:
    root = Path(request['install_root'])
    pointer = root / '.portable-updates/current.json'
    previous = pointer.read_bytes() if pointer.exists() else None
    child = None
    activated = False
    handed_off = False
    try:
        progress('Esperando cierre', 'La aplicación principal se cerrará antes de continuar.')
        _handoff(job, request['parent_pid'])
        handed_off = True
        stage = _prepare(request, job, progress)
        progress('Abriendo pokeLDN', 'Esperando confirmación de la ventana nueva.')
        child = _launch(stage, request, job, handshake=True)
        _startup(child, job)
        # Trial launch bypasses the pointer: a power loss before readiness keeps old active.
        _write(pointer, {'root': str(stage), 'commit': request['target']})
        activated = True
        _write(job / 'outcome.json', {'ok': True, 'commit': request['target']})
        # Last failure-prone action: once released, the new UI may touch the radio.
        _write(job / 'app.commit', {'commit': request['target']})
        return True
    except (UpdateError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        # The failing instance must be stopped before any old version touches the radio.
        recovery_error = ''
        try:
            if child is not None:
                _stop(child)
            if activated:
                if previous is None:
                    pointer.unlink(missing_ok=True)
                else:
                    _write(pointer, json.loads(previous))
            if handed_off:
                _launch(Path(request['current_root']), request, job, handshake=False)
        except (OSError, ValueError, subprocess.SubprocessError) as recovery:
            recovery_error = f' No se pudo reabrir la versión anterior: {recovery}'
        message = str(error) + recovery_error
        _write(job / 'outcome.json', {'ok': False, 'error': message})
        progress('No se pudo actualizar', message)
        return False


def acknowledge_startup():
    """New UI calls this after mounting, before checking radio or accepting trades."""
    token = os.environ.pop('POKELDN_UPDATE_JOB', '')
    if not token:
        return
    job = Path(token).resolve()
    _request(job)
    _write(job / 'app.ready', {'pid': os.getpid()})
    deadline = time.monotonic() + START_TIMEOUT
    while time.monotonic() < deadline:
        if (job / 'app.commit').exists():
            return
        if (job / 'outcome.json').exists():
            outcome = json.loads((job / 'outcome.json').read_text())
            if not outcome.get('ok'):
                raise UpdateError('El actualizador canceló el arranque de esta versión.')
        time.sleep(.1)
    raise UpdateError('El actualizador no confirmó la activación.')
