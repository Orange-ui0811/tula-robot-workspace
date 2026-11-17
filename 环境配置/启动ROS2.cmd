@echo off
chcp 65001 >nul
title Ubuntu 24.04 - ROS2 Jazzy
wsl.exe --distribution Ubuntu-24.04 --user l --cd ~
if errorlevel 1 pause
