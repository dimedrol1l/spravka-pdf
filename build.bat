@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Razdelenie spravok - Windows build

set "ROOT=%~dp0"
set "RELEASE=%ROOT%releases\RazdelenieSpravok-windows-x64.zip"
set "TESSERACT=%TESSERACT_HOME%"
if not exist "%TESSERACT%\tesseract.exe" set "TESSERACT=%ROOT%vendor\tesseract"
if not exist "%TESSERACT%\tesseract.exe" set "TESSERACT=%ProgramFiles%\Tesseract-OCR"
if not exist "%TESSERACT%\tesseract.exe" set "TESSERACT=%ProgramFiles(x86)%\Tesseract-OCR"

if exist "%RELEASE%" (
    echo Refusing to overwrite existing release:
    echo %RELEASE%
    exit /b 1
)
if not exist "%TESSERACT%\tesseract.exe" (
    echo ERROR: Tesseract was not found. Install it or set TESSERACT_HOME.
    exit /b 1
)
if not exist "%TESSERACT%\tessdata\rus.traineddata" (
    echo ERROR: Russian Tesseract data is missing.
    exit /b 1
)
if not exist "%TESSERACT%\tessdata\eng.traineddata" (
    echo ERROR: English Tesseract data is missing.
    exit /b 1
)
set "TESSERACT_HOME=%TESSERACT%"

set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON=py -3"
if not defined PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON=python"
)
if not defined PYTHON (
    echo ERROR: Install Python 3.11 or newer and add it to PATH.
    exit /b 1
)
%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.11 or newer is required.
    exit /b 1
)

set "BUILD_ROOT=%TEMP%\spravki-build-%RANDOM%-%RANDOM%"
mkdir "%BUILD_ROOT%" 2>nul
if errorlevel 1 (
    echo ERROR: Could not create temporary build directory.
    exit /b 1
)
set "VPY=%BUILD_ROOT%\venv\Scripts\python.exe"
set "PYINSTALLER_CONFIG_DIR=%BUILD_ROOT%\pyinstaller-config"
set "SPRAVKI_BUILD_ROOT=%BUILD_ROOT%"

%PYTHON% -m venv "%BUILD_ROOT%\venv"
if errorlevel 1 goto :fail
"%VPY%" -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto :fail
"%VPY%" packaging\self_test.py
if errorlevel 1 goto :fail

"%VPY%" -m PyInstaller --noconfirm --clean --windowed ^
    --name RazdelenieSpravok ^
    --distpath "%BUILD_ROOT%\dist" ^
    --workpath "%BUILD_ROOT%\work" ^
    --specpath "%BUILD_ROOT%\spec" ^
    app_gui.py
if errorlevel 1 goto :fail

xcopy /E /I /Y "%TESSERACT%" "%BUILD_ROOT%\dist\RazdelenieSpravok\tesseract" >nul
if errorlevel 1 goto :fail
copy /Y "HOW_TO_USE.txt" "%BUILD_ROOT%\dist\RazdelenieSpravok\HOW_TO_USE.txt" >nul
if errorlevel 1 goto :fail
copy /Y "LICENSE" "%BUILD_ROOT%\dist\RazdelenieSpravok\LICENSE" >nul
if errorlevel 1 goto :fail
copy /Y "packaging\START.bat" "%BUILD_ROOT%\dist\RazdelenieSpravok\START.bat" >nul
if errorlevel 1 goto :fail

mkdir "%ROOT%releases" 2>nul
powershell -NoProfile -Command "$root = $env:SPRAVKI_BUILD_ROOT; Compress-Archive -Path (Join-Path $root 'dist\RazdelenieSpravok') -DestinationPath (Join-Path $root 'release.zip') -CompressionLevel Optimal"
if errorlevel 1 goto :fail
move "%BUILD_ROOT%\release.zip" "%RELEASE%" >nul
if errorlevel 1 goto :fail

rmdir /S /Q "%BUILD_ROOT%"
echo Created: %RELEASE%
exit /b 0

:fail
echo BUILD FAILED. Temporary files are at:
echo %BUILD_ROOT%
echo They were kept so the error can be inspected.
exit /b 1
