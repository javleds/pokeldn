"""Choose portable data before importing settings or app.paths; never move data."""
import json
import os
from pathlib import Path
import sys
from uuid import uuid4


class DataLocationError(Exception):
    pass


class ChoiceRequired(DataLocationError):
    def __init__(self, locations):
        self.candidates = list(locations)
        super().__init__('Hay datos portátiles en más de una carpeta. Elige cuál abrir.')


def _absolute(value) -> Path:
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        raise DataLocationError('La ruta de datos no es válida o no se puede resolver.') from error


def _canonical() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return _absolute(base / 'pokeldn-portable')


def binding_path() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home())) / 'pokeldn-portable'
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'pokeldn-portable-config'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'pokeldn-portable'
    return _absolute(base / 'portable-data.json')


def candidates(root: Path) -> list[Path]:
    locations = [_canonical(), _absolute(Path(root) / '.local-preview' / 'portable')]
    return list(dict.fromkeys(locations))


def _accessible(path: Path):
    try:
        if not path.is_dir():
            raise DataLocationError(f'La carpeta de datos no existe o no es un directorio: {path}')
        if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
            raise DataLocationError(f'La carpeta de datos no tiene permisos de lectura y escritura: {path}')
        # Listing checks actual traversal/access without reading any personal content.
        with os.scandir(path):
            pass
    except OSError as error:
        raise DataLocationError(f'No se puede acceder a la carpeta de datos: {path}') from error


def _populated(path: Path) -> bool:
    try:
        if not path.exists():
            return False
        _accessible(path)
        with os.scandir(path) as entries:
            return any(entry.name != '.DS_Store' for entry in entries)
    except OSError as error:
        raise DataLocationError(f'No se puede revisar la carpeta de datos: {path}') from error


def save_choice(path: Path) -> Path:
    selected = _absolute(path)
    _accessible(selected)
    binding = binding_path()
    temporary = binding.with_name(binding.name + '.' + uuid4().hex + '.tmp')
    try:
        binding.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open('x', encoding='utf-8') as output:
            json.dump({'version': 1, 'path': str(selected)}, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, binding)
    except OSError as error:
        raise DataLocationError('No se pudo guardar la elección de carpeta de datos.') from error
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass  # Preserve the actionable save error if cleanup is also unavailable.
    return selected


def _saved(binding: Path) -> Path:
    try:
        record = json.loads(binding.read_text(encoding='utf-8'))
        if (not isinstance(record, dict) or record.get('version') != 1
                or not isinstance(record.get('path'), str) or not Path(record['path']).is_absolute()):
            raise ValueError('Invalid data binding')
    except (OSError, UnicodeError, ValueError) as error:
        raise DataLocationError(f'La elección guardada está dañada o no se puede leer: {binding}') from error
    selected = _absolute(record['path'])
    _accessible(selected)
    return selected


def resolve(root: Path) -> Path:
    """Explicit overrides stay isolated; all ordinary launches share one binding."""
    explicit = os.environ.get('POKELDN_DATA')
    if explicit:
        selected = _absolute(explicit)
        try:
            if selected.exists():
                _accessible(selected)
        except OSError as error:
            raise DataLocationError(f'No se puede acceder a la carpeta indicada: {selected}') from error
        return selected
    binding = binding_path()
    try:
        if binding.exists():
            return _saved(binding)
    except OSError as error:
        raise DataLocationError(f'No se puede leer la elección de datos: {binding}') from error
    locations = candidates(root)
    populated = [path for path in locations if _populated(path)]
    if len(populated) > 1:
        raise ChoiceRequired(populated)
    if populated:
        return save_choice(populated[0])
    canonical = locations[0]
    try:
        canonical.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise DataLocationError(f'No se pudo crear la carpeta de datos: {canonical}') from error
    return save_choice(canonical)
