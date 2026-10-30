"""Small, dependency-free engine. FFmpeg and FFprobe are external executables.
All generated audio uses explicit lossless defaults unless user requests otherwise.
"""
from __future__ import annotations

import array
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import tempfile
import time
from apt.files import publish_file
from dataclasses import dataclass
from typing import Callable

APP_NAME = "Audio Post Toolkit"
AUDIO_TYPES = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".caf"}
LOSSLESS_FORMATS = {"wav", "flac", "aiff"}
CANCEL = threading.Event()
ACTIVE_PROCESS: subprocess.Popen | None = None
PROCESS_LOCK = threading.Lock()


class ToolkitError(Exception):
    pass


def find_executable(name: str) -> str | None:
    # Same directory as executable/script is allowed for portable distributions.
    stem = name + (".exe" if os.name == "nt" else "")
    dirs = [Path(sys.executable).parent, Path(__file__).resolve().parent.parent]
    for folder in dirs:
        candidate = folder / stem
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def require_ffmpeg() -> tuple[str, str]:
    ffmpeg = find_executable("ffmpeg")
    ffprobe = find_executable("ffprobe")
    if not ffmpeg or not ffprobe:
        raise ToolkitError("找不到 FFmpeg / FFprobe。請安裝 FFmpeg 並加入 PATH，或將執行檔放在程式同一資料夾。")
    return ffmpeg, ffprobe


def cancel() -> None:
    CANCEL.set()
    with PROCESS_LOCK:
        if ACTIVE_PROCESS and ACTIVE_PROCESS.poll() is None:
            ACTIVE_PROCESS.terminate()


def run_command(args: list[str], *, allow_failure: bool = False) -> str:
    """Run without a shell; no implicit conversion or mutation of original input."""
    global ACTIVE_PROCESS
    if CANCEL.is_set():
        raise ToolkitError("已取消")
    popen_opts = {}
    if os.name == "nt":
        popen_opts["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, **popen_opts) as process:
        with PROCESS_LOCK:
            ACTIVE_PROCESS = process
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=0.25)
                    break
                except subprocess.TimeoutExpired:
                    if CANCEL.is_set():
                        process.terminate()
                        try:
                            process.communicate(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.communicate()
                        raise ToolkitError("已取消")
            if CANCEL.is_set():
                raise ToolkitError("已取消")
            msg = stderr.decode("utf-8", errors="replace")
            if process.returncode and not allow_failure:
                raise ToolkitError((msg or stdout.decode("utf-8", errors="replace"))[-1500:])
            return msg + "\n" + stdout.decode("utf-8", errors="replace")
        finally:
            with PROCESS_LOCK:
                if ACTIVE_PROCESS is process:
                    ACTIVE_PROCESS = None


def run_binary_command(args: list[str], *, timeout: float = 120, track_active: bool = True) -> bytes:
    """Cancellable raw PCM capture without a flashing Windows console."""
    global ACTIVE_PROCESS
    if CANCEL.is_set():
        raise ToolkitError("已取消")
    if timeout <= 0 or not math.isfinite(timeout):
        raise ValueError("Binary command timeout must be positive and finite")
    options = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)} if os.name == 'nt' else {}
    with subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **options) as process:
        if track_active:
            with PROCESS_LOCK:
                ACTIVE_PROCESS = process
        deadline = time.monotonic() + timeout
        try:
            while True:
                if CANCEL.is_set():
                    raise ToolkitError("已取消")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ToolkitError("音訊分析逾時，已停止處理")
                try:
                    data, stderr = process.communicate(timeout=min(0.25, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if CANCEL.is_set():
                raise ToolkitError("已取消")
            if process.returncode:
                raise ToolkitError(stderr.decode("utf-8", "replace")[-1500:] or
                                   f"音訊解碼失敗（exit {process.returncode}）")
            return data
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
            if track_active:
                with PROCESS_LOCK:
                    if ACTIVE_PROCESS is process:
                        ACTIVE_PROCESS = None


def probe(path: Path) -> dict:
    _, ffprobe = require_ffmpeg()
    out = run_command([ffprobe, "-v", "quiet", "-show_entries", "format=duration,format_name:stream=index,codec_type,codec_name,sample_rate,channels,sample_fmt,bits_per_raw_sample,bits_per_sample", "-select_streams", "a:0", "-of", "json", str(path)])
    info = json.loads(out)
    if not info.get("streams"):
        raise ToolkitError("找不到可讀取的音訊軌道")
    return info


def stream_info(path: Path) -> tuple[int, int, int | None]:
    info = probe(path)
    s = info["streams"][0]
    sample_rate = int(s["sample_rate"])
    channels = int(s["channels"])
    bits_raw = s.get("bits_per_raw_sample") or s.get("bits_per_sample") or "0"
    bits = int(bits_raw) if str(bits_raw).isdigit() and int(bits_raw) else None
    return sample_rate, channels, bits


def output_root(source: Path, override: str = "") -> Path:
    dest = Path(override).expanduser() if override.strip() else source.parent / "APTK_Output"
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def unique_output(directory: Path, name: str, extension: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (name + extension)
    index = 1
    while target.exists():
        target = directory / f"{name}_{index:02d}{extension}"
        index += 1
    return target


def codec_args(fmt: str, depth: str = "24") -> list[str]:
    if fmt == "wav":
        return ["-c:a", {"8":"pcm_u8", "16":"pcm_s16le", "24":"pcm_s24le", "32":"pcm_s32le", "32f":"pcm_f32le", "64f":"pcm_f64le"}[depth]]
    if fmt == "aiff":
        return ["-c:a", {"8":"pcm_s8", "16":"pcm_s16be", "24":"pcm_s24be", "32":"pcm_s32be", "32f":"pcm_f32be", "64f":"pcm_f64be"}[depth]]
    if fmt == "flac":
        return ["-c:a", "flac", "-compression_level", "8", "-sample_fmt", "s16" if depth == "16" else "s32"]
    if fmt == "mp3":
        return ["-c:a", "libmp3lame", "-b:a", "320k"]
    if fmt == "aac":
        return ["-c:a", "aac", "-b:a", "320k"]
    raise ToolkitError("不支援的輸出格式")


def make_ffmpeg(src: Path, dest: Path, *, filters: str = "", fmt: str = "wav", depth: str = "24", rate: str = "保留", channels: str = "保留") -> list[str]:
    ffmpeg, _ = require_ffmpeg()
    args = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-n", "-i", str(src), "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "0"]
    chain = [filters] if filters else []
    if rate != "保留":
        # High-quality software resampling; never assume libsoxr is bundled.
        chain.append(f"aresample={int(rate)}:resampler=swr:filter_size=64:phase_shift=10:cutoff=0.97")
    if chain:
        args.extend(["-af", ",".join(chain)])
    if rate != "保留":
        args.extend(["-ar", rate])
    if channels != "保留":
        args.extend(["-ac", channels])
    args.extend(codec_args(fmt, depth))
    args.append(str(dest))
    return args


def run_output(src: Path, suffix: str, opts: dict, *, filters: str = "", fmt: str = "wav", depth: str = "24", rate: str = "保留", channels: str = "保留") -> Path:
    out = unique_output(output_root(src, opts.get("destination", "")), src.stem + suffix, "." + ("m4a" if fmt == "aac" else fmt))
    with tempfile.TemporaryDirectory(prefix='.aptk_', dir=out.parent) as temp:
        staged = Path(temp) / out.name
        run_command(make_ffmpeg(src, staged, filters=filters, fmt=fmt, depth=depth, rate=rate, channels=channels))
        if not staged.is_file() or staged.stat().st_size == 0:
            raise ToolkitError("未產生有效輸出")
        if CANCEL.is_set():
            raise ToolkitError("已取消")
        publish_file(staged, out)
    return out


def convert(src: Path, opts: dict) -> Path:
    fmt = opts.get("fmt", "wav")
    depth = opts.get("depth", "auto")
    if depth == 'auto':
        stream = probe(src)['streams'][0]
        codec = stream.get('codec_name', '')
        bits = int(stream.get('bits_per_raw_sample') or stream.get('bits_per_sample') or 0)
        if codec.startswith('pcm_f64'): depth = '64f'
        elif codec.startswith('pcm_f32'): depth = '32f'
        elif bits in (8,16,24,32): depth = str(bits)
        else: depth = '24'
    rate = opts.get("rate", "保留")
    channels = opts.get("channels", "保留")
    if fmt == "flac" and depth in ("32f", "64f", "32"):
        raise ToolkitError("FLAC 不支援浮點取樣，請選 16-bit 或 24-bit。")
    if fmt in {"mp3", "aac"}:
        depth = "24"
    return run_output(src, "_converted", opts, fmt=fmt, depth=depth, rate=rate, channels=channels)


def process_filter(src: Path, opts: dict, filter_expression: str, suffix: str) -> Path:
    depth = opts.get("depth", "24")
    return run_output(src, suffix, opts, filters=filter_expression, depth=depth)


def _extract_loudnorm_json(output: str) -> dict:
    decoder = json.JSONDecoder()
    for m in reversed(list(re.finditer(r"\{\s*\"input_i\"", output))):
        try:
            value, _ = decoder.raw_decode(output[m.start():])
            if "input_tp" in value and "input_lra" in value:
                return value
        except (ValueError, json.JSONDecodeError):
            pass
    raise ToolkitError("無法取得 LUFS 分析結果")


def scan_loudness(src: Path, *, target_i=-16, target_tp=-1.5, target_lra=11) -> dict:
    ffmpeg, _ = require_ffmpeg()
    output = run_command([ffmpeg, "-hide_banner", "-nostdin", "-i", str(src), "-af",
                          f"loudnorm=I={target_i}:LRA={target_lra}:TP={target_tp}:print_format=json", "-f", "null", "-"])
    return _extract_loudnorm_json(output)


def normalize(src: Path, opts: dict) -> Path:
    I = float(opts.get("target_i", "-16"))
    TP = float(opts.get("target_tp", "-1.5"))
    LRA = float(opts.get("target_lra", "11"))
    if not -70 <= I <= -5 or not -9 <= TP <= 0 or not 1 <= LRA <= 50:
        raise ToolkitError("響度設定超出 FFmpeg 支援範圍")
    measurements = scan_loudness(src, target_i=I, target_tp=TP, target_lra=LRA)
    if not all(math.isfinite(float(measurements[key])) for key in
               ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')):
        raise ToolkitError("音檔沒有可測量的有效響度，無法正規化；原檔未修改。")
    rate, _, _ = stream_info(src)
    # Two-pass loudnorm. Explicit output sample rate avoids implicit 192kHz output.
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:"
          f"measured_I={measurements['input_i']}:"
          f"measured_LRA={measurements['input_lra']}:"
          f"measured_TP={measurements['input_tp']}:"
          f"measured_thresh={measurements['input_thresh']}:"
          f"offset={measurements['target_offset']}:linear=true:print_format=summary")
    out = run_output(src, "_loudnorm", opts, filters=af, rate=str(rate))
    return out


def scan_quality(src: Path) -> str:
    ffmpeg, _ = require_ffmpeg()
    audio = probe(src)
    s = audio["streams"][0]
    fmt = audio.get("format", {})
    out = run_command([ffmpeg, "-hide_banner", "-nostdin", "-i", str(src), "-af", "astats=metadata=0:reset=0,volumedetect", "-f", "null", "-"])
    names = ["DC offset", "Peak level dB", "RMS level dB", "Peak count", "Number of NaNs", "Number of Infs", "mean_volume", "max_volume"]
    items = [line.strip() for line in out.splitlines() if any(name in line for name in names)]
    return "\n".join([f"檔案：{src.name}", f"編碼：{s.get('codec_name','?')}", f"取樣率：{s.get('sample_rate','?')} Hz", f"聲道：{s.get('channels','?')}", f"時長：{float(fmt.get('duration',0)):.2f} 秒", "", "品質測量：", *items, "", "注意：峰值與 DC 指標需搭配聽覺確認，不能單靠數值判定音檔合格。"])


def silence_scan(src: Path, opts: dict) -> str:
    ffmpeg, _ = require_ffmpeg()
    db = float(opts.get("silence_db", "-45"))
    secs = float(opts.get("silence_sec", "0.35"))
    if not -100 <= db <= 0 or not .05 <= secs <= 60:
        raise ToolkitError("靜音參數超出範圍")
    out = run_command([ffmpeg, "-hide_banner", "-nostdin", "-i", str(src), "-af", f"silencedetect=noise={db}dB:d={secs}", "-f", "null", "-"])
    lines = [line.strip() for line in out.splitlines() if "silence_start:" in line or "silence_end:" in line]
    return "\n".join([f"檔案：{src.name}", f"閾值：{db} dB，最短：{secs} 秒", "", *(lines or ["未偵測到符合條件的靜音區段"])])


def save_report(src: Path, suffix: str, opts: dict, contents: str) -> Path:
    """Stage a complete UTF-8 report, then publish without replacing any file.

    Directly writing the destination used to leave corrupt/partial reports after
    disk-full errors or cancellation. This uses the same guarded publication
    strategy as processed audio, on the destination's own filesystem.
    """
    if CANCEL.is_set():
        raise ToolkitError("已取消")
    out = unique_output(output_root(src, opts.get("destination", "")), src.stem + suffix, ".txt")
    with tempfile.TemporaryDirectory(prefix='.aptk_report_', dir=out.parent) as folder:
        staged = Path(folder) / out.name
        with staged.open('x', encoding='utf-8-sig') as report:
            report.write(contents)
            report.flush()
            os.fsync(report.fileno())
        if CANCEL.is_set():
            raise ToolkitError("已取消")
        publish_file(staged, out)
    return out


def inspect_audio(src: Path) -> str:
    """Read-only audio format inspection; no decoding or transcoding."""
    data = probe(src)
    stream = data["streams"][0]
    fmt = data.get("format", {})
    rate, channels, bits = stream_info(src)
    duration = float(fmt.get("duration", 0) or 0)
    codec = stream.get("codec_name", "unknown")
    lossless = codec.startswith("pcm_") or codec in {"flac", "alac", "wavpack"}
    return "\n".join([
        f"檔案：{src.name}",
        f"格式：{fmt.get('format_name', 'unknown')}",
        f"編碼：{codec}",
        f"取樣率：{rate} Hz",
        f"聲道：{channels}",
        f"位元深度：{bits if bits is not None else '無法確認／不適用'}",
        f"長度：{duration:.3f} 秒",
        f"檔案大小：{src.stat().st_size:,} bytes",
        f"編碼類型：{'無損或 PCM' if lossless else '有損或未確認'}",
        "備註：此功能只讀取媒體資訊，不會重新編碼或修改原檔。",
    ])


def estimate_bpm_key(src: Path) -> str:
    from apt.rhythm import detect_tempo
    from apt.music import detect_key
    return json.dumps({'tempo': detect_tempo(src), 'key': detect_key(src)}, ensure_ascii=False, indent=2)


def compare_files(first: Path, second: Path) -> str:
    if importlib.util.find_spec("numpy") is None:
        raise ToolkitError("此模組需要選裝 numpy：pip install numpy")
    import numpy as np
    ffmpeg, _ = require_ffmpeg()
    # Decode mono at fixed analysis rate; streamed in bounded 2-minute chunks.
    def decode(path: Path) -> np.ndarray:
        args = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error",
                "-i", str(path), "-t", "120", "-map", "0:a:0",
                "-ac", "1", "-ar", "8000", "-f", "f32le", "-"]
        return np.frombuffer(run_binary_command(args, timeout=90), dtype="<f4")

    a, b = decode(first), decode(second)
    n = min(a.size, b.size)
    if n < 8000:
        raise ToolkitError("音檔太短，無法比較")
    x, y = a[:n].astype("f8"), b[:n].astype("f8")
    corr = float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-20))
    delta = x-y
    rms = float(np.sqrt(np.mean(delta*delta)))
    rms_db = 20*math.log10(max(rms,1e-12))
    return f"A：{first.name}\nB：{second.name}\n比較長度：{n/8000:.1f} 秒（最多 120 秒）\n相關係數：{corr:.5f}\n相減後 RMS：{rms_db:.2f} dBFS\n\n本比較不會自動對齊時間或相位；兩檔若未同步，結果不代表音質差異。"



def estimate_alignment(first: Path, second: Path) -> str:
    """Estimate relative time offset using short mono analysis, without changing audio."""
    if importlib.util.find_spec("numpy") is None:
        raise ToolkitError("音訊對齊分析需要選裝 numpy：pip install numpy")
    import numpy as np
    ffmpeg, _ = require_ffmpeg()
    def read(path):
        cmd = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error",
               "-i", str(path), "-t", "45", "-map", "0:a:0",
               "-ac", "1", "-ar", "2000", "-f", "f32le", "-"]
        return np.frombuffer(run_binary_command(cmd, timeout=60),
                             dtype="<f4").astype(np.float64)
    a, b = read(first), read(second)
    if min(len(a), len(b)) < 4000:
        raise ToolkitError("需要至少兩秒可分析的音訊")
    # Cross-correlate transients/envelopes; robust against moderate timbre differences.
    def envelope(x):
        x = np.abs(x)
        window = np.ones(80, dtype=np.float64) / 80
        return np.convolve(x, window, mode="same")[::20]
    a, b = envelope(a), envelope(b)
    a -= np.mean(a); b -= np.mean(b)
    length = len(a) + len(b) - 1
    fft_size = 1 << (length - 1).bit_length()
    corr = np.fft.irfft(np.fft.rfft(a, fft_size) * np.conj(np.fft.rfft(b, fft_size)), fft_size)
    linear = np.concatenate((corr[-(len(b)-1):], corr[:len(a)]))
    lags = np.arange(-(len(b)-1), len(a))
    max_lag = 2000  # +/- 20 s at 100 Hz
    valid = np.abs(lags) <= max_lag
    idx = np.argmax(linear[valid])
    lag = int(lags[valid][idx])
    confidence = float(linear[valid][idx] / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
    return (f"A：{first.name}\nB：{second.name}\n"
            f"將 B 對齊 A 所需的位移：{lag / 100:.3f} 秒\n"
            f"匹配分數：{confidence:.3f}（非機率）\n\n"
            "分析前 45 秒，搜尋 ±20 秒偏移；僅產生報告，不修改音檔。\n"
            "反覆節奏、靜音、混音差異及時間伸縮可能造成誤判。")

def noise_residual(src: Path, opts: dict) -> Path:
    reduction = float(opts.get("noise_amount", "12"))
    if not 0.01 <= reduction <= 60:
        raise ToolkitError("降噪強度須在 0.01 至 60 dB")
    # Original minus denoised signal => approximate residual/noise.
    ffmpeg, _ = require_ffmpeg()
    out = unique_output(output_root(src, opts.get("destination", "")), src.stem + "_noise_residual", ".wav")
    graph = f"[0:a]asplit=2[a][b];[b]afftdn=nr={reduction}[clean];[a][clean]amix=inputs=2:weights='1 -1':normalize=0[residual]"
    with tempfile.TemporaryDirectory(prefix='.aptk_', dir=out.parent) as temp:
        staged = Path(temp) / out.name
        args = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-n", "-i", str(src), "-filter_complex", graph, "-map", "[residual]", "-c:a", "pcm_s24le", str(staged)]
        run_command(args)
        if CANCEL.is_set():
            raise ToolkitError("已取消")
        publish_file(staged, out)
    return out


def deepfilter_denoise(src: Path, opts: dict) -> Path:
    """Use the locally installed neural model; never fall back to FFT denoise."""
    from apt.worker import run_job
    dest = unique_output(output_root(src, opts.get("destination", "")),
                         src.stem + "_ai_denoised", ".wav")
    run_job('denoise', src, destination=dest, model_dir=opts.get('model_dir'),
            runtime_python=opts.get('runtime_python'), cancelled=CANCEL.is_set)
    return dest


def demucs_split(src: Path, opts: dict) -> Path:
    from apt.worker import run_job
    target = unique_directory(output_root(src, opts.get('destination', '')) / f'{src.stem}_stems')
    run_job('split', src, destination=target, model_dir=opts.get('model_dir'),
            model_name=opts.get('model_name'), split_mode=opts.get('split_mode', 'vocal'),
            runtime_python=opts.get('runtime_python'), cancelled=CANCEL.is_set)
    return target


def _demucs_split_local(src: Path, opts: dict) -> Path:
    """Local-only Demucs inference, including frozen desktop execution."""
    from apt.models import require_local_model
    local = require_local_model(opts.get("model_dir"))
    try:
        import numpy as np
        import soundfile as sf
        from apt.demucs_adapter import infer
    except ImportError as exc:
        raise ToolkitError("尚未安裝相容的 Demucs 執行環境") from exc
    def progress(_):
        if CANCEL.is_set():
            raise ToolkitError("已取消")
    original, stems, model_rate, _ = infer(src, local, opts.get('model_name'), CANCEL.is_set)
    if opts.get('split_mode', 'vocal') == 'vocal':
        if 'vocals' not in stems:
            raise ToolkitError("模型不含人聲軌")
        stems = {'vocals': stems['vocals'], 'instrumental': original - stems['vocals']}
    elif opts.get('split_mode') != 'four':
        raise ToolkitError("未知分離模式")
    root = output_root(src, opts.get('destination', ''))
    out = unique_directory(root / f'{src.stem}_stems')
    out.mkdir(exist_ok=False)
    try:
        for name, tensor in stems.items():
            progress(None)
            samples = tensor.detach().cpu().numpy().T
            if samples.ndim != 2 or len(samples)==0 or not np.isfinite(samples).all():
                raise ToolkitError("模型輸出不完整或含有非有限數值")
            filename = re.sub(r'[^a-zA-Z0-9_-]', '_', name) + '.wav'
            target = out / filename
            if target.exists():
                raise ToolkitError("模型輸出軌名衝突")
            sf.write(target, samples, model_rate, subtype='FLOAT')
            info = sf.info(target)
            if info.frames != len(samples) or info.channels != samples.shape[1]:
                raise ToolkitError("分軌輸出驗證失敗")
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
    return out


def unique_directory(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while (path.parent / f"{path.name}_{counter:02d}").exists():
        counter += 1
    return path.parent / f"{path.name}_{counter:02d}"


def copy_renamed(sources: list[Path], opts: dict, log: Callable[[str],None]) -> list[Path]:
    prefix = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", opts.get("prefix", "Audio_"))
    start = int(opts.get("number_start", "1"))
    padding = int(opts.get("padding", "4"))
    if not 0 <= start <= 99999999 or not 1 <= padding <= 8:
        raise ToolkitError("檔名編號設定無效")
    outputs = []
    for n, src in enumerate(sources, start=start):
        if CANCEL.is_set():
            break
        target = unique_output(output_root(src, opts.get("destination", "")), prefix+str(n).zfill(padding), src.suffix)
        with tempfile.TemporaryDirectory(prefix='.aptk_copy_', dir=target.parent) as temp:
            staged = Path(temp) / target.name
            shutil.copy2(src, staged)
            if CANCEL.is_set():
                break
            publish_file(staged, target)
        outputs.append(target)
        log(f"已複製：{target.name}")
    return outputs


def run_tool(tool: str, src: Path, opts: dict) -> tuple[str, Path | None]:
    """Return human-readable status and optional output artifact."""
    if tool in ('chords', 'progression', 'ai_status', 'pitch', 'meter'):
        if tool == 'chords':
            from apt.music import detect_chords
            result = detect_chords(src)
        elif tool == 'progression':
            from apt.harmony import progression
            result = progression(src)
        else:
            from apt.worker import run_job
            result = run_job(tool if tool in ('pitch','meter') else 'status', src, model_dir=opts.get('model_dir'),
                             runtime_python=opts.get('runtime_python'), cancelled=CANCEL.is_set)
        contents = json.dumps(result, ensure_ascii=False, indent=2)
        return contents, save_report(src, '_' + tool, opts, contents)
    if tool == "convert":
        p = convert(src, opts)
    elif tool == "denoise":
        n = float(opts.get("noise_amount", "12"))
        p = process_filter(src, opts, f"afftdn=nr={max(0.01,min(60,n))}", "_denoised")
    elif tool == "residual":
        p = noise_residual(src, opts)
    elif tool == "ai_denoise":
        p = deepfilter_denoise(src, opts)
    elif tool == 'dereverb':
        from apt.worker import run_job
        p = unique_output(output_root(src, opts.get('destination', '')), src.stem + '_dereverb', '.wav')
        run_job('dereverb', src, destination=p, strength=float(opts.get('strength', '.5')),
                runtime_python=opts.get('runtime_python'), cancelled=CANCEL.is_set)
    elif tool == "declick":
        p = process_filter(src, opts, "adeclick", "_declick")
    elif tool == "declip":
        p = process_filter(src, opts, "adeclip", "_declip")
    elif tool == "deess":
        p = process_filter(src, opts, "deesser=i=0.15:m=0.55:f=0.55", "_deess")
    elif tool == "mic":
        k = max(0, min(100, float(opts.get("mic_strength", "65")))) / 100
        filt = ",".join([
            "highpass=f=55",
            f"equalizer=f=170:t=q:w=0.8:g={.8*k:.3f}",
            f"equalizer=f=480:t=q:w=1.0:g={-.9*k:.3f}",
            f"equalizer=f=4200:t=q:w=0.9:g={1.25*k:.3f}",
            f"equalizer=f=10500:t=q:w=0.7:g={.6*k:.3f}",
        ])
        p = process_filter(src, opts, filt, "_u87_inspired_EQ")
    elif tool == "loudscan":
        measure = scan_loudness(src)
        contents = "\n".join([f"檔案：{src.name}",f"Integrated LUFS：{measure['input_i']}",f"True Peak dBTP：{measure['input_tp']}",f"LRA：{measure['input_lra']}", f"門檻：{measure['input_thresh']}"])
        p = save_report(src, "_loudness", opts, contents)
        return contents, p
    elif tool == "normalize":
        p = normalize(src, opts)
    elif tool == "silence":
        contents = silence_scan(src, opts)
        p = save_report(src, "_silence", opts, contents)
        return contents, p
    elif tool == "inspect":
        contents = inspect_audio(src)
        p = save_report(src, "_metadata", opts, contents)
        return contents, p
    elif tool == "quality":
        contents = scan_quality(src)
        p = save_report(src, "_quality", opts, contents)
        return contents, p
    elif tool == "rhythm":
        contents = estimate_bpm_key(src)
        p = save_report(src, "_rhythm", opts, contents)
        return contents, p
    elif tool == "split":
        p = demucs_split(src, opts)
    else:
        raise ToolkitError("未知工具：" + tool)
    return f"完成：{src.name} → {p.name}", p


def waveform_peaks(src: Path, bins: int = 360) -> list[float]:
    """First 2 minutes only. Constant memory, no scientific Python dependencies."""
    ffmpeg, _ = require_ffmpeg()
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(src), "-t", "120", "-map", "0:a:0", "-ac", "1", "-ar", "2000", "-f", "s16le", "-"]
    payload = run_binary_command(cmd, timeout=30, track_active=False)
    if not payload:
        return []
    samples = array.array("h")
    samples.frombytes(payload[:len(payload)//2*2])
    if sys.byteorder == "big":
        samples.byteswap()
    segment = max(1, math.ceil(len(samples)/bins))
    return [min(1, max((abs(v)/32768 for v in samples[i:i+segment]), default=0)) for i in range(0, len(samples), segment)][:bins]
