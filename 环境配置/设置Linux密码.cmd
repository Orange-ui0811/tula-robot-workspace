@echo off
chcp 65001 >nul
title 设置 Ubuntu 用户 l 的密码
echo 为 Ubuntu 用户 l 设置你自己的 Linux 密码。
echo 输入时屏幕不会显示字符，这是正常现象。请勿把密码发到聊天中。
wsl.exe --distribution Ubuntu-24.04 --user root --cd / --exec passwd l
pause
