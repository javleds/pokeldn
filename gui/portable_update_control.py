"""Portable update discovery and the hand-off to an independent updater window."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys

import flet as ft

from pokeldn.app import portable_update
from pokeldn.app.paths import DATA, ROOT


class PortableUpdate:
    def __init__(self, view):
        self.view = view
        self.candidate = None
        self.handoff = False
        self.checking = False
        self.error = ''
        self.checked = False
        self.status = ft.Text('Actualizaciones: sin comprobar', size=13, color='#243139', max_lines=2)
        self.button = ft.IconButton(
            icon=ft.Icons.SYSTEM_UPDATE_ALT, tooltip='Actualización disponible',
            icon_color='white', icon_size=24, visible=False,
            on_click=self.confirm, on_focus=lambda e: view.header_focus(self.button))

    def blocked(self):
        setup = self.view.setup
        pending = getattr(setup, 'bank_persistence_tasks', ())
        return (self.view.closing or setup.busy or setup.checking or setup.session_busy
                or any(not task.done() for task in pending))

    def sync(self):
        before = (self.button.visible, self.button.disabled)
        self.button.visible = self.candidate is not None
        self.button.disabled = self.handoff or self.blocked()
        if self.checking:
            self.status.value = 'Actualizaciones: comprobando main…'
        elif self.error:
            self.status.value = 'Actualizaciones: ' + self.error
        elif self.candidate:
            self.status.value = 'Actualización disponible desde main'
        elif self.checked:
            self.status.value = 'Sin actualizaciones pendientes en main'
        else:
            self.status.value = 'Actualizaciones: sin comprobar'
        if self.status.parent is not None and self.view.connected and not self.view.closing:
            self.status.update()
        if (before != (self.button.visible, self.button.disabled)
                and self.button.parent is not None and self.view.connected and not self.view.closing):
            self.button.update()

    async def check(self, e=None):
        if self.checking or self.view.page.web or self.view.setup.demo or getattr(sys, 'frozen', False):
            return
        self.checking = True
        self.sync()
        try:
            self.candidate = await asyncio.to_thread(portable_update.check, Path(ROOT))
            self.error = ''
        except (portable_update.UpdateError, OSError) as exc:
            # Offline/dirty/diverged installations remain usable; never offer a blind update.
            self.error = str(exc)
            self.candidate = None
        finally:
            self.checking = False
            self.checked = True
        if self.view.connected and not self.view.closing:
            self.sync()
            self.view.shortcuts.sync()
            self.view.sync_header_navigation()
            self.view.page.update()

    def confirm(self, e=None):
        if self.candidate is None or self.handoff or self.blocked():
            return
        page = self.view.page
        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text('Actualizar pokeLDN'),
            content=ft.Column([
                ft.Text(f'Versión {self.candidate.current[:8]} → {self.candidate.target[:8]}'),
                ft.Text('Se cerrará la app y una ventana independiente mostrará el progreso. '
                        'Al terminar se abrirá de nuevo. Se conservarán tus datos.'),
                ft.Text('La preparación necesita Internet y espacio para otra instalación.'),
            ], tight=True, width=480),
            actions=[ft.TextButton('Cancelar', on_click=lambda e: page.pop_dialog()),
                     ft.TextButton('Actualizar', on_click=self.begin)]))

    async def begin(self, e=None):
        if self.candidate is None or self.handoff or self.blocked():
            return
        page = self.view.page
        page.pop_dialog()
        self.handoff = True
        self.sync()
        self.view.control.disabled = True
        page.update()
        job = None
        try:
            job = await asyncio.to_thread(portable_update.create_job, self.candidate, DATA, os.getpid())
            env = os.environ.copy()
            env['POKELDN_DATA'] = str(DATA.resolve())
            env.pop('POKELDN_UPDATE_JOB', None)
            with (job / 'helper.log').open('ab') as log:
                process = subprocess.Popen(
                    [sys.executable, '-m', 'gui.portable_updating', '--job', str(job)],
                    cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    start_new_session=True)
            await self.wait_ready(job, process)
            # Recheck after awaiting the helper: no activity may have acquired the radio meanwhile.
            if self.blocked():
                raise portable_update.UpdateError('La app está ocupada. Intenta actualizar al terminar.')
            (job / 'proceed').touch()
            await self.view.close(None)
            if not self.view.closing:
                raise portable_update.UpdateError('No se pudo cerrar la app para actualizar.')
        except (OSError, portable_update.UpdateError) as exc:
            if job is not None:
                (job / 'cancel').touch()
            self.handoff = False
            self.view.control.disabled = False
            self.error = str(exc)
            self.sync()
            if not self.view.closing:
                page.update()
                page.show_dialog(ft.AlertDialog(
                    modal=True, title=ft.Text('No se inició la actualización'),
                    content=ft.Text(self.error + (f'\nRegistro: {job / "helper.log"}' if job else '')),
                    actions=[ft.TextButton('Cerrar', on_click=lambda e: page.pop_dialog())]))

    @staticmethod
    async def wait_ready(job, process):
        for _ in range(150):
            if process.poll() is not None or (job / 'outcome.json').exists():
                raise portable_update.UpdateError('El actualizador no pudo iniciarse. La app sigue abierta.')
            if (job / 'helper.ready').is_file() and (job / 'engine.ready').is_file():
                return
            await asyncio.sleep(.1)
        raise portable_update.UpdateError('La ventana de actualización no respondió. La app sigue abierta.')
