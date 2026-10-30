"""Local, cancellable AI jobs. Only the parent publishes completed artifacts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
from .files import publish_file


class JobCancelled(RuntimeError):
    pass


def app_directory():
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent


def worker_command(runtime_python=None):
    root = app_directory()
    configured = runtime_python or os.environ.get('APT_AI_PYTHON')
    external = Path(configured).expanduser() if configured else root / '.apt-ai' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if configured and not external.is_file():
        raise FileNotFoundError(f'AI Python does not exist: {external}')
    if external.is_file():
        script = root / 'worker' / 'ai_worker.py' if getattr(sys, 'frozen', False) else root / 'ai_worker.py'
        if not script.is_file():
            raise FileNotFoundError(f'AI worker source is missing: {script}')
        # Preserve venv symlinks: resolving python to the base interpreter loses
        # its pyvenv.cfg and therefore the environment's installed packages.
        return [str(external.absolute()), str(script)]
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--ai-worker']
    return [sys.executable, str(root / 'ai_worker.py')]


def run_job(operation, source=None, *, model_dir=None, model_name=None,
            split_mode='vocal', destination=None, runtime_python=None, strength=.5,
            cancelled=None, command=None):
    """A terminated child can only leave files inside this job's temporary folder.

    `command` is an internal test seam; GUI/CLI never accept arbitrary commands.
    Cancellation is honored until publication; after commit, completion wins.
    """
    def check_cancel():
        if cancelled and cancelled():
            raise JobCancelled('已取消')

    check_cancel()
    target = Path(destination).resolve() if destination else None
    if operation not in ('status', 'pitch', 'meter') and target is None:
        raise ValueError('An output destination is required')
    if target:
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.apt_job_', dir=target.parent if target else None) as temp:
        folder = Path(temp)
        request = {'operation': operation, 'source': str(Path(source).resolve()) if source else None,
                   'model_dir': str(Path(model_dir).expanduser().resolve()) if model_dir else None,
                   'model_name': model_name, 'split_mode': split_mode, 'strength': strength}
        (folder / 'request.json').write_text(json.dumps(request), encoding='utf-8')
        args = list(command) if command is not None else worker_command(runtime_python)
        flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
        # File-backed logs prevent pipe deadlocks and unbounded memory use.
        with (folder / 'worker.log').open('wb') as log:
            env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
            env['PATH'] = str(app_directory()) + os.pathsep + env.get('PATH', '')
            for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
                env.setdefault(key, str(min(4, os.cpu_count() or 1)))
            # PyInstaller alters library search paths; restore them for external Python.
            if getattr(sys, 'frozen', False) and Path(args[0]).resolve() != Path(sys.executable).resolve():
                for key in ('LD_LIBRARY_PATH', 'LIBPATH'):
                    if key + '_ORIG' in env:
                        env[key] = env[key + '_ORIG']
                    else:
                        env.pop(key, None)
            restore_dll = getattr(sys, 'frozen', False) and os.name == 'nt' and Path(args[0]).resolve() != Path(sys.executable).resolve()
            if restore_dll:
                import ctypes
                ctypes.windll.kernel32.SetDllDirectoryW(None)
            try:
                process = subprocess.Popen(args + [str(folder)], stdin=subprocess.DEVNULL,
                                           stdout=log, stderr=log, env=env, **flags)
            finally:
                if restore_dll:
                    ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
            try:
                while True:
                    check_cancel()
                    try:
                        process.wait(timeout=.1)
                        break
                    except subprocess.TimeoutExpired:
                        pass
                check_cancel()
            finally:
                if process.poll() is None:
                    if os.name == 'nt':
                        # Also stop a decoder that the worker may have launched.
                        try:
                            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
                        except (OSError, subprocess.TimeoutExpired):
                            pass
                        if process.poll() is None:
                            process.terminate()
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        response_path = folder / 'result.json'
        if not response_path.is_file():
            with (folder / 'worker.log').open('rb') as log:
                log.seek(max(0, log.seek(0, 2) - 2000))
                detail = log.read().decode('utf-8', 'replace')
            raise RuntimeError(f'AI worker exited ({process.returncode}): {detail}')
        response = json.loads(response_path.read_text(encoding='utf-8'))
        if process.returncode or not response.get('ok'):
            raise RuntimeError(response.get('error', 'AI worker failed'))
        check_cancel()
        result = response['result']
        if operation in ('status', 'pitch', 'meter'):
            return result
        artifact = folder / 'stems' if operation == 'split' else folder / 'output.wav'
        if not artifact.exists():
            raise RuntimeError('AI worker did not produce its output')
        _publish(artifact, target)
        result['output'] = str(target)
        if isinstance(result.get('quality'), dict):
            result['quality']['path'] = str(target)
        return result


def _publish(artifact, target):
    if artifact.is_file():
        publish_file(artifact, target)
        return
    paths = list(artifact.iterdir())
    if not paths or any(not p.is_file() or p.suffix != '.wav' for p in paths):
        raise RuntimeError('Invalid stem output')
    target.mkdir(exist_ok=False)
    try:
        for path in paths:
            publish_file(path, target / path.name)
    except BaseException:
        import shutil
        shutil.rmtree(target)
        raise


def execute(folder):
    """Child entry. It knows only the temporary destination, never the final one."""
    folder = Path(folder).resolve()
    try:
        request = json.loads((folder / 'request.json').read_text(encoding='utf-8'))
        op = request['operation']
        if op != 'status':
            import soundfile as sf
            try:
                sf.info(request['source'])
            except (RuntimeError, ValueError):
                from aptk.core import require_ffmpeg, run_command
                ffmpeg, _ = require_ffmpeg()
                decoded = folder / 'decoded.wav'
                run_command([ffmpeg, '-nostdin', '-v', 'error', '-n', '-i', request['source'],
                             '-map', '0:a:0', '-vn', '-c:a', 'pcm_s24le', str(decoded)])
                request['source'] = str(decoded)
        if op == 'status':
            from .models import runtime_status
            result = runtime_status(request.get('model_dir'))
        elif op == 'pitch':
            from .pitch import track_pitch
            result = track_pitch(request['source'])
        elif op == 'meter':
            from .meter import analyze_meter
            result = analyze_meter(request['source'], request.get('model_dir'))
        elif op == 'denoise':
            from .models import denoise
            result = denoise(request['source'], folder / 'output.wav', request['model_dir'], preserve_format=True)
        elif op == 'dereverb':
            from .dereverb import dereverberate
            result = dereverberate(request['source'], folder / 'output.wav', request['strength'])
        elif op == 'split':
            from aptk.core import _demucs_split_local
            result_path = _demucs_split_local(Path(request['source']), {
                'destination': str(folder), 'model_dir': request['model_dir'],
                'model_name': request.get('model_name'), 'split_mode': request['split_mode']})
            result_path.rename(folder / 'stems')
            result = {'engine': 'Demucs', 'files': sorted(p.name for p in (folder / 'stems').iterdir())}
        else:
            raise ValueError(f'Unknown operation: {op}')
        response = {'ok': True, 'result': result}
        code = 0
    except BaseException as exc:
        response = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
        code = 1
    (folder / 'result.json').write_text(json.dumps(response, ensure_ascii=False), encoding='utf-8')
    return code
