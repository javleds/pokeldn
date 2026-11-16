"""Portable onboarding state. Hardware operations reuse the desktop services."""
import asyncio
from collections import deque
import os
from pathlib import Path
import re
import tempfile
from time import strftime

from gui import board
from gui.app import keys_problem
from pokeldn import pokemon
from pokeldn.app import runner, settings
from pokeldn.app.paths import DATA, ROOT
from pokeldn.app.redact import Redactor

PERCENT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?%")
MAX_KEYS = 1024 * 1024
SUPPORTED_RADIO_CHIPS = ("ESP32-C6", "ESP32-S3")


def validate_keys(path: str) -> str:
    try:
        if not path or not Path(path).is_file():
            return "Selecciona el archivo prod.keys."
        if Path(path).stat().st_size > MAX_KEYS:
            return "El archivo supera el límite de 1 MB."
        return keys_problem(path)
    except (OSError, ValueError, UnicodeError):
        return "No se pudo leer un archivo de claves válido."


def choose_port(ports, preferred: str):
    matches = [p for p in ports if p.device == preferred]
    if matches:
        return matches[0]
    return ports[0] if len(ports) == 1 else None


class Setup:
    def __init__(self, demo: bool = False):
        self.demo = demo
        self.settings = settings.Settings() if demo else settings.load()
        self.engine_ready = False
        self.engine_error = ""
        self.keys_error = "Selecciona el archivo prod.keys."
        self.radio_state = "missing"
        self.radio_detail = "Conecta el módulo con un cable USB de datos."
        self.device = ""
        self.chip = ""
        self.serial_number = None
        self.busy = False
        self.session_busy = False
        self.active_team = None
        self.checking = False
        self.phase = "idle"
        self.error = ""
        self.progress = None
        self.logs = deque(maxlen=500)
        self.listeners = set()
        self.redact = Redactor()
        self.initialized = False
        self.process = None

    @property
    def ready(self):
        return self.engine_ready and not self.keys_error and self.radio_state == "ready"

    def notify(self):
        for listener in tuple(self.listeners):
            try:
                listener()
            except RuntimeError:
                # A closed Flet session must not interrupt a flash in progress.
                self.listeners.discard(listener)

    def log(self, text: str):
        for line in text.splitlines():
            self.logs.append(f"[{strftime('%H:%M:%S')}] {self.redact(line)[:1000]}")
        self.notify()

    def _save(self, **values):
        if self.demo:
            return
        # Reload before writing so another settings editor's unrelated fields survive.
        current = settings.load()
        for name, value in values.items():
            setattr(current, name, value)
        current.save()
        self.settings = current

    async def check(self):
        if self.busy or self.checking or self.session_busy:
            return
        self.checking = True
        self.notify()
        try:
            if self.demo:
                self.engine_ready = True
                self.radio_state, self.chip = "flash", "ESP32-C6"
                self.radio_detail = "Demo: módulo simulado; firmware pendiente."
                return
            self.keys_error = await asyncio.to_thread(validate_keys, self.settings.keys)
            try:
                names = await asyncio.to_thread(pokemon.SERVICE.names, "sv", "species")
                self.engine_ready = bool(names)
                self.engine_error = "" if names else "El motor no devolvió datos."
            except (pokemon.BuilderError, OSError, ValueError) as error:
                self.engine_ready = False
                self.engine_error = self.redact(str(error))
            try:
                await self.check_radio()
            except Exception as error:
                self.radio_state = "error"
                self.radio_detail = "No se pudo comprobar el módulo. Revisa los detalles."
                self.log(f"Comprobación fallida: {type(error).__name__}: {error}")
        finally:
            self.checking = False
            self.initialized = True
            self.notify()

    async def check_radio(self):
        self.device, self.chip = "", ""
        present = await asyncio.to_thread(board.ports)
        port = choose_port(present, self.settings.radio_port)
        if port is None:
            self.radio_state = "ambiguous" if present else "missing"
            self.radio_detail = ("Hay varias placas. Deja conectado solo el módulo que quieres configurar."
                                 if present else "Conecta el módulo con un cable USB de datos.")
            return
        self.device = port.device
        self.serial_number = getattr(port, "serial_number", None)
        self.radio_state = "checking"
        self.notify()
        try:
            ident = await asyncio.to_thread(board.identify, self.device, False)
            self.chip = ident.chip
            self.radio_state = "ready" if ident.current else "flash"
            self.radio_detail = (f"Firmware {ident.firmware_version or 'compatible'} · USB conectado"
                                 if ident.current else "El firmware necesita una actualización compatible.")
        except Exception as error:
            # Device drivers and esptool have different exception types. Never infer
            # readiness from a successful USB enumeration alone.
            self.log(f"No respondió la radio: {type(error).__name__}: {error}")
            try:
                self.chip = await asyncio.to_thread(board.detect_chip, self.device)
                self.radio_state = "flash"
                self.radio_detail = "Firmware de radio requerido."
            except Exception as error:
                self.radio_state = "error"
                self.radio_detail = "No se pudo abrir la placa. Revisa el cable y los permisos USB."
                self.log(f"No se pudo identificar el chip: {type(error).__name__}: {error}")
                return
        if self.chip not in SUPPORTED_RADIO_CHIPS:
            self.radio_state = "unsupported"
            self.radio_detail = "Usa un ESP32-C6 o ESP32-S3 para este dispositivo."
        elif not port.native:
            self.radio_state = "error"
            self.radio_detail = f"Usa el puerto USB nativo del {self.chip}."
        else:
            self._save(radio_port=self.device)

    async def import_keys(self, data: bytes):
        if self.busy or self.checking or self.session_busy:
            return
        if self.demo:
            self.keys_error = ""
            self.notify()
            return
        if not data or len(data) > MAX_KEYS:
            self.keys_error = "Selecciona un archivo de claves de hasta 1 MB."
            self.notify()
            return
        folder = DATA / "portable"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "prod.keys"
        fd, name = tempfile.mkstemp(prefix=".keys-", dir=folder)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            problem = await asyncio.to_thread(validate_keys, name)
            if problem:
                self.keys_error = problem
                return
            os.replace(name, target)
            self._save(keys=str(target))
            self.keys_error = ""
        except OSError:
            self.keys_error = "No se pudieron guardar las claves en este dispositivo."
        finally:
            Path(name).unlink(missing_ok=True)
            self.notify()

    async def install(self, *, reinstall: bool = False):
        allowed = self.radio_state == "flash" or (reinstall and self.radio_state == "ready")
        if self.busy or self.checking or self.session_busy or not allowed or self.chip not in SUPPORTED_RADIO_CHIPS:
            return
        self.busy = True
        self.error = ""
        self.progress = None
        self.logs.clear()
        self.phase = "download"
        self.notify()
        try:
            if self.demo:
                for message, progress in [("Demo: puerto USB detectado", None),
                                          ("Demo: ESP32-C6 identificado", None),
                                          ("Demo: firmware verificado", None),
                                          ("Demo: escribiendo… 25%", .25),
                                          ("Demo: escribiendo… 64%", .64),
                                          ("Demo: verificando…", 1.0)]:
                    self.phase = "write"
                    self.progress = progress
                    self.log(message)
                    await asyncio.sleep(2)
                self.radio_state, self.radio_detail = "ready", "Demo: módulo preparado."
            else:
                await self._install_real()
            self.phase = "done"
            self.progress = 1.0
            self.log("Módulo inalámbrico listo." if not self.demo else "Demo finalizada; no se escribió hardware.")
        except Exception as error:
            self.phase = "error"
            self.radio_state = "error"
            self.error = "La instalación no terminó. Revisa los detalles y comprueba la conexión."
            self.log(f"Instalación fallida: {type(error).__name__}: {error}")
        finally:
            self.busy = False
            self.notify()

    async def _install_real(self):
        present = await asyncio.to_thread(board.ports)
        port = next((p for p in present if p.device == self.device), None)
        if port is None:
            raise OSError("El módulo se desconectó antes de instalar.")
        if getattr(port, "serial_number", None) != self.serial_number:
            raise OSError("La placa conectada ha cambiado; repite la comprobación.")
        chip = await asyncio.to_thread(board.detect_chip, self.device)
        if chip not in SUPPORTED_RADIO_CHIPS or chip != self.chip:
            raise ValueError("El chip conectado ha cambiado o no es compatible; repite la comprobación.")
        if not port.native:
            raise ValueError(f"Usa el puerto USB nativo del {chip}.")
        firmware = board.bundled_firmware(chip)
        if not Path(firmware).is_file():
            loop = asyncio.get_running_loop()
            await asyncio.to_thread(board.download_firmware,
                                    lambda line: loop.call_soon_threadsafe(self.log, line))
        if not Path(firmware).is_file():
            raise OSError(f"La release no contiene firmware para {chip}.")
        self.phase = "write"
        self.log(f"Instalando firmware de radio para {chip}.")
        env = dict(os.environ, NO_COLOR="1", PYTHONUNBUFFERED="1")
        env.pop("POKELDN_RADIO", None)
        # Passing the selected image also lets the existing flasher reject a swapped chip.
        self.process = await asyncio.create_subprocess_exec(
            *runner.command("--module", "gui.board", "--port", self.device,
                            "--kind", "radio", "--firmware", firmware),
            cwd=ROOT, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        async for raw in self.process.stdout:
            line = raw.decode("utf-8", "replace").strip()
            match = PERCENT.search(line)
            if match:
                self.progress = min(1.0, float(match[1]) / 100)
            self.log(line)
        code = await self.process.wait()
        if code:
            raise OSError(f"El instalador terminó con código {code}.")
        self.phase = "verify"
        self.progress = None
        self.log("Reiniciando y comprobando la radio…")
        await asyncio.sleep(3)
        # Re-enumeration may change the port. Prefer the same USB serial identity.
        for _ in range(4):
            present = await asyncio.to_thread(board.ports)
            candidates = ([p for p in present if getattr(p, "serial_number", None) == self.serial_number]
                          if self.serial_number else [p for p in present if p.device == self.device])
            if len(candidates) == 1:
                try:
                    ident = await asyncio.to_thread(board.identify, candidates[0].device, False)
                    if ident.current and ident.chip == chip and candidates[0].native:
                        self.device = candidates[0].device
                        self._save(radio_port=self.device)
                        self.radio_state = "ready"
                        self.radio_detail = "Firmware instalado y comunicación verificada."
                        return
                except Exception as error:
                    self.log(f"Esperando respuesta: {type(error).__name__}: {error}")
            await asyncio.sleep(2)
        raise OSError("El firmware se escribió, pero la radio no confirmó que está lista.")


# A web reconnect must not create a second owner of the serial port.
_shared = None


def shared_setup():
    global _shared
    if _shared is None:
        _shared = Setup()
    return _shared
