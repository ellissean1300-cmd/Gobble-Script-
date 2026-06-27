# install-gobblescript.ps1
#
# Sets up Windows so:
#   - Double-clicking a .gob file shows its printed output in a window
#     (gobblescript_textgui.py). Most GobbleScript programs print text,
#     so this is the sensible default.
#   - Right-clicking a .gob file offers "Run in Canvas (pixel) mode"
#     (gobblescript_canvas.py), for programs specifically written to draw
#     pixels, like examples/ring.gob.
#
# This script does NOT download anything. It expects gobblescript.py,
# gobblescript_canvas.py, and gobblescript_textgui.py to already be sitting
# in the same folder as this script, and points Windows at those exact
# files. Run it again any time (e.g. after moving the folder) to re-point
# the association -- it also cleans up entries from older versions of this
# installer if you'd run one before.
#
# Everything it changes lives under HKEY_CURRENT_USER, so no admin rights
# are needed, and Uninstall-GobbleScript.bat cleanly undoes all of it.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$interpScript = Join-Path $root "gobblescript.py"
$canvasScript = Join-Path $root "gobblescript_canvas.py"
$textGuiScript = Join-Path $root "gobblescript_textgui.py"

Write-Host ""
Write-Host "GobbleScript setup" -ForegroundColor Cyan
Write-Host "-------------------"

foreach ($pair in @(
    @{Path = $interpScript; Name = "gobblescript.py"},
    @{Path = $canvasScript; Name = "gobblescript_canvas.py"},
    @{Path = $textGuiScript; Name = "gobblescript_textgui.py"}
)) {
    if (-not (Test-Path $pair.Path)) {
        Write-Host "Can't find $($pair.Name) next to this script." -ForegroundColor Red
        Write-Host "Expected it at: $($pair.Path)"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

function Find-Exe {
    param([string[]]$Names)
    foreach ($name in $Names) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

# Prefer a plain python.exe / python3.exe on PATH; fall back to the
# Windows "py" launcher, which is present on most Windows Python installs
# even when python.exe isn't directly on PATH.
$pythonExe = Find-Exe -Names @("python", "python3")
$pyLauncher = Find-Exe -Names @("py")

if (-not $pythonExe -and -not $pyLauncher) {
    Write-Host "Python wasn't found on this computer." -ForegroundColor Red
    Write-Host "Install it from https://www.python.org/downloads/"
    Write-Host "(tick 'Add python.exe to PATH' during install), then run this installer again."
    Read-Host "Press Enter to exit"
    exit 1
}

if ($pythonExe) {
    $consoleExe = $pythonExe
    $windowedCandidate = $pythonExe -replace "python3?\.exe$", "pythonw.exe"
    $windowedExe = if (Test-Path $windowedCandidate) { $windowedCandidate } else { $pythonExe }
}
else {
    $consoleExe = $pyLauncher
    $windowedCandidate = $pyLauncher -replace "py\.exe$", "pyw.exe"
    $windowedExe = if (Test-Path $windowedCandidate) { $windowedCandidate } else { $pyLauncher }
}

Write-Host "Console Python:  $consoleExe"
Write-Host "Windowed Python: $windowedExe"

# --- clean up artifacts from an older version of this installer, if any ---
$classesRoot = "HKCU:\Software\Classes"
$legacyWrapper = Join-Path $root "Run-GobbleScript-Text.bat"
if (Test-Path $legacyWrapper) {
    Remove-Item -Path $legacyWrapper -Force
    Write-Host "Removed old $legacyWrapper (no longer needed)"
}
Remove-Item -Path "$classesRoot\GobbleScript.File\shell\runtext" -Recurse -Force -ErrorAction SilentlyContinue

# --- registry: associate .gob with a new GobbleScript.File type ---
New-Item -Path "$classesRoot\.gob" -Force | Out-Null
Set-Item  -Path "$classesRoot\.gob" -Value "GobbleScript.File"

New-Item -Path "$classesRoot\.gob\OpenWithProgids" -Force | Out-Null
New-ItemProperty -Path "$classesRoot\.gob\OpenWithProgids" -Name "GobbleScript.File" `
    -Value "" -PropertyType String -Force | Out-Null

New-Item -Path "$classesRoot\GobbleScript.File" -Force | Out-Null
Set-Item -Path "$classesRoot\GobbleScript.File" -Value "GobbleScript Program"

New-Item -Path "$classesRoot\GobbleScript.File\DefaultIcon" -Force | Out-Null
Set-Item -Path "$classesRoot\GobbleScript.File\DefaultIcon" -Value "$consoleExe,0"

# Double-click -> text output window (the sensible default; most programs print text)
New-Item -Path "$classesRoot\GobbleScript.File\shell\open\command" -Force | Out-Null
Set-Item -Path "$classesRoot\GobbleScript.File\shell\open\command" `
    -Value ('"' + $windowedExe + '" "' + $textGuiScript + '" "%1"')

# Right-click -> "Run in Canvas (pixel) mode", for programs that draw pixels
New-Item -Path "$classesRoot\GobbleScript.File\shell\runcanvas" -Force | Out-Null
Set-Item -Path "$classesRoot\GobbleScript.File\shell\runcanvas" -Value "Run in Canvas (pixel) mode"

New-Item -Path "$classesRoot\GobbleScript.File\shell\runcanvas\command" -Force | Out-Null
Set-Item -Path "$classesRoot\GobbleScript.File\shell\runcanvas\command" `
    -Value ('"' + $windowedExe + '" "' + $canvasScript + '" "%1"')

# --- tell Explorer the association changed, so it takes effect right away ---
Add-Type -Namespace GobbleShell -Name Notify -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(long wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@
[GobbleShell.Notify]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Double-click any .gob file to see its text output in a window."
Write-Host "Right-click a .gob file and choose 'Run in Canvas (pixel) mode' for pixel-art programs like ring.gob."
Write-Host ""
Read-Host "Press Enter to close"
