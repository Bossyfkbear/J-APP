"""Offline, non-AI spectral noise attenuation; explicit and reversible workflow."""
from pathlib import Path
import numpy as np
import soundfile as sf


def spectral_denoise(source, destination, noise_seconds=0.5, reduction_db=12.0):
    """Reduce stationary noise estimated from the first `noise_seconds` of audio.

    Requires a noise-only lead-in. Does not overwrite source, preserve sample rate,
    channels and PCM subtype when possible. Not a replacement for trained AI denoise.
    """
    src, dst = Path(source), Path(destination)
    if src.resolve() == dst.resolve():
        raise ValueError('Output must differ from input')
    if dst.exists():
        raise FileExistsError(dst)
    if not (0.1 <= noise_seconds <= 30 and 0 <= reduction_db <= 36):
        raise ValueError('Noise duration or reduction outside allowed range')
    with sf.SoundFile(src) as reader:
        rate, channels = reader.samplerate, reader.channels
        nfft = 2048 if rate <= 48000 else 4096
        hop = nfft // 2
        if reader.frames < nfft * 2:
            raise ValueError('Audio too short')
        count = min(int(noise_seconds * rate), reader.frames)
        if count < nfft:
            raise ValueError('Noise sample too short; increase noise_seconds')
        # Use a few Hann-windowed frames for a robust stationary-noise estimate.
        noise = reader.read(count, dtype='float64', always_2d=True)
        win = np.hanning(nfft + 1)[:-1]
        spectra = [np.abs(np.fft.rfft(noise[i:i+nfft] * win[:, None], axis=0))
                   for i in range(0, len(noise)-nfft+1, hop)]
        profile = np.median(np.stack(spectra), axis=0)
        reader.seek(0)
        floor = 10 ** (-reduction_db / 20)
        # Periodic Hann, 50% overlap: window-square normalization avoids gain drift.
        prev = np.zeros((hop, channels), dtype='float64')
        dst.parent.mkdir(parents=True, exist_ok=True)
        subtype = reader.subtype if reader.format == 'WAV' and dst.suffix.lower() == '.wav' else None
        try:
            with sf.SoundFile(dst, mode='w', samplerate=rate, channels=channels,
                              subtype=subtype, format='WAV' if dst.suffix.lower()=='.wav' else None) as out:
                buffer = np.zeros((nfft, channels), dtype='float64')
                # Pad by half-window on both ends to protect start and end transients.
                remaining = reader.frames
                readbuf = np.zeros((hop, channels), dtype='float64')
                accum = np.zeros((nfft, channels), dtype='float64')
                weights = np.zeros(nfft, dtype='float64')
                produced = 0
                total_hops = (reader.frames + hop - 1)//hop + 2
                for step in range(total_hops):
                    buffer[:hop] = buffer[hop:]
                    buffer[hop:] = 0
                    if step > 0 and remaining:
                        chunk = reader.read(min(hop, remaining), dtype='float64', always_2d=True)
                        buffer[hop:hop+len(chunk)] = chunk
                        remaining -= len(chunk)
                    spec = np.fft.rfft(buffer * win[:, None], axis=0)
                    magnitude = np.abs(spec)
                    gain = np.clip((magnitude - profile * 1.5) / (magnitude + 1e-12), floor, 1)
                    processed = np.fft.irfft(spec * gain, n=nfft, axis=0) * win[:, None]
                    accum += processed
                    weights += win**2
                    if step:
                        block = accum[:hop] / np.maximum(weights[:hop, None], 1e-10)
                        take = min(hop, reader.frames - produced)
                        if take > 0:
                            out.write(np.clip(block[:take], -1, 1))
                            produced += take
                    accum[:hop] = accum[hop:]
                    accum[hop:] = 0
                    weights[:hop] = weights[hop:]
                    weights[hop:] = 0
        except Exception:
            dst.unlink(missing_ok=True)
            raise
    return {'output': str(dst), 'sample_rate': rate, 'channels': channels,
            'noise_profile_seconds': noise_seconds, 'reduction_db': reduction_db,
            'method': 'stationary spectral attenuation (not AI)'}
