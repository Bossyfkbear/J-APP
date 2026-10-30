@echo off
setlocal
cd /d "%~dp0"
set "APT_LAUNCH=py -3.11"
if defined APT_PYTHON set APT_LAUNCH="%APT_PYTHON%"
%APT_LAUNCH% -c "import sys,struct; assert sys.platform=='win32' and sys.version_info[:2]==(3,11) and struct.calcsize('P')==8"
if errorlevel 1 (
  echo Windows and Python 3.11 x64 are required to build.
  exit /b 1
)
if not exist .venv-apt-core\Scripts\python.exe %APT_LAUNCH% -m venv .venv-apt-core
if errorlevel 1 exit /b 1
set "APT_BUILD_PY=%~dp0.venv-apt-core\Scripts\python.exe"
"%APT_BUILD_PY%" -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8"
if errorlevel 1 (
  echo Existing .venv-apt-core must use Python 3.11 x64. Move it aside and rerun build.
  exit /b 1
)
"%APT_BUILD_PY%" -m pip install -r requirements-build.txt -r requirements-preview.txt
if errorlevel 1 exit /b 1
"%APT_BUILD_PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --name AudioPostToolkit --collect-all soundfile --collect-all sounddevice --collect-all tkinterdnd2 --collect-all numpy --exclude-module torch --exclude-module torchaudio --exclude-module df --exclude-module demucs --exclude-module librosa --exclude-module nara_wpe --paths . run_gui.py
if errorlevel 1 exit /b 1
"%APT_BUILD_PY%" scripts\stage_windows_release.py dist\AudioPostToolkit
if errorlevel 1 exit /b 1
start "" /wait "%~dp0dist\AudioPostToolkit\AudioPostToolkit.exe" --diagnostics "%~dp0dist\AudioPostToolkit\native-diagnostics.json"
if errorlevel 1 (
  echo Native GUI initialization failed. Check native-diagnostics.json before using this build.
  exit /b 1
)
start "" /wait "%~dp0dist\AudioPostToolkit\AudioPostToolkit.exe" --smoke-test "%~dp0dist\AudioPostToolkit\native-audio-smoke.json"
if errorlevel 1 (
  echo Frozen audio processing smoke-test failed. See native-audio-smoke.json.
  exit /b 1
)
echo Built lightweight dist\AudioPostToolkit\AudioPostToolkit.exe
echo Keep the whole folder together. Optional AI is installed separately.
echo Native audio/GUI validation is still required before release.
