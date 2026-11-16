"""Independent progress window for a source-based portable update.

The worker belongs to this process, not to the main application being replaced.
Closing the window cannot interrupt an installation or its rollback.
"""
import argparse
import asyncio
from collections import deque
from dataclasses import fields
import json
import os
from pathlib import Path
import queue
import sys

import flet as ft

from gui import theme
from gui.portable import CYAN, INK, PAPER, RED


def read_log_tail(path: Path, offset: int, limit: int = 16 * 1024):
    """Read only bounded new output, skipping older bursts and handling truncation."""
    try:
        with path.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            if offset > size:
                offset = 0
            start = max(offset, size - limit)
            stream.seek(start)
            block = stream.read(limit)
    except FileNotFoundError:
        return offset, []  # The engine has not reached this phase yet.
    lines = block.decode("utf-8", errors="replace").splitlines()
    if start > offset:
        lines.insert(0, "… salida anterior disponible en el archivo de log …")
    return start + len(block), lines


class UpdateWindow:
    def __init__(self, page, job: Path):
        self.page = page
        self.job = job
        self.finished = False
        self.connected = True
        self.events = queue.Queue(maxsize=200)
        self.lines = deque(maxlen=80)
        self.log_offsets = {"update.log": 0, "app.log": 0}
        self.stage = ft.Text("Preparando actualización…", size=23, color=INK,
                             weight=ft.FontWeight.W_600, max_lines=2)
        self.detail = ft.Text("Esperando el cierre de pokeLDN.", size=15, color=INK,
                              max_lines=3)
        self.spinner = ft.ProgressRing(width=26, height=26, stroke_width=3, color=CYAN)
        self.details = ft.ListView(expand=True, spacing=3, auto_scroll=True, visible=False)
        self.toggle = ft.TextButton("Mostrar detalles", on_click=self.toggle_details)
        self.close_button = ft.TextButton("Cerrar", disabled=True, on_click=self.close)
        self.log_path = ft.Text(f"Logs: update.log · app.log · helper.log\nCarpeta: {job}",
                                size=12, color=INK, selectable=True, max_lines=3)
        self.spacer = ft.Container(expand=True)
        self.control = ft.Container(bgcolor=RED, padding=16, expand=True, content=ft.Column([
            ft.Text("POKÉDEX · ACTUALIZACIÓN", size=21, color="white", weight=ft.FontWeight.W_700),
            ft.Container(bgcolor=PAPER, border_radius=16, padding=20, expand=True,
                         content=ft.Column([
                             ft.Row([self.spinner, ft.Container(self.stage, expand=True)], spacing=14),
                             self.detail,
                             ft.Text("No apagues el dispositivo. La app volverá a abrirse al terminar.",
                                     size=14, color=INK),
                             self.details,
                             self.spacer,
                             self.log_path,
                             ft.Row([self.toggle, ft.Container(expand=True), self.close_button]),
                         ], spacing=12, expand=True)),
        ], spacing=14, expand=True))

    def progress(self, stage: str, detail: str):
        """Called by the worker thread; all Flet changes happen on the page loop."""
        print(f"[{stage}] {detail}", flush=True)
        try:
            self.events.put_nowait((stage, detail))
        except queue.Full:
            # Full history lives in the log; keep the latest visible status bounded.
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass  # The page loop drained it between put and get.
            self.events.put_nowait((stage, detail))

    def flush(self):
        changed = False
        while True:
            try:
                stage, detail = self.events.get_nowait()
            except queue.Empty:
                break
            self.stage.value = stage
            self.detail.value = detail[-1500:]
            self.lines.append(f"{stage}: {detail}"[-1500:])
            changed = True
        if changed:
            self.render_details()

    def render_details(self):
        self.details.controls = [ft.Text(line, size=12, color=INK, selectable=True)
                                 for line in self.lines]
        self.update()

    async def refresh_logs(self):
        changed = False
        for filename, offset in self.log_offsets.items():
            try:
                position, lines = await asyncio.to_thread(read_log_tail, self.job / filename, offset)
            except OSError as error:
                print(f"No se pudo leer {filename}: {error}", flush=True)
                continue
            self.log_offsets[filename] = position
            for line in lines:
                self.lines.append(f"[{filename}] {line}"[-1500:])
            changed |= bool(lines)
        if changed:
            self.render_details()

    async def disconnect(self, event):
        self.connected = False

    async def reconnect(self, event):
        self.connected = True
        self.update()

    def update(self):
        if not self.connected:
            return
        try:
            self.page.update()
        except RuntimeError as error:
            # Losing the viewer must not cancel the worker and strand activation.
            self.connected = False
            print(f"La ventana se desconectó: {error}", flush=True)

    def toggle_details(self, event):
        self.details.visible = not self.details.visible
        self.spacer.visible = not self.details.visible
        self.toggle.content = "Ocultar detalles" if self.details.visible else "Mostrar detalles"
        self.update()

    async def close(self, event):
        if self.finished:
            await self.page.window.destroy()

    async def window_event(self, event):
        if event.type == ft.WindowEventType.CLOSE:
            await self.close(event)

    async def run(self):
        from pokeldn.app import portable_update

        # Announce readiness only after Flet accepted the visible controls.
        self.page.add(self.control)
        (self.job / "helper.ready").write_text(str(os.getpid()), encoding="utf-8")
        worker = asyncio.create_task(asyncio.to_thread(portable_update.apply, self.job, self.progress))
        try:
            while not worker.done():
                self.flush()
                await self.refresh_logs()
                await asyncio.sleep(0.25)
            ok = await worker
        except Exception as error:
            # Keep unexpected failures visible too; do not claim recovery succeeded.
            print(f"Error del actualizador: {type(error).__name__}: {error}", flush=True)
            ok = False
            self.progress("No se pudo completar la actualización", str(error))
        self.flush()
        await self.refresh_logs()
        self.finished = True
        self.spinner.visible = False
        self.close_button.disabled = False
        if ok:
            self.stage.value = "Actualización completada"
            self.detail.value = "pokeLDN se abrió con la nueva versión."
            self.update()
            if self.connected:
                await self.page.window.destroy()
            return
        self.stage.value = "No se pudo completar la actualización"
        outcome = self.job / "outcome.json"
        if outcome.is_file():
            try:
                result = json.loads(outcome.read_text(encoding="utf-8"))
                self.detail.value = str(result.get("error") or self.detail.value)[-1500:]
            except (OSError, ValueError, TypeError) as error:
                print(f"No se pudo leer el resultado: {error}", flush=True)
        self.details.visible = True
        self.spacer.visible = False
        self.toggle.content = "Ocultar detalles"
        self.update()


def configure(page):
    page.title = "pokeLDN · Actualización"
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


def run(job: Path):
    # The main application keeps its own server; the helper needs an ephemeral port.
    for key in ("FLET_SERVER_PORT", "FLET_FORCE_WEB_SERVER", "POKELDN_GUI_WEB",
                "POKELDN_PORTABLE_DEMO", "POKELDN_RADIO"):
        os.environ.pop(key, None)
    os.environ["FLET_SERVER_IP"] = "127.0.0.1"

    async def main(page):
        configure(page)
        view = UpdateWindow(page, job)
        page.window.on_event = view.window_event
        page.on_disconnect = view.disconnect
        page.on_connect = view.reconnect
        await view.run()

    ft.run(main, port=0, assets_dir=str(Path(__file__).parent / "assets"))


def cli():
    parser = argparse.ArgumentParser(description="Ventana auxiliar de actualización portátil")
    parser.add_argument("--job", required=True, type=Path)
    args = parser.parse_args()
    if not args.job.is_absolute() or not (args.job / "request.json").is_file():
        parser.error("--job debe identificar un trabajo absoluto creado por pokeLDN")
    run(args.job)


if __name__ == "__main__":
    cli()
