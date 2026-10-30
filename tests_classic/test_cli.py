import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class CLITests(unittest.TestCase):
    def test_help(self):
        p=subprocess.run([sys.executable,str(ROOT/'cli.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0)
        self.assertIn('denoise',p.stdout)
    def test_missing_file(self):
        p=subprocess.run([sys.executable,str(ROOT/'cli.py'),'inspect','missing.wav'],capture_output=True,text=True)
        self.assertEqual(p.returncode,1)
    def test_batch_conversion(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            src=folder/'test.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.2:sample_rate=48000','-c:a','pcm_s24le',str(src)],check=True)
            p=subprocess.run([sys.executable,str(ROOT/'cli.py'),'convert',str(src),'--destination',str(folder/'out')],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertTrue(list((folder/'out').glob('*.wav')))
    def test_conversion_with_ascii_redirected_output(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            src = ROOT / 'validation' / 'audio' / 'enhanced.wav'
            env = dict(os.environ, PYTHONIOENCODING='ascii:strict')
            p = subprocess.run(
                [sys.executable, str(ROOT/'cli.py'), 'convert', str(src),
                 '--destination', str(folder/'out')],
                capture_output=True, env=env)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(b'OUTPUT:', p.stdout)
            self.assertTrue(list((folder/'out').glob('*.wav')))
