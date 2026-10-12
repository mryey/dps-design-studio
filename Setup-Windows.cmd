@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name "DPS Design Studio" app.py
if errorlevel 1 goto failed
powershell -NoProfile -File "%~dp0Install-Windows.ps1"
if errorlevel 1 goto failed
echo DPS Design Studio is installed. Use the desktop shortcut.
pause
exit /b 0
:failed
echo Setup did not finish. Keep this window open and copy the error above.
pause
exit /b 1
