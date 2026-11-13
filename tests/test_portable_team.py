import asyncio
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from gui.portable_team import Team, TeamStore, local_tools
from pokeldn.app.settings import Settings


class Service:
    def __init__(self, folder):
        self.folder = folder
        self.legal = True
        self.count = 0
        self.calls = []

    def options(self, *args):
        return {'effort': {'kind': 'ev', 'max': 252, 'total': 510}, 'base': [90, 110, 80, 100, 80, 95]}

    def encounters(self, *args):
        return []

    def move_options(self, *args):
        return [33, 145]

    def make(self, game, species, trainer, level, shiny, nickname, version, options):
        self.count += 1
        path = self.folder / f'pokemon{self.count}.pk9'
        path.write_bytes(f'{species}:{level}:{nickname}'.encode())
        self.calls.append((trainer, level, options))
        return {'file': str(path), 'legal': self.legal, 'report': 'No legal\nOtro error'}

    def check_bytes(self, game, data):
        return {'legal': self.legal, 'report': 'No legal\nOtro error'}


@pytest.fixture
def team(tmp_path):
    s = Settings(keys='fixture.keys', received=str(tmp_path / 'received'))
    setup = SimpleNamespace(settings=s, busy=False, checking=False, session_busy=False,
                            active_team=None, demo=False, radio_state='ready', device='fixture-port')
    return Team('sv', setup, store=TeamStore('sv', tmp_path / 'drafts'), service=Service(tmp_path))


def prepare(team, index=0):
    team.add(index)
    team.edit(index, 'species', 59)
    asyncio.run(team.validate(index))


def test_draft_is_saved_but_legality_is_never_restored(team):
    prepare(team)
    assert team.can_start
    restored = Team('sv', team.setup, store=team.store, service=team.service)
    assert restored.slots[0]['species'] == 59
    assert restored.states[0] == 'pending'
    assert not restored.can_start
    assert restored.store.path.stat().st_mode & 0o777 == 0o600


def test_invalid_level_keeps_input_and_blocks_build(team):
    prepare(team)
    team.edit(0, 'level', '101')
    assert not team.can_start
    asyncio.run(team.validate(0))
    assert team.slots[0]['level'] == '101'
    assert team.states[0] == 'invalid'
    assert team.service.count == 1


def test_illegal_pokemon_never_enables_trade(team):
    team.service.legal = False
    prepare(team)
    assert team.states[0] == 'invalid'
    assert team.errors[0] == 'No legal'
    assert not team.can_start


def test_options_are_normalized_without_changing_draft(team):
    prepare(team)
    team.edit(0, 'effort', {'atk': '252', 'spe': '252', 'hp': '6'}, option=True)
    asyncio.run(team.validate(0))
    assert team.can_start
    assert team.service.calls[-1][2]['effort']['atk'] == 252
    assert team.slots[0]['options']['effort']['atk'] == '252'
    team.edit(0, 'effort', {'atk': '252', 'spe': '252', 'hp': '7'}, option=True)
    asyncio.run(team.validate(0))
    assert not team.can_start
    assert '510' in team.errors[0]


def test_slow_old_result_cannot_validate_new_revision(team):
    entered, release = threading.Event(), threading.Event()
    make = team.service.make
    def slow(*args):
        entered.set()
        release.wait(3)
        return make(*args)
    team.service.make = slow
    async def scenario():
        team.add(0)
        team.edit(0, 'species', 59)
        task = asyncio.create_task(team.validate(0))
        await asyncio.to_thread(entered.wait, 2)
        team.edit(0, 'nickname', 'Nuevo')
        release.set()
        await task
        assert team.states[0] == 'pending'
        assert team.results[0] == {}
        assert not team.can_start
    asyncio.run(scenario())


def test_all_occupied_slots_required_empty_slots_ignored(team):
    prepare(team, 0)
    prepare(team, 1)
    assert team.can_start
    team.add(2)
    assert team.can_start  # No species: this is not an offer yet.
    team.edit(2, 'species', 7)
    assert not team.can_start
    team.clear(2)
    assert team.can_start
    team.clear()
    assert not team.can_start


def test_boxes_unlock_only_after_species_and_blank_drafts_do_not_validate(team):
    assert [team.slot_available(i) for i in range(6)] == [True, False, False, False, False, False]
    team.edit(0, 'nickname', 'Shell')
    asyncio.run(team.validate_all())
    assert team.service.count == 0 and team.states[0] == 'empty' and team.errors[0] == ''
    with pytest.raises(ValueError, match='anterior'):
        team.edit(5, 'species', 7)
    for index in range(6):
        assert team.slot_available(index)
        team.edit(index, 'species', index + 1)
    assert all(team.slot_available(i) for i in range(6))
    assert team.slots[0]['nickname'] == 'Shell'


@pytest.mark.parametrize('removed', [0, 1, 2])
def test_clear_compacts_drafts_and_keeps_current_validation(team, removed):
    for index in range(3):
        team.edit(index, 'species', index + 1)
        team.edit(index, 'nickname', f'Pokemon {index}')
    asyncio.run(team.validate_all())
    before = [dict(slot) for slot in team.slots[:3]]
    files = [result.get('file') for result in team.results[:3]]
    team.clear(removed)
    assert team.slots[:2] == [slot for i, slot in enumerate(before) if i != removed]
    assert team.slots[2:] == [None] * 4
    assert [r['file'] for r in team.results[:2]] == [f for i, f in enumerate(files) if i != removed]
    assert team.can_start
    assert team.service.count == 3
    restored = Team('sv', team.setup, store=team.store, service=team.service)
    assert restored.slots == team.slots


def test_clearing_species_compacts_like_deleting_box(team):
    prepare(team)
    team.edit(1, 'species', 7)
    team.edit(0, 'species', None)
    assert team.slots[0]['species'] == 7
    assert team.slots[1:] == [None] * 5


def test_old_sparse_saved_team_is_ordered_without_losing_draft_fields(team):
    first = dict(species=7, nickname='Shell', level='10', options={})
    second = dict(species=25, nickname='Spark', level='20', options={})
    unfinished = dict(species=0, nickname='Draft', level='30', options={})
    team.store.save(dict(slots=[None, first, unfinished, None, second, None]))
    restored = Team('sv', team.setup, store=team.store, service=team.service)
    assert restored.slots == [first, second, unfinished, None, None, None]
    assert restored.states == ['pending', 'pending', 'empty', 'empty', 'empty', 'empty']


def test_late_validation_cannot_overwrite_compacted_box(team):
    entered, release = threading.Event(), threading.Event()
    make = team.service.make
    def slow(*args):
        if args[1] == 1:
            entered.set()
            release.wait(3)
        return make(*args)
    team.service.make = slow
    team.edit(0, 'species', 1)
    team.edit(1, 'species', 7)
    async def scenario():
        await team.validate(1)
        survivor = team.results[1]['file']
        task = asyncio.create_task(team.validate(0))
        await asyncio.to_thread(entered.wait, 3)
        try:
            team.clear(0)
        finally:
            release.set()
        await task
        assert team.slots[0]['species'] == 7
        assert team.results[0]['file'] == survivor
        assert team.states[0] == 'legal' and team.can_start
    asyncio.run(scenario())


def test_trainer_change_preserves_base_and_invalidates(team):
    prepare(team)
    base = team.settings.trainer('sv')
    team.profiles['alex'] = dict(base, ot='Alex')
    team.set_trainer('alex')
    assert not team.can_start
    assert team.settings.trainer('sv') == base
    assert team.trainer['ot'] == 'Alex'


def test_corrupt_store_is_preserved_and_read_only(team):
    team.store.path.parent.mkdir(parents=True)
    team.store.path.write_text('{invalid')
    broken = Team('sv', team.setup, store=team.store, service=team.service)
    assert broken.error
    with pytest.raises(ValueError):
        broken.add(0)
    assert team.store.path.read_text() == '{invalid'


@pytest.mark.parametrize('game', ['frlg', 'lgpe', 'swsh', 'bdsp', 'pla', 'sv', 'za'])
def test_local_catalog_excludes_online_and_gifts(game):
    assert set(local_tools(game)) == {'host', 'join'}
    for tool in local_tools(game).values():
        assert tool.activity == 'trade'
        assert dict(tool.variant)['link'] == 'board'


class Process:
    def __init__(self, argv, cwd, env, line, exited, **kwargs):
        self.argv, self.env, self.line, self.exited = argv, env, line, exited
        self.stopped = False
    def stop(self):
        self.stopped = True


@pytest.fixture
def launch(team, tmp_path, monkeypatch):
    import gui.portable_team as module
    monkeypatch.setattr(module, 'validate_keys', lambda path: '')
    monkeypatch.setattr(module, 'DATA', tmp_path)
    monkeypatch.setattr(module, 'SESSION', tmp_path / 'session')
    team.process_factory = Process
    prepare(team)
    return team


def test_start_uses_strict_local_runner_and_cancel_waits_for_exit(launch):
    async def scenario():
        launch.settings.allow_illegal = True
        await launch.start()
        process = launch.process
        assert process is not None, launch.error
        assert process.env['POKELDN_ALLOW_ILLEGAL'] == '0'
        assert process.env['POKELDN_RADIO'] == 'esp32:fixture-port'
        assert '--fresh-pid' not in process.argv
        with pytest.raises(ValueError):
            launch.edit(0, 'level', '1')
        launch.stop()
        assert process.stopped and launch.busy and launch.setup.session_busy
        process.exited(0)
        await asyncio.sleep(0)
        assert not launch.busy
        assert launch.phase == 'stopped'
    asyncio.run(scenario())


def test_edited_file_fails_before_process_is_launched(launch):
    Path(launch.results[0]['file']).write_bytes(b'changed')
    asyncio.run(launch.start())
    assert launch.process is None
    assert not launch.can_start
    assert 'archivo cambió' in launch.error


def test_final_legality_check_blocks_changed_service_result(launch):
    launch.service.legal = False
    asyncio.run(launch.start())
    assert launch.process is None
    assert launch.states[0] == 'invalid'


def test_exit_zero_does_not_invent_completed_trades(launch):
    async def scenario():
        await launch.start()
        launch.process.exited(0)
        await asyncio.sleep(0)
        assert launch.completed == 0
        assert launch.phase == 'error'
    asyncio.run(scenario())


def test_done_events_are_monotonic_and_determine_success(launch):
    async def scenario():
        await launch.start()
        process = launch.process
        process.line('[done] trade 1 complete')
        process.line('[done] trade 0 complete')
        process.exited(0)
        await asyncio.sleep(0)
        assert launch.completed == 1
        assert launch.phase == 'done'
    asyncio.run(scenario())


def test_shared_radio_blocks_second_session(launch):
    async def scenario():
        await launch.start()
        original = launch.process
        await launch.start()
        assert launch.process is original
        other = Team('sv', launch.setup, store=launch.store, service=launch.service)
        await other.start(discover=True)
        assert other.process is None
        launch.process.exited(0)
        await asyncio.sleep(0)
    asyncio.run(scenario())


def test_start_uses_latest_setup_keys(launch, monkeypatch):
    import gui.portable_team as module
    checked = []
    launch.setup.settings = Settings(keys='new.keys', received=launch.settings.received)
    monkeypatch.setattr(module, 'validate_keys', lambda path: checked.append(path) or '')
    async def scenario():
        await launch.start()
        assert checked == ['new.keys']
        assert launch.process is not None
        launch.process.exited(0)
        await asyncio.sleep(0)
    asyncio.run(scenario())


@pytest.mark.parametrize('confirmed', [False, True])
def test_discovery_saves_profile_only_after_confirmed_trade(launch, monkeypatch, confirmed):
    import json
    import gui.portable_team as module
    original_slots = [dict(s) if s else None for s in launch.slots]
    base = dict(launch.trainer)
    monkeypatch.setattr(module.command, 'random_offer', lambda *args: launch.results[0])
    async def scenario():
        await launch.start(discover=True)
        process = launch.process
        process.line('[trainer] ' + json.dumps(dict(game='sv', source='pokemon', ot='Fixture',
                                                   tid=123, sid=456, gender=0, language=7)))
        if confirmed:
            process.line('[done] trade 1 complete')
        process.exited(0)
        await asyncio.sleep(0)
        assert bool(launch.profiles) is confirmed
        assert launch.slots == original_slots
        assert launch.settings.trainer(launch.version) == base
        if confirmed:
            assert launch.trainer['ot'] == 'Fixture'
            await launch.validate_all()
    asyncio.run(scenario())


def test_unchanged_revision_and_metadata_are_reused(team, monkeypatch):
    from unittest.mock import Mock
    options = Mock(wraps=team.service.options)
    moves = Mock(wraps=team.service.move_options)
    monkeypatch.setattr(team.service, 'options', options)
    monkeypatch.setattr(team.service, 'move_options', moves)
    prepare(team)
    asyncio.run(team.validate(0))
    asyncio.run(team.load_options(0))
    assert team.service.count == options.call_count == moves.call_count == 1
    team.edit(0, 'nickname', 'Shell')
    asyncio.run(team.validate(0))
    assert team.service.count == 2
    assert options.call_count == moves.call_count == 1
    team.edit(0, 'level', '10')
    asyncio.run(team.validate(0))
    assert options.call_count == 1
    assert moves.call_count == 2
    team.edit(0, 'moves', [145], option=True)
    asyncio.run(team.validate(0))
    assert moves.call_count == 2
    team.edit(0, 'species', 4)
    assert team.candidate_moves(0) == []
    asyncio.run(team.validate(0))
    assert options.call_count == 2 and moves.call_count == 3


def test_candidate_failure_does_not_replace_final_validation(team, monkeypatch):
    from pokeldn.pokemon import BuilderError
    def fail(*args):
        raise BuilderError('No reference encounter')
    monkeypatch.setattr(team.service, 'move_options', fail)
    prepare(team)
    assert team.states[0] == 'legal' and team.can_start
    assert team.candidate_moves(0) == []


def test_late_move_filter_cannot_replace_new_configuration(team, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def candidates(game, species, *args):
        if species == 7:
            entered.set()
            release.wait(3)
            return [145]
        return [53]
    monkeypatch.setattr(team.service, 'move_options', candidates)
    async def scenario():
        team.add(0)
        team.edit(0, 'species', 7)
        old = asyncio.create_task(team.validate(0))
        await asyncio.to_thread(entered.wait, 2)
        team.edit(0, 'species', 4)
        await team.validate(0)
        release.set()
        await old
        assert team.candidate_moves(0) == [53]
        assert team.states[0] == 'legal'
    asyncio.run(scenario())


@pytest.mark.parametrize('returned', [False, True])
def test_discovery_return_requires_second_confirmation_and_keeps_first_trainer(launch, monkeypatch, returned):
    import json
    import gui.portable_team as module
    monkeypatch.setattr(module.command, 'random_offer', lambda *args: launch.results[0])
    async def scenario():
        await launch.start(discover=True, return_original=True)
        process = launch.process
        assert '--trade-back' in process.argv
        assert process.env['POKELDN_ALLOW_ILLEGAL'] == '0'
        for name, count in [('Original', 1), ('Other', 2)]:
            process.line('[trainer] ' + json.dumps(dict(game='sv', source='pokemon', ot=name,
                                                       tid=123, sid=456, gender=0, language=7)))
            if count == 1 or returned:
                process.line(f'[done] trade {count} complete')
            await asyncio.sleep(0)
        assert launch.return_pending is not returned
        if not returned:
            launch.stop()
        process.exited(0)
        await asyncio.sleep(0)
        assert launch.phase == ('done' if returned else 'stopped')
        assert launch.trainer['ot'] == 'Original'
        assert launch.completed == (2 if returned else 1)
        assert not launch.busy
        await launch.validate_all()
    asyncio.run(scenario())


def test_return_option_does_not_enable_illegal_team_offers(launch):
    async def scenario():
        await launch.start(return_original=True)
        assert '--trade-back' not in launch.process.argv
        launch.process.exited(0)
        await asyncio.sleep(0)
    asyncio.run(scenario())


def test_received_preview_reads_original_without_modifying_it(launch, tmp_path):
    folder = tmp_path / 'received'
    folder.mkdir(exist_ok=True)
    original = folder / 'sv-fixture.pk9'
    original.write_bytes(b'original unchanged')
    launch.run_stamp = 'fixture'
    launch.completed = 1
    launch.service.legal = False
    asyncio.run(launch._watch_received('fixture', str(folder)))
    assert launch.received_info['legal'] is False
    assert launch.received_path == str(original)
    assert original.read_bytes() == b'original unchanged'


def test_missing_native_original_stops_instead_of_reporting_return_success(launch, monkeypatch):
    import gui.portable_team as module
    monkeypatch.setattr(module.command, 'random_offer', lambda *args: launch.results[0])
    async def scenario():
        await launch.start(discover=True, return_original=True)
        launch._line("[trade-back] the console's Pokemon was not kept: the next trade offers the queue")
        assert launch.process.stopped
        assert launch.stop_requested and launch.error
        launch._exited(0)
        assert launch.phase != 'done'
    asyncio.run(scenario())

@pytest.mark.parametrize('handler,egg,version,accepted', [
    (0, False, 44, True), (0, False, 45, True),
    (1, False, 44, False), (0, True, 44, False), (0, False, 50, False),
])
def test_swsh_identifies_first_received_owner_before_finalizing(team, tmp_path, handler, egg, version, accepted):
    model = Team('swsh', team.setup, store=TeamStore('swsh', tmp_path / 'drafts'), service=team.service)
    folder = Path(model.settings.received)
    folder.mkdir()
    (folder / 'swsh-fixture-1.pk8').write_bytes(b'first original')
    (folder / 'swsh-fixture-2.pk8').write_bytes(b'second trade')
    seen = []
    def owner(game, data):
        seen.append(data)
        return dict(ot='Fixture', tid=123, sid=456, gender=0, language=7,
                    handler=handler, egg=egg, version=version)
    model.service.owner = owner
    model.run_stamp = 'fixture'
    model.discovering = model.busy = model.setup.session_busy = True
    model.completed = 1
    async def scenario():
        model._exited(0)
        assert model.busy  # Exit waits for PKHeX; no premature failed identification.
        for _ in range(200):
            if not model.busy:
                break
            await asyncio.sleep(.01)
        assert not model.busy
        assert bool(model.profiles) is accepted
        assert model.phase == ('done' if accepted else 'error')
        if accepted:
            assert model.trainer['ot'] == 'Fixture'
        assert seen == [b'first original']
    asyncio.run(scenario())


def test_received_trainer_result_cannot_cross_sessions(team, tmp_path):
    folder = tmp_path / 'received'
    folder.mkdir()
    (folder / 'sv-old.pk9').write_bytes(b'original')
    def owner(*args):
        team.run_stamp = 'new'
        return dict(ot='Old', tid=1, sid=2, gender=0, language=2, handler=0, egg=False, version=50)
    team.service.owner = owner
    team.run_stamp = 'old'
    asyncio.run(team._learn_received_trainer('old', str(folder)))
    assert team.found_trainer is None


@pytest.mark.parametrize('game,language,accepted', [('za', 11, True), ('za', 7, True), ('za', 12, False), ('sv', 11, False)])
def test_discovery_preserves_za_latin_american_spanish(team, tmp_path, game, language, accepted):
    import json
    model = Team(game, team.setup, store=TeamStore(game, tmp_path / 'profiles'), service=team.service)
    model.discovering = True
    model.completed = 1
    model._line('[trainer] ' + json.dumps(dict(game=game, source='session', ot='Fixture',
                                             tid=123, sid=456, gender=0, language=language)))
    async def scenario():
        model._exited(0)
        assert bool(model.profiles) is accepted
        assert model.phase == ('done' if accepted else 'error')
        if accepted:
            restored = Team(game, team.setup, store=model.store, service=team.service)
            assert restored.trainer == dict(ot='Fixture', tid=123, sid=456, gender=0, language=language)
            await model.validate_all()
    asyncio.run(scenario())


@pytest.mark.parametrize('role', ['host', 'join'])
def test_lgpe_code_is_three_digits_and_reaches_launcher(team, tmp_path, role):
    from pokeldn.app import command
    from pokeldn.lgpe.session import code_picks
    model = Team('lgpe', team.setup, store=TeamStore('lgpe', tmp_path / 'drafts'), service=team.service)
    assert model.code == '000'
    model.configure(role, model.version, '078')
    values = model._values(model.tools[role], [tmp_path / 'offer.pb7'])
    if role == 'host':
        field = next(f for f in model.tools[role].fields if f.kind == 'linkcode')
        assert values[field.key] == '0,7,8'
        assert not command.code_error(field, values[field.key], 'lgpe')
        assert code_picks(values[field.key].split(',')) == [0, 7, 8]
    else:
        assert '--code' not in values  # Upstream joiner scans; it has no code filter.
    for invalid in ('', '12', '1234', 'a12'):
        with pytest.raises(ValueError, match='tres dígitos'):
            model.configure(role, model.version, invalid)
    assert model.code == '078'
