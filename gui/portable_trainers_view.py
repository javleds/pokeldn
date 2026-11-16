"""Trainer management inside the portable settings shell."""
import asyncio
from functools import partial
from pathlib import Path

import flet as ft

from gui import theme
from gui.portable_trainers import TrainerLibrary, GAMES, GAME_FOLDERS, LANGUAGES, IMPORT_LIMIT, export_filename
from pokeldn import console_trainer


class TrainersView:
    def __init__(self, shell):
        self.shell, self.page = shell, shell.page
        self.library = TrainerLibrary(shell.setup)
        self.picker = ft.FilePicker()
        self.query = ft.TextField(hint_text="Buscar entrenador, ID o idioma", expand=True,
                                  height=42, text_size=14, on_change=self.refresh)
        self.game = theme.dropdown([('', 'Todos los juegos'), *[(g, GAME_FOLDERS[g]) for g in GAMES]],
                                   '', on_select=self.refresh)
        self.game.width = 190
        self.game.color = "#243139"
        self.game.menu_height, self.game.menu_width = 160, 280
        self.game.menu_style = ft.MenuStyle(bgcolor="#F3F1EA", max_size=ft.Size(280, 160),
                                           min_size=ft.Size(0, 0))
        for option in self.game.options:
            option.style = ft.ButtonStyle(color="#243139")
        self.rows = ft.ListView(expand=True, spacing=4)
        self.message = ft.Text('', size=12, max_lines=2)
        self.control = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Volver a ajustes",
                                 on_click=lambda e: shell.go('health')),
                    ft.Text("Entrenadores", size=23, expand=True),
                    ft.TextButton("Importar JSON", on_click=self.import_json),
                    ft.TextButton("Exportar todos", on_click=self.export_all)]),
            ft.Row([self.query, self.game]),
            self.row(["Juego", "OT", "ID", "SID", "Idioma"], header=True),
            self.rows, self.message,
        ], expand=True, spacing=6)
        self.refresh(update=False)

    @staticmethod
    def row(values, actions=None, header=False):
        widths = (112, None, 64, 64, 48)
        cells = [ft.Container(ft.Text(str(value), size=12,
                                     weight=ft.FontWeight.W_600 if header else None,
                                     max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                     tooltip=str(value)),
                              width=width, expand=width is None)
                 for value, width in zip(values, widths)]
        cells.append(ft.Container(actions, width=76))
        return ft.Container(ft.Row(cells, spacing=6), padding=6,
                            bgcolor="#E4E7E5" if not header else None, border_radius=6)

    def show(self, message, error=False):
        self.message.value = message
        self.message.color = "#D83C46" if error else "#219A59"
        if self.control.parent is not None:
            self.control.update()

    def refresh(self, e=None, update=True):
        try:
            entries = self.library.entries(self.query.value or '', self.game.value or '')
            rows = []
            for entry in entries:
                p = entry['profile']
                tid, sid = console_trainer.shown(entry['game'], p['tid'], p['sid'])
                actions = ft.Row([
                    ft.IconButton(ft.Icons.DOWNLOAD, tooltip="Exportar entrenador", width=32,
                                  on_click=partial(self.export_one, entry)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Eliminar entrenador", width=32,
                                  on_click=lambda e, entry=entry: self.confirm_delete(entry)),
                ], spacing=0)
                rows.append(self.row([GAME_FOLDERS[entry['game']], p['ot'], tid, sid,
                                      LANGUAGES[p['language']]], actions))
            self.rows.controls = rows or [ft.Text("No hay entrenadores para este filtro.", size=14)]
        except (ValueError, OSError) as error:
            self.show(str(error), True)
        if update and self.control.parent is not None:
            self.control.update()

    async def export_one(self, entry, e=None):
        await self.export([entry], export_filename(entry))

    async def export_all(self, e=None):
        await self.export(None, Path("entrenadores.json"))

    async def export(self, entries, relative):
        try:
            data = self.library.export_json(entries)
            folder = await self.picker.get_directory_path(dialog_title="Carpeta de exportación")
            if not folder:
                return
            target = Path(folder) / relative
            if target.exists():
                self.show(f"Ya existe {relative}; elige otra carpeta para conservarlo.", True)
                return
            def write():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(data)
            await asyncio.to_thread(write)
            self.show(f"Exportado: {relative}")
        except (OSError, ValueError, RuntimeError) as error:
            self.show(str(error), True)

    async def import_json(self, e=None):
        try:
            files = await self.picker.pick_files(allow_multiple=False, with_data=self.page.web,
                file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["json"])
            if not files:
                return
            selected = files[0]
            if selected.size > IMPORT_LIMIT:
                raise ValueError("El archivo de entrenadores es demasiado grande.")
            if selected.bytes is not None:
                data = selected.bytes
            else:
                def read():
                    with Path(selected.path).open('rb') as stream:
                        return stream.read(IMPORT_LIMIT + 1)
                data = await asyncio.to_thread(read)
            count = self.library.import_json(data)
            self.refresh()
            self.show(f"Importados {count} entrenadores nuevos.")
        except (OSError, ValueError, RuntimeError) as error:
            self.show(str(error), True)

    def confirm_delete(self, entry):
        def remove(e):
            self.page.pop_dialog()
            try:
                self.library.delete(entry['game'], entry['id'])
                self.refresh()
                self.show("Entrenador eliminado; sus Pokémon se conservan.")
            except (ValueError, OSError) as error:
                self.show(str(error), True)
        self.page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("¿Eliminar entrenador?"),
            content=ft.Text(f"{entry['profile']['ot']} · {GAME_FOLDERS[entry['game']]}"),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                     ft.TextButton("Eliminar", on_click=remove)]))
