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
    def test_mic_reference_tonal_match_without_ffmpeg(self):
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as folder_name:
            folder = Path(folder_name)
            rate = 48000
            samples = np.random.default_rng(50).normal(0, .04, rate * 2)
            original = folder / '原始錄音.wav'
            target = folder / 'reference.wav'
            sf.write(original, samples, rate, subtype='PCM_24')
            sf.write(target, .6*samples+.4*np.roll(samples, 1), rate, subtype='PCM_24')
            command = [sys.executable, str(ROOT/'cli.py'), 'mic', str(original),
                       '--reference-path', str(target), '--mic-strength', '60',
                       '--destination', str(folder/'outputs')]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs = list((folder/'outputs').glob('*_mic_tonal_match.wav'))
            self.assertEqual(len(outputs), 1)
            self.assertEqual(sf.info(outputs[0]).frames, len(samples))
            self.assertEqual(sf.info(outputs[0]).subtype, 'FLOAT')

    def test_cli_technical_qa_valid_and_no_overwrite(self):
        import json
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            source=folder/'原音.wav'
            processed=folder/'處理後.wav'
            x=.03*np.sin(np.arange(48000)*2*np.pi*400/48000)
            sf.write(source,x,48000,subtype='PCM_24')
            sf.write(processed,x*.7,48000,subtype='PCM_24')
            command=[sys.executable,str(ROOT/'cli.py'),'qa',str(source),str(processed),
                     '--destination',str(folder/'report')]
            a=subprocess.run(command,capture_output=True,text=True)
            b=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(a.returncode,0,a.stderr)
            self.assertEqual(b.returncode,0,b.stderr)
            self.assertIn('TECHNICAL_INTEGRITY: PASS',a.stdout)
            output=list((folder/'report').glob('*.json'))
            self.assertEqual(len(output),2)
            self.assertTrue(all(json.loads(p.read_text(encoding='utf-8'))['technical_integrity_pass'] for p in output))

    def test_cli_qa_requires_two_files(self):
        command=[sys.executable,str(ROOT/'cli.py'),'qa',str(ROOT/'validation'/'audio'/'enhanced.wav')]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('requires exactly two files',result.stderr)
