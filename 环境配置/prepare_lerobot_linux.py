from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import hashlib
import json
import shutil

archive = Path('/mnt/e/迈瑞博/程序文件/TULA_Robot_Workspace.zip')
workspace = Path.home() / 'lerobot_workspace'
destination = workspace / 'lerobot'
prefix = 'TULA_Robot_Workspace/lerobot/'
excluded = {'.git', '.venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
if destination.exists() and any(destination.iterdir()):
    raise SystemExit(f'Refusing to overwrite existing source: {destination}')
destination.mkdir(parents=True, exist_ok=True)
count = 0
with ZipFile(archive) as z:
    for info in z.infolist():
        if not info.filename.startswith(prefix) or info.is_dir():
            continue
        relative = PurePosixPath(info.filename[len(prefix):])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Unsafe archive entry: {info.filename}')
        if excluded.intersection(relative.parts) or relative.suffix in {'.pyc', '.pyo', '.pyd'}:
            continue
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            continue
        target = destination.joinpath(*relative.parts)
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError(f'Entry leaves source directory: {info.filename}')
        target.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as src, target.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        count += 1
source_info = {
    'archive': str(archive),
    'source': str(destination),
    'source_version': '0.6.2',
    'files_extracted': count,
    'pyproject_sha256': hashlib.sha256((destination / 'pyproject.toml').read_bytes()).hexdigest(),
    'uv_lock_sha256': hashlib.sha256((destination / 'uv.lock').read_bytes()).hexdigest(),
    'excluded': sorted(excluded),
}
(workspace / 'source-origin.json').write_text(json.dumps(source_info, indent=2))
print(json.dumps(source_info, indent=2))
