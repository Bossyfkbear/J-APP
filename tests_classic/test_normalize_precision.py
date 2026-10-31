"""Full-file normalization retains PCM precision and source file bytes."""
import hashlib
import numpy as np
import soundfile as sf
from aptk import core


def test_float32_loudnorm_retains_precision(tmp_path):
    core.CANCEL.clear()
    sr=48000
    data=.06*np.sin(np.arange(sr*3)*2*np.pi*997/sr)
    src=tmp_path/'source_float.wav'
    sf.write(src,data,sr,subtype='FLOAT')
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    dest=core.normalize(src,{'destination':str(tmp_path/'out'),'target_i':'-20',
                             'target_tp':'-2','target_lra':'11'})
    info=sf.info(dest)
    assert (info.samplerate,info.subtype,info.channels,info.frames)==(sr,'FLOAT',1,len(data))
    assert hashlib.sha256(src.read_bytes()).hexdigest()==digest


def test_pcm24_loudnorm_preserves_stereo(tmp_path):
    core.CANCEL.clear()
    sr=44100
    t=np.arange(sr*3)/sr
    data=np.column_stack((.09*np.sin(2*np.pi*410*t),.06*np.sin(2*np.pi*530*t)))
    src=tmp_path/'source_24.wav'
    sf.write(src,data,sr,subtype='PCM_24')
    dest=core.normalize(src,{'destination':str(tmp_path/'out'),'target_i':'-18',
                             'target_tp':'-2','target_lra':'11'})
    info=sf.info(dest)
    assert (info.samplerate,info.subtype,info.channels,info.frames)==(sr,'PCM_24',2,len(data))
