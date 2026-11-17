@echo off
setlocal DisableDelayedExpansion
chcp 65001 <nul >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
setlocal EnableDelayedExpansion

echo TULA - select an existing Python environment
echo 1. Conda environment
echo 2. Full path to python.exe
echo 3. System Python ^(python or py^)
echo 4. uv environment ^(default: script directory's .venv^)
set "mode="
set "python="
set "conda="
set /p "mode=Choose [1-4]: "
if "!mode!"=="1" goto conda
if "!mode!"=="2" goto custom
if "!mode!"=="3" goto system
if "!mode!"=="4" goto uv
echo Invalid selection. Run this launcher again to retry.
goto end

:conda
set "conda=!CONDA_EXE!"
if defined conda if /i not "!conda:~-4!"==".exe" set "conda="
if defined conda if not exist "!conda!" set "conda="
if not defined conda (where conda.exe >nul 2>nul && set "conda=conda.exe")
for %%D in (miniconda3 anaconda3) do (
    if not defined conda if exist "!USERPROFILE!\%%D\Scripts\conda.exe" set "conda=!USERPROFILE!\%%D\Scripts\conda.exe"
    if not defined conda if exist "!LOCALAPPDATA!\%%D\Scripts\conda.exe" set "conda=!LOCALAPPDATA!\%%D\Scripts\conda.exe"
    if not defined conda if exist "!ProgramData!\%%D\Scripts\conda.exe" set "conda=!ProgramData!\%%D\Scripts\conda.exe"
)
if defined conda goto conda_env
echo Conda was not found. Enter its installation directory, or rerun with option 2.
set "folder="
set /p "folder=Conda installation directory: "
if defined folder set "folder=!folder:"=!"
set "conda=!folder!\Scripts\conda.exe"
if not exist "!conda!" (
    echo Conda executable was not found: !conda!
    goto end
)
:conda_env
set "env="
set /p "env=Conda environment name (e.g. MiRobot): "
if defined env set "env=!env:"=!"
if not defined env (
    echo An environment name is required.
    goto end
)
goto check

:custom
set /p "python=Full path to python.exe: "
if defined python set "python=!python:"=!"
goto interpreter

:system
python.exe -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "python=python.exe"
    goto check
)
py.exe -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "python=py.exe"
    goto check
)
echo No working system Python was found. Rerun with option 1, 2 or 4.
goto end

:uv
set "folder=.venv"
set /p "folder=Existing uv environment directory [ .venv ]: "
set "folder=!folder:"=!"
set "python=!folder!\Scripts\python.exe"
:interpreter
if not exist "!python!" (
    echo Python executable was not found: !python!
    goto end
)
:check
if defined conda (
    "!conda!" run --no-capture-output -n "!env!" python -c "import serial; assert tuple(map(int, serial.VERSION.split('.')[:2])) >= (3, 5), 'pyserial >= 3.5 is required'"
) else (
    "!python!" -c "import serial; assert tuple(map(int, serial.VERSION.split('.')[:2])) >= (3, 5), 'pyserial >= 3.5 is required'"
)
if errorlevel 1 (
    echo Python/environment is unavailable, or pyserial 3.5+ is missing.
    echo Check the error above. If needed, install manually and rerun:
    if defined conda (
        echo "!conda!" run -n "!env!" python -m pip install "pyserial>=3.5"
    ) else if "!mode!"=="4" (
        echo uv pip install --python "!python!" "pyserial>=3.5"
    ) else (
        echo "!python!" -m pip install "pyserial>=3.5"
    )
    goto end
)
if defined conda (
    "!conda!" run --no-capture-output -n "!env!" python tula_windows_menu.py
) else (
    "!python!" tula_windows_menu.py
)
echo Program exited.
:end
echo.
pause
