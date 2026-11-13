"""Opt-in resource monitor; no sampling when hidden or disconnected."""
import asyncio
import time

import flet as ft
import psutil


def cpu_temperature():
    """Use CPU sensors only; unsupported platforms return no reading."""
    read = getattr(psutil, 'sensors_temperatures', None)
    if read is None:
        return None
    try:
        sensors = read()
    except (OSError, psutil.Error):
        return None
    values = [sensor.current for name, entries in sensors.items()
              if name.lower() in ('cpu_thermal', 'cpu-thermal', 'coretemp', 'k10temp')
              for sensor in entries if sensor.current is not None]
    return max(values) if values else None


def temperature_label(value):
    if value is None:
        return 'Temp N/D', '#BBC5C7'
    # Diagnostic display bands, not hardware throttling thresholds.
    if value < 60:
        return f'{value:.0f} °C · Fresco', '#86DBB0'
    if value < 75:
        return f'{value:.0f} °C · Templado', '#FFE19B'
    return f'{value:.0f} °C · Caliente', '#FF9B9B'


class ResourceSampler:
    def __init__(self):
        self.process = psutil.Process()
        self.previous = {}
        self.when = None
        self.system_previous = None

    def sample(self):
        now = time.monotonic()
        current, ram = {}, 0
        try:
            processes = [self.process, *self.process.children(recursive=True)]
        except psutil.Error:
            processes = [self.process]
        for process in processes:
            try:
                with process.oneshot():
                    key = (process.pid, process.create_time())
                    usage = process.cpu_times()
                    current[key] = usage.user + usage.system
                    ram += process.memory_info().rss
            except psutil.Error:
                continue
        elapsed = now - self.when if self.when is not None else 0
        used = sum(max(0, value - self.previous[key]) for key, value in current.items() if key in self.previous)
        app_cpu = 100 * used / elapsed / (psutil.cpu_count() or 1) if elapsed > 0 else None
        memory = psutil.virtual_memory()
        times = psutil.cpu_times()
        total = sum(times) - getattr(times, 'guest', 0) - getattr(times, 'guest_nice', 0)
        idle = times.idle + getattr(times, 'iowait', 0)
        system_cpu = None
        if self.system_previous is not None:
            delta = total - self.system_previous[0]
            if delta > 0:
                system_cpu = max(0, min(100, 100 * (1 - (idle - self.system_previous[1]) / delta)))
        self.system_previous = total, idle
        self.previous, self.when = current, now
        return dict(ram=ram, memory_used=memory.total - memory.available, memory_total=memory.total,
                    memory_percent=memory.percent, cpu=system_cpu,
                    app_cpu=app_cpu, cores=psutil.cpu_count() or 1, temperature=cpu_temperature())


class ResourceOverlay:
    def __init__(self, page):
        self.page = page
        self.enabled = False
        self.connected = True
        self.task = None
        self.memory = ft.Text('Midiendo…', size=11, color='white')
        self.cpu = ft.Text('', size=11, color='white')
        self.temperature = ft.Text('', size=11)
        self.control = ft.TransparentPointer(ft.Container(
            ft.Column([self.memory, self.cpu, self.temperature], spacing=0),
            bgcolor='#D9233139', padding=6, border_radius=6),
            right=12, bottom=8, visible=False)

    def toggle(self):
        self.enabled = not self.enabled
        self.control.visible = self.enabled
        self.sync()
        self.control.update()

    def sync(self):
        if self.task is not None:
            self.task.cancel()
            self.task = None
        if self.enabled and self.connected:
            self.task = self.page.run_task(self.run)

    async def run(self):
        sampler = ResourceSampler()
        while self.enabled and self.connected:
            try:
                data = await asyncio.to_thread(sampler.sample)
                if not self.enabled or not self.connected:
                    return
                gib, mib = 1024 ** 3, 1024 ** 2
                self.memory.value = (f"RAM {data['memory_used']/gib:.1f}/{data['memory_total']/gib:.1f} GiB "
                                     f"· {data['memory_percent']:.0f}% · App {data['ram']/mib:.0f} MiB "
                                     f"({100*data['ram']/data['memory_total']:.1f}%)")
                pct = lambda value: '…' if value is None else f'{value:.1f}%'
                self.cpu.value = f"CPU {pct(data['cpu'])} · App {pct(data['app_cpu'])} · {data['cores']} CPU lógicas"
                self.temperature.value, self.temperature.color = temperature_label(data['temperature'])
            except (OSError, psutil.Error):
                self.memory.value = 'Recursos no disponibles'
                self.cpu.value = self.temperature.value = ''
            self.control.update()
            await asyncio.sleep(1)
