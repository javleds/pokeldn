"""PyInstaller runtime hook: select the Portable profile before application imports."""
import os

os.environ["POKELDN_PORTABLE"] = "1"
for variable in ("POKELDN_GUI_WEB", "FLET_FORCE_WEB_SERVER", "POKELDN_PORTABLE_DEMO", "FLET_VIEW_PATH"):
    os.environ.pop(variable, None)
os.environ["FLET_SERVER_IP"] = "127.0.0.1"
os.environ.setdefault("FLET_SERVER_PORT", "8590")
# gui/main.py resolves storage before importing paths/settings. Keeping this
# decision there also lets a bundled app show the existing-folder picker.
