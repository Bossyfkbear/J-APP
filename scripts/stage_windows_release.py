"""Copy external-worker sources and dependency notices into an existing build."""
from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import sys


def stage(destination):
    root = Path(__file__).resolve().parents[1]
    destination = Path(destination).resolve()
    if not (destination / 'AudioPostToolkit.exe').is_file():
        raise FileNotFoundError('Build AudioPostToolkit.exe before staging')
    worker = destination / 'worker'
    worker.mkdir(exist_ok=True)
    for name in ('apt', 'aptk'):
        shutil.copytree(root / name, worker / name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(root / 'ai_worker.py', worker / 'ai_worker.py')
    (destination / 'scripts').mkdir(exist_ok=True)
    shutil.copy2(root / 'scripts' / 'download_models.py', destination / 'scripts' / 'download_models.py')
    for name in ('requirements-ai-windows.txt', 'requirements.txt', 'setup_ai_windows.bat',
                 'setup_ffmpeg_windows.bat',
                 'README.md', 'THIRD_PARTY_NOTICES.md', 'INTEGRATION_STATUS.md',
                 'WINDOWS_BUILD.md', 'AI_COMPATIBILITY.md', 'REUSE_POLICY.md'):
        shutil.copy2(root / name, destination / name)
    shutil.copytree(root / 'validation', destination / 'validation', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    licenses = destination / 'third_party_licenses'
    licenses.mkdir(exist_ok=True)
    python_root = Path(sys.base_prefix)
    native_notices = [python_root / 'LICENSE.txt']
    native_notices.extend((python_root / 'tcl').glob('**/license*'))
    native_notices.extend((python_root / 'tcl').glob('**/LICENSE*'))
    for source in native_notices:
        if source.is_file():
            target = licenses / 'Python-Tcl-Tk' / source.relative_to(python_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    inventory = []
    for dist in metadata.distributions():
        name = dist.metadata['Name']
        if not name:
            continue
        safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
        copied = []
        for entry in dist.files or []:
            if not any(part.lower().startswith(('license', 'copying', 'notice')) for part in entry.parts):
                continue
            source = Path(dist.locate_file(entry))
            if source.is_file():
                target = licenses / safe / str(entry)
                if not target.resolve().is_relative_to((licenses / safe).resolve()):
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied.append(str(target.relative_to(destination)))
        inventory.append({'package': name, 'version': dist.version,
                          'license_metadata': dist.metadata.get('License-Expression') or dist.metadata.get('License'),
                          'license_files': copied})
    (destination / 'build-dependencies.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Staged external AI worker and {len(inventory)} dependency records')


if __name__ == '__main__':
    stage(sys.argv[1])
