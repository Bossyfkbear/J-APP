@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_and_build_windows.ps1"
if errorlevel 1 (
  echo.
  echo Upload or Windows build failed. Read the error above. Your original files are unchanged.
  pause
  exit /b 1
)
echo.
echo Finished. Check windows-build-artifact for the downloaded build.
pause
