"""Resolve the portable installation's active version using only the stdlib."""
import json
import os
from pathlib import Path
import re
import sys


def active_root(root: Path) -> Path:
    pointer = root / '.portable-updates/current.json'
    if not pointer.exists():
        return root
    record = json.loads(pointer.read_text())
    selected = Path(record['root']).resolve()
    releases = (root / '.portable-updates/releases').resolve()
    if selected.parent != releases or not re.fullmatch(r'[0-9a-f]{40}', record['commit']):
        raise ValueError('La referencia de versión portátil no es válida.')
    marker = json.loads((selected / '.portable-ready.json').read_text())
    if marker.get('commit') != record['commit']:
        raise ValueError('La versión portátil no terminó de prepararse.')
    if not (selected / '.venv/bin/python').is_file() or not (selected / 'scripts/run_portable.sh').is_file():
        raise ValueError('La versión portátil está incompleta.')
    return selected


def main():
    root = Path(os.environ['POKELDN_INSTALL_ROOT']).resolve()
    try:
        lock_path = root / '.portable-updates/update.lock'
        if lock_path.exists():
            import fcntl
            with lock_path.open('a') as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    raise ValueError('Hay una actualización en curso; espera a que termine.') from error
        selected = active_root(root)
    except (OSError, KeyError, ValueError) as error:
        print(f'No se pudo abrir pokeLDN: {error}', file=sys.stderr)
        return 1
    env = dict(os.environ, POKELDN_DISPATCHED='1')
    env['POKELDN_DATA'] = str(Path(env['POKELDN_DATA']).expanduser().resolve())
    env.pop('POKELDN_PKHEX', None)
    os.execvpe('bash', ['bash', str(selected / 'scripts/run_portable.sh'), *sys.argv[1:]], env)


if __name__ == '__main__':
    sys.exit(main())
