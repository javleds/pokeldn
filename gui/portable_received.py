"""Receive/edit/return sessions. Original bytes never pass through the editor."""
import asyncio
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile

from gui.portable_team import Team, TeamStore, DATA, STATS
from gui.views.pokemon import VERSIONS
from pokeldn import pokemon, portable_return
from pokeldn.app import received

MODES = {
    'team': 'Equipo', 'evolution': 'Evolución', 'level': 'Nivel',
    'nature': 'Naturaleza', 'effort': 'EVs', 'modifier': 'Modificador', 'validator': 'Validador',
}


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class ReceivedTeam(Team):
    def __init__(self, game, setup, mode, **kwargs):
        if mode not in MODES or mode == 'team':
            raise ValueError('Modalidad no disponible.')
        kwargs.setdefault('store', TeamStore(game, DATA / 'portable' / 'received-drafts'))
        super().__init__(game, setup, **kwargs)
        self.mode = mode
        self.active = False
        self.params = {'level': '100', 'nature': 0, 'effort': {s: '0' for s in STATS}}
        self.original = None
        self.original_hash = ''
        self.original_editable = {}
        self.original_owner = None
        self.original_legal = None
        self.candidate_legal = False
        self.candidate_data = None
        self.candidate_revision = -1
        self.report = ''
        self.return_dir = None
        self.slots = [None] * 6
        self.states = ['empty'] * 6
        self.pending_receipts = []
        for journal in (DATA / 'portable' / 'returns').glob('*/journal.json'):
            try:
                record = json.loads(journal.read_text())
                if record.get('game') == game and (record.get('received') or (journal.parent / 'request.json').exists()) and not record.get('returned'):
                    self.pending_receipts.append(journal)
            except (OSError, ValueError):
                self.pending_receipts.append(journal)
        self.recovery_notice = ('Hay devoluciones anteriores pendientes. Se conservan los originales; '
                                'no se reenvían automáticamente a otra consola.' if self.pending_receipts else '')

    @property
    def supported(self):
        return portable_return.supports(self.game, self.role)

    @property
    def support_reason(self):
        return '' if self.supported else 'Esta combinación de juego y rol aún no admite devolución controlada.'

    @property
    def can_start(self):
        return (not self.active and self.supported and not self.setup.busy
                and not self.setup.checking and not self.setup.session_busy)

    @property
    def trainer(self):
        return deepcopy(self.original_owner) if self.original_owner else super().trainer

    @property
    def return_pending(self):
        return self.original is not None and self.completed < 2

    def save(self):
        # Received drafts never overwrite Equipo or trainer profiles.
        if self.return_dir is not None:
            self._journal()

    def _journal(self):
        if self.return_dir is None:
            return
        record = {'schema': 1, 'game': self.game, 'mode': self.mode, 'role': self.role,
                  'version': self.version, 'sha256': self.original_hash,
                  'received': self.original is not None, 'returned': self.completed >= 2,
                  'phase': self.phase}
        atomic_write(self.return_dir / 'journal.json', json.dumps(record).encode())

    def configure_param(self, key, value):
        if self.active:
            return
        if key not in self.params:
            raise ValueError('Opción no disponible.')
        self.params[key] = deepcopy(value)
        self.notify()

    def configure(self, role, version, code):
        if self.active:
            raise ValueError('La sesión está activa.')
        super().configure(role, version, code)

    def _parameter_fields(self):
        if self.mode == 'level':
            level = int(self.params['level'])
            if not 1 <= level <= 100:
                raise ValueError('Nivel: usa un valor de 1 a 100.')
            return {'level': level}
        if self.mode == 'nature':
            nature = int(self.params['nature'])
            if not 0 <= nature < 25:
                raise ValueError('Selecciona una naturaleza válida.')
            return {'nature': nature}
        if self.mode == 'effort':
            values = {s: int(self.params['effort'].get(s, 0)) for s in STATS}
            maximum = 200 if self.game == 'lgpe' else 10 if self.game == 'pla' else 252
            if any(not 0 <= n <= maximum for n in values.values()):
                raise ValueError(f'Esfuerzo: usa valores de 0 a {maximum}.')
            if self.game not in ('lgpe', 'pla') and sum(values.values()) > 510:
                raise ValueError('La suma de EVs no puede superar 510.')
            return {'effort': values}
        return {}

    async def start(self):
        if not self.can_start:
            self.error = self.support_reason or 'Hay otra operación en curso.'
            self.notify()
            return
        try:
            self._parameter_fields()
        except (ValueError, TypeError):
            self.error = 'Revisa los valores de la modalidad antes de iniciar.'
            self.notify()
            return
        self.active = True
        self.original = None
        self.original_owner = None
        self.original_hash = ''
        self.original_legal = None
        self.return_dir = None
        self.candidate_data = None
        self.candidate_legal = False
        self.report = ''
        self.slots = [None] * 6
        self.metadata.clear()
        self._metadata_keys.clear()
        self.move_options.clear()
        await super().start(discover=True, return_original=True)
        if self.active and self.process is None:
            # Demo or a competing session can refuse before Team acquires the radio.
            self.active = self.busy = False
            self.phase = 'error'
        elif self.active:
            self.phase = 'receiving'
        self.notify()

    def _run_env(self, settings):
        env = super()._run_env(settings)
        self.return_dir = DATA / 'portable' / 'returns' / self.run_stamp
        self.return_dir.mkdir(parents=True, mode=0o700)
        self._journal()
        return {**env, 'POKELDN_RETURN_DIR': str(self.return_dir), 'POKELDN_RETURN_GAME': self.game}

    def _line(self, line):
        self.log(line)
        count = received.trades_done(line)
        if count is not None:
            self.completed = max(self.completed, min(count, 2))
            self._capture_received()
            self._journal()
        if line.startswith('[portable-return] error'):
            self.error = line.split('error', 1)[1].strip()
            self.candidate_legal = False
            self.errors[0] = self.error
            self.states[0] = 'invalid'
            self.busy = False
            self.phase = 'editing' if self.mode == 'modifier' and self.slots[0] else 'review'
        self.notify()

    async def _watch_received(self, stamp, folder):
        # Gate writes only a committed original, independent of preview/save-shown files.
        while self.run_stamp == stamp and self.active:
            directory = self.return_dir
            if directory and (directory / 'request.json').exists():
                try:
                    if (directory / 'request.json').stat().st_size > 4096 or (directory / 'original.bin').stat().st_size > pokemon.RECORD_LIMIT:
                        raise ValueError('El registro recibido excede el tamaño permitido.')
                    request = json.loads((directory / 'request.json').read_text())
                    data = (directory / 'original.bin').read_bytes()
                    digest = hashlib.sha256(data).hexdigest()
                    if request.get('game') != self.game or request.get('sha256') != digest:
                        raise ValueError('El original no coincide con la sesión.')
                    self.original, self.original_hash = data, digest
                    if self._bank_capture is not None:
                        await self._bank_capture.original(data)
                    self.received_path = str(directory / 'original.bin')
                    self._journal()
                    info = await asyncio.to_thread(self.service.edit_received, self.game, data, {})
                    owner = await asyncio.to_thread(self.service.owner, self.game, data)
                    if self.run_stamp != stamp or not self.active:
                        return
                    self.original_owner = {k: owner[k] for k in ('ot', 'tid', 'sid', 'gender', 'language')}
                    self.original_editable = deepcopy(info['editable'])
                    self.received_info = info
                    self.original_legal = info.get('legal') is True
                    self.report = str(info.get('report') or '')
                    self.log('Informe del original:\n' + self.report)
                    self._set_received_draft(info['editable'])
                    self.busy = False
                    self.phase = 'editing' if self.mode == 'modifier' else 'review'
                    self.notify()
                    if self.mode in ('evolution', 'validator'):
                        await self.return_original_now()
                    else:
                        for key, value in self._parameter_fields().items():
                            self.edit(0, key, value, option=key not in ('level', 'species', 'nickname', 'shiny'))
                        await self.validate(0)
                        if self.mode != 'modifier' and self.candidate_legal:
                            await self.return_edited_now()
                    return
                except (OSError, ValueError, KeyError, TypeError, pokemon.BuilderError) as exc:
                    if self.run_stamp == stamp and self.active:
                        self.error = self.redact(str(exc))
                        self.report = self.error
                        self.busy = False
                        self.phase = 'review'
                        self._journal()
                        self.notify()
                        if self.original is not None and self.mode in ('evolution', 'validator'):
                            self.log('No se pudo analizar el original: ' + self.error)
                            await self.return_original_now()
                    return
            await asyncio.sleep(.2)

    def _set_received_draft(self, snapshot):
        self.slots[0] = {k: deepcopy(snapshot[k]) for k in ('species', 'level', 'nickname', 'shiny')}
        self.slots[0]['options'] = {k: deepcopy(v) for k, v in snapshot.items()
                                    if k not in ('species', 'level', 'nickname', 'shiny')}
        self._invalidate(0)

    def edit(self, index, key, value, option=False):
        if not self.active or self.busy or self.phase not in ('editing', 'review') or index != 0 or self.original is None:
            return
        # setup.session_busy intentionally remains true while this editor is unlocked.
        draft = self.slots[0]
        if draft is None:
            return
        target = draft['options'] if option else draft
        if value is None:
            original = self.original_editable.get(key)
            target[key] = deepcopy(original)
        else:
            target[key] = deepcopy(value)
        self._invalidate(0)
        self.candidate_legal = False
        self.candidate_data = None
        if key in ('species', 'form'):
            self.metadata.pop(0, None)
        self.notify()

    async def load_options(self, index):
        found = await super().load_options(index)
        found.pop('encounters', None)
        found.pop('sweets', None)
        return found

    async def validate(self, index):
        if self.original is None or self.busy or not self.active:
            return
        revision, stamp = self._revision[0], self.run_stamp
        self.states[0] = 'validating'
        self.candidate_legal = False
        self.notify()
        try:
            draft = self.normalized(self.slots[0])
            owner, version = deepcopy(self.trainer), VERSIONS.get(self.version, '')
            flat = {k: draft[k] for k in ('species', 'level', 'nickname', 'shiny')}
            flat['species'], flat['level'] = int(flat['species']), int(flat['level'])
            flat.update(draft['options'])
            flat.pop('moves', None)
            moves = self.requested_move_slots(self.slots[0]['options'].get('moves', self.original_editable['moves']))
            changes = {k: v for k, v in flat.items() if v != self.original_editable.get(k)}
            if moves != self.original_editable['moves']:
                changes['move_slots'] = moves
            info = await asyncio.to_thread(self.service.edit_received, self.game, self.original, changes)
            if stamp != self.run_stamp or revision != self._revision[0] or not self.active:
                return
            self.candidate_data = base64.b64decode(info['data'], validate=True)
            self.candidate_legal = info.get('legal') is True
            self.candidate_revision = revision
            self.results[0] = info
            self.report = str(info.get('report') or '')
            self.errors[0] = '' if self.candidate_legal else self.report.splitlines()[0] if self.report else 'Pokémon no legal.'
            self.states[0] = 'legal' if self.candidate_legal else 'invalid'
            self.error = self.errors[0]
            await self.load_options(0)
            try:
                await self.load_moves(0, draft, owner, version)
            except pokemon.BuilderError:
                pass
        except (ValueError, TypeError, OSError, pokemon.BuilderError) as exc:
            if stamp == self.run_stamp and revision == self._revision[0]:
                self.error = self.errors[0] = self.redact(str(exc)).splitlines()[0]
                self.report = self.redact(str(exc))
                self.states[0] = 'invalid'
                self.candidate_legal = False
        finally:
            if stamp == self.run_stamp:
                self.notify()

    async def return_original_now(self):
        await self._return(True)

    async def return_edited_now(self):
        await self._return(False)

    async def _return(self, original):
        if not self.active or self.busy or self.original is None or self.completed >= 2:
            return
        if not original and (not self.candidate_legal or self.candidate_revision != self._revision[0]):
            self.error = 'Valida una copia legal actual antes de devolverla.'
            self.notify()
            return
        self.busy = True
        self.notify()
        stamp, directory, revision = self.run_stamp, self.return_dir, self._revision[0]
        try:
            if hashlib.sha256((directory / 'original.bin').read_bytes()).hexdigest() != self.original_hash:
                raise ValueError('El archivo original cambió. Se bloqueó la devolución.')
            response = {'action': 'original' if original else 'edited', 'sha256': self.original_hash}
            if not original:
                candidate = bytes(self.candidate_data)
                checked = await asyncio.to_thread(self.service.check_bytes, self.game, candidate)
                if (not self.active or self.stop_requested or self.run_stamp != stamp
                        or self.return_dir != directory or self._revision[0] != revision):
                    return
                if checked.get('legal') is not True:
                    raise ValueError('La validación final bloqueó la copia editada.')
                atomic_write(directory / 'edited.bin', candidate)
                response['candidate_sha256'] = hashlib.sha256(candidate).hexdigest()
            atomic_write(directory / 'response.json', json.dumps(response).encode())
            self.phase = 'returning'
            self.error = ''
            self._journal()
        except (OSError, ValueError, pokemon.BuilderError) as exc:
            if self.run_stamp == stamp:
                self.error = self.redact(str(exc))
                self.busy = False
                self.phase = 'editing' if self.mode == 'modifier' and self.slots[0] else 'review'
        self.notify()

    def _exited(self, code):
        self._capture_received()
        self.active = self.busy = False
        self.phase = 'stopped' if self.stop_requested else 'done' if code == 0 and self.completed == 2 else 'error'
        if self.return_pending:
            self.error = 'Devolución pendiente. Se conserva el original; no hay reanudación automática.'
        elif self.phase == 'error' and not self.error:
            self.error = 'La sesión terminó sin confirmar recepción y devolución.'
        try:
            self._journal()
        except OSError as exc:
            self.error = 'No se pudo actualizar el registro de devolución: ' + self.redact(str(exc))
        finally:
            self.setup.session_busy = False
            self.setup.active_team = None
            self.process = None
        self.notify()

    def stop(self):
        if not self.active:
            return
        self.stop_requested, self.phase, self.busy = True, 'stopping', True
        try:
            self._journal()
        except OSError as exc:
            self.error = 'No se pudo guardar el estado: ' + self.redact(str(exc))
        finally:
            if self.process:
                self.process.stop()
        self.notify()

    def reset(self):
        if self.active:
            return
        if self.return_pending and self.return_dir is not None:
            journal = self.return_dir / 'journal.json'
            if journal not in self.pending_receipts:
                self.pending_receipts.append(journal)
            self.recovery_notice = ('Hay devoluciones anteriores pendientes. Se conservan los originales; '
                                    'no se reenvían automáticamente a otra consola.')
        self.slots = [None] * 6
        self.received_info = None
        self.original = None
        self.original_owner = None
        self.original_legal = None
        self.candidate_data = None
        self.candidate_legal = False
        self.report = ''
        self.return_dir = None
        self.phase = 'idle'
        self.error = ''
        self.notify()
