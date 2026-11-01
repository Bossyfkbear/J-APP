"""High-resolution waveform must retain actual dynamics and source bytes."""
import hashlib

import numpy as np
import soundfile as sf

from aptk import core
from aptk.waveform_view import pixel_envelope, waveform_polygons


def test_waveform_signed_envelope_is_detailed_and_source_unchanged(tmp_path):
    sr = 48000
    duration = 4
    t = np.arange(sr * duration) / sr
    amp = np.where(t < 1, .10, np.where(t < 2, .7, np.where(t < 3, .02, 0)))
    samples = amp * np.sin(2 * np.pi * 440 * t)
    source = tmp_path / "waveform 立體錄音.wav"
    sf.write(source, samples, sr, subtype="PCM_24")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    data = core.waveform_envelope(source, bins=2400)
    assert len(data["samples"]) >= 2000
    assert abs(data["duration_seconds"] - duration) < .02
    assert all(len(point) == 3 for point in data["samples"])
    assert min(x[0] for x in data["samples"][:400]) < -.05
    assert max(x[1] for x in data["samples"][700:1100]) > .60
    assert max(x[2] for x in data["samples"][1300:1700]) < .05
    assert max(abs(v) for point in data["samples"][1900:] for v in point) < .001
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_display_keeps_signed_peaks_and_continuous_polygons():
    envelope = [(0, 0, 0)] * 20 + [(-.98, .73, .45)] + [(0, 0, 0)] * 19
    columns = pixel_envelope(envelope, 10)
    assert len(columns) == 10
    assert min(p[0] for p in columns) < -.95
    assert max(p[1] for p in columns) > .70
    outer, inner = waveform_polygons(envelope, 10, 100)
    assert len(outer) == 40
    assert len(inner) == 40
    assert all(isinstance(value, (float, int)) for value in outer + inner)


def test_invalid_waveform_options_fail():
    import pytest
    with pytest.raises(ValueError):
        core.waveform_envelope("unused.wav", bins=10)
    with pytest.raises(ValueError):
        core.waveform_envelope("unused.wav", max_seconds=200)
