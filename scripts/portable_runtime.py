"""PyInstaller runtime hook: select the Portable profile before application imports."""
import os
import sys
from pathlib import Path

os.environ["POKELDN_PORTABLE"] = "1"
for variable in ("POKELDN_GUI_WEB", "FLET_FORCE_WEB_SERVER", "POKELDN_PORTABLE_DEMO", "FLET_VIEW_PATH"):
    os.environ.pop(variable, None)
os.environ["FLET_SERVER_IP"] = "127.0.0.1"
os.environ.setdefault("FLET_SERVER_PORT", "8590")
if not os.environ.get("POKELDN_DATA"):
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    os.environ["POKELDN_DATA"] = str(base / "pokeldn-portable")
