"""Portable archive listing and a single-record editor using the existing controls."""
import asyncio
from functools import partial
from pathlib import Path

import flet as ft

from gui import theme
from gui.portable_bank import PortableBank
from gui.portable_team_view import TeamView
from gui.portable_trainer_labels import trainer_label
from gui.portable_trainers import GAMES, GAME_FOLDERS


class BankView:
    def __init__(self, shell):
        self.shell, self.page = shell, shell.page
        self.library = getattr(shell.setup, 'bank_library', None) or PortableBank()
        shell.setup.bank_library = self.library
        self.picker = ft.FilePicker()
        self.opening = False
        self.query = ft.TextField(hint_text="Buscar Pokémon, apodo o entrenador", expand=True,
                                  height=42, text_size=14, on_change=self.refresh)
        self.game = theme.dropdown([('', 'Todos los juegos'), *[(g, GAME_FOLDERS[g]) for g in GAMES]],
                                   '', on_select=self.refresh)
        self.game.width = 190
        # Flet 1.0.5 applies Dropdown.bgcolor over MenuStyle.bgcolor.
        self.game.bgcolor = "#F3F1EA"
        self.game.color = "#243139"
        self.game.menu_height, self.game.menu_width = 160, 280
        self.game.menu_style = ft.MenuStyle(bgcolor="#F3F1EA", max_size=ft.Size(280, 160),
                                           min_size=ft.Size(0, 0))
        for option in self.game.options:
            option.style = ft.ButtonStyle(color="#243139")
        self.rows = ft.ListView(expand=True, spacing=5)
        self.message = ft.Text('', size=12, max_lines=2)
        self.control = ft.Column([
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Volver a ajustes",
                                 on_click=lambda e: shell.go('health')),
                    ft.Text("Banco", size=23, expand=True),
                    ft.TextButton("Exportar todos", on_click=self.export_all),
                    ft.TextButton("Eliminar todos", on_click=self.confirm_delete_all)]),
            ft.Row([self.query, self.game]), self.rows, self.message,
        ], expand=True, spacing=6)
        self.refresh(update=False)

    def show(self, message, error=False):
        self.message.value = message
        self.message.color = "#D83C46" if error else "#219A59"
        if self.control.parent is not None:
            self.control.update()

    def editable(self):
        if self.shell.setup.session_busy or self.shell.setup.busy or self.shell.setup.checking:
            raise ValueError("Espera a que termine la sesión o comprobación.")

    def refresh(self, e=None, update=True):
        try:
            rows = []
            for entry in self.library.list(self.query.value or '', self.game.value or ''):
                owner = entry['trainer']
                identity = trainer_label(entry['game'], owner) if all(
                    key in owner for key in ('ot', 'tid', 'sid', 'language')) else "Entrenador sin analizar"
                title = f"{entry['species'] or 'Sin analizar'} · {entry['nickname'] or 'Sin apodo'}"
                actions = ft.Row([
                    ft.IconButton(ft.Icons.EDIT, tooltip="Editar copia y preparar envío",
                                  on_click=partial(self.open_record, entry, True), width=34),
                    ft.IconButton(ft.Icons.SEND, tooltip="Preparar envío del original intacto",
                                  on_click=partial(self.open_record, entry, False), width=34),
                    ft.IconButton(ft.Icons.DOWNLOAD, tooltip="Exportar original",
                                  on_click=partial(self.export_one, entry), width=34),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Eliminar del banco",
                                  on_click=partial(self.confirm_delete, entry), width=34),
                ], spacing=0)
                rows.append(ft.Container(ft.Row([
                    ft.Text(GAME_FOLDERS[entry['game']], width=105, size=12),
                    ft.Column([ft.Text(title, size=14, max_lines=1, tooltip=title,
                                       overflow=ft.TextOverflow.ELLIPSIS),
                               ft.Text(identity, size=11, max_lines=1, tooltip=identity,
                                       overflow=ft.TextOverflow.ELLIPSIS)], expand=True, spacing=3),
                    actions,
                ], spacing=6), padding=8, bgcolor="#E4E7E5", border_radius=8))
            self.rows.controls = rows or [ft.Text("Aún no hay Pokémon recibidos para este filtro.", size=14)]
        except (OSError, ValueError) as error:
            self.show(str(error), True)
        if update and self.control.parent is not None:
            self.control.update()

    async def open_record(self, entry, edit, e=None):
        if self.opening:
            return
        self.opening = True
        try:
            self.editable()
            self.show("Preparando copia para editar…" if edit else "Validando original para envío…")
            data = await asyncio.to_thread(self.library.data, entry['id'])
            await self.shell.open_bank_record(entry['game'], data, edit=edit)
        except (OSError, ValueError, RuntimeError) as error:
            self.show(str(error), True)
        finally:
            self.opening = False

    async def export_one(self, entry, e=None):
        await self.export([entry['id']], Path(GAME_FOLDERS[entry['game']]) / (entry['id'] + '.json'))

    async def export_all(self, e=None):
        await self.export(None, Path('banco.json'))

    async def export(self, ids, relative):
        try:
            data = await asyncio.to_thread(self.library.export, ids)
            folder = await self.picker.get_directory_path(dialog_title="Carpeta de exportación")
            if not folder:
                return
            target = Path(folder) / relative
            def write():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(data)
            await asyncio.to_thread(write)
            self.show(f"Exportado: {relative}")
        except FileExistsError:
            self.show("Ya existe ese archivo; elige otra carpeta para conservarlo.", True)
        except (OSError, ValueError, RuntimeError) as error:
            self.show(str(error), True)

    def confirm_delete(self, entry, e=None):
        self.confirm("¿Eliminar del banco?", entry['species'] or entry['id'],
                     lambda: self.library.delete(entry['id']))

    def confirm_delete_all(self, e=None):
        self.confirm("¿Eliminar todo el banco?", "Se eliminarán TODOS los registros, incluso los ocultos por filtros.",
                     self.library.delete_all)

    def confirm(self, title, detail, operation):
        async def remove(e):
            self.page.pop_dialog()
            try:
                self.editable()
                await asyncio.to_thread(operation)
                self.refresh()
                self.show("Eliminado del banco. Los archivos de las sesiones se conservan.")
            except (OSError, ValueError) as error:
                self.show(str(error), True)
        self.page.show_dialog(ft.AlertDialog(modal=True, title=ft.Text(title), content=ft.Text(detail),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                     ft.TextButton("Eliminar", on_click=remove)]))


class BankEditorView(TeamView):
    def refresh(self, update=True):
        # Base controls manage validation and radio session locks; the archive has
        # one immutable source, not six independently generated drafts.
        super().refresh(update=False)
        self.mode_menu.disabled = True
        self.session_title.value = "Banco · Copia" if self.model.edit_enabled else "Banco · Original"
        self.trainer.disabled = True
        self.find.visible = False
        self.clear_one.visible = self.clear_all.visible = False
        for button in self.slot_buttons[1:]:
            button.visible = False
        self.editor.disabled = not self.model.edit_enabled or self.model.busy
        self.editor_tabs.disabled = not self.model.edit_enabled or self.model.busy
        self.start.tooltip = "Enviar copia validada" if self.model.edit_enabled else "Enviar original intacto"
        self.back.tooltip = "Volver al banco"
        if update and self.control.parent is not None:
            self.control.update()

    def _back(self, e):
        if self.model.busy:
            self._cancel(e)
            return
        self.dispose()
        self.shell.go('bank')

    def dispose(self):
        super().dispose()
        self.model.dispose()
