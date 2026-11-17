#!/usr/bin/env python3
"""Verify a ROS2 installation using its actual demo nodes and GUI."""
import json
import os
from pathlib import Path
import subprocess
import time

report = {}
env = os.environ.copy()
env['ROS_DOMAIN_ID'] = '87'
env['ROS_LOCALHOST_ONLY'] = '1'
out_dir = Path.home() / 'ros2_setup_validation'
out_dir.mkdir(exist_ok=True)

def run(args, timeout=30):
    result = subprocess.run(args, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    return {'exit_code': result.returncode, 'output': result.stdout}

report['user'] = run(['id'])
report['environment'] = {
    key: os.environ.get(key) for key in ('ROS_DISTRO', 'DISPLAY', 'WAYLAND_DISPLAY')
}
report['rclpy'] = run(['python3', '-c', 'import rclpy; print(rclpy.__file__)'])
report['packages'] = run(['dpkg-query', '-W', 'ros-jazzy-desktop', 'ros-dev-tools',
                          'ros-jazzy-rviz2', 'python3-colcon-common-extensions'])
report['graphics'] = run(['glxinfo', '-B'])

talker_log = out_dir / 'talker.log'
listener_log = out_dir / 'listener.log'
with talker_log.open('w') as talker_out, listener_log.open('w') as listener_out:
    talker = subprocess.Popen(['ros2', 'run', 'demo_nodes_cpp', 'talker'],
                              env=env, stdout=talker_out, stderr=subprocess.STDOUT,
                              start_new_session=True)
    listener = subprocess.Popen(['ros2', 'run', 'demo_nodes_py', 'listener'],
                                env=env, stdout=listener_out, stderr=subprocess.STDOUT,
                                start_new_session=True)
    try:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if 'I heard' in listener_log.read_text():
                break
            if talker.poll() is not None or listener.poll() is not None:
                break
            time.sleep(1)
        report['pub_sub'] = {
            'passed': 'I heard' in listener_log.read_text(),
            'talker_log': talker_log.read_text(),
            'listener_log': listener_log.read_text(),
        }
    finally:
        import signal
        for proc in (talker, listener):
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=10)

rviz_log = out_dir / 'rviz.log'
with rviz_log.open('w') as rviz_out:
    rviz = subprocess.Popen(['ros2', 'run', 'rviz2', 'rviz2'], env=env,
                            stdout=rviz_out, stderr=subprocess.STDOUT,
                            start_new_session=True)
    try:
        time.sleep(10)
        log = rviz_log.read_text()
        report['rviz'] = {
            'running_after_10s': rviz.poll() is None,
            'renderer_initialized': 'OpenGl version' in log or 'OpenGL version' in log,
            'log': log,
        }
    finally:
        if rviz.poll() is None:
            os.killpg(rviz.pid, signal.SIGTERM)
            rviz.wait(timeout=10)

report_path = out_dir / 'report.json'
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(report_path.read_text())
passed = (report['rclpy']['exit_code'] == 0 and report['packages']['exit_code'] == 0
          and report['pub_sub']['passed'] and report['rviz']['running_after_10s']
          and report['rviz']['renderer_initialized'])
raise SystemExit(0 if passed else 1)
