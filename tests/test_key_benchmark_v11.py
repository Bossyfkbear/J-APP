import csv
import numpy as np
import pytest
import soundfile as sf
from apt.benchmark import benchmark_keys


def test_key_manifest(tmp_path,monkeypatch):
    from apt import music
    monkeypatch.setattr(music,'detect_key',lambda p: {'key':'C major','candidates':[{'key':'C major'},{'key':'A minor'}]})
    with (tmp_path/'keys.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['path','key']);w.writerow(['one.wav','C major']);w.writerow(['two.wav','A minor'])
    result=benchmark_keys(tmp_path/'keys.csv')
    assert result['n']==2
    assert result['accuracy']==.5
    assert result['top3_accuracy']==1


def test_key_invalid_reference(tmp_path):
    (tmp_path/'keys.csv').write_text('path,key\na.wav,H major\n')
    with pytest.raises(ValueError,match='Unsupported key'):
        benchmark_keys(tmp_path/'keys.csv')


def test_key_missing_file_recorded(tmp_path):
    (tmp_path/'keys.csv').write_text('path,key\nmissing.wav,C major\n')
    result=benchmark_keys(tmp_path/'keys.csv')
    assert result['accuracy']==0
    assert result['results'][0]['error']
