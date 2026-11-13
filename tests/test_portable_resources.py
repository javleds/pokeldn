from collections import namedtuple
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from gui.portable_resources import ResourceOverlay, ResourceSampler, temperature_label


def test_sampler_tracks_total_and_app_without_first_sample_spike(monkeypatch):
    import gui.portable_resources as module
    times = namedtuple('Times', 'user system idle')
    process = Mock(pid=1)
    process.oneshot.return_value.__enter__ = Mock()
    process.oneshot.return_value.__exit__ = Mock()
    process.children.return_value = []
    process.create_time.return_value = 10
    process.cpu_times.side_effect = [times(2, 2, 0), times(3, 3, 0)]
    process.memory_info.return_value = SimpleNamespace(rss=100)
    monkeypatch.setattr(module.psutil, 'Process', lambda: process)
    monkeypatch.setattr(module.psutil, 'cpu_count', lambda: 4)
    monkeypatch.setattr(module.psutil, 'cpu_times', Mock(side_effect=[times(10, 10, 80), times(12, 12, 84)]))
    monkeypatch.setattr(module.psutil, 'virtual_memory', lambda: SimpleNamespace(total=1000, available=600, percent=40))
    monkeypatch.setattr(module.time, 'monotonic', Mock(side_effect=[10, 12]))
    monkeypatch.setattr(module, 'cpu_temperature', lambda: None)
    sampler = ResourceSampler()
    first, second = sampler.sample(), sampler.sample()
    assert first['cpu'] is first['app_cpu'] is None
    assert second['cpu'] == 50
    assert second['app_cpu'] == 25
    assert second['ram'] == 100 and second['memory_used'] == 400


def test_overlay_stops_sampling_when_hidden_or_disconnected():
    page = Mock()
    overlay = ResourceOverlay(page)
    overlay.control.update = Mock()
    overlay.toggle()
    assert overlay.control.visible
    task = overlay.task
    overlay.connected = False
    overlay.sync()
    task.cancel.assert_called_once()
    assert overlay.task is None
    overlay.connected = True
    overlay.sync()
    assert overlay.task is not None
    overlay.toggle()
    assert not overlay.control.visible and overlay.task is None


@pytest.mark.parametrize('temperature,label', [(None,'N/D'),(40,'Fresco'),(65,'Templado'),(80,'Caliente')])
def test_temperature_bands(temperature,label):
    assert label in temperature_label(temperature)[0]
