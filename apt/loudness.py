"""Offline EBU R128 loudness and true-peak measurement through FFmpeg."""
import re
import subprocess
from pathlib import Path
from .core import ffmpeg


def _number(section, label, unit):
    match = re.search(rf'\b{re.escape(label)}:\s*([-+]?\d+(?:\.\d+)?|-inf|inf)\s*{unit}', section)
    if not match:
        raise ValueError(f'FFmpeg loudness summary missing {label}')
    value = float(match.group(1))
    return value if value not in (float('inf'), float('-inf')) else None


def measure_loudness(path):
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    command = [ffmpeg(), '-hide_banner', '-nostdin', '-nostats', '-loglevel', 'info',
               '-i', str(source), '-map', '0:a:0', '-vn', '-sn', '-dn',
               '-filter:a', 'ebur128=peak=true', '-f', 'null', '-']
    run = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                         text=True, errors='replace')
    if run.returncode:
        raise RuntimeError(f'FFmpeg loudness analysis failed: {run.stderr[-2000:]}')
    if 'Summary:' not in run.stderr:
        raise RuntimeError('FFmpeg did not provide an EBU R128 summary')
    summary = run.stderr.rsplit('Summary:', 1)[-1]
    integrated, rest = summary.split('Loudness range:', 1)
    loudness_range, true_peak = rest.split('True peak:', 1)
    return {'path': str(source), 'integrated_lufs': _number(integrated, 'I', 'LUFS'),
            'loudness_range_lu': _number(loudness_range, 'LRA', 'LU'),
            'true_peak_dbtp': _number(true_peak, 'Peak', 'dBFS'),
            'method': 'FFmpeg ebur128 true-peak analysis'}
