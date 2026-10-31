# Audio Post Toolkit — integrated development build

Offline desktop toolkit for audio file analysis, conversion, music estimates, integrity inspection and optional local AI speech denoising. It never uploads audio or downloads models automatically.

## Windows 11 development download

**Built Windows development EXE is available through GitHub Actions.** A confirmed successful Windows run is [41109767399](https://github.com/Bossyfkbear/J-APP/actions/runs/41109767399). Successful builds publish a 90-day **Actions artifact**. A permanent [prerelease](https://github.com/Bossyfkbear/J-APP/releases) is also attempted when GitHub grants the workflow a suitable token; GitHub may reject that optional step with HTTP 403. This is not an installer and is not yet a production-validated audio product.

Download `AudioPostToolkit-Windows-Development.zip` from the newest successful prerelease (or the `AudioPostToolkit-Windows-Development` artifact of a successful Actions run), extract **the complete folder**, and run `AudioPostToolkit/AudioPostToolkit.exe`. Keep the supporting files with the EXE. FFmpeg and FFprobe must be installed on PATH or placed beside the EXE; FFplay is needed for individual preview. Optional AI weights/Python are installed only at user request with `setup_ai_windows.bat`. No website deployment is involved. Actual Windows audio-device playback and real-recording quality still require acceptance.

## Run from source

Requires Python 3.10+, NumPy and SoundFile. Install `requirements.txt`, then:

```text
python app.py
python cli.py --help
python -m apt --help
```

FFmpeg and FFprobe must be on PATH or beside the application. `build_windows.bat` requires Windows/Python 3.11 x64, uses `.venv-apt-core`, and builds a lightweight `dist/AudioPostToolkit/AudioPostToolkit.exe` plus its supporting folder. Torch/models are external. Keep the entire folder together. The script also stages optional-worker sources, dependency notices and a native GUI diagnostic. A successful Windows Actions run has built the EXE; the source archive itself does not include compiled binaries.

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
- Windows EXE creation and frozen smoke checks passed on a Windows CI runner; physical audio-device and real-recording quality still need workstation verification.

This is an in-progress personal utility, not a certified restoration or mastering system.

GitHub is optional. See `WINDOWS_BUILD.md` for local Windows builds; the optional
cloud workflow is active and has produced a Windows development artifact. Optional setup with
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

## V1.9.6: optional measured microphone tonal EQ

The microphone-tone tool now accepts a separate reference recording, ideally the **same voice recorded in the same environment and source position**, at the same sample rate. It calculates a conservative one-third-octave tonal EQ (max ±6 dB; adjustable strength), applies a linear-phase FIR in bounded-size blocks, and exports a 32-bit float WAV with the source's original frame count, sample rate and channel count. It never overwrites original recordings. Without a reference, the earlier experimental U87-inspired EQ preset remains available.

**Not calibrated U87 emulation:** a spectral match does not model microphone noise, polar response, proximity effect or electronics. U87 target measurements have not been supplied. This tool remains a development feature requiring professional listening acceptance.

## V1.9.7 — setup and dependency diagnostics

A new **環境檢查 / Environment Check** module runs *without selecting audio*. It reports the installed FFmpeg, FFprobe, FFplay, NumPy and SoundFile and whether an output device is detected. Windows development releases now include **setup_ffmpeg_windows.bat**, a user-initiated optional installation helper using the Windows Package Manager (`winget install --exact --id Gyan.FFmpeg`). It asks for explicit approval, downloads neither on application launch nor without consent, and does not bundle FFmpeg into the lightweight EXE. Reopen the app after installation so PATH refreshes.

The measured microphone reference-EQ mode uses bundled NumPy/SoundFile and does not require FFmpeg, whereas the fallback U87-inspired EQ uses FFmpeg. No model installation or U87 calibration is implied by successful diagnostics.

## V1.9.8 — frozen mic-match and CLI acceptance

The Windows packaged executable's synthetic audio smoke test now runs the **actual measured microphone matching FIR**, checks output 48 kHz stereo / 32-bit float / exact 48,000 frames, and verifies the original source SHA256 did not change. A source-level CLI regression also exercises the same option without relying on an FFmpeg filter. Use:

```text
python cli.py mic source.wav --reference-path target_mic.wav --mic-strength 60 --destination output
```

A target reference must have the same sampling rate as the input. This remains a frequency-response matching EQ; it is **not** calibrated U87 microphone emulation or a perceptual certification.

## V1.9.9 — safe automatic bit depth

For FFmpeg filter operations invoked from the CLI with `--depth auto`, output precision now follows the source's known PCM subtype (including 24-bit and 32/64-bit floating point) instead of incorrectly passing the literal `auto` to a codec table. Compressed or unspecified formats retain the conservative 24-bit PCM default. No source audio is overwritten. Two new real-audio regression checks cover native 24-bit and 32-bit float preservation.

## V2.0.0 — install optional AI modules separately

To keep Windows core small, `setup_ai_windows.bat` now supports installing **only the tool needed**, into a separate `.apt-ai` Python 3.11 x64 virtual environment. It does not run automatically, and model files are downloaded **only** when you explicitly supply `--with-models`. All existing tools and user audio remain untouched. Commands:

```bat
setup_ai_windows.bat --list
setup_ai_windows.bat --module denoise --with-models
setup_ai_windows.bat --module split --with-models
setup_ai_windows.bat --module meter --with-models
setup_ai_windows.bat --module pitch
setup_ai_windows.bat --module dereverb
```

Omitting `--module` installs the original full set for backwards compatibility, but is **not recommended** for light installations. Model download hashes are checked against known pinned official artifacts. The AI venv may require gigabytes of disk space due to PyTorch; each module has its own requirements manifest to avoid unrelated installation work. Each selected neural model is still an optional inference runtime, not part of the lightweight core EXE. Windows 11 real-device neural inference remains pending user workstation verification.

## V2.0.1 — independent optional AI readiness checks

The app's **Environment Check** now reports package presence separately for DeepFilterNet denoise, Demucs separation, Beat This! beat detection, pYIN pitch and WPE dereverb. For neural models, it also verifies that expected local model files exist. The probe runs the optional Python environment with isolated flags and does **not** import PyTorch models, perform inference, install anything or use the network; `ready_for_manual_test` does **not** mean professionally validated. A module that can decode audio with SoundFile may start on WAV/FLAC/AIFF without requiring FFmpeg; other tools and compressed sources still need their respective external codec backends.

## V2.0.2 — Windows packaged AI setup verification

Windows CI now launches **the actual included `setup_ai_windows.bat --list`** inside the finished EXE distribution, validates that all five independent requirement manifests are shipped, and verifies the command does not require or install neural dependencies. The batch script accepts an explicit `APT_PYTHON` environment override, otherwise locates Python 3.11 x64 using the Windows `py` launcher or `python`. It does not install optional packages on application launch.

## V2.0.3 — physical output audition (requires a user)

The Environment Check panel now provides an **explicitly triggered** low-level stereo speaker test: 1 second, 660 Hz, peak at most -30 dBFS, 50 ms fade-in/out. The app asks for permission before playback and for an explicit hearing confirmation afterwards. It never uses or records a microphone and never sends audio elsewhere. The report only reflects the user's session-local confirmation; CI tests the deterministic test waveform and bounds but **cannot verify audible playback** without the user's actual Windows sound hardware and ears. This is a setup aid, not final professional audio listening QA.

## V2.0.4 — correct audio interface clock for speaker check

The opt-in physical speaker test queries the **default output interface** instead of assuming every device supports 48 kHz. It validates stereo playback settings and uses the interface's actual default sample rate (including 44.1 kHz) for a low-volume one-second signal. The test still requires the user to explicitly confirm hearing it.

## V2.0.5 — A/B preview follows the actual audio interface sample rate

The single-clock A/B audition now checks the **default output device's sample rate** and uses it for decoding, loudness comparison and sounddevice playback (44.1 kHz, 48 kHz and other supported rates). Crossfades remain 5 ms regardless of rate and A/B switching retains the playback cursor. Decoding explicitly uses FFmpeg and does not touch or overwrite source audio. Automated Windows tests cover a mocked 44.1 kHz device and actual 48→44.1 kHz files; a workstation test is still needed to confirm real physical device playback and audio quality.

## V2.0.6 — local source/output engineering QA report

Once a selected audio file has been processed, click **生成原音／輸出技術驗收報告 JSON** in the waveform/A-B section. The app reads both full files offline, computes their SHA-256 hashes, checks sample rate, channel count, exact duration difference, PCM subtype, per-channel sample peaks, RMS, clipped and nonfinite samples, and confirms neither file changed during the check. The JSON report is saved under the selected output folder using staging and non-overwriting publication. Differences in rate/channel/duration are warnings, not automatic failures, because they may be deliberate exports. A PASS only means the file is technically readable and stable; it **does not measure true peak, LUFS, AI artifacts or listening quality.** It never transmits audio.

## V2.0.7 — automate the offline engineering QA from the command line

In addition to the GUI QA button, the same **no-overwrite JSON report** is now available for scripted batch workflows:

```text
python cli.py qa original.wav processed.wav --destination QA_Reports
```

The CLI requires exactly two files, exits nonzero for corrupt/unreadable audio, and never uploads anything. A PASS means basic *technical file integrity*, not perceptual quality. The Windows frozen EXE smoke test also generates a real engineering QA JSON from synthetic stereo files and verifies unmodified source SHA-256.

## V2.0.8 — opt-in real AI inference smoke tests (Windows)

For a module already installed with `setup_ai_windows.bat`, the new **`verify_ai_windows.bat`** runs the *actual* installed model against 8 seconds of synthetic stereo test audio, checks the produced result and ensures the input is unchanged. Commands:

```bat
verify_ai_windows.bat --list
verify_ai_windows.bat --module denoise
verify_ai_windows.bat --module split
verify_ai_windows.bat --module meter
verify_ai_windows.bat --module pitch
verify_ai_windows.bat --module dereverb
```

No audio recording, model download, network call or dependency installation is performed by the verification script. A successful result is evidence of **local model execution only**, not professional perceptual quality, real-world microphone emulation or physical audio-interface playback. On a computer without downloaded model weights, model self-test fails explicitly instead of pretending to have passed. Windows CI only verifies the tool and its packaging; it **does not install and run these large AI models automatically**.

## V2.0.9 — Windows Unicode QA regression

The CLI's technical-acceptance test explicitly reads UTF-8 JSON, independent of the Windows console ANSI code page. The QA report itself always writes UTF-8 and preserves Traditional Chinese messages and file names; no audio-processing behavior changed.

## V2.1.0 — run actual installed AI model self-test inside the GUI

Open **環境檢查** and select one installed module (denoise, split, meter, pitch or dereverb), then click **執行所選模型推論自測**. The app requests permission before launching the optional external Python environment and the V2.0.8 real-inference script. It operates on synthetic audio only, performs no package/model download, and shows the success/error details in the process log. You may cancel the subprocess from the app. The 15-minute safety timeout prevents indefinite CPU inference. A PASS is only evidence of this local model processing a short synthetic fixture, not proof of professional listening quality or U87 microphone modelling.

## Real Windows optional DSP acceptance

A separate GitHub Actions workflow [Windows real optional DSP acceptance](https://github.com/Bossyfkbear/J-APP/actions/workflows/windows-optional-dsp.yml) runs **real** (not mocked) pYIN and NARA-WPE processing on deterministic synthetic stereo audio under Windows Python 3.11. Pitch must recover 220Hz within ±15Hz, dereverb must preserve stereo frame count, and the original SHA256 must be unchanged. The workflow attaches JSON proof. This does **not** establish neural pretrained DeepFilterNet/Demucs/Beat This! acceptance, studio DAC playback, or human listening quality.

## Optional full neural checkpoint acceptance on Windows

The separate [Windows real pretrained audio-model acceptance](https://github.com/Bossyfkbear/J-APP/actions/workflows/windows-pretrained-acceptance.yml) matrix runs three independent Windows jobs: DeepFilterNet denoise, Demucs separation and Beat This! tempo/beat tracking. Each installs only its own pinned CPU environment, downloads its explicitly selected official pretrained checkpoint with a fixed SHA-256, and invokes the actual worker on 8 seconds of synthetic audio, retaining JSON evidence. It does not use private recordings. This costly integration test is separate from the lightweight core EXE workflow and **must pass before native pretrained model acceptance can be claimed**. Even a PASS does not substitute professional listening QA or calibrated U87 microphone testing.

## Packaged Windows external-AI end-to-end acceptance

The main Windows development workflow now (after the frozen GUI checks) runs the actual shipped `setup_ai_windows.bat --module pitch` and `verify_ai_windows.bat --module pitch` from inside the complete EXE release folder. This tests venv creation, pinned `librosa` installation, staging of the external Python worker, real pYIN processing on synthetic audio, source SHA256 preservation and 220Hz accuracy. The temporary optional `.apt-ai` is removed **before ZIP packaging**, so the portable core remains lightweight. The small UTF-8 `native-pitch-inference.json` is included as technical evidence. Other pretrained models passed in their own Windows CPU acceptance jobs; device playback and listening QA remain workstation-only.

## Beat-tracker numerical acceptance

The real Beat This! test now checks the **measured tempo** and a nonempty beat timeline, rather than only checking the presence of `beat_seconds` keys. For the deterministic 120 BPM click fixture, acceptance requires 4+ detected beats and 100–140 BPM (generous 20 BPM tolerance). The report preserves beat/downbeat counts and tempo. If actual inference misses that reference, the CI fails and the limitation must be addressed instead of being called a pass.

## Windows one-click optional AI setup

On the **Environment Check** panel, choose the desired AI module and click **安裝所選 AI 模組**. Installation requires explicit approval. Only the chosen module is installed in an isolated `.apt-ai` Python 3.11 environment; DeepFilterNet, Demucs and Beat This! also download the requested official SHA256-pinned model (with a disk-space warning). There is a cancellable 30-minute installation limit, and installation results appear in the process log. When installation finishes, the desktop app **automatically discovers** the canonical model folder on the next tool selection; manually selected model folders remain supported. The default core EXE remains small and retains source audio unchanged.

### Frozen Windows DLL isolation for optional AI

The integrated AI installer and model self-test now launch external Python with the PyInstaller-modified DLL search directory temporarily cleared and restored. This prevents the frozen desktop EXE from contaminating third-party scientific-library DLL resolution in the optional venv. The core app still does not bundle optional AI weights.

## V2.2.2: mastering-preserving loudness export

Two-pass loudness normalization now defaults to preserving the source's known PCM sample precision, including 32-bit float and 64-bit float, instead of silently exporting 24-bit PCM. Stereo channel count and source sample rate remain unchanged, and the panel offers explicit depth overrides. Regression tests verify float32 and 24-bit stereo with unchanged source SHA-256.

## One-click FFmpeg setup

The Environment Check panel includes **安裝／修復 FFmpeg（Windows）**. It opens the included interactive `setup_ffmpeg_windows.bat` and requires explicit user consent for any winget installation. This keeps external FFmpeg binaries out of the lightweight core ZIP and avoids silent downloads on startup.

## BPM / key: results-only popup (V2.3.1)

Selecting **BPM／調性** and clicking **開始處理** now opens a single compact result popup containing only `BPM:`, `拍號:`, and `調性:` after the audio has been analyzed. The GUI no longer dumps analysis JSON or creates a text report for this operation. The time signature is shown as **無法判定** when it cannot be reliably detected, rather than fabricating 4/4; the separately installed Beat This! model provides its own beat/downbeat tool. Multi-file jobs show one grouped result popup with each filename.

## V2.3.2 — results-first desktop workflow

All 25 audio tool panels now return a concise, readable **完成結果** popup: processing tools show the output file or folder; analysis tools show values, timestamps or comparison summaries; rhythm shows only BPM, time signature and key; setup shows which core/AI modules are ready. Batched files are consolidated into one bounded summary rather than flooding dialogs. Technical machine-readable reports may still be saved behind the scenes for auditing, but no raw JSON, FFmpeg command lines or Python traceback appears in the normal GUI. The previous PROCESS LOG panel is hidden by default, retaining an internal diagnostic buffer. Errors are summarized in plain language and the original source files stay unchanged.

## V2.3.3 — four integrated category workspaces

The desktop sidebar is now consolidated into **four major categories** only: **轉換與交件**, **修復**, **音樂與 AI**, and **音色與檔案**. Choosing a category opens one integrated workspace with its tools in a compact grid at the top. For example, **修復** includes WPE dereverb, noise residual, declick, declip and de-ess, while **音樂與 AI** includes neural denoise/separation, BPM/key, beat tracking, pitch and chord/progression analysis. Moving between a category's tools retains selected source files, output folder and per-tool settings, and each action still provides only a concise user-readable result popup rather than raw logs. All 25 existing independent processing functions remain in place.
