"""Pokédex onboarding at 800 × 480; desktop navigation stays in main.py."""
import asyncio
from dataclasses import fields
import os
import sys
from pathlib import Path

import flet as ft

from gui import theme
from gui.portable_resources import ResourceOverlay
from gui.portable_update_control import PortableUpdate
from pokeldn.app import portable_update
from gui.portable_setup import MAX_KEYS, SUPPORTED_RADIO_CHIPS, Setup, shared_setup
from pokeldn.app.i18n import t as tr
from pokeldn.app.catalog import GAMES

RED = "#D83C46"
DARK_RED = "#A52D39"
PAPER = "#F3F1EA"
INK = "#243139"
MUTED = "#5C6870"
CYAN = "#00C8D8"
GREEN = "#219A59"
AMBER = "#B67808"
GAME_NAMES = {
    "frlg": "Rojo Fuego / Verde Hoja",
    "lgpe": "Let's Go Pikachu / Eevee",
    "swsh": "Espada / Escudo",
    "bdsp": "Diamante Brillante / Perla Reluciente",
    "pla": "Leyendas Arceus",
    "sv": "Escarlata / Púrpura",
    "za": "Leyendas Z-A",
}
PORTABLE_GAMES = tuple(game for game in GAMES if game.key in GAME_NAMES)


def game_avatar(game):
    fallback = ft.Icon(ft.Icons.CATCHING_POKEMON, size=76, color=RED)
    path = Path(__file__).parent / "assets" / "games" / f"{game.key}.png"
    image = ft.Image(src=f"games/{game.key}.png", width=100, height=100,
                     fit=ft.BoxFit.CONTAIN, error_content=fallback,
                     semantics_label=GAME_NAMES[game.key]) if path.is_file() else fallback
    return ft.Container(image, width=128, height=128, border_radius=64,
                        bgcolor="#E4E7E5", alignment=ft.Alignment.CENTER,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS)



def label(key, fallback, **kwargs):
    return ft.Text(tr(f"portable.{key}", fallback), color=INK, size=18, **kwargs)


class PortableView:
    def __init__(self, page, setup):
        self.page, self.setup = page, setup
        self.closing = False
        self.setup_listener = None
        self.screen = "progress" if setup.busy else "home" if setup.ready else "health"
        self.startup_pending = not setup.initialized or setup.checking
        self.buttons = []
        self.focus_index = 0
        self.local = False
        self.team_view = None
        self.trainers_view = None
        self.bank_view = None
        self.selected_game = None
        self.game_list = None
        self.gallery_navigation = asyncio.Lock()
        self.focus_tasks = set()
        self.connected = True
        self.picker = ft.FilePicker()
        self.error = ""
        self.rendered_screen = ""
        self.rendered_busy = False
        self.log_list = ft.ListView(expand=True, spacing=5, auto_scroll=True, padding=14)
        self.body = ft.Container(expand=True, bgcolor=PAPER, border_radius=16, padding=ft.Padding(24, 16, 24, 12))
        self.header_text = label("header", "POKÉDEX · INICIO", weight=ft.FontWeight.W_700)
        self.header_text.color = "#FFFFFF"
        self.step = ft.Text("", color=INK, size=15, weight=ft.FontWeight.W_700)
        self.settings_button = ft.IconButton(
            icon=ft.Icons.SETTINGS, tooltip=tr("portable.settings", "Ajustes"),
            icon_color="white", icon_size=24, visible=False,
            on_click=lambda e: self.go("health"),
            on_focus=lambda e: self.header_focus(self.settings_button),
            style=ft.ButtonStyle(side={ft.ControlState.FOCUSED: ft.BorderSide(2, CYAN)},
                                 shape=ft.RoundedRectangleBorder(radius=10)))
        self.updater = PortableUpdate(self)
        self.close_button = ft.IconButton(
            icon=ft.Icons.CLOSE, tooltip=tr("portable.close", "Cerrar"),
            icon_color="white", visible=not page.web, on_click=self.close,
            on_focus=lambda e: self.header_focus(self.close_button))
        self.footer = ft.Text("", size=14, color=INK, text_align=ft.TextAlign.CENTER)
        lens = ft.Container(width=34, height=34, border_radius=18, bgcolor=CYAN,
                            border=ft.Border.all(3, "#E9FCFF"),
                            content=ft.Container(width=9, height=9, border_radius=6, bgcolor="white", margin=5))
        lamps = ft.Row([ft.Container(width=9, height=9, border_radius=5, bgcolor=color)
                        for color in ("#F4DB65", "#65E4A1", DARK_RED)], spacing=5)
        self.control = ft.Container(bgcolor=RED, padding=8, expand=True, content=ft.Column([
            ft.Container(ft.Row([lens, lamps, ft.Container(self.header_text, expand=True, padding=ft.Padding.only(left=14)),
                                 ft.Container(self.step, bgcolor=PAPER, border_radius=16, padding=ft.Padding(12, 4, 12, 4)),
                                 self.updater.button, self.settings_button, self.close_button]),
                         height=40, padding=ft.Padding(10, 0, 10, 0)),
            self.body,
            ft.Container(self.footer, height=24, alignment=ft.Alignment.CENTER),
        ], spacing=6, expand=True))
        self.resources = ResourceOverlay(page)
        self.control = ft.Stack([self.control, self.resources.control], expand=True)
        self.render(update=False)

    def header_focus(self, control):
        if control in self.buttons:
            self.focus_index = self.buttons.index(control)

    async def close(self, e):
        if self.closing or self.setup.session_busy or (self.updater.handoff and e is not None):
            return
        if self.setup.busy:
            self.go("progress")
            return
        self.closing = True
        self.disconnect_focus()
        self.resources.connected = False
        self.resources.sync()
        if self.setup_listener is not None:
            self.setup.listeners.discard(self.setup_listener)
        if self.team_view is not None:
            self.team_view.dispose()
        # A completed trade may still be writing its final archive entry.
        # Wait for bytes, not optional PKHeX metadata enrichment.
        pending = getattr(self.setup, "bank_persistence_tasks", set())
        if pending:
            await asyncio.gather(*tuple(pending), return_exceptions=True)
        await self.page.window.destroy()

    def button(self, key, text, callback, primary=False, disabled=False, icon=None):
        index = len(self.buttons)
        async def clicked(e):
            result = callback()
            if asyncio.iscoroutine(result):
                await result
        def focused(e):
            self.focus_index = index
        control = ft.Button(label(key, text, weight=ft.FontWeight.W_600), on_click=clicked,
                            disabled=disabled, height=46, expand=True, icon=icon,
                            on_focus=focused, autofocus=primary and not disabled,
                            style=ft.ButtonStyle(
                                bgcolor=INK if primary else "#E2E5E4",
                                color="#FFFFFF" if primary else INK,
                                side={ft.ControlState.FOCUSED: ft.BorderSide(3, CYAN),
                                      ft.ControlState.DEFAULT: ft.BorderSide(1, "#A4ACAF")},
                                shape=ft.RoundedRectangleBorder(radius=12), padding=12))
        control.content.color = "#FFFFFF" if primary else INK
        self.buttons.append(control)
        return control

    def actions(self, *buttons):
        return ft.Row(list(buttons), spacing=12)

    def title(self, key, text):
        item = label(key, text, weight=ft.FontWeight.W_700)
        item.size = 27
        return item

    def card(self, content, dark=False):
        return ft.Container(content, bgcolor=INK if dark else "#E4E7E5", border_radius=12,
                            border=ft.Border.all(1, "#ADB4B5"), padding=16)

    def status(self, key, text, state, detail):
        color = GREEN if state == "ready" else AMBER
        icon = ft.Icons.CHECK_CIRCLE if state == "ready" else ft.Icons.INFO_OUTLINE
        indicator = (ft.ProgressRing(width=24, height=24, stroke_width=3, color=AMBER)
                     if state == "checking" else ft.Icon(icon, color=color, size=24))
        return ft.Container(ft.Row([indicator,
                            ft.Container(label(key, text, weight=ft.FontWeight.W_600), expand=True),
                            ft.Text(detail, size=16, color=color)]),
                            bgcolor="#E4E7E5", border_radius=9, padding=ft.Padding(12, 9, 12, 9))

    def go(self, screen):
        if self.setup.session_busy and screen != 'team':
            return
        if self.setup.busy and screen not in ("progress", "logs"):
            return
        self.startup_pending = False
        self.screen, self.focus_index = screen, 0
        self.render()
        self.schedule_focus()

    def schedule_focus(self):
        if not self.connected:
            return
        # Flet returns a concurrent Future; keep it alive while the client replies.
        task = self.page.run_task(self.focus)
        if task is not None:
            self.focus_tasks.add(task)
            task.add_done_callback(self.focus_tasks.discard)

    def disconnect_focus(self):
        self.connected = False
        for task in tuple(self.focus_tasks):
            task.cancel()
        self.focus_tasks.clear()

    async def focus(self):
        async with self.gallery_navigation:
            if self.connected:
                await self._focus()

    async def _focus(self):
        if self.screen in ('team', 'trainers', 'bank'):
            return
        enabled = [b for b in self.buttons if not b.disabled]
        if enabled:
            target = self.buttons[min(self.focus_index, len(self.buttons) - 1)]
            if self.screen == "home" and self.focus_index < len(PORTABLE_GAMES):
                await self.game_list.scroll_to(offset=self.game_scroll_offset(self.focus_index), duration=150)
            if self.screen == 'team':
                return
            await (target if not target.disabled else enabled[0]).focus()

    async def key(self, e):
        if self.updater.handoff:
            return
        if e.key == "?":
            self.resources.toggle()
            return
        if self.screen in ('team', 'trainers', 'bank'):
            # Native input/dropdown navigation owns arrows; Escape must not dismiss
            # a confirmation and navigate away in the same event.
            return
        if e.key == "Escape":
            self.go("progress" if self.screen == "logs" else "board" if self.screen == "reinstall" else "health")
        elif e.key in ("Arrow Up", "Arrow Down", "Arrow Left", "Arrow Right"):
            if self.screen == "logs" and e.key in ("Arrow Up", "Arrow Down"):
                self.log_list.auto_scroll = False
                self.log_list.update()
                await self.log_list.scroll_to(delta=-80 if e.key == "Arrow Up" else 80, duration=100)
                return
            if not self.buttons:
                return
            if self.screen == "home":
                count = len(PORTABLE_GAMES)
                if e.key == "Arrow Up":
                    self.focus_index = self.buttons.index(self.settings_button)
                elif e.key == "Arrow Down":
                    self.focus_index = next((i for i, game in enumerate(PORTABLE_GAMES)
                                             if game == self.selected_game), 0)
                elif self.focus_index < count:
                    direction = -1 if e.key == "Arrow Left" else 1
                    self.focus_index = max(0, min(count - 1, self.focus_index + direction))
                else:
                    header = [i for i in range(count, len(self.buttons)) if not self.buttons[i].disabled]
                    if header:
                        position = header.index(self.focus_index) if self.focus_index in header else 0
                        direction = -1 if e.key == 'Arrow Left' else 1
                        self.focus_index = header[max(0, min(len(header) - 1, position + direction))]
                await self.focus()
                return
            direction = -1 if e.key in ("Arrow Up", "Arrow Left") else 1
            for _ in self.buttons:
                self.focus_index = (self.focus_index + direction) % len(self.buttons)
                if not self.buttons[self.focus_index].disabled:
                    break
            await self.focus()

    def changed(self):
        self.updater.sync()
        if self.closing or not self.connected:
            return
        if self.startup_pending and self.setup.initialized and not self.setup.checking:
            self.startup_pending = False
            if self.screen == "health" and self.setup.ready and not self.setup.busy:
                self.go("home")
                return
        if self.screen == 'team' and self.team_view:
            self.team_view.refresh()
            return
        if self.setup.busy and self.screen not in ("progress", "logs"):
            self.screen = "progress"
        if self.screen == self.rendered_screen == "logs":
            self.update_logs()
            self.log_status.value = "En vivo" if self.setup.busy else self.phase_text()
            self.step.value = "DEMO" if self.setup.demo else ("En curso" if self.setup.busy else "Finalizado")
            self.log_list.update()
            self.log_status.update()
            self.step.update()
            return
        if (self.screen == self.rendered_screen == "progress"
                and self.rendered_busy == self.setup.busy):
            self.phase_label.value = self.phase_text()
            self.progress_bar.value = self.setup.progress
            self.percent_label.value = f"{self.setup.progress:.0%}" if self.setup.progress is not None else ""
            self.phase_label.update()
            self.progress_bar.update()
            self.percent_label.update()
            return
        self.render()

    def render(self, update=True):
        s = self.setup
        self.body.padding = ft.Padding(16, 8, 16, 8) if self.screen == 'team' else ft.Padding(24, 16, 24, 12)
        self.buttons = []
        self.step.value = "DEMO" if s.demo else ""
        self.header_text.value = tr("portable.header", "POKÉDEX · INICIO")
        self.footer.value = tr("portable.hints", "↑↓ Seleccionar · Enter Confirmar · Esc Volver")
        if s.demo:
            self.footer.value = "DEMO VISUAL · Sin claves ni hardware reales"
        content = getattr(self, f"view_{self.screen}")()
        self.settings_button.visible = self.screen in ("home", "ready", "team") and not s.busy
        self.close_button.disabled = s.busy or s.session_busy
        self.settings_button.disabled = s.session_busy
        self.updater.sync()
        for control in (self.updater.button, self.settings_button, self.close_button):
            if control.visible:
                self.buttons.append(control)
        self.body.content = content
        self.rendered_screen, self.rendered_busy = self.screen, s.busy
        if update:
            self.page.update()
            # These controls stay mounted while the body is replaced.
            if self.header_text.parent is not None:
                self.header_text.update()
                self.step.update()
                self.footer.update()
                self.updater.button.update()
                self.settings_button.update()
                self.close_button.update()

    def layout(self, heading, content, actions):
        return ft.Column([heading, ft.Container(content, expand=True), actions], spacing=12, expand=True)

    def view_health(self):
        s = self.setup
        statuses = ft.Column([
            ft.Text(("La comprobación está tardando más de lo habitual. " if s.check_slow else "")
                    + s.check_detail if s.checking else "Comprobamos que todo esté listo.",
                    size=14, max_lines=2),
            self.status("engine", "Motor Pokémon", "checking" if s.checking and not s.engine_ready else "ready" if s.engine_ready else "error",
                        "Listo" if s.engine_ready else "Comprobando…" if s.checking else "Revisar"),
            self.status("keys", "Claves de la consola", "ready" if not s.keys_error else "missing",
                        "Listas" if not s.keys_error else "Pendientes"),
            self.status("radio", "Módulo inalámbrico", s.radio_state,
                        {"ready": "Listo", "flash": "Firmware requerido", "checking": "Comprobando…"}.get(s.radio_state, "Revisar conexión")),
        ], spacing=8, scroll=ft.ScrollMode.AUTO)
        if s.engine_error:
            statuses.controls.append(ft.Text(s.engine_error, size=15, color=AMBER))
        primary = self.button("configure", "Abrir mi Pokédex" if s.ready else "Configurar ahora",
                              lambda: self.go("home" if s.ready else "keys"), True, s.checking)
        local = self.button("local", "Modo local", self.enter_local, disabled=not s.engine_ready)
        retry = (self.button("module", "Módulo", lambda: self.go("board"), disabled=s.checking)
                 if s.radio_state == "ready" else self.button("retry", "Revisar", self.recheck, disabled=s.checking))
        statuses.controls.append(ft.Row([
            self.button("trainers", "Entrenadores", lambda: self.go("trainers"), disabled=s.busy or s.session_busy),
            self.button("bank", "Banco", lambda: self.go("bank"), disabled=s.busy or s.session_busy),
        ]))
        if not self.page.web and not s.demo and not s.checking and not getattr(sys, 'frozen', False):
            statuses.controls[0] = ft.Row([
                ft.Container(self.updater.status, expand=True),
                ft.IconButton(ft.Icons.REFRESH, tooltip='Comprobar actualizaciones',
                              height=28, width=28, icon_size=20,
                              on_click=self.updater.check, disabled=self.updater.handoff),
            ], height=32)
        return self.layout(self.title("health", "Preparando tu Pokédex"), statuses, self.actions(primary, local, retry))

    def view_trainers(self):
        from gui.portable_trainers_view import TrainersView
        self.header_text.value = "CONFIGURACIÓN · ENTRENADORES"
        self.trainers_view = TrainersView(self)
        return self.trainers_view.control

    def view_bank(self):
        from gui.portable_bank_view import BankView
        self.header_text.value = "CONFIGURACIÓN · BANCO"
        self.bank_view = BankView(self)
        return self.bank_view.control

    async def open_bank_record(self, game_key, data, *, edit):
        from gui.portable_bank_team import BankTeam
        from gui.portable_bank_view import BankEditorView
        from gui.portable_team import shared_team
        from gui.popups import Dialogs
        from pokeldn.app.popups import Manager
        if self.setup.session_busy or self.setup.busy or self.setup.checking:
            raise ValueError("Espera a que termine la sesión o comprobación.")
        controller = BankTeam(game_key, self.setup, data, edit=edit,
                              source_team=shared_team(game_key, self.setup))
        await controller.load_original()
        if (self.setup.session_busy or self.setup.busy or self.setup.checking
                or self.closing or self.screen != 'bank'):
            controller.dispose()
            return
        if self.team_view:
            self.team_view.dispose()
        async def call_ui(fn):
            fn()
        controller.popups = Manager(Dialogs(self.page), call=lambda fn: self.page.run_task(call_ui, fn))
        self.selected_game = next(game for game in PORTABLE_GAMES if game.key == game_key)
        self.team_view = BankEditorView(self, controller)
        self.go('team')
        self.page.run_task(self.team_view.load)

    def enter_local(self):
        self.local = True
        self.go("home")

    async def recheck(self):
        await self.setup.check()

    def view_keys(self):
        self.header_text.value = "CONFIGURACIÓN"
        self.step.value = "1 de 2" + (" · DEMO" if self.setup.demo else "")
        valid = not self.setup.keys_error
        controls = [label("keys_hint", "Selecciona el archivo prod.keys de tu consola."),
                    self.card(ft.Row([ft.Icon(ft.Icons.KEY, size=44, color=AMBER), ft.Column([
                        label("key_file", "prod.keys", weight=ft.FontWeight.W_700),
                        ft.Text("Claves verificadas" if valid else "Sin verificar", color=GREEN if valid else MUTED, size=18),
                    ], spacing=4)])),
                    label("keys_privacy", "Las claves se guardan solo en este dispositivo.")]
        if self.page.web and not self.setup.demo:
            controls.append(ft.Text("Vista web: el archivo se enviará al servidor local de esta app.", size=14, color=MUTED))
        if self.error:
            controls.append(ft.Text(self.error, color=AMBER, size=15))
        return self.layout(self.title("keys_title", "Claves de la consola"),
                           ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO),
                           self.actions(self.button("select_file", "Cambiar archivo" if valid else "Seleccionar archivo", self.pick_keys, not valid),
                                        self.button("next", "Continuar", lambda: self.go("board"), valid, not valid)))

    async def pick_keys(self):
        self.error = ""
        if self.setup.demo:
            await self.setup.import_keys(b"demo")
            return
        try:
            files = await self.picker.pick_files(dialog_title="Seleccionar prod.keys", allow_multiple=False,
                        file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["keys"], with_data=self.page.web)
            if not files:
                return
            selected = files[0]
            if selected.size > MAX_KEYS:
                self.error = "El archivo supera el límite de 1 MB."
            elif selected.bytes is not None:
                await self.setup.import_keys(selected.bytes)
            elif selected.path:
                def read():
                    with Path(selected.path).open("rb") as stream:
                        return stream.read(MAX_KEYS + 1)
                await self.setup.import_keys(await asyncio.to_thread(read))
            else:
                self.error = "El selector no pudo leer el archivo."
            self.error = self.error or self.setup.keys_error
        except Exception:
            self.error = "No se pudo seleccionar el archivo. Inténtalo de nuevo."
        self.render()

    def view_board(self):
        s = self.setup
        self.header_text.value = "CONFIGURACIÓN"
        self.step.value = "2 de 2" + (" · DEMO" if s.demo else "")
        state = "Conectado por USB" if s.radio_state in ("ready", "flash") else "Revisa la conexión USB"
        info = ft.Column([self.card(ft.Row([ft.Icon(ft.Icons.MEMORY, size=50, color=INK), ft.Column([
                    label("board_name", s.chip or "ESP32-C6 / ESP32-S3", weight=ft.FontWeight.W_700),
                    ft.Text(state, color=GREEN if s.radio_state == "ready" else MUTED, size=18),
                ], spacing=8)])), ft.Text(s.radio_detail, size=18, color=INK)], spacing=12, scroll=ft.ScrollMode.AUTO)
        if s.radio_state == "flash":
            info.controls.append(label("flash_hint", "Instalaremos el firmware de radio. Mantén el módulo conectado."))
            main = self.button("install", "Instalar firmware", self.install, True, s.checking)
        elif s.radio_state == "ready":
            main = self.button("continue", "Continuar", lambda: self.go("ready"), True)
        else:
            main = self.button("check_usb", "Comprobar conexión", self.recheck, True, s.checking)
        secondary = (self.button("reinstall", "Reinstalar firmware", lambda: self.go("reinstall"), disabled=s.checking)
                     if s.radio_state == "ready" else
                     self.button("later", "Ahora no", self.enter_local, disabled=not s.engine_ready or s.checking))
        return self.layout(self.title("board_title", "Preparar módulo inalámbrico"), info,
                           self.actions(main, secondary))

    def view_reinstall(self):
        s = self.setup
        self.header_text.value = "CONFIRMAR REINSTALACIÓN"
        info = ft.Column([
            self.card(ft.Column([label("board_name", s.chip or "ESP32-C6 / ESP32-S3", weight=ft.FontWeight.W_700),
                                 ft.Text(s.device if not s.demo else "Placa simulada · DEMO", size=16, color=MUTED)], spacing=8)),
            label("reinstall_explain", "La placa ya tiene firmware compatible. Esta acción volverá a escribir el firmware de radio disponible."),
            label("reinstall_warning", "Mantén la placa conectada y el dispositivo encendido hasta terminar."),
        ], spacing=12, scroll=ft.ScrollMode.AUTO)
        allowed = s.radio_state == "ready" and s.chip in SUPPORTED_RADIO_CHIPS and not s.busy and not s.checking
        return self.layout(self.title("reinstall_title", "¿Reinstalar firmware?"), info, self.actions(
            self.button("cancel", "Cancelar", lambda: self.go("board"), True),
            self.button("confirm_reinstall", "Confirmar reinstalación", lambda: self.install(reinstall=True), disabled=not allowed)))

    async def install(self, *, reinstall=False):
        self.screen = "progress"
        # Closing a web client must not cancel a firmware write owned by the server.
        await asyncio.shield(self.setup.install(reinstall=reinstall))

    def phase_text(self):
        return {"idle": "Preparando…", "download": "Preparando firmware…", "write": "Instalando firmware…",
                "verify": "Comprobando la radio…", "done": "Firmware instalado", "error": "Requiere atención"}[self.setup.phase]

    def view_progress(self):
        s = self.setup
        self.header_text.value = "CONFIGURACIÓN"
        self.step.value = "2 de 2" + (" · DEMO" if s.demo else "")
        percentage = f"{s.progress:.0%}" if s.progress is not None else ""
        self.phase_label = label("phase", self.phase_text(), weight=ft.FontWeight.W_700)
        self.progress_bar = ft.ProgressBar(value=s.progress, expand=True, height=18, border_radius=9, color=GREEN, bgcolor="#CBD2D1")
        self.percent_label = ft.Text(percentage, size=24, color=INK, weight=ft.FontWeight.W_700)
        info = ft.Column([
            ft.Row([ft.Icon(ft.Icons.MEMORY, size=42, color=INK), label("board_name", s.chip or "ESP32-C6 / ESP32-S3", weight=ft.FontWeight.W_700)]),
            self.card(ft.Column([self.phase_label,
                     ft.Row([self.progress_bar, self.percent_label]),
                     label("keep_connected", "Mantén el módulo conectado y el dispositivo encendido.")], spacing=15)),
        ], spacing=12, scroll=ft.ScrollMode.AUTO)
        if s.error:
            info.controls.append(ft.Text(s.error, color=AMBER, size=16))
        buttons = [self.button("details", "Ver detalles", lambda: self.go("logs"), True, icon=ft.Icons.SUBJECT)]
        if not s.busy:
            buttons.append(self.button("continue", "Continuar" if s.phase == "done" else "Revisar conexión",
                          lambda: self.go("ready" if s.phase == "done" else "board")))
        return self.layout(self.title("preparing_radio", "Preparando módulo inalámbrico"), info, self.actions(*buttons))

    def view_logs(self):
        s = self.setup
        self.header_text.value = "DETALLES DE INSTALACIÓN"
        self.step.value = "DEMO" if s.demo else ("En curso" if s.busy else "Finalizado")
        self.footer.value = "↑↓ Recorrer registro · Esc Volver al progreso"
        self.update_logs()
        self.log_status = ft.Text("En vivo" if s.busy else self.phase_text(), color=GREEN, size=16)
        heading = ft.Row([ft.Container(self.title("log_title", "Registro de instalación"), expand=True),
                          self.log_status])
        return self.layout(heading, ft.Container(self.log_list, bgcolor=INK, border_radius=12, expand=True),
                           self.actions(self.button("back_progress", "Volver al progreso", lambda: self.go("progress"), True, icon=ft.Icons.ARROW_BACK)))

    def update_logs(self):
        self.log_list.controls = [ft.Text(line, font_family="monospace", size=15, color="#D9F4F0", selectable=True)
                                  for line in self.setup.logs] or [ft.Text("Esperando mensajes del instalador…", color="#D9F4F0", size=16)]

    def view_ready(self):
        s = self.setup
        if not s.ready:
            return self.view_health()
        return self.layout(self.title("ready_title", "¡Todo listo!"), ft.Column([
            ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, size=48, color=GREEN), label("ready_hint", "Tu taller Pokémon está preparado.")]),
            self.status("engine", "Motor Pokémon", "ready", "Disponible"),
            self.status("keys", "Claves de la consola", "ready", "Verificadas"),
            self.status("radio", "Módulo inalámbrico", "ready", "Listo"),
        ], spacing=10, scroll=ft.ScrollMode.AUTO), self.actions(self.button("open", "Abrir mi Pokédex", lambda: self.go("home"), True)))

    def game_scroll_offset(self, index):
        viewport = (getattr(self.page, "width", None) or 800) - 64
        maximum = max(0, len(PORTABLE_GAMES) * 182 - 12 + 8 - viewport)
        return min(maximum, max(0, index * 182 - 182))

    async def select_game(self, game):
        # Flet 1.0.5 closes the session if a scroll/focus response arrives after
        # its control was unmounted. Finish gallery calls before replacing it.
        async with self.gallery_navigation:
            if self.screen != 'home' or game not in PORTABLE_GAMES or self.setup.session_busy:
                return
            self.open_team(game)

    def open_team(self, game):
        from gui.portable_team import shared_team
        from gui.portable_team_view import TeamView
        from gui.popups import Dialogs
        from pokeldn.app.popups import Manager
        if self.team_view:
            self.team_view.dispose()
        self.selected_game = game
        controller = shared_team(game.key, self.setup)
        async def call_ui(fn):
            fn()
        if not controller.busy:
            controller.popups = Manager(Dialogs(self.page), call=lambda fn: self.page.run_task(call_ui, fn))
        self.team_view = TeamView(self, controller)
        self.go('team')
        self.page.run_task(self.team_view.load)

    def open_trade_mode(self, mode, resume=False):
        if self.setup.session_busy and not resume:
            return
        if mode == 'team':
            self.open_team(self.selected_game)
            return
        from gui.portable_received import ReceivedTeam
        from gui.portable_received_view import ReceivedView
        from gui.portable_team import shared_team
        from gui.popups import Dialogs
        from pokeldn.app.popups import Manager
        if self.team_view:
            self.team_view.dispose()
        if not hasattr(self.setup, 'received_modes'):
            self.setup.received_modes = {}
        key = (self.selected_game.key, mode)
        if resume:
            controller = self.setup.active_team
        else:
            controller = self.setup.received_modes.get(key)
            if controller is None:
                controller = ReceivedTeam(self.selected_game.key, self.setup, mode)
                base = shared_team(self.selected_game.key, self.setup)
                controller.role, controller.version, controller.code = base.role, base.version, base.code
                self.setup.received_modes[key] = controller
        async def call_ui(fn):
            fn()
        if not controller.active:
            controller.popups = Manager(Dialogs(self.page), call=lambda fn: self.page.run_task(call_ui, fn))
        self.team_view = ReceivedView(self, controller, trainer_model=shared_team(self.selected_game.key, self.setup))
        self.go('team')
        self.page.run_task(self.team_view.load)

    def view_team(self):
        self.header_text.value = 'POKÉDEX · ' + GAME_NAMES[self.selected_game.key].upper()
        self.header_text.size = 16
        self.footer.value = 'Tab / Shift+Tab Navegar · Enter Elegir · Guardado automático'
        return self.team_view.control

    def view_home(self):
        self.header_text.value = "POKÉDEX · JUEGOS"
        self.footer.value = "← → Explorar · Enter Elegir · ↑ Ajustes"
        tiles = []
        for index, game in enumerate(PORTABLE_GAMES):
            async def focused(e, index=index):
                async with self.gallery_navigation:
                    if self.screen != 'home':
                        return
                    self.focus_index = index
                    await self.game_list.scroll_to(offset=self.game_scroll_offset(index), duration=150)
            async def selected(e, game=game):
                await self.select_game(game)
            tile = ft.Button(
                ft.Column([game_avatar(game), ft.Container(
                    ft.Text(GAME_NAMES[game.key], size=18,
                            color="#FFFFFF" if game == self.selected_game else INK,
                            text_align=ft.TextAlign.CENTER, max_lines=3),
                    height=72, alignment=ft.Alignment.TOP_CENTER)],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16,
                    alignment=ft.MainAxisAlignment.CENTER),
                width=170, on_click=selected,
                on_focus=focused, tooltip=GAME_NAMES[game.key],
                style=ft.ButtonStyle(bgcolor=DARK_RED if game == self.selected_game else PAPER, padding=10,
                    side={ft.ControlState.FOCUSED: ft.BorderSide(3, CYAN),
                          ft.ControlState.DEFAULT: ft.BorderSide(2, DARK_RED if game == self.selected_game else PAPER)},
                    shape=ft.RoundedRectangleBorder(radius=18)))
            tiles.append(tile)
            self.buttons.append(tile)
        self.game_list = ft.ListView(tiles, horizontal=True, spacing=12,
                                    build_controls_on_demand=False, padding=4,
                                    scroll=ft.ScrollMode.ALWAYS, expand=True)
        return ft.Column([self.title("choose_game", "Elige el juego"),
                          self.game_list], spacing=12, expand=True)

    async def start(self):
        if self.setup.active_team:
            game = next(g for g in PORTABLE_GAMES if g.key == self.setup.active_team.game)
            if getattr(self.setup.active_team, 'mode', None):
                self.selected_game = game
                self.open_trade_mode(self.setup.active_team.mode, resume=True)
            else:
                self.open_team(game)
            return
        if not self.setup.initialized:
            await self.setup.check()
        if not self.startup_pending:
            return
        if not self.setup.checking:
            self.startup_pending = False
        if self.setup.ready and not self.setup.busy:
            self.go("home")
        else:
            await self.focus()


async def main(page: ft.Page):
    page.title = "Pokédex · Configuración"
    page.padding = 0
    page.bgcolor = RED
    page.theme_mode = ft.ThemeMode.LIGHT
    page.fonts = {**(page.fonts or {}), **theme.FONT_ASSETS}
    page.theme = ft.Theme(color_scheme_seed=RED, font_family="Arial",
                         text_theme=ft.TextTheme(**{
                             field.name: ft.TextStyle(color=INK, font_family_fallback=theme.FALLBACK_FONTS)
                             for field in fields(ft.TextTheme)}),
                         icon_button_theme=ft.IconButtonTheme(style=ft.ButtonStyle(
                             visual_density=ft.VisualDensity.COMPACT, padding=0)))
    page.window.width, page.window.height = 800, 480
    page.window.min_width, page.window.min_height = 640, 400
    page.window.prevent_close = True
    # The macOS title bar consumes 32 logical pixels inside Flet's reported
    # window height. Reserve it in addition to the portable 480-pixel canvas.
    if not page.web and sys.platform == 'darwin':
        page.window.height = 512
        page.window.min_width, page.window.min_height = 800, 512
    demo = os.environ.get("POKELDN_PORTABLE_DEMO") == "1"
    setup = Setup(demo=True) if demo else shared_setup()
    view = PortableView(page, setup)
    page.on_keyboard_event = view.key
    async def window_event(e):
        if e.type == ft.WindowEventType.CLOSE:
            await view.close(e)
    page.window.on_event = window_event
    # Notifications can originate from another web session: dispatch on this page.
    def changed():
        if not view.closing and view.connected:
            page.run_task(refresh)
    async def refresh():
        view.changed()
    view.setup_listener = changed
    setup.listeners.add(changed)
    async def disconnect(e):
        view.disconnect_focus()
        view.resources.connected = False
        view.resources.sync()
        setup.listeners.discard(changed)
    async def reconnect(e):
        if view.closing:
            return
        view.connected = True
        view.resources.connected = True
        view.resources.sync()
        setup.listeners.add(changed)
        view.changed()
    page.on_disconnect = disconnect
    page.on_connect = reconnect
    # A trial version cannot touch the radio or accept input until the helper
    # commits its startup handshake. A missing board is not an update failure.
    trial = bool(os.environ.get("POKELDN_UPDATE_JOB"))
    view.control.disabled = trial
    page.add(view.control)
    if trial:
        try:
            await asyncio.to_thread(portable_update.acknowledge_startup)
        except (portable_update.UpdateError, OSError):
            await view.close(None)
            return
        view.control.disabled = False
        page.update()
    page.run_task(view.updater.check)
    await view.start()
