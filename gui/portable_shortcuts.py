"""User-scoped Linux shortcuts, reached from the portable header."""
import asyncio
import sys

import flet as ft

from pokeldn.app import portable_shortcuts, portable_update
from pokeldn.app.paths import DATA


class ShortcutMenu:
    def __init__(self, view):
        self.view = view
        self.busy = False
        self.menu_open = False
        self.button = ft.IconButton(
            icon=ft.Row([ft.Icon(ft.Icons.ADD_TO_HOME_SCREEN, color='white', size=24),
                         ft.Icon(ft.Icons.ARROW_DROP_DOWN, color='white', size=14)], spacing=0, tight=True),
            tooltip='Accesos directos', width=48, height=40, padding=4,
            on_click=self.opened, on_focus=lambda e: view.header_focus(self.button),
            style=ft.ButtonStyle(side={ft.ControlState.FOCUSED: ft.BorderSide(2, '#00C8D8')}))
        self.control = ft.ContextMenu(
            content=self.button, width=48, height=40,
            secondary_trigger=None, tertiary_trigger=None,
            on_dismiss=self.dismissed, on_select=self.dismissed,
            items=[self.item('Agregar al menú', ft.Icons.APPS, 'menu'),
                   self.item('Agregar al escritorio', ft.Icons.DESKTOP_WINDOWS, 'desktop')])

    def item(self, title, icon, kind):
        async def selected(event):
            await self.install(kind)
        return ft.PopupMenuItem(
            content=ft.Row([ft.Icon(icon, color='#243139', size=20),
                            ft.Text(title, color='#243139', size=15)], spacing=10),
            height=44, on_click=selected)

    def supported(self):
        return (sys.platform.startswith('linux') and not getattr(sys, 'frozen', False)
                and not self.view.page.web and not self.view.setup.demo)

    def blocked(self):
        return self.busy or self.view.updater.handoff or self.view.updater.blocked()

    def sync(self):
        before = self.control.visible, self.control.disabled
        self.control.visible = self.supported() and (
            self.view.settings_button.visible or self.view.updater.button.visible)
        self.control.disabled = self.blocked()
        self.button.disabled = self.control.disabled
        if (before != (self.control.visible, self.control.disabled) and self.control.parent is not None
                and self.view.connected and not self.view.closing):
            self.control.update()

    async def opened(self, event):
        if not self.supported() or self.blocked():
            return
        self.menu_open = True
        try:
            await self.control.open(local_position=ft.Offset(0, 40))
        except RuntimeError:
            self.menu_open = False
            raise

    def dismissed(self, event):
        self.menu_open = False

    async def install(self, kind):
        self.menu_open = False
        if not self.supported() or self.blocked():
            return
        self.busy = True
        self.sync()
        title = 'No se pudo agregar el acceso'
        try:
            result = await asyncio.to_thread(portable_shortcuts.install_shortcut,
                                             kind, portable_update.installation_root(), DATA)
            title = 'Acceso agregado al menú' if kind == 'menu' else 'Acceso agregado al escritorio'
            message = f'{result.path}\n\nAbrirá la app con tus datos actuales:\n{DATA}'
            if result.backup:
                message += f'\n\nEl acceso anterior se conservó en:\n{result.backup}'
            if result.warning:
                message += f'\n\n{result.warning}'
        except (portable_shortcuts.ShortcutError, OSError) as error:
            message = str(error)
        finally:
            self.busy = False
            self.sync()
        if self.view.closing or not self.view.connected:
            return
        self.view.page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text(title),
            content=ft.Column([ft.Text(message, selectable=True)], width=480,
                              height=210, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton('Listo', on_click=lambda e: self.view.page.pop_dialog())]))
