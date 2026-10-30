@echo off
setlocal
cd /d "%~dp0"
REM Explicit opt-in optional audio modules; --list is read-only.
REM The user must choose --with-models to download official models.
if defined APT_PYTHON goto override
py -3.11 -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8" >nul 2>nul
if not errorlevel 1 goto use_py
python -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8" >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3.11 x64 not found. Install it or set APT_PYTHON to its executable.
exit /b 1
:override
"%APT_PYTHON%" scripts\setup_ai_modules.py %*
exit /b %errorlevel%
:use_py
py -3.11 scripts\setup_ai_modules.py %*
exit /b %errorlevel%
:use_python
python scripts\setup_ai_modules.py %*
exit /b %errorlevel%
