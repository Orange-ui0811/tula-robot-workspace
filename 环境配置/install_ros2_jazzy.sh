#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

if [[ $(id -u) -ne 0 ]]; then
  echo 'Run this installer as root.' >&2
  exit 1
fi
. /etc/os-release
if [[ ${ID} != ubuntu || ${VERSION_ID} != 24.04 ]]; then
  echo 'This installer requires Ubuntu 24.04.' >&2
  exit 1
fi

exec > >(tee -a /var/log/ros2-jazzy-setup.log) 2>&1
trap 'echo "Installation failed at line $LINENO (exit $?)"' ERR

configure_mirrors() {
  python3 - <<'PY'
from pathlib import Path
backup_dir = Path('/var/backups/ros2-jazzy-setup')
backup_dir.mkdir(exist_ok=True)
for filename in ('ubuntu.sources', 'ros2.sources'):
    p = Path('/etc/apt/sources.list.d') / filename
    if not p.exists():
        continue
    text = p.read_text()
    backup = backup_dir / filename
    if not backup.exists():
        backup.write_text(text)
    text = text.replace('http://archive.ubuntu.com/ubuntu/', 'https://mirrors.tuna.tsinghua.edu.cn/ubuntu/')
    text = text.replace('http://security.ubuntu.com/ubuntu/', 'https://mirrors.tuna.tsinghua.edu.cn/ubuntu/')
    text = text.replace('http://packages.ros.org/ros2/ubuntu', 'https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu')
    if filename == 'ros2.sources':
        text = text.replace('Types: deb deb-src', 'Types: deb')
    if p.is_symlink():
        p.unlink()
    p.write_text(text)
PY
}

if [[ ${1:-} != --finish ]]; then
echo 'STEP 1/6: Ubuntu packages and locale'
configure_mirrors
apt-get update
apt-get upgrade -y
apt-get install -y ca-certificates curl locales software-properties-common git build-essential python3-venv
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
add-apt-repository -y universe

echo 'STEP 2/6: Official ROS apt source'
curl --fail --location --retry 3 --connect-timeout 30 \
  https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  --output /tmp/ros-apt-source-release.json
ROS_APT_SOURCE_VERSION=$(python3 -c 'import json; print(json.load(open("/tmp/ros-apt-source-release.json"))["tag_name"])')
curl --fail --location --retry 3 --connect-timeout 30 \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.noble_all.deb" \
  --output /tmp/ros2-apt-source.deb
dpkg -i /tmp/ros2-apt-source.deb
configure_mirrors

echo 'STEP 3/6: ROS2 Jazzy desktop and development tools'
apt-get update
apt-get install -y ros-jazzy-desktop ros-dev-tools \
  ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher-gui mesa-utils

echo 'STEP 4/6: Development user and workspace'
DEV_USER=l
if ! id "$DEV_USER" >/dev/null 2>&1; then
  adduser --disabled-password --gecos '' "$DEV_USER"
fi
usermod -aG sudo,dialout,video "$DEV_USER"
install -d -o "$DEV_USER" -g "$DEV_USER" "/home/$DEV_USER/ros2_ws/src"
python3 - <<'PY'
from pathlib import Path
import configparser
p = Path('/etc/wsl.conf')
c = configparser.ConfigParser()
if p.exists():
    c.read(p)
for section in ('boot', 'user'):
    if not c.has_section(section):
        c.add_section(section)
c['boot']['systemd'] = 'true'
c['user']['default'] = 'l'
with p.open('w') as f:
    c.write(f)
p = Path('/home/l/.bashrc')
s = p.read_text()
marker = '# ROS2 Jazzy development environment'
if marker not in s:
    s += '\n' + marker + '\nsource /opt/ros/jazzy/setup.bash\n'
    s += 'if [ -f "$HOME/ros2_ws/install/setup.bash" ]; then\n'
    s += '    source "$HOME/ros2_ws/install/setup.bash"\nfi\n'
    p.write_text(s)
PY
chown "$DEV_USER:$DEV_USER" "/home/$DEV_USER/.bashrc"
fi

echo 'STEP 5/6: Initialize rosdep'
install -d /etc/ros/rosdep/sources.list.d
curl --fail --location --retry 3 --connect-timeout 30 \
  https://mirrors.tuna.tsinghua.edu.cn/rosdistro/rosdep/sources.list.d/20-default.list \
  --output /tmp/rosdep-default.list
python3 - <<'PY'
from pathlib import Path
p = Path('/etc/ros/rosdep/sources.list.d/20-default.list')
s = Path('/tmp/rosdep-default.list').read_text()
s = s.replace('https://raw.githubusercontent.com/ros/rosdistro/master',
              'https://mirrors.tuna.tsinghua.edu.cn/rosdistro')
s = '\n'.join(line for line in s.splitlines() if not line.lstrip().startswith('gbpdistro ')) + '\n'
p.write_text(s)
p = Path('/home/l/.config/rosdistro/config.yaml')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text('index_url: https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml\n')
PY
chown -R l:l /home/l/.config/rosdistro
runuser -u l -- rosdep update --rosdistro jazzy

echo 'STEP 6/6: Record package versions'
dpkg-query -W ros-jazzy-desktop ros-dev-tools ros-jazzy-rviz2 python3-colcon-common-extensions
apt-get clean
echo 'ROS2_JAZZY_INSTALL_COMPLETE'
