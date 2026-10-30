"""CLI auto-depth should not silently downgrade source bit depth."""
import numpy as np
import soundfile as sf
from aptk import core


def test_default_filter_auto_float_preserved(tmp_path):
    core.CANCEL.clear()
    source=tmp_path/'source.wav'
    sf.write(source,np.sin(np.arange(48000)*2*np.pi*500/48000)*.25,48000,subtype='FLOAT')
    report,output=core.run_tool('mic',source,{'destination':str(tmp_path/'out'),'depth':'auto'})
    assert '完成' in report
    assert sf.info(output).subtype=='FLOAT'
    assert sf.info(output).samplerate==48000


def test_default_filter_auto_pcm24_preserved(tmp_path):
    core.CANCEL.clear()
    source=tmp_path/'source.wav'
    sf.write(source,np.sin(np.arange(48000)*2*np.pi*500/48000)*.25,48000,subtype='PCM_24')
    _,output=core.run_tool('declick',source,{'destination':str(tmp_path/'out'),'depth':'auto'})
    assert sf.info(output).subtype=='PCM_24'
