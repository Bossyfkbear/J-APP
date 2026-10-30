"""Explicit setup step: fetch pinned official models, never called by inference."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile
import argparse

MODELS = {
    'BeatThis': ('https://cloud.cp.jku.at/public.php/dav/files/7ik4RrBKTS273gp/final0.ckpt',
                 '8c328b45f59d8dd3dff219253ff6a8d6482be57d0133a29140e2febbf8eb8331'),
    'DeepFilterNet3': ('https://raw.githubusercontent.com/Rikorose/DeepFilterNet/main/models/DeepFilterNet3.zip',
                       '49c52edc8947ae1f9bf50d81530beaf3a2c3245aeaf34b6f31ff535cd22284d2'),
    'Demucs': ('https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th',
               '8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4'),
}


def install(name, directory):
    url, expected = MODELS[name]
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    if target.exists():
        print(f'Preserved existing model directory: {target}')
        return
    with tempfile.TemporaryDirectory(prefix='.apt_model_', dir=directory) as temp:
        root = Path(temp)
        package = root / 'download'
        digest = hashlib.sha256()
        with urllib.request.urlopen(url, timeout=60) as response, package.open('xb') as output:
            while block := response.read(1024 * 1024):
                output.write(block)
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError(f'{name}: SHA256 differs from the reviewed model; nothing installed')
        staged = root / name
        if name == 'DeepFilterNet3':
            with zipfile.ZipFile(package) as archive:
                for entry in archive.infolist():
                    path = root / entry.filename
                    if not path.resolve().is_relative_to(staged) or ((entry.external_attr >> 16) & 0o170000) == 0o120000:
                        raise ValueError('Unexpected model archive path')
                archive.extractall(root)
        elif name == 'BeatThis':
            staged.mkdir()
            shutil.move(str(package), staged / 'final0.ckpt')
        else:
            staged.mkdir()
            shutil.move(str(package), staged / '955717e8-8726e21a.th')
            (staged / 'htdemucs.yaml').write_text("models: ['955717e8']\n", encoding='utf-8')
        manifest = {'name': name, 'source': url, 'download_sha256': expected,
                    'files': {str(p.relative_to(staged)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in staged.rglob('*') if p.is_file()}}
        (staged / 'APT_PROVENANCE.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        if target.exists():
            raise FileExistsError(target)
        staged.rename(target)
        print(f'Installed verified {name}: {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download pinned official models for subsequent offline use')
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'models')
    args = parser.parse_args()
    for name in MODELS:
        install(name, args.directory)
