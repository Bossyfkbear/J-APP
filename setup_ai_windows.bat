@echo off
setlocal
cd /d "%~dp0"
set "APT_LAUNCH=py -3.11"
if defined APT_PYTHON set APT_LAUNCH="%APT_PYTHON%"
%APT_LAUNCH% -c "import sys,struct; assert sys.platform=='win32' and sys.version_info[:2]==(3,11) and struct.calcsize('P')==8"
if errorlevel 1 (
  echo Optional AI requires Python 3.11 x64.
  exit /b 1
)
if not exist .apt-ai\Scripts\python.exe %APT_LAUNCH% -m venv .apt-ai
if errorlevel 1 exit /b 1
set "APT_AI_PY=%~dp0.apt-ai\Scripts\python.exe"
"%APT_AI_PY%" -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8"
if errorlevel 1 (
  echo Existing .apt-ai must use Python 3.11 x64. Move it aside and rerun setup.
  exit /b 1
)
"%APT_AI_PY%" -m pip install -r requirements-ai-windows.txt -r requirements.txt
if errorlevel 1 exit /b 1
"%APT_AI_PY%" -c "import torch,torchaudio; from df.enhance import init_df,enhance; from demucs.pretrained import get_model; from demucs.apply import apply_model; from beat_this.inference import Audio2Beats"
if errorlevel 1 (
  echo AI import check failed. See the error above.
  exit /b 1
)
"%APT_AI_PY%" -m pip check
if errorlevel 1 exit /b 1
"%APT_AI_PY%" -m pip freeze > ai-runtime-installed.txt
if /I "%~1"=="--with-models" (
  "%APT_AI_PY%" scripts\download_models.py
  if errorlevel 1 exit /b 1
)
echo Optional AI environment is ready. Select your local model in the application.
echo Use --with-models to download the pinned official models during setup.
echo Re-run setup after moving this folder.
