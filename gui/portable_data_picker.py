"""Choose an existing portable data folder before importing settings or paths."""
import argparse
import asyncio
from dataclasses import fields
import os
from pathlib import Path
import sys

import flet as ft

from gui import theme

# Keep this bootstrap independent of gui.portable, which imports paths/settings.
RED = "#D83C46"
PAPER = "#F3F1EA"
INK = "#243139"
CYAN = "#00C8D8"


class DataPicker:
    def __init__(self, page, candidates: list[Path], error: str = ""):
        self.page = page
        self.candidates = candidates
        self.busy = False
        self.exit_code = 2
        self.buttons = []
        self.error = ft.Text(error, color=RED, size=15, visible=bool(error), selectable=True)
        self.cancel = ft.TextButton("Cancelar", on_click=self.cancelled)
        choices = []
        for index, path in enumerate(candidates):
            async def selected(event, path=path):
                await self.choose(path)
            button = ft.Button("Usar esta carpeta", on_click=selected,
                               autofocus=index == 0, height=42,
                               style=ft.ButtonStyle(bgcolor=INK, color="white",
                                   side={ft.ControlState.FOCUSED: ft.BorderSide(3, CYAN)}))
            self.buttons.append(button)
            choices.append(ft.Container(bgcolor="#E4E7E5", border_radius=10, padding=12,
                content=ft.Column([
                    ft.Text(str(path), size=15, color=INK, selectable=True),
                    ft.Row([ft.Container(expand=True), button]),
                ], spacing=8)))
        self.control = ft.Container(bgcolor=RED, padding=16, expand=True, content=ft.Column([
            ft.Text("POKÉDEX · CARPETA DE DATOS", color="white", size=21,
                    weight=ft.FontWeight.W_700),
            ft.Container(bgcolor=PAPER, border_radius=16, padding=20, expand=True,
                content=ft.Column([
                    ft.Text("Elige tus datos existentes" if candidates else "Revisar carpeta de datos",
                            color=INK, size=24, weight=ft.FontWeight.W_600),
                    ft.Text("Selecciona dónde están tus claves, entrenadores y banco. "
                            "No moveremos ni combinaremos datos.", color=INK, size=16),
                    ft.ListView([*choices, self.error], spacing=12, expand=True),
                    ft.Row([ft.Text("Tab para navegar · Enter para elegir", color=INK, size=12),
                            ft.Container(expand=True), self.cancel]),
                ], spacing=12, expand=True)),
        ], spacing=14, expand=True))

    async def choose(self, path: Path):
        if self.busy or path not in self.candidates:
            return
        from pokeldn.app import portable_data

        self.busy = True
        for button in self.buttons:
            button.disabled = True
        self.cancel.disabled = True
        self.error.visible = False
        self.page.update()
        try:
            await asyncio.to_thread(portable_data.save_choice, path)
        except (portable_data.DataLocationError, OSError) as error:
            self.error.value = str(error)
            self.error.visible = True
            self.busy = False
            self.cancel.disabled = False
            for button in self.buttons:
                button.disabled = False
            self.page.update()
            return
        self.exit_code = 0
        await self.page.window.destroy()

    async def cancelled(self, event):
        if not self.busy:
            self.exit_code = 2
            await self.page.window.destroy()

    async def window_event(self, event):
        if event.type == ft.WindowEventType.CLOSE:
            await self.cancelled(event)


def configure(page):
    page.title = "pokeLDN · Carpeta de datos"
    page.padding = 0
    page.bgcolor = RED
    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts = {**(page.fonts or {}), **theme.FONT_ASSETS}
    page.theme = ft.Theme(color_scheme_seed=RED, font_family="Arial", text_theme=ft.TextTheme(**{
        field.name: ft.TextStyle(color=INK, font_family_fallback=theme.FALLBACK_FONTS)
        for field in fields(ft.TextTheme)}))
    page.window.width, page.window.height = 800, 512 if sys.platform == "darwin" else 480
    page.window.min_width, page.window.min_height = page.window.width, page.window.height
    page.window.prevent_close = True


def run(root: Path) -> int:
    from pokeldn.app import portable_data

    candidates, error = [], ""
    try:
        portable_data.resolve(root)
        return 0
    except portable_data.ChoiceRequired as required:
        candidates = required.candidates
    except portable_data.DataLocationError as problem:
        error = str(problem)

    # This window precedes the app server; never bind an inherited fixed port.
    for key in ("FLET_SERVER_PORT", "FLET_FORCE_WEB_SERVER", "POKELDN_GUI_WEB", "POKELDN_RADIO"):
        os.environ.pop(key, None)
    os.environ["FLET_SERVER_IP"] = "127.0.0.1"
    views = []

    async def main(page):
        configure(page)
        view = DataPicker(page, candidates, error)
        views.append(view)
        page.window.on_event = view.window_event
        page.add(view.control)

    ft.run(main, port=0, assets_dir=str(Path(__file__).parent / "assets"))
    return views[-1].exit_code if views else 2


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Elegir la carpeta de datos portátil")
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.root.is_absolute():
        parser.error("--root debe ser una ruta absoluta")
    return run(args.root)


if __name__ == "__main__":
    raise SystemExit(cli())
