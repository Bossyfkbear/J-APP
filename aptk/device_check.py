"""User-initiated, low-volume physical speaker test. Never runs automatically."""
import math


def make_test_tone(*, sample_rate=48000, duration=1.0, frequency=660.0, level_dbfs=-30.0):
    import numpy as np
    if not (8000 <= sample_rate <= 192000):
        raise ValueError('Unsupported playback sample rate')
    if not (0.25 <= duration <= 2.0):
        raise ValueError('Test duration must be 0.25–2 seconds')
    if not (100 <= frequency <= min(2000, sample_rate / 4)):
        raise ValueError('Test tone frequency out of safe range')
    if not (-48 <= level_dbfs <= -24):
        raise ValueError('Test tone must be low-volume (-48 to -24 dBFS)')
    n = int(sample_rate * duration)
    t = np.arange(n, dtype=np.float64) / sample_rate
    fade = min(n//2, int(sample_rate * .05))
    envelope = np.ones(n)
    envelope[:fade] = np.linspace(0,1,fade,endpoint=False)
    envelope[-fade:] = np.linspace(1,0,fade,endpoint=True)
    signal = np.sin(t * (2 * math.pi * frequency)) * envelope * (10 ** (level_dbfs/20))
    result = np.column_stack((signal,signal)).astype('float32')
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite speaker test tone')
    return result


def play_speaker_test():
    import sounddevice as sd
    outputs = [d for d in sd.query_devices() if d['max_output_channels'] >= 2]
    if not outputs:
        raise RuntimeError('No stereo output device detected')
    test = make_test_tone()
    # Explicit user action only. PortAudio uses current default stereo output.
    sd.play(test, samplerate=48000, blocking=True)
    return {'played': True, 'level_dbfs': -30, 'duration_seconds': 1,
            'confirmed_heard': False,
            'note': 'A successful API call cannot prove that audio was audible; user must confirm.'}
