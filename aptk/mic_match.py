"""Optional measured microphone tonal match; not U87 physical emulation."""
from __future__ import annotations
import math
import tempfile
from pathlib import Path


def _spectrum(path, *, seconds=15, window_size=4096):
    import numpy as np
    import soundfile as sf
    with sf.SoundFile(path) as reader:
        if reader.samplerate < 8000 or reader.frames < window_size:
            raise ValueError("參考音檔太短或取樣率低於 8kHz")
        rate = reader.samplerate
        samples = reader.read(min(reader.frames, seconds * rate), dtype="float32", always_2d=True)
    if not np.isfinite(samples).all():
        raise ValueError("參考錄音含有 NaN / Infinity")
    mono = samples.mean(axis=1, dtype="float64")
    positions = np.linspace(0,len(mono)-window_size,
                            min(128,max(1,(len(mono)-window_size)//2048+1)),dtype=int)
    frames = np.stack([mono[int(i):int(i)+window_size] for i in positions])
    rms = np.sqrt(np.mean(frames**2,axis=1))
    frames = frames[rms>max(1e-5,float(np.percentile(rms,65))*.15)]
    if len(frames)==0:
        raise ValueError("參考音檔太小聲或全是靜音")
    spectrum = np.mean(abs(np.fft.rfft(frames*np.hanning(window_size),axis=1))**2,axis=0)
    return rate,spectrum,np.fft.rfftfreq(window_size,1/rate)


def measured_filter(source,reference,*,strength=65.,taps=1025,max_change_db=6.):
    """Design symmetrical linear-phase FIR by conservative third-octave matching."""
    import numpy as np
    strength=float(strength)
    if not math.isfinite(strength) or not 0<=strength<=100:
        raise ValueError("音色匹配強度必須是 0–100%")
    sr,a,freqs=_spectrum(source)
    sr_ref,b,_=_spectrum(reference)
    if sr_ref!=sr:
        raise ValueError("來源與目標參考錄音必須有相同取樣率")
    centers=80*2**(np.arange(30)/3)
    centers=centers[centers<min(16000,sr*.415)]
    if len(centers)<5:
        raise ValueError("參考錄音有效頻帶不足")
    floor_a=max(float(a.max())*1e-7,1e-18)
    floor_b=max(float(b.max())*1e-7,1e-18)
    gain=[]
    for center in centers:
        band=abs(np.log2(np.maximum(freqs,1)/center))<.23
        gain.append(10*math.log10(max(float(b[band].mean()),floor_b)/
                                   max(float(a[band].mean()),floor_a)) if band.any() else 0.)
    gain=np.asarray(gain)
    mids=(centers>=180)&(centers<=min(4000,sr*.35))
    gain-=np.median(gain[mids])
    gain=np.clip(gain,-max_change_db,max_change_db)
    for _ in range(2):
        gain=np.convolve(np.pad(gain,(1,1),mode="edge"),[.2,.6,.2],mode="valid")
    gain*=strength/100
    nfft=16384
    fgrid=np.fft.rfftfreq(nfft,1/sr)
    xp=np.r_[1.,40.,centers,sr/2]
    yp=np.r_[0.,0.,gain,0.]
    response=10**(np.interp(np.log2(np.maximum(1,fgrid)),np.log2(xp),yp)/20)
    impulse=np.fft.irfft(response,n=nfft)
    half=taps//2
    kernel=np.r_[impulse[-half:],impulse[:half+1]]*np.hanning(taps)
    if not np.isfinite(kernel).all() or abs(kernel.sum())<1e-6:
        raise RuntimeError("音色匹配濾波器無效")
    kernel/=kernel.sum()
    return kernel,dict(source_sample_rate=sr,strength_percent=strength,
                       bands_hz=[round(float(v),1) for v in centers],
                       band_gain_db=[round(float(v),3) for v in gain],
                       max_band_change_db=max_change_db,
                       kind="measured_tonal_match_not_microphone_emulation")


def process(source,reference,destination,*,strength=65.,cancelled=None,block_size=8192):
    """Preserve samples/channel/rate; stage and publish new FLOAT WAV only."""
    import numpy as np
    import soundfile as sf
    from apt.files import publish_file
    source,reference,destination=map(Path,(source,reference,destination))
    if source.resolve()==reference.resolve():
        raise ValueError("來源與目標參考音檔不能相同")
    if destination.exists() or destination.resolve() in (source.resolve(),reference.resolve()):
        raise FileExistsError("輸出檔已存在或與原音檔衝突")
    def check():
        if cancelled is not None and cancelled():
            raise RuntimeError("已取消")
    check()
    h,report=measured_filter(source,reference,strength=strength)
    half=len(h)//2
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".apt_mic_",dir=destination.parent) as temp:
        staged=Path(temp)/"output.wav"
        peak=0.
        with sf.SoundFile(source) as reader,sf.SoundFile(
            staged,"w",samplerate=reader.samplerate,channels=reader.channels,
            format="WAV",subtype="FLOAT") as writer:
            n=reader.frames
            if reader.samplerate!=report["source_sample_rate"]:
                raise RuntimeError("來源音檔取樣率已改變")
            for start in range(0,n,block_size):
                check()
                count=min(block_size,n-start)
                begin=start-half
                end=start+count+half
                lo,hi=max(0,begin),min(n,end)
                reader.seek(lo)
                x=reader.read(hi-lo,dtype="float32",always_2d=True)
                x=np.pad(x,((max(0,-begin),max(0,end-n)),(0,0)))
                size=1<<(len(x)+len(h)-2).bit_length()
                y=np.fft.irfft(np.fft.rfft(x,n=size,axis=0)*
                              np.fft.rfft(h,n=size)[:,None],n=size,axis=0)
                result=y[2*half:2*half+count]
                if len(result)!=count or not np.isfinite(result).all():
                    raise RuntimeError("輸出音訊資料無效")
                peak=max(peak,float(np.max(np.abs(result))))
                writer.write(result.astype("float32"))
            check()
        output_info=sf.info(staged)
        input_info=sf.info(source)
        if (output_info.frames,output_info.channels,output_info.samplerate,output_info.subtype)!=(input_info.frames,input_info.channels,input_info.samplerate,"FLOAT"):
            raise RuntimeError("音訊長度或格式驗證失敗")
        check()
        publish_file(staged,destination)
    return dict(report,output=str(destination),peak_sample=peak,
                channels=input_info.channels,frames=input_info.frames,subtype="FLOAT")
