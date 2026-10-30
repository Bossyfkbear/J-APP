"""Thin offline adapter to the official Beat This! beat/downbeat model."""
from pathlib import Path
import numpy as np
import soundfile as sf


def analyze_meter(path, model_dir=None, max_seconds=180):
    checkpoint = Path(model_dir).expanduser().resolve() if model_dir else None
    if checkpoint and checkpoint.is_dir():
        checkpoint = checkpoint / 'final0.ckpt'
    if checkpoint is None or not checkpoint.is_file():
        raise ValueError('Select a local Beat This! model folder containing final0.ckpt')
    with sf.SoundFile(path) as f:
        rate = f.samplerate
        total = f.frames
        raw = f.read(int(rate * max_seconds), dtype='float32', always_2d=True)
    if len(raw) < rate * 4 or not np.isfinite(raw).all():
        raise ValueError('Beat tracking requires at least four seconds of finite audio')
    from beat_this.inference import Audio2Beats
    # An open local checkpoint is accepted by torch.load. This avoids upstream's
    # filename-not-found path that would otherwise try downloading a model.
    with checkpoint.open('rb') as handle:
        tracker = Audio2Beats(checkpoint_path=handle, device='cpu', float16=False, dbn=False)
    beats, downbeats = tracker(raw, rate)
    duration = len(raw) / rate
    beats, downbeats = (np.asarray(values, dtype=float) for values in (beats, downbeats))
    for values in (beats, downbeats):
        if values.ndim != 1 or not np.isfinite(values).all() or np.any(np.diff(values)<=0):
            raise ValueError('Beat This! returned an invalid timeline')
        if len(values) and (values[0]<0 or values[-1]>duration+.05):
            raise ValueError('Beat This! returned timestamps outside the excerpt')
    intervals = np.diff(beats)
    # Count the model's detected beats between its downbeats; no new meter model.
    bars = [{'start_seconds':float(left), 'end_seconds':float(right),
             'detected_beats':int(np.searchsorted(beats,right-.001)-np.searchsorted(beats,left-.001))}
            for left,right in zip(downbeats[:-1],downbeats[1:])]
    return {'method':'Beat This! 1.1.0 / official minimal postprocessor',
            'model':checkpoint.name, 'network_used':False,
            'tempo_bpm':float(60/np.median(intervals)) if len(intervals) else None,
            'beat_seconds':beats.tolist(), 'downbeat_seconds':downbeats.tolist(),
            'bars':bars, 'time_signature':None,
            'analyzed_seconds':duration, 'truncated':len(raw)<total,
            'limitations':'Model beat/downbeat estimates may be wrong. Counts between detected downbeats do not uniquely establish a notated time signature.'}
