import asyncio
import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gui.portable_received import ReceivedTeam, atomic_write
from gui.portable_team import TeamStore
from pokeldn.app.settings import Settings


class Service:
    def __init__(self):
        self.legal = True
        self.edits = []
    def edit_received(self, game, data, fields):
        self.edits.append((bytes(data), fields))
        snapshot = dict(species=7, level=5, nickname='', shiny=False, form=0,
                        moves=[33, 145, 0, 0], nature=0, friendship=70,
                        effort={s: 0 for s in ('hp', 'atk', 'def', 'spa', 'spd', 'spe')})
        snapshot.update(fields)
        return dict(data=base64.b64encode(b'edited' if fields else data).decode(),
                    editable=snapshot, legal=self.legal, report='Legal' if self.legal else 'Invalid\nOther error',
                    species='Squirtle', species_id=7, level=snapshot['level'], ot='Original')
    def move_options(self, game, species, trainer, level, shiny, version, options):
        return [33, 145]

    def owner(self, game, data):
        return dict(ot='Original', tid=1, sid=2, gender=0, language=7)
    def check_bytes(self, game, data):
        return {'legal': self.legal}


@pytest.fixture
def model(tmp_path, monkeypatch):
    import gui.portable_received as module
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module.portable_return, 'supports', lambda game, role: True)
    setup = SimpleNamespace(settings=Settings(), busy=False, checking=False, session_busy=True, active_team=None)
    m = ReceivedTeam('sv', setup, 'modifier', service=Service(), store=TeamStore('sv', tmp_path/'unused'))
    m.active = m.busy = True
    m.run_stamp = 'fixture'
    m.return_dir = tmp_path/'portable'/'returns'/'fixture'
    m.return_dir.mkdir(parents=True)
    m.load_options = AsyncMock(return_value={})
    return m


async def receive(m, data=b'original'):
    atomic_write(m.return_dir/'original.bin', data)
    atomic_write(m.return_dir/'request.json', json.dumps(dict(game=m.game, sha256=hashlib.sha256(data).hexdigest())).encode())
    await m._watch_received(m.run_stamp, '')


def test_modifier_edits_copy_and_keeps_original_and_trainer(model):
    async def scenario():
        await receive(model)
        assert model.phase == 'editing' and not model.busy and model.setup.session_busy
        assert model.trainer['ot'] == 'Original'
        model.edit(0, 'level', '20')
        await model.validate(0)
        assert model.service.edits[-1] == (b'original', {'level': 20})
        assert model.original == b'original'
        assert (model.return_dir/'original.bin').read_bytes() == b'original'
        assert model.candidate_legal
        await model.return_edited_now()
        response = json.loads((model.return_dir/'response.json').read_text())
        assert response['action'] == 'edited'
        assert model.busy and model.phase == 'returning'
    asyncio.run(scenario())


def test_validator_returns_illegal_original_without_rebuilding(model):
    model.mode = 'validator'
    model.service.legal = False
    asyncio.run(receive(model))
    assert model.original_legal is False
    assert 'Other error' in model.report
    assert json.loads((model.return_dir/'response.json').read_text())['action'] == 'original'
    assert not (model.return_dir/'edited.bin').exists()


def test_illegal_edit_waits_for_original_fallback(model):
    async def scenario():
        model.mode = 'level'
        model.service.legal = False
        await receive(model)
        assert model.phase == 'review' and not model.busy
        await model.return_edited_now()
        assert not (model.return_dir/'response.json').exists()
        await model.return_original_now()
        assert json.loads((model.return_dir/'response.json').read_text())['action'] == 'original'
    asyncio.run(scenario())


def test_dirty_or_finally_invalid_copy_cannot_return(model):
    async def scenario():
        await receive(model)
        model.edit(0, 'level', 20)
        await model.return_edited_now()
        assert not (model.return_dir/'response.json').exists()
        await model.validate(0)
        model.service.legal = False
        await model.return_edited_now()
        assert not (model.return_dir/'response.json').exists()
        assert not model.busy
    asyncio.run(scenario())


def test_cancel_preserves_original_and_persistent_pending_record(model):
    async def scenario():
        await receive(model)
        model.completed = 1
        model.stop()
        model._exited(0)
        assert model.return_pending and model.phase == 'stopped'
        assert (model.return_dir/'original.bin').read_bytes() == b'original'
        assert json.loads((model.return_dir/'journal.json').read_text())['returned'] is False
        assert not model.setup.session_busy
    asyncio.run(scenario())


def test_second_confirmation_required_for_success(model):
    asyncio.run(receive(model))
    model.completed = 1
    model._exited(0)
    assert model.phase == 'error'
    model.completed = 2
    model._exited(0)
    assert model.phase == 'done'
    assert json.loads((model.return_dir/'journal.json').read_text())['returned'] is True


def test_tampered_original_blocks_return(model):
    async def scenario():
        await receive(model)
        (model.return_dir/'original.bin').write_bytes(b'tampered')
        await model.return_original_now()
        assert not (model.return_dir/'response.json').exists()
        assert 'cambió' in model.error
    asyncio.run(scenario())


def test_pre_run_parameters_reject_out_of_bounds(model):
    model.mode = 'level'
    model.params['level'] = '0'
    with pytest.raises(ValueError): model._parameter_fields()
    model.mode = 'effort'
    model.params['effort'] = {s: 252 for s in model.params['effort']}
    with pytest.raises(ValueError): model._parameter_fields()


from test_pokemon_service import TRAINER, service


@pytest.mark.parametrize('mode', ['evolution', 'level', 'nature', 'effort', 'modifier', 'validator'])
def test_modes_process_real_record_without_rebuilding_trainer(model, service, mode):
    model.mode = mode
    model.service = service
    built = service.make('sv', 25, TRAINER)
    data = base64.b64decode(built['data'])
    model.params['level'] = '100'
    model.params['nature'] = 3
    async def scenario():
        await receive(model, data)
        assert model.original == data
        assert model.original_owner['ot'] == TRAINER['ot']
        assert model.received_info['species_id'] == 25
        assert model.states[0] != 'validating'
        if mode == 'modifier':
            assert model.phase == 'editing' and model.candidate_legal
            model.edit(0, 'nickname', 'TEST')
            await model.validate(0)
            assert model.results[0]['editable']['nickname'] == 'TEST'
            assert model.results[0]['identity'] == service.edit_received('sv', data)['identity']
        else:
            assert model.phase == 'returning', model.error
            response = json.loads((model.return_dir/'response.json').read_text())
            assert response['action'] == ('original' if mode in ('evolution', 'validator') else 'edited')
    asyncio.run(scenario())


def test_demo_refusal_does_not_leave_active_session(model):
    model.active = model.busy = False
    model.setup.session_busy = False
    model.setup.demo = True
    asyncio.run(model.start())
    assert not model.active and not model.busy and model.phase == 'error'
    assert not model.setup.session_busy


def test_exit_releases_radio_even_when_journal_write_fails(model, monkeypatch):
    monkeypatch.setattr(model, '_journal', lambda: (_ for _ in ()).throw(OSError('disk full')))
    model._exited(-1)
    assert not model.setup.session_busy and model.setup.active_team is None
    assert model.process is None
    assert 'registro' in model.error


def test_stale_final_validation_cannot_publish_into_new_session(model, monkeypatch):
    import threading
    async def scenario():
        await receive(model)
        entered, release = threading.Event(), threading.Event()
        def check(*args):
            entered.set()
            release.wait(5)
            return {'legal': True}
        monkeypatch.setattr(model.service, 'check_bytes', check)
        old_directory = model.return_dir
        pending = asyncio.create_task(model.return_edited_now())
        await asyncio.to_thread(entered.wait, 5)
        model.run_stamp = 'new-session'
        model.return_dir = old_directory.parent/'new-session'
        model.return_dir.mkdir()
        model.active = True
        model.stop_requested = False
        release.set()
        await pending
        assert not (model.return_dir/'response.json').exists()
        assert not (old_directory/'response.json').exists()
    asyncio.run(scenario())


def test_reset_keeps_notice_of_pending_return(model):
    asyncio.run(receive(model))
    model.completed = 1
    model._exited(-1)
    journal = model.return_dir/'journal.json'
    model.reset()
    assert model.original is None and model.received_info is None
    assert journal in model.pending_receipts
    assert model.recovery_notice
    assert journal.exists()


@pytest.mark.parametrize('mode', ['evolution', 'validator'])
def test_unreadable_original_can_still_return_intact(model, monkeypatch, mode):
    model.mode = mode
    monkeypatch.setattr(model.service, 'edit_received', lambda *a: (_ for _ in ()).throw(ValueError('Cannot parse')))
    asyncio.run(receive(model))
    assert model.report == 'Cannot parse'
    assert model.original_legal is None
    assert json.loads((model.return_dir/'response.json').read_text())['action'] == 'original'


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv'])
def test_received_native_records_are_read_without_changing_original(model, service, game):
    from pokeldn import pokemon
    model.game = game
    model.mode = 'validator'
    model.service = service
    data = pokemon.offer_bytes(game, base64.b64decode(service.make(game, 25, TRAINER)['data']))
    if game == 'frlg':
        from pokeldn.frlg.save.mon import Mon
        data = Mon.from_pk3(data).raw
    asyncio.run(receive(model, data))
    assert model.received_info['species_id'] == 25, model.report
    assert model.original == data
    assert json.loads((model.return_dir/'response.json').read_text())['action'] == 'original'
