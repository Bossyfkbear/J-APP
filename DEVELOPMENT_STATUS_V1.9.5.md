# V1.9.5 development handoff

## Verified baseline (2026-10-31, Asia/Taipei)

The previous main commit `99294e9` passed **Windows development build** on GitHub Actions run [41109767399](https://github.com/Bossyfkbear/J-APP/actions/runs/41109767399). The workflow produced `AudioPostToolkit-Windows-Development` (ZIP artifact; 14-day retention). This was the first confirmed Windows frozen build; do not confuse it with real sound-card listening QA.

## This change

- Centralize raw binary subprocess output to a cancellable, timeout-bounded runner.
- Keep FFmpeg's binary PCM undecoded; prevent console flashes on Windows.
- Apply it to waveform overview, 120-second comparison and alignment analysis.
- Add tests for exact bytes, failures, timeout and cancellation.
- Preserve original audio and existing independent tools.

## Still required for general release

- Run application on a real Windows 11 workstation with FFmpeg/FFprobe/FFplay installed or staged.
- Test sound-device A/B, physical preview and optional AI environment on actual session material.
- Check artist/audio engineer listening acceptance and model quality; U87 is still experimental EQ.
- No website is needed: this is a Windows desktop tool, not a web app.
