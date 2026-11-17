#!/usr/bin/env bash
set -Eeuo pipefail
unset PYTHONPATH PYTHONHOME
export UV_HTTP_TIMEOUT=120
export UV_HTTP_RETRIES=3
export UV_LINK_MODE=copy
export UV_PYTHON_DOWNLOADS=never
WORKSPACE=/home/l/lerobot_workspace
TOOLS=/home/l/.local/share/lerobot-tools
cd "$WORKSPACE/lerobot"
if [[ ! -x "$TOOLS/bin/uv" ]]; then
    python3 -m venv "$TOOLS"
    "$TOOLS/bin/python" -m pip install --index-url https://pypi.org/simple --upgrade pip uv
fi
"$TOOLS/bin/uv" sync --locked --python /usr/bin/python3 \
    --extra core_scripts --extra training --extra pusht
"$TOOLS/bin/uv" pip check --python .venv/bin/python
"$TOOLS/bin/uv" pip freeze --python .venv/bin/python > "$WORKSPACE/installed-requirements.txt"
cat > "$WORKSPACE/activate.sh" <<'ACTIVATE'
# LeRobot dedicated shell: ROS2 has its own launch entry.
unset PYTHONPATH PYTHONHOME
export PATH="/home/l/.local/share/lerobot-tools/bin:$PATH"
source /home/l/lerobot_workspace/lerobot/.venv/bin/activate
cd /home/l/lerobot_workspace/lerobot
export HF_HOME=/home/l/lerobot_workspace/cache/huggingface
export HF_HUB_DISABLE_TELEMETRY=1
export UV_PYTHON_DOWNLOADS=never
export UV_LINK_MODE=copy
export PS1='(LeRobot) \u@\h:\w\$ '
ACTIVATE
mkdir -p "$WORKSPACE/cache/huggingface"
echo LEROBOT_INSTALL_COMPLETE
