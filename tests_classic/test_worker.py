"""Subprocess lifecycle and publication checks; no neural mocks counted as AI QA."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from apt.worker import JobCancelled, run_job


class WorkerLifecycleTests(unittest.TestCase):
    def test_cancel_removes_partial_job_and_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'original.wav'
            source.write_bytes(b'original')
            target = root / 'result.wav'
            child = "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); (p/'output.wav').write_bytes(b'partial'); time.sleep(30)"
            start = time.monotonic()
            with self.assertRaises(JobCancelled):
                run_job('denoise', source, destination=target,
                        command=[sys.executable, '-c', child],
                        cancelled=lambda: time.monotonic() - start > .3)
            self.assertLess(time.monotonic() - start, 4)
            self.assertFalse(target.exists())
            self.assertEqual(source.read_bytes(), b'original')
            self.assertEqual(list(root.glob('.apt_job_*')), [])

    def test_commit_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'result.wav'
            child = "import json,pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/'output.wav').write_bytes(b'complete'); (p/'result.json').write_text(json.dumps({'ok':True,'result':{}}))"
            result = run_job('denoise', destination=target, command=[sys.executable, '-c', child])
            self.assertEqual(result['output'], str(target))
            self.assertEqual(target.read_bytes(), b'complete')
            with self.assertRaises(FileExistsError):
                run_job('denoise', destination=target, command=[sys.executable, '-c', child])

    def test_failed_child_does_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'result.wav'
            child = "import pathlib,sys; (pathlib.Path(sys.argv[1])/'output.wav').write_bytes(b'partial'); raise SystemExit(9)"
            with self.assertRaisesRegex(RuntimeError, 'exited \\(9\\)'):
                run_job('denoise', destination=target, command=[sys.executable, '-c', child])
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
