"""Offline technical QA of source/output WAV, FLAC, AIFF and similar files.

No external services, model downloads or hearing-quality claims. Source files
are read only; reports are staged and published without replacing anything.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


def _sha256(path: Path, cancelled=None):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            if cancelled and cancelled():
                raise RuntimeError('已取消')
            chunk=stream.read(1024*1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def examine(source, processed, *, cancelled=None):
    """Read-only full-file engineering checks; no downmix or resampling."""
    from apt.quality import inspect_audio
    source, processed=Path(source),Path(processed)
    if source.resolve()==processed.resolve():
        raise ValueError('來源與輸出必須為不同檔案')
    if not source.is_file() or not processed.is_file():
        raise FileNotFoundError('來源或輸出音檔不存在')
    source_hash_before=_sha256(source,cancelled)
    output_hash_before=_sha256(processed,cancelled)
    a=inspect_audio(source)
    if cancelled and cancelled():
        raise RuntimeError('已取消')
    b=inspect_audio(processed)
    source_unchanged=source_hash_before==_sha256(source,cancelled)
    output_unchanged=output_hash_before==_sha256(processed,cancelled)
    rate_same=a['sample_rate']==b['sample_rate']
    channels_same=a['channels']==b['channels']
    drift_ms=(b['duration_seconds']-a['duration_seconds'])*1000
    finite=not any(a['nonfinite_samples']) and not any(b['nonfinite_samples'])
    # Sample clipping is a warning: peak==1 can be a legitimate intentionally
    # limited signal. True-peak measurements require an independent meter.
    warnings=[]
    if not rate_same:
        warnings.append('取樣率不同：若未要求重採樣，請核對參數')
    if not channels_same:
        warnings.append('聲道數不同：確認是否有意轉單聲道／立體聲')
    if abs(drift_ms)>1.:
        warnings.append('音檔長度差超過 1ms：可能存在處理延遲或裁切')
    if any(b['clipped_samples']):
        warnings.append('輸出存在達到滿刻度的取樣：需要聽感及 true peak 驗收')
    if not finite:
        warnings.append('音檔含有 NaN／Infinity，無法通過基本完整性檢查')
    if not source_unchanged or not output_unchanged:
        warnings.append('檢查過程中檔案內容已改變；請關閉其他編輯程式再重試')
    checks={
        'separate_source_and_output': True,
        'source_unchanged_during_check': source_unchanged,
        'output_unchanged_during_check': output_unchanged,
        'finite_samples': finite,
        'sample_rate_preserved': rate_same,
        'channel_count_preserved': channels_same,
        'duration_difference_ms': round(drift_ms,4),
        'has_output_clipped_samples': any(b['clipped_samples']),
    }
    technical_integrity_pass=finite and source_unchanged and output_unchanged
    return {
        'schema_version': 1,
        'kind': 'local_engineering_checks_not_perceptual_quality',
        'source': {'file_name': source.name,'sha256':source_hash_before,**{key:a[key] for key in (
            'sample_rate','channels','frames','duration_seconds','subtype','sample_peak_dbfs',
            'rms_dbfs','clipped_samples','nonfinite_samples')}},
        'output': {'file_name':processed.name,'sha256':output_hash_before,**{key:b[key] for key in (
            'sample_rate','channels','frames','duration_seconds','subtype','sample_peak_dbfs',
            'rms_dbfs','clipped_samples','nonfinite_samples')}},
        'checks': checks, 'technical_integrity_pass': bool(technical_integrity_pass),
        'warnings':warnings,
        'limitations':[
            '取樣峰值並非 true peak；本報告不測量 LUFS 或聲音透明度',
            '不評估人聲清晰度、AI 模型產生的失真、聲像、相位或音樂性',
            '改變聲道數、取樣率或長度不一定代表錯誤，需要依交付規格判讀',
            '本報告不讀取或上傳私人檔案以外的資料，也不代表實際聽感驗收',
        ],
    }


def publish_report(source,processed,destination='',*,cancelled=None):
    """Emit a safely published UTF-8 JSON report, never overwrite user files."""
    from apt.files import publish_file
    from .core import output_root, unique_output
    source,processed=Path(source),Path(processed)
    report=examine(source,processed,cancelled=cancelled)
    directory=output_root(source,str(destination))
    target=unique_output(directory,source.stem+'_technical_qa','.json')
    if cancelled and cancelled():
        raise RuntimeError('已取消')
    with tempfile.TemporaryDirectory(prefix='.apt_qa_',dir=directory) as root:
        staged=Path(root)/target.name
        with staged.open('x',encoding='utf-8') as f:
            json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        if cancelled and cancelled():
            raise RuntimeError('已取消')
        publish_file(staged,target)
    return target,report
