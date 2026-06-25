@echo off
REM  Build the Arvore Windows installer.
REM  Run from the repo root:   packaging\build-windows.bat
REM
REM  Prerequisites:
REM    * Python 3.10+ with PyQt6, pyserial, pyinstaller (pip install).
REM    * Inno Setup 6 (iscc.exe on PATH, or adjust the INNO variable below).
REM    * ide\arvore.ico present.

setlocal
set HERE=%~dp0
set ROOT=%HERE%..
set DIST=%ROOT%\dist

REM Auto-detect the Inno Setup compiler if it's not on PATH.
set INNO=iscc.exe
where %INNO% >nul 2>nul
if errorlevel 1 (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        set INNO="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    ) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
        set INNO="%ProgramFiles%\Inno Setup 6\ISCC.exe"
    ) else (
        echo error: ISCC.exe not found. Install Inno Setup 6 or put it on PATH.
        exit /b 1
    )
)

if not exist "%ROOT%\ide\arvore.png" (
    echo error: %ROOT%\ide\arvore.png missing.
    exit /b 1
)

if not exist "%HERE%arvore.ico" (
    echo error: %HERE%arvore.ico missing — convert the PNG to ICO first,
    echo   e.g.  magick ide\arvore.png -define icon:auto-resize ^
packaging\arvore.ico
    exit /b 1
)

echo [1/2] Running PyInstaller...
cd /d "%ROOT%"
python -m PyInstaller --clean --noconfirm packaging\arvore.spec
if errorlevel 1 exit /b 1

echo [2/2] Running Inno Setup...
%INNO% "%HERE%arvore.iss"
if errorlevel 1 exit /b 1

echo Done. Installer in %DIST%\Arvore_Setup_*.exe
endlocal
