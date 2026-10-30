import numpy as np, soundfile as sf, pytest
from apt.core import analyze,convert,detect_tempo
from apt.models import denoise,ModelUnavailable

def test_analysis(tmp_path):
    p=tmp_path/"a.wav"; sf.write(p,np.zeros(48000),48000,subtype="PCM_24")
    a=analyze(p); assert a["sample_rate"]==48000 and a["channels"]==1 and a["sample_peak_dbfs"] is None

def test_conversion(tmp_path):
    p=tmp_path/"a.wav"; q=tmp_path/"b.flac"; sf.write(p,np.zeros(48000),48000)
    convert(p,q); assert sf.info(q).samplerate==48000

def test_model_fails_safely():
    with pytest.raises(ModelUnavailable): denoise("x.wav","y.wav")

def test_tempo_short_rejected(tmp_path):
    p=tmp_path/"a.wav"; sf.write(p,np.zeros(100),48000)
    with pytest.raises(ValueError): detect_tempo(p)
