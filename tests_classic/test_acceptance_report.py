"""Offline technical acceptance, no audio uploaded or modified."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from aptk.acceptance import examine, publish_report


def test_technical_report_same_format_and_nonoverwriting(tmp_path):
    sr=48000
    t=np.arange(sr,dtype='float64')/sr
    raw=.25*np.sin(2*np.pi*997*t)
    source=tmp_path/'original.wav'
    processed=tmp_path/'output.wav'
    sf.write(source,raw,sr,subtype='PCM_24')
    sf.write(processed,raw*.5,sr,subtype='PCM_24')
    originals=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,processed)]
    folder=tmp_path/'reports'
    path,report=publish_report(source,processed,folder)
    saved=json.loads(path.read_text(encoding='utf-8'))
    assert saved==report
    assert report['technical_integrity_pass'] is True
    assert report['checks']['sample_rate_preserved']
    assert report['checks']['channel_count_preserved']
    assert report['checks']['duration_difference_ms']==0
    assert report['source']['subtype']=='PCM_24'
    assert report['output']['subtype']=='PCM_24'
    assert not report['warnings']
    second,_=publish_report(source,processed,folder)
    assert second!=path
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,processed)]==originals


def test_different_length_and_rate_warning_not_false_failure(tmp_path):
    source=tmp_path/'a.wav'
    processed=tmp_path/'b.wav'
    sf.write(source,np.zeros((48000,2)),48000,subtype='FLOAT')
    sf.write(processed,np.zeros(44100//2),44100,subtype='FLOAT')
    report=examine(source,processed)
    assert report['checks']['sample_rate_preserved'] is False
    assert report['checks']['channel_count_preserved'] is False
    assert report['checks']['duration_difference_ms'] < -400
    assert report['technical_integrity_pass'] is True
    assert len(report['warnings'])>=3


def test_rejects_self_comparison_and_cancellation(tmp_path):
    a=tmp_path/'a.wav'; b=tmp_path/'b.wav'
    sf.write(a,np.zeros(10000),48000)
    sf.write(b,np.zeros(10000),48000)
    with pytest.raises(ValueError,match='不同檔案'):
        examine(a,a)
    with pytest.raises(RuntimeError,match='已取消'):
        publish_report(a,b,tmp_path/'out',cancelled=lambda:True)
    assert not (tmp_path/'out').exists()
