@echo off
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
  echo [HATA] "py" launcher bulunamadi. Python 3.11+ kurun veya PATH'e ekleyin.
  pause
  exit /b 1
)

echo Derleme ortami: Python 3.12 ^(3.10.0 ile PyInstaller/bottle analizi cokuyor^)
py -3.12 -m venv .build_venv --clear
if errorlevel 1 (
  echo [HATA] Python 3.12 yok. https://www.python.org/downloads/ adresinden kurun.
  pause
  exit /b 1
)

.build_venv\Scripts\python.exe -m pip install -q --upgrade pip
.build_venv\Scripts\python.exe -m pip install -q -r requirements-build.txt
.build_venv\Scripts\pyinstaller.exe --noconfirm tradinwidget.spec
if errorlevel 1 (
  echo [HATA] PyInstaller basarisiz.
  pause
  exit /b 1
)
echo.
echo Tamam: dist\TradinWidget.exe
pause
