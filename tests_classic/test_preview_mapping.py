"""Preview must follow selected audio in multi-file batches."""
from pathlib import Path
import tempfile
import unittest

from aptk.ui import selected_preview_path


class PreviewSelectionTests(unittest.TestCase):
    def test_selected_source_is_matched_to_its_own_output(self):
        with tempfile.TemporaryDirectory() as folder:
            a = Path(folder) / 'a.wav'
            b = Path(folder) / 'b.wav'
            ao = Path(folder) / 'a_processed.wav'
            bo = Path(folder) / 'b_processed.wav'
            pair = {str(a.resolve()): ao, str(b.resolve()): bo}
            self.assertEqual(selected_preview_path([a, b], (0,), pair), a)
            self.assertEqual(selected_preview_path([a, b], (1,), pair, processed=True), bo)
            self.assertEqual(selected_preview_path([a, b], (0,), pair, processed=True), ao)

    def test_unprocessed_source_never_plays_unrelated_batch_output(self):
        with tempfile.TemporaryDirectory() as folder:
            a = Path(folder) / 'a.wav'
            b = Path(folder) / 'b.wav'
            pair = {str(b.resolve()): Path(folder) / 'b_processed.wav'}
            self.assertIsNone(selected_preview_path([a, b], (0,), pair, processed=True))

    def test_empty_or_missing_selection(self):
        source = Path('a.wav')
        self.assertIsNone(selected_preview_path([], (), {}, processed=True))
        self.assertEqual(selected_preview_path([source], (), {}, processed=False), source)
        self.assertEqual(selected_preview_path([source], (99,), {}, processed=False), source)


if __name__ == '__main__':
    unittest.main()
