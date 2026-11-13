"""Compact receive/edit/return views sharing the established Equipo controls."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import flet as ft

from gui.portable_team_view import TeamView, STATS, PAPER, INK, MUTED, RED, GREEN, CYAN, labeled, text
from gui.portable_received import MODES as MODE_LABELS
from gui.views.sprites import Sprite
from gui.views.widgets import on_ui

MODES = tuple(MODE_LABELS.items())


class ReceivedView(TeamView):
    """Presentation only: the controller owns immutable originals and return decisions."""

    def __init__(self, shell, controller, trainer_model=None):
        self.shell, self.page, self.model = shell, shell.page, controller
        self.selected, self.tab = 0, 'basic'
        self.species_names, self.move_names, self.nature_names = [], [], []
        self.loading_error = ''
        self.editor_controls, self.tab_buttons = [], []
        self.basic_content, self.basic_sprite, self.editor_sprite = None, None, None
        self.basic_controls, self.editor_cache = [], {}
        self.logs_dialog, self.logs_list = None, None
        self.disposed, self.loaded = False, False
        self._editor_identity = None
        self._portrait_identity = None
        self.adapter = SimpleNamespace(settings=controller.settings, ui=lambda fn: on_ui(self.page, fn))
        self.trainer_model = trainer_model or controller
        self._init_trainer()
        self.back = self.icon(ft.Icons.ARROW_BACK, 'Volver a juegos', self._back)
        self.mode_menu = ft.PopupMenuButton(
            content=ft.Row([text(dict(MODES)[controller.mode], 17, weight=ft.FontWeight.W_700),
                            ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=INK)], spacing=4),
            tooltip='Modalidad de intercambio',
            items=[ft.PopupMenuItem(content=title, height=36, checked=key == controller.mode,
                                   on_click=lambda e, key=key: self._mode(key)) for key, title in MODES])
        self.connection = ft.TextButton('Anfitrión · Configurar', on_click=self._connection)
        self.start = self.icon(ft.Icons.SWAP_HORIZ, 'Iniciar intercambio', self._start, GREEN)
        self.new_run = self.icon(ft.Icons.TUNE, 'Configurar nuevo intercambio', self._new_run)
        self.cancel = self.icon(ft.Icons.STOP_CIRCLE_OUTLINED, 'Cancelar intercambio', self._cancel, RED)
        self.logs = self.icon(ft.Icons.ARTICLE_OUTLINED, 'Ver logs', self._logs)
        self.original = self.icon(ft.Icons.UNDO, 'Devolver original intacto', self._original, INK)
        self.edited = self.icon(ft.Icons.SEND, 'Devolver Pokémon editado', self._edited, GREEN)
        self.comparison = self.icon(ft.Icons.COMPARE_ARROWS, 'Comparar datos del Pokémon', self._comparison)
        self.details = self.icon(ft.Icons.FACT_CHECK_OUTLINED, 'Detalles de legalidad', self._details)
        self.loader = ft.ProgressRing(width=23, height=23, stroke_width=3, color=CYAN)
        self.phase_label = text('', 15, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        self.status = text('', 12, max_lines=2)
        self.editor = ft.Container(expand=True)
        for key, title in (('basic', 'Básico'), ('stats', 'EV / IV'), ('advanced', 'Avanzado')):
            self.tab_buttons.append(ft.TextButton(title, height=30,
                on_click=lambda e, key=key: self._select_tab(key),
                style=ft.ButtonStyle(padding=ft.Padding(10, 2, 10, 2))))
        self.max_checks = {}
        for group, title in (('effort', 'EVs máx.'), ('friendship', 'Amistad máx.')):
            self.max_checks[group] = ft.Checkbox(label=title, value=False, height=30,
                label_style=ft.TextStyle(size=12, color=INK), visual_density=ft.VisualDensity.COMPACT,
                tooltip='Aplicar máximos al recibido. Desmarcar vuelve a los valores originales.',
                on_change=lambda e, group=group: self._toggle_max(group, e.control.value))
        self.editor_tabs = ft.Row([*self.tab_buttons, ft.Container(expand=True),
                                   *self.max_checks.values()], height=30, spacing=3)
        self.editor_group = ft.Column([self.editor_tabs, self.editor], spacing=7, expand=True)
        self.card = ft.Container(padding=12, border_radius=12, bgcolor='#E4E7E5')
        self.intro = self._configuration()
        self.body = ft.Column([], spacing=10, expand=True)
        self.activity_bar = ft.Container(ft.Row([self.loader, ft.Container(self.phase_label, expand=True),
            self.original, self.edited, self.comparison, self.details, self.logs, self.cancel,
            self.new_run, self.start], height=40, spacing=5), padding=ft.Padding(10, 2, 4, 2), border_radius=10)
        self.control = ft.Column([
            self._trade_header(), self.activity_bar,
            self.body, self.status,
        ], spacing=7, expand=True)
        self.model.listeners.add(self._notified)
        self.refresh(update=False)

    async def _start(self, e):
        if self.model.active:
            return
        self.model.profiles = deepcopy(self.trainer_model.profiles)
        self.model.selected_trainer = self.trainer_model.selected_trainer
        await super()._start(e)

    def _find_trainer(self, e):
        if not self.model.active:
            self.shell.open_trade_mode('team')
            self.shell.team_view._find_trainer(e)

    async def load(self):
        try:
            self.species_names, self.move_names, self.nature_names = await asyncio.gather(
                self.model.names('species'), self.model.names('moves'), self.model.names('natures'))
            if self.model.mode == 'nature':
                self._set_choices(self.nature, [(str(n['id']), n['name']) for n in self.nature_names])
                self._set_selection(self.nature, self.model.params.get('nature', 0))
            if self.model.slots[0]:
                await self.model.load_options(0)
                self._draw_editor()
            self.loaded = True
        except Exception as error:
            self.loading_error = str(error)
        self.refresh()

    def _mode(self, mode):
        if not self.model.active:
            self.shell.open_trade_mode(mode)

    def _back(self, e):
        if not self.model.active:
            self.shell.go('home')

    def _configure(self, key, value):
        if not self.model.active:
            self.model.configure_param(key, value)
            self.refresh()

    def _configuration(self):
        m = self.model
        hints = {
            'evolution': 'Recibe y devuelve el original intacto. La consola aplica la evolución por intercambio si cumple sus requisitos.',
            'level': 'Elige el nivel deseado. Se modifica una copia y solo se devuelve si pasa la validación.',
            'nature': 'Elige la naturaleza. Se conserva al entrenador original y se valida la copia antes de devolverla.',
            'effort': 'Configura los valores de esfuerzo. Se validan los límites del juego y la legalidad del recibido.',
            'modifier': 'Al recibir tu Pokémon se abrirá el editor. Puedes devolver una copia legal o el original intacto.',
            'validator': 'Comprueba la legalidad y devuelve el original sin modificarlo. El informe completo queda disponible en Detalles.',
        }
        icons = {'evolution': ft.Icons.AUTO_AWESOME, 'level': ft.Icons.TRENDING_UP,
                 'nature': ft.Icons.SPA_OUTLINED, 'effort': ft.Icons.BAR_CHART,
                 'modifier': ft.Icons.TUNE, 'validator': ft.Icons.VERIFIED_OUTLINED}
        titles = {'evolution': 'Evoluciona por intercambio', 'level': 'Un nuevo nivel',
                  'nature': 'Elige su naturaleza', 'effort': 'Distribuye su esfuerzo',
                  'modifier': 'Tu Pokémon, a tu medida', 'validator': 'Comprueba su legalidad'}
        controls = [ft.Row([
            ft.Container(ft.Icon(icons[m.mode], size=30, color=GREEN), width=56, height=56,
                         bgcolor='#D6EEE0', border_radius=14, alignment=ft.Alignment.CENTER),
            ft.Column([text(titles[m.mode], 20, weight=ft.FontWeight.W_700),
                       text(hints[m.mode], 13, max_lines=3)], spacing=4, expand=True)], spacing=14)]
        self.param_controls = []
        if m.mode == 'level':
            control = ft.TextField(value=str(m.params.get('level', '100')), width=150, height=44,
                color=INK, text_size=16, keyboard_type=ft.KeyboardType.NUMBER,
                on_change=lambda e: self._configure('level', e.control.value))
            self.param_controls.append(control)
            controls.append(labeled('Nivel · 1 a 100', control, width=150))
        elif m.mode == 'nature':
            self.nature = self.dropdown([], str(m.params.get('nature', 0)),
                lambda e: self._configure('nature', int(e.control.value)) if e.control.value is not None else None, clear_value='0')
            self.param_controls.append(self.nature)
            controls.append(labeled('Naturaleza', self.nature, width=280))
        elif m.mode == 'effort':
            fields = []
            for key, title in STATS:
                def changed(e, key=key):
                    values = dict(m.params.get('effort') or {})
                    values[key] = e.control.value
                    self._configure('effort', values)
                control = ft.TextField(value=str(m.params.get('effort', {}).get(key, 0)), height=42,
                    color=INK, text_size=15, keyboard_type=ft.KeyboardType.NUMBER, on_change=changed)
                self.param_controls.append(control)
                fields.append(labeled(title, control, expand=True))
            controls.append(ft.Row(fields, spacing=8))
            limit = 'AVs · 0–200 por estadística' if m.game == 'lgpe' else 'Esfuerzo · 0–10 por estadística' if m.game == 'pla' else 'EVs · 0–252 por estadística · 510 en total'
            controls.append(text(limit, 13))
        controls.append(ft.Row([ft.Icon(ft.Icons.SWAP_HORIZ, size=18, color=MUTED),
            ft.Text('Recibir  →  Revisar  →  Devolver · Confirma en la misma consola', size=12, color=MUTED)], spacing=6))
        return ft.Container(ft.Column(controls, spacing=14, tight=True), padding=18,
                            border_radius=14, bgcolor='#FFFEF8', border=ft.Border.all(1, '#DEE2DD'))

    def _show_card(self):
        m = self.model
        info = m.received_info
        if not info:
            self.card.bgcolor = '#E4E7E5'
            received = getattr(m, 'original', None) is not None
            self.card.content = ft.Row([
                ft.Icon(ft.Icons.CATCHING_POKEMON, size=56, color=MUTED),
                ft.Column([text('Original recibido' if received else 'Tu Pokémon aparecerá aquí',
                                20, weight=ft.FontWeight.W_700),
                           text('No se pudieron leer sus datos. Consulta el informe.' if received else
                                'Mostraremos su imagen y datos al confirmar la recepción.', 13)],
                          spacing=8, expand=True)], spacing=18)
            return
        wanted = (info.get('species_id', 0), bool(info.get('shiny')), info.get('form_id', 0))
        if wanted != self._portrait_identity:
            self._portrait_identity = wanted
            self.portrait = Sprite(self.adapter, wanted[0], wanted[1], size=80, form=wanted[2])
        legality = getattr(m, 'original_legal', info.get('legal'))
        validator = m.mode == 'validator'
        self.card.bgcolor = ('#D6EEE0' if legality is True else '#F4DADF' if legality is False else '#E4E7E5') if validator else '#E4E7E5'
        lines = [text(info.get('nickname') or info.get('species') or 'Pokémon recibido', 21),
                 text(f"{info.get('species', '')} · Nivel {info.get('level', '?')}", 15),
                 text(f"Entrenador original: {info.get('ot', '?')}", 14)]
        changes = [label for label, before, after in self._comparison_rows() if before != after]
        candidate = self._comparison_candidate()
        lines.append(text('Copia: ' + (', '.join(changes) if changes else 'sin diferencias en los datos mostrados')
                          if candidate else 'Original recibido · Copia aún no calculada', 13, max_lines=2))
        if candidate and candidate.get('editable', {}).get('level') is not None:
            lines.append(text(f"Nivel: {info.get('level', '?')} → {candidate['editable']['level']}", 16,
                              weight=ft.FontWeight.W_700))
        if validator:
            lines.append(text('Legal' if legality is True else 'No legal' if legality is False else 'Validando…', 16,
                              weight=ft.FontWeight.W_700))
        self.card.content = ft.Row([self.portrait.control, ft.Column(lines, spacing=6, expand=True)], spacing=16)

    def refresh(self, update=True):
        m = self.model
        active = m.active
        editing = m.mode == 'modifier' and bool(m.slots[0]) and m.phase == 'editing'
        ready_to_return = active and m.phase in ('editing', 'review') and not m.busy
        self.back.disabled = self.mode_menu.disabled = self.connection.disabled = active
        self.connection.content = 'Anfitrión' if m.role == 'host' else 'Unirse'
        self._refresh_trainer(active)
        for name in ('settings_button', 'close_button'):
            button = getattr(self.shell, name, None)
            if button is not None:
                button.disabled = active
                if update and button.parent is not None:
                    button.update()
        self.new_run.visible = not active and m.phase != 'idle'
        self.new_run.disabled = active
        self.start.visible = not active and m.phase == 'idle'
        self.start.disabled = not getattr(m, 'supported', True) or bool(self.loading_error)
        self.start.opacity = 0.4 if self.start.disabled else 1
        self.loader.visible = active and not ready_to_return
        self.cancel.visible = active
        self.cancel.disabled = m.phase in ('stopping', 'cancelled')
        self.logs.visible = bool(m.logs) or active
        self.original.visible = ready_to_return
        self.edited.visible = editing
        self.edited.disabled = not m.candidate_legal or m.states[0] in ('pending', 'validating')
        self.edited.opacity = 0.4 if self.edited.disabled else 1
        self.details.visible = bool(m.report)
        self.comparison.visible = bool(m.received_info)
        for control in self.param_controls:
            control.disabled = active
        self.phase_label.value = {
            'idle': 'Listo para iniciar', 'preparing': 'Preparando oferta · Aún no busca consola',
            'receiving': 'Proceso iniciado · Esperando tu Pokémon', 'running': 'Proceso iniciado · Esperando tu Pokémon',
            'editing': 'Edita el recibido · Original conservado', 'review': 'Revisa el resultado antes de devolver',
            'returning': 'Confirma la devolución en tu consola', 'done': 'Devolución confirmada',
            'stopping': 'Esperando cierre de sesión…', 'stopped': 'Sesión detenida', 'error': 'La sesión requiere atención',
        }.get(m.phase, m.phase)
        if m.error and not active:
            self.phase_label.value = 'No se pudo iniciar' if m.phase == 'idle' else 'La sesión requiere atención'
        self.activity_bar.bgcolor = '#F4DADF' if m.error else '#D7F1EE' if active else '#E4E7E5'
        self.phase_label.color = RED if m.error else INK
        if editing:
            identity = getattr(m, 'run_stamp', '')
            if self._editor_identity != identity:
                self._editor_identity = identity
                self.basic_content = None
                self.editor_cache.clear()
                self._draw_editor()
            if self.basic_content is not None and self.tab == 'basic':
                self._sync_move_choices()
                draft = m.slots[0]
                wanted = (int(draft.get('species') or 0), bool(draft.get('shiny')),
                          int(draft.get('options', {}).get('form') or 0))
                if self.editor_sprite is not None and getattr(self.editor_sprite, 'portable_wanted', None) != wanted:
                    self.editor_sprite.portable_wanted = wanted
                    self.editor_sprite.show(*wanted[:2], form=wanted[2], update=False)
            for control in self.editor_controls:
                control.disabled = m.busy
            for group, checkbox in self.max_checks.items():
                maximum = self._maximum(group)
                chosen = m.slots[0].get('options', {}).get(group)
                checkbox.visible = self.tab == 'basic'
                checkbox.disabled = m.busy or maximum is None
                checkbox.value = (chosen == maximum if group == 'effort' else str(chosen) == str(maximum)) and maximum is not None
            kind = m.metadata.get(0, {}).get('effort', {}).get('kind')
            self.max_checks['effort'].label = {'avs': 'AVs máx.', 'gvs': 'Esfuerzo máx.'}.get(kind, 'EVs máx.')
            self.body.controls = [self.editor_group]
        elif active or m.received_info or getattr(m, 'original', None) is not None:
            self._show_card()
            self.body.controls = [self.card]
            if m.return_pending and not active:
                self.body.controls.append(text('Devolución pendiente. Conserva el original; no se reenvía automáticamente.', 16))
        else:
            self.body.controls = [self.intro]
        error = m.error or self.loading_error or (m.errors[0] if editing else '')
        self.status.value = error.splitlines()[0] if error else getattr(m, 'support_reason', '') if not getattr(m, 'supported', True) else (
            'Pokémon válido · Puedes devolver la copia' if editing and m.candidate_legal else
            'Los cambios no modifican el archivo original.' if editing else getattr(m, 'recovery_notice', '') or 'Intercambio local · Original conservado sin modificaciones')
        self.status.color = RED if error else GREEN if editing and m.candidate_legal else MUTED
        if self.logs_list is not None:
            self.logs_list.controls = [ft.Text(line, size=12, color='#EAF2EC', selectable=True) for line in m.logs]
        if update and self.control.parent is not None and getattr(self.shell, 'screen', 'team') == 'team':
            self.control.update()
            if self.logs_list is not None and self.logs_list.parent is not None:
                self.logs_list.update()

    def _new_run(self, e):
        if self.model.active:
            return
        self.model.reset()
        self._editor_identity = None
        self.basic_content = None
        self.editor_cache.clear()
        self.refresh()

    async def _original(self, e):
        if not self.model.active or self.model.busy or self.model.phase not in ('editing', 'review'):
            return
        await self.model.return_original_now()
        self.refresh()

    async def _edited(self, e):
        m = self.model
        if not m.active or m.busy or m.phase != 'editing' or not m.candidate_legal or m.states[0] in ('pending', 'validating'):
            return
        await m.return_edited_now()
        self.refresh()

    def _comparison_candidate(self):
        m = self.model
        revision = getattr(m, '_revision', [-1])[0]
        if (m.states[0] in ('pending', 'validating') or revision < 0
                or getattr(m, 'candidate_revision', -2) != revision):
            return None
        return m.results[0]

    def _comparison_rows(self):
        original = self.model.received_info or {}
        candidate = self._comparison_candidate()
        labels = dict(species='Especie', form='Forma', nickname='Apodo', level='Nivel', shiny='Variocolor',
                      nature='Naturaleza', ability='Habilidad', gender='Género Pokémon', held_item='Objeto',
                      ball='Poké Ball', friendship='Amistad', moves='Movimientos', ivs='IVs', effort='EV / AV / Esfuerzo',
                      trainer_gender='Género entrenador', language='Idioma (ID)', met_date='Fecha de encuentro',
                      egg_location='Lugar de huevo (ID)', egg_date='Fecha de huevo',
                      is_egg='Es huevo', was_egg='Procede de huevo',
                      ot='Entrenador', tid='TID (16 bits)', sid='SID (16 bits)', pid='PID',
                      encryption_constant='EC', version='Juego de origen', met_location='Lugar de encuentro',
                      met_level='Nivel de encuentro', tracker='HOME tracker', alpha='Alfa',
                      gigantamax='Gigamax', dynamax_level='Nivel Dinamax', tera='Teratipo')
        rows = []
        for section in ('identity', 'editable'):
            before, after = original.get(section, {}), (candidate or {}).get(section, {})
            for key in dict.fromkeys([*before, *after]):
                rows.append((labels.get(key, key), self._data_value(key, before.get(key)),
                             self._data_value(key, after.get(key)) if candidate else '—'))
        return rows

    def _data_value(self, key, value):
        if value is None:
            return 'No disponible'
        if isinstance(value, bool):
            return 'Sí' if value else 'No'
        if isinstance(value, dict):
            return ' · '.join(f'{title} {value.get(stat, "—")}' for stat, title in STATS)
        if isinstance(value, list):
            return ' / '.join(self._data_value('move', item) for item in value)
        catalog = {'species': self.species_names, 'move': self.move_names, 'nature': self.nature_names}.get(key, [])
        name = next((entry['name'] for entry in catalog if entry['id'] == value), None)
        return f'{name} ({value})' if name else str(value) if value != '' else 'Sin apodo'

    def _comparison(self, e):
        candidate = self._comparison_candidate()
        rows = self._comparison_rows()
        controls = [text('Datos leídos de los archivos · No verifica cambios posteriores en la consola.', 12),
                    text('Copia calculada' if candidate else 'Sin copia actual · Mostrando solo el original', 14),
                    ft.Row([text('Campo', 13, width=145), text('Original', 13, expand=True),
                            text('Copia', 13, expand=True)])]
        for label, before, after in rows:
            changed = candidate is not None and before != after
            controls.append(ft.Container(ft.Row([text(label, 12, width=145),
                text(before, 12, expand=True, selectable=True), text(after, 12, expand=True, selectable=True)],
                vertical_alignment=ft.CrossAxisAlignment.START), padding=5,
                bgcolor='#FFF0C2' if changed else None))
        if not rows:
            controls.append(text('No se pudieron leer los datos detallados del original.', 14))
        self._dialog('Original y copia · Cambios resaltados',
                     ft.Container(ft.ListView(controls, spacing=5, height=240), width=660, bgcolor=PAPER),
                     [ft.TextButton('Cerrar', on_click=self._dismiss)])

    def _details(self, e):
        self._dialog('Informe de legalidad', ft.Container(ft.ListView([
            text(self.model.report or 'Sin informe disponible.', 14, selectable=True)
        ], height=230), bgcolor=PAPER), [ft.TextButton('Cerrar', on_click=self._dismiss)])

    def _connection(self, e):
        if not self.model.active:
            super()._connection(e)
