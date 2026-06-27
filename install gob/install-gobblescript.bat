@echo off
setlocal EnableDelayedExpansion
cls

echo.
echo GobbleScript setup
echo -------------------

set "root=%~dp0"
set "interpScript=%root%gobblescript.py"
set "canvasScript=%root%gobblescript_canvas.py"
set "textGuiScript=%root%gobblescript_textgui.py"
set "iconFile=%root%Gob.ico"

:: Verify required files exist
if not exist "%interpScript%" (
    echo Can't find gobblescript.py next to this script.
    echo Expected it at: %interpScript%
    goto :error
)
if not exist "%canvasScript%" (
    echo Can't find gobblescript_canvas.py next to this script.
    echo Expected it at: %canvasScript%
    goto :error
)
if not exist "%textGuiScript%" (
    echo Can't find gobblescript_textgui.py next to this script.
    echo Expected it at: %textGuiScript%
    goto :error
)
if not exist "%iconFile%" (
    echo Can't find Gob.ico next to this script.
    echo Expected it at: %iconFile%
    goto :error
)

:: Locate Python executable or py launcher
set "pythonExe="
for /f "delims=" %%i in ('where python.exe 2^>nul') do if not defined pythonExe set "pythonExe=%%i"
if not defined pythonExe (
    for /f "delims=" %%i in ('where python3.exe 2^>nul') do if not defined pythonExe set "pythonExe=%%i"
)

set "pyLauncher="
for /f "delims=" %%i in ('where py.exe 2^>nul') do if not defined pyLauncher set "pyLauncher=%%i"

if not defined pythonExe if not defined pyLauncher (
    echo Python wasn't found on this computer.
    echo Install it from https://www.python.org/downloads/
    echo ^(tick 'Add python.exe to PATH' during install^), then run this installer again.
    goto :error
)

:: Determine console vs windowed executables
if defined pythonExe (
    set "consoleExe=%pythonExe%"
    set "windowedCandidate=%pythonExe:python.exe=pythonw.exe%"
    set "windowedCandidate=!windowedCandidate:python3.exe=pythonw.exe!"
    if exist "!windowedCandidate!" (set "windowedExe=!windowedCandidate!") else (set "windowedExe=%pythonExe%")
) else (
    set "consoleExe=%pyLauncher%"
    set "windowedCandidate=%pyLauncher:py.exe=pyw.exe%"
    if exist "!windowedCandidate!" (set "windowedExe=!windowedCandidate!") else (set "windowedExe=%pyLauncher%")
)

echo Console Python:  !consoleExe!
echo Windowed Python: !windowedExe!

:: Clean up artifacts from older installers
if exist "%root%Run-GobbleScript-Text.bat" (
    del /f "%root%Run-GobbleScript-Text.bat"
    echo Removed old %root%Run-GobbleScript-Text.bat
)
reg delete "HKCU\Software\Classes\GobbleScript.File\shell\runtext" /f >nul 2>&1

:: Associate .gob with GobbleScript.File
reg add "HKCU\Software\Classes\.gob" /ve /t REG_SZ /d "GobbleScript.File" /f >nul
reg add "HKCU\Software\Classes\.gob\OpenWithProgids" /v "GobbleScript.File" /t REG_SZ /d "" /f >nul
reg add "HKCU\Software\Classes\GobbleScript.File" /ve /t REG_SZ /d "GobbleScript Program" /f >nul

:: Use Gob.ico as the file icon
reg add "HKCU\Software\Classes\GobbleScript.File\DefaultIcon" /ve /t REG_SZ /d "!iconFile!" /f >nul

:: Double-click -> Text Output
reg add "HKCU\Software\Classes\GobbleScript.File\shell\open\command" /ve /t REG_SZ /d "\"!windowedExe!\" \"!textGuiScript!\" \"%%1\"" /f >nul

:: Right-click -> Canvas Mode
reg add "HKCU\Software\Classes\GobbleScript.File\shell\runcanvas" /ve /t REG_SZ /d "Run in Canvas (pixel) mode" /f >nul
reg add "HKCU\Software\Classes\GobbleScript.File\shell\runcanvas\command" /ve /t REG_SZ /d "\"!windowedExe!\" \"!canvasScript!\" \"%%1\"" /f >nul

:: Notify Explorer that associations changed via an inline PowerShell call
powershell -NoProfile -ExecutionPolicy Bypass -Command "$type = Add-Type -Name 'Notify' -Namespace 'GobbleShell' -MemberDefinition '[DllImport(\"shell32.dll\")] public static extern void SHChangeNotify(long e, uint f, IntPtr d1, IntPtr d2);' -PassThru; $type::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)" >nul 2>&1

echo.
echo Done.
echo The Gob.ico icon has been assigned to .gob files.
echo Double-click any .gob file to see its text output in a window.
echo Right-click a .gob file and choose 'Run in Canvas ^(pixel^) mode' for pixel-art programs.
echo.
pause
exit /b 0

:error
pause
exit /b 1