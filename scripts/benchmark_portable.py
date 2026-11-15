#!/usr/bin/env python3
"""Measure the real Team model and PKHeX with disposable data, without radio or Flutter.

Run with .venv/bin/python scripts/benchmark_portable.py --output /tmp/benchmark.json
RSS includes this harness and descendants, not OS/Flutter. CPU counts are sampled,
so short-lived processes and peaks can be missed. A cold process is not a cold disk.
"""
import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import threading
import time
from types import SimpleNamespace

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Measurement:
    def __init__(self):
        self.process = psutil.Process()
        self.stop = threading.Event()
        self.first_cpu = {}
        self.latest_cpu = {}
        self.peak_rss = 0
        self.sample_count = 0
        self.names = set()

    def sample(self, initial=False):
        processes = [self.process, *self.process.children(recursive=True)]
        rss = 0
        for process in processes:
            try:
                with process.oneshot():
                    key = (process.pid, process.create_time())
                    cpu = process.cpu_times()
                    value = cpu.user + cpu.system
                    if key not in self.first_cpu:
                        self.first_cpu[key] = value if initial else 0
                    self.latest_cpu[key] = value
                    rss += process.memory_info().rss
                    self.names.add(process.name())
            except psutil.NoSuchProcess:
                continue
        self.peak_rss = max(self.peak_rss, rss)
        self.sample_count += 1

    def poll(self):
        while not self.stop.wait(0.1):
            try:
                self.sample()
            except psutil.Error as exc:
                self.error = str(exc)
                return

    @contextmanager
    def stage(self, name, rows):
        self.error = ''
        self.sample(initial=True)
        started = time.perf_counter()
        thread = threading.Thread(target=self.poll, daemon=True)
        thread.start()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - started
            self.stop.set()
            thread.join()
            self.sample()
            cpu_seconds = sum(self.latest_cpu[k] - self.first_cpu[k] for k in self.latest_cpu)
            rows.append(dict(stage=name, seconds=round(elapsed, 4),
                             peak_sampled_rss_mib=round(self.peak_rss / 1024**2, 2),
                             sampled_cpu_seconds=round(cpu_seconds, 4),
                             samples=self.sample_count, process_names=sorted(self.names),
                             sampling_error=self.error))


async def workload(game, folder, rows):
    with Measurement().stage('import_team_and_service', rows):
        from gui.portable_team import Team, TeamStore
        from pokeldn.app.settings import Settings
        from pokeldn.pokemon import Service
    service = Service()
    service.allow_illegal = False
    setup = SimpleNamespace(settings=Settings(received=str(folder / 'received'), sprites=False),
                            busy=False, checking=False, session_busy=False,
                            active_team=None, demo=False, radio_state='missing', device='')
    team = Team(game, setup, store=TeamStore(game, folder / 'drafts'), service=service)
    statuses = []
    try:
        with Measurement().stage('cold_catalogs', rows):
            for kind in ('species', 'moves', 'natures'):
                await team.names(kind)
        with Measurement().stage('first_six_species_validate', rows):
            for index, species in enumerate((1, 4, 7, 25, 133, 129)):
                team.edit(index, 'species', species)
                team.edit(index, 'level', '100')
            await team.validate_all()
        statuses.append(dict(stage=rows[-1]['stage'], states=list(team.states)))
        with Measurement().stage('unchanged_six_validate_cached', rows):
            await team.validate_all()
        for attempt in range(3):
            with Measurement().stage(f'edit_one_nickname_{attempt + 1}', rows):
                team.edit(0, 'nickname', f'Bench{attempt}')
                await team.validate(0)
            statuses.append(dict(stage=rows[-1]['stage'], states=list(team.states)))
        with Measurement().stage('edit_six_nicknames', rows):
            for index in range(6):
                team.edit(index, 'nickname', f'Team{index}')
            await team.validate_all()
        statuses.append(dict(stage=rows[-1]['stage'], states=list(team.states)))
        with Measurement().stage('edit_six_levels_recalculate_options', rows):
            for index in range(6):
                team.edit(index, 'level', '99')
            await team.validate_all()
        statuses.append(dict(stage=rows[-1]['stage'], states=list(team.states)))
        with Measurement().stage('warm_idle_3_seconds', rows):
            await asyncio.sleep(3)
        return statuses
    finally:
        service.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', choices=('sv', 'frlg', 'swsh', 'lgpe'), default='sv')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), game=args.game,
                  platform=platform.platform(), machine=platform.machine(), python=platform.python_version(),
                  logical_cpus=psutil.cpu_count(), system_ram_gib=round(psutil.virtual_memory().total / 1024**3, 2),
                  sample_interval_seconds=0.1,
                  scope='Real Team + PKHeX; sampler overhead included. No Flutter, radio, OS memory or disk-cold guarantee.', stages=[])
    with tempfile.TemporaryDirectory(prefix='pokeldn-benchmark-') as folder:
        os.environ['POKELDN_DATA'] = folder
        report['validation'] = asyncio.run(workload(args.game, Path(folder), report['stages']))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if all(set(row['states']) == {'legal'} for row in report['validation']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
