"""Bounded-memory offline beat/tempo estimation, with ambiguity exposed."""
from __future__ import annotations
import numpy as np
import soundfile as sf


def _onsets(path, analysis_rate=11025, hop=256, max_seconds=900):
    with sf.SoundFile(path) as f:
        sr=f.samplerate
        stride=max(1,round(sr/analysis_rate))
        actual=sr/stride
        blocks=[]
        remaining=int(sr*max_seconds)
        offset=0
        while remaining:
            chunk=f.read(min(65536,remaining),dtype='float32',always_2d=True)
            if not len(chunk):break
            phase=(-offset)%stride
            blocks.append(chunk.mean(axis=1)[phase::stride])
            offset+=len(chunk)
            remaining-=len(chunk)
    if not blocks:raise ValueError('Empty audio')
    x=np.concatenate(blocks)
    if len(x)<actual*3:raise ValueError('At least 3 seconds of audio required')
    nfft=1024
    if len(x)<nfft:raise ValueError('Audio too short')
    # Spectral flux: detects transients better than raw RMS, with modest memory use.
    prev=np.zeros(nfft//2+1)
    novelty=[]
    window=np.hanning(nfft)
    for start in range(0,len(x)-nfft+1,hop):
        mag=np.abs(np.fft.rfft(x[start:start+nfft]*window))
        novelty.append(np.maximum(0,mag-prev).sum())
        prev=mag
    onset=np.asarray(novelty,dtype=np.float64)
    onset=np.maximum(0,onset-np.median(onset))
    if onset.max()>0:onset/=onset.max()
    return onset,actual/hop


def _acf(x):
    n=len(x)
    size=1 << (2*n-1).bit_length()
    spectrum=np.fft.rfft(x-x.mean(),n=size)
    ac=np.fft.irfft(spectrum*spectrum.conj(),n=size)[:n]
    return ac/np.maximum(1,np.arange(n,0,-1))


def detect_tempo(path,min_bpm=50,max_bpm=220):
    if not (20<=min_bpm<max_bpm<=350):raise ValueError('BPM range must be between 20 and 350')
    onset,rate=_onsets(path)
    if onset.max()<1e-8:return {'bpm':None,'confidence':0.0,'alternatives':[],'reason':'no transients'}
    ac=_acf(onset)
    lo=max(1,int(np.floor(rate*60/max_bpm)))
    hi=min(len(ac)-1,int(np.ceil(rate*60/min_bpm)))
    if hi<=lo:return {'bpm':None,'confidence':0.0,'alternatives':[],'reason':'insufficient duration'}
    peaks=[]
    for lag in range(lo,hi+1):
        if ac[lag]>=ac[max(lo,lag-1)] and ac[lag]>=ac[min(hi,lag+1)]:
            # Reward coherent beat subdivisions without making half/double tempo invisible.
            strength=ac[lag]
            if lag*2<len(ac):strength+=0.25*max(0,ac[lag*2])
            if lag//2>=lo:strength+=0.15*max(0,ac[lag//2])
            peaks.append((strength,lag))
    peaks.sort(reverse=True)
    if not peaks or peaks[0][0]<=0:return {'bpm':None,'confidence':0.0,'alternatives':[],'reason':'no stable periodicity'}
    selected=[]
    for strength,lag in peaks:
        bpm=60*rate/lag
        if all(abs(bpm-item['bpm'])>2 for item in selected):
            selected.append({'bpm':round(bpm,2),'strength':round(float(strength),5)})
        if len(selected)==5:break
    best=selected[0]
    # ACF ratio is an indicator, not a calibrated accuracy probability.
    confidence=float(np.clip(ac[peaks[0][1]]/(ac[0]+1e-12),0,1))
    return {'bpm':best['bpm'],'confidence':round(confidence,3),'alternatives':selected[1:],
            'method':'spectral-flux autocorrelation','warning':'half/double tempo and rubato can be ambiguous'}
