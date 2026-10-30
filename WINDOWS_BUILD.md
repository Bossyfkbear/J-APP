# Windows build — GitHub is optional

The source archive contains no built EXE. The GitHub Actions workflow is now
active and has successfully generated a Windows development EXE folder.
Successful main-branch builds publish a **development prerelease** with a
downloadable ZIP and SHA-256 record. No website is deployed.
The prerelease is not a claim of device-playback or perceptual sound quality.

## Local Windows build

On Windows with Python 3.11 x64, run `build_windows.bat`. It builds the original
desktop interface, stages the external AI worker and dependency notices, and
initializes every GUI panel through the built executable. Set `APT_PYTHON` to
an existing Python 3.11 x64 executable if the `py` launcher is absent. Both the
build and optional AI setup scripts honor this setting.

Keep the entire resulting `dist/AudioPostToolkit` folder together; the EXE
depends on its supporting files. Optional `setup_ai_windows.bat --with-models`
installs the external runtime and pinned official models. No GitHub account or
repository is required for local building.

The current Linux/Wine attempt failed with `wineserver: socket: Operation not
permitted` before a Windows Python or EXE could run. No executable was produced;
native Windows execution and physical audio acceptance are still required.

## Optional cloud build

Place the contents of the `AudioPostToolkit` directory at the root of the chosen
GitHub repository, including `.github/workflows/windows-build.yml`. Run the
manual **Windows development build** action. It uses Windows 2022 / Python 3.11
x64, runs the build script and frozen application's GUI initialization check,
then retains the whole application folder as a ZIP with a SHA256 record.

The build is a development artifact. FFmpeg/FFprobe/FFplay and AI weights are
external. No runner audio-device or listening acceptance is claimed. Read the
native diagnostic for missing executables. GitHub repository access and Actions
availability are required; any account usage is governed by that account.

References: https://docs.github.com/en/actions/get-started/quickstart
and https://github.com/actions/upload-artifact .

## GitHub Actions evidence (V1.9.1 preparation)

The workflow first runs the source regression suite, then checks that the Windows
EXE exists and its native JSON diagnostic explicitly reports a frozen process and
all tool panels initialized. A green Actions run is **not** proof that real Windows
audio devices work, that models are installed, or that the audio quality passes
engineer listening tests. The EXE and support directory must remain together.

The published development ZIP currently relies on FFmpeg/FFprobe/FFplay being
installed or supplied alongside the EXE. The Windows runner having FFmpeg does
not mean those executables were bundled into the release artifact.


## Browser-authenticated GitHub upload helper (V1.9.2)

Use `publish_and_build_windows.bat` from the source folder to upload via the GitHub CLI after you sign in as `Bossyfkbear`, start the Windows workflow, and download the artifact after a green run. See `GITHUB_UPLOAD.md`. It does not bypass any repository permissions or guarantee a successful Windows build.

## Frozen audio-processing check (V1.9.3)

In addition to the GUI test, the cloud Windows workflow runs `AudioPostToolkit.exe --smoke-test <json-output-path>` after staging. The executable must decode an included **synthetic test fixture**, perform float-preserving and 24-bit conversion, preserve the fixture SHA-256 hash, and publish distinct outputs without replacement. The resulting `native-audio-smoke.json` is retained alongside GUI diagnostics. No real soundcard or human listening is exercised.

The CI installer requires `ffmpeg` and `ffprobe` for audio tests. `ffplay` is optional; its availability is reported, not counted as physical soundcard verification.

## V1.9.4 additional release checks

The local Windows `build_windows.bat` now checks frozen audio conversion in addition to GUI
initialization; it exits with an error if synthetic float/24-bit export or source integrity
checks fail. In the cloud workflow, the same executable is smoke-tested and the Windows
artifact includes the JSON evidence. It also tests 48 kHz 24-bit **stereo** decoded-sample
equality so that a regression causing unintended mono downmix fails the build.

A green build still does not prove acoustic transparency on arbitrary source material,
physical soundcard compatibility, or AI model quality. The release folder needs external
FFmpeg; see README for required tools and optional installs.

## Published development prereleases (2026-10-31)

GitHub Actions [confirmed Windows build](https://github.com/Bossyfkbear/J-APP/actions/runs/41109767399) produced an EXE folder and passed frozen GUI and synthetic-audio smoke tests. Newly successful main-branch runs publish a versioned prerelease under [Releases](https://github.com/Bossyfkbear/J-APP/releases), with the same ZIP and SHA256 record. The Actions artifact is retained up to 90 days; the prerelease download remains available unless manually removed.

On Windows 11, extract the full ZIP and run `AudioPostToolkit/AudioPostToolkit.exe`. Ensure external FFmpeg and FFprobe are on PATH or beside the EXE. For ffplay preview, also provide ffplay. Physical soundcard checks, real-session listening, AI model runtimes and U87 calibration have **not** passed end-user acceptance.
