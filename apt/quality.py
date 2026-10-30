"""Offline audio integrity checks; no external models or network calls."""
from pathlib import Path
import numpy as np
import soundfile as sf


def inspect_audio(path, blocksize=262144):
    """Streamed PCM integrity report; peak is sample peak, not true peak."""
    p = Path(path)
    with sf.SoundFile(str(p)) as f:
        if f.frames == 0:
            raise ValueError('Empty audio input')
        pcm_bits = {'PCM_U8': 8, 'PCM_16': 16, 'PCM_24': 24, 'PCM_32': 32}.get(f.subtype)
        clip_threshold = 1.0 - 2.0 ** (1 - pcm_bits) if pcm_bits else 1.0
        peaks = np.zeros(f.channels, dtype=np.float64)
        squares = np.zeros(f.channels, dtype=np.float64)
        clipped = np.zeros(f.channels, dtype=np.int64)
        nonfinite = np.zeros(f.channels, dtype=np.int64)
        total = 0
        for chunk in f.blocks(blocksize=blocksize, dtype='float64', always_2d=True):
            finite = np.isfinite(chunk)
            nonfinite += (~finite).sum(axis=0)
            clean = np.where(finite, chunk, 0.)
            peaks = np.maximum(peaks, np.max(np.abs(clean), axis=0))
            squares += np.sum(clean * clean, axis=0)
            clipped += np.sum(np.abs(clean) >= clip_threshold, axis=0)
            total += len(chunk)
        rms = np.sqrt(squares / total)
        to_db = lambda values: [float(20 * np.log10(v)) if v > 0 else None for v in values]
        return {'path': str(p), 'sample_rate': f.samplerate, 'channels': f.channels,
                'frames': total, 'duration_seconds': total / f.samplerate,
                'subtype': f.subtype, 'sample_peak': peaks.tolist(),
                'sample_peak_dbfs': to_db(peaks), 'rms': rms.tolist(),
                'rms_dbfs': to_db(rms), 'clipped_samples': clipped.tolist(),
                'nonfinite_samples': nonfinite.tolist(),
                'warning': 'Sample peak only; not true peak, LUFS or perceptual quality.'}
