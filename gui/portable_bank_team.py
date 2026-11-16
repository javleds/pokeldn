"""One archived Pokémon, edited as a copy or offered without rewriting its entity."""
import asyncio
import base64
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile

from gui.portable_team import Team
from gui.views.pokemon import VERSIONS
from pokeldn import pokemon


class _TransientStore:
    def __init__(self, source):
        self.value = ({'slots': [None] * 6, 'profiles': {},
                       'selected_trainer': 'base', 'role': source.role,
                       'version': source.version, 'code': source.code} if source else {})

    def load(self):
        return deepcopy(self.value)

    def save(self, value):
        self.value = deepcopy(value)


class BankTeam(Team):
    """TeamView-compatible controller; neither archive nor saved Equipo is writable."""
    def __init__(self, game, setup, original: bytes, *, edit=False, source_team=None,
                 service=None, process_factory=None):
        super().__init__(game, setup, store=_TransientStore(source_team), service=service,
                         process_factory=process_factory)
        self.disposed = False
        self.original = bytes(original)
        self.original_hash = hashlib.sha256(self.original).hexdigest()
        self.edit_enabled = edit
        self.original_owner = None
        self.original_editable = {}
        self._candidate_folder = tempfile.TemporaryDirectory(prefix='pokeldn-bank-')
        self.slots = [None] * 6
        self.states = ['empty'] * 6

    @property
    def can_start(self):
        return not self.disposed and super().can_start

    @property
    def trainer(self):
        return deepcopy(self.original_owner) if self.original_owner else super().trainer

    def slot_available(self, index):
        return index == 0

    def add(self, index):
        raise ValueError('El banco permite preparar únicamente el Pokémon seleccionado.')

    def clear(self, index=None):
        raise ValueError('El original se conserva en el banco. Vuelve al listado para eliminarlo.')

    def set_trainer(self, key):
        raise ValueError('El Pokémon del banco conserva su entrenador original.')

    async def load_original(self):
        if self.disposed:
            return
        try:
            info = await asyncio.to_thread(self.service.edit_received, self.game, self.original, {})
            if self.disposed:
                return
            owner = await asyncio.to_thread(self.service.owner, self.game, self.original)
            if self.disposed:
                return
            self.original_owner = {key: owner[key] for key in ('ot', 'tid', 'sid', 'gender', 'language')}
            self.profiles = {'original': deepcopy(self.original_owner)}
            self.selected_trainer = 'original'
            self.original_editable = deepcopy(info['editable'])
            self.slots[0] = {key: deepcopy(info['editable'][key])
                             for key in ('species', 'level', 'nickname', 'shiny')}
            self.slots[0]['options'] = {key: deepcopy(value) for key, value in info['editable'].items()
                                       if key not in ('species', 'level', 'nickname', 'shiny')}
            self._invalidate(0)
            await self.validate(0)
        except (OSError, ValueError, KeyError, TypeError, pokemon.BuilderError) as exc:
            if self.disposed:
                return
            self.error = self.errors[0] = self.redact(str(exc))
            self.states[0] = 'error'
            self.notify()

    def edit(self, index, key, value, option=False):
        if self.disposed:
            return
        self._editable()
        if index != 0 or not self.edit_enabled or self.slots[0] is None:
            return
        target = self.slots[0]['options'] if option else self.slots[0]
        value = deepcopy(self.original_editable.get(key) if value is None else value)
        if target.get(key) == value:
            return
        target[key] = value
        if key in ('species', 'form'):
            self.metadata.pop(0, None)
        self._invalidate(0)
        self.notify()

    async def load_options(self, index):
        if self.disposed:
            return {}
        found = await super().load_options(index)
        found.pop('encounters', None)
        found.pop('sweets', None)
        return found

    async def validate(self, index):
        if not self.disposed:
            await super().validate(index)

    async def _validate(self, index, revision):
        if self.disposed or index != 0 or self.slots[0] is None or revision != self._revision[0]:
            return
        self.states[0], self.errors[0] = 'validating', ''
        self.notify()
        try:
            draft = self.normalized(self.slots[0])
            changes = {}
            if self.edit_enabled:
                flat = {key: draft[key] for key in ('species', 'level', 'nickname', 'shiny')}
                flat['species'], flat['level'] = int(flat['species']), int(flat['level'])
                flat.update(draft['options'])
                flat.pop('moves', None)
                moves = self.requested_move_slots(self.slots[0]['options'].get('moves', self.original_editable['moves']))
                changes = {key: value for key, value in flat.items()
                           if value != self.original_editable.get(key)}
                if moves != self.original_editable['moves']:
                    changes['move_slots'] = moves
            info = await asyncio.to_thread(self.service.edit_received, self.game, self.original, changes)
            if self.disposed or revision != self._revision[0]:
                return
            data = base64.b64decode(info['data'], validate=True) if changes else self.original
            checked = await asyncio.to_thread(self.service.check_bytes, self.game, data)
            if self.disposed or revision != self._revision[0]:
                return
            legal = info.get('legal') is True and checked.get('legal') is True
            target = Path(self._candidate_folder.name) / f'{revision}.{pokemon.EXTENSIONS[self.game]}'
            target.write_bytes(data)
            target.chmod(0o600)
            self.results[0] = {**info, 'file': str(target), 'legal': legal}
            self._hashes[0] = hashlib.sha256(data).hexdigest()
            self._result_revision[0] = revision
            self.states[0] = 'legal' if legal else 'invalid'
            report = str(checked.get('report') or info.get('report') or 'Pokémon no legal.')
            self.errors[0] = '' if legal else report.splitlines()[0]
            self.error = self.errors[0]
            await self.load_options(0)
            if self.disposed or revision != self._revision[0]:
                return
            try:
                await self.load_moves(0, draft, deepcopy(self.trainer), VERSIONS.get(self.version, ''))
            except pokemon.BuilderError:
                pass
        except (ValueError, TypeError, KeyError, OSError, pokemon.BuilderError) as exc:
            if not self.disposed and revision == self._revision[0]:
                self.errors[0] = self.error = self.redact(str(exc)).splitlines()[0]
                self.states[0] = 'invalid'
                self.results[0] = {}
        finally:
            if not self.disposed and revision == self._revision[0]:
                self._validated_revision[0] = revision
            if not self.disposed:
                self.notify()

    async def start(self, discover=False, return_original=False):
        if self.disposed:
            return
        if discover or return_original:
            raise ValueError('El banco solo envía el Pokémon seleccionado.')
        await super().start()

    def _run_env(self, settings):
        data = Path(self.results[0]['file']).read_bytes()
        if hashlib.sha256(data).hexdigest() != self._hashes[0]:
            raise ValueError('El candidato del banco cambió antes de iniciar.')
        return {**super()._run_env(settings),
                'POKELDN_EXACT_OFFER_GAME': self.game,
                'POKELDN_EXACT_OFFER_SHA256': hashlib.sha256(pokemon.entity_bytes(self.game, data)).hexdigest()}

    def dispose(self):
        if self.busy or self.disposed:
            return
        self.disposed = True
        self._revision = [revision + 1 for revision in self._revision]
        for pending in (self._tasks, self._metadata_tasks, self._move_tasks):
            for _, task in pending.values():
                task.cancel()
            pending.clear()
        self.slots = [None] * 6
        self.results = [{} for _ in range(6)]
        self.states = ['empty'] * 6
        self.metadata.clear()
        self.move_options.clear()
        self._candidate_folder.cleanup()
