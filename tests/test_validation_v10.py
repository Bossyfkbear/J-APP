"""Deterministic audio-based regression tests; not a substitute for real-song datasets."""
import csv
import numpy as np
import soundfile as sf
from apt.benchmark import benchmark_tempo
from apt.rhythm import _onsets
from apt.music import _load


def test_chunk_decimation_is_continuous(tmp_path):
    sr=44100
    x=np.sin(2*np.pi*440*np.arange(sr*4)/sr).astype('float32')
    p=tmp_path/'tone.wav';sf.write(p,x,sr)
    y,rate=_load(p)
    assert len(y)==len(x[::4])
    assert np.max(np.abs(y-x[::4]))<0.0001
    onsets,orate=_onsets(p)
    assert len(onsets)>0 and orate>0


def test_benchmark_multiple_tempos(tmp_path):
    sr=22050
    rows=[]
    for bpm in (80,100,120,140):
        x=np.zeros(sr*12,dtype='float32')
        for t in np.arange(0,12,60/bpm):
            pos=int(round(t*sr))
            length=min(220,len(x)-pos)
            if length>0:x[pos:pos+length]+=np.hanning(length).astype('float32')
        name=f'{bpm}.wav';sf.write(tmp_path/name,x,sr)
        rows.append((name,bpm))
    manifest=tmp_path/'tempo.csv'
    with manifest.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(('path','bpm'));w.writerows(rows)
    result=benchmark_tempo(manifest)
    assert result['n']==4
    assert result['accuracy_4pct_octave']>=.75
