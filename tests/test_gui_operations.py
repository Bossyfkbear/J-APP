from pathlib import Path
import pytest
from apt.gui import run_operation, OPERATIONS

def test_modules_present():
    assert set(('Tempo','Key','Chords','Progression','Convert')).issubset(OPERATIONS)

def test_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_operation('Tempo',str(tmp_path/'missing.wav'))

def test_convert_requires_different_destination(tmp_path):
    f=tmp_path/'input.wav'; f.write_bytes(b'not-a-wave')
    with pytest.raises(ValueError):
        run_operation('Convert',str(f),str(f))

def test_convert_no_overwrite(tmp_path):
    a=tmp_path/'a.wav'; b=tmp_path/'b.wav'; a.write_bytes(b'a'); b.write_bytes(b'b')
    with pytest.raises(FileExistsError):
        run_operation('Convert',str(a),str(b))
