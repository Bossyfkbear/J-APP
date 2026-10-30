# Audio Post Toolkit V1.9.7

- Add fileless environment diagnostics within the existing desktop interface; visible report of FFmpeg/FFprobe/FFplay and runtime readiness. Diagnostics do not install dependencies.
- Add an explicit, opt-in Windows FFmpeg installer helper using the public winget package `Gyan.FFmpeg`, copied to the release folder. Do not bundle FFmpeg into core EXE to keep the default distribution small.
- Measured reference EQ from V1.9.6 may run without FFmpeg; the U87-inspired fallback still requires FFmpeg.
- Windows CI checks the helper has been staged. Desktop audio-device output remains unverified by CI, and U87 is an uncalibrated tonal experiment.

## Release publication hardening

The V1.9.6 Windows run passed 81 tests, GUI boot and frozen WAV conversion, but the optional `gh release create` step returned HTTP 403. The Action now treats such Release publication errors as a warning while retaining the verified Windows ZIP as a 90-day Actions Artifact; documentation distinguishes actual EXE build success from optional permanent hosting.
