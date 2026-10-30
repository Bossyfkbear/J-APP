"""User-triggered actual optional model inference against synthetic, private audio.

This is separate from ordinary unit tests, and never installs or downloads models.
It cannot prove perceptual quality, model generalization or physical playback.
Run with the selected external .apt-ai Python 3.11 environment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
# Frozen EXE distribution stages pure Python AI worker sources in /worker.
WORKER = ROOT / "worker"
if WORKER.is_dir():
    sys.path.insert(0, str(WORKER))
else:
    sys.path.insert(0, str(ROOT))

MODULES = ('denoise', 'split', 'meter', 'pitch', 'dereverb')
MODEL_DIRS = {'denoise': 'DeepFilterNet3', 'split': 'Demucs', 'meter': 'BeatThis'}


def synthetic_source(path: Path, *, rate: int = 48000, duration: int = 8) -> Path:
    """Create deterministic low-level sound with voiced tone and clear beats."""
    import numpy as np
    import soundfile as sf
    if not 8000 <= rate <= 96000 or not 5 <= duration <= 20:
        raise ValueError('Unsupported synthetic-audio settings')
    t = np.arange(rate * duration, dtype=np.float64) / rate
    voice = .035 * np.sin(2*np.pi*220*t) + .014*np.sin(2*np.pi*440*t)
    clicks = np.zeros_like(voice)
    click = .08 * np.hanning(int(rate * .02))
    for second in np.arange(0,duration,.5):
        start = int(second*rate)
        stop = min(len(clicks),start+len(click))
        clicks[start:stop] += click[:stop-start]
    noise = np.random.default_rng(2026).normal(0,.003,len(voice))
    audio = np.column_stack((voice+clicks+noise, .9*voice+clicks*.7+noise*.7))
    sf.write(path,audio,rate,subtype='PCM_24')
    return path


def digest(path):
    result = hashlib.sha256()
    with open(path,'rb') as f:
        while block := f.read(1024*1024):
            result.update(block)
    return result.hexdigest()


def verify_result(module, result, destination):
    """Output checks, never an AI sound-quality rating."""
    import soundfile as sf
    from apt.quality import inspect_audio
    if module in ('denoise','dereverb'):
        if not destination.is_file():
            raise RuntimeError('AI worker did not publish WAV output')
        info=inspect_audio(destination)
        if not info['frames'] or any(info['nonfinite_samples']):
            raise RuntimeError('AI output was empty or contained NaN/Infinity')
        return {'frames':info['frames'],'sample_rate':info['sample_rate'],
                'channels':info['channels'],'sample_peak':info['sample_peak']}
    if module=='split':
        if not destination.is_dir():
            raise RuntimeError('AI worker did not publish stems')
        stems=sorted(destination.glob('*.wav'))
        if len(stems)<2:
            raise RuntimeError('Expected at least two separate stems')
        details={}
        for stem in stems:
            info=inspect_audio(stem)
            if not info['frames'] or any(info['nonfinite_samples']):
                raise RuntimeError('Stem missing or contains nonfinite samples: '+stem.name)
            details[stem.name]={'frames':info['frames'],'rate':info['sample_rate'],
                                'channels':info['channels']}
        return {'stems':details}
    if not isinstance(result,dict):
        raise RuntimeError('Analysis model returned non-dictionary result')
    if module=='pitch' and not result:
        raise RuntimeError('Pitch model returned empty result')
    if module=='meter' and not isinstance(result.get('beat_seconds'),list):
        raise RuntimeError('Beat model did not produce beat timeline')
    return {'result_keys':sorted(result.keys())}


def run(module, root=ROOT):
    """Run a single installed model, with no customer audio and no internet."""
    if module not in MODULES:
        raise ValueError('Unknown module')
    from apt.worker import run_job
    root=Path(root).resolve()
    model=root/'models'/MODEL_DIRS[module] if module in MODEL_DIRS else None
    if model is not None and not model.is_dir():
        raise FileNotFoundError(f'Local {MODEL_DIRS[module]} model is not installed. '
                                f'Set up this module with --with-models first.')
    with tempfile.TemporaryDirectory(prefix='apt_ai_verify_') as temp:
        directory=Path(temp)
        source=synthetic_source(directory/'synthetic_input.wav')
        checksum=digest(source)
        dest=directory/('stems' if module=='split' else 'output.wav')
        kwargs={'model_dir':str(model) if model else None}
        if module not in ('pitch','meter'):
            kwargs['destination']=str(dest)
        started=time.monotonic()
        result=run_job(module,source,**kwargs)
        metrics=verify_result(module,result,dest)
        if digest(source)!=checksum:
            raise RuntimeError('Synthetic input changed during model inference')
        return {'module':module, 'status':'pass', 'real_model_inference':True,
                'used_customer_audio':False, 'downloaded_model':False,
                'source_sha256_unchanged':True,
                'elapsed_seconds':round(time.monotonic()-started,2),
                'measurements':metrics,
                'limitations':'Synthetic processing passed; does not certify studio audio transparency, latency, or U87 behavior.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Run one already-installed offline neural/audio module on synthetic test audio')
    parser.add_argument('--module', choices=MODULES)
    parser.add_argument('--list',action='store_true',help='List supported modules without loading them')
    parser.add_argument('--report',type=Path,help='Optional new JSON report path; never overwrite')
    args=parser.parse_args(argv)
    if args.list:
        print(json.dumps({'modules':list(MODULES),'model_download':False},indent=2))
        return 0
    if args.module is None:
        parser.error('--module is required unless --list is supplied')
    try:
        result=run(args.module)
        if args.report:
            from apt.files import publish_file
            args.report.parent.mkdir(parents=True,exist_ok=True)
            if args.report.exists():
                raise FileExistsError(args.report)
            with tempfile.TemporaryDirectory(prefix='.apt_ai_report_',dir=args.report.parent) as directory:
                staged=Path(directory)/args.report.name
                staged.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                publish_file(staged,args.report)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,RuntimeError,ImportError) as exc:
        print(json.dumps({'module':args.module,'status':'fail',
                          'real_model_inference':False,
                          'error':f'{type(exc).__name__}: {exc}'},
                         ensure_ascii=False,indent=2),file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
