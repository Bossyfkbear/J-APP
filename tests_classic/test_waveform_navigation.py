"""Waveform seeking/zoom keeps source untouched, with bounded decoding."""
import hashlib
import numpy as np
import pytest
import soundfile as sf
from aptk import core
from aptk.waveform_view import clamp_viewport,zoom_viewport,format_time,cursor_seconds


def test_viewport_zoom_and_clamping():
    assert zoom_viewport(0,120,600,2,cursor=30)==(15.,60.)
    assert zoom_viewport(300,30,600,2,cursor=315)==(307.5,15.)
    assert clamp_viewport(595,30,600)==(570.,30.)
    assert clamp_viewport(50,120,.4)==(0.,.4)
    assert format_time(93.4)=="01:33.4"
    assert cursor_seconds(500.,1000,30.,60.)==60.


@pytest.mark.parametrize("value",[-1.,float("nan"),float("inf")])
def test_invalid_seek(value):
    with pytest.raises(ValueError):
        core.waveform_envelope("unused.wav",start_seconds=value)


def test_bounded_seek_with_real_audio(tmp_path):
    sr=48000
    t=np.arange(sr*10)/sr
    audio=np.where(t<5,.12,.75)*np.sin(2*np.pi*240*t)
    src=tmp_path/"long_錄音.wav"
    sf.write(src,audio,sr,subtype="PCM_24")
    sha=hashlib.sha256(src.read_bytes()).hexdigest()
    a=core.waveform_envelope(src,bins=1200,max_seconds=3,start_seconds=0)
    b=core.waveform_envelope(src,bins=1200,max_seconds=3,start_seconds=7)
    assert abs(a["duration_seconds"]-3)<.01
    assert b["start_seconds"]==7
    assert abs(b["source_duration_seconds"]-10)<.01
    assert max(v[2] for v in a["samples"])<.15
    assert max(v[2] for v in b["samples"])>.4
    assert len(a["samples"])==1200
    assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
