import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aptk import core

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'requires FFmpeg')
class AudioSmokeTests(unittest.TestCase):
    def setUp(self):
        core.CANCEL.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / '含中文 音檔.wav'
        subprocess.run([shutil.which('ffmpeg'), '-hide_banner','-nostdin','-loglevel','error','-f','lavfi','-i',
                        'sine=frequency=440:sample_rate=48000:duration=3','-c:a','pcm_s24le',str(self.src)], check=True)
        self.opts={'destination':str(self.root / 'out')}

    def test_inspect_audio_no_changes(self):
        original = self.src.read_bytes()
        report, output = core.run_tool("inspect", self.src, self.opts)
        self.assertIn("48000 Hz", report)
        self.assertIn("pcm_s24le", report)
        self.assertTrue(output.exists())
        self.assertEqual(original, self.src.read_bytes())

    def test_probe(self):
        self.assertEqual(core.stream_info(self.src)[0],48000)
        self.assertEqual(core.stream_info(self.src)[1],1)

    def test_convert_rate_depth_and_channels(self):
        result=core.convert(self.src,{**self.opts,'fmt':'wav','depth':'32f','rate':'44100','channels':'2'})
        self.assertTrue(result.exists())
        rate,channels,_=core.stream_info(result)
        self.assertEqual((rate,channels),(44100,2))
        self.assertEqual(core.probe(result)['streams'][0]['codec_name'],'pcm_f32le')
        self.assertTrue(self.src.exists())

    def test_no_overwrite(self):
        a=core.convert(self.src,{**self.opts,'fmt':'wav','depth':'24'})
        b=core.convert(self.src,{**self.opts,'fmt':'wav','depth':'24'})
        self.assertNotEqual(a,b)

    def test_filters(self):
        for name,flt in [('denoise','afftdn=nr=12'),('declick','adeclick'),('declip','adeclip'),('deess','deesser=i=0.15:m=0.55:f=0.55')]:
            with self.subTest(name=name):
                file=core.process_filter(self.src,self.opts,flt,'_'+name)
                self.assertGreater(file.stat().st_size,1000)
                self.assertEqual(core.stream_info(file)[0],48000)

    def test_residual(self):
        file=core.noise_residual(self.src,self.opts)
        self.assertTrue(file.exists())
        self.assertGreater(file.stat().st_size,1000)

    def test_loudness_report_and_normalize(self):
        m=core.scan_loudness(self.src)
        self.assertIn('input_i',m)
        output=core.normalize(self.src,{**self.opts,'target_i':'-16','target_tp':'-1.5','target_lra':'11'})
        self.assertEqual(core.stream_info(output)[0],48000)
        self.assertGreater(output.stat().st_size,1000)
        after=core.scan_loudness(output)
        self.assertLessEqual(float(after['input_tp']), -1.45)

    def test_quality_silence(self):
        self.assertIn('DC offset',core.scan_quality(self.src))
        self.assertIn('未偵測到符合條件',core.silence_scan(self.src,{}))

    def test_mic_eq(self):
        status,out=core.run_tool('mic',self.src,self.opts)
        self.assertTrue(out.exists())
        self.assertIn('u87',out.name.lower())

    def test_batch_copy(self):
        out=core.copy_renamed([self.src],{**self.opts,'prefix':'錄音_','number_start':'1','padding':'4'},lambda x:None)
        self.assertEqual(out[0].name,'錄音_0001.wav')
        self.assertEqual(out[0].read_bytes(),self.src.read_bytes())

    def test_input_never_deleted_even_on_failure(self):
        with self.assertRaises(core.ToolkitError):
            core.convert(self.src,{**self.opts,'fmt':'flac','depth':'32f'})
        self.assertTrue(self.src.exists())

if __name__=='__main__':
    unittest.main()
