import tempfile
from pathlib import Path
import unittest
import numpy as np
import soundfile as sf
from apt.validation import compare_audio


class NativeComparisonTests(unittest.TestCase):
    def test_tail_and_right_channel_are_not_discarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.wav', Path(tmp)/'b.wav'
            x = np.zeros((8000*121, 2), dtype='float64')
            sf.write(a, x, 8000, subtype='DOUBLE')
            self.assertTrue(compare_audio(a,a)['decoded_samples_identical'])
            x[-1, 1] = 2**-40
            sf.write(b, x, 8000, subtype='DOUBLE')
            result = compare_audio(a,b)
            self.assertEqual(result['differing_samples_per_channel'], [0,1])
            self.assertEqual(result['difference_peak'], [0.,2**-40])

    def test_incompatible_rates_are_not_subtracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.wav', Path(tmp)/'b.wav'
            sf.write(a,np.zeros(100),8000); sf.write(b,np.zeros(100),16000)
            self.assertFalse(compare_audio(a,b)['samples_comparable'])

    def test_unmatched_tail_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.wav', Path(tmp)/'b.wav'
            sf.write(a,np.zeros(100),8000); sf.write(b,np.zeros(110),8000)
            result=compare_audio(a,b)
            self.assertFalse(result['decoded_samples_identical'])
            self.assertEqual(result['unpaired_output_frames'],10)
