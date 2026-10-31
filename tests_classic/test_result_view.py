"""Every tool result in the GUI is readable, not machine-source dumps."""
import json
from pathlib import Path
from aptk.result_view import format_result, format_batch


def test_chords_and_progression_no_raw_json():
    report=json.dumps({"estimated_key":"C major","segments":[
        {"start_seconds":0,"chord":"C","roman":"I"},
        {"start_seconds":2.3,"chord":"Am","roman":"vi"},
        {"start_seconds":4.5,"chord":"F","roman":"IV"}]})
    result=format_result('progression',report,Path("session_progression.txt"))
    assert "00:02  Am（vi）" in result
    assert "00:04  F（IV）" in result
    assert "segments" not in result and "{" not in result


def test_meter_and_pitch_human_results():
    meter=format_result('meter',json.dumps({
        'tempo_bpm':120,'beat_seconds':[0,.5,1],
        'downbeat_seconds':[0,2],'time_signature':None}))
    assert meter.splitlines()==["BPM: 120","拍號: 無法判定","拍點: 3 個","小節起點: 2 個"]
    pitch=format_result('pitch',json.dumps({"median_voiced_hz":220.63,"frames":[
        {'hz':220},{'hz':None},{'hz':221}]}))
    assert "220.6 Hz" in pitch and "2" in pitch


def test_file_processing_shows_output_only(tmp_path):
    out=tmp_path/'processed.wav'
    text=format_result('convert','完成：foo.wav → processed.wav',out)
    assert str(out) in text
    assert "{" not in text


def test_verification_and_environment_are_human_readable():
    status=format_result('setup',json.dumps({'core_ready':True,
        'executables':{'ffmpeg':{'available':True},'ffprobe':{'available':True}},
        'optional_modules':{'modules':{'pitch':{'ready_for_manual_test':True}}}}))
    assert "正常" in status and "pitch：可執行自測" in status
    verify=format_result('verify',json.dumps({'decoded_samples_identical':True,
        'source_rate':48000,'output_rate':48000,'source_channels':2,
        'output_channels':2,'duration_difference_seconds':0}))
    assert '完全相同' in verify and '48000' in verify


def test_batch_does_not_flood_dialog():
    text=format_batch([("file"+str(i),"處理完成") for i in range(40)])
    assert '另有 28 個檔案完成' in text
    assert 'file39' not in text
    assert "{" not in text
