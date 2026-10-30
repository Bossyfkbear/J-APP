"""Machine-readable readiness report; never auto-installs or downloads anything."""
from importlib import metadata, util
import json
import platform
from pathlib import Path
import subprocess
import sys


def inspect_optional_modules(root=None):
    """Report installed optional runtimes WITHOUT loading models or using network."""
    import os
    import json
    import subprocess
    from .worker import app_directory
    root = Path(root) if root is not None else app_directory()
    root = root.absolute()
    models = root / 'models'
    env = root / '.apt-ai'
    candidate = env / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    requirements = {
        'denoise': ('torch', 'torchaudio', 'df'),
        'split': ('torch', 'torchaudio', 'demucs'),
        'meter': ('torch', 'torchaudio', 'beat_this'),
        'pitch': ('librosa',),
        'dereverb': ('nara_wpe', 'scipy'),
    }
    files = {
        'denoise': (models / 'DeepFilterNet3' / 'config.ini').is_file() and
                   (models / 'DeepFilterNet3' / 'checkpoints').is_dir(),
        'split': (models / 'Demucs' / '955717e8-8726e21a.th').is_file() and
                 (models / 'Demucs' / 'htdemucs.yaml').is_file(),
        'meter': (models / 'BeatThis' / 'final0.ckpt').is_file(),
    }
    output = {
        'installed_python': str(candidate) if candidate.is_file() else None,
        'packages': {},
        'modules': {},
        'models_found': files,
        'tested_inference': False,
        'note': 'Read-only package/model presence checks, not neural processing acceptance.',
    }
    if candidate.is_file():
        script = ("import importlib.util,json; names="
                  "['torch','torchaudio','df','demucs','beat_this','librosa','nara_wpe','scipy'];"
                  "print(json.dumps({name:bool(importlib.util.find_spec(name)) for name in names}))")
        flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
        restore_dll = sys.platform == 'win32' and getattr(sys, 'frozen', False)
        if restore_dll:
            import ctypes
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        try:
            result = subprocess.run([str(candidate), '-I', '-c', script],
                                    capture_output=True, text=True, timeout=15,
                                    cwd=str(root), **flags)
            if result.returncode == 0:
                output['packages'] = json.loads(result.stdout)
            else:
                output['error'] = result.stderr[-800:] or f'Python exited {result.returncode}'
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            output['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            if restore_dll:
                import ctypes
                ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
    for module, packages in requirements.items():
        found = all(output['packages'].get(name, False) for name in packages)
        model = bool(files.get(module, True))
        output['modules'][module] = {
            'dependencies_installed': found,
            'local_model_present': model if module in files else None,
            'ready_for_manual_test': found and model,
        }
    return output


def collect(check_gui=False):
    from aptk.core import find_executable
    from .worker import worker_command
    report = {'platform': platform.system(), 'python': platform.python_version(),
              'frozen': bool(getattr(sys, 'frozen', False)), 'executables': {}, 'packages': {},
              'gui': {'tested': False}, 'audio_device': {'tested': False}}
    for name in ('ffmpeg', 'ffprobe', 'ffplay'):
        path = find_executable(name)
        entry = {'path': path, 'available': False}
        if path:
            try:
                flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform=='win32' else {}
                run = subprocess.run([path, '-version'], capture_output=True, text=True, timeout=10, **flags)
                entry.update(available=run.returncode==0, version=run.stdout.splitlines()[0] if run.stdout else '')
            except Exception as exc:
                entry['error'] = str(exc)
        report['executables'][name] = entry
    for name in ('numpy', 'soundfile', 'sounddevice'):
        entry = {'available': util.find_spec(name) is not None}
        try:
            entry['version'] = metadata.version(name)
        except metadata.PackageNotFoundError:
            entry['version'] = 'not exposed by this build'
        report['packages'][name] = entry
    try:
        report['ai_worker_command'] = worker_command()
    except Exception as exc:
        report['ai_worker_error'] = str(exc)
    if check_gui:
        try:
            from aptk.ui import App, TOOL_INFO
            app = App()
            try:
                app.withdraw()
                for tool in TOOL_INFO:
                    app.select_tool(tool)
                    app.update_idletasks()
                report['gui'] = {'tested': True, 'ok': True, 'tool_panels': len(TOOL_INFO)}
            finally:
                app.destroy()
        except Exception as exc:
            report['gui'] = {'tested': True, 'ok': False, 'error': str(exc)}
    try:
        import sounddevice as sd
        devices = list(sd.query_devices())
        report['audio_device'] = {'tested': True, 'output_device_count': sum(d['max_output_channels']>0 for d in devices),
                                  'playback_verified': False}
    except Exception as exc:
        report['audio_device']['error'] = str(exc)
    report['optional_modules'] = inspect_optional_modules()
    report['core_ready'] = all(report['executables'][n]['available'] for n in ('ffmpeg','ffprobe')) and all(report['packages'][n]['available'] for n in ('numpy','soundfile'))
    report['release_verified'] = False
    report['remaining'] = ['Native Windows GUI and real audio-device playback', 'Native neural model inference and listening acceptance', 'User-recording listening acceptance', 'Calibrated U87 source/target measurement data']
    return report



def audio_smoke():
    """Verify a frozen application can convert actual audio without touching input.

    This test uses a distributed synthetic fixture, not user recordings. It
    does not claim physical audio-device or perceptual sound-quality acceptance.
    """
    import hashlib
    import tempfile
    import soundfile as sf
    from apt.worker import app_directory
    from aptk.core import convert

    source = app_directory() / 'validation' / 'audio' / 'enhanced.wav'
    if not source.is_file():
        raise FileNotFoundError(f'Missing bundled test audio: {source}')
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='aptk_smoke_') as temp:
        output = Path(temp)
        first = convert(source, {'destination': str(output), 'fmt': 'wav',
                                 'depth': 'auto'})
        info = sf.info(first)
        if info.samplerate != 48000 or info.channels != 1 or info.subtype != 'FLOAT':
            raise RuntimeError(f'Auto-precision WAV export mismatch: {info}')
        second = convert(source, {'destination': str(output), 'fmt': 'wav',
                                  'depth': '24', 'rate': '44100'})
        result_info = sf.info(second)
        if (result_info.samplerate != 44100 or result_info.channels != 1
                or result_info.subtype != 'PCM_24'):
            raise RuntimeError(f'Resampled PCM-24 export mismatch: {result_info}')
        if first == second or not first.is_file() or not second.is_file():
            raise RuntimeError('Converted outputs missing or overwritten')
        # Confirm a stereo 24-bit session remains stereo/24-bit at the original
        # native sample rate, without changing or linking the source file.
        import numpy as np
        t = np.arange(48000, dtype=np.float64) / 48000.0
        stereo = np.column_stack((.125 * np.sin(2 * np.pi * 440 * t),
                                  .10 * np.sin(2 * np.pi * 997 * t)))
        stereo_source = output / 'Original Stereo 24bit.wav'
        sf.write(stereo_source, stereo, 48000, subtype='PCM_24')
        stereo_digest = hashlib.sha256(stereo_source.read_bytes()).hexdigest()
        stereo_output = convert(stereo_source, {'destination': str(output), 'fmt': 'wav', 'depth': 'auto'})
        stereo_info = sf.info(stereo_output)
        if stereo_info.samplerate != 48000 or stereo_info.channels != 2 or stereo_info.subtype != 'PCM_24':
            raise RuntimeError(f'Stereo PCM-24 source format was not preserved: {stereo_info}')
        original_samples, _ = sf.read(stereo_source, dtype='float64', always_2d=True)
        converted_samples, _ = sf.read(stereo_output, dtype='float64', always_2d=True)
        if not np.array_equal(original_samples, converted_samples):
            raise RuntimeError('Stereo PCM-24 decoded samples differ after lossless conversion')
        if hashlib.sha256(stereo_source.read_bytes()).hexdigest() != stereo_digest:
            raise RuntimeError('Stereo PCM-24 source was modified')
        # Exercise the real, optional microphone matching code IN the frozen EXE.
        from aptk.mic_match import process as mic_match_process
        reference = output / 'Target mic reference.wav'
        sf.write(reference, 0.85 * stereo + 0.15 * np.roll(stereo, 1, axis=0),
                 48000, subtype='PCM_24')
        mic_output = output / 'Matched mic float.wav'
        mic_result = mic_match_process(stereo_source, reference, mic_output, strength=65)
        mic_info = sf.info(mic_output)
        if (mic_info.samplerate, mic_info.channels, mic_info.frames, mic_info.subtype) != (
                48000, 2, 48000, 'FLOAT'):
            raise RuntimeError(f'Frozen microphone match output mismatch: {mic_info}')
        if (mic_result['frames'] != 48000 or
                hashlib.sha256(stereo_source.read_bytes()).hexdigest() != stereo_digest):
            raise RuntimeError('Frozen microphone matching changed the source or length')
    intact = hashlib.sha256(source.read_bytes()).hexdigest() == original
    if not intact:
        raise RuntimeError('Input audio changed during frozen processing')
    return {'ok': True, 'source_sha256_unchanged': intact,
            'auto_float_48k_mono': True, 'pcm24_44100_mono': True,
            'output_collision_avoided': True, 'stereo_pcm24_preserved': True,
            'mic_match_float_stereo_preserved': True,
            'device_playback_tested': False}


def write_audio_smoke(path):
    try:
        report = audio_smoke()
    except Exception as exc:
        report = {'ok': False, 'error': f'{type(exc).__name__}: {exc}',
                  'device_playback_tested': False}
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def write_report(path, check_gui=False):
    report = collect(check_gui)
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(collect('--gui' in sys.argv), ensure_ascii=False, indent=2))
