# Audio Post Toolkit V1.9.3 — development handoff (2026-10-29)

## Changes made from V1.9.2

- `aptk/core.py`: lossless staged publication for UTF-8 text reports. A cancelled write or copy failure cannot leave an incomplete final report. Existing filenames are never overwritten.
- `aptk/ui.py`: batch renaming does not require FFmpeg, because it copies original bytes without audio decoding.
- `apt/diagnostics.py` and `run_gui.py`: added deterministic end-to-end source audio processing smoke tests and `--smoke-test <jsonpath>` for the frozen app.
- `.github/workflows/windows-build.yml`: added mandatory post-freeze 48k/32f + 44.1k/24-bit conversion, collision safety, input SHA verification, and collection of the generated `native-audio-smoke.json`. Uses `ffmpeg`/`ffprobe` for CI; `ffplay` optional.
- `tests_classic/test_export_safety.py`, `tests_classic/test_frozen_audio_smoke.py`: new tests for failed text publication, cancellation, Unicode, collision handling, and actual FFmpeg processing.
- Version identifier bumped to 1.9.3-integrated. No older DSP or optional AI modules were removed.

## Verification

- Native Python source compile: successful on Linux.
- Actual FFmpeg processing smoke check: passed; synthetic source hash unchanged.
- Focused regression suite: 11 passed, 1 skipped.
- Full Python suite completed on Linux/Python 3.13: **67 passed, 2 skipped, 4 subtests passed**. Both skips are Windows-specific or optional model-dependent. This is not native Windows acceptance.
- No native Windows EXE or actual audio-device tests have been completed. Do not label as a production-ready release.
- GitHub J-APP still blocked: connector reports `Resource not accessible by integration` (HTTP 403) for write operations. Read permission does not authorize a commit.

## Next

1. Configure ChatGPT GitHub App installation under Bossyfkbear with repository Contents write access, or upload with `publish_and_build_windows.bat` using GitHub CLI on the user's Windows machine.
2. Execute Windows GitHub Actions and inspect native diagnostics, audio smoke and artifact SHA256. Fix actual runner failures if present.
3. Record Windows soundcard A/B playback tests; perform real speech listening, AI weight/runtime QA, and U87 calibration only if reference recordings are supplied.
