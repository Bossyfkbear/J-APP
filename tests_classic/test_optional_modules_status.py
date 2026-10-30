"""Optional module diagnostics never download or infer audio."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json

from apt.diagnostics import inspect_optional_modules


def test_absent_external_runtime_is_reported_without_exec(tmp_path):
    with patch('apt.diagnostics.subprocess.run') as runner:
        result = inspect_optional_modules(tmp_path)
    runner.assert_not_called()
    assert result['installed_python'] is None
    assert all(not status['ready_for_manual_test'] for status in result['modules'].values())
    assert result['tested_inference'] is False


def test_installed_modules_are_independent(tmp_path):
    env = tmp_path / '.apt-ai'
    from sys import platform
    py = env / ('Scripts/python.exe' if platform == 'win32' else 'bin/python')
    py.parent.mkdir(parents=True)
    py.write_text('fake python')
    checkpoint=tmp_path/'models'/'BeatThis'/'final0.ckpt'
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b'test-only')
    fake=SimpleNamespace(returncode=0,stdout=json.dumps({
        'torch':True,'torchaudio':True,'beat_this':True,'df':False,
        'demucs':False,'librosa':False,'nara_wpe':False,'scipy':False
    }),stderr='')
    with patch('apt.diagnostics.subprocess.run',return_value=fake) as runner:
        report=inspect_optional_modules(tmp_path)
    runner.assert_called_once()
    assert report['modules']['meter']['ready_for_manual_test'] is True
    assert report['modules']['denoise']['ready_for_manual_test'] is False
    assert report['modules']['split']['ready_for_manual_test'] is False
    assert report['tested_inference'] is False
