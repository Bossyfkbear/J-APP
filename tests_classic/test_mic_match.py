"""Measurable tonal-match regressions; not evidence of a U87 model."""
import hashlib
import numpy as np
import pytest
import soundfile as sf
from aptk.mic_match import process, measured_filter


def pair(tmp_path,stereo=False):
    sr=48000
    rng=np.random.default_rng(123)
    signal=rng.normal(0,.07,(sr*3,2 if stereo else 1))
    target=(signal+np.roll(signal,1,axis=0)+np.roll(signal,2,axis=0))/3
    a,b=tmp_path/'source.wav',tmp_path/'target.wav'
    sf.write(a,signal,sr,subtype='PCM_24')
    sf.write(b,target,sr,subtype='PCM_24')
    return a,b


def test_measured_match_changes_tonal_balance_preserving_stereo(tmp_path):
    a,b=pair(tmp_path,True)
    digest=hashlib.sha256(a.read_bytes()).hexdigest()
    out=tmp_path/'result.wav'
    report=process(a,b,out,strength=100)
    x,_=sf.read(a,always_2d=True)
    y,_=sf.read(out,always_2d=True)
    assert x.shape==y.shape
    assert (sf.info(out).samplerate,sf.info(out).subtype)==(48000,'FLOAT')
    assert hashlib.sha256(a.read_bytes()).hexdigest()==digest
    def ratio(samples):
        s=np.abs(np.fft.rfft(samples[:48000,0]))**2
        f=np.fft.rfftfreq(48000,1/48000)
        return s[(f>5000)&(f<11000)].mean()/s[(f>300)&(f<1000)].mean()
    assert ratio(y)<ratio(x)*.8
    assert np.corrcoef(y[:,0],x[:,0])[0,1]>.7
    assert report['frames']==144000


def test_reference_validation_and_no_overwrite(tmp_path):
    a,b=pair(tmp_path)
    with pytest.raises(FileExistsError):
        process(a,b,a)
    with pytest.raises(ValueError):
        process(a,a,tmp_path/'same.wav')
    different=tmp_path/'different.wav'
    sf.write(different,np.ones(16000)*.01,16000)
    with pytest.raises(ValueError,match='相同取樣率'):
        measured_filter(a,different)


def test_cancelled_leaves_no_file(tmp_path):
    a,b=pair(tmp_path)
    out=tmp_path/'cancel.wav'
    with pytest.raises(RuntimeError,match='已取消'):
        process(a,b,out,cancelled=lambda:True)
    assert not out.exists()


def test_zero_strength_is_identity(tmp_path):
    a,b=pair(tmp_path)
    out=tmp_path/'zero.wav'
    process(a,b,out,strength=0)
    x,_=sf.read(a,dtype='float32')
    y,_=sf.read(out,dtype='float32')
    np.testing.assert_allclose(x,y,atol=1e-6)
