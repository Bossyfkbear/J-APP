"""Friendly GUI results for every tool. Never display raw JSON or logs by default."""
from __future__ import annotations

import json
import math
from pathlib import Path


def _parsed(message):
    if isinstance(message, dict):
        return message
    try:
        value = json.loads(message)
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _number(value, suffix="", ndigits=2):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return f"{value:.{ndigits}f}".rstrip("0").rstrip(".") + suffix
    return "無法判定"


def _time(seconds):
    if not isinstance(seconds, (int, float)) or not math.isfinite(seconds):
        return "--:--"
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _lines(text, limit=12):
    return "\n".join(str(text).splitlines()[:limit])


def format_result(tool, message, output=None):
    """Convert an actual successful processing result into brief, readable lines."""
    obj = _parsed(message)
    if tool == "rhythm":
        from .rhythm_result import format_summary, summary_lines
        return summary_lines(format_summary(obj))
    if tool in ("chords", "progression"):
        segments = obj.get("segments") or []
        kind = "和弦進行" if tool == "progression" else "和弦"
        key = obj.get("estimated_key")
        lines = [f"推估調性：{key}" if key else "推估調性：無法判定"]
        for part in segments[:18]:
            chord = part.get("chord") or "未辨識"
            roman = f"（{part['roman']}）" if tool == "progression" and part.get("roman") else ""
            lines.append(f"{_time(part.get('start_seconds'))}  {chord}{roman}")
        if len(segments) > 18:
            lines.append(f"其餘 {len(segments)-18} 個段落已儲存至分析報告")
        return "\n".join(lines) if segments else f"{kind}：無法判定"
    if tool == "meter":
        beats = obj.get("beat_seconds") or []
        bars = obj.get("downbeat_seconds") or []
        return "\n".join((f"BPM: {_number(obj.get('tempo_bpm'))}",
                          f"拍號: {obj.get('time_signature') or '無法判定'}",
                          f"拍點: {len(beats)} 個",
                          f"小節起點: {len(bars)} 個"))
    if tool == "pitch":
        return "\n".join(("音高：" + _number(obj.get("median_voiced_hz"), " Hz", 1),
                          "有效音高影格：" + str(sum(1 for f in obj.get("frames", [])
                                                    if isinstance(f, dict) and f.get("hz") is not None))))
    if tool == "ai_status":
        return "AI 模型：" + ("可使用" if obj.get("ready") else "尚未就緒")
    if tool == "setup":
        executable = obj.get("executables") or {}
        ffmpeg = executable.get("ffmpeg") or {}
        ffprobe = executable.get("ffprobe") or {}
        optional = (obj.get("optional_modules") or {}).get("modules") or {}
        lines = ["核心音訊環境：" + ("正常" if obj.get("core_ready") else "需要安裝／檢查")]
        lines.append("FFmpeg：" + ("可使用" if ffmpeg.get("available") else "尚未安裝"))
        lines.append("FFprobe：" + ("可使用" if ffprobe.get("available") else "尚未安裝"))
        for name, status in optional.items():
            lines.append(f"{name}：" + ("可執行自測" if status.get("ready_for_manual_test")
                                      else "尚未完整安裝"))
        return "\n".join(lines)
    if tool == "verify":
        identical = obj.get("decoded_samples_identical")
        rate = obj.get("source_rate"), obj.get("output_rate")
        channels = obj.get("source_channels"), obj.get("output_channels")
        return "\n".join((
            "取樣內容：" + ("完全相同" if identical else "存在差異"),
            f"取樣率：{rate[0]} / {rate[1]} Hz",
            f"聲道：{channels[0]} / {channels[1]}",
            "長度差：" + _number(obj.get("duration_difference_seconds"), " 秒", 4),
        ))
    if tool == "loudscan":
        text = str(message)
        return "\n".join(line for line in text.splitlines()
                         if any(word in line for word in ("Integrated LUFS", "True Peak", "LRA"))) or "無法讀取響度"
    if tool in ("silence", "inspect", "quality", "compare", "align"):
        return _lines(message, 12)
    if output is not None:
        path = Path(output)
        return ("處理完成\n" + ("輸出資料夾：" if path.is_dir() else "輸出檔案：") + str(path))
    # No output is normal for some read-only operations.
    return _lines(message, 8) or "處理完成"


def format_batch(results, errors=(), *, max_items=12):
    """Bound the size of dialogs for bulk processing, preserving truthful counts."""
    all_results = list(results)
    all_errors = list(errors)
    if not all_results and not all_errors:
        return "未產生結果"
    items = []
    for name, summary in all_results[:max_items]:
        items.append((f"{name}\n" if len(all_results) > 1 else "") + str(summary))
    if len(all_results) > max_items:
        items.append(f"另有 {len(all_results) - max_items} 個檔案完成")
    for name, error in all_errors[:5]:
        items.append(f"{name}：處理失敗\n{str(error)[:200]}")
    if len(all_errors) > 5:
        items.append(f"另有 {len(all_errors)-5} 個檔案失敗")
    text = "\n\n".join(items)
    return text[:4500] + ("\n…其餘結果請查看輸出資料夾" if len(text) > 4500 else "")
