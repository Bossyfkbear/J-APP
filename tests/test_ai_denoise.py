import pytest
from apt.models import denoise, ModelUnavailable

def test_requires_local_model(tmp_path):
    source=tmp_path/'a.wav'; source.write_bytes(b'not a wave')
    with pytest.raises(ModelUnavailable):
        denoise(source,tmp_path/'out.wav',tmp_path/'missing')

def test_never_overwrite_source(tmp_path):
    source=tmp_path/'a.wav'; source.write_bytes(b'data')
    with pytest.raises(ValueError):
        denoise(source,source,tmp_path)
