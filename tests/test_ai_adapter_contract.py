"""Offline contract checks: do not require installing a neural model."""
import numpy as np
import pytest
from apt.models import validate_enhancement


def test_enhancement_valid():
    assert validate_enhancement(np.zeros(480, dtype=np.float32), 480) == 480

@pytest.mark.parametrize('data,expected', [([float('nan')], 1), ([float('inf')], 1), ([], 1), ([0.0], 2)])
def test_enhancement_rejects_invalid(data, expected):
    with pytest.raises(ValueError):
        validate_enhancement(np.asarray(data), expected)
