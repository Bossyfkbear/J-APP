@echo off
setlocal
cd /d "%~dp0"
echo Audio Post Toolkit - optional FFmpeg installer
echo This script uses the official Windows Package Manager and DOES NOT run automatically.
where ffmpeg >nul 2>nul
if not errorlevel 1 (
  where ffprobe >nul 2>nul
  if not errorlevel 1 (
    echo FFmpeg and FFprobe are already available on PATH.
    echo Run the application environment check to confirm FFplay availability.
    exit /b 0
  )
)
where winget >nul 2>nul
if errorlevel 1 (
  echo The winget command is unavailable. Install Microsoft App Installer first,
  echo or download FFmpeg from https://www.gyan.dev/ffmpeg/builds/
  echo and place ffmpeg.exe, ffprobe.exe, ffplay.exe beside AudioPostToolkit.exe.
  pause
  exit /b 1
)
echo You are about to install the third-party Gyan.FFmpeg package via winget.
echo You must approve the install. No audio file is sent or uploaded.
choice /C YN /M "Continue with winget installation"
if errorlevel 2 exit /b 0
winget install --exact --id Gyan.FFmpeg --source winget --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
  echo Installation was not completed; check winget errors above.
  pause
  exit /b 1
)
echo FFmpeg installation finished. Close and reopen Audio Post Toolkit
echo so the new system PATH becomes available, then use Environment Check.
pause
