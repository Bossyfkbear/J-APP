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
