import tempfile
from pathlib import Path
import unittest
import hashlib
import numpy as np
import soundfile as sf
from aptk.ab_preview import prepare_pair
from apt.meter import analyze_meter
import os


class AuditionMeterTests(unittest.TestCase):
    def test_offset_and_loudness_match_leave_originals_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a.wav',Path(tmp)/'b.wav'
            sr=48000; t=np.arange(sr*4)/sr
            x=.1*np.sin(2*np.pi*997*t)
            sf.write(a,x,sr,subtype='FLOAT')
            sf.write(b,np.r_[np.zeros(4800),x*.25],sr,subtype='FLOAT')
            hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b)]
            aa,bb,report=prepare_pair(a,b,0,4,processed_offset_ms=100,match_loudness=True,return_info=True)
            self.assertLess(np.sqrt(np.mean((aa-bb)**2)),.002)
            self.assertAlmostEqual(report['b_gain_db'],12.04,delta=.15)
            self.assertEqual(hashes,[hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b)])

    def test_matching_silence_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'silence.wav';sf.write(p,np.zeros(48000),48000)
            with self.assertRaises(ValueError): prepare_pair(p,p,duration=1,match_loudness=True)

    def test_ab_preview_rejects_nonoverlapping_short_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'short.wav'
            sf.write(p, np.ones(4800) * 0.01, 48000, subtype='FLOAT')
            with self.assertRaisesRegex(ValueError, 'no common audio'):
                prepare_pair(p, p, start=3, duration=1)

    def test_missing_model_never_requests_download(self):
        with self.assertRaisesRegex(ValueError, 'local Beat This'):
            analyze_meter('unused.wav')

    @unittest.skipUnless(os.environ.get('APT_BEAT_TEST_MODEL'), 'Optional real model test')
    def test_actual_click_track_produces_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'clicks.wav';sr=22050
            x=np.zeros(sr*12)
            rng=np.random.default_rng(11)
            click=rng.normal(size=441)*np.hanning(441)
            for i in range(24):
                start=int((i*.5)*sr)
                x[start:start+441]+=click*(.6 if i%3==0 else .15)
            sf.write(p,x,sr,subtype='FLOAT')
            r=analyze_meter(p,os.environ['APT_BEAT_TEST_MODEL'])
            self.assertGreater(len(r['beat_seconds']),16)
            self.assertLess(abs(r['tempo_bpm']-120),8)
            self.assertIsNone(r['time_signature'])
            self.assertTrue(r['downbeat_seconds'])
