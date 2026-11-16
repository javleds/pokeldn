"""Resolve portable data before importing paths, settings, or hardware services."""
import os
from pathlib import Path
import subprocess
import sys

from pokeldn.app import portable_data


def configure_data(code_root: Path, *, interactive: bool = True) -> Path:
    root = Path(os.environ.get('POKELDN_INSTALL_ROOT', code_root)).expanduser().resolve()
    try:
        chosen = portable_data.resolve(root)
    except portable_data.DataLocationError as error:
        if not interactive:
            raise SystemExit(str(error)) from error
        # The picker runs separately, before the main Flet client and its settings.
        if getattr(sys, 'frozen', False):
            command = [sys.executable, '--choose-portable-data', '--root', str(root)]
        else:
            command = [sys.executable, '-m', 'gui.portable_data_picker', '--root', str(root)]
        result = subprocess.run(command, cwd=code_root, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
        chosen = portable_data.resolve(root)
    os.environ['POKELDN_DATA'] = str(chosen)
    return chosen
