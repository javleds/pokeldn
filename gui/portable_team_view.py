"""Compact Equipo presentation; generation and session ownership live in portable_team."""
import asyncio
import json
from types import SimpleNamespace

import flet as ft

from gui import theme
from gui.views.sprites import Sprite
from gui.views.widgets import on_ui
from pokeldn import console_trainer
from pokeldn.lgpe.session import CODE_PICKER

PAPER = "#F3F1EA"
INK = "#243139"
MUTED = "#5C6870"
RED = "#A52D39"
GREEN = "#217448"
CYAN = "#00A9BA"
STATS = (("hp", "PS"), ("atk", "Ataque"), ("def", "Defensa"),
         ("spa", "At. Esp."), ("spd", "Def. Esp."), ("spe", "Velocidad"))


def text(value, size=14, **kwargs):
    return ft.Text(value, size=size, color=INK, **kwargs)


def labeled(name, control, expand=False, width=None):
    return ft.Column([text(name, 12), control], spacing=3, expand=expand, width=width,
                     tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


class TeamView:
    """Owns controls, never the serial connection. Status refreshes preserve active inputs."""

    def __init__(self, shell, controller):
        self.shell, self.page, self.model = shell, shell.page, controller
        self.selected = next((i for i, slot in enumerate(controller.slots) if slot), 0)
        self.tab = "basic"
        self.species_names = []
        self.move_names = []
        self.loading_error = ""
        self.editor_controls = []
        self.slot_sprites = []
        self.slot_labels = []
        self.slot_marks = []
        self.slot_buttons = []
        self.logs_dialog = None
        self.logs_list = None
        self.disposed = False
        self.loaded = False
        self.last_profiles = None
        self.basic_content = None
        self.basic_controls = []
        self.basic_sprite = None
        self.editor_cache = {}
        self.adapter = SimpleNamespace(settings=controller.settings, ui=lambda fn: on_ui(self.page, fn))
        self.back = self.icon(ft.Icons.ARROW_BACK, "Volver a juegos", self._back)
        self.connection = ft.TextButton("Anfitrión · Configurar", on_click=self._connection)
        self.trainer_model = controller
        self._init_trainer()
        self.clear_all = self.icon(ft.Icons.DELETE_OUTLINE, "Vaciar equipo", lambda e: self._confirm_clear(None), RED)
        for button in (self.trainer_info, self.find, self.clear_all):
            button.height = 40
        self.clear_one = self.icon(ft.Icons.BACKSPACE_OUTLINED, "Vaciar esta caja", lambda e: self._confirm_clear(self.selected), RED)
        self.start = self.icon(ft.Icons.SWAP_HORIZ, "Iniciar intercambio", self._start, GREEN)
        self.cancel = self.icon(ft.Icons.STOP_CIRCLE_OUTLINED, "Cancelar intercambio", self._cancel, RED)
        self.logs = self.icon(ft.Icons.ARTICLE_OUTLINED, "Ver logs", self._logs)
        self.loader = ft.ProgressRing(width=25, height=25, stroke_width=3, color=CYAN, visible=False)
        self.cancel.visible = False
        self.logs.visible = False
        self.slot_row = self._slot_row()
        self.tab_buttons = []
        for key, title in (("basic", "Básico"), ("stats", "EV / IV"), ("advanced", "Avanzado")):
            button = ft.TextButton(title, on_click=lambda e, key=key: self._select_tab(key), height=30,
                                   style=ft.ButtonStyle(padding=ft.Padding(10, 2, 10, 2)))
            self.tab_buttons.append(button)
        self.editor = ft.Container(expand=True)
        self.max_checks = {}
        for group, title in (("effort", "EVs máx."), ("friendship", "Amistad máx.")):
            self.max_checks[group] = ft.Checkbox(label=title, value=False, height=30,
                label_style=ft.TextStyle(size=12, color=INK),
                visual_density=ft.VisualDensity.COMPACT,
                tooltip="Aplicar máximos a esta caja. Desmarcar vuelve a Automático.",
                on_change=lambda e, group=group: self._toggle_max(group, e.control.value))
        self.session_title = text("Equipo", 16, weight=ft.FontWeight.W_700)
        from gui.portable_received import MODES
        self.mode_menu = ft.PopupMenuButton(content=ft.Row([self.session_title,
            ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=INK)], spacing=4), tooltip='Modalidad de intercambio',
            items=[ft.PopupMenuItem(content=title, height=36, checked=key == 'team',
                on_click=lambda e, key=key: self.shell.open_trade_mode(key)) for key, title in MODES.items()])
        self.session = ft.Column([], spacing=10, expand=True, visible=False, scroll=ft.ScrollMode.AUTO)
        self.status = text("Cargando datos Pokémon…", 12, max_lines=2)
        self.status_panel = ft.Container(self.status, padding=ft.Padding(8, 4, 8, 4), border_radius=8)
        self.editor_tabs = ft.Row([*self.tab_buttons, ft.Container(expand=True), *self.max_checks.values(), self.clear_one], height=30, spacing=3)
        self.slot_panel = ft.Container(self.slot_row, border_radius=10)
        self.control = ft.Column([
            self._trade_header(),
            self.slot_panel,
            self.editor_tabs,
            self.editor, self.session, self.status_panel,
        ], spacing=7, expand=True)
        self.model.listeners.add(self._notified)
        self._draw_editor()
        self.refresh(update=False)

    def _init_trainer(self):
        self.last_profiles = None
        self.trainer = self.dropdown([], None, self._trainer_selected, clear_value='base')
        self.trainer.expand = True
        self.trainer.tooltip = 'Entrenador de la oferta · El recibido conserva su propietario original'
        self.trainer_info = self.icon(ft.Icons.BADGE_OUTLINED, 'Datos del entrenador', self._trainer_info)
        self.find = self.icon(ft.Icons.PERSON_SEARCH, 'Encontrar mi entrenador', self._find_trainer, GREEN)

    def _trade_header(self):
        self.connection.tooltip = 'Configurar conexión local'
        self.connection.height = self.mode_menu.height = 40
        trainer = ft.Row([self.trainer, self.trainer_info, self.find], spacing=2)
        return ft.Row([self.back, labeled('Modalidad', self.mode_menu, width=150),
                       labeled('Entrenador', trainer, expand=True),
                       labeled('Conexión', self.connection, width=105)], spacing=8, height=60,
                      vertical_alignment=ft.CrossAxisAlignment.END)

    def _refresh_trainer(self, locked):
        m = self.trainer_model
        choices = [('base', 'Base de pokeLDN'), *[(key, f"{item['ot']} · {key[:6]}")
                   for key, item in m.profiles.items() if key != 'base']]
        if choices != self.last_profiles:
            self._set_choices(self.trainer, choices)
            self.last_profiles = choices
        if not self.trainer.portable_searching:
            self.trainer.value = m.selected_trainer
        self.trainer.data = m.selected_trainer
        self.trainer.disabled = self.trainer_info.disabled = self.find.disabled = locked
        self.trainer_info.opacity = self.find.opacity = 0.4 if locked else 1

    def icon(self, icon, tooltip, callback, color=INK):
        return ft.IconButton(icon, tooltip=tooltip, on_click=callback, icon_size=21, width=36, height=40,
                             icon_color=color, style=ft.ButtonStyle(
                                 side={ft.ControlState.FOCUSED: ft.BorderSide(2, CYAN)},
                                 shape=ft.RoundedRectangleBorder(radius=8), padding=5))

    def dropdown(self, choices, value, callback, search=True, clear_value=None):
        selected_value = str(value) if value is not None else None
        def selected(e):
            nonlocal selected_value
            if e.control.value not in {option.key for option in e.control.options}:
                return
            selected_value = e.control.value
            e.control.data = selected_value
            e.control.portable_searching = False
            callback(e)

        def restore_selection(e):
            e.control.portable_searching = False
            # Search text is a query, never a new free-form option.
            e.control.value = e.control.data
            e.control.text = next((option.text for option in e.control.options
                                   if option.key == e.control.data), "")
            if e.control.parent is not None:
                e.control.update()

        def begin_search(e):
            if e.control.disabled or self.model.busy or e.control.portable_searching:
                return
            # Flet 1.0.5 ignores backend-only text changes in its controller.
            # Clear the widget value too; data/model retain the committed option.
            e.control.portable_searching = True
            e.control.value = None
            e.control.text = ""
            if e.control.parent is not None:
                e.control.update()

        control = theme.dropdown([(str(key), name) for key, name in choices],
                                 selected_value, on_select=selected,
                                 editable=search, enable_filter=search, enable_search=True, menu_height=220)
        def clear(e):
            if control.disabled or self.model.busy:
                return
            control.value = control.data = clear_value
            control.portable_searching = False
            control.text = next((option.text for option in control.options
                                 if option.key == clear_value), "")
            callback(SimpleNamespace(control=control))
            if control.parent is not None:
                control.update()

        if search:
            control.on_focus = begin_search
            # Subscribe so Flutter synchronizes the query back to Python. Otherwise
            # restoring the same label can be omitted as an unchanged property.
            control.on_text_change = lambda e: None
            control.selected_suffix = ft.IconButton(ft.Icons.CLOSE, tooltip="Limpiar selección",
                icon_size=15, width=24, height=28, padding=0, icon_color=MUTED,
                visual_density=ft.VisualDensity.COMPACT, on_click=clear)
        control.on_blur = restore_selection
        # The desktop helper removes menu_height for initially short lists. These
        # lists are populated later, so always bound the portable overlay explicitly.
        control.menu_height = 160
        control.menu_width = 280
        control.data = selected_value
        control.portable_searching = False
        control.expand = False
        # A finite preferred width fills each constrained form column without
        # propagating an infinite minimum width to Flutter's menu overlay.
        control.width = 280
        control.expanded_insets = ft.Padding(0, 0, 0, 0)
        control.bgcolor = "#FFFEF8"
        control.fill_color = "#FFFEF8"
        control.color = INK
        control.text_size = 14
        control.height = 40
        control.border = {
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(border_radius=8, side=ft.BorderSide(1, "#B3BABB")),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(border_radius=8, side=ft.BorderSide(2, CYAN)),
        }
        control.content_padding = ft.Padding(8, 4, 8, 4)
        control.border_color = "#B3BABB"
        control.focused_border_color = CYAN
        control.menu_style = ft.MenuStyle(bgcolor=PAPER, max_size=ft.Size(280, 160),
                                         min_size=ft.Size(0, 0))
        if search:
            control.trailing_icon = ft.Row([control.selected_suffix, ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=16)],
                                          tight=True, spacing=0, height=28)
            control.selected_trailing_icon = control.trailing_icon
        else:
            control.trailing_icon = ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=16)
            control.selected_trailing_icon = ft.Icon(ft.Icons.ARROW_DROP_UP, size=16)
        return control

    def _notified(self):
        if not self.disposed:
            self.page.run_task(self._refresh_async)

    async def _refresh_async(self):
        if not self.disposed:
            self.refresh()

    def dispose(self):
        self.disposed = True
        self.model.listeners.discard(self._notified)

    async def load(self):
        try:
            self.species_names, self.move_names = await asyncio.gather(
                self.model.names("species"), self.model.names("moves"))
            if self.model.slots[self.selected]:
                await self.model.load_options(self.selected)
            self.loaded = True
            self._draw_editor()
            self.refresh()
            await self.model.validate_all()
        except Exception as error:
            self.loading_error = str(error)
            self.refresh()

    def _slot_row(self):
        controls = []
        for i, slot in enumerate(self.model.slots):
            sprite = Sprite(self.adapter, int((slot or {}).get("species") or 0), size=34)
            sprite.frame.bgcolor = "#E4E7E5"
            self.slot_sprites.append(sprite)
            name = text(f"Caja {i + 1}", 11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
            mark = ft.Container(ft.Icon(ft.Icons.ADD, size=13, color=MUTED), width=14, height=14)
            self.slot_labels.append(name)
            self.slot_marks.append(mark)
            button = ft.Button(ft.Column([sprite.control, ft.Row([name, mark], spacing=3,
                                   alignment=ft.MainAxisAlignment.CENTER)], spacing=1,
                                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                               expand=True, height=58, tooltip=f"Caja {i + 1}",
                               on_click=lambda e, i=i: self._select_slot(i),
                               style=ft.ButtonStyle(bgcolor=PAPER, padding=3,
                                   side={ft.ControlState.FOCUSED: ft.BorderSide(2, CYAN)},
                                   shape=ft.RoundedRectangleBorder(radius=9)))
            self.slot_buttons.append(button)
            controls.append(button)
        self.session_spacer = ft.Container(expand=True, visible=False)
        return ft.Row([self.session_spacer, *controls, self.start, self.loader, self.cancel, self.logs, self.clear_all], spacing=5, height=58)

    def refresh(self, update=True):
        m = self.model
        if self.basic_content is not None and self.tab == "basic" and m.slots[self.selected]:
            self._sync_move_choices()
        self._refresh_trainer(m.busy)
        self.connection.content = 'Anfitrión' if m.role == 'host' else 'Unirse'
        for control in [self.back, self.connection, self.trainer, self.trainer_info, self.find,
                        self.clear_all, self.clear_one, *self.slot_buttons, *self.tab_buttons,
                        *self.editor_controls]:
            control.disabled = m.busy
        for name in ("settings_button", "close_button"):
            button = getattr(self.shell, name, None)
            if button is not None:
                button.disabled = m.busy or bool(getattr(getattr(m, "setup", None), "session_busy", False))
                if update and button.parent is not None:
                    button.update()
        self.start.disabled = not m.can_start
        self.start.opacity = 0.4 if self.start.disabled else 1
        self.start.visible = not m.busy
        self.loader.visible = m.busy
        self.cancel.visible = m.busy
        self.cancel.disabled = m.phase in ("stopping", "cancelled")
        self.logs.visible = bool(m.logs) or m.busy
        self.clear_all.visible = not m.busy
        self.clear_one.visible = not m.busy
        discovery = bool(getattr(m, 'discovering', False))
        self.mode_menu.disabled = m.busy
        draft = m.slots[self.selected]
        first_empty = next((i for i, slot in enumerate(m.slots) if not (slot or {}).get('species')), 5)
        for i, button in enumerate(self.slot_buttons):
            button.disabled = m.busy or i > first_empty
            button.opacity = 0.4 if i > first_empty else 1
        self.clear_all.disabled = m.busy or not any(m.slots)
        self.clear_one.disabled = m.busy or draft is None
        self.clear_all.opacity = 0.4 if self.clear_all.disabled else 1
        self.clear_one.opacity = 0.4 if self.clear_one.disabled else 1
        for control in [*self.tab_buttons[1:], *self.editor_controls[1:]]:
            control.disabled = m.busy or not (draft or {}).get('species')
        for group, checkbox in self.max_checks.items():
            maximum = self._maximum(group)
            checkbox.visible = self.tab == 'basic' and not discovery
            checkbox.disabled = m.busy or maximum is None or not (draft or {}).get('species')
            chosen = (draft or {}).get('options', {}).get(group)
            checkbox.value = (chosen == maximum if group == 'effort' else str(chosen) == str(maximum)) and maximum is not None
        kind = m.metadata.get(self.selected, {}).get('effort', {}).get('kind')
        self.max_checks['effort'].label = {'avs': 'AVs máx.', 'gvs': 'Esfuerzo máx.'}.get(kind, 'EVs máx.')
        self.session_title.value = 'Identificar' if discovery else 'Equipo'
        self.editor.visible = not m.busy and not discovery
        self.session_spacer.visible = discovery
        self.slot_row.height = 44 if discovery else 58
        self.slot_panel.padding = ft.Padding(10, 2, 4, 2) if discovery else 0
        self.slot_panel.bgcolor = ('#F4DADF' if m.error else '#D7F1EE' if m.busy else '#E4E7E5') if discovery else None
        if discovery:
            phase = ('La sesión requiere atención' if m.error else
                     'Preparando oferta · Aún no busca consola' if m.phase == 'preparing' else
                     'Devolución confirmada' if m.completed >= 2 else
                     'Pokémon recibido · Devolución en curso' if m.completed and m.busy else
                     'Recepción confirmada' if m.completed else
                     'Cerrando la sesión' if m.phase == 'stopping' else
                     'Proceso iniciado · Esperando tu Pokémon' if m.busy else 'Sesión finalizada')
            self.session_spacer.content = text(phase, 15, weight=ft.FontWeight.W_600)
        for button in self.slot_buttons:
            button.visible = not discovery
        self.editor_tabs.visible = not discovery
        self.start.visible = not m.busy and not discovery
        self.clear_all.visible = not m.busy and not discovery
        self.session.visible = m.busy or discovery
        if discovery:
            self._discovery_view()
        elif m.busy:
            heading, detail = {
                'preparing': ('Preparando intercambio', 'Comprobando ofertas y conexión. Aún no busca consola.'),
                'running': ('Proceso iniciado', 'Esperando confirmaciones de tu consola. Si no conecta, revisa el código.'),
                'stopping': ('Cerrando la sesión', 'Cancelación solicitada. Espera antes de desconectar la placa.'),
            }.get(m.phase, ('Intercambio en curso', 'Confirma el intercambio en tu consola.'))
            self.session.controls = [ft.Container(ft.Column([
                text(heading, 23, weight=ft.FontWeight.W_700), text(detail, 14),
                text(f'{m.completed} de {len(m.active_slots)} intercambios confirmados', 13)
            ], spacing=10), bgcolor='#D7F1EE', border_radius=14, padding=18)]
        names = {int(n["id"]): n["name"] for n in self.species_names}
        active = m.active_slots[m.completed] if m.busy and m.completed < len(m.active_slots) else None
        for i, slot in enumerate(m.slots):
            self.slot_labels[i].value = names.get(int((slot or {}).get("species") or 0), f"Caja {i + 1}")
            self.slot_buttons[i].style.bgcolor = "#D6F3EF" if i == self.selected else PAPER
            mark = self.slot_marks[i]
            if m.busy and i in m.active_slots:
                done = m.active_slots.index(i) < m.completed
                mark.content = (ft.ProgressRing(width=13, height=13, stroke_width=2, color=CYAN)
                                if i == active else ft.Icon(ft.Icons.CHECK_CIRCLE if done else ft.Icons.SCHEDULE,
                                                           color=GREEN if done else MUTED, size=13))
                self.slot_buttons[i].tooltip = f"Caja {i + 1} · {'Enviado' if done else 'En curso' if i == active else 'En cola'}"
            else:
                state = m.states[i]
                icon = (ft.Icons.CHECK_CIRCLE if state == "legal" else ft.Icons.ERROR_OUTLINE
                        if state in ("invalid", "error") else ft.Icons.HOURGLASS_TOP
                        if state in ("pending", "validating") else ft.Icons.ADD)
                mark.content = ft.Icon(icon, size=13, color=GREEN if state == "legal" else RED
                                       if state in ("invalid", "error") else MUTED)
                self.slot_buttons[i].tooltip = f"Caja {i + 1}"
                if i > first_empty:
                    mark.content = ft.Icon(ft.Icons.LOCK_OUTLINE, size=13, color=MUTED)
                    self.slot_buttons[i].tooltip = 'Elige especie en la caja anterior para habilitarla'
            wanted = (int((slot or {}).get("species") or 0), bool((slot or {}).get("shiny")),
                      int((slot or {}).get("options", {}).get("form") or 0))
            if getattr(self.slot_sprites[i], "portable_wanted", None) != wanted:
                self.slot_sprites[i].portable_wanted = wanted
                self.slot_sprites[i].show(*wanted[:2], form=wanted[2], update=False)
                if not wanted[0]:
                    self.slot_sprites[i].frame.content = ft.Icon(ft.Icons.ADD, size=24, color=MUTED)
        portrait = getattr(self, "editor_sprite", None)
        if portrait is not None and self.tab == "basic":
            draft = m.slots[self.selected] or {}
            wanted = (int(draft.get("species") or 0), bool(draft.get("shiny")),
                      int(draft.get("options", {}).get("form") or 0))
            if getattr(portrait, "portable_wanted", None) != wanted:
                portrait.portable_wanted = wanted
                portrait.show(*wanted[:2], form=wanted[2], update=False)
        error = m.error or self.loading_error or ('' if discovery else m.errors[self.selected])
        if discovery and getattr(m, 'return_pending', False) and not m.busy:
            error = 'Devolución pendiente: el original no tiene confirmación de regreso. Revisa Received y tu consola.'
        if error:
            self.status.value, self.status.color = error.splitlines()[0], RED
        elif m.busy:
            self.status.value, self.status.color = "Sesión activa · Configuración bloqueada", MUTED
        elif m.states[self.selected] == "validating":
            self.status.value, self.status.color = "Validando cambios…", MUTED
        elif m.phase == "done":
            self.status.value, self.status.color = "✓ Sesión finalizada · Intercambios confirmados", GREEN
        elif m.phase == "stopped":
            self.status.value, self.status.color = "Sesión detenida · Revisa los logs y tu consola", MUTED
        elif m.states[self.selected] == "legal":
            self.status.value, self.status.color = "Pokémon válido · Guardado automáticamente", GREEN
        elif m.states[self.selected] == "pending" and (m.slots[self.selected] or {}).get("species"):
            self.status.value, self.status.color = "Cambios pendientes de validación…", MUTED
        else:
            self.status.value, self.status.color = "Selecciona una caja y elige una especie.", MUTED
        if discovery and not error:
            self.status.value = 'Identificación · Devolución del original sin modificaciones' if m.return_original else 'Identificación · Solo recepción'
        self.status_panel.bgcolor = '#F4DADF' if error else '#D6EEE0' if self.status.color == GREEN else None
        if self.logs_list is not None:
            self.logs_list.controls = [ft.Text(line, size=12, color="#EAF2EC", selectable=True)
                                       for line in m.logs]
        if update and self.control.parent is not None and getattr(self.shell, "screen", "team") == "team":
            self.control.update()
            if self.logs_list is not None and self.logs_list.parent is not None:
                self.logs_list.update()

    def _draw_editor(self):
        self.editor_controls = []
        self.editor_sprite = None
        for i, button in enumerate(self.tab_buttons):
            button.style.bgcolor = INK if ("basic", "stats", "advanced")[i] == self.tab else PAPER
            button.style.color = "white" if ("basic", "stats", "advanced")[i] == self.tab else INK
        draft = self.model.slots[self.selected] or {'level': '100', 'nickname': '', 'shiny': False, 'options': {}}
        if self.tab == "basic":
            if self.basic_content is None:
                self.basic_content = self._basic(draft)
                self.basic_controls = list(self.editor_controls)
                self.basic_sprite = self.editor_sprite
            self.editor_controls = self.basic_controls
            self.editor_sprite = self.basic_sprite
            self.editor.content = self.basic_content
            self._sync_basic(draft)
        else:
            key = (self.selected, self.tab)
            signature = json.dumps([draft, self.model.metadata.get(self.selected, {})], sort_keys=True)
            cached = self.editor_cache.get(key)
            if cached and cached[0] == signature:
                _, self.editor.content, self.editor_controls = cached
            else:
                self.editor.content = self._stats(draft) if self.tab == "stats" else self._advanced(draft)
                self.editor_cache[key] = (signature, self.editor.content, list(self.editor_controls))

    def _choice(self, label, key, values, current, option=False, default=True, callback=None):
        if isinstance(current, bool):
            current = int(current)
        pairs = [(str(n["id"]), n["name"]) for n in values]
        if default:
            pairs.insert(0, ("", "Automático"))
        if current not in (None, "") and str(current) not in {key for key, _ in pairs}:
            pairs.append((str(current), str(current)))
        def selected(e):
            if self.model.busy:
                return
            raw = e.control.value
            value = int(raw) if raw not in (None, "") and str(raw).lstrip("-").isdigit() else raw or None
            if key in ("alpha", "gigantamax") and value is not None:
                value = bool(value)
            if callback:
                callback(value)
            else:
                self.model.edit(self.selected, key, value, option=option)
                if key == 'species':
                    self.selected = min(self.selected, next((i for i, s in enumerate(self.model.slots)
                                                            if not (s or {}).get('species')), 5))
                    self.editor_cache.clear()
                    self._draw_editor()
                    self.refresh()
                    if not value:
                        self.page.run_task(self.model.validate_all)
                self.page.run_task(self._commit, self.selected, key in ("species", "form"))
        control = self.dropdown(pairs, current if current is not None else "", selected,
                                clear_value="" if default else None)
        self.editor_controls.append(control)
        return labeled(label, control, expand=True)

    def _field(self, label, key, value, option=False, width=None, callback=None):
        index = self.selected
        dirty = False
        def changed(e):
            nonlocal index, dirty
            if self.model.busy:
                return
            index = self.selected
            dirty = True
            if callback:
                callback(e.control.value)
            else:
                self.model.edit(index, key, e.control.value, option=option)
        async def blurred(e):
            nonlocal dirty
            if dirty:
                dirty = False
                await self._commit(index)
        control = ft.TextField(value=str(value if value is not None else ""), on_change=changed,
                               on_blur=blurred, text_size=14, height=40, dense=True,
                               size_constraints=ft.BoxConstraints(min_height=40 + theme.field_density),
                               strut_style=ft.StrutStyle(size=14, height=(28 + theme.field_density) / 14,
                                                        force_strut_height=True),
                               text_vertical_align=ft.VerticalAlignment.CENTER,
                               content_padding=ft.Padding(8, 6, 8, 6), bgcolor="#FFFEF8", color=INK,
                               border_color="#B3BABB", focused_border_color=CYAN, border_radius=8)
        self.editor_controls.append(control)
        return labeled(label, control, expand=width is None, width=width)

    @staticmethod
    def _set_choices(control, pairs):
        if getattr(control, "portable_pairs", None) == pairs:
            return
        control.options = [ft.DropdownOption(key=key, text=name) for key, name in pairs]
        control.portable_pairs = pairs

    @staticmethod
    def _set_selection(control, value):
        control.value = control.data = str(value) if value is not None else None
        control.text = next((o.text for o in control.options if o.key == control.value), "")

    def _sync_move_choices(self):
        draft = self.model.slots[self.selected] or {}
        moves = list(draft.get("options", {}).get("moves") or [])
        moves += [None] * (4 - len(moves))
        candidates = set(self.model.candidate_moves(self.selected))
        for i, control in enumerate(self.basic_controls[4:8]):
            current = str(moves[i]) if moves[i] is not None else ""
            pairs = [("", "Automático"), *[(str(n["id"]), n["name"]) for n in self.move_names
                       if n["id"] in candidates or str(n["id"]) == current]]
            if current and current not in {key for key, _ in pairs}:
                pairs.append((current, current))
            self._set_choices(control, pairs)

    def _sync_basic(self, draft):
        species, nickname, level, shiny, *moves = self.basic_controls
        pairs = [(str(n["id"]), n["name"]) for n in self.species_names]
        self._set_choices(species, pairs)
        self._set_selection(species, draft.get("species"))
        nickname.value = str(draft.get("nickname", ""))
        level.value = str(draft.get("level", ""))
        shiny.value = bool(draft.get("shiny"))
        self._sync_move_choices()
        values = list(draft.get("options", {}).get("moves") or [])
        values += [None] * (4 - len(values))
        for control, value in zip(moves, values):
            self._set_selection(control, value if value is not None else "")

    def _basic(self, draft):
        species = self._choice("Especie", "species", self.species_names, draft.get("species"), default=False)
        species.expand = 4
        nickname_limit = 10 if self.model.game in ("frlg", "rse") else 12
        nickname = self._field(f"Apodo · máx. {nickname_limit}", "nickname", draft.get("nickname", ""))
        nickname.expand = 3
        level = self._field("Nivel", "level", draft.get("level", ""), width=65)
        async def shiny_changed(e):
            if self.model.busy:
                return
            self.model.edit(self.selected, "shiny", bool(e.control.value))
            await self._commit(self.selected)
        shiny = ft.Switch(value=bool(draft.get("shiny")), on_change=shiny_changed,
                          active_color=GREEN, width=55, height=40)
        self.editor_controls.append(shiny)
        sprite = Sprite(self.adapter, int(draft.get("species") or 0), bool(draft.get("shiny")), size=80,
                        form=int(draft.get("options", {}).get("form") or 0))
        sprite.frame.bgcolor = "#E4E7E5"
        self.editor_sprite = sprite
        moves = list(draft.get("options", {}).get("moves") or [])
        moves += [None] * (4 - len(moves))
        controls = []
        for i in range(4):
            def change(value, i=i):
                current = list(self.model.slots[self.selected].get("options", {}).get("moves") or [])
                current += [None] * (4 - len(current))
                current[i] = value
                self.model.edit(self.selected, "moves", current, option=True)
                self.page.run_task(self._commit, self.selected)
            controls.append(self._choice(f"Movimiento {i + 1}", "moves", [],
                                          moves[i], option=True, callback=change))
        return ft.Row([ft.Container(sprite.control, width=82), ft.Column([
            ft.Row([species, nickname, level, labeled("Variocolor", shiny, width=65)], spacing=8),
            ft.Row(controls, spacing=8)], spacing=9, expand=True)], spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _stats(self, draft):
        found = self.model.metadata.get(self.selected, {})
        effort = found.get("effort", {"kind": "evs", "max": 252, "total": 510})
        effort_name = {"avs": "AV", "gvs": "Esfuerzo"}.get(effort.get("kind"), "EV")
        rows = []
        for group, title in (("effort", effort_name), ("ivs", "IV")):
            fields = []
            for stat, title_stat in STATS:
                def changed(value, group=group, stat=stat):
                    values = dict(self.model.slots[self.selected].get("options", {}).get(group) or {})
                    values[stat] = value
                    self.model.edit(self.selected, group, values, option=True)
                fields.append(self._field(title_stat, group,
                    draft.get("options", {}).get(group, {}).get(stat, ""), option=True, callback=changed))
            rows.append(ft.Row([ft.Container(text(title, 13), width=35), *fields], spacing=7))
        max_effort = ft.TextButton(f"Maximizar {effort_name}", on_click=lambda e: self._max("effort"))
        max_friend = ft.TextButton("Amistad al máximo", on_click=lambda e: self._max("friendship"))
        self.editor_controls += [max_effort, max_friend]
        rows.append(ft.Row([text(f"{effort_name}: 0–{effort['max']}" +
                                (f" · total {effort['total']}" if effort.get("total") else "") + " · IV: 0–31", 12),
                            ft.Container(expand=True), max_effort, max_friend], spacing=6))
        return ft.Column(rows, spacing=7, scroll=ft.ScrollMode.AUTO)

    def _advanced(self, draft):
        found = self.model.metadata.get(self.selected, {})
        if not found:
            return text("Elige una especie para cargar sus opciones.", 15)
        chosen = draft.get("options", {})
        fields = []
        mapping = (("Naturaleza", "nature", "natures"), ("Habilidad", "ability", "abilities"),
                   ("Objeto", "held_item", "held"), ("Poké Ball", "ball", "balls"),
                   ("Forma", "form", "forms"), ("Tipo teracristal", "tera", "tera"))
        for title, key, values in mapping:
            if found.get(values):
                fields.append(self._choice(title, key, found[values], chosen.get(key), option=True))
        if found.get("gendered"):
            fields.append(self._choice("Sexo", "gender", [{"id": 0, "name": "Macho"}, {"id": 1, "name": "Hembra"}],
                                       chosen.get("gender"), option=True))
        fields.append(self._field("Amistad", "friendship", chosen.get("friendship", ""), option=True))
        for key, available, title in (("alpha", "alpha", "Alfa"), ("gigantamax", "gigantamax", "Gigamax")):
            if found.get(available):
                fields.append(self._choice(title, key, [{"id": 0, "name": "No"}, {"id": 1, "name": "Sí"}],
                                           chosen.get(key), option=True))
        if found.get("dynamax"):
            fields.append(self._field("Nivel Dinamax", "dynamax_level", chosen.get("dynamax_level", ""), option=True))
        if found.get("sweets"):
            fields.append(self._choice("Confite", "sweet", [{"id": i, "name": str(i)} for i in range(found["sweets"])],
                                       chosen.get("sweet"), option=True))
        rows = [ft.Row(fields[i:i + 3], spacing=10) for i in range(0, len(fields), 3)]
        encounters = [{"id": item["key"], "name": str(item.get("name") or item.get("kind") or item["key"])
                       + " · " + str(item.get("place", ""))} for item in found.get("encounters", [])]
        if encounters:
            rows.append(ft.Row([self._choice("Encuentro", "encounter", encounters,
                                             chosen.get("encounter"), option=True)]))
        friend = ft.TextButton("Amistad al máximo", on_click=lambda e: self._max("friendship"))
        self.editor_controls.append(friend)
        rows.append(friend)
        return ft.Column(rows, spacing=8, scroll=ft.ScrollMode.AUTO)

    async def _commit(self, index, load_options=False):
        if self.model.busy:
            return
        # Validation loads metadata and owns revision-scoped errors. Keeping a second
        # error here could display an obsolete failure after the draft becomes legal.
        await self.model.validate(index)
        if load_options and index == self.selected:
            self._draw_editor()
        self.refresh()

    def _select_slot(self, index):
        first_empty = next((i for i, slot in enumerate(self.model.slots) if not (slot or {}).get('species')), 5)
        if self.model.busy or index == self.selected or index > first_empty:
            return
        self.selected = index
        if not (self.model.slots[index] or {}).get('species'):
            self.tab = 'basic'
        self._draw_editor()
        self.refresh()
        if self.tab != "basic" and self.model.slots[index] and index not in self.model.metadata:
            self.page.run_task(self._load_selected, index)

    async def _load_selected(self, index):
        try:
            await self.model.load_options(index)
        except Exception as error:
            self.loading_error = str(error)
            self.refresh()
            return
        self.loading_error = ""
        if index == self.selected and self.tab != "basic":
            self._draw_editor()
            self.refresh()

    def _select_tab(self, tab):
        if not self.model.busy:
            self.tab = tab
            self._draw_editor()
            self.refresh()

    def _maximum(self, group):
        if group == "friendship":
            return 255
        found = self.model.metadata.get(self.selected)
        if not found or not found.get('effort') or not found.get('base'):
            return None
        effort = found["effort"]
        remaining = effort.get("total") or effort["max"] * 6
        value = {}
        for index in sorted(range(6), key=lambda i: -found["base"][i]):
            value[STATS[index][0]] = give = min(effort["max"], remaining)
            remaining -= give
        return value

    def _toggle_max(self, group, enabled):
        if self.model.busy or self.model.slots[self.selected] is None:
            return
        if enabled:
            self._max(group)
            return
        self.model.edit(self.selected, group, None, option=True)
        self.refresh()
        self.page.run_task(self._commit, self.selected)

    def _max(self, group):
        if self.model.busy:
            return
        value = self._maximum(group)
        if value is None:
            return
        self.model.edit(self.selected, group, value, option=True)
        self._draw_editor()
        self.refresh()
        self.page.run_task(self._commit, self.selected)

    def _dialog(self, title, content, actions):
        dialog = ft.AlertDialog(title=text(title, 21, weight=ft.FontWeight.W_700),
                                content=ft.Container(content, width=600), bgcolor=PAPER,
                                actions=actions, modal=True, scrollable=False)
        self.page.show_dialog(dialog)
        return dialog

    def _dismiss(self, e=None):
        self.page.pop_dialog()

    def _confirm_clear(self, index):
        if self.model.busy:
            return
        def clear(e):
            if not self.model.busy:
                self.model.clear(index)
                self.selected = min(self.selected, next((i for i, s in enumerate(self.model.slots)
                                                        if not (s or {}).get('species')), 5))
                self.tab = 'basic'
                self.editor_cache.clear()
                self._draw_editor()
                self.refresh()
                self.page.run_task(self.model.validate_all)
            self._dismiss()
        self._dialog("¿Vaciar el equipo?" if index is None else f"¿Vaciar la caja {index + 1}?",
                     text("Se borrarán los borradores seleccionados. Los entrenadores se conservan."),
                     [ft.TextButton("Cancelar", on_click=self._dismiss), ft.TextButton("Vaciar", on_click=clear)])

    def _trainer_selected(self, e):
        if not self.model.busy and not getattr(self.model, 'active', False):
            self.trainer_model.set_trainer(e.control.value)
            self.page.run_task(self.trainer_model.validate_all)

    def _trainer_info(self, e):
        trainer = self.trainer_model.trainer
        tid, sid = console_trainer.shown(self.model.game, int(trainer["tid"]), int(trainer["sid"]))
        language = {1: "Japonés", 2: "Inglés", 3: "Francés", 4: "Italiano", 5: "Alemán",
                    7: "Español", 8: "Coreano", 9: "Chino simplificado", 10: "Chino tradicional", 11: "Español latinoamericano"}.get(
                        trainer.get("language"), str(trainer.get("language", "")))
        values = (("Nombre", trainer.get("ot", "")), ("Sexo", "Masculino" if trainer.get("gender") == 0 else "Femenino"),
                  ("Idioma", language), ("ID visible", str(tid)), ("ID secreto visible", str(sid)))
        self._dialog("Datos del entrenador", ft.Column([
            ft.Row([labeled(label, text(value, 17), expand=True) for label, value in values[i:i + 3]], spacing=15)
            for i in range(0, len(values), 3)], spacing=18), [ft.TextButton("Listo", on_click=self._dismiss)])

    def _find_trainer(self, e):
        return_original = ft.Switch(label="Devolver Pokémon original", value=True)
        async def begin(e):
            self._dismiss()
            await self.model.start(discover=True, return_original=return_original.value)
            self.refresh()
        self._dialog("Encontrar mi entrenador", ft.Column([text(
            "Se ofrecerá un Pokémon aleatorio legal. Intercambia un Pokémon capturado por ti en este juego. "
            "Guardaremos sus datos sin reemplazar el entrenador base."), return_original,
            text("Para recuperarlo, realiza un segundo intercambio en la consola. "
                 "La consola puede aplicar una evolución por intercambio.", 13)], tight=True, spacing=12),
            [ft.TextButton("Cancelar", on_click=self._dismiss), ft.TextButton("Iniciar búsqueda", on_click=begin)])

    def _discovery_view(self):
        m = self.model
        received = m.completed >= 1
        returned = m.completed >= 2
        heading = ('Original devuelto' if returned else 'Devuelve el Pokémon de cortesía en tu consola'
                   if received and m.return_original and m.busy else 'Pokémon recibido' if received
                   else 'Esperando tu Pokémon')
        if m.phase == 'preparing':
            heading = 'Preparando oferta legal…'
        if m.phase == 'stopping':
            heading = 'Esperando el cierre de la sesión…'
        info = m.received_info
        if info:
            wanted = (info.get('species_id', 0), bool(info.get('shiny')), info.get('form_id', 0))
            if getattr(self, 'received_sprite_key', None) != wanted:
                self.received_sprite_key = wanted
                self.received_sprite = Sprite(self.adapter, wanted[0], wanted[1], size=80, form=wanted[2])
            card = ft.Row([self.received_sprite.control, ft.Column([
                text(info.get('nickname') or info.get('species') or 'Pokémon recibido', 21),
                text(f"{info.get('species', '')} · Nivel {info.get('level', '?')}", 15),
                text(f"Entrenador original: {info.get('ot', '?')}", 14),
            ], spacing=6, expand=True)], spacing=16)
        else:
            card = text(m.received_error or ('Leyendo datos del Pokémon recibido…' if received
                        else 'Ofrece un Pokémon capturado por ti para identificar al entrenador.'), 16)
        def stage(label, done):
            return ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE if done else ft.Icons.SCHEDULE,
                                  color=GREEN if done else MUTED, size=20), text(label, 15)], spacing=6)
        stages = [stage('Recibir e identificar', received)]
        if m.return_original:
            stages.append(stage('Devolver original', returned))
        controls = [text(heading, 21, weight=ft.FontWeight.W_700), ft.Row(stages, spacing=24),
                    ft.Container(card, bgcolor='#E4E7E5', padding=12, border_radius=12)]
        if m.found_trainer:
            controls.append(text(f"Entrenador identificado: {m.found_trainer.get('ot', '')}", 14))
        if not m.busy:
            def close(e):
                m.discovering = False
                self._draw_editor()
                self.refresh()
            controls.append(ft.TextButton('Volver a Equipo', on_click=close))
        self.session.controls = controls

    def _connection(self, e):
        m = self.model
        role = self.dropdown([(key, "Anfitrión" if key == "host" else "Unirse") for key in m.tools],
                             m.role, lambda e: None, search=False)
        versions = next((f.choices for tool in m.tools.values() for f in tool.fields if f.key == "--version"), ())
        version = self.dropdown(versions, m.version, lambda e: None, search=False)
        is_lgpe = m.game == 'lgpe'
        code = ft.TextField(value=m.code, label="Código · 3 dígitos" if is_lgpe else "Código de intercambio",
                            text_size=16, color=INK, max_length=3 if is_lgpe else None,
                            keyboard_type=ft.KeyboardType.NUMBER if is_lgpe else None)
        preview = text('', 13)
        error = ft.Text('', size=12, color=RED, visible=False)
        def update_preview(e=None):
            raw = code.value or ''
            valid = len(raw) == 3 and all(c in '0123456789' for c in raw)
            preview.value = (' → '.join(CODE_PICKER[int(c)].capitalize() for c in raw)
                             if valid else 'Introduce tres dígitos del 0 al 9, en el orden elegido.')
            if e is not None:
                preview.update()
        if is_lgpe:
            code.on_change = update_preview
            update_preview()
        has_code = any(f.kind in ("code", "linkcode") or f.key in ("--code", "--link-code")
                       for tool in m.tools.values() for f in tool.fields)
        content = [labeled("Papel", role)]
        if versions:
            content.append(labeled("Versión", version))
        if has_code:
            content.append(code)
            if is_lgpe:
                content.append(preview)
                for start in (0, 5):
                    content.append(ft.Row([ft.Container(text(f'{i} = {CODE_PICKER[i].capitalize()}', 11), expand=True)
                                           for i in range(start, start + 5)], spacing=3))
                content.append(error)
        content.append(text("Código para Anfitrión · Unirse conserva la búsqueda de pokeLDN." if is_lgpe
                            else "Conexión local · opciones según el juego", 12))
        async def save(e):
            if not m.busy:
                try:
                    m.configure(role.value, version.value or m.version, code.value)
                except ValueError as exc:
                    if not is_lgpe:
                        raise
                    error.value, error.visible = str(exc), True
                    if error in content:
                        error.update()
                    return
                await m.validate_all()
            self._dismiss()
            self.refresh()
        self._dialog("Conexión", ft.Column(content, spacing=8 if is_lgpe else 14),
                     [ft.TextButton("Cancelar", on_click=self._dismiss), ft.TextButton("Guardar", on_click=save)])

    async def _start(self, e):
        await self.model.start()
        self.refresh()

    def _cancel(self, e):
        def stop(e):
            self.model.stop()
            self._dismiss()
            self.refresh()
        self._dialog("¿Cancelar el intercambio?", text(
            "Se solicitará el cierre de pokeLDN. Un intercambio confirmado no se deshace. "
            "Espera a que la sesión termine antes de desconectar la placa. "
            + ("Ya recibimos tu Pokémon: cancelar ahora puede dejar su devolución pendiente; "
               "no hay reanudación automática." if getattr(self.model, 'return_pending', False) else "")),
            [ft.TextButton("Continuar", on_click=self._dismiss), ft.TextButton("Solicitar cancelación", on_click=stop)])

    def _logs(self, e):
        self.logs_list = ft.ListView([ft.Text(line, size=12, color="#EAF2EC", selectable=True)
                                      for line in self.model.logs], height=235, auto_scroll=True, spacing=3)
        def close(e):
            self.logs_list = None
            self._dismiss()
        self.logs_dialog = self._dialog("Logs del intercambio", ft.Container(
            self.logs_list, bgcolor=INK, padding=12, border_radius=10), [ft.TextButton("Volver", on_click=close)])

    def _back(self, e):
        if not self.model.busy:
            self.shell.go("home")
