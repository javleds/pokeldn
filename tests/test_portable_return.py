"""The native return gate never blocks the protocol or trusts UI legality flags."""
import base64
import hashlib
import json
import time

from pokeldn.portable_return import ReturnGate
from pokeldn.trade_back import TradeBack


def wait_until(predicate):
    deadline = time.monotonic() + 2
    while not predicate() and time.monotonic() < deadline:
        time.sleep(.01)
    assert predicate()


def respond(folder, gate, action, candidate=None):
    message = {'action': action, 'sha256': gate.digest}
    if candidate is not None:
        (folder / 'edited.bin').write_bytes(candidate)
        message['candidate_sha256'] = hashlib.sha256(candidate).hexdigest()
    (folder / 'response.json').write_text(json.dumps(message))


def test_original_is_preserved_and_can_return_even_if_illegal(tmp_path):
    def no_check(*args):
        raise AssertionError('The intact original must not go through generation/check.')
    gate = ReturnGate(tmp_path, 'sv', check=no_check)
    try:
        gate.begin(b'original')
        assert gate.current() is None
        assert (tmp_path / 'original.bin').read_bytes() == b'original'
        assert json.loads((tmp_path / 'request.json').read_text())['sha256'] == gate.digest
        respond(tmp_path, gate, 'original')
        wait_until(lambda: gate.current() is not None)
        assert gate.current() == b'original'
    finally:
        gate.close()


def test_edited_illegal_is_withheld_and_original_can_recover(tmp_path):
    gate = ReturnGate(tmp_path, 'sv', check=lambda *a: {'legal': False})
    try:
        gate.begin(b'original')
        respond(tmp_path, gate, 'edited', b'illegal!')
        wait_until(lambda: bool(gate.error))
        assert gate.current() is None
        respond(tmp_path, gate, 'original')
        wait_until(lambda: gate.current() is not None)
        assert gate.current() == b'original'
    finally:
        gate.close()


def test_edited_bytes_are_checked_again_and_native_length_is_preserved(tmp_path):
    checked = []
    def check(game, data):
        checked.append((game, data))
        return {'legal': True, 'data': base64.b64encode(data).decode()}
    gate = ReturnGate(tmp_path, 'sv', check=check)
    try:
        gate.begin(b'original')
        respond(tmp_path, gate, 'edited', b'modified')
        wait_until(lambda: gate.current() is not None)
        assert gate.current() == b'modified'
        assert checked == [('sv', b'modified')]
        assert (tmp_path / 'original.bin').read_bytes() == b'original'
    finally:
        gate.close()


def test_stale_response_is_rejected_without_exposing_an_offer(tmp_path):
    gate = ReturnGate(tmp_path, 'sv')
    try:
        gate.begin(b'original')
        (tmp_path / 'response.json').write_text(json.dumps({'action': 'original', 'sha256': 'another-run'}))
        wait_until(lambda: bool(gate.error))
        assert gate.current() is None
    finally:
        gate.close()


def test_host_offers_nothing_until_explicit_return_choice(tmp_path, monkeypatch):
    monkeypatch.setenv('POKELDN_RETURN_DIR', str(tmp_path))
    monkeypatch.setenv('POKELDN_RETURN_GAME', 'sv')
    partner = TradeBack('sv', [b'initial'], log=lambda *a: None)
    try:
        assert partner.theirs().offer == b'initial'
        partner.offer(b'original')
        partner.done()
        for _ in range(1000):
            assert partner.theirs().offer is None
            assert not partner.theirs().accepted
        respond(tmp_path, partner.gate, 'original')
        wait_until(lambda: partner.theirs().offer is not None)
        assert partner.theirs().offer == b'original'
        assert partner.theirs().accepted
    finally:
        partner.close()


class PausedGate:
    """Protocol fixture: completion is controlled by the test, with no thread or IO."""
    def __init__(self):
        self.original = None
        self.result = None
    def begin(self, original):
        assert self.original is None
        self.original = bytes(original)
    def current(self):
        return self.result
    def close(self):
        pass


def test_scarlet_joiner_acks_completion_but_waits_before_next_offer():
    from pokeldn.sv import trade
    from pokeldn.trade_back import Rounds
    gate = PausedGate()
    initial, original, edited = b'A' * 348, b'B' * 348, b'C' * 348
    stage = trade.JoinerTradeStage([initial], rounds=Rounds([initial], gate=gate))
    stage.host_offers = [original]
    stage.step_index = len(trade.STEPS)
    replies = stage.on_message(1, trade.table_update(trade.KEY_EXCHANGE, False))
    assert replies and stage.trades == 1
    assert stage.offer is None and not stage.done
    assert stage.offer_first() == []
    offered = trade.build(trade.KEY_TRADE, trade.KIND_OFFER, 0, b'D' * 348)
    assert stage.on_message(0, offered) == []
    assert stage.poll() == []
    gate.result = edited
    replies = stage.poll()
    assert stage.offer == edited
    assert any(trade.parse(payload)[3] == edited for _, port, payload in replies if port == 0)


def test_firered_joiner_holds_party_request_until_return_is_ready(monkeypatch):
    from test_host_end_to_end import _mon
    from pokeldn.frlg.link import trade
    gate = PausedGate()
    monkeypatch.setattr(ReturnGate, 'from_environment', lambda *a: gate)
    engine = trade.TradeEngine([_mon(0x11)], trades=2, offered_slots=[0, 0])
    engine.round = 1
    original = _mon(0x22)
    engine.party[0] = original
    gate.begin(original.raw)
    engine._on_req(trade.BLOCK_REQ_SIZE_200)
    assert engine.sender is None and engine._party_sent == 0
    for _ in range(20):
        engine.tick(sender_only=True)
    assert engine.sender is None and engine._party_sent == 0
    edited = _mon(0x33)
    gate.result = edited.raw
    engine.tick(sender_only=True)
    assert engine.party[0].raw == edited.raw
    assert engine.sender is not None
    assert engine._party_sent == 1


def test_firered_host_holds_party_exchange_until_return_is_ready(monkeypatch):
    from test_host_end_to_end import _mon
    from pokeldn.frlg.link.host_trade import HostTradeEngine
    gate = PausedGate()
    monkeypatch.setattr(ReturnGate, 'from_environment', lambda *a: gate)
    engine = HostTradeEngine([_mon(0x11)], trades=2, offered_slots=[0, 0])
    engine.round = 1
    original = _mon(0x22)
    engine.party[0] = original
    gate.begin(original.raw)
    before = engine._parent_polls
    for _ in range(20):
        engine._begin_party_exchange()
        engine.tick()
    assert engine._parent_polls == before + 20
    assert not engine._return_applied
    edited = _mon(0x33)
    gate.result = edited.raw
    engine._begin_party_exchange()
    assert engine.party[0].raw == edited.raw and engine._return_applied


def test_gate_rejects_another_native_session(tmp_path):
    import pytest
    gate = ReturnGate(tmp_path, 'sv')
    gate.bind(('console', 1))
    gate.bind(('console', 1))
    with pytest.raises(ValueError, match='reconnect'):
        gate.bind(('console', 2))
    assert gate.current() is None
    assert gate.closed.is_set()


class DelayedGate(PausedGate):
    def begin(self, original):
        super().begin(original)
        self.ready_at = time.monotonic() + 5
        self.paused = 0
    def current(self):
        if self.original is not None and time.monotonic() >= self.ready_at:
            return self.original
        if self.original is not None:
            self.paused += 1
        return None


def test_controlled_bdsp_join_waits_then_returns_original(monkeypatch, tmp_path):
    from test_trade_back_bdsp_join import test_the_bdsp_joiner_offers_back_the_console_pokemon_byte_for_byte
    gate = DelayedGate()
    monkeypatch.setattr(ReturnGate, 'from_environment', lambda *a: gate)
    test_the_bdsp_joiner_offers_back_the_console_pokemon_byte_for_byte(monkeypatch, tmp_path)
    assert gate.paused > 0


def test_controlled_swsh_join_waits_then_returns_original(monkeypatch, tmp_path, capsys):
    from test_trade_back_swsh_join import test_the_sword_joiner_returns_the_consoles_pokemon_in_the_next_trade
    gate = DelayedGate()
    monkeypatch.setattr(ReturnGate, 'from_environment', lambda *a: gate)
    test_the_sword_joiner_returns_the_consoles_pokemon_in_the_next_trade(tmp_path, monkeypatch, capsys, 'join')
    assert gate.paused > 0


def test_controlled_lgpe_join_holds_the_next_offer(monkeypatch, tmp_path):
    from test_trade_back_lgpe_join import _join, box
    from pokeldn.lgpe import pb7
    gate = PausedGate()
    monkeypatch.setattr(ReturnGate, 'from_environment', lambda *a: gate)
    mod = _join()
    path = tmp_path / 'initial.pb7'
    path.write_bytes(box(133, 0x1000))
    args = mod.build_parser().parse_args(['--trade-back', '--offer', str(path)])
    args.offers = [str(path)]
    args.offer = str(path)
    mod.setup_trade_back(args)
    class Window:
        def send(self, body):
            return body
    state, sent = {'window': Window()}, []
    def console(kind, step, body):
        mod.answer(args, state, pb7.parse_message(pb7.build_message(kind, body, step=step)),
                   lambda b, p: sent.append(pb7.parse_message(b)))
    original = box(64, 0xCAFE)
    console(2, 2, original)
    console(3, 4, b'\1\0\0\0')
    console(3, 5, b'\2\0\0\0')
    before = len(sent)
    console(4, 6, box(25, 6))
    assert gate.original == original
    assert len(sent) == before
    mod.poll_return(args, state)
    assert len(sent) == before
    gate.result = original
    mod.poll_return(args, state)
    assert sent[-1]['body'] == original


def test_controlled_pla_join_preserves_heartbeat_and_waits(monkeypatch):
    import pla_join
    from pokeldn import pla
    from pokeldn.ldn import channel_table
    from pokeldn.pla import data_exchange, game_channel, joiner, trade_box
    from test_pla_joiner import OUR_IP, OUR_MAC, SSID, Clock, _console_trade, _game, _msg, _seat
    gate = PausedGate()
    monkeypatch.setattr(ReturnGate, 'from_environment', lambda *a: gate)
    keys, clock = pla.session_keys(SSID), Clock()
    exchange = data_exchange.build_record(player_id=bytes.fromhex('504b4c44'), name='POKELDN')
    queued = trade_box.build_our_record(**data_exchange.read_record(exchange))
    args = pla_join.build_parser().parse_args(['--offer', 'unused.pa8', '--trade-back'])
    args.next_offers = []
    session = pla_join.make_session(args, keys, OUR_IP, OUR_MAC, queued, exchange, our_var=0x687E, clock=clock)
    _seat(keys, session)
    session.receive([_msg(data_exchange.build_content_message(data_exchange.REFERENCE_RECORD, 0x02), joiner.PROTO_STREAM, port=0)])
    session.receive([_game(channel_table.build([(bytes(game_channel.KEY_SIZE), True)]), 1, 1)])
    session.receive([_msg(game_channel.build_open(game_channel.HOST_OPEN_PAYLOAD), 0x7C, 0)])
    session.receive([_msg(game_channel.build_open(game_channel.HOST_OPEN_PAYLOAD, sequence_id=2), 0x7C, 0)])
    _console_trade(keys, clock, session, trade_box.REFERENCE_RECORD, {0: 3, 1: 2})
    assert session.pending_return and session.offer is None
    for _ in range(20):
        session.poll()
    assert session.offer is None
    gate.result = gate.original
    session.poll()
    assert not session.pending_return and session.offer == gate.original


def test_controlled_frlg_host_returns_original_after_protocol_pause(monkeypatch):
    import test_host_end_to_end as stack
    gate = PausedGate()
    polls = []
    def current():
        polls.append(None)
        return gate.original if len(polls) > 20 else None
    gate.current = current
    monkeypatch.setattr(ReturnGate, 'from_environment', lambda *a: gate)
    original_session = stack.HostSession
    def controlled_session(*args, **kwargs):
        kwargs['offered_slots'] = [0, 0]
        return original_session(*args, **kwargs)
    monkeypatch.setattr(stack, 'HostSession', controlled_session)
    host, child, radio, ours, theirs, elapsed = stack._run_full_stack()
    assert len(polls) > 20
    assert host.trade.commits == child.confirmed == 2
    assert child.party[1].raw == theirs[0].raw
    assert gate.original == theirs[0].raw
    assert child.disconnect_seen and not radio.pending
