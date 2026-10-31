"""Simple, copy-friendly musical results. No JSON or invented time signature."""
from aptk.rhythm_result import format_summary, summary_lines


def test_three_line_result_has_only_requested_fields():
    report={'tempo':{'bpm':120.0,'confidence':.5,'alternatives':[{'bpm':60}]},
            'key':{'key':'C major','candidates':[{'score':.7}]}}
    summary=format_summary(report)
    assert list(summary)==['BPM','拍號','調性']
    assert summary=={'BPM':'120','拍號':'無法判定','調性':'C 大調'}
    assert summary_lines(summary).splitlines()==[
        'BPM: 120','拍號: 無法判定','調性: C 大調']


def test_no_guessing_time_signature():
    summary=format_summary({'tempo':{'bpm':93.4},'key':{'key':'A minor'},
                            'meter':{'bars':[{'detected_beats':4}]}})
    assert summary['拍號']=='無法判定'
    assert summary['調性']=='A 小調'
    assert summary['BPM']=='93.4'


def test_all_unknown_does_not_crash():
    assert format_summary({})=={
        'BPM':'無法判定','拍號':'無法判定','調性':'無法判定'}


def test_explicit_meter_only_when_available():
    result=format_summary({'tempo':{'bpm':60},'key':{'key':'F# minor'},
                           'meter':{'time_signature':'3/4'}})
    assert summary_lines(result)=='BPM: 60\n拍號: 3/4\n調性: F# 小調'
