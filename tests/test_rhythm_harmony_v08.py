import numpy as np
import soundfile as sf
from apt.rhythm import detect_tempo
from apt.harmony import romanize

def test_click_120(tmp_path):
    sr=11025
    x=np.zeros(sr*12,dtype='float32')
    pulse=np.hanning(100).astype('float32')
    for t in np.arange(0,12,.5):
        start=int(t*sr)
        x[start:start+100]+=pulse
    path=tmp_path/'click.wav'
    sf.write(path,x,sr)
    result=detect_tempo(path,100,140)
    assert result['bpm'] is not None
    assert abs(result['bpm']-120)<3,result

def test_quality_aware_roman():
    assert romanize('Cm','C major')=='i'
    assert romanize('G7','C major')=='V7'
    assert romanize('Bdim','C major')=='vii°'
    assert romanize('Fmaj7','C major')=='IVmaj7'
