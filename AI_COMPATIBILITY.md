# AI compatibility findings

Inspected the actual PyPI distributions demucs 4.0.1 and deepfilternet 0.5.6.

- Demucs 4.0.1 does not ship demucs.api. Both frontends now share an adapter using its shipped get_model, apply_model and convert_audio functions.
- DeepFilterNet 0.5.6 may raise SystemExit when checkpoints are missing. The adapter catches this as a normal model error, preventing a worker from silently exiting while the UI remains busy.
- Model directories are resolved to absolute paths before loading, so a local folder named DeepFilterNet is not treated as an upstream download alias. Model logging is disabled to avoid writing into the supplied model directory.
- No deepfilterlib 0.5.6 Windows cp312 wheel was available through the package index checked. The cp311 Windows x64 wheel was downloaded successfully. Windows AI packaging therefore uses a separate Python 3.11 environment.
- CPU dependencies are in requirements-ai-windows.txt. Torch/Torchaudio 2.5.1+cpu, DeepFilterNet/DeepFilterLib 0.5.6 and Demucs 4.0.1 were installed and used successfully with Python 3.11 on Linux. The corresponding Windows environment remains unverified. Transitive dependencies are not fully locked; setup records the installed versions and runs pip check. Packaging is pinned to 23.2 because DeepFilterNet requires <24.

Verified in this environment: real local model loading, 96 kHz stereo denoising with return to source format/length, actual htdemucs vocal/instrumental inference, WPE processing, pYIN A4 tracking, source hashes unchanged, a speech denoise reference measurement, and isolated worker cancellation/no-publication-on-failure. Worker lifecycle tests do not establish native Windows process behavior. Perceptual acceptance and native Windows packaging still require validation.

Models and optional runtimes are loaded only when used. The default build now excludes Torch, Demucs, DeepFilterNet, librosa and NARA-WPE. It includes external-worker source files and can use .apt-ai beside the EXE, APT_AI_PYTHON, or the GUI's explicit Python selection. A Python venv must be recreated after moving it. The build produces an EXE plus dependencies, not a single-file portable EXE. No Windows EXE has been generated in this Linux environment.
