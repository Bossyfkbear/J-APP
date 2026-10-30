"""Model smoke-test entry is offline and does not fake actual model acceptance."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
import pytest

REPO=Path(__file__).resolve().parents[1]
SCRIPT=REPO/'scripts'/'verify_optional_ai.py'


def load():
    spec=importlib.util.spec_from_file_location('ai_verify',SCRIPT)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_audio_is_deterministic_and_bounded(tmp_path):
    mod=load()
    a=mod.synthetic_source(tmp_path/'a.wav')
    b=mod.synthetic_source(tmp_path/'b.wav')
    xa,sra=sf.read(a,always_2d=True)
    xb,srb=sf.read(b,always_2d=True)
    assert xa.shape==xb.shape==(48000*8,2)
    assert sra==srb==48000
    np.testing.assert_array_equal(xa,xb)
    assert np.max(np.abs(xa))<.2


def test_list_does_not_load_models_or_download(tmp_path):
    result=subprocess.run([sys.executable,str(SCRIPT),'--list'],
                          capture_output=True,text=True,check=True)
    info=json.loads(result.stdout)
    assert len(info['modules'])==5
    assert info['model_download'] is False


def test_missing_model_fails_without_starting_inference(tmp_path):
    mod=load()
    with pytest.raises(FileNotFoundError,match='not installed'):
        mod.run('denoise',root=tmp_path)


def test_diagnostics_on_nonfinite_and_empty_stem(tmp_path):
    mod=load()
    out=tmp_path/'empty.wav'
    sf.write(out,np.zeros(100),48000)
    # A valid quiet WAV is technically valid: neural audio quality requires ears.
    info=mod.verify_result('denoise',{},out)
    assert info['frames']==100
    with pytest.raises(RuntimeError):
        mod.verify_result('split',{},tmp_path/'missing_stems')
