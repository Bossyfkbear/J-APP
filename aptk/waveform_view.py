"""Pure waveform display helpers, no UI or third-party packages."""
from __future__ import annotations

import math


def pixel_envelope(envelope, width: int):
    """Collapse signed min/max/RMS bins into native display columns.

    Preserves true minimum and maximum transients instead of averaging away
    peaks. RMS is used only to show a secondary visual body layer.
    """
    if not envelope:
        return []
    width = max(1, min(int(width), 4096))
    n = len(envelope)
    out = []
    for x in range(min(width, n)):
        a = (x*n) // min(width, n)
        b = max(a+1, ((x+1)*n) // min(width, n))
        segment = envelope[a:b]
        lo = min(float(s[0]) for s in segment)
        hi = max(float(s[1]) for s in segment)
        rms = math.sqrt(sum(float(s[2])**2 for s in segment) / len(segment))
        out.append((max(-1., min(1., lo)), max(-1., min(1., hi)),
                    max(0., min(1., rms))))
    return out


def waveform_polygons(envelope, width: int, height: int, *, margin: int = 6):
    """Return continuous Tk Canvas polygon coords for the peaks and RMS body."""
    columns = pixel_envelope(envelope, width)
    if not columns:
        return [], []
    middle = float(height) / 2.
    scale = max(1., middle - margin)
    n = len(columns)
    upper = []
    lower = []
    inner_top = []
    inner_bottom = []
    for i, (lo, hi, rms) in enumerate(columns):
        x = (i + .5) * max(1., width - 1) / n
        upper.extend((x, middle - hi * scale))
        lower.extend((x, middle - lo * scale))
        inner_top.extend((x, middle - rms * .75 * scale))
        inner_bottom.extend((x, middle + rms * .75 * scale))
    lower_pairs = [lower[i:i+2] for i in range(0, len(lower), 2)]
    inner_pairs = [inner_bottom[i:i+2] for i in range(0, len(inner_bottom), 2)]
    outer = upper + [v for pair in reversed(lower_pairs) for v in pair]
    inner = inner_top + [v for pair in reversed(inner_pairs) for v in pair]
    return outer, inner
