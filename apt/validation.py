"""Full-file native-rate comparison. Technical evidence, not perceptual scoring."""
from pathlib import Path
import numpy as np
import soundfile as sf


def compare_audio(first, second, cancelled=None):
    with sf.SoundFile(first) as a, sf.SoundFile(second) as b:
        result = {'source': str(Path(first)), 'output': str(Path(second)),
                  'source_rate': a.samplerate, 'output_rate': b.samplerate,
                  'source_channels': a.channels, 'output_channels': b.channels,
                  'source_frames': a.frames, 'output_frames': b.frames,
                  'source_subtype': a.subtype, 'output_subtype': b.subtype,
                  'duration_difference_seconds': b.frames / b.samplerate - a.frames / a.samplerate,
                  'comparison': 'Native-rate, same-position decoded samples; no downmix, alignment or gain change.'}
        if a.samplerate != b.samplerate or a.channels != b.channels:
            result.update(samples_comparable=False, decoded_samples_identical=False,
                          reason='Sample rate or channel count differs; numerical subtraction would be misleading.')
            return result
        result['samples_comparable'] = True
        n = min(a.frames, b.frames)
        if not n:
            raise ValueError('Cannot compare empty audio')
        c = a.channels
        sum_a = np.zeros(c); sum_b = np.zeros(c)
        aa = np.zeros(c); bb = np.zeros(c); ab = np.zeros(c)
        dd = np.zeros(c); peak = np.zeros(c)
        differing = np.zeros(c, dtype='int64')
        left = n
        while left:
            if cancelled and cancelled():
                raise RuntimeError('已取消')
            count = min(left, 262144)
            x = a.read(count, dtype='float64', always_2d=True)
            y = b.read(count, dtype='float64', always_2d=True)
            if not np.isfinite(x).all() or not np.isfinite(y).all():
                raise ValueError('Nonfinite samples prevent a valid comparison')
            delta = x - y
            differing += np.count_nonzero(x != y, axis=0)
            sum_a += x.sum(0); sum_b += y.sum(0)
            aa += np.sum(x*x, 0); bb += np.sum(y*y, 0); ab += np.sum(x*y, 0)
            dd += np.sum(delta*delta, 0); peak = np.maximum(peak, np.max(np.abs(delta), 0))
            left -= count
        denominator = np.sqrt(np.maximum(0, aa-sum_a**2/n) * np.maximum(0, bb-sum_b**2/n))
        correlation = [(float(np.clip((ab[i]-sum_a[i]*sum_b[i]/n)/denominator[i], -1, 1))
                        if denominator[i] > 1e-20 else None) for i in range(c)]
        rms = np.sqrt(dd / n)
        result.update(compared_frames=n, differing_samples_per_channel=differing.tolist(),
                      decoded_samples_identical=bool(a.frames == b.frames and not differing.any()),
                      difference_peak=peak.tolist(), difference_rms=rms.tolist(),
                      difference_rms_dbfs=[float(20*np.log10(v)) if v > 0 else None for v in rms],
                      correlation=correlation,
                      unpaired_source_frames=a.frames-n, unpaired_output_frames=b.frames-n,
                      limitation='A numerical difference is not a sound-quality score. Decoded-sample identity does not imply identical container metadata.')
        return result
