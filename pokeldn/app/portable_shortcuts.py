"""Install user-owned Linux launchers for the active portable installation."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
from uuid import uuid4


FILENAME = 'pokeldn-portable.desktop'
ENV = Path('/usr/bin/env')
BASH = Path('/usr/bin/bash')


class ShortcutError(Exception):
    pass


@dataclass(frozen=True)
class Result:
    path: Path
    backup: Path | None = None
    warning: str = ''


def _path(value) -> Path:
    raw = str(value)
    if any(unicodedata.category(char) == 'Cc' for char in raw):
        raise ShortcutError('La ruta contiene caracteres de control no permitidos.')
    try:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ShortcutError('Las rutas del acceso deben ser absolutas.')
        resolved = path.resolve()
        if any(unicodedata.category(char) == 'Cc' for char in str(resolved)):
            raise ShortcutError('La ruta resuelta contiene caracteres de control no permitidos.')
        return resolved
    except (OSError, ValueError, RuntimeError) as error:
        raise ShortcutError('No se pudo resolver una ruta del acceso.') from error


def _string(value: str) -> str:
    # Desktop Entry string escaping happens before Exec's argument decoding.
    return value.replace('\\', '\\\\').replace(' ', '\\s')


def _argument(value: str) -> str:
    quoted = ''.join('\\' + char if char in '\\"`$' else char for char in value)
    return '"' + quoted.replace('\\', '\\\\').replace('%', '%%') + '"'


def _executable(path: Path):
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ShortcutError(f'No está disponible el ejecutable requerido: {path}')


def _entry(root: Path, data: Path) -> bytes:
    launcher = root / 'scripts/run_portable.sh'
    icon = root / 'gui/assets/portable/icon.png'
    if not root.is_dir() or not launcher.is_file() or not os.access(launcher, os.R_OK):
        raise ShortcutError('No se encontró el script de arranque en la instalación estable.')
    if not icon.is_file():
        raise ShortcutError('No se encontró el icono de pokeLDN Portable.')
    if not data.is_dir():
        raise ShortcutError('La carpeta de datos activa no existe.')
    _executable(ENV)
    _executable(BASH)
    args = [str(ENV), 'POKELDN_INSTALL_ROOT=' + str(root), 'POKELDN_DATA=' + str(data),
            str(BASH), str(launcher)]
    return ('[Desktop Entry]\nType=Application\nName=pokeLDN Portable\n'
            'Comment=Taller Pokémon portátil\n'
            'Exec=' + ' '.join(_argument(arg) for arg in args) + '\n'
            'Path=' + _string(str(root)) + '\n'
            'Icon=' + _string(str(icon)) + '\n'
            'Terminal=false\nCategories=Game;\n').encode('utf-8')


def _configured_desktop() -> Path:
    config = _path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'user-dirs.dirs'
    try:
        lines = config.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeError) as error:
        raise ShortcutError('No se pudo encontrar la carpeta de escritorio configurada.') from error
    values = [line for line in lines if re.match(r'^\s*XDG_DESKTOP_DIR\s*=', line)]
    if len(values) != 1:
        raise ShortcutError('No hay una única carpeta de escritorio configurada.')
    match = re.fullmatch(r'\s*XDG_DESKTOP_DIR\s*=\s*"((?:[^"\\]|\\.)*)"\s*(?:#.*)?', values[0])
    if not match:
        raise ShortcutError('La configuración de la carpeta de escritorio no es válida.')
    raw = match.group(1)
    result = ''
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == '\\':
            index += 1
            if index == len(raw) or raw[index] not in '\\"$`':
                raise ShortcutError('La configuración del escritorio contiene un escape no admitido.')
            result += raw[index]
        elif char == '$' and index == 0 and (raw == '$HOME' or raw.startswith('$HOME/')):
            result += str(Path.home())
            index += len('$HOME') - 1
        elif char in '$`':
            raise ShortcutError('Sólo se admite $HOME al resolver la carpeta de escritorio.')
        else:
            result += char
        index += 1
    return _path(result)


def _desktop() -> Path:
    utility = shutil.which('xdg-user-dir')
    if utility:
        try:
            result = subprocess.run([utility, 'DESKTOP'], capture_output=True, text=True,
                                    timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ShortcutError('No se pudo consultar la carpeta de escritorio.') from error
        if result.returncode:
            raise ShortcutError('No se pudo consultar la carpeta de escritorio configurada.')
        folder = _path(result.stdout.rstrip('\n'))
    else:
        folder = _configured_desktop()
    if folder == Path('/usr/share') or Path('/usr/share') in folder.parents:
        raise ShortcutError('El acceso sólo puede instalarse para tu usuario.')
    if folder == Path.home().resolve() or not folder.is_dir():
        raise ShortcutError('El escritorio está deshabilitado o su carpeta no existe.')
    return folder


def _destination(kind: str) -> Path:
    if kind == 'desktop':
        return _desktop() / FILENAME
    if kind != 'menu':
        raise ShortcutError('Elige menú o escritorio para crear el acceso.')
    base = _path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    folder = _path(base / 'applications')
    if folder == Path('/usr/share/applications') or Path('/usr/share') in folder.parents:
        raise ShortcutError('El acceso sólo puede instalarse para tu usuario.')
    folder.mkdir(parents=True, exist_ok=True)
    return folder / FILENAME


def _backup(target: Path) -> Path:
    backup = target.with_name(target.name + '.bak-' + uuid4().hex)
    if target.is_symlink():
        os.symlink(os.readlink(target), backup)
    else:
        with target.open('rb') as source, backup.open('xb') as output:
            shutil.copyfileobj(source, output)
        shutil.copystat(target, backup, follow_symlinks=False)
    return backup


def _install(target: Path, content: bytes, mode: int) -> Path | None:
    present = target.exists() or target.is_symlink()
    if present and not target.is_symlink():
        if not stat.S_ISREG(target.stat().st_mode):
            raise ShortcutError('El destino existe y no es un archivo de acceso directo.')
        with target.open('rb') as existing:
            unchanged = existing.read(len(content) + 1) == content
        if unchanged:
            target.chmod(mode)
            return None
    descriptor, filename = tempfile.mkstemp(prefix='.' + FILENAME + '.', dir=target.parent)
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content)
            output.flush()
            os.fchmod(output.fileno(), mode)
            os.fsync(output.fileno())
        backup = _backup(target) if present else None
        os.replace(temporary, target)
        return backup
    finally:
        temporary.unlink(missing_ok=True)


def _finish(kind: str, target: Path) -> str:
    name = 'gio' if kind == 'desktop' else 'update-desktop-database'
    utility = shutil.which(name)
    warning = ('Puede ser necesario permitir el lanzamiento desde el menú contextual del escritorio.'
               if kind == 'desktop' else 'El menú puede tardar en mostrar el acceso; cierra sesión si no aparece.')
    if not utility:
        return warning
    args = ([utility, 'set', str(target), 'metadata::trusted', 'true'] if kind == 'desktop'
            else [utility, str(target.parent)])
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return warning
    return warning if result.returncode else ''


def install_shortcut(kind: str, root: Path, data: Path) -> Result:
    if not sys.platform.startswith('linux') or getattr(sys, 'frozen', False):
        raise ShortcutError('Los accesos están disponibles en la versión fuente para Linux.')
    try:
        content = _entry(_path(root), _path(data))
        target = _destination(kind)
        backup = _install(target, content, 0o755 if kind == 'desktop' else 0o644)
        return Result(target, backup, _finish(kind, target))
    except (OSError, UnicodeError) as error:
        raise ShortcutError(f'No se pudo crear el acceso directo: {error}') from error
