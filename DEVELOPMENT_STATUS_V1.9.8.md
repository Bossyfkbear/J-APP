# Audio Post Toolkit V1.9.8

- Extended native Windows frozen-EXE synthetic smoke test to execute the measured microphone matching FIR (not just source-level unit tests). Verifies 48 kHz 2-channel / float WAV / 48,000 frames and original SHA256 preservation.
- Exposes the measured microphone matching reference option through the root CLI (`--reference-path`) while preserving the original optional U87-inspired fallback.
- New CLI regression renders the microphone matching output using source/target reference audio and verifies exact duration and format.
- This is functional integration evidence, not U87 hardware calibration, physical speaker playback, or full mastering-grade listening acceptance.
