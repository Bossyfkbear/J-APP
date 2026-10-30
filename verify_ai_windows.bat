@echo off
setlocal
cd /d "%~dp0"
REM No model downloads or installation. Runs a real inference smoke on synthetic audio.
REM Usage: verify_ai_windows.bat --module denoise
REM        verify_ai_windows.bat --module split
REM        verify_ai_windows.bat --module meter
REM        verify_ai_windows.bat --module pitch
REM        verify_ai_windows.bat --module dereverb
if /I "%~1"=="--list" (
  if defined APT_PYTHON (
    "%APT_PYTHON%" scripts\verify_optional_ai.py --list
    exit /b %errorlevel%
  )
  py -3.11 scripts\verify_optional_ai.py --list
  exit /b %errorlevel%
)
if not exist ".apt-ai\Scripts\python.exe" (
  echo Optional AI environment is missing. Install only the selected module first:
  echo setup_ai_windows.bat --module denoise --with-models
  exit /b 1
)
".apt-ai\Scripts\python.exe" scripts\verify_optional_ai.py %*
exit /b %errorlevel%
