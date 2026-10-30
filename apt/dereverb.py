"""Optional WPE late-reverberation reduction; this is DSP, not a neural model."""
from pathlib import Path
import math
import os
import tempfile
from .files import publish_file


def dereverberate(source, destination, strength=.5):
    import numpy as np
    import soundfile as sf
    from nara_wpe.utils import stft, istft
    from nara_wpe.wpe import wpe
    strength = float(strength)
    if not math.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError('Dereverb strength must be between 0 and 1')
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve() or destination.exists():
        raise FileExistsError('Dereverb requires a new output path')
    info = sf.info(source)
    if info.channels not in (1, 2) or info.frames < info.samplerate // 2:
        raise ValueError('WPE requires at least 0.5 seconds of mono/stereo audio')
    if not 8000 <= info.samplerate <= 192000:
        raise ValueError('WPE supports sample rates from 8 to 192 kHz')
    fft_size = 1 << int(math.ceil(math.log2(info.samplerate * .032)))
    hop = fft_size // 4
    block = info.samplerate * 20
    context = info.samplerate
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.apt_wpe_', dir=destination.parent) as temp:
        staged = Path(temp) / 'output.wav'
        with sf.SoundFile(source) as reader, sf.SoundFile(staged, 'w', samplerate=info.samplerate,
                                                        channels=info.channels, subtype='FLOAT') as writer:
            pending = None
            for start in range(0, info.frames, block):
                left = max(0, start - context)
                right = min(info.frames, start + block + context)
                reader.seek(left)
                raw = reader.read(right - left, dtype='float64', always_2d=True)
                if not np.isfinite(raw).all():
                    raise ValueError('Input contains NaN or infinity')
                if strength and np.max(np.abs(raw)) > 1e-12:
                    spectrum = stft(raw.T, size=fft_size, shift=hop)
                    # Independent channel filters avoid mixing left/right recordings.
                    restored = []
                    for channel in spectrum:
                        estimate = wpe(channel.T[:, None, :], taps=10, delay=3, iterations=3)
                        wave = istft(estimate[:, 0, :].T, size=fft_size, shift=hop)
                        restored.append(wave[:len(raw)])
                    wet = np.asarray(restored).T
                    if wet.shape != raw.shape or not np.isfinite(wet).all():
                        raise ValueError('WPE produced invalid audio')
                    mixed = raw * (1 - strength) + wet * strength
                else:
                    mixed = raw
                offset = start - left
                current = mixed[offset:offset + block + context].copy()
                if pending is not None:
                    count = min(context, len(current), len(pending))
                    ramp = np.linspace(0., 1., count)[:, None]
                    current[:count] = pending[:count] * (1 - ramp) + current[:count] * ramp
                writer.write(current[:block])
                pending = current[block:]
        written = sf.info(staged)
        if written.frames != info.frames or written.channels != info.channels or written.samplerate != info.samplerate:
            raise RuntimeError('WPE export duration or format mismatch')
        publish_file(staged, destination)
    return {'engine': 'NARA-WPE', 'neural': False, 'output': str(destination),
            'sample_rate': info.samplerate, 'frames': info.frames, 'channels': info.channels,
            'subtype': 'FLOAT', 'strength': strength,
            'note': 'Late-reverb reduction is estimated; audition for altered speech and room tone.'}
