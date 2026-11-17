"""Use the actual installed LeRobot registry, parser and factory."""
import subprocess
import sys
import tempfile
import unittest


class DiscoveryTest(unittest.TestCase):
    def test_fresh_process_discovers_installed_plugin_and_creates_robot(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = """
import sys
from dataclasses import dataclass
from importlib.metadata import distribution
from unittest.mock import patch
import draccus
from lerobot.robots import Robot, RobotConfig, make_robot_from_config
from lerobot.utils.import_utils import register_third_party_plugins

@dataclass
class Args:
    robot: RobotConfig

assert "lerobot_robot_tula" not in sys.modules
assert distribution("lerobot_robot_tula").metadata["Name"] == "lerobot_robot_tula"
with patch("ctypes.CDLL", side_effect=AssertionError("DLL load forbidden during discovery")):
    register_third_party_plugins()
    assert "lerobot_robot_tula" in sys.modules
    cfg = draccus.parse(Args, args=[
        "--robot.type=tula_robot", "--robot.port=MOCK",
        "--robot.calibration_dir", sys.argv[1],
        "--robot.action_limits_deg", "{joint_1: [-10, 10], joint_2: [-20, 20]}",
    ])
    obj = make_robot_from_config(cfg.robot)
    assert isinstance(obj, Robot)
    assert obj.config.type == obj.name == "tula_robot"
    assert obj.action_features == {"joint_1.pos": float, "joint_2.pos": float}
    assert obj.observation_features == obj.action_features
    assert tuple(obj.config.action_limits_deg["joint_2"]) == (-20, 20)
    assert not obj.is_connected
"""
            result = subprocess.run([sys.executable, "-B", "-c", code, tmp], cwd=tmp,
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
