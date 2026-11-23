"""Portable drag scrolling and an explicit touch entry to searchable options."""
import asyncio
import inspect
from types import SimpleNamespace

import flet as ft


def drag_scroll(content, scroll, *, horizontal=False):
    """Scroll on drag while Flutter's gesture arena keeps taps mutually exclusive."""
    origin = None

    def position(e):
        return e.global_position.x if horizontal else e.global_position.y

    def down(e):
        nonlocal origin
        ft.context.disable_auto_update()
        origin = position(e)

    async def started(e):
        nonlocal origin
        ft.context.disable_auto_update()
        previous, origin = origin, None
        if previous is not None:
            await scroll(previous - position(e))

    async def dragged(e):
        ft.context.disable_auto_update()
        if e.primary_delta:
            await scroll(-e.primary_delta)

    axis = "horizontal" if horizontal else "vertical"
    return ft.GestureDetector(
        content=content, expand=content.expand, drag_interval=0,
        **{f"on_{axis}_drag_down": down, f"on_{axis}_drag_start": started,
           f"on_{axis}_drag_update": dragged},
    )


class TouchSelector(ft.Container):
    """A committed value whose entire button opens the dedicated search dialog."""

    def __init__(self, page, options, value, selected, clear, can_open):
        self.host_page = page
        self.options, self.value, self.text = options, value, ""
        self.on_select = selected
        self.can_open = can_open
        self.picker = None
        self.portable_searching = False
        self.caption = ft.Text(size=14, color="#243139", weight=ft.FontWeight.W_400, max_lines=1,
                               overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.open_button = ft.TextButton(
            ft.Row([self.caption, ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=20, color="#243139")],
                   spacing=4), expand=True, height=40, on_click=self.open_picker,
            style=ft.ButtonStyle(padding=ft.Padding(8, 0, 4, 0),
                shape=ft.RoundedRectangleBorder(radius=8),
                side={ft.ControlState.FOCUSED: ft.BorderSide(2, "#00C8D8")}))
        self.selected_suffix = ft.IconButton(ft.Icons.CLOSE, tooltip="Limpiar selección",
            icon_size=15, width=28, height=28, padding=0, icon_color="#5C6870",
            visual_density=ft.VisualDensity.COMPACT, on_click=clear)
        super().__init__(
            content=ft.Row([self.open_button, self.selected_suffix], spacing=0),
            width=280, height=40, bgcolor="#FFFEF8", border_radius=8,
            border=ft.Border.all(1, "#B3BABB"), data=value,
        )
        self.before_update()

    def before_update(self):
        self.opacity = 0.45 if self.disabled else 1
        self.text = next((o.text or o.key for o in self.options if o.key == self.value), "")
        self.caption.value = self.text or "Seleccionar…"
        self.open_button.tooltip = self.text or "Seleccionar opción"

    def open_picker(self, e=None):
        if self.disabled or not self.can_open() or (self.picker and not self.picker.closed):
            return
        self.picker = TouchOptions(self.host_page, self, self.on_select)
        self.picker.open()


class TouchOptions:
    """A temporary query; only an enabled option commits to the original selector."""

    def __init__(self, page, control, selected):
        self.page, self.control, self.selected = page, control, selected
        self.closed = False
        self.previous_keys = None
        self.keyboard_handler = self.key
        self.navigation = asyncio.Lock()
        self.query = ft.TextField(label="Buscar opción", height=48, text_size=16,
                                  on_change=self.filter, autofocus=False,
                                  color="#23342B", bgcolor="#FFFEF8")
        self.rows = ft.ListView(spacing=2, expand=True, scroll=ft.ScrollMode.AUTO,
                                build_controls_on_demand=False)
        self.dialog = ft.AlertDialog(
            modal=True, bgcolor="#FFFEF8", content_padding=16,
            content=ft.Container(ft.Column([
                self.query, drag_scroll(self.rows, self.scroll),
            ], spacing=8, expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH), width=400, height=248),
            actions=[ft.TextButton("Cancelar", on_click=self.cancel)],
            on_dismiss=self.dismissed,
        )
        self.filter(update=False)

    def open(self):
        if not self.control.disabled:
            self.previous_keys = getattr(self.page, "on_keyboard_event", None)
            self.page.on_keyboard_event = self.keyboard_handler
            self.page.show_dialog(self.dialog)

    async def key(self, e):
        if e.key == "Escape":
            await self.cancel()
        elif e.key == "F11" and self.previous_keys:
            result = self.previous_keys(e)
            if inspect.isawaitable(result):
                await result

    def restore_keys(self):
        if getattr(self.page, "on_keyboard_event", None) is self.keyboard_handler:
            self.page.on_keyboard_event = self.previous_keys

    def filter(self, e=None, *, update=True):
        if self.closed:
            return
        query = (self.query.value or "").strip().casefold()
        self.rows.controls = []
        for option in self.control.options:
            label = option.text or option.key or ""
            if query not in label.casefold():
                continue

            async def choose(e, key=option.key):
                await self.choose(key)

            self.rows.controls.append(drag_scroll(ft.TextButton(
                label, on_click=choose, disabled=option.disabled, height=40,
                style=ft.ButtonStyle(color="#23342B", alignment=ft.Alignment.CENTER_LEFT),
            ), self.scroll))
        if not self.rows.controls:
            self.rows.controls.append(ft.Text("Sin coincidencias", color="#23342B"))
        if update:
            self.rows.update()

    async def scroll(self, delta):
        async with self.navigation:
            if not self.closed:
                await self.rows.scroll_to(delta=delta, duration=0)

    async def choose(self, key):
        async with self.navigation:
            if self.closed or self.control.disabled:
                return
            option = next((o for o in self.control.options if o.key == key), None)
            if option is None or option.disabled:
                return
            self.closed = True
            self.restore_keys()
            self.page.pop_dialog()
            self.control.value = key
            self.control.text = option.text or key
            self.selected(SimpleNamespace(control=self.control))
            self.control.update()

    async def cancel(self, e=None):
        async with self.navigation:
            if not self.closed:
                self.closed = True
                self.restore_keys()
                self.page.pop_dialog()

    def dismissed(self, e):
        self.closed = True
        self.restore_keys()
