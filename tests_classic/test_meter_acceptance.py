"""Real inference evidence must assert useful numeric BPM, not just JSON keys."""
import importlib.util
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('aptk_verify',HERE/'scripts'/'verify_optional_ai.py')
VERIFY=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


def test_meter_verification_accepts_known_120_bpm_clicks(tmp_path):
    proof=VERIFY.verify_result('meter',{
        'tempo_bpm': 120.0,
        'beat_seconds': [i/2 for i in range(16)],
        'downbeat_seconds': [0.0,2.0,4.0,6.0]
    },tmp_path/'unused')
    assert proof['tempo_bpm']==120
    assert proof['beat_count']==16


@pytest.mark.parametrize('value',[
    {'tempo_bpm':None,'beat_seconds':[],'downbeat_seconds':[]},
    {'tempo_bpm':240,'beat_seconds':list(range(9)),'downbeat_seconds':[]},
    {'tempo_bpm':100,'beat_seconds':[0,1],'downbeat_seconds':[]}
])
def test_meter_verification_rejects_missing_or_inaccurate_timeline(tmp_path,value):
    with pytest.raises(RuntimeError):
        VERIFY.verify_result('meter',value,tmp_path/'unused')
