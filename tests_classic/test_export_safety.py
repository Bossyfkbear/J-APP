"""Regression checks for interrupted/colliding exports and loudness targets."""
import errno
import os
import hashlib
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from apt.files import publish_file
from apt.worker import _publish
from aptk import core


@pytest.fixture
def source(tmp_path):
    core.CANCEL.clear()
    p = tmp_path / '原音.wav'
    t = np.arange(48000 * 5) / 48000
    sf.write(p, .08 * np.sin(2*np.pi*997*t), 48000, subtype='PCM_24')
    yield p
    core.CANCEL.clear()


def test_no_hardlinks_supports_audio_and_stems_without_overwrite(source, tmp_path):
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    with patch('apt.files.os.link', side_effect=OSError(errno.ENOTSUP, 'unsupported')):
        out = core.convert(source, {'destination': str(tmp_path / 'out')})
        np.testing.assert_array_equal(sf.read(source)[0], sf.read(out)[0])
        with pytest.raises(FileExistsError):
            publish_file(source, out)
        stems = tmp_path / 'staged'
        stems.mkdir()
        (stems / 'vocals.wav').write_bytes(source.read_bytes())
        _publish(stems, tmp_path / 'stems')
        assert (tmp_path / 'stems' / 'vocals.wav').read_bytes() == source.read_bytes()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original


def test_failed_fallback_copy_removes_only_its_partial_file(source, tmp_path):
    target = tmp_path / 'out.wav'
    def fail_copy(reader, writer, **kwargs):
        writer.write(reader.read(32))
        raise OSError(errno.ENOSPC, 'disk full')
    with patch('apt.files.os.link', side_effect=OSError(errno.ENOTSUP, 'unsupported')):
        with patch('apt.files.shutil.copyfileobj', side_effect=fail_copy):
            with pytest.raises(OSError, match='disk full'):
                publish_file(source, target)
    assert not target.exists()
    assert sf.info(source).frames == 240000


@pytest.mark.parametrize('operation', ['residual', 'rename', 'report'])
def test_output_collision_never_removes_or_replaces_existing_file(source, tmp_path, operation):
    target = tmp_path / 'already-owned.wav'
    target.write_bytes(b'keep this existing file')
    with patch.object(core, 'unique_output', return_value=target):
        with pytest.raises(FileExistsError):
            if operation == 'residual':
                core.noise_residual(source, {})
            elif operation == 'rename':
                core.copy_renamed([source], {}, lambda _: None)
            else:
                core.save_report(source, '_report', {}, 'new report')
    assert target.read_bytes() == b'keep this existing file'


def test_batch_copy_does_not_link_output_to_original(source, tmp_path):
    original = source.read_bytes()
    output = core.copy_renamed([source], {'destination': str(tmp_path/'renamed')}, lambda _: None)[0]
    output.write_bytes(b'edited copy')
    assert source.read_bytes() == original


def test_custom_loudness_targets_and_silence(source, tmp_path):
    original = source.read_bytes()
    out = core.normalize(source, {'target_i': '-23', 'target_tp': '-3', 'target_lra': '7'})
    measured = core.scan_loudness(out)
    assert abs(float(measured['input_i']) + 23) < .2
    assert float(measured['input_tp']) <= -2.95
    assert sf.info(out).samplerate == 48000
    assert source.read_bytes() == original
    silence = tmp_path/'silence.wav'
    sf.write(silence, np.zeros(48000), 48000)
    with pytest.raises(core.ToolkitError, match='有效響度'):
        core.normalize(silence, {})
    assert not list((tmp_path/'APTK_Output').glob('silence_loudnorm*'))


@pytest.mark.skipif(os.name != 'nt', reason='Windows-specific no-overwrite rename semantics')
def test_windows_fallback_does_not_expose_partial_audio(source, tmp_path):
    target = tmp_path / 'result.wav'
    def fail_copy(reader, writer, **kwargs):
        writer.write(reader.read(64))
        raise OSError(errno.ENOSPC, 'disk full')
    with patch('apt.files.os.link', side_effect=OSError(errno.ENOTSUP, 'unsupported')):
        with patch('apt.files.shutil.copyfileobj', side_effect=fail_copy):
            with pytest.raises(OSError, match='disk full'):
                publish_file(source, target)
    assert not target.exists()
    assert not list(tmp_path.glob('*.partial'))
    with patch('apt.files.os.link', side_effect=OSError(errno.ENOTSUP, 'unsupported')):
        publish_file(source, target)
    assert target.read_bytes() == source.read_bytes()


def test_report_publish_error_removes_staging_without_partial_file(source, tmp_path):
    output = tmp_path / 'reports'
    with patch.object(core, 'publish_file', side_effect=OSError(errno.ENOSPC, 'disk full')):
        with pytest.raises(OSError, match='disk full'):
            core.save_report(source, '_analysis', {'destination': str(output)}, '文字報告\n' * 128)
    assert not (output / '原音_analysis.txt').exists()
    assert not list(output.glob('.aptk_report_*'))


def test_cancelled_report_leaves_no_file(source, tmp_path):
    core.CANCEL.set()
    try:
        with pytest.raises(core.ToolkitError, match='已取消'):
            core.save_report(source, '_cancelled', {'destination': str(tmp_path / 'output')}, 'not committed')
        assert not (tmp_path / 'output').exists()
    finally:
        core.CANCEL.clear()


def test_successful_report_preserves_unicode_and_does_not_replace(source, tmp_path):
    output = tmp_path / 'reports'
    opts = {'destination': str(output)}
    first = core.save_report(source, '_analysis', opts, '原音 Unicode\n')
    second = core.save_report(source, '_analysis', opts, '第二份報告\n')
    assert first != second
    assert first.read_text(encoding='utf-8-sig') == '原音 Unicode\n'
    assert second.read_text(encoding='utf-8-sig') == '第二份報告\n'
    assert not list(output.glob('.aptk_report_*'))
