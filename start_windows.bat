@echo off
chcp 65001 > nul
cd /d "%~dp0"
if exist .venv-apt-core\Scripts\python.exe (
  .venv-apt-core\Scripts\python.exe app.py
  goto finish
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.11 -c "import tkinter" >nul 2>nul
  if not errorlevel 1 (
    py -3.11 app.py
  ) else (
    py -3 app.py
  )
) else (
  python app.py
)
:finish
if errorlevel 1 (
  echo.
  echo Start failed. AI features require Python 3.11 x64 and compatible dependencies.
  pause
)
