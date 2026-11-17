"""Reproduce reported baseline defects using fakes; never load a DLL or open a port.

This records observed defects, not product acceptance or a fix regression suite.
Run from any directory with Python 3.11+: python -B <this-file>
"""
from __future__ import annotations

import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import types

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / '程序文件/TULA_Robot_Workspace/lerobot_robot_tula/src/lerobot_robot_tula'


def forbidden_library_load(*args, **kwargs):
    raise RuntimeError('Native library loading is forbidden in this reproduction.')


ctypes.CDLL = forbidden_library_load
package = types.ModuleType('lerobot_robot_tula')
package.__path__ = [str(PACKAGE)]
sys.modules[package.__name__] = package

from lerobot_robot_tula.controller import TulaController


class FakeDriver:
    def __init__(self, positions, status=0):
        self.positions = {axis: iter(values) for axis, values in positions.items()}
        self.last = {}
        self.status = status
        self.status_reads = 0

    def read_status(self, axis):
        self.status_reads += 1
        return self.status

    def write_degrees(self, axis, degrees):
        pass

    def read_counts(self, axis):
        self.last[axis] = next(self.positions[axis], self.last.get(axis, 0))
        return self.last[axis]


def make_controller(driver, axes):
    controller = TulaController(driver, axes)
    controller.connected = True  # Simulated connection; connect() is never called.
    return controller


results = []
driver = FakeDriver({1: [200]}, status=0x8000)
controller = make_controller(driver, (1,))
success = controller.set_angles({1: 1.0}, timeout=0.1, tolerance_counts=0, poll_hz=1000)
if success is not True or driver.status_reads != 1:
    raise AssertionError('R1 baseline behavior changed; review the new behavior.')
results.append({
    'id': 'R1', 'scenario': 'Axis reports running while position enters tolerance',
    'reported_success': success, 'fake_status': '0x8000 MOTOR_RUNNING',
    'target_counts': 200, 'status_queries': driver.status_reads,
    'issue_reproduced': True,
})

driver = FakeDriver({1: [200, 240], 2: [0, 200]})
controller = make_controller(driver, (1, 2))
success = controller.set_angles({1: 1.0, 2: 1.0}, timeout=0.1,
                                tolerance_counts=0, poll_hz=1000)
final_positions = {axis: driver.read_counts(axis) for axis in (1, 2)}
if success is not True or final_positions != {1: 240, 2: 200}:
    raise AssertionError('R2 baseline behavior changed; review the new behavior.')
results.append({
    'id': 'R2', 'scenario': 'An axis leaves tolerance after its first successful sample',
    'reported_success': success, 'target_counts_each_axis': 200,
    'final_fake_read_counts': final_positions, 'issue_reproduced': True,
})

# Replace only external framework base/config imports. Execute actual robot methods.
lerobot = types.ModuleType('lerobot')
lerobot.__path__ = []
sys.modules['lerobot'] = lerobot
robots = types.ModuleType('lerobot.robots')
robots.Robot = object
sys.modules['lerobot.robots'] = robots
config = types.ModuleType('lerobot_robot_tula.config')
config.TulaRobotConfig = object
sys.modules[config.__name__] = config

from lerobot_robot_tula.robot import TulaRobot

entered = threading.Event()
release = threading.Event()
stop_requested = threading.Event()
stopped = threading.Event()
errors = []


class BlockingController:
    axes = (1,)
    connected = True

    def __init__(self):
        self.driver = self

    def require_connection(self):
        pass

    def set_angles(self, *args, **kwargs):
        entered.set()
        if not release.wait(5):
            raise RuntimeError('Reproduction coordination timed out.')
        return True

    def stop(self, axis):
        stopped.set()


robot = TulaRobot.__new__(TulaRobot)
robot._lock = threading.RLock()
robot._axes = {'joint_1': 1}
robot._limits = {'joint_1': (-10, 10)}
robot._controller = BlockingController()


def run_wait():
    try:
        robot.move_and_wait({'joint_1.pos': 1.0})
    except Exception as exc:
        errors.append(repr(exc))


def run_stop():
    try:
        stop_requested.set()
        robot.stop()
    except Exception as exc:
        errors.append(repr(exc))


wait_thread = threading.Thread(target=run_wait)
stop_thread = threading.Thread(target=run_stop)
wait_thread.start()
stop_started = False
try:
    if not entered.wait(2):
        raise AssertionError('Wait operation did not start.')
    stop_thread.start()
    stop_started = True
    if not stop_requested.wait(2):
        raise AssertionError('Stop request did not start.')
    blocked = not stopped.wait(0.1)
finally:
    release.set()
    wait_thread.join(2)
    if stop_started:
        stop_thread.join(2)
if errors or wait_thread.is_alive() or stop_thread.is_alive():
    raise AssertionError(f'Reproduction did not finish cleanly: {errors}')
if not blocked or not stopped.is_set():
    raise AssertionError('R3 baseline behavior changed; review the new behavior.')
results.append({
    'id': 'R3', 'scenario': 'stop() waits for move_and_wait() to release the same instance lock',
    'stop_blocked_during_wait': blocked,
    'stop_reached_fake_driver_after_release': stopped.is_set(),
    'scope': 'Python lock behavior only; not physical stop latency',
    'issue_reproduced': True,
})

source_paths = [PACKAGE / name for name in ('config.py', 'controller.py', 'robot.py', 'td201_driver.py')]
report = {
    'review_date': '2026-11-17',
    'assessed_source_revision': '790aae86bb358d46a2a9c01b9f914eabf1bf21ac',
    'checkout_revision_at_run': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'python_version': sys.version.split()[0],
    'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source_paths},
    'cases': results,
    'real_dll_or_serial_used': False,
    'result_meaning': 'Three baseline defects reproduced with simulated inputs; not product acceptance.',
}
output = Path(__file__).with_name('离线复现结果.json')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
