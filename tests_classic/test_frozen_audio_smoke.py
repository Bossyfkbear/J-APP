"""A real FFmpeg fixture run, reused by the frozen Windows build."""
from apt.diagnostics import audio_smoke


def test_native_audio_smoke_source_and_output_formats():
    report = audio_smoke()
    assert report['ok'] is True
    assert report['source_sha256_unchanged'] is True
    assert report['pcm24_44100_mono'] is True
    assert report['auto_float_48k_mono'] is True
    assert report['stereo_pcm24_preserved'] is True
    assert report['mic_match_float_stereo_preserved'] is True
    assert report['qa_report_generated'] is True
    assert report['device_playback_tested'] is False
