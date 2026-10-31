"""Three-line BPM / meter / key results for the desktop GUI.

The light NumPy rhythm estimator does not establish a reliable time signature.
Never infer 4/4 just because tempo exists. No raw JSON is shown to users.
"""
from __future__ import annotations

import math


def format_summary(estimate: dict) -> dict[str, str]:
    tempo = estimate.get("tempo") or {}
    key = estimate.get("key") or {}
    bpm = tempo.get("bpm")
    if isinstance(bpm, (int, float)) and math.isfinite(bpm) and bpm > 0:
        bpm_text = f"{bpm:.1f}".rstrip("0").rstrip(".")
    else:
        bpm_text = "無法判定"

    # A meter estimate is only presented if explicitly supplied by a
    # time-signature estimator. The default tempo algorithm does not have one.
    meter = estimate.get("meter")
    meter_text = "無法判定"
    if isinstance(meter, dict):
        value = meter.get("time_signature")
        if value and value not in ("unknown", "N/A", "?"):
            meter_text = str(value)

    name = key.get("key") if isinstance(key, dict) else None
    if isinstance(name, str) and name:
        if name.endswith(" major"):
            key_text = name[:-6] + " 大調"
        elif name.endswith(" minor"):
            key_text = name[:-6] + " 小調"
        else:
            key_text = name
    else:
        key_text = "無法判定"
    return {"BPM": bpm_text, "拍號": meter_text, "調性": key_text}


def summary_lines(summary: dict) -> str:
    return "\\n".join(f"{label}: {summary[label]}" for label in ("BPM", "拍號", "調性"))
