"""Bounded, shared-clock A/B audition. Original files are never changed."""
import subprocess
import tempfile
import math
import os
from pathlib import Path


def prepare_pair(source, processed, start=0.0, duration=30.0, *, processed_offset_ms=0., match_loudness=False, return_info=False, sample_rate=48000):
    import numpy as np
    import soundfile as sf
    from .core import require_ffmpeg, stream_info
    if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 192000:
        raise ValueError('Invalid A/B playback sample rate (8000–192000 Hz)')
    if not 0 <= start or not 0.1 <= duration <= 120:
        raise ValueError('Preview start must be nonnegative; duration must be 0.1–120 seconds')
    if not math.isfinite(start) or not math.isfinite(processed_offset_ms) or abs(processed_offset_ms)>2000:
        raise ValueError('Offset must be finite and within ±2000 ms')
    if start + processed_offset_ms/1000 < 0:
        raise ValueError('Offset precedes the start of B; choose a later preview start')
    details = {'processed_offset_ms': processed_offset_ms, 'b_gain_db': 0., 'common_gain_db': 0., 'loudness_matched': False, 'playback_sample_rate': sample_rate}
    ffmpeg, _ = require_ffmpeg()
    paths = (Path(source), Path(processed))
    specs = [stream_info(p) for p in paths]
    if any(ch not in (1, 2) for _, ch, _ in specs):
        raise ValueError('A/B preview currently supports mono and stereo files')
    if specs[0][1] != specs[1][1]:
        raise ValueError('A/B comparison requires matching channel counts')
    arrays = []
    # Standard audition rate only; no change to source or output files.
    with tempfile.TemporaryDirectory(prefix='aptk_ab_') as directory:
        for index, path in enumerate(paths):
            target = Path(directory) / f'{index}.wav'
            command = [ffmpeg, '-hide_banner', '-nostdin', '-loglevel', 'error',
                       '-ss', str(start + (processed_offset_ms/1000 if index else 0)), '-i', str(path), '-t', str(duration),
                       '-map', '0:a:0', '-vn', '-ar', str(sample_rate), '-c:a', 'pcm_f32le', str(target)]
            flags = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, timeout=120, **flags)
            if result.returncode:
                raise RuntimeError(result.stderr.decode(errors='replace')[-1200:])
            data, _ = sf.read(target, dtype='float32', always_2d=True)
            if not len(data) or not np.isfinite(data).all():
                raise ValueError('Preview contains no common audio or has nonfinite samples; choose an earlier start or shorter duration')
            arrays.append(data)
        count = min(map(len, arrays))
        if count <= 0:
            raise ValueError("Selected A/B preview range contains no common audio; choose an earlier start or smaller offset")
        arrays = [a[:count].copy() for a in arrays]
        if match_loudness:
            from .core import scan_loudness
            levels = []
            for index, samples in enumerate(arrays):
                target = Path(directory) / f'level{index}.wav'
                sf.write(target, samples, sample_rate, subtype='FLOAT')
                levels.append(float(scan_loudness(target)['input_i']))
            if not all(math.isfinite(v) and v > -70 for v in levels):
                raise ValueError('Loudness matching requires measurable nonsilent excerpts')
            difference = levels[0] - levels[1]
            if abs(difference)>24:
                raise ValueError('Loudness difference exceeds 24 LU; check the selected excerpts')
            arrays[1] *= 10**(difference/20)
            details.update(b_gain_db=difference, loudness_matched=True, measured_lufs=levels)
        peak = max(float(np.max(np.abs(a))) for a in arrays)
        ceiling = 10**(-1/20)
        if peak > ceiling:
            gain = ceiling/peak
            arrays = [a*gain for a in arrays]
            details['common_gain_db'] = 20*math.log10(gain)
    return (*arrays, details) if return_info else tuple(arrays)


def choose_output_rate():
    """Use selected default PortAudio output's native clock, without playing audio."""
    import sounddevice as sd
    device = sd.query_devices(kind='output')
    if int(device.get('max_output_channels') or 0) < 1:
        raise ValueError('No available default output device')
    rate = int(round(float(device.get('default_samplerate') or 0)))
    if not 8000 <= rate <= 192000:
        raise ValueError('Default output device sample rate is unsupported')
    return rate


class ABPlayer:
    """A single output stream and sample cursor for both signals."""
    def __init__(self, a, b, *, sample_rate=48000):
        import numpy as np
        if not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 192000:
            raise ValueError('Invalid A/B playback sample rate')
        if a.shape != b.shape or a.ndim != 2 or not len(a):
            raise ValueError('A/B buffers must have identical nonempty shapes')
        self.sample_rate = sample_rate
        self.buffers = (a, b)
        self.position = 0
        self.selected = 0
        self.mix = 0.0
        self.stream = None
        self.underruns = 0
        self._np = np

    def select(self, value):
        if value not in (0, 1):
            raise ValueError('Select A=0 or B=1')
        self.selected = value

    def render(self, frames):
        np = self._np
        start = self.position
        count = min(frames, len(self.buffers[0]) - start)
        output = np.zeros((frames, self.buffers[0].shape[1]), dtype='float32')
        if count:
            goal = float(self.selected)
            fade = min(max(1, round(self.sample_rate * .005)), count)  # 5 ms, no cursor reset.
            weights = np.full(count, goal, dtype='float32')
            weights[:fade] = np.linspace(self.mix, goal, fade)
            a, b = (x[start:start + count] for x in self.buffers)
            output[:count] = a * (1 - weights[:, None]) + b * weights[:, None]
            self.mix = goal
            self.position += count
        return output

    def start(self):
        import sounddevice as sd
        self.close()
        self.position = 0
        self.mix = float(self.selected)
        def callback(outdata, frames, timing, status):
            if status:
                self.underruns += 1
            outdata[:] = self.render(frames)
            if self.position >= len(self.buffers[0]):
                raise sd.CallbackStop
        sd.check_output_settings(samplerate=self.sample_rate,
                                 channels=self.buffers[0].shape[1], dtype='float32')
        self.stream = sd.OutputStream(samplerate=self.sample_rate,
                                      channels=self.buffers[0].shape[1],
                                      dtype='float32', callback=callback)
        try:
            self.stream.start()
        except Exception:
            self.close()
            raise

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None
