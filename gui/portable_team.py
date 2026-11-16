"""Portable team drafts and sessions. UI state never authorizes an unchecked offer."""
import asyncio
from collections import deque
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import uuid

from gui.localization import error_message
from gui.portable_setup import validate_keys
from gui.views.pokemon import VERSIONS
from pokeldn import console_trainer, pokemon
from pokeldn.app import command, received, runner, settings as settings_module
from pokeldn.app.catalog import GAMES
from pokeldn.app.paths import DATA, SESSION
from pokeldn.app.redact import Redactor

STATS = ('hp', 'atk', 'def', 'spa', 'spd', 'spe')


class PortableService(pokemon.Service):
    """Share PKHeX's worker, requesting Spanish data without changing desktop locale."""
    def _ask(self, request):
        return pokemon.SERVICE._ask({**request, 'display_language': 'es'})


SERVICE = PortableService()


def local_tools(game):
    found = next(g for g in GAMES if g.key == game)
    return {dict(t.variant).get('role', 'host'): t for t in found.tools
            if t.activity == 'trade' and dict(t.variant).get('link') == 'board'}


class TeamStore:
    """One atomically replaced private draft per game; no upstream settings migration."""
    def __init__(self, game, root=None):
        if game not in {g.key for g in GAMES}:
            raise ValueError('Juego no disponible.')
        self.path = Path(root or DATA / 'portable' / 'teams') / f'{game}.json'

    def load(self):
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or value.get('schema') != 1:
                raise ValueError('Versión de borrador desconocida.')
            slots = value.get('slots')
            if not isinstance(slots, list) or len(slots) != 6 or any(s is not None and not isinstance(s, dict) for s in slots):
                raise ValueError('El borrador debe contener seis cajas.')
            if not isinstance(value.get('profiles', {}), dict):
                raise ValueError('Perfiles inválidos.')
            return value
        except (ValueError, OSError) as exc:
            raise ValueError(f'No se pudo leer {self.path.name}; se conserva el archivo original.') from exc

    def save(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=self.path.stem, suffix='.tmp', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(dict(value, schema=1), stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)


class Team:
    def __init__(self, game, setup, *, store=None, service=None, process_factory=None):
        self.game, self.setup = game, setup
        self.settings = setup.settings
        self._received_folder = self.settings.received
        self.store = store or TeamStore(game)
        self.service = service or SERVICE
        self.process_factory = process_factory or runner.Process
        self.tools = local_tools(game)
        self.listeners = set()
        self.busy = False
        self.phase = 'idle'
        self.error = ''
        self.logs = deque(maxlen=500)
        self.redact = Redactor()
        self.process = None
        self.popups = None
        self.completed = 0
        self.active_slots = []
        self.discovering = False
        self.return_original = False
        self.received_info = None
        self.received_path = ''
        self.received_error = ''
        self.found_trainer = None
        self.stop_requested = False
        self.metadata = {}
        self._metadata_keys = {}
        self._metadata_tasks = {}
        self._catalogs = {}
        self._validated_revision = [-1] * 6
        self.move_options = {}
        self._move_tasks = {}
        self._revision = [0] * 6
        self._tasks = {}
        self._result_revision = [-1] * 6
        self._hashes = [''] * 6
        self._storage_error = ''
        try:
            saved = self.store.load()
        except ValueError as exc:
            saved = {}
            self._storage_error = self.error = str(exc)
        saved_slots = saved.get('slots', [None] * 6)
        drafts = [s for s in saved_slots if s and s.get('species')]
        drafts += [s for s in saved_slots if s is not None and not s.get('species')]
        self.slots = drafts + [None] * (6 - len(drafts))
        self.profiles = saved.get('profiles', {})
        self.selected_trainer = saved.get('selected_trainer', 'base')
        if self.selected_trainer not in self.profiles:
            self.selected_trainer = 'base'
        self.role = saved.get('role', 'host')
        if self.role not in self.tools:
            self.role = next(iter(self.tools), 'host')
        self.version = saved.get('version', self.settings.version(game))
        if self.version not in dict(settings_module.VERSIONS.get(game, ())):
            self.version = self.settings.version(game)
        self.code = saved.get('code', '')
        if game == 'lgpe':
            from pokeldn.lgpe.session import code_picks
            raw = self.code or '000'
            try:
                self.code = ''.join(map(str, code_picks(raw.split(',') if ',' in raw else raw)))
            except ValueError:
                pass  # Keep an invalid saved value visible for correction.
        self.states = ['pending' if s and s.get('species') else 'empty' for s in self.slots]
        self.errors = [''] * 6
        self.results = [{} for _ in range(6)]

    @property
    def trainer(self):
        if self.selected_trainer == 'base':
            return self.settings.trainer(self.version or self.game)
        return deepcopy(self.profiles[self.selected_trainer])

    @property
    def can_start(self):
        indexes = [i for i, s in enumerate(self.slots) if s and s.get('species')]
        return (not self.busy and not self._storage_error and bool(indexes) and bool(self.tools)
                and not self.setup.busy and not self.setup.checking and not self.setup.session_busy
                and all(self.states[i] == 'legal' and self._result_revision[i] == self._revision[i]
                        and self.results[i].get('file') for i in indexes))

    def notify(self):
        for listener in tuple(self.listeners):
            try:
                listener()
            except RuntimeError:
                self.listeners.discard(listener)

    def save(self):
        if self._storage_error:
            raise ValueError(self._storage_error)
        try:
            self.store.save({'slots': self.slots, 'profiles': self.profiles,
                             'selected_trainer': self.selected_trainer, 'version': self.version,
                             'role': self.role, 'code': self.code})
        except OSError as exc:
            self.error = self._storage_error = f'No se pudo guardar el borrador: {exc}'
            self.notify()
            raise

    def _editable(self):
        if self.busy:
            raise ValueError('El intercambio está en curso.')
        if self._storage_error:
            raise ValueError(self._storage_error)

    def _invalidate(self, index):
        self._revision[index] += 1
        self.states[index] = 'pending' if (self.slots[index] or {}).get('species') else 'empty'
        self.results[index], self.errors[index], self._hashes[index] = {}, '', ''

    def add(self, index):
        self._editable()
        if not self.slot_available(index):
            raise ValueError('Elige una especie en la caja anterior primero.')
        if self.slots[index] is None:
            self.slots[index] = {'species': 0, 'level': '100', 'nickname': '', 'shiny': False, 'options': {}}
            self._invalidate(index)
            self.save()
            self.notify()

    def clear(self, index=None):
        self._editable()
        sources = [] if index is None else [i for i in range(6) if i != index and self.slots[i] is not None]
        old_revisions = self._revision[:]
        for name, default in (('slots', None), ('states', 'empty'), ('errors', ''),
                              ('results', {}), ('_hashes', '')):
            old = getattr(self, name)
            setattr(self, name, [old[i] for i in sources] + [deepcopy(default) for _ in range(6 - len(sources))])
        for name in ('metadata', '_metadata_keys', 'move_options'):
            old = getattr(self, name)
            setattr(self, name, {new: old[source] for new, source in enumerate(sources) if source in old})
        # Never reuse a positional revision: an old worker may still finish after
        # its Pokémon moved. Only already-current results may follow the draft.
        for name in ('_result_revision', '_validated_revision'):
            old = getattr(self, name)
            setattr(self, name, [old_revisions[new] + 1 if old[source] == old_revisions[source] else -1
                                for new, source in enumerate(sources)] + [-1] * (6 - len(sources)))
        self._revision = [revision + 1 for revision in old_revisions]
        self.states = ['pending' if state == 'validating' else state for state in self.states]
        self._tasks.clear()
        self._metadata_tasks.clear()
        self._move_tasks.clear()
        self.save()
        self.notify()

    def slot_available(self, index):
        first_empty = next((i for i, draft in enumerate(self.slots) if not (draft or {}).get('species')), 5)
        return 0 <= index <= first_empty

    def edit(self, index, key, value, option=False):
        self._editable()
        if not self.slot_available(index):
            raise ValueError('Elige una especie en la caja anterior primero.')
        if key == 'species' and not value and (self.slots[index] or {}).get('species'):
            self.clear(index)
            return
        if self.slots[index] is None:
            self.add(index)
        draft = self.slots[index]
        target = draft.setdefault('options', {}) if option else draft
        if target.get(key) == value:
            return
        if value is None:
            target.pop(key, None)
        else:
            target[key] = deepcopy(value)
        if key in ('species', 'form'):
            self.metadata.pop(index, None)
        self._invalidate(index)
        self.save()
        self.notify()

    def set_trainer(self, key):
        self._editable()
        if key != 'base' and key not in self.profiles:
            raise ValueError('Entrenador desconocido.')
        self.selected_trainer = key
        for i in range(6):
            self._invalidate(i)
        self.metadata.clear()
        self.save()
        self.notify()

    def configure(self, role, version, code):
        self._editable()
        if role not in self.tools:
            raise ValueError('Ese papel no está disponible para este juego.')
        if version not in (dict(settings_module.VERSIONS.get(self.game, ())) or {self.game: 0}):
            raise ValueError('Versión de juego no válida.')
        if self.game == 'lgpe' and (len(code) != 3 or any(c not in '0123456789' for c in code)):
            raise ValueError('El código de Let’s Go debe contener exactamente tres dígitos (0–9).')
        changed = version != self.version
        self.role, self.version, self.code = role, version, code
        if changed:
            for i in range(6):
                self._invalidate(i)
            self.metadata.clear()
        self.save()
        self.notify()

    async def names(self, kind):
        if kind in self._catalogs:
            return self._catalogs[kind]
        if kind == 'species':
            result = await asyncio.to_thread(self.service.species, self.game)
        else:
            result = await asyncio.to_thread(self.service.names, self.game, kind)
        self._catalogs[kind] = result
        return result

    async def load_options(self, index):
        draft = self.slots[index]
        if not draft or not draft.get('species'):
            return {}
        revision = self._revision[index]
        species = int(draft['species'])
        form = int(draft.get('options', {}).get('form') or 0)
        owner = deepcopy(self.trainer)
        version = VERSIONS.get(self.version, '')
        key = (species, form, version, json.dumps(owner, sort_keys=True))
        if self._metadata_keys.get(index) == key and index in self.metadata:
            return self.metadata[index]
        async def fetch():
            found = deepcopy(await asyncio.to_thread(self.service.options, self.game, species, owner, version, form))
            found['encounters'] = await asyncio.to_thread(self.service.encounters, self.game, species, owner, version, form)
            return found
        existing = self._metadata_tasks.get(index)
        if existing and existing[0] == key and not existing[1].done():
            task = existing[1]
        else:
            task = asyncio.create_task(fetch())
            self._metadata_tasks[index] = (key, task)
        found = await asyncio.shield(task)
        if self._revision[index] == revision:
            self.metadata[index] = found
            self._metadata_keys[index] = key
        return found

    @staticmethod
    def normalized(draft):
        draft = deepcopy(draft)
        options = draft.setdefault('options', {})
        for key in ('friendship', 'dynamax_level', 'form', 'nature', 'ability', 'gender', 'held_item', 'ball', 'tera', 'sweet'):
            value = options.get(key)
            if value == '':
                options.pop(key, None)
            elif isinstance(value, str) and value.isdigit():
                options[key] = int(value)
        for group in ('ivs', 'effort'):
            if isinstance(options.get(group), dict):
                options[group] = {k: int(v) if isinstance(v, str) and v.isdigit() else v
                                  for k, v in options[group].items() if v != ''}
        if isinstance(options.get('moves'), list):
            options['moves'] = [int(v) if isinstance(v, str) and v.isdigit() else v
                                for v in options['moves'] if v not in (None, '', 0, '0')]
        return draft

    def _move_key(self, index):
        draft = self.normalized(self.slots[index] or {})
        draft.pop('nickname', None)
        draft['options'].pop('moves', None)
        return json.dumps([draft, self.trainer, self.version], sort_keys=True)

    def candidate_moves(self, index):
        cached = self.move_options.get(index)
        return cached[1] if cached and cached[0] == self._move_key(index) else []

    async def load_moves(self, index, draft, owner, version):
        key = self._move_key(index)
        cached = self.move_options.get(index)
        if cached and cached[0] == key:
            return cached[1]
        options = deepcopy(draft.get('options', {}))
        options.pop('moves', None)
        existing = self._move_tasks.get(index)
        if existing and existing[0] == key and not existing[1].done():
            task = existing[1]
        else:
            task = asyncio.create_task(asyncio.to_thread(self.service.move_options,
                self.game, draft['species'], owner, int(draft['level']),
                bool(draft.get('shiny')), version, options))
            self._move_tasks[index] = (key, task)
        moves = await asyncio.shield(task)
        if self.slots[index] is not None and self._move_key(index) == key:
            self.move_options[index] = (key, moves)
        return moves

    def draft_problem(self, draft, found):
        if not isinstance(draft.get('species'), int) or draft['species'] <= 0:
            return 'Elige una especie.'
        level = str(draft.get('level', ''))
        if not level.isdigit() or not 1 <= int(level) <= 100:
            return 'Nivel: introduce un entero entre 1 y 100.'
        if len(str(draft.get('nickname', ''))) > (10 if self.game in settings_module.GEN3 else 12):
            return 'El apodo supera el límite del juego.'
        options = draft.get('options', {})
        for key, maximum in (('friendship', 255), ('dynamax_level', 10)):
            if key in options and (type(options[key]) is not int or not 0 <= options[key] <= maximum):
                return f'{key}: introduce un entero entre 0 y {maximum}.'
        for group, maximum, total in (('ivs', 31, None), ('effort', found.get('effort', {}).get('max', 252), found.get('effort', {}).get('total'))):
            values = options.get(group, {})
            if not isinstance(values, dict) or any(k not in STATS or type(v) is not int or not 0 <= v <= maximum for k, v in values.items()):
                return f'{"IV" if group == "ivs" else "EV"}: valores enteros entre 0 y {maximum}.'
            if total is not None and sum(values.values()) > total:
                return f'EV: el total no puede superar {total}.'
        return ''

    async def validate(self, index):
        if self.busy or not (self.slots[index] or {}).get('species'):
            return
        revision = self._revision[index]
        if self._validated_revision[index] == revision and self.states[index] in ('legal', 'invalid'):
            return
        existing = self._tasks.get(index)
        if existing and existing[0] == revision and not existing[1].done():
            await asyncio.shield(existing[1])
            return
        task = asyncio.create_task(self._validate(index, revision))
        self._tasks[index] = (revision, task)
        await asyncio.shield(task)

    async def _validate(self, index, revision):
        if revision != self._revision[index] or not (self.slots[index] or {}).get('species'):
            return
        draft, owner, version = self.normalized(self.slots[index]), deepcopy(self.trainer), VERSIONS.get(self.version, '')
        self.states[index], self.errors[index] = 'validating', ''
        self.notify()
        try:
            # Cheap input checks precede all expensive service calls.
            problem = self.draft_problem(draft, self.metadata.get(index, {}))
            if problem:
                raise ValueError(problem)
            found = await self.load_options(index)
            if problem := self.draft_problem(draft, found):
                raise ValueError(problem)
            if revision != self._revision[index]:
                return
            try:
                await self.load_moves(index, draft, owner, version)
            except pokemon.BuilderError:
                # A reference without the chosen moves can fail while a specific
                # event/moveset works. Suggestions must never override final legality.
                pass
            if revision != self._revision[index]:
                return
            info = await asyncio.to_thread(self.service.make, self.game, draft['species'], owner,
                                           int(draft['level']), bool(draft.get('shiny')), draft.get('nickname', ''),
                                           version, draft.get('options', {}))
            data = await asyncio.to_thread(Path(info['file']).read_bytes)
            checked = await asyncio.to_thread(self.service.check_bytes, self.game, data)
            legal = info.get('legal') is True and checked.get('legal') is True
            report = str(checked.get('report') or info.get('report') or 'Pokémon no legal.')
            if revision == self._revision[index]:
                self.results[index] = info
                self._hashes[index] = hashlib.sha256(data).hexdigest()
                self._result_revision[index] = revision
                self.states[index] = 'legal' if legal else 'invalid'
                self.errors[index] = '' if legal else report.splitlines()[0]
        except Exception as exc:
            if revision == self._revision[index]:
                self.states[index] = 'invalid' if isinstance(exc, ValueError) else 'error'
                self.errors[index] = (self.redact(error_message(exc)).splitlines() or ['No se pudo validar.'])[0]
                self.results[index] = {}
        finally:
            if revision == self._revision[index]:
                self._validated_revision[index] = revision
            self.notify()

    async def validate_all(self):
        await asyncio.gather(*(self.validate(i) for i, draft in enumerate(self.slots) if draft is not None))

    def log(self, line):
        self.logs.append(self.redact(str(line))[:1500])
        self.notify()

    def _values(self, tool, files):
        values = {f.key: f.default for f in tool.fields}
        offer = next(f for f in tool.fields if f.kind == 'pokemon')
        values[offer.key] = [{'file': str(path), 'legal': True, 'bank': True} for path in files]
        for f in tool.fields:
            if f.kind == 'code':
                values[f.key] = self.code
            elif f.kind == 'linkcode':
                values[f.key] = ','.join(self.code)
            if f.key == '--version':
                values[f.key] = self.version
        values['--fresh-pid'] = False
        values['--trade-back'] = self.discovering and self.return_original
        return values

    def _run_env(self, settings):
        return runner.base_env(settings, self.setup.device)

    @property
    def return_pending(self):
        return self.discovering and self.return_original and self.completed == 1

    async def start(self, discover=False, return_original=False):
        # Closing a web tab must not strand preparation with the shared radio reserved.
        await asyncio.shield(self._start(discover, return_original))

    async def _start(self, discover=False, return_original=False):
        if self.busy or self.setup.busy or self.setup.checking or self.setup.session_busy:
            return
        if not discover and not self.can_start:
            self.error = 'Todas las cajas ocupadas deben tener una validación legal actual.'
            self.notify()
            return
        if self.setup.demo:
            self.error = 'La demo no inicia intercambios físicos.'
            self.notify()
            return
        self.busy = self.setup.session_busy = True
        self.setup.active_team = self
        self.phase, self.error, self.completed = 'preparing', '', 0
        self.discovering, self.found_trainer, self.stop_requested = discover, None, False
        self.return_original = discover and return_original
        self.run_stamp = ''
        self.received_info, self.received_path, self.received_error = None, '', ''
        self.active_slots = [] if discover else [i for i, s in enumerate(self.slots) if s and s.get('species')]
        self.logs.clear()
        self.notify()
        try:
            if self._storage_error:
                raise ValueError(self._storage_error)
            # Setup replaces its settings object when keys or the device are configured.
            if problem := await asyncio.to_thread(validate_keys, self.setup.settings.keys):
                raise ValueError(problem)
            if self.setup.radio_state != 'ready' or not self.setup.device:
                raise ValueError('Configura el módulo inalámbrico antes de iniciar.')
            run_folder = DATA / 'portable' / 'runs' / uuid.uuid4().hex
            run_folder.mkdir(parents=True, mode=0o700)
            files = []
            if discover:
                info = await asyncio.to_thread(command.courtesy_offer, self.game, self.trainer, VERSIONS.get(self.version, ''))
                candidates = [(None, info)]
            else:
                candidates = [(i, self.results[i]) for i in self.active_slots]
            for index, info in candidates:
                data = await asyncio.to_thread(Path(info['file']).read_bytes)
                if index is not None and hashlib.sha256(data).hexdigest() != self._hashes[index]:
                    self._invalidate(index)
                    raise ValueError('El archivo cambió después de validarlo. Vuelve a validar la caja.')
                checked = await asyncio.to_thread(self.service.check_bytes, self.game, data)
                if checked.get('legal') is not True:
                    if index is not None:
                        self.states[index] = 'invalid'
                        self.errors[index] = str(checked.get('report') or 'Pokémon no legal.').splitlines()[0]
                    raise ValueError('PKHeX bloqueó una oferta no legal.')
                target = run_folder / f'{len(files) + 1}.{pokemon.EXTENSIONS[self.game]}'
                target.write_bytes(data)
                target.chmod(0o600)
                files.append(target)
            tool = self.tools[self.role]
            if self.return_original and not any(f.key == '--trade-back' for f in tool.fields):
                raise ValueError('Esta herramienta no admite devolver el original.')
            values = self._values(tool, files)
            if problems := command.problems(tool, values):
                raise ValueError(str(problems[0]))
            for field in tool.fields:
                if field.kind in ('code', 'linkcode') and (problem := command.code_error(field, values.get(field.key, ''), self.game)):
                    raise ValueError(problem)
            run_settings = deepcopy(self.setup.settings)
            self._received_folder = run_settings.received
            run_settings.allow_illegal = False
            run_settings.radio = ''  # portable only uses the configured USB radio
            # Keep selected original trainer and use the matching displayed ID representation in the launcher.
            raw = self.trainer
            tid, sid = console_trainer.shown(self.game, raw['tid'], raw['sid'])
            run_settings.per_game_trainer = True
            run_settings.played[self.game] = self.version
            run_settings.game_trainers[self.version] = {**raw, 'tid': tid, 'sid': sid}
            stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
            self.run_stamp = stamp
            args = command.build(tool, values, {}, run_settings, stamp)
            SESSION.mkdir(parents=True, exist_ok=True)
            Path(run_settings.received).expanduser().mkdir(parents=True, exist_ok=True)
            if self.stop_requested:
                self._exited(None)
                return
            loop = asyncio.get_running_loop()
            self.phase = 'running'
            self.log('Iniciando intercambio local. Esperando a la consola.')
            self.process = self.process_factory(['--run', tool.script, *args], str(SESSION),
                self._run_env(run_settings),
                lambda line: loop.call_soon_threadsafe(self._line, line),
                lambda code: loop.call_soon_threadsafe(self._exited, code),
                popups=self.popups, label='Intercambios · Equipo')
            if discover:
                asyncio.create_task(self._watch_received(stamp, run_settings.received))
        except Exception as exc:
            self.error = self.redact(error_message(exc))
            self.log(self.error)
            self._exited(-1)
        finally:
            self.notify()

    def _line(self, line):
        self.log(line)
        if self.discovering and self.return_original and line.startswith("[trade-back] the console's Pokemon was not kept:"):
            self.error = 'pokeLDN no conservó el original para devolverlo. Revisa los logs y la consola.'
            self.stop()
            return
        count = received.trades_done(line)
        if count is not None:
            expected = (2 if self.return_original else 1) if self.discovering else len(self.active_slots)
            self.completed = max(self.completed, min(count, expected))
        if self.discovering and not self.found_trainer and (found := console_trainer.read(line)) and found.get('game') == self.game:
            if found.get('source') in ('session', 'pokemon'):
                self.found_trainer = found
        self.notify()

    async def _learn_received_trainer(self, stamp, folder):
        if self.found_trainer or self.game not in console_trainer.GAME_VERSIONS:
            return
        files = await asyncio.to_thread(received.session_files, folder, stamp)
        if not files:
            return
        try:
            data = await asyncio.to_thread(Path(files[0]).read_bytes)
            owner = await asyncio.to_thread(self.service.owner, self.game, data)
            found = console_trainer.own(self.game, owner)
        except (OSError, ValueError, pokemon.BuilderError):
            return  # A growing/unreadable record is retried at process exit.
        if self.run_stamp == stamp and not self.found_trainer and found:
            self.found_trainer = dict(found, game=self.game, source='pokemon')

    async def _finish_discovery(self, stamp, code):
        try:
            await self._learn_received_trainer(stamp, self._received_folder)
        finally:
            if self.run_stamp == stamp:
                self._exited(code, trainer_checked=True)

    async def _watch_received(self, stamp, folder):
        # Read only the first saved record of this run. The native trade-back
        # owns the original bytes; this metadata is never used as an offer.
        while self.run_stamp == stamp:
            files = await asyncio.to_thread(received.session_files, folder, stamp)
            if files and self.completed:
                if self.discovering:
                    await self._learn_received_trainer(stamp, folder)
                try:
                    data = await asyncio.to_thread(Path(files[0]).read_bytes)
                    info = await asyncio.to_thread(self.service.check_bytes, self.game, data)
                except (OSError, ValueError, pokemon.BuilderError):
                    info = None
                if self.run_stamp != stamp:
                    return
                self.received_path = files[0]
                if info is not None:
                    self.received_info = info
                    self.notify()
                    return
            if not self.busy:
                if self.completed and self.received_info is None:
                    self.received_error = 'No se pudo mostrar el archivo recibido. Revisa los logs y la carpeta Received.'
                    self.notify()
                return
            await asyncio.sleep(.3)

    def _exited(self, code, *, trainer_checked=False):
        if (self.discovering and self.completed and not self.found_trainer
                and self.game in console_trainer.GAME_VERSIONS and not trainer_checked):
            # Keep the radio/session locked until the final saved record is read.
            asyncio.get_running_loop().create_task(self._finish_discovery(self.run_stamp, code))
            return
        if self.discovering and self.completed and self.found_trainer:
            found = self.found_trainer
            try:
                profile = {k: found[k] for k in ('ot', 'tid', 'sid', 'gender', 'language')}
                if (not profile['ot'] or any(type(profile[k]) is not int or not 0 <= profile[k] <= 65535 for k in ('tid', 'sid'))
                        or profile['gender'] not in (0, 1)
                        or profile['language'] not in (settings_module.TRAINER_LANGUAGES | ({11} if self.game == 'za' else set()))):
                    raise ValueError('Datos de entrenador incompletos.')
                key = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()[:16]
                self.profiles[key] = profile
                self.selected_trainer = key
                for i in range(6):
                    self._invalidate(i)
                self.save()
            except (KeyError, ValueError, OSError) as exc:
                self.error = f'No se guardó el entrenador: {exc}'
        elif self.discovering and not self.stop_requested and not self.error:
            self.error = 'No se pudo identificar un entrenador compatible en un intercambio confirmado.'
        expected = (2 if self.return_original else 1) if self.discovering else len(self.active_slots)
        self.phase = ('stopped' if self.stop_requested else 'done' if code == 0 and self.completed == expected and not self.error else 'error')
        if self.phase == 'error' and not self.error:
            self.error = 'La sesión terminó sin confirmar todos los intercambios. Revisa los logs y la consola.'
        self.busy = self.setup.session_busy = False
        self.setup.active_team = None
        self.process = None
        if self.return_pending:
            self.log('Devolución pendiente: no se confirmó el segundo intercambio. '
                     'Conserva los archivos de Received; no hay reanudación automática.')
        self.notify()
        if self.discovering and self.completed and self.found_trainer and not self.error:
            asyncio.get_running_loop().create_task(self.validate_all())

    def stop(self):
        if not self.busy:
            return
        self.stop_requested, self.phase = True, 'stopping'
        self.log('Cancelación solicitada. Esperando el cierre; un intercambio confirmado no se revierte.')
        if self.process:
            self.process.stop()


def shared_team(game, setup):
    if not hasattr(setup, 'teams'):
        setup.teams = {}
    if game not in setup.teams:
        setup.teams[game] = Team(game, setup)
    return setup.teams[game]
