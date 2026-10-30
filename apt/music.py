"""Offline, dependency-light tonal and chord estimation. Estimates, not transcription."""
from __future__ import annotations
import numpy as np
import soundfile as sf

NOTES=('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
MAJOR=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
MINOR=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
CHORDS={'':(0,4,7),'m':(0,3,7),'dim':(0,3,6),'7':(0,4,7,10),'maj7':(0,4,7,11),'m7':(0,3,7,10)}

def _load(path, max_seconds=600):
    with sf.SoundFile(path) as f:
        sr=f.samplerate
        # Cap RAM for long tracks by decimating on read; avoid full-file reads.
        stride=max(1,int(np.ceil(sr/11025)))
        blocks=[]
        left=int(sr*max_seconds)
        offset=0
        while left>0:
            b=f.read(min(65536,left),dtype='float32',always_2d=True)
            if not len(b):break
            phase=(-offset)%stride
            blocks.append(b.mean(axis=1)[phase::stride])
            offset+=len(b);left-=len(b)
        x=np.concatenate(blocks) if blocks else np.empty(0,dtype=np.float32)
    return x,sr/stride

def _frames_chroma(path, window_seconds=1.0):
    x,sr=_load(path)
    if len(x)<sr*2:raise ValueError('At least 2 seconds of audio required')
    size=2**int(np.ceil(np.log2(max(4096,int(sr*window_seconds)))))
    hop=max(1,int(sr*window_seconds))
    frequencies=np.fft.rfftfreq(size,1/sr)
    valid=(frequencies>=65.4)&(frequencies<=2100)
    bins=np.where(valid)[0]
    midi=np.rint(69+12*np.log2(frequencies[bins]/440)).astype(int)%12
    chromas=[];times=[]
    for start in range(0,len(x)-int(sr*.5),hop):
        segment=x[start:start+size]
        if len(segment)<size:segment=np.pad(segment,(0,size-len(segment)))
        spectrum=np.abs(np.fft.rfft(segment*np.hanning(size)))
        # Compress loud partials, and reduce the impact of harmonics.
        weights=np.sqrt(spectrum[bins])
        chroma=np.bincount(midi,weights=weights,minlength=12).astype(float)
        total=chroma.sum()
        chromas.append(chroma/total if total>1e-9 else np.zeros(12))
        times.append(round(start/sr,3))
    return np.asarray(chromas),times

def _rank_keys(chroma):
    result=[]
    for root in range(12):
        for mode,profile in (('major',MAJOR),('minor',MINOR)):
            p=np.roll(profile,root)
            score=float(np.dot(chroma-chroma.mean(),p-p.mean())/(np.linalg.norm(chroma-chroma.mean())*np.linalg.norm(p-p.mean())+1e-12))
            result.append({'key':f'{NOTES[root]} {mode}','score':round(score,4)})
    return sorted(result,key=lambda item:item['score'],reverse=True)

def detect_key(path):
    chromas,_=_frames_chroma(path)
    ranking=_rank_keys(chromas.mean(axis=0))
    return {'key':ranking[0]['key'],'candidates':ranking[:3],'method':'chromagram/profile correlation; experimental','confidence':'not calibrated'}

def detect_chords(path, window_seconds=1.0):
    if not .25<=window_seconds<=10:raise ValueError('window_seconds must be between 0.25 and 10')
    chromas,times=_frames_chroma(path,window_seconds)
    templates=[]
    for root in range(12):
        for suffix,intervals in CHORDS.items():
            t=np.zeros(12)
            for interval in intervals:t[(root+interval)%12]=1
            t/=np.linalg.norm(t)
            templates.append((NOTES[root]+suffix,t))
    segments=[]
    for i,chroma in enumerate(chromas):
        if chroma.sum()<1e-7:
            chord='N'
        else:
            norm=chroma/(np.linalg.norm(chroma)+1e-12)
            chord=max(templates,key=lambda item:float(np.dot(norm,item[1])))[0]
        end=round(times[i]+window_seconds,3)
        if segments and segments[-1]['chord']==chord:
            segments[-1]['end_seconds']=end
        else:
            segments.append({'start_seconds':times[i],'end_seconds':end,'chord':chord})
    ranking=_rank_keys(chromas.mean(axis=0))
    return {'estimated_key':ranking[0]['key'],'segments':segments,'method':'chromagram/template matching; experimental','limitations':'harmonics, inversions, dense mixes and modulations may cause errors'}
