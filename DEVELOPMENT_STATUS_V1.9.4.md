# Audio Post Toolkit V1.9.4 — Development progress

- Base: V1.9.3 source; no function or existing module removed.
- Added local frozen-EXE audio smoke check to Windows build script (formerly Actions-only).
- Extended real FFmpeg smoke test with native-rate 24-bit stereo: frame/channel/rate/subtype checks, decoded-sample identity and SHA-256 source integrity.
- Improved A/B audition: reject nonoverlapping/out-of-range previews, hide FFmpeg child console on Windows.
- Extended Windows CI to reject failed stereo checks.
- No GitHub upload / Windows EXE / device playback acceptance asserted here. GitHub App integration must have explicit repository Contents write permission on Bossyfkbear/J-APP; previous writes returned 403.
- AI/U87 quality verification and beat/time-signature guarantees remain outside these tests.
