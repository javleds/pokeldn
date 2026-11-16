"""Only confirmed, complete current-run records enter the portable bank."""
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gui.portable_bank import PortableBank
from gui.portable_bank_capture import ReceiptCapture, receipt_ordinal
from gui.portable_received import ReceivedTeam
from gui.portable_team import Team, TeamStore
from pokeldn.app.settings import Settings


class Service:
    def check_bytes(self, game, data):
        return dict(species='Magikarp', species_id=129, level=5, legal=False)
    def owner(self, game, data):
        return dict(ot='RED', tid=1, sid=2, language=2, gender=0, version=4)


def capture(tmp_path, service=None, game='frlg'):
    folder = tmp_path / 'received'
    folder.mkdir(exist_ok=True)
    tasks, logs = set(), []
    return ReceiptCapture(game, 'run', str(folder), PortableBank(tmp_path / 'bank'),
                          service or Service(), tasks, logs.append)


@pytest.mark.parametrize('name,ordinal', [
    ('frlg-run.pk3', 1), ('frlg-run-2.pk3', 2),
    ('frlg-run_3.pk3', 3), ('frlg-run_trade2_Pikachu.pk3', 2),
    ('frlg-run-preview.pk3', None), ('other-run.pk3', None),
    ('frlg-run_trade0_Pikachu.pk3', None), ('frlg-old-run.pk3', None),
])
def test_only_known_current_run_filenames_have_trade_ordinals(name, ordinal):
    assert receipt_ordinal(name, 'frlg', 'run') == ordinal


def test_confirmation_gates_all_receipts_and_excludes_previews(tmp_path):
    cap = capture(tmp_path)
    folder = Path(cap.folder)
    (folder / 'frlg-run.pk3').write_bytes(b'a' * 100)
    (folder / 'frlg-run-2.pk3').write_bytes(b'b' * 100)
    (folder / 'frlg-run-3.pk3').write_bytes(b'c' * 100)
    (folder / 'frlg-run-preview.pk3').write_bytes(b'd' * 100)
    async def scenario():
        cap.schedule(0)
        await cap.drain()
        assert cap.library.list() == []
        cap.schedule(1)
        await cap.drain()
        rows = cap.library.list()
        assert len(rows) == 1 and cap.library.data(rows[0]['id']) == b'a' * 100
        cap.schedule(2)
        await cap.drain()
        assert {cap.library.data(row['id']) for row in cap.library.list()} == {b'a' * 100, b'b' * 100}
    asyncio.run(scenario())


def test_late_write_and_final_scan_capture_without_recreating_deleted_entries(tmp_path):
    cap = capture(tmp_path)
    path = Path(cap.folder) / 'frlg-run.pk3'
    async def scenario():
        cap.schedule(1)
        await asyncio.sleep(.03)
        path.write_bytes(b'a' * 100)
        await cap.drain()
        row = cap.library.list()[0]
        cap.library.delete(row['id'])
        cap.schedule(1)
        await cap.drain()
        assert cap.library.list() == []
    asyncio.run(scenario())


def test_duplicate_numbered_frlg_files_do_not_consume_next_confirmed_receipt(tmp_path):
    cap = capture(tmp_path)
    for name, data in [('frlg-run.pk3', b'a' * 100),
                       ('frlg-run_trade1_Magikarp.pk3', b'a' * 100),
                       ('frlg-run_trade2_Zubat.pk3', b'b' * 100)]:
        (Path(cap.folder) / name).write_bytes(data)
    async def scenario():
        cap.schedule(2)
        await cap.drain()
    asyncio.run(scenario())
    assert len(cap.library.list()) == 2


def test_incomplete_record_not_archived_and_analysis_failure_preserves_raw(tmp_path):
    class Broken(Service):
        def check_bytes(self, *args):
            raise ValueError('unreadable')
        def owner(self, *args):
            raise ValueError('unreadable')
    cap = capture(tmp_path, Broken())
    async def scenario():
        assert not await cap.original(b'short')
        assert await cap.original(b'x' * 100)
        await cap.drain()
    asyncio.run(scenario())
    row = cap.library.list()[0]
    assert cap.library.data(row['id']) == b'x' * 100
    assert row['species'] == 'Desconocido'
    assert row['legal'] is False


def test_team_done_and_exit_capture_every_confirmed_record(tmp_path):
    library = PortableBank(tmp_path / 'bank')
    folder = tmp_path / 'received'
    folder.mkdir()
    setup = SimpleNamespace(settings=Settings(received=str(folder)), bank_library=library,
                            busy=False, checking=False, session_busy=False, active_team=None)
    team = Team('frlg', setup, store=TeamStore('frlg', tmp_path / 'teams'), service=Service())
    team.run_stamp = 'run'
    team.active_slots = [0, 1]
    team._begin_bank_capture('run', str(folder))
    async def scenario():
        (folder / 'frlg-run.pk3').write_bytes(b'a' * 100)
        team._line('[done] trade 1 complete')
        await team._bank_capture.drain()
        # The final receipt can arrive between the last done event and process exit.
        team._line('[done] trade 2 complete')
        (folder / 'frlg-run-2.pk3').write_bytes(b'b' * 100)
        team._exited(0)
        await team._bank_capture.drain()
    asyncio.run(scenario())
    assert len(library.list()) == 2


def test_received_gate_archives_before_analysis_failure_and_original_return(tmp_path, monkeypatch):
    import gui.portable_received as received_module
    monkeypatch.setattr(received_module, 'DATA', tmp_path)
    library = PortableBank(tmp_path / 'bank')
    data = b'x' * 100
    class Broken(Service):
        def edit_received(self, *args):
            rows = library.list()
            assert len(rows) == 1 and library.data(rows[0]['id']) == data
            raise ValueError('analysis failed')
    setup = SimpleNamespace(settings=Settings(received=str(tmp_path / 'received')),
                            bank_library=library, busy=False, checking=False,
                            session_busy=True, active_team=None)
    team = ReceivedTeam('frlg', setup, 'validator', service=Broken(),
                        store=TeamStore('frlg', tmp_path / 'teams'))
    team.run_stamp = 'run'
    team.active = team.busy = True
    team.return_dir = tmp_path / 'return'
    team.return_dir.mkdir()
    team._begin_bank_capture('run', str(tmp_path / 'received'))
    (team.return_dir / 'original.bin').write_bytes(data)
    (team.return_dir / 'request.json').write_text(json.dumps({
        'game': 'frlg', 'sha256': hashlib.sha256(data).hexdigest()}))
    async def scenario():
        await team._watch_received('run', str(tmp_path / 'received'))
        await team._bank_capture.drain()
    asyncio.run(scenario())
    assert json.loads((team.return_dir / 'response.json').read_text())['action'] == 'original'
    assert library.data(library.list()[0]['id']) == data


def test_ordinary_team_does_not_inherit_exact_bank_offer_environment(tmp_path, monkeypatch):
    setup = SimpleNamespace(settings=Settings(), device='fixture',
                            busy=False, checking=False, session_busy=False, active_team=None)
    team = Team('frlg', setup, store=TeamStore('frlg', tmp_path / 'teams'), service=Service())
    monkeypatch.setenv('POKELDN_EXACT_OFFER_GAME', 'sv')
    monkeypatch.setenv('POKELDN_EXACT_OFFER_SHA256', 'old')
    env = team._run_env(setup.settings)
    assert 'POKELDN_EXACT_OFFER_GAME' not in env
    assert 'POKELDN_EXACT_OFFER_SHA256' not in env


def test_storage_failure_is_reported_without_blocking_return_flow(tmp_path):
    cap = capture(tmp_path)
    def full(*args):
        raise OSError('disk full')
    cap.library.deposit = full
    async def scenario():
        assert await cap.original(b'a' * 100) is False
        await cap.drain()
    asyncio.run(scenario())
    assert cap.library.list() == []
