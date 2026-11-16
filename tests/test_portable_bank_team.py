import asyncio
import base64
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gui.portable_bank_team import BankTeam
from pokeldn.app.settings import Settings
from tests.test_portable_received import Service


@pytest.fixture
def model():
    settings = Settings()
    setup = SimpleNamespace(settings=settings, busy=False, checking=False,
                            session_busy=False, active_team=None, demo=False)
    service = Service()
    bank = BankTeam('sv', setup, b'original bytes', edit=True, service=service)
    bank.load_options = AsyncMock(return_value={})
    yield bank
    bank.dispose()


def test_load_and_edit_keep_original_owner_and_bytes(model):
    async def scenario():
        await model.load_original()
        assert model.can_start
        assert Path(model.results[0]['file']).read_bytes() == b'original bytes'
        assert model.trainer['ot'] == 'Original'
        model.edit(0, 'level', '20')
        assert not model.can_start
        await model.validate(0)
        assert model.can_start
        assert model.service.edits[-1] == (b'original bytes', {'level': 20})
        assert Path(model.results[0]['file']).read_bytes() == b'edited'
        assert model.original == b'original bytes'
        assert model.trainer['ot'] == 'Original'
    asyncio.run(scenario())


def test_original_send_ignores_editor_input_and_never_serializes_original(model):
    model.edit_enabled = False
    asyncio.run(model.load_original())
    old = deepcopy(model.slots)
    model.edit(0, 'nickname', 'Changed')
    assert model.slots == old
    assert Path(model.results[0]['file']).read_bytes() == model.original
    assert all(not changes for _, changes in model.service.edits)
    assert model.slot_available(0) and not model.slot_available(1)


def test_illegal_original_cannot_start_new_bank_trade(model):
    model.service.legal = False
    asyncio.run(model.load_original())
    assert not model.can_start
    assert model.states[0] == 'invalid'


def test_bank_does_not_write_source_equipo_state(model):
    source = SimpleNamespace(profiles={'a': {'ot': 'Source'}}, selected_trainer='a',
                             role='host', version='scarlet', code='12345678',
                             slots=[{'species': 25}] + [None] * 5)
    before = deepcopy(vars(source))
    bank = BankTeam('sv', model.setup, b'original', source_team=source, service=model.service)
    bank.code = '87654321'
    bank.save()
    assert vars(source) == before
    assert bank.slots == [None] * 6
    bank.dispose()


def test_stale_validation_cannot_enable_newer_draft(model, monkeypatch):
    import threading
    entered, release = threading.Event(), threading.Event()
    original = model.service.edit_received
    asyncio.run(model.load_original())
    def delayed(game, data, changes):
        if changes.get('level') == 20:
            entered.set()
            release.wait(3)
        return original(game, data, changes)
    monkeypatch.setattr(model.service, 'edit_received', delayed)
    async def scenario():
        model.edit(0, 'level', '20')
        task = asyncio.create_task(model.validate(0))
        await asyncio.to_thread(entered.wait, 3)
        model.edit(0, 'level', '30')
        release.set()
        await task
        assert not model.can_start
        await model.validate(0)
        assert model.can_start
        assert model.service.edits[-1][1] == {'level': 30}
    asyncio.run(scenario())


def test_launch_scope_hashes_current_candidate_and_rejects_tampering(model, monkeypatch):
    import hashlib
    from gui import portable_team
    monkeypatch.setattr(portable_team.runner, 'base_env', lambda *args: {'EXISTING': 'value'})
    model.setup.device = 'fixture-device'
    asyncio.run(model.load_original())
    env = model._run_env(model.settings)
    assert env['POKELDN_EXACT_OFFER_GAME'] == 'sv'
    assert env['POKELDN_EXACT_OFFER_SHA256'] == hashlib.sha256(model.original).hexdigest()
    assert env['EXISTING'] == 'value'
    Path(model.results[0]['file']).write_bytes(b'changed externally')
    with pytest.raises(ValueError, match='cambió'):
        model._run_env(model.settings)


def test_dispose_cancels_pending_validation_and_keeps_candidate_folder_deleted(model, monkeypatch):
    import threading
    entered, release = threading.Event(), threading.Event()
    asyncio.run(model.load_original())
    original = model.service.edit_received
    def delayed(game, data, changes):
        entered.set()
        release.wait(3)
        return original(game, data, changes)
    monkeypatch.setattr(model.service, 'edit_received', delayed)
    async def scenario():
        model.edit(0, 'level', '20')
        task = asyncio.create_task(model.validate(0))
        await asyncio.to_thread(entered.wait, 3)
        folder = Path(model._candidate_folder.name)
        model.dispose()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert model.disposed and not model.can_start
        assert not folder.exists()
        assert not model._tasks and not model._metadata_tasks and not model._move_tasks
        assert model.results == [{} for _ in range(6)]
        await model.validate(0)
        await model.start()
        await model.load_original()
        assert not folder.exists()
        assert model.slots == [None] * 6
    asyncio.run(scenario())


def test_dispose_during_original_load_drops_late_result(model, monkeypatch):
    import threading
    entered, release = threading.Event(), threading.Event()
    original = model.service.edit_received
    def delayed(game, data, changes):
        entered.set()
        release.wait(3)
        return original(game, data, changes)
    monkeypatch.setattr(model.service, 'edit_received', delayed)
    async def scenario():
        task = asyncio.create_task(model.load_original())
        await asyncio.to_thread(entered.wait, 3)
        model.dispose()
        release.set()
        await task
        assert model.original_owner is None
        assert model.slots == [None] * 6
        assert not model.can_start
        assert not Path(model._candidate_folder.name).exists()
    asyncio.run(scenario())
