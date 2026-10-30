"""Reproducible offline benchmarks with user-provided, legally obtained audio/labels."""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
from .rhythm import detect_tempo
from .music import detect_chords


def _tempo_ok(estimated, reference, tolerance=.04, octave=False):
    if estimated is None or reference <= 0:
        return False
    multipliers=(.5,1,2) if octave else (1,)
    return any(abs(estimated*m-reference)/reference <= tolerance for m in multipliers)


def benchmark_tempo(manifest, min_bpm=50, max_bpm=220):
    """CSV: path,bpm; relative audio paths resolve from CSV directory."""
    manifest=Path(manifest).resolve()
    results=[]
    with manifest.open(newline='',encoding='utf-8-sig') as handle:
        reader=csv.DictReader(handle)
        if not {'path','bpm'}.issubset(reader.fieldnames or []):
            raise ValueError('Manifest needs path,bpm columns')
        for row in reader:
            p=(manifest.parent / row['path']).resolve()
            ref=float(row['bpm'])
            if not math.isfinite(ref) or ref<=0:raise ValueError('Invalid reference BPM')
            try:
                pred=detect_tempo(p,min_bpm,max_bpm)['bpm']
                error=None
            except (OSError,ValueError,RuntimeError) as exc:
                pred=None;error=str(exc)
            results.append({'path':row['path'],'reference_bpm':ref,'estimated_bpm':pred,
                            'correct_4pct':_tempo_ok(pred,ref),
                            'correct_4pct_octave':_tempo_ok(pred,ref,octave=True),'error':error})
    if not results:raise ValueError('Empty benchmark manifest')
    return {'n':len(results),'accuracy_4pct':sum(r['correct_4pct'] for r in results)/len(results),
            'accuracy_4pct_octave':sum(r['correct_4pct_octave'] for r in results)/len(results),
            'results':results}


def _normalize_chord(chord):
    # Strict vocabulary matching: unknown chords do not get silently counted as correct.
    return chord.strip().replace(':maj7','maj7').replace(':min7','m7').replace(':maj','').replace(':min','m').replace(':dim','dim')


def benchmark_chords(manifest,window_seconds=1.0):
    """CSV: path,start_seconds,end_seconds,chord; one row per ground-truth segment."""
    manifest=Path(manifest).resolve()
    grouped={}
    with manifest.open(newline='',encoding='utf-8-sig') as handle:
        reader=csv.DictReader(handle)
        if not {'path','start_seconds','end_seconds','chord'}.issubset(reader.fieldnames or []):
            raise ValueError('Manifest needs path,start_seconds,end_seconds,chord')
        for row in reader:
            start,end=float(row['start_seconds']),float(row['end_seconds'])
            if not (math.isfinite(start) and math.isfinite(end) and 0<=start<end):
                raise ValueError('Invalid chord interval')
            grouped.setdefault(row['path'],[]).append((start,end,_normalize_chord(row['chord'])))
    if not grouped:raise ValueError('Empty benchmark manifest')
    total=correct=0.
    files=[]
    for name,refs in grouped.items():
        pred=detect_chords((manifest.parent/name).resolve(),window_seconds)['segments']
        match=duration=0.
        for start,end,label in refs:
            duration+=end-start
            for seg in pred:
                overlap=max(0,min(end,seg['end_seconds'])-max(start,seg['start_seconds']))
                if overlap and _normalize_chord(seg['chord'])==label:match+=overlap
        total+=duration;correct+=match
        files.append({'path':name,'duration_seconds':duration,'matched_seconds':match,
                      'weighted_accuracy':match/duration})
    return {'n_files':len(files),'weighted_accuracy':correct/total if total else None,
            'evaluated_seconds':total,'files':files,
            'note':'Exact-label time overlap on supplied annotated intervals; not MIREX WCSR.'}


def benchmark_keys(manifest):
    """Evaluate key recognition against CSV path,key (e.g. C major, A minor)."""
    from .music import detect_key, NOTES
    manifest=Path(manifest).resolve()
    allowed={f'{note} {mode}' for note in NOTES for mode in ('major','minor')}
    results=[]
    with manifest.open(newline='',encoding='utf-8-sig') as handle:
        reader=csv.DictReader(handle)
        if not {'path','key'}.issubset(reader.fieldnames or []):
            raise ValueError('Manifest needs path,key columns')
        for row in reader:
            reference=row['key'].strip()
            if reference not in allowed:
                raise ValueError(f'Unsupported key: {reference}')
            try:
                prediction=detect_key((manifest.parent/row['path']).resolve())
                predicted=prediction['key']
                top3=[item['key'] for item in prediction['candidates']]
                error=None
            except (OSError,ValueError,RuntimeError) as exc:
                predicted=None;top3=[];error=str(exc)
            results.append({'path':row['path'],'reference_key':reference,
                            'estimated_key':predicted,'correct':predicted==reference,
                            'top3_correct':reference in top3,'error':error})
    if not results:raise ValueError('Empty benchmark manifest')
    return {'n':len(results),'accuracy':sum(r['correct'] for r in results)/len(results),
            'top3_accuracy':sum(r['top3_correct'] for r in results)/len(results),
            'results':results}
