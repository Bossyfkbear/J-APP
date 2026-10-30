"""Monophonic fundamental-frequency tracking through pYIN, not note transcription."""
import numpy as np
import soundfile as sf


def track_pitch(path, max_seconds=600):
    import librosa
    with sf.SoundFile(path) as source:
        rate = source.samplerate
        channels = source.channels
        total = source.frames
        raw = source.read(int(rate * max_seconds), dtype='float32', always_2d=True)
    if len(raw) < .1 * rate or not np.isfinite(raw).all():
        raise ValueError('Pitch analysis requires finite audio at least 0.1 seconds long')
    channel = int(np.argmax(np.mean(raw.astype('float64') ** 2, axis=0)))
    mono = librosa.resample(raw[:, channel], orig_sr=rate, target_sr=16000)
    f0, voiced, probabilities = librosa.pyin(mono, sr=16000, fmin=50., fmax=1200.,
                                           frame_length=1024, hop_length=160)
    frames = []
    for i, (hz, active, probability) in enumerate(zip(f0, voiced, probabilities)):
        timestamp = i * .01
        if timestamp >= len(raw) / rate:
            break
        valid = bool(active) and bool(np.isfinite(hz))
        midi = 69 + 12 * np.log2(hz / 440) if valid else None
        frames.append({'seconds': round(timestamp, 3), 'hz': round(float(hz), 3) if valid else None,
                       'note': librosa.midi_to_note(int(round(midi))) if valid else None,
                       'cents_from_note': round(float(100 * (midi - round(midi))), 1) if valid else None,
                       'voiced_probability': round(float(probability), 4) if np.isfinite(probability) else None})
    valid_hz = [frame['hz'] for frame in frames if frame['hz'] is not None]
    return {'method': 'pYIN / librosa', 'source_channels': channels,
            'analysis_channel_1_based': channel + 1, 'analysis_rate': 16000,
            'analyzed_seconds': len(raw) / rate, 'truncated': len(raw) < total,
            'median_voiced_hz': float(np.median(valid_hz)) if valid_hz else None,
            'frames': frames,
            'limitations': 'Monophonic voice/instrument estimate, 50–1200 Hz; polyphony, noise and octave errors require review. Voicing probability is not calibrated pitch accuracy.'}
