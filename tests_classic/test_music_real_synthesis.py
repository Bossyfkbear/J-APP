"""Real offline tempo/chord/progression tests on known synthesized music."""
import numpy as np
import soundfile as sf
from apt.rhythm import detect_tempo
from apt.music import detect_chords
from apt.harmony import progression, romanize

NOTE_NUMBERS={
    'C3':48,'F3':53,'G3':55,'A3':57,'B3':59,
    'C4':60,'D4':62,'E4':64,'F4':65,'G4':67,'A4':69,'B4':71,
}


def create_chord_audio(path, seconds=3, sr=22050):
    chords=[('C',['C4','E4','G4']),('Am',['A3','C4','E4']),
            ('F',['F3','A3','C4']),('G',['G3','B3','D4'])]
    chunks=[]
    for name,notes in chords:
        t=np.arange(sr*seconds)/sr
        # Harmonics typical of real instruments, with smooth song boundaries.
        audio=np.zeros(len(t),dtype=np.float64)
        for note in notes:
            hz=440*2**((NOTE_NUMBERS[note]-69)/12)
            audio+=(np.sin(2*np.pi*hz*t)+.12*np.sin(4*np.pi*hz*t))
        fade=np.minimum(1,np.minimum(t,.5)*(1/.2))
        fade*=np.minimum(1,np.maximum(0,(seconds-t)/.2))
        chunks.append(audio*.05*fade)
    sf.write(path,np.concatenate(chunks),sr,subtype='PCM_24')
    return chords


def chord_at(result,time):
    return next((s['chord'] for s in result['segments']
                 if s['start_seconds'] <= time < s['end_seconds']),None)


def roman_at(result,time):
    return next((s['roman'] for s in result['segments']
                 if s['start_seconds'] <= time < s['end_seconds']),None)


def test_known_four_chord_progression(tmp_path):
    path=tmp_path/'C_Am_F_G.wav'
    create_chord_audio(path)
    detected=detect_chords(path)
    timeline=progression(path,key='C major')
    expected=['C','Am','F','G']
    moments=[1.5,4.5,7.5,10.5]
    actual=[chord_at(detected,t) for t in moments]
    romans=[roman_at(timeline,t) for t in moments]
    assert actual==expected,{'expected':expected,'detected':actual,'timeline':detected['segments']}
    assert romans==['I','vi','IV','V'],romans
    assert len(timeline['segments'])>=4


def test_music_input_is_never_modified(tmp_path):
    path=tmp_path/'demo.wav'
    create_chord_audio(path)
    original=path.read_bytes()
    detect_chords(path)
    progression(path,key='C major')
    assert path.read_bytes()==original


def test_tempo_candidates_include_known_120_bpm(tmp_path):
    path=tmp_path/'120bpm.wav'
    sr=22050
    duration=12
    audio=np.zeros(sr*duration,dtype='float64')
    n=int(.04*sr)
    click=np.sin(2*np.pi*1750*np.arange(n)/sr)*np.hanning(n)*.2
    for i in range(0,sr*duration,sr//2):
        audio[i:i+n]+=click[:min(n,len(audio)-i)]
    sf.write(path,audio,sr,subtype='PCM_24')
    result=detect_tempo(path)
    possibilities=[result['bpm']]+[p['bpm'] for p in result['alternatives']]
    assert any(bpm is not None and abs(bpm-120)<5 for bpm in possibilities),result


def test_roman_numerals_for_major_progression():
    assert [romanize(chord,'C major') for chord in ['C','Am','F','G7']]==['I','vi','IV','V7']
