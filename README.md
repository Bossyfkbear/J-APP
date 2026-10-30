# Audio Post Toolkit — integrated development build

Offline desktop toolkit for audio file analysis, conversion, music estimates, integrity inspection and optional local AI speech denoising. It never uploads audio or downloads models automatically.

## Run from source

Requires Python 3.10+, NumPy and SoundFile. Install `requirements.txt`, then:

```text
python app.py
python cli.py --help
python -m apt --help
```

FFmpeg and FFprobe must be on PATH or beside the application. `build_windows.bat` requires Windows/Python 3.11 x64, uses `.venv-apt-core`, and builds a lightweight `dist/AudioPostToolkit/AudioPostToolkit.exe` plus its supporting folder. Torch/models are external. Keep the entire folder together. The script also stages optional-worker sources, dependency notices and a native GUI diagnostic. It has not been run on Windows; no EXE is included in this source archive.

For optional local AI, run `setup_ai_windows.bat`; add `--with-models` to explicitly download checksum-verified official DeepFilterNet3 and htdemucs models during setup. Subsequent processing is offline. This creates `.apt-ai` beside the source or EXE and does not change another Python environment. The GUI can also select an existing Python executable. Re-run setup if the folder is moved.

## Restored desktop workflow

The default desktop entry (`app.py`, `run_gui.py`, `start_windows.bat`) restores
V0.4's dark interface, file queue, waveform overview, individual original/output
preview, batch naming, silence detection, two-pass loudness normalization,
metadata inspection, click/clipping/sibilance repair, residual extraction and
comparison/alignment estimates. `apt` modules from V1.6 onward are retained and
connected for local AI denoise, chords and harmony analysis. The compact V1.9
interface remains available via `python -m apt.gui`.

Model folder pickers are provided. Demucs now uses a supplied local repository
and the Python API, including four-source output; it no longer starts a model
download through the default CLI. Both neural engines have now run successfully
with official weights in the Linux CPU validation environment.

Validation: the current source passed 64 automated tests and 4 subtests in one
9.46-second run on Linux/Python 3.12, including real Beat This! inference.
Earlier DeepFilterNet/Demucs runs are documented in `validation/VALIDATION.md`;
those models were not rerun for the export fixes. These checks do not establish
Windows operation or professional listening acceptance.

## Available functions

- Synchronized A/B audition: choose a 0.1–120 second excerpt and switch on one cursor. Optional dependencies are in `requirements-preview.txt`. Manual B delay compensation supports ±2000 ms; positive values skip B's delayed beginning. Optional matching measures integrated LUFS on equal-length excerpts, applies B gain, then shared sample-peak attenuation if needed. Original files stay unchanged. Silence and differences over 24 LU are rejected for matching. Both excerpts are auditioned at 48 kHz, with matching mono/stereo counts. Automatic delay estimation and physical-device validation remain pending.
- AI beat/downbeat analysis: official Beat This! 1.1.0 with a local final0 checkpoint, using upstream preprocessing and minimal postprocessing. Reports beat/downbeat timestamps and detected beats between consecutive downbeats over up to three minutes. The earlier custom accent-group detector has been removed. Notated time signatures still require interpretation.
- Analyze audio: sample peak, RMS, length, sample rate, channels and subtype.
- Quality check: streamed per-channel sample peak, RMS, PCM full-scale rail hits and nonfinite counts.
- Full precision comparison: stream both entire files at native rate/channel count; report exact decoded-sample identity, residual peak/RMS, correlation and unmatched tail lengths. Different rates/channel counts are reported instead of silently resampling or downmixing.
- WPE late-reverb reduction: optional NARA-WPE linear prediction, independent channels, bounded blocks with overlapping context; preserves sample rate/channels/frame count and writes 32-bit float WAV. This is DSP, not neural dereverberation. Dry/wet ratio is selectable.
- pYIN pitch tracking: optional monophonic 50–1200 Hz estimate with timestamps, note names, cents and voicing probability. Up to the first ten minutes, using the strongest channel; not polyphonic transcription.
- Loudness / True Peak: FFmpeg EBU R128 integrated LUFS, loudness range and true peak. This is a technical measurement, not a listening assessment.
- Convert audio with source rate/channels by default. WAV output keeps a known source PCM subtype (8/16/24/32-bit integer or 32/64-bit float); compressed sources default to 24-bit PCM. Conversion publishes a completed file only and refuses overwrites. Rate, channel count and WAV depth are selectable in the GUI and CLI.
- Estimate tempo, key, chords and chord progression. These are exploratory estimates; no real-world labelled corpus scores are claimed.
- DeepFilterNet AI speech denoise using a model installed locally. Channels are processed independently. The full GUI/root CLI restore the source sample rate/frame count and known PCM subtype after internal 48 kHz processing. Compressed sources use 24-bit PCM. The compact `apt` CLI keeps its existing model-rate/PCM24 contract. Existing files are never overwritten; there is no silent DSP fallback. Upsampling back does not recover bandwidth removed by the model.
- Full GUI AI/WPE/pitch jobs run in an isolated process. Cancel stops the worker and removes uncommitted temporary output. Closing the app allows that cleanup to finish. Optional compressed-format decoding uses the local FFmpeg.
- AI Model Status reports optional runtime and local model availability.
- Vocal separation uses a local Demucs model repository. It exports vocals and
  instrumental as 32-bit float WAV files at the model sample rate, preserving
  headroom without PCM clipping.

## AI denoise setup

Install compatible local `torch`, `torchaudio` and DeepFilterNet packages for your Python/Windows setup. Place the model files locally and select that directory in the GUI. The CLI is:

```text
python -m apt ai-status --model-dir C:\models\DeepFilterNet
python -m apt denoise-ai input.wav cleaned.wav --model-dir C:\models\DeepFilterNet
python -m apt separate-vocals song.wav vocals.wav --model-dir C:\models\Demucs
python -m apt loudness input.wav
```

The status command loads the selected local model to confirm its runtime compatibility. The AI adapter validates input/output finiteness, output length, full-scale headroom and WAV format. Its result includes an audio integrity report. This does not establish that noise was removed transparently; critically listen to the result.

## Audio fidelity limits

AI processing resamples internally to the model's sample rate; retaining the source export format is not bit-perfect processing and cannot restore out-of-band information. PCM output that exceeds available headroom is rejected rather than clipped. WPE and Demucs use float WAV to retain headroom. For conversion, specify codec/rate/channel options carefully. Keep originals.

## Not implemented or not validated

- Calibrated U87 emulation needs paired source/target measurements; the microphone preset remains explicitly an EQ experiment. Reliable automatic meter identification is unfinished.
- WPE and pYIN are implemented; they still need acceptance on real recording sessions. Music estimates have not been benchmarked on a labelled corpus. One speech denoise fixture does not certify transparency.
- GUI visual inspection and physical-device A/B playback are not verified here. Automatic A/B delay estimation is not implemented; manual compensation and loudness matching are available.
- Windows executable creation and runtime validation must be done on Windows.

This is an in-progress personal utility, not a certified restoration or mastering system.

GitHub is optional. See `WINDOWS_BUILD.md` for local Windows builds; the optional
cloud workflow has not been uploaded or executed. Optional setup with
--with-models also downloads the pinned Beat This! checkpoint.

Export fixes: custom loudness targets now apply to both analysis and processing;
silent/unmeasurable files are rejected before normalization. Audio outputs use
no-overwrite publication, including a copy fallback for filesystems without hard
links. The fallback was fault-tested on Linux, not validated on an actual exFAT
disk. During fallback copying, a destination can be visible before completion;
handled write failures remove that partial file. Abrupt power loss can still
leave a partial copy. Batch-renamed copies remain independent of their originals.


### Windows no-overwrite publish hardening (V1.9.1)

On Windows volumes where hard links cannot be created, output publication now
first writes a complete sibling `.partial` file, flushes it, and then uses a
non-replacing same-volume rename. Interrupted copies therefore cannot leave a
partly written *final-named* export. Source audio is never changed. The existing
POSIX fallback remains exclusive but may expose a partial destination while
writing; abrupt power loss is still outside the guarantees of either path.


### GitHub upload and Windows build shortcut (V1.9.2)

If the ChatGPT GitHub connector lacks write permission, use `publish_and_build_windows.bat` with Git for Windows and GitHub CLI. It uses a browser-authenticated GitHub login, commits source without force pushing, starts the Windows Actions workflow, and downloads the resulting development archive on success. See `GITHUB_UPLOAD.md` for requirements and caveats.

### V1.9.3: guarded reports and frozen audio-processing smoke test

- Analysis text reports now stage a full UTF-8 file and publish it using the same non-overwriting mechanism as audio. Cancelled/failed writes leave no publicly visible partial report.
- Pure file renaming works even without FFmpeg. Other audio-processing tools still require the appropriate backend.
- Windows CI now runs a *frozen-EXE* audio smoke test using included synthetic data: preserves a 48 kHz mono floating-point WAV, generates a 44.1 kHz/24-bit WAV, avoids filename collisions, and verifies the input SHA-256 is unchanged. The frozen test emits `native-audio-smoke.json` in the artifact.
- This verifies neither device playback nor the sound of a user recording. FFmpeg and optional AI models remain external; Windows host CI has not yet run due to GitHub authorization.
