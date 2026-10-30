# Integration state

V1.6 was not a complete replacement for V0.4. The original V0.4 source was recovered from the user handoff archive and integrated in aptk, with apt preserved. app.py/run_gui.py open the restored full UI. Individual ffplay preview is retained. A separate synchronized A/B player now uses a shared sample cursor and bounded in-memory excerpts through optional sounddevice.

Validated on Linux/Python 3.11: real DeepFilterNet3 and Demucs htdemucs CPU inference; WPE processing; pYIN A4 fixture; 50 existing/core/worker tests plus 3 new native-comparison tests. A speech-plus-white-noise fixture improved direct reference SNR from approximately 0 to 14.33 dB. This is one fixture, not a perceptual certification. See validation/VALIDATION.md.

Implemented this integration: cancellable subprocess workers, staged output publication, external AI Python selection, lightweight core build with external optional runtime, explicit checksum-verified official-model installer, WPE late-reverb reduction, pYIN monophonic pitch timeline, and native-rate full-file per-channel comparison. AI status no longer needs an audio file. GUI denoise preserves known source PCM format/rate/length after internal model-rate processing. Dependency notices and native-build diagnostics are collected during packaging.

Open release blockers: no Windows host is available to create and run the EXE; no display/audio device is available here for GUI/physical playback acceptance; no calibrated source/target U87 recordings were supplied. Notated meter interpretation and a labelled real-recording music-analysis benchmark remain unfinished. WPE and pYIN are implemented but not accepted on the user's real recording workload. A/B automatic delay alignment remains optional unfinished work; manual compensation and LUFS matching are implemented. Physical device output is unverified.

Do not count build scripts as an EXE. setup_ai_windows.bat installs into an external .apt-ai environment; --with-models explicitly downloads pinned official models. The application itself never downloads models or uploads audio. Frozen Windows integration, child-process termination and DLL handling still require native verification.

Do not call this a complete product. Do not silently discard either apt or aptk while resolving remaining duplication. Keep original audio unchanged. Do not implement auto sentence splitting.

Later update: manual A/B delay compensation and integrated-LUFS matching are now
implemented and checked with original-hash preservation. Official Beat This!
1.1.0 now supplies beat/downbeat timelines; the custom accent-group detector
was removed. Definitive score-meter interpretation remains unresolved.
Four targeted checks including real Beat This! inference passed. The manual Windows
Actions workflow is prepared but unexecuted; no matching installed GitHub
repository was found. This supersedes the earlier A/B loudness-matching gap.

2026-10-29 export fixes: both normalization passes use the requested targets;
silence is rejected clearly; outputs have a no-overwrite fallback where hard
links are unavailable; residual/copy/report filename collisions preserve
existing files; FFmpeg cancellation is checked before output publication and
termination has a bounded graceful wait. Failed GUI jobs no longer display a
green success indicator. Both Windows setup scripts accept APT_PYTHON and
reject incompatible pre-existing virtual environments without deleting them.

Current source: 64 tests and 4 subtests passed in one 9.46-second run on
Linux/Python 3.12, including real Beat This! inference. Unsupported-hardlink and
disk-full cases use injected filesystem errors, not a native exFAT test.
Earlier model-validation records remain separate from this run.

The local Wine build attempt failed at startup with
`wineserver: socket: Operation not permitted`, before Windows Python/EXE
creation. No EXE exists. GitHub remains optional; no workflow was run.
