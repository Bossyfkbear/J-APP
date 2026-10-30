from __future__ import annotations
import json, subprocess, shutil, math, os, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from .files import publish_file

LOSSLESS={".wav",".flac",".aiff",".aif",".caf"}
WAV_SUBTYPE_CODECS = {
    'PCM_U8': 'pcm_u8', 'PCM_16': 'pcm_s16le', 'PCM_24': 'pcm_s24le',
    'PCM_32': 'pcm_s32le', 'FLOAT': 'pcm_f32le', 'DOUBLE': 'pcm_f64le',
}

def ffmpeg():
    from aptk.core import find_executable
    exe=find_executable("ffmpeg")
    if not exe: raise RuntimeError("FFmpeg not found. Install it or put ffmpeg on PATH.")
    return exe

def convert(src, dst, sample_rate=None, channels=None, codec=None):
    src,dst=Path(src),Path(dst)
    if not src.is_file(): raise FileNotFoundError(src)
    if src.resolve()==dst.resolve(): raise ValueError("Source and destination must differ")
    if dst.exists(): raise FileExistsError(dst)
    dst.parent.mkdir(parents=True,exist_ok=True)
    cmd=[ffmpeg(),"-hide_banner","-loglevel","error","-nostdin","-n","-i",str(src),"-map","0:a:0","-vn"]
    if sample_rate: cmd += ["-ar",str(sample_rate)]
    if channels: cmd += ["-ac",str(channels)]
    if codec: cmd += ["-c:a",codec]
    elif dst.suffix.lower()==".wav":
        # Keep the source PCM precision when its subtype is known. Compressed
        # sources have no meaningful PCM bit depth, so use 24-bit WAV.
        try:
            subtype = sf.info(str(src)).subtype
        except (RuntimeError, ValueError):
            subtype = None
        cmd += ["-c:a", WAV_SUBTYPE_CODECS.get(subtype, "pcm_s24le")]
    # FFmpeg may leave a partial output on failure. Publish only a completed
    # temporary file and never replace an existing destination.
    with tempfile.TemporaryDirectory(prefix='.apt_convert_',dir=dst.parent) as scratch:
        temporary=Path(scratch)/(dst.name)
        subprocess.run(cmd+[str(temporary)],check=True)
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise IOError('Conversion produced no audio file')
        publish_file(temporary,dst)
    return dst

def analyze(path):
    path=Path(path)
    info=sf.info(path)
    peak=0.; sumsq=0.; n=0; clipped=0
    with sf.SoundFile(path) as f:
        while True:
            x=f.read(65536,dtype="float64",always_2d=True)
            if len(x)==0: break
            peak=max(peak,float(np.max(np.abs(x))))
            sumsq+=float(np.sum(x*x)); n+=x.size
            clipped+=int(np.count_nonzero(np.abs(x)>=0.999969))
    rms=math.sqrt(sumsq/n) if n else 0
    db=lambda v: 20*math.log10(v) if v>0 else None
    return {"file":str(path),"sample_rate":info.samplerate,"channels":info.channels,"frames":info.frames,"duration_seconds":info.duration,"subtype":info.subtype,"sample_peak_dbfs":db(peak),"rms_dbfs":db(rms),"near_full_scale_samples":clipped}

def detect_tempo(path,min_bpm=50,max_bpm=220):
    from .rhythm import detect_tempo as estimate
    return estimate(path,min_bpm,max_bpm)
