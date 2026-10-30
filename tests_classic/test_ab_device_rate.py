"""A/B preview follows default output clock without hardware playback in CI."""
import hashlib
import sys
from types import SimpleNamespace
import numpy as np
import soundfile as sf
import pytest

from aptk.ab_preview import ABPlayer, prepare_pair, choose_output_rate


def test_default_output_device_44100(monkeypatch):
    fake=SimpleNamespace(query_devices=lambda kind: {'max_output_channels':2,
                                                      'default_samplerate':44100.})
    monkeypatch.setitem(sys.modules,'sounddevice',fake)
    assert choose_output_rate()==44100


def test_prepare_pair_device_rate_and_unchanged_sources(tmp_path):
    sr=48000
    t=np.arange(sr*2,dtype=np.float64)/sr
    source=tmp_path/'original.wav'
    processed=tmp_path/'processed.wav'
    sf.write(source,.1*np.sin(2*np.pi*440*t),sr,subtype='PCM_24')
    sf.write(processed,.08*np.sin(2*np.pi*440*t),sr,subtype='PCM_24')
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,processed)]
    a,b,info=prepare_pair(source,processed,start=0,duration=2,return_info=True,sample_rate=44100)
    assert a.shape==b.shape
    assert a.shape[0]==88200
    assert a.shape[1]==1
    assert info['playback_sample_rate']==44100
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,processed)]==hashes


def test_player_uses_device_rate_and_retains_cursor(monkeypatch):
    class FakeStream:
        def __init__(self,**kwargs):
            self.settings=kwargs
        def start(self):
            pass
        def close(self):
            pass
    state={}
    def check(**kwargs):
        state['check']=kwargs
    def build(**kwargs):
        state['stream']=FakeStream(**kwargs)
        return state['stream']
    fake=SimpleNamespace(check_output_settings=check,OutputStream=build,CallbackStop=type('CallbackStop',(Exception,),{}))
    monkeypatch.setitem(sys.modules,'sounddevice',fake)
    x=np.zeros((44100,2),dtype='float32')
    y=np.full_like(x,.03)
    player=ABPlayer(x,y,sample_rate=44100)
    player.start()
    assert state['check']['samplerate']==44100
    assert state['stream'].settings['samplerate']==44100
    player.render(1024)
    assert player.position==1024
    player.select(1)
    ramp=player.render(256)
    assert player.position==1280
    assert ramp.shape==(256,2)
    assert ramp[-1,0]>.02
    player.close()


@pytest.mark.parametrize('rate',[0,4000,300000,48000.3])
def test_invalid_output_rates_rejected(rate):
    with pytest.raises(ValueError):
        ABPlayer(np.zeros((5,1),dtype='float32'),np.zeros((5,1),dtype='float32'),sample_rate=rate)
