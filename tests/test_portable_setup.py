"""Onboarding never treats a USB port or a flash exit code as a ready radio."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from gui import board, portable_setup as setup


def port(device="/dev/test", serial="one"):
    return board.Port(device, "USB", serial, True)


def real_state(monkeypatch, tmp_path):
    config = SimpleNamespace(keys="", radio_port="", save=lambda: None)
    monkeypatch.setattr(setup.settings, "load", lambda: config)
    monkeypatch.setattr(setup, "DATA", tmp_path)
    return setup.Setup()


def test_port_selection_does_not_guess_between_boards():
    a, b = port(), port("/dev/other", "two")
    assert setup.choose_port([a, b], "") is None
    assert setup.choose_port([a, b], b.device) is b
    assert setup.choose_port([a], "old-port") is a


def test_invalid_keys_preserve_previous_copy(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    target = tmp_path / "portable" / "prod.keys"
    target.parent.mkdir()
    target.write_bytes(b"old keys")
    monkeypatch.setattr(setup, "validate_keys", lambda path: "Invalid")
    asyncio.run(state.import_keys(b"not a key"))
    assert target.read_bytes() == b"old keys"
    assert state.keys_error == "Invalid"
    assert not list(target.parent.glob('.keys-*'))


def test_valid_keys_are_private_and_persisted(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    monkeypatch.setattr(setup, "validate_keys", lambda path: "")
    asyncio.run(state.import_keys(b"test-only"))
    target = Path(state.settings.keys)
    assert target.read_bytes() == b"test-only"
    assert target.stat().st_mode & 0o777 == 0o600
    assert not state.keys_error


def test_check_rejects_another_chip(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    monkeypatch.setattr(board, "ports", lambda: [port()])
    monkeypatch.setattr(board, "identify", lambda *a: SimpleNamespace(chip="ESP32-S3", current=True, firmware_version="1"))
    asyncio.run(state.check_radio())
    assert state.radio_state == "unsupported"


def test_demo_never_uses_hardware_or_saves(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real service used in demo")
    monkeypatch.setattr(board, "ports", forbidden)
    monkeypatch.setattr(setup.settings, "load", forbidden)
    state = setup.Setup(demo=True)
    monkeypatch.setattr(setup.asyncio, "sleep", AsyncMock())
    async def run():
        await state.check()
        await state.import_keys(b"demo")
        await state.install()
    asyncio.run(run())
    assert state.ready and state.phase == "done"
    assert all("Demo" in line for line in state.logs)


def test_install_is_single_owner_and_preserves_logs_on_failure(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    state.radio_state, state.chip = "flash", "ESP32-C6"
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def install():
            calls.append(True)
            state.log("writing")
            entered.set()
            await release.wait()
            raise OSError("disconnected")
        monkeypatch.setattr(state, "_install_real", install)
        first = asyncio.create_task(state.install())
        await entered.wait()
        await state.install()
        assert len(calls) == 1
        release.set()
        await first
    asyncio.run(run())
    assert state.phase == "error" and not state.busy
    assert any("writing" in line for line in state.logs)
    assert any("disconnected" in line for line in state.logs)


def test_logs_are_bounded_and_redacted():
    state = setup.Setup(demo=True)
    for n in range(510):
        state.log(f"/Users/example/firmware line {n}")
    assert len(state.logs) == 500
    assert all("/Users/example" not in line for line in state.logs)


def test_compatible_firmware_is_not_reinstalled(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    monkeypatch.setattr(board, "ports", lambda: [port()])
    monkeypatch.setattr(board, "identify", lambda *a: SimpleNamespace(chip="ESP32-C6", current=True, firmware_version="1"))
    install = AsyncMock()
    monkeypatch.setattr(state, "_install_real", install)
    async def run():
        await state.check_radio()
        await state.install()
    asyncio.run(run())
    assert state.radio_state == "ready"
    install.assert_not_called()


def test_flash_checks_response_after_successful_write(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    state.device, state.chip, state.serial_number = "/dev/test", "ESP32-C6", "one"
    image = tmp_path / "c6.bin"
    image.write_bytes(b"fixture")
    monkeypatch.setattr(board, "FIRMWARE_C6", str(image))
    monkeypatch.setattr(board, "ports", lambda: [port()])
    monkeypatch.setattr(board, "detect_chip", lambda *a: "ESP32-C6")
    monkeypatch.setattr(board, "identify", lambda *a: SimpleNamespace(current=False, chip="ESP32-C6"))
    monkeypatch.setattr(setup.asyncio, "sleep", AsyncMock())
    async def run():
        reader = asyncio.StreamReader()
        reader.feed_data(b"Writing 64%\n")
        reader.feed_eof()
        monkeypatch.setattr(setup.asyncio, "create_subprocess_exec", AsyncMock(return_value=SimpleNamespace(stdout=reader, wait=AsyncMock(return_value=0))))
        state.radio_state = "flash"
        await state.install()
    asyncio.run(run())
    assert state.phase == "error"
    assert state.radio_state != "ready"
    assert any("64%" in line for line in state.logs)


def test_closed_ui_does_not_interrupt_logging():
    state = setup.Setup(demo=True)
    def closed():
        raise RuntimeError("session closed")
    state.listeners.add(closed)
    state.log("writing")
    assert not state.listeners
    assert "writing" in state.logs[-1]


def test_ready_reinstall_requires_explicit_opt_in(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    state.radio_state, state.chip = 'ready', 'ESP32-C6'
    flash = AsyncMock()
    monkeypatch.setattr(state, '_install_real', flash)
    asyncio.run(state.install())
    flash.assert_not_called()
    asyncio.run(state.install(reinstall=True))
    flash.assert_awaited_once()


def test_reinstall_does_not_bypass_missing_or_wrong_hardware(monkeypatch, tmp_path):
    state = real_state(monkeypatch, tmp_path)
    flash = AsyncMock()
    monkeypatch.setattr(state, '_install_real', flash)
    for status, chip in [('missing','ESP32-C6'), ('error','ESP32-C6'), ('ready','ESP32-S3')]:
        state.radio_state, state.chip = status, chip
        asyncio.run(state.install(reinstall=True))
    flash.assert_not_called()
