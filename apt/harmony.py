"""Offline harmonic interpretation with correct chord-quality roman numerals."""
from __future__ import annotations
from .music import detect_chords, NOTES

MAJOR_DEGREES=(0,2,4,5,7,9,11)
MINOR_DEGREES=(0,2,3,5,7,8,10)
DEGREE_NAMES=('I','II','III','IV','V','VI','VII')

def romanize(chord: str,key: str)->str:
    if chord=='N':return 'N'
    root=next((n for n in sorted(NOTES,key=len,reverse=True) if chord.startswith(n)),None)
    if root is None:return '?'
    parts=key.split()
    if len(parts)!=2 or parts[0] not in NOTES or parts[1] not in ('major','minor'):
        raise ValueError('Expected key such as C major or A minor')
    suffix=chord[len(root):]
    if suffix not in ('','m','dim','7','maj7','m7'):return '?'
    offset=(NOTES.index(root)-NOTES.index(parts[0]))%12
    degrees=MINOR_DEGREES if parts[1]=='minor' else MAJOR_DEGREES
    if offset not in degrees:return f'chromatic({chord})'
    label=DEGREE_NAMES[degrees.index(offset)]
    if suffix in ('m','m7'):label=label.lower()
    elif suffix=='dim':label=label.lower()+'°'
    if suffix=='maj7':label+='maj7'
    elif suffix in ('7','m7'):label+='7'
    return label

def progression(path,window_seconds=1.0,key=None):
    chords=detect_chords(path,window_seconds)
    chosen=key or chords['estimated_key']
    segments=[dict(s,roman=romanize(s['chord'],chosen)) for s in chords['segments']]
    return {'estimated_key':chosen,'segments':segments,'method':'estimated chords mapped to key',
            'warning':'Estimates only; modulation, inversions and borrowed chords are not reliably identified'}
