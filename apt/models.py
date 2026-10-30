"""Optional, offline neural audio modules. No automatic downloads."""
from pathlib import Path

class ModelUnavailable(RuntimeError):
    pass

def runtime_status(model_dir=None):
    """Report whether the optional neural runtime and local weights are present."""
    from importlib.util import find_spec
    packages = {name: find_spec(name) is not None for name in ('torch', 'torchaudio', 'df')}
    result = {'engine': 'DeepFilterNet', 'packages': packages,
              'runtime_ready': all(packages.values()), 'model_directory': None,
              'model_ready': False, 'network_used': False}
    if model_dir:
        try:
            path = require_local_model(model_dir)
            result['model_directory'] = str(path)
            if result['runtime_ready']:
                _, state, _ = load_deepfilter(path)
                result['model_sample_rate'] = int(state.sr())
                result['model_ready'] = True
        except ModelUnavailable as exc:
            result['model_error'] = str(exc)
        except Exception as exc:
            result['model_error'] = f'{type(exc).__name__}: {exc}'
    result['ready'] = result['runtime_ready'] and result['model_ready']
    return result

def require_local_model(model_dir):
    if not model_dir:
        raise ModelUnavailable('Select an installed local DeepFilterNet model directory.')
    p = Path(model_dir).expanduser().resolve()
    if not p.is_dir() or not any(p.iterdir()):
        raise ModelUnavailable('Local model directory missing or empty.')
    return p

def load_deepfilter(model_dir):
    local = require_local_model(model_dir)
    if not (local / 'config.ini').is_file() or not (local / 'checkpoints').is_dir():
        raise ModelUnavailable('DeepFilterNet model requires config.ini and checkpoints/')
    from df.enhance import init_df
    try:
        return init_df(model_base_dir=str(local), post_filter=False, log_file=None)
    except (Exception, SystemExit) as exc:
        raise ModelUnavailable(f'Cannot load local DeepFilterNet model: {exc}') from exc

def validate_enhancement(audio, expected_samples):
    """Reject corrupt neural output instead of silently writing broken audio."""
    import numpy as np
    values = np.asarray(audio)
    if values.ndim != 1 or values.size != expected_samples:
        raise ValueError(f'AI output length mismatch: {values.size} vs {expected_samples}')
    if not np.all(np.isfinite(values)):
        raise ValueError('AI output contains NaN or infinity')
    return int(values.size)

def denoise(src, dst, model_dir=None, preserve_format=False):
    """DeepFilterNet neural speech enhancement; no silent fallback to DSP.

    DeepFilterNet's 48 kHz processing is intentional; output is 48 kHz WAV.
    Install the optional deepfilternet package separately and provide a local
    model directory. The package may have version-specific API requirements.
    """
    import os
    import tempfile
    import numpy as np
    import soundfile as sf
    source, destination = Path(src), Path(dst)
    if source.resolve() == destination.resolve():
        raise ValueError('Source and output must differ.')
    if destination.exists():
        raise FileExistsError(destination)
    if destination.suffix.lower() != '.wav':
        raise ValueError('AI denoising currently exports WAV only.')
    local = require_local_model(model_dir)
    if not source.is_file():
        raise FileNotFoundError(source)
    try:
        import torch
        import torchaudio
        from df.enhance import init_df, enhance
    except ImportError as exc:
        raise ModelUnavailable('Install optional deepfilternet, torch and torchaudio dependencies.') from exc
    # Initialize only from the explicit local path; never use default model lookup.
    try:
        model, state, _ = load_deepfilter(local)
    except Exception as exc:
        raise ModelUnavailable(f'Cannot load local DeepFilterNet model: {exc}') from exc
    info = sf.info(str(source))
    if info.frames == 0:
        raise ValueError('Empty audio input.')
    # Read through libsndfile to avoid torchaudio decoder backend differences.
    # AI inference is mono-per-channel and never silently downmixes stereo.
    raw, sr = sf.read(str(source), dtype='float32', always_2d=True)
    if not np.all(np.isfinite(raw)):
        raise ValueError('Input audio contains NaN or infinity')
    audio = torch.from_numpy(raw.T.copy())
    model_sr = int(state.sr())
    if sr != model_sr:
        try:
            audio = torchaudio.functional.resample(audio, sr, model_sr)
        except Exception as exc:
            raise ModelUnavailable(f'Cannot resample {sr} Hz audio to model rate {model_sr} Hz: {exc}') from exc
    # DeepFilterNet inference per channel avoids implicit downmixing.
    outputs = []
    with torch.no_grad():
        for channel in audio:
            enhanced = enhance(model, state, channel.unsqueeze(0), pad=True)
            if isinstance(enhanced, np.ndarray):
                enhanced = torch.from_numpy(enhanced)
            samples = enhanced.detach().cpu().reshape(-1).numpy()
            validate_enhancement(samples, int(audio.shape[-1]))
            outputs.append(samples)
    n = int(audio.shape[-1])
    result = np.column_stack([c[:n] for c in outputs])
    output_rate = model_sr
    subtype = 'PCM_24'
    if preserve_format:
        output_rate = sr
        subtype = info.subtype if info.subtype in {'PCM_U8', 'PCM_16', 'PCM_24', 'PCM_32', 'FLOAT', 'DOUBLE'} else 'PCM_24'
        if sr != model_sr:
            result = torchaudio.functional.resample(torch.from_numpy(result.T.copy()), model_sr, sr).numpy().T
        if len(result) < len(raw):
            raise ValueError('Resampled AI output is shorter than the source')
        result = result[:len(raw)]
        n = len(raw)
    if not np.all(np.isfinite(result)):
        raise ValueError('AI output contains NaN or infinity')
    bits = {'PCM_U8': 8, 'PCM_16': 16, 'PCM_24': 24, 'PCM_32': 32}.get(subtype)
    ceiling = 1.0 - 2.0 ** (1 - bits) if bits else 1.0
    if subtype not in ('FLOAT', 'DOUBLE') and (np.max(result) > ceiling or np.min(result) < -1.0):
        raise ValueError('AI output exceeds full scale; refusing clipped PCM export')
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.apt_ai_', suffix='.wav', dir=str(destination.parent))
    os.close(fd)
    try:
        sf.write(tmp, result, output_rate, subtype=subtype)
        from .files import publish_file
        publish_file(tmp, destination)
        os.unlink(tmp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    written = sf.info(str(destination))
    if (written.channels != len(outputs) or written.samplerate != output_rate
            or written.subtype != subtype or written.frames != n):
        destination.unlink(missing_ok=True)
        raise IOError('Export validation failed: WAV format, length or channel count differs')
    from .quality import inspect_audio
    try:
        quality = inspect_audio(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if any(quality['nonfinite_samples']):
        destination.unlink(missing_ok=True)
        raise IOError('Export validation failed: nonfinite samples in WAV')
    return {'output': str(destination), 'engine': 'DeepFilterNet', 'sample_rate': output_rate,
            'model_sample_rate': model_sr, 'subtype': subtype,
            'channels': len(outputs), 'source_sample_rate': sr,
            'frames': written.frames, 'quality': quality,
            'note': 'Neural processing is not bit-perfect; listen for artifacts.'}

def separate_vocals(src, dst, model_dir=None):
    """Separate vocals and accompaniment with a locally installed Demucs model.

    Write 32-bit float WAV stems to retain headroom. No remote model lookup.
    """
    import os
    import tempfile
    import numpy as np
    import soundfile as sf
    source, vocal_path = Path(src), Path(dst)
    backing_path = vocal_path.with_name(vocal_path.stem + '_instrumental.wav')
    if not source.is_file():
        raise FileNotFoundError(source)
    if vocal_path.suffix.lower() != '.wav':
        raise ValueError('Vocal separation exports WAV only')
    if len({source.resolve(), vocal_path.resolve(), backing_path.resolve()}) != 3:
        raise ValueError('Source and output paths must differ')
    if vocal_path.exists() or backing_path.exists():
        raise FileExistsError('Vocal or instrumental output already exists')
    local = require_local_model(model_dir)
    try:
        from .demucs_adapter import infer
    except ImportError as exc:
        raise ModelUnavailable('Install optional Demucs to use vocal separation') from exc
    try:
        mix, stems, model_rate, selected = infer(source, local)
    except ModelUnavailable:
        raise
    except Exception as exc:
        raise ModelUnavailable(f'Cannot load or run local Demucs model: {exc}') from exc
    if 'vocals' not in stems:
        raise ValueError('Selected model has no vocals stem')
    vocals = stems['vocals'].detach().cpu().numpy().T
    instrumental = mix.detach().cpu().numpy().T - vocals
    if vocals.ndim != 2 or instrumental.shape != vocals.shape:
        raise ValueError('Demucs output channel or length mismatch')
    if not np.isfinite(vocals).all() or not np.isfinite(instrumental).all():
        raise ValueError('Demucs output contains NaN or infinity')
    vocal_path.parent.mkdir(parents=True, exist_ok=True)
    pending = []
    published = []
    try:
        for destination, samples in ((vocal_path, vocals), (backing_path, instrumental)):
            fd, temp_name = tempfile.mkstemp(prefix='.apt_stem_', suffix='.wav', dir=destination.parent)
            os.close(fd)
            temp = Path(temp_name)
            pending.append(temp)
            sf.write(temp, samples, model_rate, subtype='FLOAT')
            info = sf.info(temp)
            if info.frames != len(samples) or info.channels != samples.shape[1] or info.subtype != 'FLOAT':
                raise IOError('Stem WAV export validation failed')
        for temp, destination in zip(pending, (vocal_path, backing_path)):
            from .files import publish_file
            publish_file(temp, destination)
            published.append(destination)
    except Exception:
        for path in published:
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in pending:
            path.unlink(missing_ok=True)
    return {'vocals': str(vocal_path), 'instrumental': str(backing_path),
            'engine': 'Demucs', 'model': selected, 'sample_rate': model_rate,
            'channels': vocals.shape[1], 'frames': len(vocals), 'subtype': 'FLOAT'}

def emulate_u87(src, dst, model_dir=None):
    raise ModelUnavailable('U87 modeling requires calibrated paired recordings.')
