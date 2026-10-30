# V2.0.5

- Corrected A/B audition to use the default output device sample rate instead of assuming 48 kHz.
- Applied same rate to FFmpeg preview snippets, loudness-measurement WAVs, PortAudio output stream, and 5ms crossfades.
- Kept A/B aligned on one playback cursor and read-only sources.
- Added tests for default 44.1kHz interface, real 48→44.1kHz preparation, stream rate and cursor continuity.
- No claim of completed physical audio-device or music-listening QA.
