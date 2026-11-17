"""Importing this package registers the config without loading TD-201."""
from .config import TulaRobotConfig
from .robot import TulaRobot

__all__ = ["TulaRobot", "TulaRobotConfig"]
