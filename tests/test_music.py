import numpy as np
import soundfile as sf
import pytest
from apt.music import detect_key,detect_chords

def test_music_analysis_runs(tmp_path):
    sr=11025;t=np.arange(sr*4)/sr
    signal=sum(np.sin(2*np.pi*f*t) for f in (261.6256,329.6276,391.9954))*.15
    p=tmp_path/'chord.wav';sf.write(p,signal,sr)
    key=detect_key(p)
    chords=detect_chords(p)
    assert len(key['candidates'])==3
    assert chords['segments'] and chords['segments'][0]['start_seconds']==0

def test_short_audio_rejected(tmp_path):
    p=tmp_path/'short.wav';sf.write(p,np.zeros(100),11025)
    with pytest.raises(ValueError):detect_key(p)
