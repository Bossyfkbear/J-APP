import csv
import numpy as np
import soundfile as sf
from apt.benchmark import benchmark_tempo,benchmark_chords,_tempo_ok

def test_tempo_metrics():
    assert _tempo_ok(120,120)
    assert not _tempo_ok(60,120)
    assert _tempo_ok(60,120,octave=True)

def test_tempo_manifest(tmp_path):
    sr=11025
    x=np.zeros(sr*12,dtype='float32')
    for t in np.arange(0,12,.5):x[int(t*sr):int(t*sr)+100]=np.hanning(100)
    sf.write(tmp_path/'click.wav',x,sr)
    with (tmp_path/'tempo.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['path','bpm']);w.writerow(['click.wav',120])
    r=benchmark_tempo(tmp_path/'tempo.csv',100,140)
    assert r['n']==1 and r['accuracy_4pct']==1

def test_chord_manifest_schema(tmp_path):
    (tmp_path/'bad.csv').write_text('wrong,column\na,b\n')
    import pytest
    with pytest.raises(ValueError,match='Manifest needs'):
        benchmark_chords(tmp_path/'bad.csv')
