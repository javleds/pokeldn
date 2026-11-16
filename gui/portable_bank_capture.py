"""Archive only current-run, confirmed receipts; previews are not bank deposits."""
import asyncio
import hashlib
from pathlib import Path
import re

from pokeldn import pokemon
from pokeldn.app import received


def receipt_ordinal(path, game, stamp):
    """Launcher filenames encode trade numbers; never infer them from mtime."""
    name = Path(path).name
    suffix = Path(path).suffix.lower()
    if suffix not in ('.' + pokemon.EXTENSIONS[game], '.ek3' if game == 'frlg' else ''):
        return None
    stem = name[:-len(suffix)]
    base = f'{game}-{stamp}'
    if stem == base:
        return 1
    tail = stem[len(base):] if stem.startswith(base) else ''
    match = re.fullmatch(r'(?:-(\d+)|_(\d+)|_trade(\d+)_[^/]+)', tail)
    if not match:
        return None
    number = int(next(group for group in match.groups() if group is not None))
    return number if number > 0 else None


class ReceiptCapture:
    def __init__(self, game, stamp, folder, library, service, tasks, log, persistence_tasks=None):
        self.game, self.stamp, self.folder = game, stamp, folder
        self.library, self.service, self.tasks, self.log = library, service, tasks, log
        self.seen_paths = set()
        self.seen_hashes = set()
        self.lock = asyncio.Lock()
        self.confirmed = 0
        self.persistence_tasks = persistence_tasks if persistence_tasks is not None else set()

    def _task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def schedule(self, confirmed):
        self.confirmed = max(self.confirmed, confirmed)
        if self.confirmed:
            task = self._task(self.scan())
            self.persistence_tasks.add(task)
            task.add_done_callback(self.persistence_tasks.discard)

    async def drain(self):
        """Wait for capture and metadata tasks, used by deterministic tests."""
        while self.tasks:
            await asyncio.gather(*tuple(self.tasks))

    async def original(self, data):
        """The native return gate has already committed these exact original bytes."""
        async with self.lock:
            return await self._archive(data)

    async def _archive(self, data):
        if len(data) not in pokemon.RECORD_SIZES[self.game]:
            self.log('Banco: el registro recibido está incompleto; se conserva en Received.')
            return False
        digest = hashlib.sha256(data).hexdigest()
        if digest in self.seen_hashes:
            return True
        fallback = dict(species='Desconocido', species_id=0, level=0, legal=False)
        try:
            row = await asyncio.to_thread(self.library.deposit, self.game, data, fallback, {})
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.log(f'Banco: no se pudo guardar el original: {exc}')
            return False
        self.seen_hashes.add(digest)
        self._task(self._enrich(row['id'], data, fallback))
        return True

    async def _enrich(self, entry_id, data, fallback):
        info, owner = fallback, {}
        try:
            read = await asyncio.to_thread(self.service.check_bytes, self.game, data)
            if isinstance(read, dict):
                info = {**fallback, **read}
        except (OSError, ValueError, TypeError, AttributeError, pokemon.BuilderError) as exc:
            self.log(f'Banco: original conservado sin análisis completo: {exc}')
        try:
            owner = await asyncio.to_thread(self.service.owner, self.game, data)
        except (OSError, ValueError, TypeError, AttributeError, pokemon.BuilderError):
            pass
        try:
            await asyncio.to_thread(self.library.enrich, entry_id, info, owner)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            # Deletion during background analysis must never recreate the entry.
            self.log(f'Banco: no se actualizaron los datos del original: {exc}')

    async def scan(self):
        # Some adapters emit [done] immediately before writing the received file.
        # Retry briefly, then the process-exit scan provides the final opportunity.
        async with self.lock:
            for attempt in range(3):
                found = await asyncio.to_thread(received.session_files, self.folder, self.stamp)
                for path in found:
                    ordinal = receipt_ordinal(path, self.game, self.stamp)
                    if ordinal is None or ordinal > self.confirmed or path in self.seen_paths:
                        continue
                    try:
                        source = Path(path)
                        if source.stat().st_size not in pokemon.RECORD_SIZES[self.game]:
                            continue
                        data = await asyncio.to_thread(source.read_bytes)
                        if await self._archive(data):
                            self.seen_paths.add(path)
                    except OSError as exc:
                        self.log(f'Banco: no se pudo leer el recibido confirmado: {exc}')
                if attempt < 2:
                    await asyncio.sleep(.1)
