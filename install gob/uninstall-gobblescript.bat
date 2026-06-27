@echo off
setlocal EnableDelayedExpansion
cls

echo.
echo Removing GobbleScript file association...

set "root=%~dp0"

:: Delete Registry Keys
reg delete "HKCU\Software\Classes\.gob" /f >nul 2>&1
reg delete "HKCU\Software\Classes\GobbleScript.File" /f >nul 2>&1

:: Remove old wrapper artifacts if present
if exist "%root%Run-GobbleScript-Text.bat" (
    del /f "%root%Run-GobbleScript-Text.bat"
    echo Removed %root%Run-GobbleScript-Text.bat
)

:: Notify Explorer that associations changed
powershell -NoProfile -ExecutionPolicy Bypass -Command "$type = Add-Type -Name 'Notify' -Namespace 'GobbleShell' -MemberDefinition '[DllImport(\"shell32.dll\")] public static extern void SHChangeNotify(long e, uint f, IntPtr d1, IntPtr d2);' -PassThru; $type::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)" >nul 2>&1

echo Done. .gob files are no longer associated with GobbleScript.
echo.
pause
exit /b 0