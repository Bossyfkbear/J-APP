import numpy as np
import soundfile as sf
from apt.quality import inspect_audio

def test_quality_multichannel(tmp_path):
    p = tmp_path / 'qa.wav'
    samples = np.column_stack((np.zeros(1000), np.ones(1000) * .5))
    sf.write(p, samples, 48000, subtype='FLOAT')
    result = inspect_audio(p, blocksize=77)
    assert result['frames'] == 1000
    assert result['channels'] == 2
    assert result['sample_peak'] == [0.0, 0.5]
    assert result['clipped_samples'] == [0, 0]

def test_quality_empty(tmp_path):
    import pytest
    p = tmp_path / 'empty.wav'
    sf.write(p, np.array([], dtype='float32'), 48000)
    with pytest.raises(ValueError, match='Empty'):
        inspect_audio(p)
