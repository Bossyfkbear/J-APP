# Validation record — 2026-10-28

Environment: Linux x86_64, Python 3.11.17, CPU; FFmpeg 6.1.1.
Torch/Torchaudio 2.5.1+cpu, DeepFilterNet/DeepFilterLib 0.5.6,
Demucs 4.0.1, NumPy 1.26.4, SoundFile 0.14.0, SciPy 1.14.1,
NARA-WPE 0.0.11, librosa 0.10.2.post1. Dependency compatibility check passed.

## Automated checks

- Full `tests` + `tests_classic` run: 50 passed in 3.92 seconds.
- After process-tree cleanup changes and adding native comparison checks:
  targeted worker/comparison run: 6 passed in 0.93 seconds (3 new checks).
- Native comparison fixture: detects a right-channel-only 2^-40 difference after
  120 seconds in a float64 WAV; reports rate mismatches and unmatched tail frames.
- Worker checks: cancel while a child is active, remove temporary partial output,
  preserve original bytes, reject overwrite, and reject nonzero child exit.

These tests do not use mock inference as evidence of AI quality.

## Actual inference

- Official DeepFilterNet3 archive SHA256:
  `49c52edc8947ae1f9bf50d81530beaf3a2c3245aeaf34b6f31ff535cd22284d2`.
- Official htdemucs checkpoint SHA256:
  `8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4`.
- DeepFilterNet: two-second 96 kHz stereo PCM24 synthetic fixture; output
  192000 frames, 96 kHz, stereo PCM24, finite, no PCM rail hits, source unchanged.
- Demucs: same fixture, actual htdemucs inference and vocal/instrumental float
  exports completed. This verifies model/API/export integration, not musical
  separation accuracy on a reference stem corpus.
- WPE: same fixture, native-rate stereo float export, exact frame count and finite
  samples. This does not establish perceptually successful dereverberation.
- pYIN: A4 440 Hz plus silence, median voiced estimate 441.272 Hz; 300 timeline
  frames. This checks one known tone, not universal pitch accuracy.

## Speech denoise reference measurement

Input: first approximately eight seconds of LibriSpeech 5703-47212-0000,
*Ashiel Mystery — A Detective Story*, chapter 2, narrated by Garth Comira.
Retrieved through librosa's `libri1` example:
https://librosa.org/data/audio/5703-47212-0000.ogg
Collection: https://www.openslr.org/12/
License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ .

Changes: resample to 48 kHz, scale clean peak to 0.5, add deterministic Gaussian
white noise (NumPy seed 2026) at equal RMS, then run official DeepFilterNet3.
Direct reference SNR = 10 log10(sum(clean^2) / sum((clean - test)^2)); no
post-hoc alignment or gain fitting was applied to improve this number.

| Measurement | Result |
| --- | --- |
| Input SNR | approximately 0 dB |
| Enhanced SNR | 14.3279 dB |
| Output duration | 384001 samples / 48000 Hz |
| Output peak | -6.7894 dBFS sample peak |
| Nonfinite samples | 0 |
| Original input hash | unchanged |

The extra sample comes from the preparation resampler, and output length matches
the prepared input exactly. The bundled noisy/enhanced examples are modified
CC-BY-4.0 derivatives with the attribution above. Results from one excerpt and
one white-noise condition are not a perceptual rating or a promise for other
recordings. No human listening certification, PESQ, STOI or labelled stem score
is claimed.

## Actual release blockers

The available environment is Linux, with no display or sound device configured.
The Windows EXE has not been built or run; Windows GUI, DLL loading, external
Python launch, cancellation and physical playback need native acceptance.
There are no calibrated paired microphone recordings for a measured U87 model.
Reliable automatic meter identification remains an implementation gap.

## 2026-10-29 reuse-focused update

Replaced the custom accent-group algorithm with official Beat This! 1.1.0,
Audio2Beats, CPU, upstream minimal postprocessing. Official final0 checkpoint
SHA256: 8c328b45f59d8dd3dff219253ff6a8d6482be57d0133a29140e2febbf8eb8331.
Four focused checks passed in 8.70 seconds on Linux/Python 3.12.14:
actual model inference on a 12-second 120 BPM click track (beat timeline,
downbeats, tempo within 8 BPM), missing local model rejection before inference,
manual A/B offset plus LUFS matching with original hashes unchanged, and silent
excerpt rejection for matching. This is integration evidence, not a music-corpus
accuracy claim. Earlier accent-group test results are superseded by this adapter.
Windows build workflow remains prepared but unexecuted.
# Current-source export regression run — 2026-10-29

Linux/Python 3.12: `pytest -q tests tests_classic` passed 64 tests and 4 subtests
in 9.46 seconds. OMP_NUM_THREADS and OPENBLAS_NUM_THREADS were set to 2;
APT_BEAT_TEST_MODEL selected the previously verified local official checkpoint.
This included actual Beat This! inference. DeepFilterNet, Demucs and WPE
inference were not rerun for this change.

Added coverage: no-hardlink fallback conversion and stem publication, existing
output preservation, cleanup after simulated disk-full writes, residual/copy/
report filename collisions, independence of copied originals, custom -23 LUFS
normalization and silence rejection. File hashes/decoded samples verify source
preservation. Filesystem errors were injected; native exFAT was not tested.
No Windows executable, physical playback or listening sign-off is implied.

