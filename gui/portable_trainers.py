"""Portable trainer library over the existing per-game TeamStore profiles."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from pokeldn import console_trainer
from pokeldn.app import settings

GAMES = ('frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za')
GAME_LABELS = {
    'frlg': 'Rojo/Verde', 'lgpe': "Let's Go", 'swsh': 'Espada/Escudo',
    'bdsp': 'Diamante/Perla', 'pla': 'Arceus', 'sv': 'Escarlata/Púrpura', 'za': 'Z-A',
}
GAME_FOLDERS = {
    'frlg': 'rojo_verde', 'lgpe': 'lets_go', 'swsh': 'espada_escudo',
    'bdsp': 'diamante_perla', 'pla': 'arceus', 'sv': 'escarlata_purpura', 'za': 'za',
}
LANGUAGES = {1: 'JA', 2: 'EN', 3: 'FR', 4: 'IT', 5: 'DE', 7: 'ES',
             8: 'KO', 9: 'ZH-S', 10: 'ZH-T', 11: 'ES-LA'}
PROFILE_FIELDS = ('ot', 'tid', 'sid', 'gender', 'language')
IMPORT_LIMIT = 2 * 1024 * 1024
MAX_ENTRIES = 2000
TYPE = 'pokeldn.portable.trainer'


def profile_id(profile):
    """Match the identity used when Team saves an identified trainer."""
    core = {key: profile[key] for key in PROFILE_FIELDS}
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]


def _safe_name(value):
    ascii_value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9_-]+', '_', ascii_value).strip('_-') or 'trainer'


def export_filename(entry):
    """Relative game folder plus portable filename; no user text becomes a path."""
    game, profile = entry['game'], entry['profile']
    tid, sid = console_trainer.shown(game, profile['tid'], profile['sid'])
    folder = GAME_FOLDERS[game]
    language = LANGUAGES[profile['language']].lower()
    return Path(folder) / f"{folder}_{_safe_name(profile['ot'])}_{tid}_{sid}_{language}.json"


def _validate_entry(value):
    if not isinstance(value, dict) or set(value) != {'schema', 'type', 'game', 'game_version', 'profile'}:
        raise ValueError('Registro de entrenador incompleto o con campos desconocidos.')
    if type(value['schema']) is not int or value['schema'] != 1 or value['type'] != TYPE:
        raise ValueError('Formato de entrenadores no compatible.')
    game = value['game']
    if not isinstance(game, str) or game not in GAMES:
        raise ValueError('Juego de entrenador no disponible.')
    version = value['game_version']
    versions = {key for key, _ in settings.VERSIONS.get(game, ())} or {game}
    if version is not None and (not isinstance(version, str) or version not in versions):
        raise ValueError('Versión de juego incompatible.')
    profile = value['profile']
    if not isinstance(profile, dict) or set(profile) != set(PROFILE_FIELDS):
        raise ValueError('Datos de entrenador incompletos.')
    ot = profile['ot']
    if not isinstance(ot, str) or not ot.strip() or any(unicodedata.category(c).startswith('C') for c in ot):
        raise ValueError('Nombre de entrenador no válido.')
    for name in ('tid', 'sid'):
        if type(profile[name]) is not int or not 0 <= profile[name] <= 65535:
            raise ValueError('Los IDs deben ser enteros originales de 16 bits.')
    if type(profile['gender']) is not int or profile['gender'] not in (0, 1):
        raise ValueError('Género de entrenador no válido.')
    language = profile['language']
    allowed = settings.TRAINER_LANGUAGES | ({11} if game == 'za' else set())
    if game == 'frlg':
        allowed = {1, 2, 3, 4, 5, 7}
    if type(language) is not int or language not in allowed:
        raise ValueError('Idioma de entrenador no válido para el juego.')
    limit = (5 if language == 1 else 7) if game == 'frlg' else 12
    if len(ot) > limit:
        raise ValueError(f'El nombre de entrenador supera {limit} caracteres.')
    if game == 'frlg':
        from pokeldn.frlg.text import charmap
        encoded = charmap.encode(ot, language=language)
        if charmap.decode(encoded, language=language) != ot or len(encoded) > limit:
            raise ValueError('El nombre no se puede representar en Gen III.')
    return dict(id=profile_id(profile), game=game, game_version=version, profile=deepcopy(profile))


class TrainerLibrary:
    def __init__(self, setup, teams=None):
        self.setup = setup
        self._teams = teams

    def _team(self, game):
        if self._teams is not None:
            return self._teams[game]
        from gui.portable_team import shared_team
        return shared_team(game, self.setup)

    def _games(self):
        return tuple(self._teams) if self._teams is not None else GAMES

    def _editable(self, games):
        if any(getattr(self.setup, field, False) for field in ('busy', 'checking', 'session_busy')):
            raise ValueError('Espera a que termine la sesión o comprobación.')
        for game in games:
            team = self._team(game)
            if team.busy:
                raise ValueError('El intercambio está en curso.')
            if team._storage_error:
                raise ValueError(team._storage_error)

    def entries(self, query='', game=''):
        if game and game not in self._games():
            raise ValueError('Juego de entrenador no disponible.')
        found = []
        for key in self._games():
            if game and key != game:
                continue
            team = self._team(key)
            if team._storage_error:
                raise ValueError(team._storage_error)
            for entry_id, profile in team.profiles.items():
                if entry_id == 'base':
                    continue
                row = dict(id=entry_id, game=key, game_version=profile.get('game_version'),
                           profile={field: profile[field] for field in PROFILE_FIELDS})
                tid, sid = console_trainer.shown(key, profile['tid'], profile['sid'])
                haystack = f"{key} {GAME_FOLDERS[key]} {profile['ot']} {tid} {sid} {LANGUAGES.get(profile['language'], '')}"
                if query.casefold() in haystack.casefold():
                    found.append(row)
        return sorted(found, key=lambda row: (row['game'], row['profile']['ot'].casefold(), row['id']))

    def export_json(self, entries=None):
        rows = self.entries() if entries is None else entries
        output = []
        for row in rows:
            entry = dict(schema=1, type=TYPE, game=row['game'], game_version=row.get('game_version'),
                         profile=deepcopy(row['profile']))
            _validate_entry(entry)
            output.append(entry)
        return json.dumps(output, ensure_ascii=False, indent=2).encode('utf-8')

    def import_json(self, data):
        if not isinstance(data, bytes) or not data or len(data) > IMPORT_LIMIT:
            raise ValueError('Selecciona JSON de entrenadores de hasta 2 MiB.')
        try:
            values = json.loads(data)
        except (ValueError, UnicodeError) as exc:
            raise ValueError('JSON de entrenadores no válido.') from exc
        if not isinstance(values, list) or len(values) > MAX_ENTRIES:
            raise ValueError('El archivo debe ser un array de hasta 2000 entrenadores.')
        rows = [_validate_entry(value) for value in values]
        games = {row['game'] for row in rows}
        if not games <= set(self._games()):
            raise ValueError('Juego de entrenador no disponible.')
        self._editable(games)
        added = 0
        for game in sorted(games):
            team = self._team(game)
            previous = deepcopy(team.profiles)
            known = {profile_id(p) for key, p in team.profiles.items() if key != 'base'}
            changed = 0
            for row in rows:
                if row['game'] != game or row['id'] in known:
                    continue
                profile = deepcopy(row['profile'])
                if row['game_version'] is not None:
                    profile['game_version'] = row['game_version']
                team.profiles[row['id']] = profile
                known.add(row['id'])
                changed += 1
            if not changed:
                continue
            try:
                team.save()
            except (OSError, ValueError):
                team.profiles = previous
                raise
            added += changed
            team.notify()
        return added

    def delete(self, game, entry_id):
        if game not in self._games():
            raise ValueError('Juego de entrenador no disponible.')
        self._editable((game,))
        team = self._team(game)
        if entry_id == 'base' or entry_id not in team.profiles:
            raise ValueError('Entrenador desconocido.')
        previous = deepcopy(team.profiles)
        selected = team.selected_trainer
        del team.profiles[entry_id]
        if selected == entry_id:
            team.selected_trainer = 'base'
        try:
            team.save()
        except (OSError, ValueError):
            team.profiles, team.selected_trainer = previous, selected
            raise
        if selected == entry_id:
            for index in range(6):
                team._invalidate(index)
            team.metadata.clear()
        team.notify()
