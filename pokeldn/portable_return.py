"""Private, nonblocking hand-off for a portable receive/edit/return session.

The native transport keeps servicing packets while ``current`` is None. Only the
original record held in memory may bypass legality; edited records are checked in
this child as well as by the UI. No file named by an IPC message is ever opened.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import threading

from pokeldn import pokemon


# Enable a pair only after its adapter has a nonblocking pending-offer path.
SUPPORTED = frozenset(
    (game, role)
    for game in ('frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv')
    for role in ('host', 'join')
)
SUPPORTED_SCRIPTS = frozenset(
    f'{game}_host.py' for game in ('lgpe', 'swsh', 'bdsp', 'pla', 'sv')
) | {
    'frlg_trade_host.py', 'frlg_trade_join.py', 'lgpe_join.py',
    'swsh_connect.py', 'bdsp_connect.py', 'pla_join.py', 'sv_join.py',
}


def supports(game, role):
    return (game, role) in SUPPORTED


def _atomic(path, data):
    temporary = path.with_name(path.name + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _read(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Return response is too large.')
    return data


class ReturnGate:
    def __init__(self, folder, game, log=print, check=None):
        self.folder = Path(folder)
        if self.folder.is_symlink() or not self.folder.is_dir():
            raise ValueError('A private return session directory is required.')
        self.game, self.log = game, log
        self.check = check or pokemon.SERVICE.check_bytes
        self.original = None
        self.digest = None
        self.result = None
        self.error = ''
        self.closed = threading.Event()
        self.worker = None
        self.session = None
        self.bindings = {}

    @classmethod
    def from_environment(cls, game, log=print):
        folder = os.environ.get('POKELDN_RETURN_DIR')
        if not folder:
            return None
        if game != os.environ.get('POKELDN_RETURN_GAME'):
            raise ValueError('Return session game does not match the native transport.')
        # A native run owns this directory once, including across reconnects.
        fd = os.open(Path(folder) / "native.claim", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        return cls(folder, game, log)

    def bind(self, identity, *, key="session"):
        """Fail closed if a reused adapter sees another native participant/session."""
        if key in self.bindings and self.bindings[key] != identity:
            self.close()
            self.result = None
            raise ValueError('The original native return session ended; reconnect is not permitted.')
        self.bindings[key] = identity
        if key == "session":
            self.session = identity

    def _status(self, state, error=''):
        _atomic(self.folder / 'status.json', json.dumps(
            {'state': state, 'sha256': self.digest, 'error': error}).encode())

    def begin(self, original):
        if self.original is not None or (self.folder / 'request.json').exists():
            raise ValueError('A return session cannot be reused for another original.')
        self.original = bytes(original)
        if not self.original or len(self.original) > pokemon.RECORD_LIMIT:
            raise ValueError('Invalid original record size.')
        self.digest = hashlib.sha256(self.original).hexdigest()
        _atomic(self.folder / 'original.bin', self.original)
        _atomic(self.folder / 'request.json', json.dumps(
            {'game': self.game, 'sha256': self.digest, 'size': len(self.original)}).encode())
        self._status('waiting')
        self.log('[portable-return] received')
        self.worker = threading.Thread(target=self._wait, daemon=True, name='portable-return')
        self.worker.start()

    def current(self):
        return None if self.closed.is_set() else self.result

    def _answer(self, message):
        if not isinstance(message, dict) or message.get('sha256') != self.digest:
            raise ValueError('Return response does not match the received original.')
        action = message.get('action')
        if action == 'original':
            return self.original
        if action != 'edited':
            raise ValueError('Unknown return action.')
        candidate = _read(self.folder / 'edited.bin', pokemon.RECORD_LIMIT)
        if hashlib.sha256(candidate).hexdigest() != message.get('candidate_sha256'):
            raise ValueError('Edited record changed before dispatch.')
        reply = self.check(self.game, candidate)
        if reply.get('legal') is not True:
            raise ValueError('The edited record is not legal; return the original or correct the edit.')
        result = pokemon.offer_bytes(self.game, base64.b64decode(reply['data'], validate=True))
        if self.game == 'frlg':
            from pokeldn.frlg.save.mon import Mon
            result = Mon.from_pk3(result).raw
        if len(result) != len(self.original):
            raise ValueError('Edited record does not match the native return format.')
        return result

    def _wait(self):
        previous = None
        while not self.closed.is_set():
            try:
                raw = _read(self.folder / 'response.json', 4096)
                if raw != previous:
                    previous = raw
                    result = self._answer(json.loads(raw))
                    if self.closed.is_set():
                        return
                    self.error = ''
                    self._status('ready')
                    self.result = result
                    self.log('[portable-return] ready')
                    return
            except FileNotFoundError:
                pass
            except (OSError, ValueError, KeyError, TypeError, pokemon.BuilderError):
                self.error = 'Return response rejected. Correct the edit or return the original.'
                try:
                    self._status('error', self.error)
                except OSError:
                    pass
                self.log('[portable-return] error: ' + self.error)
            self.closed.wait(.1)

    def close(self):
        self.closed.set()
