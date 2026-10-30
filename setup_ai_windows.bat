@echo off
setlocal
cd /d "%~dp0"
REM Explicit opt-in: no optional AI or model downloads on normal application launch.
REM Usage: setup_ai_windows.bat --module denoise --with-models
REM        setup_ai_windows.bat --module split --with-models
REM        setup_ai_windows.bat --module meter --with-models
REM        setup_ai_windows.bat --module pitch
REM        setup_ai_windows.bat --module dereverb
REM        setup_ai_windows.bat --list
set "APT_LAUNCH=py -3.11"
if defined APT_PYTHON set "APT_LAUNCH="%APT_PYTHON%""
%APT_LAUNCH% scripts\setup_ai_modules.py %*
if errorlevel 1 (
  echo Optional module setup failed. See the error above.
  exit /b 1
)
echo Optional module setup finished.
