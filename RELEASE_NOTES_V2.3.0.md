# Audio Post Toolkit V2.3.0 — desktop setup and high-precision audio

- Lightweight Windows desktop EXE retains its independent AI plugin layout.
- One-click setup from GUI for chosen AI modules (only explicit model downloads) and optional FFmpeg installation via interactive winget batch.
- Installed local DeepFilterNet, Demucs and Beat This! models are auto-discovered, with manual overrides.
- Isolation of PyInstaller DLL search path when launching optional external Python.
- Two-pass loudness normalization preserves source PCM 24-bit, 32-bit float and 64-bit float precision by default, with manual selection.
- Existing 25 UI tool panels, native full-file technical QA, A/B preview and user-triggered device test remain available.
- Windows CI builds GUI, runs source tests, frozen PCM smoke, and installed Python pitch inference from final staged distribution. Five separate AI/DSP Windows inference jobs previously passed on synthetic audio.
