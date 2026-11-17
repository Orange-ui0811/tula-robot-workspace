@echo off
chcp 65001 >nul
title LeRobot - Ubuntu 24.04
wsl.exe --distribution Ubuntu-24.04 --user l --cd /home/l/lerobot_workspace/lerobot --exec /bin/bash --rcfile /home/l/lerobot_workspace/activate.sh -i
if errorlevel 1 pause
