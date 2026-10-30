# Audio Post Toolkit V1.9.2 — continuation (2026-10-29)

## Changes from V1.9.1

- Added an opt-in Windows helper: `publish_and_build_windows.bat` + PowerShell script. It signs in using official GitHub CLI browser authentication, verifies the target GitHub account and write permission, pushes without force, triggers the Windows workflow, watches it and downloads the artifact after success.
- Added `GITHUB_UPLOAD.md` and annotated the existing build documentation.
- Strengthened Windows GitHub Actions portability: when FFmpeg is missing from the runner PATH, the workflow installs it using Chocolatey for **CI test execution** and adds its bin directory to PATH. FFmpeg remains an external prerequisite for using the downloadable EXE.
- Ignored downloaded CI binaries in `.gitignore` to avoid accidental repository commits on rerun.
- No existing DSP algorithms, AI adapters, GUI tool modules or user recordings were removed or modified in this iteration.

## Verification and limitations

- Python source compilation was successful on Linux. Targeted export safety + validation tests: **10 passed, 1 skipped** (Windows-only). Full suite from previous V1.9.1 evaluation: **63 passed, 2 skipped, 4 subtests passed**; this is historical evidence, not a fresh Windows result.
- GitHub connector read works, but `create_file` still returns HTTP 403 `Resource not accessible by integration`; `Bossyfkbear/J-APP` remains empty at last check. No remote commit or Windows build has been made by this session.
- The Windows uploader script and workflow have not been executed on actual Windows; treat as candidate until run.
- Physical playback, processing quality, optional AI on Windows, and U87 calibration remain unverified.
