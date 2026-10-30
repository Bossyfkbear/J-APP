"""Speaker check is quiet, bounded and opt-in; no actual device access in CI."""
import numpy as np
import pytest
from aptk.device_check import make_test_tone


def test_test_tone_stereo_and_strict_level():
    samples=make_test_tone()
    assert samples.shape == (48000,2)
    assert samples.dtype == np.float32
    assert np.max(abs(samples)) < .04
    assert samples[0,0] == 0
    assert abs(samples[-1,0]) < .00001
    assert np.array_equal(samples[:,0],samples[:,1])


@pytest.mark.parametrize('bad',[
    {'duration':3}, {'duration':0},
    {'level_dbfs':0}, {'level_dbfs':-15},
    {'frequency':4000}, {'sample_rate':4000}
])
def test_invalid_test_levels_never_render(bad):
    with pytest.raises(ValueError):
        make_test_tone(**bad)


def test_playback_uses_actual_default_output_rate(monkeypatch):
    import sys
    from types import SimpleNamespace
    calls={}
    def check_output_settings(**kwargs):
        calls['checked']=kwargs
    def play(samples, samplerate, blocking):
        calls.update(frames=samples.shape[0],rate=samplerate,blocking=blocking)
        assert np.max(abs(samples)) < .04
    fake=SimpleNamespace(
        query_devices=lambda kind: {'max_output_channels':2,'default_samplerate':44100.0},
        check_output_settings=check_output_settings,
        play=play)
    monkeypatch.setitem(sys.modules,'sounddevice',fake)
    from aptk.device_check import play_speaker_test
    report=play_speaker_test()
    assert report['output_sample_rate']==44100
    assert calls['frames']==44100
    assert calls['rate']==44100 and calls['blocking'] is True
    assert calls['checked']['channels']==2
    assert report['confirmed_heard'] is False
