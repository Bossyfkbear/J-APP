import numpy as np
import soundfile as sf
import pytest
from apt.restoration import spectral_denoise

def test_stationary_denoise(tmp_path):
    sr=16000
    rng=np.random.default_rng(7)
    x=rng.normal(0,.012,sr*2)
    t=np.arange(sr)/sr
    x[sr:]+=0.3*np.sin(2*np.pi*440*t)
    source=tmp_path/'input.wav'; output=tmp_path/'output.wav'
    sf.write(source,x,sr,subtype='PCM_24')
    result=spectral_denoise(source,output,noise_seconds=.5)
    y,rate=sf.read(output)
    assert rate==sr and len(y)==len(x)
    assert sf.info(output).subtype=='PCM_24'
    assert np.std(y[:sr//2])<np.std(x[:sr//2])
    assert np.std(y[sr:])>.04
    with pytest.raises(FileExistsError): spectral_denoise(source,output)
