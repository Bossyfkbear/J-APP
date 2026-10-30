"""Regression tests for safe native PCM subprocess handling."""
import sys
import threading
import time
import unittest

import aptk.core as core


class BinarySubprocessTests(unittest.TestCase):
    def setUp(self):
        core.CANCEL.clear()

    def tearDown(self):
        core.CANCEL.clear()

    def test_preserves_raw_pcm_bytes(self):
        command = [sys.executable, "-c",
                   "import sys;sys.stdout.buffer.write(bytes([0,255,128,10]))"]
        self.assertEqual(core.run_binary_command(command, timeout=10),
                         bytes([0, 255, 128, 10]))
        self.assertIsNone(core.ACTIVE_PROCESS)

    def test_failed_decoder_reports_error_and_cleans_process(self):
        command = [sys.executable, "-c",
                   "import sys;sys.stderr.write('decode error');sys.exit(4)"]
        with self.assertRaisesRegex(core.ToolkitError, "decode error"):
            core.run_binary_command(command, timeout=10)
        self.assertIsNone(core.ACTIVE_PROCESS)

    def test_timeout_kills_child(self):
        command = [sys.executable, "-c", "import time;time.sleep(10)"]
        with self.assertRaisesRegex(core.ToolkitError, "逾時"):
            core.run_binary_command(command, timeout=0.2)
        self.assertIsNone(core.ACTIVE_PROCESS)

    def test_cancellation_kills_child(self):
        result = []
        command = [sys.executable, "-c", "import time;time.sleep(10)"]

        def worker():
            try:
                core.run_binary_command(command, timeout=20)
            except core.ToolkitError as exc:
                result.append(str(exc))

        thread = threading.Thread(target=worker)
        thread.start()
        try:
            for _ in range(100):
                with core.PROCESS_LOCK:
                    active = core.ACTIVE_PROCESS is not None
                if active:
                    break
                time.sleep(0.02)
            self.assertTrue(active, "child process did not start")
            core.cancel()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(), "cancel failed to stop child")
            self.assertTrue(any("已取消" in item for item in result))
            self.assertIsNone(core.ACTIVE_PROCESS)
        finally:
            core.cancel()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
